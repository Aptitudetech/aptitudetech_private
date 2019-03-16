// Copyright (c) 2019, Aptitudetech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Simplified Time Reporting', {
	refresh: function(frm) {
	}
});
frappe.ui.form.on("Simplified Time Reporting", {
    	onload_post_render: function(frm) {
		frappe.call({
			method: "onload_post_render",
			doc: frm.doc,
			args: {	},
			callback: function() {
				frm.refresh();
			}
		});
	
    	},
	on_submit: function(frm) {
                frappe.call({
                        method: "on_submit",
                        doc: frm.doc,
                        args: { },
                        callback: function() {
                        }
                });

        },

});





frappe.ui.form.on("Timesheet Detail", {		
	time_logs_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn);
	},

	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var time_diff = (moment(child.to_time).diff(moment(child.from_time),"seconds")) / ( 60 * 60 * 24);
		var std_working_hours = 0;

		if(frm._setting_hours) return;

		var hours = moment(child.to_time).diff(moment(child.from_time), "seconds") / 3600;
		std_working_hours = time_diff * frappe.working_hours;

		if (std_working_hours < hours && std_working_hours > 0) {
			frappe.model.set_value(cdt, cdn, "hours", std_working_hours);
		} else {
			frappe.model.set_value(cdt, cdn, "hours", hours);
		}
	},

	time_logs_add: function(frm) {
		var $trigger_again = $('.form-grid').find('.grid-row').find('.btn-open-row');
		$trigger_again.on('click', () => {
			$('.form-grid')
				.find('[data-fieldname="timer"]')
				.append(frappe.render_template("timesheet"));
			frm.trigger("control_timer");
		})
	},
	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn)
	},

	billing_hours: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	costing_rate: function(frm, cdt, cdn) {
		calculate_billing_costing_amount(frm, cdt, cdn)
	},

	billable: function(frm, cdt, cdn) {
		update_billing_hours(frm, cdt, cdn);
		update_time_rates(frm, cdt, cdn);
		calculate_billing_costing_amount(frm, cdt, cdn);
	},

	activity_type: function(frm, cdt, cdn) {
		frm.script_manager.copy_from_first_row('time_logs', frm.selected_doc,
			'project');

		frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
			args: {
				employee: frm.doc.employee,
				activity_type: frm.selected_doc.activity_type
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'billing_rate', r.message['billing_rate']);
					frappe.model.set_value(cdt, cdn, 'costing_rate', r.message['costing_rate']);
					calculate_billing_costing_amount(frm, cdt, cdn);
				}
			}
		})
	}
});



var calculate_end_time = function(frm, cdt, cdn) {
	let child = locals[cdt][cdn];

	if(!child.from_time) {
		// if from_time value is not available then set the current datetime
		frappe.model.set_value(cdt, cdn, "from_time", frappe.datetime.get_datetime_as_string());
	}

	let d = moment(child.from_time);
	if(child.hours) {
		var time_diff = (moment(child.to_time).diff(moment(child.from_time),"seconds")) / (60 * 60 * 24);
		var std_working_hours = 0;
		var hours = moment(child.to_time).diff(moment(child.from_time), "seconds") / 3600;

		std_working_hours = time_diff * frappe.working_hours;

		if (std_working_hours < hours && std_working_hours > 0) {
			frappe.model.set_value(cdt, cdn, "hours", std_working_hours);
			frappe.model.set_value(cdt, cdn, "to_time", d.add(hours, "hours").format(frappe.defaultDatetimeFormat));
		} else {
			d.add(child.hours, "hours");
			frm._setting_hours = true;
			frappe.model.set_value(cdt, cdn, "to_time",
				d.format(frappe.defaultDatetimeFormat)).then(() => {
					frm._setting_hours = false;
				});
		}
	}
}
