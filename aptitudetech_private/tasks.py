
#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import frappe


def daily():
	from frappe.email.doctype.email_template.email_template import get_email_template
	issues = frappe.db.get_all('Issue', {'kanban_status' : ('!=', 'Completed')}, ['name', '_assign'])
	users = frappe.db.get_all('User', None)
	for user in users:
		uncomplete_issues = []
             	for issue in issues:
                	if issue['_assign'] != None and user['name'] in issue['_assign']:
                     		uncomplete_issues.append(issue['name'])
		user_language = frappe.db.get_value('User', {'email':user['name']}, 'language')
		email_template_name = frappe.db.get_value('Email Template', 'Pending Issues - {0}'.format(user_language).upper(), 'name')
		if not email_template_name:
			email_template_name = 'Pending Issues - EN'
	        recipient = user['name']
		print(recipient)
		print(uncomplete_issues)
#		frappe.sendmail(
 #               	recipients = [recipient],
#	        	**get_email_template(email_template_name, 'doc': None)
 #               ) 

		
