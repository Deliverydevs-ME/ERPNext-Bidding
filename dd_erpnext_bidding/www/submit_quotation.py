# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe.utils import quote

no_cache = 1


def get_context(context):
	context.no_cache = 1

	sqname = frappe.form_dict.get("sqname")

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
		raise frappe.Redirect

	try:
		doc = frappe.get_doc("Supplier Quotation", sqname)
	except frappe.DoesNotExistError:
		frappe.local.flags.redirect_location = "/supplier-quotations"
		raise frappe.Redirect

	if not frappe.has_website_permission(doc, "read"):
		frappe.throw(
			"You are not permitted to view this quotation.", frappe.PermissionError, title="Not Permitted"
		)

	rfq_name = next((d.request_for_quotation for d in doc.items if d.request_for_quotation), None)
	closing_date = None
	if rfq_name:
		closing_date = frappe.db.get_value("Request for Quotation", rfq_name, "bidding_closing_date")

	context.sq = doc
	context.sq_name = doc.name
	context.supplier_name = frappe.db.get_value("Supplier", doc.supplier, "supplier_name") or doc.supplier
	context.rfq_name = rfq_name
	context.closing_date = closing_date
	context.is_editable = doc.docstatus == 0 and frappe.has_website_permission(doc, "write")
	context.already_submitted = doc.docstatus == 1
	context.currency = doc.currency
	context.currency_symbol = (
		frappe.db.get_value("Currency", doc.currency, "symbol") or doc.currency or ""
	)
