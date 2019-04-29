// Copyright (c) 2019, Aptitudetech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Simplified Timesheet', {
	onload: function(frm){
	},
	refresh: function(frm) {
		if (frm.doc.user && !frm.doc.employee) frm.trigger('user');
		if (!frm.doc.start_date) frm.set_value('start_date', frappe.datetime.month_start());
		if (!frm.doc.end_date) frm.set_value('end_date', frappe.datetime.month_end());
	},
	user: function(frm){
		frappe.call({
			'method': 'get_employee',
			'doc': frm.doc,
			'args': {},
			'callback': function(res){
				cur_frm.refresh_fields();
				cur_frm.trigger('refresh');
			}
		});
	}
});

frappe.ui.form.on('Simplified Timesheet Detail', {
	'reported_working_start_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'reported_working_start_time', 'reported_working_end_time', 'reported_working_time');
	
	},
	'reported_working_end_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'reported_working_start_time', 'reported_working_end_time', 'reported_working_time');
	},
	'reported_working_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'reported_working_start_time', 'reported_working_end_time', 'reported_working_time');
	},
	'approved_working_start_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'approved_working_start_time', 'approved_working_end_time', 'approved_working_time');
	},
	'approved_working_end_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'approved_working_start_time', 'approved_working_end_time', 'approved_working_time');
	},
	'approved_working_time': function(frm, cdt, cdn){
		calculate_end_time(frm, cdt, cdn, 'approved_working_start_time', 'approved_working_end_time', 'approved_working_time');
	}
})

var calculate_end_time = function(frm, cdt, cdn, from_time_field, to_time_field, hours_field) {
	let child = locals[cdt][cdn];

	if(!child[from_time_field]) {
		// if from_time value is not available then set the current datetime
		frappe.model.set_value(cdt, cdn, from_time_field, frappe.datetime.get_datetime_as_string());
	}

	let d = moment(child.from_time);
	if(child[hours_field]) {
		var time_diff = (moment(child[to_time_field]).diff(moment(child[from_time_field]),"seconds")) / (60 * 60 * 24);
		var std_working_hours = 0;
		var hours = moment(child[to_time_field]).diff(moment(child[from_time_field]), "seconds") / 3600;

		std_working_hours = time_diff * frappe.working_hours;

		if (std_working_hours < hours && std_working_hours > 0) {
			frappe.model.set_value(cdt, cdn, hours_field, std_working_hours);
			frappe.model.set_value(cdt, cdn, to_time_field, d.add(hours, "hours").format(frappe.defaultDatetimeFormat));
		} else {
			d.add(child[hours_field], "hours");
			frm._setting_hours = true;
			frappe.model.set_value(cdt, cdn, to_time_field,
				d.format(frappe.defaultDatetimeFormat)).then(() => {
				frm._setting_hours = false;
			});
		}
	}
};
