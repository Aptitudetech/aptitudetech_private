#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
import math
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours

def on_issue_validate(doc, handler=None):
	"""Handle issue kanban transitions and compute work times
	"""
	now = now_datetime()
	actual_kanban_status = None

	if doc.is_new():
		# Ensure ticket status is Open
		doc.status = "Open"

		# Set captured incoming time
		doc.captured_incoming_time

		if doc.raised_by and (not doc.customer or not doc.contact):
			# Extract domain from email and fetch customer and contact
			domain = doc.raised_by.split('@')[-1] 
			customer = frappe.db.exists('Customer', {'website': ['like', '%{}'.format(domain)]})
			contact = frappe.db.exists('Contact', {'email_id': doc.raised_by})
			
			# Associate customer if match
			if customer and not doc.customer:
				doc.customer = customer
			
			# Associate contact if match
			if contact and not doc.contact:
				doc.contact = contact
	else:
		# Pull actual kanban status from database
		actual_kanban_status = doc.db_get('kanban_status')

	# Verify if the kanban status have changed
	if doc.kanban_status != actual_kanban_status:
		# Ensure ticket status is Open
		doc.status = "Open"

		# Verify if movement come from Stopped or Completed
		if actual_kanban_status in ("Stopped", "Completed"):
			# If there is an previous stopped time, increase it
			if doc.last_stopped_time:
				doc.stopped_time = (doc.stopped_time or 0.0) + time_diff_in_hours(now, doc.last_stopped_time)

			# Reset the last stopped time
			doc.last_stopped_time = None

		if actual_kanban_status and doc.kanban_status == "Incoming":
			# Only throws a validation
			frappe.msgprint(_("You can't move one ticket back to 'Incoming' state."))

		elif doc.kanban_status == 'To Be Assigned':
			# Handle assignation close if exists
			do_assignation_close(doc)
		
		elif doc.kanban_status == "Assigned":
			# Move issue status to replied
			doc.status = "Replied"

			# Set captured assignation time
			doc.captured_assigned_time = now

			# Handle create assignation
			do_assignation_open(doc)

		elif doc.kanban_status == "Working":
			# If there's an previous working/reported time, increse it
			if doc.captured_start_working_time: doc.captured_working_time = (doc.captured_working_time  or 0.0) + time_diff_in_hours(now, doc.captured_start_working_time)
			if doc.reported_working_time: doc.reported_working_time = (doc.reported_working_time or 0.0) + time_diff_in_hours(now, doc.reported_work_start_time)

			# Reset working start times
			doc.captured_start_working_time = now
			doc.reported_work_start_time = now
		
		elif doc.kanban_status == 'Stopped':
			# Validation, to check if the update dont came from "Working" or `None` status
			if actual_kanban_status and actual_kanban_status != "Working":
				frappe.throw(_("You cannot move to '{0}' from {1}, only '{2}' is acceptable").format(
					_(doc.kanban_status), _(actual_kanban_status), _("Working") 
				))

			# Start the counter on stopped time
			doc.last_stopped_time = now

			# Update status and set on hold
			doc.status = "Hold"
		
		elif doc.kanban_status == "Completed":
			# Verify if the times arent captured yet
			if not doc.captured_start_working_time: doc.captured_start_working_time = now
			if not doc.reported_work_start_time: doc.reported_work_start_time = now
			
			# Update the end times
			doc.captured_end_working_time = now
			doc.reported_work_end_time = now

			# Update ticket times
			doc.captured_working_time = (doc.captured_working_time  or 0.0) + time_diff_in_hours(now, doc.captured_start_working_time)
			doc.catured_reported_working_time = (doc.reported_working_time or 0.0) + time_diff_in_hours(now, doc.reported_work_start_time)

			# Calculate the billable time
			doc.billable_time = x_round((doc.reported_working_time or 0.01))

			# Set the user who completed the work
			doc.completed_by = frappe.session.user

			# Close the ticket
			doc.status = "Closed"
		
			# Handle assignation close
			do_assignation_close(doc)



def do_assignation_open(doc):
	"""Create an self assignated ToDo
	"""

	if not has_self_assignation(doc):
		todo = frappe.new_doc('ToDo').update({
			'reference_type': doc.doctype,
			'reference_name': doc.name,
			'assigned_by': frappe.session.user,
			'owner': frappe.session.user,
			'status': 'Open',
			'priority': 'Medium',
			'description': _('Ticket {0} has been assigned to you').format(doc.name)
		})
		todo.flags.ignore_permissions = True
		todo.save()


def do_assignation_close(doc):
	"""Close one existing todo
	"""

	todo = has_self_assignation(doc)
	if todo:
		frappe.db.set_value('ToDo', todo, 'status', 'Close')


def has_self_assignation(doc, status='Open'):
	"""Get an existing todo, or return None otherwise
	"""

	return frappe.db.exists('ToDo', {
		'reference_type': doc.doctype,
		'reference_name': doc.name,
		'assigned_by': frappe.session.user,
		'owner': frappe.session.user,
		'status': status
	})

def x_round(x):
	"""Round up time in 15 minutes
	"""
	return math.ceil(x * 4) / 4