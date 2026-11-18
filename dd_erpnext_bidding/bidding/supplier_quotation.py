# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe import _

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
	"""A sealed-bid submission must be complete: every item needs a rate and
	a lead time, and at least one supporting attachment. Uploading a file
	alone, with items left blank, does not count as a valid quotation.
	"""
	missing_rate = [d.idx for d in doc.items if not d.rate]
	if missing_rate:
		frappe.throw(
			_("Please enter a quoted rate for every item before submitting. Missing for row(s): {0}").format(
				", ".join(str(i) for i in missing_rate)
			),
			title=_("Incomplete Quotation"),
		)

	missing_lead_time = [d.idx for d in doc.items if not d.lead_time_days]
	if missing_lead_time:
		frappe.throw(
			_("Please enter the delivery lead time (in days) for every item. Missing for row(s): {0}").format(
				", ".join(str(i) for i in missing_lead_time)
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
