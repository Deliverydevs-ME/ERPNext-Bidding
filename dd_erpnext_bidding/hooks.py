app_name = "dd_erpnext_bidding"
app_title = "DD ERPNext Bidding"
app_publisher = "Delivery Devs"
app_description = "Sealed vendor bidding workflow for Request for Quotation"
app_email = "erp@deliverydevs.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext", "falcon"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "dd_erpnext_bidding",
# 		"logo": "/assets/dd_erpnext_bidding/logo.png",
# 		"title": "DD ERPNext Bidding",
# 		"route": "/dd_erpnext_bidding",
# 		"has_permission": "dd_erpnext_bidding.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dd_erpnext_bidding/css/dd_erpnext_bidding.css"
# app_include_js = "/assets/dd_erpnext_bidding/js/dd_erpnext_bidding.js"

# include js, css files in header of web template
# web_include_css = "/assets/dd_erpnext_bidding/css/dd_erpnext_bidding.css"
# web_include_js = "/assets/dd_erpnext_bidding/js/dd_erpnext_bidding.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dd_erpnext_bidding/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Request for Quotation": "public/js/request_for_quotation.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "dd_erpnext_bidding/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Editable supplier-quotation entry form (rate, lead time, attachment) for
# a logged-in supplier - the generic Supplier Quotation web view is
# read-only and has no field for either, so this replaces it as the
# destination suppliers are actually sent to.
website_route_rules = [
	{"from_route": "/submit-quotation/<path:sqname>", "to_route": "submit_quotation"},
]


# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "dd_erpnext_bidding.utils.jinja_methods",
# 	"filters": "dd_erpnext_bidding.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "dd_erpnext_bidding.install.after_install"
after_migrate = "dd_erpnext_bidding.install.create_fields"

# Uninstallation
# ------------

# before_uninstall = "dd_erpnext_bidding.uninstall.before_uninstall"
# after_uninstall = "dd_erpnext_bidding.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "dd_erpnext_bidding.utils.before_app_install"
# after_app_install = "dd_erpnext_bidding.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "dd_erpnext_bidding.utils.before_app_uninstall"
# after_app_uninstall = "dd_erpnext_bidding.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dd_erpnext_bidding.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# Blocks read/download of any attachment on a sealed Supplier Quotation for
# everyone (except Administrator, who bypasses all permission hooks by
# design) until that RFQ's bidding window opens - keeps PDF/Excel
# attachments just as confidential as the rates until then.
has_permission = {
	"File": "dd_erpnext_bidding.bidding.supplier_quotation.has_file_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Request for Quotation": "dd_erpnext_bidding.bidding.overrides.RequestforQuotationBidding",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Request for Quotation": {
		"validate": "dd_erpnext_bidding.bidding.request_for_quotation.validate",
		"on_submit": "dd_erpnext_bidding.bidding.request_for_quotation.on_submit",
	},
	"Supplier Quotation": {
		"validate": "dd_erpnext_bidding.bidding.supplier_quotation.validate",
		"on_submit": "dd_erpnext_bidding.bidding.supplier_quotation.on_submit",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"*/5 * * * *": [
			"dd_erpnext_bidding.bidding.request_for_quotation.auto_open_bids",
		],
	},
}

# Testing
# -------

# before_tests = "dd_erpnext_bidding.install.before_tests"

# Overriding Methods
# ------------------------------
#
# "Create > Request for Quotation" from a Material Request whose Request
# Type is flagged "Triggers Vendor Bidding" opens the new RFQ with Enable
# Vendor Bidding already checked.
override_whitelisted_methods = {
	"erpnext.stock.doctype.material_request.material_request.make_request_for_quotation": (
		"dd_erpnext_bidding.bidding.request_for_quotation.make_request_for_quotation"
	),
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dd_erpnext_bidding.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["dd_erpnext_bidding.utils.before_request"]
# after_request = ["dd_erpnext_bidding.utils.after_request"]

# Job Events
# ----------
# before_job = ["dd_erpnext_bidding.utils.before_job"]
# after_job = ["dd_erpnext_bidding.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"dd_erpnext_bidding.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

