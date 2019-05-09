#-*- coding: utf-8 -*-

import frappe
import boto3
import boto3.session
import rows
import json
import zipfile
import tempfile
import sqlite3
from io import BytesIO
from frappe import _
from frappe.utils import cint, flt, today, getdate, get_first_day, add_to_date
try:
	from frappe.utils import file_manager
	with_file_manager = True
except ImportError:
	with_file_manager = False
from frappe.core.doctype.file.file import create_new_folder

SQLVIEW = """
select lineitemusageaccountid as account,
       lineitemproductcode as item_group,
       productproductfamily as item_code,
       productinstancetype as item_type,
       pricingterm as item_term,
       pricingunit as item_unit,
       strftime('%Y-%m-%d', min(billbillingperiodstartdate)) as start_date,
       strftime('%Y-%m-%d', max(billbillingperiodenddate)) as end_date,
       sum(lineitemusageamount) as consumed_units,
       sum(ifnull(lineitemunblendedcost, 0.0)) / sum(ifnull(lineitemusageamount, 1.0)) as cost_per_unit
from billing_aptech
where lineitemlineitemtype != "Tax"
group by lineitemusageaccountid, lineitemproductcode, productproductfamily, productinstancetype, pricingterm, pricingunit
order by lineitemusageaccountid, lineitemproductcode, productproductfamily, productinstancetype, pricingterm, pricingunit
"""

import_fields = u"""
lineItem/UsageAccountId
lineItem/LineItemType
lineItem/ProductCode
product/productFamily
product/instanceType
pricing/term
pricing/unit
bill/BillingPeriodStartDate
bill/BillingPeriodEndDate
lineItem/UsageAmount
lineItem/UnblendedCost
lineItem/UnblendedRate
""".strip().splitlines()

def download_aws():
	settings = frappe.get_doc('Monthly Recurring Setup', 'Monthly Recurring Setup')

	_today = getdate(add_to_date(today(), months=-1))
	if _today.day != cint(settings.processing_day):
		return

	session = boto3.session.Session(region_name=settings.region_name)
	s3client = session.client('s3', config=boto3.session.Config(signature_version='s3v4'))
	first_day = get_first_day(_today, 0, 0)
	next_month = get_first_day(_today, 0, 1)

	manifest = None
	with tempfile.NamedTemporaryFile() as temp:
		s3client.download_file(
			settings.s3_bucket,
			'{}/{}/{}-{}/{}-Manifest.json'.format(
				settings.report_name,
				settings.csv_file_prefix,
				str(first_day).replace('-', ''),
				str(next_month).replace('-', ''),
				settings.csv_file_prefix),
			temp.name)

		with open(temp.name, 'rb') as f:
			manifest = json.load(f)
	
	if not manifest:
		return

	data = None
	with tempfile.NamedTemporaryFile() as temp:
		s3client.download_file(
			settings.s3_bucket,
			manifest['reportKeys'][0],
			temp.name)

		with zipfile.ZipFile(temp.name) as zf:
			for fl in zf.filelist:
				data = rows.import_from_csv(BytesIO(zf.read(fl.filename)), 
					dialect='excel', 
					import_fields=import_fields)

	if not data:
		return

	tabulated = False
	with tempfile.NamedTemporaryFile() as temp:
		conn = rows.export_to_sqlite(data, temp.name, 'billing_aptech')
		tabulated = rows.import_from_sqlite(conn, query=SQLVIEW)
	
	if not tabulated:
		return

	if not frappe.db.exists('File', 'Home/' + settings.csv_storage_folder):
		create_new_folder(settings.csv_storage_folder, 'Home')

	if not frappe.db.exists('File', 'Home/' + settings.csv_storage_folder + '/' + str(_today.year)):
		create_new_folder(str(_today.year), 'Home/' + settings.csv_storage_folder)

	
	content = BytesIO()
	
	rows.export_to_csv(tabulated, content)
	content.seek(0)
	fname = ' '.join([_today.strftime('%m'), _today.strftime('%B')]) + '.csv'
	folder = '/'.join(['Home', settings.csv_storage_folder, _today.strftime('%Y')])
	full_fname = folder + '/' + fname
	if full_fname:
		frappe.delete_doc('File', full_fname)
	if with_file_manager:
		file_manager.save_file(fname, content.read(), None, None, folder, is_private=1)
	else:
		frappe.new_doc('File').update({
			'file_name': fname,
			'content': content.read(),
			'folder': folder,
			'is_private': 1
		}).save()

	instructions = frappe.get_all('Service Instruction', fields=['*'], filters={'type': 'Amazon Web Services', 'group': 'AWS - Account Info'})

	keys = {}

	for instruction in instructions:
		if not instruction.instruction:
			continue
		instruction_data = json.loads(instruction.instruction, object_pairs_hook=frappe._dict)
		keys[int(instruction_data.aws_account_id)] = [instruction.parent, frappe.db.get_value('Service', instruction.parent, 'service_plan')]

	for row in tabulated:
		if row.account in keys:
			mful_data = {
				'service': keys[row.account][0],
				'customer': frappe.db.get_value('Service', keys[row.account][0], 'customer'),
				'metered_feature': 'MF-000011',
				'start_date': row.start_date,
				'end_date': add_to_date(row.end_date, days=-1),
				'item_group': row.item_group,
				'item_code': row.item_code,
				'item_type': row.item_type,
				'unit': row.item_unit
                        }
			usage_data = {
				'consumed_units': row.consumed_units,
				'cost_per_unit': (row.cost_per_unit or 0.0) * flt(settings.exchange_rate)
			}
			mful = frappe.db.exists('Metered Feature Units Log', mful_data)
			if mful:
				frappe.get_doc('Metered Feature Units Log', mful).update(usage_data).save()
			else:
				frappe.new_doc('Metered Feature Units Log').update(mful_data).update(usage_data).insert()
