# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

"""Shared constants for the sealed vendor bidding workflow.

Roles allowed to open bids. Adjust here if the organisation wants a
narrower or wider set of roles.
"""

BID_OPENER_ROLES = ("Purchase Manager", "System Manager")

# Supplier Quotation Item fields that carry pricing/competitive information
# and must be zeroed out in the real columns while a bid is sealed.
SQ_ITEM_MONEY_FIELDS = (
	"price_list_rate",
	"base_price_list_rate",
	"discount_percentage",
	"discount_amount",
	"rate",
	"amount",
	"base_rate",
	"base_amount",
	"net_rate",
	"net_amount",
	"base_net_rate",
	"base_net_amount",
	"lead_time_days",
)

# Supplier Quotation parent fields that carry computed totals.
SQ_PARENT_MONEY_FIELDS = (
	"total",
	"base_total",
	"net_total",
	"base_net_total",
	"total_taxes_and_charges",
	"base_total_taxes_and_charges",
	"taxes_and_charges_added",
	"base_taxes_and_charges_added",
	"taxes_and_charges_deducted",
	"base_taxes_and_charges_deducted",
	"discount_amount",
	"base_discount_amount",
	"grand_total",
	"base_grand_total",
	"rounding_adjustment",
	"base_rounding_adjustment",
	"rounded_total",
	"base_rounded_total",
	"in_words",
	"base_in_words",
)

# Supplier Quotation Taxes and Charges child row fields that carry amounts.
SQ_TAXES_MONEY_FIELDS = (
	"tax_amount",
	"total",
	"base_tax_amount",
	"base_total",
	"tax_amount_after_discount_amount",
	"base_tax_amount_after_discount_amount",
)

EVENT_SUBMITTED = "Quotation Submitted"
EVENT_LATE_BLOCKED = "Late Submission Blocked"
EVENT_AMENDMENT_BLOCKED = "Amendment Blocked"
EVENT_BIDS_OPENED = "Bids Opened"
EVENT_COMPARISON_GENERATED = "Comparative Statement Generated"
