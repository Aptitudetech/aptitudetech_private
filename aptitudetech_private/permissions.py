#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe


def get_issue_permissions_query_conditions(user):
        if not user:
                user = frappe.session.user

	issue = frappe.db.exists("Issue", {"creator": user, "_assign": user})
        if issue:
        	return '''(`tabIssue`.name = "{issue}")'''.format(issue=frappe.db.escape(issue))

def has_permission_to_issue(doc, user):
	issue = frappe.db.exists("Issue", { "creator": user, "_assign": user }) #won't work...
        if issue:
        	return doc.name == issue
