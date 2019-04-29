#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe


def get_issue_permissions_query_conditions(user):
        if not user:
                user = frappe.session.user

	if set(['Aptitude - Helpdesk Manager', 'Aptitude - Helpdesk Administrator']).intersection(set(frappe.get_roles(user))):
		return

	return '((`tabIssue`.kanban_status IN ("Incoming", "To Be Assigned", "Completed")) or locate("{0}", `tabIssue`._assign) > 0)'.format(user)


def has_permission_to_issue(doc, user):
	issue = frappe.db.exists("Issue", { "creator": user, "_assign": user }) #won't work...
        if issue:
        	return doc.name == issue
