// Copyright (c) 2016, Aptitudetech and contributors
// For license information, please see license.txt

frappe.query_reports["Project Timesheet Summary for Email"] = {
	"filters": [
		{
                        "fieldname":"customer",
                        "label": __("Customer"),
                        "fieldtype": "Link",
                        "options": "Customer",
                        "default": ""
                },
	]
}
