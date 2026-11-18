# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

from frappe.utils import get_datetime, now_datetime


def get_linked_rfq(sq_doc):
	"""Return the Request for Quotation name this Supplier Quotation was
	created against, or None if it wasn't created from an RFQ.
	"""
	for d in sq_doc.items:
		if d.request_for_quotation:
			return d.request_for_quotation
	return None


def bidding_is_open(rfq_doc):
	"""True while suppliers are still allowed to submit/amend against this RFQ."""
	if not rfq_doc.enable_vendor_bidding:
		return False
	if rfq_doc.bidding_status == "Bids Opened":
		return False
	if rfq_doc.bidding_closing_date and now_datetime() > get_datetime(rfq_doc.bidding_closing_date):
		return False
	return True
