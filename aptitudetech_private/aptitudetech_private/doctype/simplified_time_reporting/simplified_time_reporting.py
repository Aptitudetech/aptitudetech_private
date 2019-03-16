
# -*- coding: utf-8 -*-
# Copyright (c) 2019, Aptitudetech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class SimplifiedTimeReporting(Document):


	def onload_post_render(self):
		import json
		#https://stackoverflow.com/a/610923/8291000
		issues = self.load_closed_issues()
		remaining_issues = []
		try:
			if self.timesheet_detail:
				td_issues=[td.issue for td in self.get('timesheet_detail')]	
				for issue in issues: #Load newest issues - not in the timesheet table yet
					if issue['name'] not in td_issues:
						remaining_issues.append(issue)
				self.add_timesheet_rows(remaining_issues)

		except AttributeError:
			self.employee = frappe.db.get_value("Employee", {"user_id" : frappe.session.user}, "name")
			self.add_timesheet_rows(issues)

	def add_timesheet_rows(self, issues = []):
		import datetime
		from datetime import datetime
		if issues:
			for issue in issues:
				end_time_obj = datetime.strptime(issue['reported_work_end_time'].split('.')[0], '%Y-%m-%d %H:%M:%S')
				start_time_obj = datetime.strptime(issue['reported_work_start_time'].split('.')[0], '%Y-%m-%d %H:%M:%S')
				diff_time = self.get_diff_time(start_time_obj, end_time_obj)
				detail = {
					'issue': issue['name'],
					'from_time': issue['reported_work_start_time'], 
					'to_time': issue['reported_work_end_time'], 
					'note' : issue['description'],
					'project' : issue['project'] if issue['project'] else None,
					'hours' : diff_time
				}
				self.append("timesheet_detail", detail)

	def before_save(self):
		import json, datetime
		from frappe.utils import now_datetime
		from datetime import datetime

		_now = now_datetime()
		self.posting_date = datetime.strptime(str(_now).split('.')[:-1][0], '%Y-%m-%d %H:%M:%S')

		self.total_reported_time = self.get_total_reported_time()
                self.total_captured_time = self.get_total_captured_time()

	def on_submit(self):
		import json
		import datetime
		from frappe.utils import now_datetime

		if self.workflow_state == 'Approved' or self.workflow_state == 'To Approve':
			_now = now_datetime()
			expenses_list = []
			if self.expenses:
				data = json.loads(str(frappe.as_json(self.expenses))) #need to be as_json, otherwhise the json won't load because of the datetime attribute
				for expense in data:
					try:
						description = expense["description"]
					except:
						description = ""
					exp = {
						'expense_date' : expense['date'],
						'expense_type' : expense['reason'],
						'description' : description,
						'claim_amount' : expense['claim_amount'],
						'sanctioned_amount' : expense['claim_amount']
					}
					expenses_list.append(exp)

				frappe.new_doc('Expense Claim').update({ 
		                	"employee": self.employee,
					"approval_status" : "Draft",
					"posting_date" : datetime.datetime.now().date(),
					"expenses" : expenses_list,
					"company" : "Aptitude Technologies"
				}).save()					

	def get_total_reported_time(self):
		import json
		total_reported_time = 0
		issues = json.loads(str(frappe.as_json(self.timesheet_detail)))

		for issue in issues:
			total_reported_time = total_reported_time + issue['hours']
		return total_reported_time


	def get_total_captured_time(self):
		import datetime
		from datetime import datetime
		total_captured_time = 0
		issues = self.load_closed_issues()		
		
		for issue in issues:
			end_time_obj = datetime.strptime(issue['captured_end_working_time'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                        start_time_obj = datetime.strptime(issue['captured_start_working_time'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                        diff_time = self.get_diff_time(start_time_obj, end_time_obj)

#			diff_time = self.get_diff_time(issue['captured_start_working_time'], issue['captured_end_working_time'])
			total_captured_time = total_captured_time + diff_time
		return total_captured_time


	def get_diff_time(self, start_time, end_time):
		import datetime
		return round(self.round_number_quarter((end_time - start_time).total_seconds()/3600), 2)

	def round_number_quarter(self, number):
		import math
		return math.ceil(number*4)/4




	def load_closed_issues(self):
		import datetime, json

		cur_month = datetime.datetime.now().strftime("%m")
		cur_year = datetime.datetime.now().strftime("%Y")
		next_month = int(cur_month) + 1
		next_year = cur_year
		if next_month == 13:
			next_month = 1
			next_year = int(next_year) + 1
		start_date = "{0}-{1}-01".format(cur_year, cur_month) 
		end_date = "{0}-{1}-01".format(next_year, next_month)
		closed_issues = frappe.db.get_all("Issue", {"kanban_status" : "Completed", "reported_work_start_time" : [ ">=", start_date ], "reported_work_end_time" : [ "<=", end_date ]},['_assign, name, reported_work_start_time, reported_work_end_time, description, captured_start_working_time, captured_end_working_time'])

		self_issues = []

		for issue in closed_issues:
			
			if issue['_assign'] and frappe.session.user in issue['_assign']:
				issue.project = frappe.db.get_value('Task', {'issue' : issue['name']}, 'project')
				self_issues.append(issue)

		return json.loads(str(frappe.as_json(self_issues)))
				
