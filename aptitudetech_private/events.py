# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe
import math
from frappe import _
from frappe.utils import now_datetime, time_diff_in_hours
from frappe.utils.user import get_system_managers
from frappe.utils import get_datetime



def on_task_validate(doc, handler=None):
	doc.depends_on_tasks = ""
	doc.update_depends_on()
	doc.populate_depends_on = lambda *args, **kwargs: None


def on_issue_after_insert(doc, handler=None):
    beat = frappe.new_doc("Ticket Work Beat")
    beat.update({
        'issue': doc.name,
        'user': frappe.session.user,
        'status': doc.kanban_status,
        'start_time': now_datetime()
    })
    beat.flags.ignore_permissions = True
    beat.insert()
    project = frappe.db.get_value('Project', {'customer': doc.customer, 'default_activity_type': doc.activity_type},
                                  'name')
    task = frappe.new_doc('Task')
    task.project = project
    task.issue = doc.name
    task.subject = doc.subject
    task.status = 'Open'
    task.priority = doc.priority
    task.description = doc.description
    task.flags.ignore_permissions = True
    task.save()


def on_issue_on_update(doc, handler=None):
    import html2text

    if frappe.db.count('Communication', {'reference_doctype': doc.doctype, 'reference_name': doc.name, 'sent_or_received': 'Received'}) == 1:
        email = frappe.db.exists('Communication', {'reference_doctype': doc.doctype, 'reference_name': doc.name, 'sent_or_received': 'Received'}, 'content')
        doc.db_set("description", html2text.html2text(frappe.db.get_value("Communication", email, "content")))


def on_issue_validate(doc, handler=None):
    """Handle issue kanban transitions and compute work times
    """
    now = now_datetime()
    actual_kanban_status = None
    completed = False

    if doc.kanban_status == 'Working':
        for stop in doc.on_hold_reason:
            if not stop.restart_time:
                frappe.throw(_('Please enter all restart time in the On Hold Restart table'))
    if doc.kanban_status == 'Released' and frappe.db.get_value('Issue', doc.name) != 'Released':
        doc.release_date = frappe.utils.nowdate()

    if doc.is_new():
        # Ensure ticket status is Open
        doc.status = "Open"

        # Set captured incoming time
        # doc.captured_incoming_time

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
        actual_kanban_status = frappe.db.get_value(doc.doctype, doc.name, 'kanban_status')

        # Log Ticket Work Beat
        active_work_beat = frappe.db.sql("""
            SELECT name
            FROM `tabTicket Work Beat`
            WHERE
                issue = %s
                AND status = %s
                AND ifnull(end_time, "") = ""
            ORDER BY start_time DESC
            LIMIT 1
            """, (doc.name, actual_kanban_status))
        if active_work_beat:
            frappe.db.set_value("Ticket Work Beat", active_work_beat[0][0], "end_time", now)
        else:
            beat = frappe.new_doc("Ticket Work Beat")
            beat.update({
                'issue': doc.name,
                'user': frappe.session.user,
                'status': doc.kanban_status,
                'start_time': now
            })
            beat.flags.ignore_permissions = True
            beat.insert()

    # Verify if the kanban status have changed
    if doc.kanban_status != actual_kanban_status:

        # Ensure ticket status is Open
        doc.status = "Open"

        # Verify if movement come from Stopped or Completed
        # if actual_kanban_status in ("Stopped", "Completed"):
        # 	# If there is an previous stopped time, increase it
        # 	if doc.last_stopped_time:
        # 		doc.stopped_time = (doc.stopped_time or 0.0) + time_diff_in_hours(now, doc.last_stopped_time)
        #
        # 	# Reset the last stopped time
        # 	doc.last_stopped_time = None

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
            # doc.captured_assigned_time = now

            # Handle create assignation if not exists
            do_assignation_open(doc)

        elif doc.kanban_status == "Working":
            # If there's an previous working/reported time, increse it
            # if doc.captured_start_working_time:
            # 	doc.captured_working_time = (doc.captured_working_time  or 0.0) \
            # 		+ time_diff_in_hours(now, doc.captured_start_working_time)

            # if doc.reported_work_start_time:
            # 	doc.reported_working_time = (doc.reported_working_time or 0.0) \
            # 		+ time_diff_in_hours(now, doc.reported_work_start_time)

            # Calculate the billable time
            # doc.billable_time = x_round((doc.reported_working_time or 0.01))

            # Reset working start times
            # doc.captured_start_working_time = now
            # doc.reported_work_start_time = now

            # Handle create assignation if not exists
            do_assignation_open(doc)

        elif doc.kanban_status == 'Stopped':
            # If there's an previous working/reported time, increse it
            # if doc.captured_start_working_time:
            # 	doc.captured_working_time = (doc.captured_working_time  or 0.0) \
            # 		+ time_diff_in_hours(now, doc.captured_start_working_time)

            # if doc.reported_work_start_time:
            # 	doc.reported_working_time = (doc.reported_working_time or 0.0) \
            # 		+ time_diff_in_hours(now, doc.reported_work_start_time)

            # Reset start and end times
            # doc.captured_start_working_time = None
            # doc.captured_end_working_time = None
            # doc.reported_work_end_time = None
            # doc.reported_work_end_time = None

            # Calculate the billable time
            # doc.billable_time = x_round((doc.reported_working_time or 0.01))

            # Validation, to check if the update dont came from "Working" or `None` status
            if actual_kanban_status and actual_kanban_status != "Working":
                frappe.throw(_("You cannot move to '{0}' from {1}, only '{2}' is acceptable").format(
                    _(doc.kanban_status), _(actual_kanban_status), _("Working")))

            # Start the counter on stopped time
            # doc.last_stopped_time = now

            # Update status and set on hold
            doc.status = "Hold"

            # Handle create assignation if not exists
            do_assignation_open(doc)

        elif doc.kanban_status == "Completed":
            # Verify if the times arent captured yet
            # if not doc.captured_start_working_time:
            # 	doc.captured_start_working_time = now

            # if not doc.reported_work_start_time:
            # 	doc.reported_work_start_time = now

            # Update the end times
            # doc.captured_end_working_time = now
            # doc.reported_work_end_time = now

            # Update ticket times
            # doc.captured_working_time = (doc.captured_working_time  or 0.0) \
            # 	+ time_diff_in_hours(now, doc.captured_start_working_time)
            #
            # doc.reported_working_time = (doc.reported_working_time or 0.0) \
            # 	+ time_diff_in_hours(now, doc.reported_work_start_time)

            # Calculate the billable time
            # doc.billable_time = x_round((doc.reported_working_time or 0.01))

            # Set the user who completed the work
            doc.completed_by = frappe.session.user

            # Close the ticket
            doc.status = "Closed"
            completed = True

            # Handle assignation close
            do_all_assignation_close(doc)

    # else:
    # 	# Calculate the billable time
    # 	doc.billable_time = x_round((doc.reported_working_time or 0.01))
    import uuid
    to_keep = []

    if frappe.db.exists('Task', {'issue': doc.name}):
        task = frappe.get_doc('Task', {'issue': doc.name})
        if doc.status == 'Working':
            task.status = 'Working'
            if len(doc.work_log) > 0:
                task.act_start_date = get_datetime(doc.work_log[0]['work_start_time']).date()  # date
        elif doc.status == 'Incoming':
            task.status = 'Open'
        elif doc.status == 'Completed':
            task.status = 'Completed'
            task.act_end_date = get_datetime(doc.work_log[-1]['work_end_time']).date()  # date
            task.actual_time = (get_datetime(doc.work_log[-1]['work_end_time']) - get_datetime(
                doc.work_log[-1]['work_start_time'])).seconds // 3600
        if task.priority != doc.priority:
            task.priority = doc.priority

    # else:
    #     project = frappe.db.get_value('Project', {'customer': doc.customer, 'default_activity_type': doc.activity_type},
    #                                   'name')
    #     task = frappe.new_doc('Task')
    #     task.project = project
    #     task.issue = doc.name
    #     task.subject = doc.subject
    #     task.status = 'Open'
    #     task.priority = doc.priority
    #     task.description = doc.description
    #     task.flags.ignore_permissions = True
    #     task.save()

    for wl in doc.work_log:
        if not wl.work_logs_id:
            wl.work_logs_id = str(uuid.uuid1())
        work_start_time = get_datetime(wl.work_start_time)
        work_end_time = get_datetime(wl.work_end_time)
        diff_days = work_end_time - work_start_time
        is_new_ts = False
        found = False

        if diff_days.days >= 1:
            frappe.throw(_("Please divide the Work Log per day. Problematic Work Log: {0}").format(work_start_time))
        if work_end_time < work_start_time:
            frappe.throw("Start Time can't be greater than End Time in the Work Log")
        # get timesheet for current month
#         ts_data = frappe.db.get_all('Timesheet',
#                                {'start_date': (
#                                'between', (work_start_time.replace(day=1).date(), work_start_time.date()))}, 'name')
#         if not ts_data and not is_new_ts:
#             is_new_ts = True
#             employee = frappe.db.get_value('Employee', {'user_id': frappe.session.user}, '*', as_dict=True)
#             ts = frappe.new_doc('Timesheet')
#             ts.company = 'Aptitude Technologies'
#             ts.employee = employee['name']
# ##########################
#             # ts.append('time_logs', {
#             #     'issue': doc.name,
#             #     'activity_type': doc.activity_type,
#             #     'from_time': work_start_time,
#             #     'hours': (work_end_time - work_start_time).seconds // 3600,  # have the nb of hours
#             #     'to_time': work_end_time,
#             #     'completed': completed,
#             #     'note': wl.work_description,
#             #     'project': task.project,
#             #     'task': task.name,
#             #     'billable': doc.billable,
#             #     'work_logs_id': wl.work_logs_id,
#             # })
#             # ts.flags.ignore_permissions = True
#             # ts.save()
#         else:
#             ts = frappe.get_doc('Timesheet', ts_data[0]['name'])
#             ts_detail = frappe.db.get_value('Timesheet Detail', {'parent': ts.name, 'parenttype': 'Timesheet',
#                                                                 'work_logs_id': wl.work_logs_id}, '*')
#             # update existing rows
#             if ts_detail:
#                 if work_start_time != ts_detail.start_time:
#                     ts_detail.start_time = wl.work_start_time
#                 if work_end_time != ts_detail.end_time:
#                     ts_detail.end_time = wl.work_end_time
#                 if wl.work_description != ts_detail.note:
#                     ts_detail.note = wl.work_description
#                 found = True
            # else:
        # if not found or is_new_ts:
        #     ts.append('time_logs', {
        #         'issue': doc.name,
        #         'activity_type': doc.activity_type,
        #         'from_time': work_start_time,
        #         'hours': (work_end_time - work_start_time).seconds // 3600,  # have the nb of hours
        #         'to_time': work_end_time,
        #         'completed': completed,
        #         'note': wl.work_description,
        #         'project': task.project,
        #         'task': task.name,
        #         'billable': doc.billable,
        #         'work_logs_id': wl.work_logs_id,
        #     })
                # ts.flags.ignore_permissions = True
                # ts.save()

            # Clear TimeSheet Details who are not linked to an issue anymore
    #         timesheet_detail_list = frappe.db.get_all('Timesheet Detail', {'parent': ts.name, 'parenttype': 'Timesheet'}, '*')
    #         for detail in timesheet_detail_list:
    #             if detail.work_logs_id:
    #                 for wl in doc.work_log:
    #                     if detail.work_logs_id == wl.work_logs_id:
    #                         to_keep.append(detail)
    #                         break
    #             else:
    #                 to_keep.append(detail)
    #
    #         frappe.msgprint(_("About to remove: {0} <br> desc: {1}").format(frappe.as_json(ts.time_logs), to_keep))
    # if to_keep:
    #     ts.set("time_logs", to_keep)
    # ts.flags.ignore_permissions = True
    # ts.save()
            # [ts.time_logs.remove(r) for r in to_remove]

def on_issue_trash(doc, handler=None):
    if frappe.session.user in get_system_managers(True):
        for wb in frappe.get_all('Ticket Work Beat', filters={'issue': doc.name}):
            frappe.delete_doc('Ticket Work Beat', wb.name)


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


def do_all_assignation_close(doc):
    """Close all existing todos related to that doc
    """
    for todo in frappe.get_all('ToDo', filters={
        'reference_type': doc.doctype,
        'reference_name': doc.name,
        'status': 'Open'}):
        frappe.db.set_value('ToDo', todo, 'status', 'Closed')


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


def on_project_onload(doc, handler=None):
    """Order task by task_order
    """

    fields = ["title", "status", "start_date", "end_date", "description", "task_weight", "task_id"]
    exclude_fieldtype = ["Button", "Column Break",
                         "Section Break", "Table", "Read Only", "Attach", "Attach Image", "Color", "Geolocation",
                         "HTML", "Image"]

    custom_fields = frappe.get_all("Custom Field", {"dt": "Project Task",
                                                    "fieldtype": ("not in", exclude_fieldtype)}, "fieldname")

    for d in custom_fields:
        fields.append(d.fieldname)

    if doc.get('name'):
        doc.tasks = []
        i = 1
        for task in frappe.get_all('Task', '*', {'project': doc.name}, order_by='`task_order` asc'):
            task_map = {
                "title": task.subject,
                "status": task.status,
                "start_date": task.exp_start_date,
                "end_date": task.exp_end_date,
                "task_id": task.name,
                "description": task.descrition,
                "task_weight": task.task_weight,
                "idx": task.task_order or i
            }
            i += 1
            doc.map_custom_fields(task, task_map, custom_fields)

            doc.append("tasks", task_map)

# def on_project_validate(doc, handler=None):
#     for i, task in enumerate(doc.tasks, 1):
#         task.task_order = i
