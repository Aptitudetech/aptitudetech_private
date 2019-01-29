#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
from frappe import _

def on_issue_validate(doc, handler=None):
	#ie new ticket
	if doc.creation == doc.modified:
		doc.captured_incoming_time = doc.creation

	if doc.kanban_status == "Assigned" and frappe.db.get_value('Issue', doc.name, 'kanban_status') == "To Be Assigned":
		doc.captured_assigned_time = doc.modified

	if doc.kanban_status == "Working" and frappe.db.get_value('Issue', doc.name, 'kanban_status') == "Assigned":
                doc.captured_start_working_time = doc.modified
		doc.reported_work_start_time = doc.captured_start_working_time

	if doc.kanban_status == "Completed" and frappe.db.get_value('Issue', doc.name, 'kanban_status') == "Working":
                doc.captured_end_working_time = doc.modified
		doc.reported_work_end_time = doc.captured_end_working_time



