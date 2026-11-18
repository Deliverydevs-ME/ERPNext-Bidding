# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from dd_erpnext_bidding.bidding import constants
from dd_erpnext_bidding.bidding.audit import log_event
from dd_erpnext_bidding.bidding.comparison import generate_comparison_statement
from dd_erpnext_bidding.bidding.crypto import unseal_supplier_quotation


def validate(doc, method=None):
	if not doc.tender_material_request:
		for d in doc.items:
			if d.material_request:
				doc.tender_material_request = d.material_request
				break

	if not doc.enable_vendor_bidding:
		return

	if not doc.bidding_opening_date or not doc.bidding_closing_date:
		frappe.throw(
			_("Set both the Submission Deadline and the Opening Date & Time to enable vendor bidding."),
			title=_("Vendor Bidding"),
		)

	if get_datetime(doc.bidding_closing_date) >= get_datetime(doc.bidding_opening_date):
		frappe.throw(
			_("The Submission Deadline must be before the Opening Date & Time - vendors must submit "
			  "before bids can be opened."),
			title=_("Vendor Bidding"),
		)


def on_submit(doc, method=None):
	if not doc.enable_vendor_bidding:
		return

	round_number = 1
	if doc.tender_material_request:
		round_number = (
			cint(
				frappe.db.count(
					"Request for Quotation",
					{
						"tender_material_request": doc.tender_material_request,
						"enable_vendor_bidding": 1,
						"docstatus": 1,
						"name": ["!=", doc.name],
					},
				)
			)
			+ 1
		)

	doc.db_set(
		{"bidding_round_number": round_number, "bidding_status": "Bidding Open"}, update_modified=False
	)


def _check_bid_opener_role():
	frappe.only_for(constants.BID_OPENER_ROLES, message=True)


@frappe.whitelist()
def open_bids(request_for_quotation):
	"""Manually open (reveal) sealed bids for this RFQ - normally this also
	happens automatically via the scheduled `auto_open_bids` job once the
	Opening Date & Time arrives.
	"""
	_check_bid_opener_role()
	rfq = frappe.get_doc("Request for Quotation", request_for_quotation)
	return _do_open(rfq, opened_by=frappe.session.user)


def _do_open(rfq, opened_by=None, auto=False):
	if rfq.bidding_status == "Bids Opened":
		return {"already_opened": True}

	now = now_datetime()
	actual_closing = now
	if rfq.bidding_closing_date and get_datetime(rfq.bidding_closing_date) < now:
		actual_closing = get_datetime(rfq.bidding_closing_date)

	rfq.db_set(
		{
			"bidding_status": "Bids Opened",
			"actual_bidding_opening_date": now,
			"actual_bidding_closing_date": actual_closing,
		},
		update_modified=False,
	)

	sq_names = frappe.get_all(
		"Supplier Quotation",
		filters={"bidding_reference": rfq.name, "docstatus": 1, "is_sealed_bid": 1},
		pluck="name",
	)

	unsealed = sum(1 for name in sq_names if unseal_supplier_quotation(name))

	log_event(
		rfq.doctype,
		rfq.name,
		constants.EVENT_BIDS_OPENED,
		round_number=rfq.bidding_round_number,
		user=opened_by or "Administrator",
		details=f"{rfq.name} opened{' automatically' if auto else ''} - {unsealed} sealed quotation(s) "
		f"out of {len(sq_names)} submitted revealed simultaneously.",
	)

	statement_name = None
	if unsealed:
		statement_name = generate_comparison_statement(rfq.name, rfq.bidding_round_number)

	return {"unsealed": unsealed, "comparison_statement": statement_name}


def auto_open_bids():
	"""Scheduled task (see hooks.py): opens every RFQ whose Opening Date &
	Time has arrived, so all its bids are revealed simultaneously without
	anyone needing to click a button.
	"""
	now = now_datetime()
	rfq_names = frappe.get_all(
		"Request for Quotation",
		filters={"docstatus": 1, "enable_vendor_bidding": 1, "bidding_status": "Bidding Open"},
		pluck="name",
	)

	for name in rfq_names:
		rfq = frappe.get_doc("Request for Quotation", name)
		if rfq.bidding_opening_date and now >= get_datetime(rfq.bidding_opening_date):
			try:
				_do_open(rfq, opened_by="Administrator", auto=True)
			except Exception:
				frappe.log_error(title="Auto bid opening failed", message=frappe.get_traceback())
