# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe


def log_event(
	reference_doctype,
	reference_name,
	event_type,
	details="",
	supplier=None,
	round_number=None,
	user=None,
	ip_address=None,
):
	"""Append one immutable entry to the Bidding Audit Log.

	Never raises - a logging failure must never block the actual bidding
	action it is recording.
	"""
	try:
		log = frappe.new_doc("Bidding Audit Log")
		log.event_type = event_type
		log.reference_doctype = reference_doctype
		log.reference_name = reference_name
		log.round_number = round_number
		log.supplier = supplier
		log.user = user or frappe.session.user
		log.ip_address = ip_address or _get_request_ip()
		log.details = details
		log.flags.ignore_permissions = True
		log.insert(ignore_permissions=True)
		return log.name
	except Exception:
		frappe.log_error(title="Bidding Audit Log failed", message=frappe.get_traceback())
		return None


def _get_request_ip():
	try:
		return frappe.local.request_ip
	except Exception:
		return None
