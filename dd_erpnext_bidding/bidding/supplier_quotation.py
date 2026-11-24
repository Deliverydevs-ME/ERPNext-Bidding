# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from dd_erpnext_bidding.bidding import constants
from dd_erpnext_bidding.bidding.audit import log_event
from dd_erpnext_bidding.bidding.crypto import seal_supplier_quotation
from dd_erpnext_bidding.bidding.utils import bidding_is_open, get_linked_rfq


def validate(doc, method=None):
	rfq_name = get_linked_rfq(doc)
	if not rfq_name:
		return

	rfq_doc = frappe.get_doc("Request for Quotation", rfq_name)
	if not rfq_doc.enable_vendor_bidding:
		return

	doc.bidding_reference = rfq_name
	if not doc.bidding_round:
		doc.bidding_round = rfq_doc.bidding_round_number

	if doc.docstatus == 1:
		_validate_complete_bid(doc)

	if doc.flags.ignore_bidding_window_check:
		return

	if not bidding_is_open(rfq_doc):
		event = constants.EVENT_LATE_BLOCKED if doc.is_new() else constants.EVENT_AMENDMENT_BLOCKED
		log_event(
			"Request for Quotation",
			rfq_name,
			event,
			supplier=doc.supplier,
			round_number=doc.bidding_round,
			details=f"Blocked {'submission' if doc.is_new() else 'amendment'} on Supplier Quotation "
			f"{doc.name or '(new)'} - this RFQ's bidding window is no longer open.",
		)
		frappe.throw(
			_("The bidding window for {0} is closed. No new submissions or changes are accepted.").format(
				rfq_name
			),
			title=_("Bidding Closed"),
		)


def _validate_complete_bid(doc):
	"""A sealed-bid submission must be complete: every item needs a rate, and
	at least one supporting attachment. Expected delivery date and lead
	time are optional. Uploading a file alone, with items left blank, does
	not count as a valid quotation.
	"""
	missing_rate = [d.idx for d in doc.items if not d.rate]
	if missing_rate:
		frappe.throw(
			_("Please enter a quoted rate for every item before submitting. Missing for row(s): {0}").format(
				", ".join(str(i) for i in missing_rate)
			),
			title=_("Incomplete Quotation"),
		)

	if not frappe.db.exists("File", {"attached_to_doctype": doc.doctype, "attached_to_name": doc.name}):
		frappe.throw(
			_(
				"Please attach your supporting document (PDF/Excel) before submitting. A quotation "
				"with no rates is not accepted even if a file is attached, and a file alone is not "
				"accepted without item-wise rates."
			),
			title=_("Incomplete Quotation"),
		)


def on_submit(doc, method=None):
	rfq_name = doc.bidding_reference or get_linked_rfq(doc)
	if not rfq_name:
		return

	if not frappe.db.get_value("Request for Quotation", rfq_name, "enable_vendor_bidding"):
		return

	seal_supplier_quotation(doc)

	log_event(
		"Request for Quotation",
		rfq_name,
		constants.EVENT_SUBMITTED,
		supplier=doc.supplier,
		round_number=doc.bidding_round,
		details=f"Supplier Quotation {doc.name} submitted and sealed (round {doc.bidding_round}).",
	)


@frappe.whitelist()
def save_quotation(name, items, action="save", valid_till=None):
	"""Backs the /submit-quotation/<name> portal page (www/submit_quotation.py).

	The generic Supplier Quotation web view is read-only and has no field
	for expected delivery date or an attachment, so logged-in suppliers
	fill in their bid through this dedicated page instead - this is what
	it calls to save rates/dates and, on final submit, hand off to the
	exact same validate/seal pipeline every other path into Supplier
	Quotation goes through. Login is required (not allow_guest); write
	permission on the specific document is still checked explicitly below.
	"""
	doc = frappe.get_doc("Supplier Quotation", name)
	if not frappe.has_website_permission(doc, "write"):
		frappe.throw(_("You are not permitted to edit this quotation."), frappe.PermissionError)

	if doc.docstatus != 0:
		frappe.throw(_("This quotation is no longer editable."))

	if isinstance(items, str):
		items = frappe.parse_json(items)

	by_name = {d.name: d for d in doc.items}
	for incoming in items:
		row = by_name.get(incoming.get("name"))
		if not row:
			continue  # never trust a row name that isn't actually on this document
		row.rate = flt(incoming.get("rate"))
		row.expected_delivery_date = incoming.get("expected_delivery_date") or None
		row.lead_time_days = cint(incoming.get("lead_time_days"))

	doc.valid_till = valid_till or None

	# Authorization was already checked above via frappe.has_website_permission -
	# the right mechanism for a portal/Website User, who has no desk role and so
	# would otherwise fail the standard role-based permission check on save/submit.
	doc.flags.ignore_permissions = True
	doc.save()

	if action == "submit":
		doc.flags.ignore_permissions = True
		doc.submit()

	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def upload_quotation_attachment(name):
	"""Standalone upload endpoint for the /submit-quotation/<name> page.

	Frappe's own `/api/method/upload_file` checks write permission via
	`doc.check_permission()` - the standard, role-based desk check - which
	a portal supplier (a Website User, or even a System User with no
	desk role on this doctype) always fails. Supplier Quotation's actual
	portal access is governed by `frappe.has_website_permission` instead
	(Contact/Supplier linkage), so file upload needs its own endpoint that
	checks the right thing, the same as save_quotation above.
	"""
	doc = frappe.get_doc("Supplier Quotation", name)
	if not frappe.has_website_permission(doc, "write"):
		frappe.throw(_("You are not permitted to attach files to this quotation."), frappe.PermissionError)

	if doc.docstatus != 0:
		frappe.throw(_("This quotation is no longer editable."))

	if "file" not in frappe.request.files:
		frappe.throw(_("No file was received."))

	upload = frappe.request.files["file"]

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": upload.filename,
			"attached_to_doctype": "Supplier Quotation",
			"attached_to_name": name,
			"content": upload.stream.read(),
			"is_private": 1,
		}
	)
	file_doc.flags.ignore_permissions = True
	file_doc.insert(ignore_permissions=True)

	return {"file_name": file_doc.file_name, "file_url": file_doc.file_url}


def has_file_permission(doc, ptype=None, user=None, debug=False):
	"""Doc-events `has_permission` hook for the File doctype (hooks.py).

	Blocks read/download of any file attached to a sealed Supplier Quotation
	for everyone - this is what keeps a supplier's PDF/Excel attachment just
	as confidential as their rates until the RFQ opens. Returning None defers
	to the normal permission system (this hook only ever denies, never
	grants - see frappe.permissions.has_controller_permissions).

	Caveat: like every permission-hook-based restriction in Frappe, this
	does not apply to the Administrator account, which bypasses all
	controller permission hooks by design.
	"""
	if doc.attached_to_doctype != "Supplier Quotation" or not doc.attached_to_name:
		return None

	if frappe.db.get_value("Supplier Quotation", doc.attached_to_name, "is_sealed_bid"):
		return False

	return None
