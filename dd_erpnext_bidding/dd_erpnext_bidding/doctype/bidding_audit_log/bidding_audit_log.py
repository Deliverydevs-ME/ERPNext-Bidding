# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BiddingAuditLog(Document):
	def on_update(self):
		if not self.is_new():
			frappe.throw("Bidding Audit Log entries cannot be modified once created.")
