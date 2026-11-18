frappe.ui.form.on("Request for Quotation", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.enable_vendor_bidding) {
			return;
		}

		const can_open_bids = frappe.user.has_role("Purchase Manager") || frappe.user.has_role("System Manager");
		if (can_open_bids && frm.doc.bidding_status !== "Bids Opened") {
			frm.add_custom_button(__("Open Bids Now"), () => open_bids(frm), __("Vendor Bidding"));
		}

		if (frm.doc.bidding_status === "Bids Opened") {
			frm.dashboard.add_comment(
				__(
					"Bids opened on {0}. To run another bidding round for this tender, create a new " +
						"Request for Quotation against the same Material Request.",
					[frappe.datetime.str_to_user(frm.doc.actual_bidding_opening_date)]
				),
				"blue",
				true
			);
		}
	},
});

function open_bids(frm) {
	frappe.confirm(
		__(
			"This will reveal every sealed quotation submitted for this RFQ at once, and generate " +
				"the comparative statement. This cannot be undone. Continue?"
		),
		() => {
			frappe.call({
				method: "dd_erpnext_bidding.bidding.request_for_quotation.open_bids",
				args: { request_for_quotation: frm.doc.name },
				freeze: true,
				freeze_message: __("Opening bids..."),
				callback(r) {
					if (!r.message) return;
					frappe.msgprint(__("Bids opened - {0} quotation(s) revealed.", [r.message.unsealed]));
					frm.reload_doc();
				},
			});
		}
	);
}
