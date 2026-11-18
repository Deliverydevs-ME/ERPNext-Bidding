# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

"""Doctype class override (hooks.py `override_doctype_class`) for the
standard erpnext Request for Quotation controller.

Fixes three things in core's own `send_to_supplier()` email, without
touching erpnext's files:

1. "Set Password" was a dead link (empty href) for any supplier whose
   portal User already existed - core only generates a reset-password
   link when it creates a brand new User. We generate one unconditionally
   instead, which is always safe (it just issues a fresh one-time key).

2. "Submit your Quotation" always pointed at the bare RFQ item-entry page,
   which has no field for lead time or an attachment - both mandatory for
   a sealed bid, and the generic Supplier Quotation web view that creates
   is read-only besides. For bidding-enabled RFQs we instead send each
   supplier straight to their own pre-created Draft quotation on our
   dedicated editable page (see www/submit_quotation.py), which a Draft
   already exists for by the time this email goes out - see
   `_create_draft_quotations` in request_for_quotation.py, which runs in
   `validate()`, always before `on_submit` (and this email) fires.

3. `get_link()` has no per-supplier context (core calls it identically
   for every supplier in the loop), so finding each supplier's own draft
   and building its own URL requires overriding the loop itself rather
   than just the one link-building method - hence `send_to_supplier` is
   reimplemented here, kept as close to erpnext's original as possible.
"""

import frappe
from frappe.utils import get_url

from erpnext.buying.doctype.request_for_quotation.request_for_quotation import RequestforQuotation


class RequestforQuotationBidding(RequestforQuotation):
	def get_link(self):
		if self.enable_vendor_bidding:
			return get_url("/supplier-quotations")
		return super().get_link()

	def update_supplier_contact(self, rfq_supplier, link):
		update_password_link, contact = "", ""

		if frappe.db.exists("User", rfq_supplier.email_id):
			user = frappe.get_doc("User", rfq_supplier.email_id)
			update_password_link = user.reset_password()
		else:
			user, update_password_link = self.create_user(rfq_supplier, link)

		contact = self.link_supplier_contact(rfq_supplier, user)
		return update_password_link, contact

	def get_supplier_quotation_link(self, supplier):
		"""This supplier's own pre-created Draft Supplier Quotation link for
		this RFQ, or the generic RFQ link if bidding isn't enabled or no
		draft exists yet (e.g. this supplier's row didn't make it into
		`_create_draft_quotations`, which should not normally happen).
		"""
		if not self.enable_vendor_bidding:
			return self.get_link()

		sq_name = frappe.db.sql(
			"""
			select sq.name from `tabSupplier Quotation` sq
			inner join `tabSupplier Quotation Item` sqi on sqi.parent = sq.name
			where sq.supplier = %s and sqi.request_for_quotation = %s and sq.docstatus = 0
			limit 1
			""",
			(supplier, self.name),
		)
		if sq_name:
			return get_url(f"/submit-quotation/{sq_name[0][0]}")

		return self.get_link()

	def send_to_supplier(self):
		"""Same as erpnext's RequestforQuotation.send_to_supplier(), except
		each supplier's link points at their own quotation (see above)
		instead of calling self.get_link() for everyone alike.
		"""
		for rfq_supplier in self.suppliers:
			if rfq_supplier.email_id is not None and rfq_supplier.send_email:
				self.validate_email_id(rfq_supplier)

				link = self.get_supplier_quotation_link(rfq_supplier.supplier)
				update_password_link, contact = self.update_supplier_contact(rfq_supplier, link)

				self.update_supplier_part_no(rfq_supplier.supplier)
				self.supplier_rfq_mail(rfq_supplier, update_password_link, link)
				rfq_supplier.email_sent = 1
				if not rfq_supplier.contact:
					rfq_supplier.contact = contact
				rfq_supplier.save()
