# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

"""Seal / unseal the pricing data on a submitted Supplier Quotation.

The real rate/amount/total values are moved into an encrypted blob stored in
a Password-type field (`sealed_bid_payload`). Frappe stores Password field
values in the separate, encrypted `__Auth` table and never returns them
through normal document reads (desk, REST API, list view, report builder,
print) regardless of role - including Administrator. The plaintext columns
are zeroed at the same time, so there is nothing sensitive left in the
document's own row for any read path to leak while a bid is sealed.
"""

import json

import frappe
from frappe.utils.password import remove_encrypted_password, set_encrypted_password

from dd_erpnext_bidding.bidding.constants import (
	DATE_FIELDS,
	SQ_ITEM_MONEY_FIELDS,
	SQ_PARENT_MONEY_FIELDS,
	SQ_TAXES_MONEY_FIELDS,
	TEXT_FIELDS,
)

SEALED_PAYLOAD_FIELD = "sealed_bid_payload"


def _empty_value(fieldname):
	if fieldname in DATE_FIELDS:
		return None
	if fieldname.endswith("in_words") or fieldname in TEXT_FIELDS:
		return ""
	return 0


def _coerce(fieldname, value):
	"""Columns like `discount_amount` are NOT NULL in the database but can
	come back as None from an in-memory doc that never touched them. Writing
	None back via a raw db_set during unseal would violate that constraint,
	so normalise to the same "empty" value the ORM would have written.
	"""
	if value is not None:
		return value
	return _empty_value(fieldname)


def seal_supplier_quotation(doc):
	"""Called right after a Supplier Quotation is submitted.

	`doc` already has its real values persisted (submit ran normally so
	erpnext's own tax/total calculations are trusted). We now read those real
	values back out, encrypt them, and overwrite the plaintext columns with
	zeros via direct db writes (bypassing the controller so nothing
	recalculates them back).
	"""
	payload = {
		"items": {d.name: {f: _coerce(f, d.get(f)) for f in SQ_ITEM_MONEY_FIELDS} for d in doc.items},
		"taxes": {
			d.name: {f: _coerce(f, d.get(f)) for f in SQ_TAXES_MONEY_FIELDS}
			for d in doc.get("taxes") or []
		},
		"parent": {f: _coerce(f, doc.get(f)) for f in SQ_PARENT_MONEY_FIELDS},
	}

	# frappe.as_json (not plain json.dumps) because item/date fields can come
	# back as real date/datetime objects - e.g. after a reload - which the
	# stdlib json module can't serialise on its own.
	set_encrypted_password(doc.doctype, doc.name, frappe.as_json(payload), SEALED_PAYLOAD_FIELD)

	zeroed_items = {f: _empty_value(f) for f in SQ_ITEM_MONEY_FIELDS}
	for d in doc.items:
		frappe.db.set_value(d.doctype, d.name, zeroed_items, update_modified=False)

	for d in doc.get("taxes") or []:
		frappe.db.set_value(d.doctype, d.name, dict.fromkeys(SQ_TAXES_MONEY_FIELDS, 0), update_modified=False)

	zeroed_parent = {f: _empty_value(f) for f in SQ_PARENT_MONEY_FIELDS}
	zeroed_parent[SEALED_PAYLOAD_FIELD] = "*" * 8
	zeroed_parent["is_sealed_bid"] = 1
	frappe.db.set_value(doc.doctype, doc.name, zeroed_parent, update_modified=False)


def unseal_supplier_quotation(sq_name):
	"""Restore the real values onto a previously sealed Supplier Quotation.

	Returns True if a payload was found and restored, False otherwise (e.g.
	called twice, or the document was never actually sealed).
	"""
	is_sealed = frappe.db.get_value("Supplier Quotation", sq_name, "is_sealed_bid")
	if not is_sealed:
		return False

	from frappe.utils.password import get_decrypted_password

	raw = get_decrypted_password(
		"Supplier Quotation", sq_name, SEALED_PAYLOAD_FIELD, raise_exception=False
	)
	if not raw:
		frappe.log_error(
			title="Sealed bid payload missing",
			message=f"Supplier Quotation {sq_name} was marked sealed but no encrypted payload was found.",
		)
		return False

	payload = json.loads(raw)

	for row_name, values in payload.get("items", {}).items():
		frappe.db.set_value("Supplier Quotation Item", row_name, values, update_modified=False)

	for row_name, values in payload.get("taxes", {}).items():
		frappe.db.set_value("Purchase Taxes and Charges", row_name, values, update_modified=False)

	parent_values = dict(payload.get("parent", {}))
	parent_values["is_sealed_bid"] = 0
	frappe.db.set_value("Supplier Quotation", sq_name, parent_values, update_modified=False)

	remove_encrypted_password("Supplier Quotation", sq_name, SEALED_PAYLOAD_FIELD)
	frappe.db.set_value("Supplier Quotation", sq_name, SEALED_PAYLOAD_FIELD, "", update_modified=False)

	return True
