// Copyright (c) 2016, Aptitudetech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Aws Transaction', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on("Aws Transaction", "refresh", function(frm) {
        frm.add_custom_button(__("Import AWS Invoice"), function() {
            // When this button is clicked, do this
                frm.call({
                        'method': 'import_aws_invoice',
                        'doc': frm.doc,
                        'args': {},

                        callback: function() {
                                cur_frm.refresh();
                        }
                });
            });
    });

frappe.ui.form.on("Aws Transaction", "refresh", function(frm) {
        frm.add_custom_button(__("connect sinnex"), function() {
            // When this button is clicked, do this
                frm.call({
                        'method': 'connect_sinnex',
                        'doc': frm.doc,
                        'args': {snx_eu_no: "105547"},

                        callback: function() {
                                cur_frm.refresh();
                        }
                });
            });
    });


/*frappe.ui.form.on("Aws Transaction", "refresh", function(frm) {
        frm.add_custom_button(__("Test AWS Download"), function() {
            // When this button is clicked, do this
                frm.call({
                        'method': 'download_aws',
                        'doc': frm.doc,
                        'args': {},

                        callback: function() {
                                cur_frm.refresh();
                        }
                });
            });
    });

frappe.ui.form.on("Aws Transaction", "refresh", function(frm) {
        frm.add_custom_button(__("Test read JSON"), function() {
            // When this button is clicked, do this
                frm.call({
                        'method': 'read_JSON',
                        'doc': frm.doc,
                        'args': {},

                        callback: function() {
                                cur_frm.refresh();
                        }
                });
            });
    });*/

