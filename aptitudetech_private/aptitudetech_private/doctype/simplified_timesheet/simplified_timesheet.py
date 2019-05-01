# -*- coding: utf-8 -*-
# Copyright (c) 2019, Aptitudetech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

class SimplifiedTimesheet(Document):
	def validate(self):
		self.update_totals()

	def update_totals(self):
		self.clear_totals()
		self.update_time_totals()
		self.update_expenses_totals()


	def get_employee(self):
		employee_name = frappe.db.exists('Employee', {'user_id': self.user})
		if not employee_name:
			frappe.throw(_('No Employee found with user ID {0}').format(self.user))
		else:
			self.employee = employee_name

	def get_details(self):
		if not self.user:
			frappe.throw(_('Select one user before get details'))

		rows = frappe.get_all('Issue', filters={
			'billable': 1,
			'billable_time': ['>', 0.0],
			'per_billed': ['<', 100],
			'completed_by': self.user
		}, order_by='captured_incoming_time')

		self.details = []

		self.clean_totals()
		for row in rows:
			d = self.append('details', {
				'issue': row.name,
				'services': '\n'.join([
					l.link_name
					for l in frappe.get_all('Dynamic Link', fields='*', filters={
						'parent': row.name,
						'parentfield': 'other_links'
					})
				])
			})
			d.get_invalid_links()
		self.update_time_totals()
		self.update_expense_totals()

	def clean_totals(self):
		self.update({
			'total_captured_working_time': 0.0,
			'total_captured_billed_time': 0.0,
			'total_reported_working_time': 0.0,
			'total_reported_billable_time': 0.0,
			'total_approved_working_time': 0.0,
			'total_approved_billable_time': 0.0,
			'total_billable_working_time': 0.0,
			'total_expenses_amount': 0.0,
			'total_taxes_included_in_expenses': 0.0,
			'total_expenses_billable_amount': 0.0,
			'total_claimed_amount': 0.0,
			'total_sanctioned_amount': 0.0
		})

	def update_time_totals(self):
		for d in self.details:
			self.set_total_captured_working_time(flt(d.captured_working_time), d.billable)
			self.set_total_reported_working_time(flt(d.reported_working_time), d.billable)
			self.set_total_approved_working_time(flt(d.approved_working_time))
			self.set_total_approved_billable_time(flt(d.approved_working_time))
			self._set_times('total_stopped_time', None, flt(d.stopped_time), False)

	def update_expense_totals(self):
		for d in self.get('expenses'):
			self._set_expenses('total_expenses_amount', flt(d.expense_amount))
			self._set_expenses('total_taxes_included_in_expenses', flt(d.taxes_amount))
			self._set_expenses('total_claimed_amount', flt(d.claimed_amount))
			self._set_expenses('total_sanctioned_amount', flt(d.sanctioned_amount))
			
			if d.billable:
				self._set_expenses('total_expenses_billable_amount', flt(d.expense_amount))

	def _set_times(self, time_field, bill_field, amount, billable):
		if time_field:
			self.set(time_field, (self.get(time_field) or 0.0) + amount)
		if billable and bill_field:
			self.set(bill_field, (self.get(bill_field) or 0.0) + amount)

	def _set_expenses(self, amount_field, amount):
		if amount_field:
			self.set(amount_field, (self.get(amount_field) or 0.0) + amount)

	def set_total_captured_working_time(self, amount, billable):
		self._set_times('total_captured_working_time', 'total_captured_billable_time', amount, billable)

	def set_total_reported_working_time(self, amount, billable):
		self._set_times('total_reported_working_time', 'total_reported_billable_time', amount, billable)

	def set_total_approved_working_time(self, amount):
		self._set_times('total_approved_working_time', None, amount, False)

	def set_total_approved_billable_time(self, amount):
		self._set_times(None, 'total_approved_billable_time',amount, True)

	def create_metered_features(self):
		times, expenses = {}, {}

		for d in self.get('details', {'billable': 1}):
			if d.metered_featur not in times:
				times.set_default(d.metered_feature, {})
			if d.service not in times[d.metered_feature]:
				times[d.metered_feature].set_default(d.service, 0.0)
			times[d.metered_feature][d.service] += d.approved_working_time

		for d in self.get('expenses', {'billable': 1}):
			if d.metered_feature not in expenses:
				expenses.set_default(d.metered_feature, {})
			if d.service not in expenses[d.metered_feature]:
				expenses[d.metered_feature].set_default(d.service, 0.0)
			expenses[d.metered_feature][d.service] += d.expense_amount

		for mf, group in times.items():
			for service, amount in group.items():
				doc = self._get_new_mflog_doc(
					mf, service, 'consumed_units', amount)
				doc.insert()

		for mf, group in expenses.items():
			for service, amount in group.items():
				doc = self.get_new_mflog_doc(
					mf, service, 'cost_per_unit', amount)
				doc.insert()

	def create_tax_recover_jv(self):
		doc = frappe.new_doc('Journal Entry').update({
			'naming_series': 'JV-',
			'posting_date': today(),
			'company': self.company,
		})

		accounts = {}
		purchase_taxes = {}
		taxes_sum = 0.0
		for d in self.expenses:
			if d.tax_and_charges_template not in purchase_taxes:
				purchase_taxes[d.tax_and_charges_template] = frappe.get_all(
					'Purchase Taxes and Charges',
					fields='*',
					filters={"parent": d.tax_and_charges_templates})
			taxes_rates = sum([t.rate for t in purchase_taxes[d.tax_and_charges_template]])
			for account in purchase_taxes[d.tax_and_charges_template]:
				if not taxes_rates:
					continue
				account_rate = ((account.rate / taxes_rates)) * d.claim_amount
				doc.append('accounts', {
					'account': d.account,
					'debit_in_account_currency': flt(account_rate, 2)
				})
				taxes_sum += flt(account_rate, 2)

		doc.append('accounts', {
			'account': frappe.db.get_value('Company', self.company, 'default_expense_claim_recoverable_taxes_account'),
			'credit_in_account_currency': taxes_sum
		})
		doc.flags.ignore_permissions = True
		doc.run_method('validate')
		doc.run_method('save')
		doc.run_method('submit')

	def create_expense_claim(self):
		doc = frappe.new_doc('Expense Claim').update({
			'employee': self.employee,
			'approval_status': 'Draft',
			'posting_date': today(),
			'company': self.company,
		})
		for expense in self.expenses:
			doc.append('expense', {
				'expense_date': expense.expense_date,
				'expense_type': expense.expense_type,
				'claim_amount': expense.claim_amount,
				'sanctioned_amount': expense.sanctioned_amount
			})

		doc.flags.ignore_permissions = True
		doc.run_method('validate')
		doc.run_method('save')
		doc.run_method('submit')

	def _get_new_mflog_doc(self, mf, service , amount_field, amount, unit='Hours'):
		other_field = 'consumed_units' if amount_field == 'cost_per_unit' else 'cost_per_unit'
		other_value = 1 if amount_field == 'cost_per_unit' else 0.0
		return frappe.new_doc('Metered Feature Units Log').update({
			'metered_feature': mf,
			'service': service,
			'customer': frappe.db.get_value('Service', service, 'customer'),
			amount_field: amount,
			other_field: other_value,
			'item_group': 'Timesheet',
			'item_type': self.employee_name,
			'item_code': self.name,
			'unit': unit
		})
