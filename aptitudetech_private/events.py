#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
import math
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours

def x_round(x):
    return math.ceil(x * 4) / 4

def on_issue_validate(doc, handler=None):
	#ie new ticket
	now = now_datetime()
	doc.status = "Open"
	if doc.raised_by:
		if not doc.customer:
			domain = doc.raised_by.split('@')[-1]
			customer = frappe.db.exists('Customer', {'website': ['like', '%' + domain]})
			if customer:
				doc.customer = customer
		if not doc.contact:
			contact = frappe.db.exists('Contact', {'email_id': doc.raised_by})
			if contact:
				doc.contact = contact

	if doc.is_new():
		doc.captured_incoming_time = now

	actual_kbn_status = None
	if not doc.is_new():
		actual_kbn_status = frappe.db.get_value('Issue', doc.name, 'kanban_status')

	if doc.kanban_status != "Stopped" and actual_kbn_status == "Stopped":
		doc.stopped_time = (doc.stopped_time or 0.0) + time_diff_in_hours(now_datetime(), doc.last_stopped_time)
		doc.last_stopped_time = now
	if actual_kbn_status == "Completed":
		doc.stopped_time = (doc.stopped_time or 0.0) + time_diff_in_hours(now_datetime(), doc.captured_end_working_time)
	if actual_kbn_status == "Working" and doc.kanban_status != "Working":
		doc.captured_working_time = (doc.captured_working_time or 0.0) + time_diff_in_hours(now_datetime(), doc.captured_start_working_time)
		doc.reported_working_time = (doc.reported_working_time or 0.0) + time_diff_in_hours(now_datetime(), doc.reported_work_start_time)

	if doc.kanban_status in ("To Be Assigned", "Completed") and actual_kbn_status != doc.kanban_status:
		has_todo = frappe.db.exists('ToDo', {
			'reference_type': 'Issue',
			'reference_name': doc.name,
			'assigned_by': frappe.session.user,
			'owner': frappe.session.user,
			'status': 'Open'})
		if has_todo:
			frappe.db.set_value('ToDo', has_todo, 'status', 'Closed')
			

	if not doc.is_new() and doc.kanban_status == "Incoming" and actual_kbn_status != "Incoming":
		frappe.throw(_("You cannot move back to 'Incoming' from '{0}'").format(actual_kbn_status))

	if doc.kanban_status in ("Assigned", "Working"):
		doc.status = "Replied"
		doc.captured_assigned_time = doc.modified
		if not frappe.db.exists('ToDo', {
			'reference_type': 'Issue',
			'reference_name': doc.name,
			'assigned_by': frappe.session.user,
			'owner': frappe.session.user,
			'status': 'Open' }):
			todo = frappe.new_doc('ToDo')
			todo.update({
				'owner': frappe.session.user,
				'reference_type' : 'Issue',
				'reference_name' : doc.name,
				'assigned_by': frappe.session.user,
				'description': 'ToDo' 
			})		
			todo.flags.ignore_permissions = True
			todo.save()

	if doc.kanban_status == "Working":
		doc.captured_start_working_time = now
		doc.reported_work_start_time = doc.captured_start_working_time

	if doc.kanban_status == "Completed" and actual_kbn_status != "Completed":
		if not doc.captured_start_working_time:
			doc.captured_start_working_time = now
		if not doc.reported_work_start_time:
			doc.reported_work_start_time = now
		doc.status = "Closed"
                doc.captured_end_working_time = now
		doc.reported_work_end_time = now
		doc.captured_working_time = (doc.captured_working_time or 0.0) + time_diff_in_hours(now, doc.captured_start_working_time)
		doc.reported_working_time = (doc.reported_working_time or 0.0) + time_diff_in_hours(now, doc.reported_work_start_time)
		doc.completed_by = frappe.session.user

	if doc.kanban_status == "Stopped" and actual_kbn_status != "Stopped":
		if actual_kbn_status and actual_kbn_status != "Working":
			frappe.throw(_("You cannot move to 'Stopped' from '{0}', only 'Working' is acceptable").format(actual_kbn_status))
		doc.last_stopped_time = now
		doc.status = "Hold"

	doc.billable_time = x_round((doc.reported_working_time or 0.0))
