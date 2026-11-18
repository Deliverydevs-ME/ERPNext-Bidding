# Copyright (c) 2026, Delivery Devs
# For license information, please see license.txt

"""Auto-generate the comparative statement once a round's bids are opened.

Reuses the existing `Supplier Quotation Comparison Tool` (falcon app) rather
than inventing a parallel doctype - that tool already knows how to pick the
lowest price per item (splitting ties) and spin up draft Purchase Orders
from the result. We only add a `bidding_round` tag to it and feed it rows
scoped to a single bidding round (its own `fetch_quotations` pulls every
submitted quotation ever linked to the RFQ, across all rounds, which is not
what we want here).
"""

import frappe

from dd_erpnext_bidding.bidding import constants
from dd_erpnext_bidding.bidding.audit import log_event


def get_round_quotation_rows(request_for_quotation, round_number):
	sq = frappe.qb.DocType("Supplier Quotation")
	sq_item = frappe.qb.DocType("Supplier Quotation Item")

	query = (
		frappe.qb.from_(sq_item)
		.from_(sq)
		.select(
			sq_item.item_code,
			sq_item.qty,
			sq_item.uom,
			sq_item.rate,
			sq_item.amount,
			sq_item.warehouse,
			sq_item.parent.as_("supplier_quotation"),
			sq.supplier,
		)
		.where(
			(sq_item.parent == sq.name)
			& (sq_item.docstatus == 1)
			& (sq.status != "Expired")
			& (sq.is_sealed_bid == 0)
			& (sq_item.request_for_quotation == request_for_quotation)
			& (sq.bidding_round == round_number)
		)
		.orderby(sq_item.item_code)
		.orderby(sq.supplier)
	)

	return query.run(as_dict=True)


def generate_comparison_statement(request_for_quotation, round_number):
	rows = get_round_quotation_rows(request_for_quotation, round_number)
	if not rows:
		return None

	company = frappe.db.get_value("Request for Quotation", request_for_quotation, "company")

	tool = frappe.new_doc("Supplier Quotation Comparison Tool")
	tool.request_for_quotation = request_for_quotation
	tool.company = company
	tool.bidding_round = round_number

	for r in rows:
		price_per_unit = r.rate or ((r.amount / r.qty) if r.qty else 0)
		tool.append(
			"items",
			{
				"item_code": r.item_code,
				"supplier": r.supplier,
				"uom": r.uom,
				"qty": r.qty,
				"total_amount": r.amount,
				"price_per_unit": price_per_unit,
				"supplier_quotation": r.supplier_quotation,
				"warehouse": r.warehouse,
			},
		)

	tool.tick_lowest_price_as_preferred()
	tool.flags.ignore_permissions = True
	tool.insert(ignore_permissions=True)
	tool.submit()

	_attach_pdf_snapshot(tool)

	log_event(
		"Request for Quotation",
		request_for_quotation,
		constants.EVENT_COMPARISON_GENERATED,
		round_number=round_number,
		details=f"Comparative statement {tool.name} generated for round {round_number} "
		f"({len(rows)} quotation lines from {len({r.supplier for r in rows})} supplier(s)).",
	)

	return tool.name


def _attach_pdf_snapshot(tool):
	try:
		pdf = frappe.get_print(tool.doctype, tool.name, as_pdf=True)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{tool.name}.pdf",
				"attached_to_doctype": tool.doctype,
				"attached_to_name": tool.name,
				"content": pdf,
				"is_private": 1,
			}
		)
		file_doc.flags.ignore_permissions = True
		file_doc.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Comparison statement PDF snapshot failed", message=frappe.get_traceback())
