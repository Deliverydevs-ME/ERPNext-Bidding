# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

BIDDING_ENABLED = "eval:doc.enable_vendor_bidding"

# Doctypes/fields from an earlier iteration of this app (in-RFQ multi-round
# table + passwordless vendor links) that the tender spec replaced with:
# one RFQ per round, and suppliers logging into the native ERPNext portal.
# Removed on every migrate so a stale site never keeps the old shape.
OBSOLETE_DOCTYPES = ["Vendor Bidding Link", "Bidding Round"]
OBSOLETE_CUSTOM_FIELDS = {
	"Request for Quotation": ["current_round", "sb_bidding_rounds", "bidding_rounds"],
}

CUSTOM_FIELDS = {
	"Request for Quotation": [
		{
			"fieldname": "tender_material_request",
			"fieldtype": "Link",
			"label": "Material Request (Tender)",
			"options": "Material Request",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "amended_from",
			"description": "The tender's parent Material Request. Every RFQ raised against the same "
			"Material Request with Vendor Bidding enabled is automatically numbered as the next round.",
		},
		{
			"fieldname": "sb_vendor_bidding",
			"fieldtype": "Section Break",
			"label": "Vendor Bidding",
			"insert_after": "tender_material_request",
			"collapsible": 1,
		},
		{
			"fieldname": "enable_vendor_bidding",
			"fieldtype": "Check",
			"label": "Enable Vendor Bidding",
			"insert_after": "sb_vendor_bidding",
			"description": "Seal every vendor's quotation until bids are opened - nobody, including "
			"Purchase Manager, can view a submitted amount before then.",
		},
		{
			"fieldname": "bidding_round_number",
			"fieldtype": "Int",
			"label": "Bidding Round",
			"default": "1",
			"read_only": 1,
			"insert_after": "enable_vendor_bidding",
			"depends_on": BIDDING_ENABLED,
			"no_copy": 1,
			"description": "Which round this RFQ will become, among all bidding-enabled RFQs raised "
			"against the same Material Request. Previewed live while still a draft; set for real "
			"on submit.",
		},
		{
			"fieldname": "cb_vendor_bidding_1",
			"fieldtype": "Column Break",
			"insert_after": "bidding_round_number",
		},
		{
			"fieldname": "bidding_closing_date",
			"fieldtype": "Datetime",
			"label": "Submission Deadline",
			"insert_after": "cb_vendor_bidding_1",
			"depends_on": BIDDING_ENABLED,
			"mandatory_depends_on": BIDDING_ENABLED,
			"allow_on_submit": 1,
			"description": "Last date/time suppliers may submit or amend their quotation. Enforced "
			"server-side - late submissions and amendments are rejected automatically.",
		},
		{
			"fieldname": "bidding_opening_date",
			"fieldtype": "Datetime",
			"label": "Opening Date & Time (For Internal Users)",
			"insert_after": "bidding_closing_date",
			"depends_on": BIDDING_ENABLED,
			"mandatory_depends_on": BIDDING_ENABLED,
			"allow_on_submit": 1,
			"description": "When submitted quotations are revealed to internal users. Must be after "
			"the submission deadline.",
		},
		{
			"fieldname": "cb_vendor_bidding_2",
			"fieldtype": "Column Break",
			"insert_after": "bidding_opening_date",
		},
		{
			"fieldname": "bidding_status",
			"fieldtype": "Select",
			"label": "Bidding Status",
			"options": "\nBidding Open\nBids Opened",
			"read_only": 1,
			"insert_after": "cb_vendor_bidding_2",
			"depends_on": BIDDING_ENABLED,
			"allow_on_submit": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "actual_bidding_opening_date",
			"fieldtype": "Datetime",
			"label": "Actual Opening Date & Time",
			"read_only": 1,
			"insert_after": "bidding_status",
			"depends_on": BIDDING_ENABLED,
			"allow_on_submit": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "actual_bidding_closing_date",
			"fieldtype": "Datetime",
			"label": "Actual Closing Date & Time",
			"read_only": 1,
			"insert_after": "actual_bidding_opening_date",
			"depends_on": BIDDING_ENABLED,
			"allow_on_submit": 1,
			"no_copy": 1,
		},
	],
	"Supplier Quotation": [
		{
			"fieldname": "bidding_reference",
			"fieldtype": "Link",
			"label": "Bidding RFQ Reference",
			"options": "Request for Quotation",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
			"insert_after": "amended_from",
		},
		{
			"fieldname": "bidding_round",
			"fieldtype": "Int",
			"label": "Bidding Round",
			"default": "0",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
			"insert_after": "bidding_reference",
		},
		{
			"fieldname": "is_sealed_bid",
			"fieldtype": "Check",
			"label": "Sealed Bid",
			"default": "0",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
			"insert_after": "bidding_round",
		},
		{
			"fieldname": "sealed_bid_payload",
			"fieldtype": "Password",
			"label": "Sealed Bid Payload",
			"hidden": 1,
			"no_copy": 1,
			"insert_after": "is_sealed_bid",
		},
		{
			"fieldname": "sealed_bid_notice",
			"fieldtype": "HTML",
			"label": "",
			"read_only": 1,
			"insert_after": "sealed_bid_payload",
			"depends_on": "eval:doc.is_sealed_bid",
			"options": (
				"<div class='alert alert-warning'>"
				"\U0001f512 This bid is sealed. Rates, delivery dates and attachments are hidden from "
				"everyone - including Purchase Manager and System Manager - until this RFQ's bidding "
				"window opens."
				"</div>"
			),
		},
	],
	"Supplier Quotation Comparison Tool": [
		{
			"fieldname": "bidding_round",
			"fieldtype": "Int",
			"label": "Bidding Round",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "request_for_quotation",
		},
	],
	"Material Request": [
		{
			"fieldname": "tender_reference",
			"fieldtype": "Data",
			"label": "Tender / Bidding Reference",
			"insert_after": "title",
			"description": "Free-text tender code/name (e.g. 'Tender A') identifying this bidding "
			"exercise - carried for reference on every RFQ round raised against this Material Request.",
		},
		{
			"fieldname": "material_request_type_link",
			"fieldtype": "Link",
			"label": "Request Type",
			"options": "Material Request Type",
			"insert_after": "material_request_type",
		},
		{
			"fieldname": "custom_project",
			"fieldtype": "Link",
			"label": "Project",
			"options": "Project",
			"insert_after": "material_request_type_link",
		},
	],
	"Request for Quotation Item": [
		{
			"fieldname": "material_request_type_link",
			"fieldtype": "Link",
			"label": "Request Type",
			"options": "Material Request Type",
			"fetch_from": "material_request.material_request_type_link",
			"read_only": 1,
			"print_hide": 1,
			"insert_after": "material_request_item",
		},
	],
}

# "Request for Quotation Item" already ships its own "Project" field
# (project_name) with no fetch_from - rather than add a duplicate field, we
# point the existing one at Material Request.custom_project.
PROPERTY_SETTERS = [
	{
		"doctype": "Request for Quotation Item",
		"fieldname": "project_name",
		"property": "fetch_from",
		"value": "material_request.custom_project",
		"property_type": "Small Text",
	},
	{
		"doctype": "Request for Quotation Item",
		"fieldname": "project_name",
		"property": "read_only",
		"value": "1",
		"property_type": "Check",
	},
]


def after_install():
	create_fields()


def create_fields():
	remove_obsolete()
	create_custom_fields(CUSTOM_FIELDS, update=True)
	for ps in PROPERTY_SETTERS:
		make_property_setter(
			ps["doctype"], ps["fieldname"], ps["property"], ps["value"], ps["property_type"], for_doctype=False
		)
	flag_bidding_request_types()


def flag_bidding_request_types():
	"""Best-effort, idempotent: if a "Tender (Bidding)" Material Request Type
	already exists (as created manually on this site), flag it so RFQs
	created from a Material Request of that type default to Enable Vendor
	Bidding = checked. Harmless no-op if it doesn't exist yet or is already
	flagged.
	"""
	if frappe.db.exists("Material Request Type", "Tender (Bidding)"):
		frappe.db.set_value("Material Request Type", "Tender (Bidding)", "is_bidding_type", 1)


def remove_obsolete():
	for doctype, fieldnames in OBSOLETE_CUSTOM_FIELDS.items():
		for fieldname in fieldnames:
			name = f"{doctype}-{fieldname}"
			if frappe.db.exists("Custom Field", name):
				frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

	for doctype in OBSOLETE_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, ignore_permissions=True, force=True)
