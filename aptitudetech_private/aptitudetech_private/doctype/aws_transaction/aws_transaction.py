# -*- coding: utf-8 -*-
# Copyright (c) 2015, Aptitudetech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import csv
import datetime
import boto3
import boto3.session
import os
import json
import zipfile
import requests
from frappe.model.document import Document
from decimal import *
from dateutil import relativedelta

class AwsTransaction(Document):
	def import_aws_invoice(self):
		self.download_aws()
		sep=b","
                first_line = 1
                total  = {
                "iphone" : 2007
                }
		total_usage_volume  = {
                "iphone" : 2007
                }
		total_usage_backup  = {
                "iphone" : 2007
                }
		list_server  = {
                "iphone" : "test"
                }

                total.clear()

		prefix = frappe.db.get_value("Monthly Recurring Setup", None, "sales_invoice_title_prefix")
                suffix = frappe.db.get_value("Monthly Recurring Setup", None, "sales_invoice_title_suffix")
		exchange_rate = frappe.db.get_value("Monthly Recurring Setup", None, "exchange_rate")
		if exchange_rate == None:
			frappe.msgprint("VIDE ")
		else:
			frappe.msgprint(exchange_rate)

		pi = frappe.new_doc("Purchase Invoice")
		total_purchase_invoice = Decimal(0)
		pi.title = "Amazon Web Services Inc."
		pi.naming_series = "PINV-AUTO-"
                pi.posting_date = datetime.date.today()
                pi.credit_to = "2111 - Creditors - AT"
                pi.supplier = "Amazon Web Services Inc."
                pi.is_paid = False
                pi.is_return = False
                pi.due_date =  datetime.date.today()
                pi.bill_date = datetime.date.today()
		pi.bill_no = "test12345"
                pi.company = "Aptitude Technologies"
                pi.currency = "CAD"
                pi.conversion_rate = "1"
                pi.buying_price_list = "Buying - Standard"
                pi.price_list_currency = "CAD"
                pi.plc_conversion_rate = "1"
                pi.ignore_pricing_rule = False
                pi.update_stock = False


                with open('/home/ubuntu/frappe-bench/apps/aptitudetech_private/aptitudetech_private/aptitudetech_private/doctype/aws_transaction/Billing-aptech-1.csv', 'rb') as csvfile:
                        spamreader = csv.reader(csvfile, delimiter=sep)
                        for row in spamreader:
                                if first_line == 0 :
                                        if row[8] in total:
                                                total[row[8]] += Decimal(row[21])
						if row[13] == "EBS:VolumeUsage.gp2":
							if row[8] in total_usage_volume:
								total_usage_volume[row[8]] += Decimal(row[16])
							else :
								total_usage_volume[row[8]] = Decimal(row[16])
						if row[13] == "EBS:SnapshotUsage":
                                                        if row[8] in total_usage_backup:
                                                                total_usage_backup[row[8]] += Decimal(row[16])
                                                        else :
                                                                total_usage_backup[row[8]] = Decimal(row[16])
						if row[82] in list_server[row[8]]:
							a=1
						else:
							if ".os." in row[82]:
								a=1
							else:
								list_server[row[8]] += row[82] + "</li><li>"
                                        else:
                                                total[row[8]] = Decimal(row[21])
						if row[13] == "EBS:VolumeUsage.gp2":
                                                	total_usage_volume[row[8]] = Decimal(row[16])
						if row[13] == "EBS:SnapshotUsage":
                                                        total_usage_backup[row[8]] = Decimal(row[16])
						list_server[row[8]] = row[82] + "</li><li>"
                                else:
                                        first_line = 0
		###Code pour boucler sur les Montly reccuring item
		price_list = frappe.db.get_value("Monthly Recurring Setup", None, "price_list")
		for mri in frappe.db.get_all("Monthly Recurring Item"):
                        mri = frappe.get_doc("Monthly Recurring Item", mri.name)
                #for key,val in total.items():
                	# Pour tous les clients on cherche si une entré dans la table des items est fait
			#customer = frappe.db.get_value("Aws Item Setup", {'aws_account_id':key}, "customer")
			#customer = frappe.db.get_value("Monthly Recurring Item", {'aws_account_id':key}, "customer")
			customer = mri.customer
			if customer:
				customer = customer
			else:
				customer = "Aptitude Technologies"
			#item = frappe.db.get_value("Monthly Recurring Item", {'aws_account_id':key}, "item")
			#reseller_margin = frappe.db.get_value("Monthly Recurring Item", {'aws_account_id':key}, "reseller_margin")
			#if  frappe.db.get_value("Aws Item Setup", {'aws_account_id':key}, "billable"):
			#if  frappe.db.get_value("Monthly Recurring Item", {'aws_account_id':key}, "billable"):
			if  mri.billable:
                        	si = frappe.new_doc("Sales Invoice")
				json_update = {
                                        "title": prefix + customer  + suffix,
                                        "naming_series": "SINV-AUTO-",
                                        "posting_date": datetime.date.today(),
                                        "company" : "Aptitude Technologies",
                                        "currency" : "CAD",
                                        "conversion_rate" : "1",
                                        "selling_price_list" : "Selling - Standard",
                                        "price_list_currency" : "CAD",
                                        "plc_conversion_rate" : "1",
                                        "base_net_total" : 0,
                                        "base_grand_total" : 0,
                                        "grand_total" : 0,
                                        "debit_to" : "1111 - Debtors CDN - AT",
                                        "customer" : customer,
                                        "taxes_and_charges": "Quebec - Taxes - AT",
                                }
                                si.set_taxes()
                                si.update (json_update)

				#Section des item amazon
				if mri.aws_account_id:
					key = mri.aws_account_id
					item = mri.item
					reseller_margin = mri.reseller_margin
                        		#self.test_2 = self.test_2 + customer + "=" +  " " + reseller_margin +  "\n\n"

					description = frappe.db.get_value("Item", item, "description")
					if key in total_usage_backup:
						description = description.replace("--BACKUP--", str(round(total_usage_backup[key],2)))
					if key in total_usage_volume:
						description = description.replace("--USAGE--", str(round(total_usage_volume[key],2)))
					if key in list_server:
						list_server[key] += "</li>"
						list_server[key] = str(list_server[key]).replace("<li></li>", "")
						description = description.replace("--SERVER--", str(list_server[key]))
				
					si.append("items",
                                	{
						"item_code": item,
                                        	"item_name": frappe.db.get_value("Item", item, "item_name"),
                                        	"description": description,
                                        	"rate": round(total[key] * Decimal(exchange_rate) * Decimal(reseller_margin),2),
                                        	"amount": round(total[key] * Decimal(exchange_rate) * Decimal(reseller_margin),2),
                                        	"base_rate": round(total[key] * Decimal(exchange_rate) * Decimal(reseller_margin),2),
                                        	"base_amount": round(total[key] * Decimal(exchange_rate) * Decimal(reseller_margin),2),
                                        	"income_account": "4181 - Service - General - AT",
                                        	"cost_center": "Main - AT",
                                        	"qty": "1",
                                        	"stock_uom":"Unit"
 					})
					pi.append("items",
                                        {
                                                "item_code": item,
                                                "item_name": frappe.db.get_value("Item", item, "item_name"),
                                                "description": frappe.db.get_value("Item", item, "description"),
                                                "rate": round(total[key] * Decimal(exchange_rate),2),
                                                "amount": round(total[key] * Decimal(exchange_rate),2),
                                                "base_rate": round(total[key] * Decimal(exchange_rate),2),
                                                "base_amount": round(total[key] * Decimal(exchange_rate),2),
                                                "expense_account": "5141 - Hosting - AWS - AT",
                                                "cost_center": "Main - AT",
                                                "qty": "1",
                                                "stock_uom":"Unit"
                                        })
					total_purchase_invoice = total_purchase_invoice + (Decimal(total[key]) * Decimal(exchange_rate))
				#Section des item synnex
				if mri.snx_eu_no:
					frappe.msgprint(customer)
					items_synnex = self.connect_sinnex(mri.snx_eu_no)
					for key, val in items_synnex.items():
						#frappe.get_doc("Monthly Recurring Item", {'supplier_part_no': val,'supplier':"Synnex"}).parent
						item = frappe.db.get_value("Item Supplier", {'supplier_part_no': key,'supplier':"Synnex"}, "parent")
						if item:
							frappe.msgprint(item)
							description = frappe.db.get_value("Item", item, "description")
							item_price = frappe.db.get_value("Item Price", {'price_list':price_list,'item_code':item}, "price_list_rate")
							si.append("items",
                                        		{
                                                		"item_code": item,
                                                		"item_name": frappe.db.get_value("Item", item, "item_name"),
                                                		"description": description,
                                                		"rate": item_price,
                                                		"amount": item_price * int(val),
                                                		"base_rate": item_price,
                                                		"base_amount": item_price * int(val),
                                                		"income_account": "4181 - Service - General - AT",
                                                		"cost_center": "Main - AT",
                                                		"qty": int(val),
                                                		"stock_uom":"Unit"
                                        		})
                        	
				#Section des items statiques
				if mri.items:
					for d in mri.items:
						item_price = frappe.db.get_value("Item Price", {'price_list':price_list,'item_code':d.item}, "price_list_rate")
						if d.quantity == None :
							quantity = 1
						else:
							quantity = d.quantity
						si.append("items", {
							"item_code": d.item,
                                        		"item_name": frappe.db.get_value("Item", d.item, "item_name"),
                                        		"description": frappe.db.get_value("Item", d.item, "description"),
                                        		"rate": item_price,
                                        		"amount": item_price * quantity,
                                        		"base_rate": item_price,
                                        		"base_amount": item_price * quantity,
                                        		"income_account": "4181 - Service - General - AT",
                                        		"cost_center": "Main - AT",
                                        		"qty": d.quantity,
							"discount_percentage": d.discount,
                                        		"stock_uom":"Unit"
						})
                        	si.save()
                        	#si.submit()
			#total_purchase_invoice = total_purchase_invoice + ( Decimal(total[key]) * Decimal(self.change_rate))
			#frappe.msgprint(key)
			#frappe.msgprint(frappe.db.get_value("Item", item, "item_name"))

		pi.base_total = round(total_purchase_invoice, 2)
                pi.base_net_total = round(total_purchase_invoice,2)
                pi.base_grand_total = round(total_purchase_invoice,2)
                pi.grand_total = round(total_purchase_invoice,2)

                #frappe.msgprint(str(json_update))
                pi.save()

		path = "/home/ubuntu/frappe-bench/apps/aptitudetech_private/aptitudetech_private/aptitudetech_private/doctype/aws_transaction/"
		os.remove(path + "tmp1.json")
                os.remove(path + "tmp2.zip")
                os.remove(path + "Billing-aptech-1.csv")
	
	def download_aws(self):

		#bucket_name = frappe.db.get_value("Aws Setup", None, "s3_bucket")
		#report_name = frappe.db.get_value("Aws Setup", None, "report_name")

		bucket_name = frappe.db.get_value("Monthly Recurring Setup", None, "s3_bucket")
                report_name = frappe.db.get_value("Monthly Recurring Setup", None, "report_name")

		session = boto3.session.Session(region_name='us-east-1')
		s3client = session.client('s3', config= boto3.session.Config(signature_version='s3v4'))
		#resp = s3client.list_objects(Bucket=bucket_name)

		# print names of all objects
		first_day_of_this_month = frappe.utils.data.get_first_day (self.transaction_date, 0, 0)
                next_month = frappe.utils.data.get_first_day (self.transaction_date, 0, 1)

		#for obj in resp['Contents']:
		#	if "Billing-aptech-Manifest.json" in str(obj['Key']):
    		#		frappe.msgprint("Object Name: " + obj['Key'])

		# Get the service client
		s3 = boto3.client('s3')

		# Download object at bucket-name with key-name to tmp.txt
		path = "/home/ubuntu/frappe-bench/apps/aptitudetech_private/aptitudetech_private/aptitudetech_private/doctype/aws_transaction/"
		s3client.download_file(bucket_name, report_name + "/Billing-aptech/" + str(first_day_of_this_month).replace("-", "") + "-" + str(next_month).replace("-","") + "/Billing-aptech-Manifest.json", path + "tmp1.json")
		
		path = "/home/ubuntu/frappe-bench/apps/aptitudetech_private/aptitudetech_private/aptitudetech_private/doctype/aws_transaction/"
                j = json.loads(open(path + "tmp1.json", 'r').read())

		s3client.download_file(bucket_name, str(j["reportKeys"]).replace("[u'","").replace("']",""), path + "tmp2.zip")
		
		zip_ref = zipfile.ZipFile(path + "tmp2.zip", 'r')
                zip_ref.extractall(path)
                zip_ref.close()

	def read_JSON(self):
		path = "/home/ubuntu/frappe-bench/apps/aptitudetech_private/aptitudetech_private/aptitudetech_private/doctype/aws_transaction/"
		zip_ref = zipfile.ZipFile(path + "tmp2.zip", 'r')
		zip_ref.extractall(path)
		zip_ref.close()
	
	def connect_sinnex(self, snx_eu_no):
		url = 'https://ws.synnex.ca/webservice/auth/token'
		data = {
  			"action_name":"create_access_token",
    			"user_name":"cfortin@aptitudetech.net",
    			"password":"743Forcha1!"
		}
		s = requests.Session()
		response = s.post(url, json=data)
		
		json_obj=json.loads(response.text)

		url = 'https://ws.synnex.ca/webservice/solutions/csp/license'
		
		headers = {
				"Authorization" : "Bearer %s" %json_obj["access_token"].encode("ascii","ignore"),
				"content-type" : "application/json"
			}
	
		data = {
			"action_name" : "get_subscriptions",
			"snx_eu_no" : snx_eu_no,
		}

		response = s.post(url, json=data, headers=headers)
		
		data = json.loads(response.text.decode('utf-8'))
		
		frappe.msgprint(json.dumps(data))
		
		item_synnex = {
			"iphone" : 2007
		}	
		for item in data["items"]:
			item_synnex[str(item["snx_sku_no"])] = int(item["quantity"])
		return item_synnex
