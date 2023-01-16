# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
        if not filters:
                filters = {}
        elif filters.get("from_date") or filters.get("to_date"):
                filters["from_time"] = "00:00:00"
                filters["to_time"] = "24:00:00"

        columns = [_("Timesheet") + ":Link/Timesheet:120", _("From") + "::140",
                _("To") + "::140", _("Hours") + "::70", _("Employee") + "::120", _("Task") + ":Link/Task:150",
                _("Project") + ":Link/Project:120", _("Note") + "::220"]

        conditions = "ts.docstatus = 1"
        if filters.get("customer"):
                conditions += " and p.customer = %(customer)s"
        if filters.get("from_date"):
                conditions += " and tsd.from_time >= timestamp(%(from_date)s, %(from_time)s)"
        if filters.get("to_date"):
                conditions += " and tsd.to_time <= timestamp(%(to_date)s, %(to_time)s)"

        data = get_data(conditions, filters)
	previous_project = ""
	total_hours = grand_total_hours = count = 0.00
	nb_row = len(data)
	nb_row_int = len(data)
	x = 0
	total_employee  = {
        	"Mark" : 13.01
        }
        total_employee.clear()
	
	

	while x < nb_row:
		if previous_project <> "" and previous_project <> data[x][6]:
			previous_project = data[x][6]
			data.insert(int(x), ["", "", "", "Total Hours", total_hours, "", "", "", ""])
			for key,val in total_employee.items():
                                data.insert(int(x), ["", "", "", key, val, "", "", "", ""])
				nb_row += 1
				x += 1
			nb_row += 1
			total_hours = 0.00
			total_employee.clear()
		else:		
			total_hours = float(data[x][3]) + float(total_hours)
			grand_total_hours = float(data[x][3]) + float(grand_total_hours)
			previous_project = data[x][6]
			if data[x][4] in total_employee:
                        	total_employee[data[x][4]] += float(data[x][3])
                        else:
                                total_employee[data[x][4]] = float(data[x][3])
		x += 1
	data.insert(int(x),["", "", "", "Total Hours", total_hours, "", "", "", ""])
	for key,val in total_employee.items():
                data.insert(int(x), ["", "", "", key, val, "", "", "", ""])
                nb_row += 1
                x += 1

        return columns, data

def get_data(conditions, filters):
        time_sheet = frappe.db.sql(""" SELECT ts.name, tsd.from_time, tsd.to_time, tsd.hours,
                ts.employee_name, tsk.subject, tsd.project, tsd.note
                FROM `tabTimesheet` ts
                LEFT JOIN `tabTimesheet Detail` tsd ON  ts.name = tsd.parent
                LEFT JOIN `tabProject` p ON p.name = tsd.project
                LEFT JOIN `tabTask` tsk on tsk.name = tsd.task
                WHERE 1=1 AND %s order by tsd.project, ts.employee_name, from_time """%(conditions), filters, as_list=1)

        return time_sheet

