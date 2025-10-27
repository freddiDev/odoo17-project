odoo.define('equip3_pos_printer_bluetooth.Models', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var _t = core._t;
var { Gui } = require('point_of_sale.Gui');
var { Printer } = require('point_of_sale.Printer');
var QWeb = core.qweb;


models.load_fields('product.product','pos_categ_id');
models.load_fields("restaurant.printer", ["EasyERPS_app_port"]);
models.load_fields("pos.config", ["is_multiple_printer"]);
models.load_models([{
    model: 'pos.config.multiple.printer',
    fields: ['name','port','receipt_template_id','copies_of_receipts','config_id','print_category_receipt','ip_address'],
    loaded: function(self,multiple_printer){
        if(multiple_printer.length){
            self.pos_multiple_printer = [];
            for(var i=0;i<multiple_printer.length;i++){
                if(multiple_printer[i].config_id && self.config_id==multiple_printer[i].config_id[0]){
                    self.pos_multiple_printer.push(multiple_printer[i])
                }
                
            }
        }
    },
    }],{'before': 'pos.config'});

models.load_models([{
    model: 'pos.category',
    condition: function(self){ return self.config.receipt_types_views === "categoryReceipt"; },
    fields: ['name'],
    loaded: function(self,category){
        if(category.length){
            self.pos_categ_id = [];
            for(var i=0;i<category.length;i++){
                self.pos_categ_id.push(category[i].id)
            }
        }else {
            try{
                Gui.showPopup('ErrorPopup', {
                    title: _t('No PoS Product Categories Found'),
                    body: _t('Please add PoS Product Categories to print Categories Receipt.'),
                });
            }catch(err) {
                console.log('No PoS Product Categories Found\nPlease add PoS Product Categories to print Categories Receipt.')
                console.error('EasyERPS ~ ',err);
            }
        }
    },
    }],{'after': 'product.product'});

    var _super_orderLine = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        export_for_printing: function(){
            var result = _super_orderLine.export_for_printing.apply(this, arguments);
            result.pos_categ_id = this.get_product().pos_categ_id;
            return result;
        }
    });

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
            var date    = new Date();
            json.LocaleStringdateStyle = date.toLocaleString('en-US', {day: "2-digit"})+" "+ date.toLocaleString('en-US', { month: "short"})+" "+date.toLocaleString('en-US', { year: "numeric"});
            json.LocaleStringtimeStyle = date.toLocaleString('en-US', { timeStyle: "short" ,hour12: true });
            json.sequence_number = this.sequence_number;
            return json;
        },

        export_for_printing: function() {
            var result = _super_order.export_for_printing.apply(this,arguments);
            var date    = new Date();
            result.date.LocaleStringdateStyle = date.toLocaleString('en-US', {day: "2-digit"})+" "+ date.toLocaleString('en-US', { month: "short"})+" "+date.toLocaleString('en-US', { year: "numeric"});
            result.date.LocaleStringtimeStyle = date.toLocaleString('en-US', { timeStyle: "short" ,hour12: true });
            return result;
        },

        computeChanges: function(categories){
            var current_res = this.build_line_resume();
            var old_res     = this.saved_resume || {};
            var json        = this.export_as_JSON();
            var add = [];
            var rem = [];
            var p_key, note;

            for (p_key in current_res) {
                for (note in current_res[p_key]['qties']) {
                    var curr = current_res[p_key];
                    var old  = old_res[p_key] || {};
                    var pid = curr.pid;
                    var found = p_key in old_res && note in old_res[p_key]['qties'];

                    if (!found) {
                        add.push({
                            'id':       pid,
                            'name':     this.pos.db.get_product_by_id(pid).display_name,
                            'category': this.pos.db.get_product_by_id(pid).pos_categ_id[0],
                            'categoryName': this.pos.db.get_product_by_id(pid).pos_categ_id[1],
                            'name_wrapped': curr.product_name_wrapped,
                            'note':     note,
                            'qty':      curr['qties'][note],
                        });
                    } else if (old['qties'][note] < curr['qties'][note]) {
                        add.push({
                            'id':       pid,
                            'name':     this.pos.db.get_product_by_id(pid).display_name,
                            'category': this.pos.db.get_product_by_id(pid).pos_categ_id[0],
                            'categoryName': this.pos.db.get_product_by_id(pid).pos_categ_id[1],
                            'name_wrapped': curr.product_name_wrapped,
                            'note':     note,
                            'qty':      curr['qties'][note] - old['qties'][note],
                        });
                    } else if (old['qties'][note] > curr['qties'][note]) {
                        rem.push({
                            'id':       pid,
                            'name':     this.pos.db.get_product_by_id(pid).display_name,
                            'category': this.pos.db.get_product_by_id(pid).pos_categ_id[0],
                            'categoryName': this.pos.db.get_product_by_id(pid).pos_categ_id[1],
                            'name_wrapped': curr.product_name_wrapped,
                            'note':     note,
                            'qty':      old['qties'][note] - curr['qties'][note],
                        });
                    }
                }
            }

            for (p_key in old_res) {
                for (note in old_res[p_key]['qties']) {
                    var found = p_key in current_res && note in current_res[p_key]['qties'];
                    if (!found) {
                        var old = old_res[p_key];
                        var pid = old.pid;
                        rem.push({
                            'id':       pid,
                            'name':     this.pos.db.get_product_by_id(pid).display_name,
                            'category': this.pos.db.get_product_by_id(pid).pos_categ_id[0],
                            'categoryName': this.pos.db.get_product_by_id(pid).pos_categ_id[1],
                            'name_wrapped': old.product_name_wrapped,
                            'note':     note,
                            'qty':      old['qties'][note],
                        });
                    }
                }
            }

            if(categories && categories.length > 0){
                // filter the added and removed orders to only contains
                // products that belong to one of the categories supplied as a parameter

                var self = this;

                var _add = [];
                var _rem = [];

                for(var i = 0; i < add.length; i++){
                    if(self.pos.db.is_product_in_category(categories,add[i].id)){
                        _add.push(add[i]);
                    }
                }
                add = _add;

                for(var i = 0; i < rem.length; i++){
                    if(self.pos.db.is_product_in_category(categories,rem[i].id)){
                        _rem.push(rem[i]);
                    }
                }
                rem = _rem;
            }

            var d = new Date();
            var hours   = '' + d.getHours();
                hours   = hours.length < 2 ? ('0' + hours) : hours;
            var minutes = '' + d.getMinutes();
                minutes = minutes.length < 2 ? ('0' + minutes) : minutes;

            return {
                'new': add,
                'cancelled': rem,
                'table': json.table || false,
                'floor': json.floor || false,
                'name': json.name  || 'unknown order',
                'sequence_number': json.sequence_number  || 'unknown order',
                'date1': json.LocaleStringdateStyle  || 'unknown order',
                'date2': json.LocaleStringtimeStyle  || 'unknown order',

                'time': {
                    'hours':   hours,
                    'minutes': minutes,
                },
            };

        },

        computeChanges_product: function(){
            var printers = this.pos.printers;
            var add = [];
            var rem = [];
            for(var i = 0; i < printers.length; i++){
                        var changes = this.computeChanges(printers[i].config.product_categories_ids);
                        if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                            if (this.pos.config.receipt_types_views === "categoryReceipt" || this.pos.config.receipt_types_views === "labelReceipt"){
                                for(var n=0;n < changes['new'].length;n++){
                                    for(var nq=0;nq < changes['new'][n].qty;nq++){
                                     add.push(changes['new'][n])
                                    }
                                }
                                for(var c=0;c < changes['cancelled'].length;c++){
                                    for(var cq=0;cq < changes['cancelled'][c].qty;cq++){
                                     rem.push(changes['cancelled'][c])
                                    }
                                }

                            }

                        }
                    }

            return {
                'new': add,
                'cancelled': rem,
                'table': changes['table'],
                'floor': changes['floor'],
                'name': changes['name'],
                'time': {
                    'hours':   changes['time']['hours'],
                    'minutes': changes['time']['hours'],
                },

            };

        },

        computeChanges_orderlines: function(){
            var printers = this.pos.printers;
            var all_changes = null;
            var add = []
            var rem = []
            for(var i = 0; i < printers.length; i++) {
                var changes = this.computeChanges(printers[i].config.product_categories_ids);
                if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    if (all_changes) {
                        if (changes['new'].length > 0) {
                            all_changes['new'].push({name_wrapped: ['### ' + printers[i].config?.name]})
                            all_changes['new'] = all_changes['new'].concat(changes['new'])
                        }
                        if (changes['cancelled'].length > 0) {
                            all_changes['cancelled'].push({name_wrapped: ['### ' + printers[i].config?.name]})
                            all_changes['cancelled'] = all_changes['cancelled'].concat(changes['cancelled'])
                        }

                    } else {
                        all_changes = changes
                    }
                }
            }
            if (all_changes){
                if (all_changes['new'].length > 0 || all_changes['cancelled'].length > 0){
                     add = all_changes.new;
                     rem = all_changes.cancelled;
                }
            }

            return {
                'all': add.concat(rem),

            };

        },

        printChanges: async function(){
                var printers = this.pos.printers;
                var order = this.pos.get_order();
                let isPrintSuccessful = true;
                var all_changes = null;
                var all_changes_product = this.computeChanges_product();
                if (this.pos.config.pos_bluetooth_printer && this.pos.config.receipt_types_views === "labelReceipt"){
                    if (all_changes_product){
                        Gui.showTempScreen('KitchenReceiptScreen', {changes:all_changes_product})
                    }
                }else {
                        for(var i = 0; i < printers.length; i++){
                        var changes = this.computeChanges(printers[i].config.product_categories_ids);
                        if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                            if (this.pos.config.pos_bluetooth_printer &&  this.pos.config.receipt_types_views === "categoryReceipt"){
                                if (all_changes){
                                    if (changes['new'].length > 0){
                                        all_changes['new'].push({name_wrapped:['### ' + printers[i].config?.name]})
                                        all_changes['new'] = all_changes['new'].concat(changes['new'])
                                    }
                                    if (changes['cancelled'].length > 0){
                                        all_changes['cancelled'].push({name_wrapped:['### ' + printers[i].config?.name]})
                                        all_changes['cancelled'] = all_changes['cancelled'].concat(changes['cancelled'])
                                    }

                                }
                                else {
                                    all_changes = changes
                                }
                            }else{
                                var receipt = QWeb.render('OrderChangeReceipt',{changes:changes, widget:this});
                                const result = await printers[i].print_receipt(receipt);
                                if (!result.successful) {
                                    isPrintSuccessful = false;
                                }
                            }

                        }
                    }
                    if (all_changes){
                        Gui.showTempScreen('KitchenReceiptScreen', {changes:all_changes})
                    }
                }


                return isPrintSuccessful;
            },
            get_receipt_bluetooth_printer: function(type){
                var self = this;
                var printers = [];
                let printers_categories = this.pos.printers;
                for (let i = 0; i < printers_categories.length; i++) {
                    let printer = printers_categories[i].config;
                    if(printer.printer_type == 'bluetooth_printer'){
                        let printer_values = {
                            'id': printer.id,
                            'name': printer.name,
                            'port': false,
                        }
                        if(['print_receipt_and_category','print_category'].includes(type)){
                            printer_values['product_categories_ids'] = printer.product_categories_ids;
                            let product_categories = [];
                            for (let i in self.pos.pos_category_by_id ) {
                                let cat = self.pos.pos_category_by_id[i];
                                if(printer.product_categories_ids.includes(cat.id)){
                                    product_categories.push({
                                        'id': cat.id,
                                        'name': cat.name,
                                        'category_type': cat.category_type,
                                        'child_id': cat.child_id,
                                    })
                                }
                            }
                            printer_values['product_categories'] = product_categories;
                        }

                        if(printer.EasyERPS_app_port){
                            printer_values['port'] = printer.EasyERPS_app_port;
                        }
                        if(printer.proxy_ip){
                            printer_values['proxy_ip'] = printer.proxy_ip;
                        }
                        printers.push(printer_values);
                    }
                }
                var orderlines = [];
                var orderlines_simple = [];
                var total_item = 0;

                function bom_combo_display_name(rec){
                    let display_name = rec.product_id[1];
                    if(self.pos.config && self.pos.config.display_product_name_without_product_code){
                        return display_name.replace(/[\[].*?[\]] */, '');
                    }
                    return display_name;
                }
                this.orderlines.each(function(orderline){
                    let line = orderline.export_for_printing();
                    
                    let bom_components = [];
                    if(line.bom_components){
                        for(let com of line.bom_components){
                            let label = '';
                            if(com.is_extra){
                                if(com.checked){
                                    label = 'Extra ' + bom_combo_display_name(com);
                                }
                            }else{
                                if(!com.checked){
                                    label = 'No ' + bom_combo_display_name(com);
                                }
                            }
                            bom_components.push({ label: label });
                        }
                    }

                    let pos_combo_options = [];
                    if(line.pos_combo_options){
                        for(let option of line.pos_combo_options){
                            pos_combo_options.push({ label: '1X ' + bom_combo_display_name(option) });
                        }
                    }


                    orderlines.push({
                        'id': line.id,
                        'quantity': line.quantity,
                        'unit_name': line.unit_name,
                        'product_name': orderline.get_orderline_product_name(),
                        'price_display': self.pos.format_currency(line.price_display),
                        'pos_categ_id': line.pos_categ_id,
                        'bom_components': bom_components,
                        'pos_combo_options': pos_combo_options,
                    });
                });
                this.orderlines.each(function(orderline){
                    let line = orderline.export_for_printing();
                    total_item+=line.quantity
                    orderlines_simple.push({
                        
                        'item': orderline.get_orderline_product_name(),
                        'item_qty': line.quantity,
                        'unit_name': line.unit_name,
                        'amount':self.pos.format_currency(line.price_display),

                    });
                });

                var paymentlines = [];
                var _paymentlines = this.paymentlines.models
                    .filter(function (paymentline) {
                        return !paymentline.is_change;
                    })
                    .map(function (paymentline) {
                        return paymentline.export_for_printing();
                    });
                for (let i = _paymentlines.length - 1; i >= 0; i--) {
                    let line = _paymentlines[i];
                    paymentlines.push({
                        'cid': line.cid,
                        'name': line.name,
                        'amount': self.pos.format_currency(line.amount),
                    });
                }

                var logo = this.pos.company_logo_base64;
                if(logo){
                    logo = logo.replace('data:image/png;base64,','')
                }


                var taxdetails = {}
                this.orderlines.each(function(orderline){
                    let line = orderline.export_for_printing();
                    var taxdetails_line = line['taxdetails'];
                    $.each(taxdetails_line, function (i, v) {
                        if(i in taxdetails){
                            taxdetails[i] = taxdetails[i] + v
                        }
                        else{
                            taxdetails[i] = v
                        }
                    })
                });

                let table = false;
                if(this.table){
                    table = {
                        name: this.table.name,
                        floor: {
                            id: this.table.floor.id,
                            name: this.table.floor.name,
                        }
                    }
                }


                var client  = this.get('client');
                var cashier = this.pos.get_cashier();
                var company = this.pos.company;
                var date    = new Date();
                var receipt = {
                    ean13: this.ean13,
                    orderlines: orderlines,
                    total_item:total_item,
                    orderlines_simple: orderlines_simple,
                    paymentlines: paymentlines,
                    subtotal: self.pos.format_currency(this.get_subtotal()),
                    total_with_tax: self.pos.format_currency(this.get_total_with_tax()),
                    total_without_tax: self.pos.format_currency(this.get_total_without_tax()),
                    total_tax: self.pos.format_currency(this.get_total_tax()),
                    total_paid: self.pos.format_currency(this.get_total_paid()),
                    total_discount: self.pos.format_currency(this.get_total_discount()),
                    // tax_details: self.pos.format_currency(this.get_tax_details()),
                    change: this.locked ? self.pos.format_currency(this.amount_return) : self.pos.format_currency(this.get_change()),
                    name : this.get_name(),
                    client: client ? client : false ,
                    cashier: cashier ? cashier.name : false,
                    date: {
                        year: date.getFullYear(),
                        month: date.getMonth(),
                        date: date.getDate(),       // day of the month
                        day: date.getDay(),         // day of the week
                        hour: date.getHours(),
                        minute: date.getMinutes() ,
                        isostring: date.toISOString(),
                        localestring: this.formatted_validation_date,
                    },
                    company: {
                        email: company.email,
                        website: company.website,
                        company_registry: company.company_registry,
                        contact_address: company.partner_id[1],
                        vat: company.vat,
                        vat_label: company.country && company.country.vat_label || _t('Tax ID'),
                        name: company.name,
                        phone: company.phone,
                        logo: logo,
                    },
                    currency: this.pos.currency,
                    printers: printers,
                    customer_count: this.customer_count,
                    plus_point: this.plus_point,
                    redeem_point: this.redeem_point,
                    table : table,

                    total_discount_wo_pricelist:  self.pos.format_currency(this.get_total_discount_wo_pricelist()),
                    rounding_order: self.pos.format_currency(this.get_total_with_tax() - this.get_total_with_tax_without_rounding() - this.total_mdr_amount_customer),
                    total:  self.pos.format_currency(this.get_total_with_tax()),
                    mdr_customer: self.pos.format_currency(this.total_mdr_amount_customer),
                    taxtotal: self.pos.format_currency(this.get_total_with_tax_without_rounding() - this.get_total_without_tax()),
                    taxdetails: taxdetails,
                    qrCodeLink: window.origin + '/report/barcode/QR/' + this.ean13
                };
                return receipt;
            },



            get_receipt_bluetooth_printer_for_category(){
                let receipt = this;
                let datas = [];
                let receipt_date = moment().format('DD MMM YYYY hh:mm A');
                if(receipt.formatted_validation_date){   
                    receipt_date = moment(receipt.formatted_validation_date, 'MM/DD/YYYY HH:mm:ss').format('DD MMM YYYY hh:mm A');
                }

                // Floor/table
                if(receipt.table){
                    datas.push({
                        "type": "text",
                        "data": receipt.table.floor.name +' / '+ receipt.table.name,
                        "styles": {
                            "bold": true,
                            "align": "center",
                            "fontType": "fontA"
                        }
                    });
                }

                // Line Break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );

                // Order Number
                datas.push({
                    "type": "text",
                    "data": "No Order : " + receipt.name,
                    "styles": {
                        "align": "left",
                        "fontType": "fontA"
                    }
                });

                // Date
                datas.push({
                    "type": "text",
                    "data": "Date : " + receipt_date,
                    "styles": {
                        "align": "left",
                        "fontType": "fontA"
                    }
                });

                // Server
                if(receipt.cashier){
                    datas.push({
                        "type": "text",
                        "data": "Server : " + receipt.cashier.name,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });
                }

                // Line Break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );


                // Category & product
                let total_quantity = 0;
                let data_orderlines = [];
                this.orderlines.each(function(orderline){
                    let line = orderline.export_for_printing();
                    total_quantity += line.quantity;
                    if(line.pos_categ_id){
                        data_orderlines.push({
                            "type": "text",
                            "data": line.pos_categ_id[1],
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        });

                    }

                    data_orderlines.push({
                        "type": "text",
                        "data": line.quantity + 'X ' + orderline.get_orderline_product_name(),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });
 
                }); 
                datas = [...datas, ...data_orderlines]

                // Total items
                datas.push({
                    "type": "text",
                    "data": "Total Items : " + total_quantity,
                    "styles": {
                        "align": "left",
                        "fontType": "fontA"
                    }
                });

                // Company name
                datas.push({
                    "type": "text",
                    "data": receipt.pos.company.name,
                    "styles": {
                        "bold": false,
                        "align": "center",
                        "fontType": "fontA"
                    }
                });

                return { "type": "print_dynamic_receipt", "datas": datas };
            },

            get_receipt_bluetooth_printer_for_queue(receiptObj){
                let receipt = this.get_receipt_bluetooth_printer('print_category');
                let datas = [];

                // Floor/table
                datas.push({
                    "type": "text",
                    "data": receiptObj.floor +' / '+ receiptObj.table,
                    "styles": {
                        "bold": true,
                        "align": "center",
                        "fontType": "fontA"
                    }
                });

                // Ticket number
                datas.push({
                    "type": "text",
                    "data": 'Ticket No :' + receiptObj.order_ticket,
                    "styles": {
                        "bold": false,
                        "align": "center",
                        "fontType": "fontA"
                    }

                });

                // DIne in/takeaway type
                let type = "**DINE-IN**";
                if(receiptObj.from == 'takeaway'){
                    type = "**TAKEAWAY**";
                }
                datas.push({
                    "type": "text",
                    "data": type,
                    "styles": {
                        "bold": false,
                        "align": "center",
                        "fontType": "fontA"
                    }
                });

                // Line Break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );

                // Order Number
                datas.push({
                    "type": "text",
                    "data": "No Order : " + receiptObj.order_number,
                    "styles": {
                        "align": "left",
                        "fontType": "fontA"
                    }
                });

                // Date
                datas.push({
                    "type": "text",
                    "data": "Date : " + moment().format('DD/MM/YY h:mm'), // Current Date
                    "styles": {
                        "align": "left",
                        "fontType": "fontA"
                    }
                });

                // Server
                datas.push(
                    {
                        "type": "text",
                        "data": "Server : " + receipt.cashier,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    }
                );

                // Line Break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );


                // Category & product
                let total_quantity = 0;
                for (var i = receiptObj.order_line.length - 1; i >= 0; i--) {
                    let line = receiptObj.order_line[i];
                    total_quantity += line.item_qty;

                    datas.push(
                        {
                            "type": "text",
                            "data": line.item_qty + 'X ' + line.item,
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        }
                    );

                    if(line.bom_components){
                        for(let component of line.bom_components){
                            datas.push({
                                "type": "text",
                                "data": '   ' + component.label,
                                "styles": {
                                    "align": "left",
                                    "fontType": "fontA"
                                }
                            });
                        }
                    }

                    let pos_combo_options = [];
                    if(line.pos_combo_options){
                        for(let option of line.pos_combo_options){
                            datas.push({
                                "type": "text",
                                "data": '   ' + option.label,
                                "styles": {
                                    "align": "left",
                                    "fontType": "fontA"
                                }
                            });
                        }
                    }

                }


                // Total items → items that send to kot after clicking order/takeaway button
                datas.push(
                    {
                        "type": "text",
                        "data": "Total Items : " + total_quantity,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    }
                );

                // Company name
                datas.push(
                    {
                        "type": "text",
                        "data": receipt.company.name,
                        "styles": {
                            "bold": false,
                            "align": "center",
                            "fontType": "fontA"
                        }
                    }
                );

                return {
                    "type": "print_dynamic_receipt",
                    "datas": datas
                };
            },

            get_receipt_bluetooth_printer_for_reprint_receipt(receipt){
                receipt.is_from_reprint_receipt = true;
                return this.get_receipt_bluetooth_printer_for_print_receipt(receipt);
            },

            get_receipt_bluetooth_printer_for_print_receipt(receipt,receipt_template=false,receipt_template_id=false){
                let self = this;
                let datas = [];
                if(!receipt_template){
                    receipt_template = this.pos.get_receipt_template(receipt_template_id);
                }
                let receipt_order = receipt.export_for_printing()
                if (this.qrCodeLink && receipt?.screen_data?.value?.name != "ReceiptScreen") {
                    console.log('Receipt', receipt)
                    const floorAndTable = `${receipt?.table?.floor?.name} / ${receipt?.table?.name}`
                    const orderNumber = `No Order: ${receipt?.name}`
                    let date = new Date();
                    if(receipt.date){
                        date = new Date(receipt.date.replace(" ", "T"));
                    }
                    const orderDateLocaleDate = date.toLocaleString('en-US', { day: "2-digit" }) + " " + date.toLocaleString('en-US', { month: "short" }) + " " + date.toLocaleString('en-US', { year: "numeric" })
                    const orderDateLocaleTime = date.toLocaleString('en-US', { timeStyle: "short", hour12: true });
                    const orderDate = `Date: ${orderDateLocaleDate} ${orderDateLocaleTime}`
                    const orderServer = `Server: ${receipt?.cashier?.name}`
                    let orderMember = false
                    if (receipt?.client?.name) {
                        orderMember = `Member: ${receipt?.client?.name}`
                    }

                    datas.push(
                        {
                            "type": "text",
                            "data": String(floorAndTable),
                            "styles": {
                                "bold": true,
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                        {
                            "type": "hr",
                            "data": {
                                "linesAfter": 0
                            }
                        },
                        {
                            "type": "text",
                            "data": String(orderNumber),
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        },
                        {
                            "type": "text",
                            "data": String(orderDate),
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        },
                        {
                            "type": "text",
                            "data": String(orderServer),
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        }
                    );
                    if (orderMember) {
                        datas.push(
                            {
                                "type": "text",
                                "data": String(orderMember),
                                "styles": {
                                    "align": "left",
                                    "fontType": "fontA"
                                }
                            }
                        )
                    }
                    datas.push(
                        {
                            "type": "hr",
                            "data": {
                                "linesAfter": 0
                            }
                        },
                    )

                    datas.push(
                        {
                            "type": "text",
                            "data": String('-----Scan This Barcode at the Cashier-----'),
                            "styles": {
                                "bold": true,
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                        {
                            "type": "hr",
                            "data": {
                                "linesAfter": 0
                            }
                        }
                    )

                    // QR Code
                    datas.push({
                        "type": "qrcode",
                        "data": this.qrCodeLink,
                        "size": "Size4",
                        "styles": {
                            "align": "center",
                        }
                    });

                    // Custom line break
                    datas.push(
                        {
                            "type": "feed",
                            "data": 1
                        },
                        {
                            "type": "feed",
                            "data": 1
                        }
                    );

                    datas.push(
                        {
                            "type": "cut",
                            "data": "full"
                        }
                    );
                    return { "type": "print_dynamic_receipt", "datas": datas };
                }

                let total_discount_wo_pricelist = receipt.get_total_discount_wo_pricelist();
                let rounding_order = receipt.get_total_with_tax() - receipt.get_total_with_tax_without_rounding() - receipt.total_mdr_amount_customer
                let total = receipt.get_total_with_tax() 
                let mdr_customer = receipt.total_mdr_amount_customer
                let taxtotal = receipt.get_total_with_tax_without_rounding() - receipt.get_total_without_tax()

                let subtotal = receipt_order.subtotal_without_tax;
                let total_with_tax = receipt.get_total_with_tax();
                let total_without_tax = receipt.get_total_without_tax();
                let total_tax = receipt.get_total_tax();
                let total_paid = receipt.get_total_paid();
                let total_discount = receipt.get_total_discount();
                let tax_details = receipt.get_tax_details();
                let change = receipt.locked ? receipt.amount_return : receipt.get_change();

                let qrcodelink = null;
                if(receipt.backendOrder){
                    qrcodelink = window.origin + '/pos/fnb/scanQrCode?order_id=' + receipt.backendOrder.id;
                }
                // <img t-att-src="'/report/barcode/?type=QR&amp;value='+receipt.name+'&amp;width=80&amp;height=80'" />
                qrcodelink = window.origin + '/report/barcode/?type="QR"&value=' + receipt.name + '&width=80&height=80';

                let date_order = '';
                if(receipt.date_order){
                    date_order = receipt.date_order;
                }
                if(!receipt.date_order){
                    date_order = moment(receipt.formatted_validation_date, 'MM/DD/YYYY HH:mm:ss').format('DD MMM YYYY hh:mm A');
                }
                let logo_base64 = this.pos.company_logo_base64.split('base64,')[1];
                if (receipt_template?.branch_id) {
                    // http://localhost:8074/web/image?model=res.branch&id=1&field=logo
                    const baseUrl = window.location.origin;
                    const imageUrl = `${baseUrl}/web/image?model=res.branch&id=${receipt_template.branch_id[0]}&field=logo`;
                    // let imageUrl = 'http://localhost:8074/web/image?model=res.branch&id=' + receipt_template.branch_id[0] + '&field=logo';
                    console.log('Processing image URL:', imageUrl);
                    this.getBase64FromUrl(imageUrl).then(
                        (base64) => {
                            logo_base64 = base64;
                            // console.log('Logo base64:', logo_base64);
                        }
                    )
                }

                var paymentlines = [];
                var _paymentlines = receipt.paymentlines.models
                    .filter(function (paymentline) {
                        return !paymentline.is_change;
                    })
                    .map(function (paymentline) {
                        return paymentline.export_for_printing();
                    });
                for (let i = _paymentlines.length - 1; i >= 0; i--) {
                    let line = _paymentlines[i];
                    paymentlines.push({
                        'cid': line.cid,
                        'name': line.name,
                        'amount': self.pos.format_currency(line.amount),
                    });
                }

                let barcode_arr = []
                if(receipt.ean13){
                    barcode_arr = receipt.ean13.split('').map(Number);
                }
                
                // Header
                datas.push(
                    {
                        "type": "image",
                        "align": "center",
                        "data": logo_base64,
                    },
                    {
                        "type": "text",
                        "data": String(this.pos.company.name),
                        "styles": {
                            "bold": true,
                            "align": "center",
                            "fontType": "fontA"
                        }
                    }
                );


                if(receipt.pos.config.pos_branch_name){
                    datas.push(
                        {
                            "type": "text",
                            "data": String(receipt.pos.config.pos_branch_name),
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                if(receipt.pos.config.branch_street || receipt.pos.config.branch_street_2){
                    datas.push(
                        {
                            "type": "text",
                            "data": '-----',
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                if(receipt.pos.config.branch_street){
                    datas.push(
                        {
                            "type": "text",
                            "data": String(receipt.pos.config.branch_street),
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                if(receipt.pos.config.branch_street_2){
                    datas.push(
                        {
                            "type": "text",
                            "data": String(receipt.pos.config.branch_street_2),
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                if(receipt.pos.config.branch_telephone){
                    datas.push(
                        {
                            "type": "text",
                            "data": String(receipt.pos.config.branch_telephone),
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                if(receipt_template.receipt_header_text && receipt_template.is_need_header){
                    datas.push(
                        {
                            "type": "text",
                            "data": String(receipt_template.receipt_header_text),
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        },
                    );
                }

                
                // Order information
                datas.push(
                    {
                        "type": "text",
                        "data": "Date : " + date_order,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    },
                    {
                        "type": "text",
                        "data": "No Order : " + receipt.name,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    },


                );

                // Server (IF FnB)
                if(receipt_template.is_table_guest_info){

                    datas.push({
                        "type": "text",
                        "data": "Server : " + receipt.cashier.name || '',
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });
                    
                }


                datas.push(
                    {
                        "type": "text",
                        "data": "Cashier : " + receipt.cashier.name || '',
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    }

                );


                

                // Feed & Line break
                datas.push(
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                );

                //Table & guest (IF FnB)
                if(receipt_template.is_table_guest_info && receipt.order_method != 'takeaway'){
                    if(receipt.table){
                        datas.push(
                            {
                                "type": "text",
                                "data": "Table : " + receipt.table.name,
                                "styles": {
                                    "align": "left",
                                    "fontType": "fontA"
                                }
                            },
                            {
                                "type": "text",
                                "data": "Guest : " + receipt.customer_count,
                                "styles": {
                                    "align": "left",
                                    "fontType": "fontA"
                                }
                            }
                        );
                        // Feed & Line break
                        datas.push(
                            {
                                "type": "hr",
                                "data": {
                                    "linesAfter": 1
                                }
                            },
                        );
                    }
                }

                /** ====================== Start Order Line (per row and feed) ====================== **/
                
                function bom_combo_display_name(rec){
                    let display_name = rec.product_id[1];
                    if(self.pos.config && self.pos.config.display_product_name_without_product_code){
                        return display_name.replace(/[\[].*?[\]] */, '');
                    }
                    return display_name;
                }
                let row_orderline = [];
                var total_item_line = 0

                datas.push({
                        "type": "row",
                        "data": [
                            {
                                "type": "column",
                                "data": "Qty",
                                "width": 3,
                                "styles": {
                                    "align": "left"
                                }
                            },
                            {
                                "type": "column",
                                "data": 'Description',
                                "width": 5,
                                "styles": {
                                    "align": "left"
                                }
                            },
                            {
                                "type": "column",
                                "data": 'Total Price',
                                "width": 4,
                                "styles": {
                                    "align": "right"
                                }
                            } 
                        ]
                });
                // Feed
                datas.push({
                    "type": "feed",
                    "data": 1
                });
                receipt.orderlines.each(function(orderline){
                    let line = orderline.export_for_printing();
                    if(line.is_service_charge){
                        return; 
                    }
                    total_item_line+=1
                    let line_product_name = line.full_product_name;
                    if(line.pos_coupon_reward_description){
                        line_product_name = line.pos_coupon_reward_description + ' (Coupon)';
                    }

                    // a. Product name & If with Code
                    datas.push({
                        "type": "row",
                        "data": [
                            {
                                "type": "column",
                                "data": String(line_product_name),
                                "width": 12,
                                "styles": {
                                    "align": "left"
                                }
                            }
                        ]
                    });

                    // b. If Lot/serial
                    if(line.lot_sn){
                        datas.push({
                            "type": "row",
                            "data": [
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 2,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": String(line.lot_sn),
                                    "width": 10,
                                    "styles": {
                                        "align": "left"
                                    }
                                }
                            ]
                        });
                    }
                    
                    // c. UOM & price
                    const isShowPrice = receipt_template.is_show_product_price
                    if (isShowPrice) {
                        datas.push({
                            "type": "row",
                            "data": [
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 2,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": line.quantity + ' ' + line.unit_name + ' x ' + self.pos.format_currency(line.price_with_pricelist),
                                    "width": 6,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": String(self.pos.format_currency(line.price_with_pricelist * line.quantity)),
                                    "width": 4,
                                    "styles": {
                                        "align": "right"
                                    }
                                } 
                            ]
                        });
                    } else {
                        datas.push({
                            "type": "row",
                            "data": [
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 2,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": line.quantity + ' ' + line.unit_name + ' x ',
                                    "width": 6,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 4,
                                    "styles": {
                                        "align": "right"
                                    }
                                } 
                            ]
                        });
                    }

                    // IF Combo
                    if(line.pos_combo_options){
                        for(let option of line.pos_combo_options){
                            console.log('combo.option:::::', option)
                            datas.push(
                                {
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "",
                                            "width": 4,
                                            "containsChinese": false,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": String(bom_combo_display_name(option)),
                                            "width": 8,
                                            "containsChinese": false,
                                            "styles": {
                                                "align": "left"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "",
                                            "width": 6,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": '1 ' + option.uom_id[1] + " x " + self.pos.format_currency(option.extra_price),
                                            "width": 3,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": String(self.pos.format_currency(option.extra_price * 1)),
                                            "width": 3,
                                            "styles": {
                                                "align": "right"
                                            }
                                        }
                                    ],
                                }
                            );
                        }
                    }
                    
                    // IF BOM
                    if(line.bom_components){
                        let bom_components = [];
                        for(let com of line.bom_components){
                            let label = '';
                            if(com.is_extra){
                                if(com.checked){
                                    label = 'Extra ' + bom_combo_display_name(com);
                                }
                            }else{
                                if(!com.checked){
                                    label = 'No ' + bom_combo_display_name(com);
                                }
                            }
                            bom_components.push({ label: label }); 
                            datas.push({
                                "type": "row",
                                "data": [
                                    {
                                        "type": "column",
                                        "data": "",
                                        "width": 4,
                                        "styles": {
                                            "align": "left"
                                        }
                                    },
                                    {
                                        "type": "column",
                                        "data": label,
                                        "width": 8,
                                        "styles": {
                                            "align": "left"
                                        }
                                    }
                                ]
                            });
                            
                        }
                    }

                    // IF Discount
                    var promotion_discount_total = 0
                    if(line.promotion_stack_apply && line.promotion_stack_apply.length > 0){

                        line.promotion_stack_apply.forEach(function(promotion_rec){
                            if(receipt_template.is_receipt_disc_in_orderline && receipt_template.is_show_discount_detail && line.all_total_discount && !promotion_rec.is_gift){
                                var text_discount = 'Discount ('+ promotion_rec.name+')'
                                if(promotion_rec.promotion_type=='percentage'){
                                    text_discount+=' '+promotion_rec.promotion_discount_int+'%'
                                }
                                var discount_value_showing = promotion_rec.discount_value_showing
                                if(discount_value_showing<0){
                                    discount_value_showing = self.pos.format_currency(discount_value_showing)
                                }
                                else{
                                    discount_value_showing = '('+self.pos.format_currency(discount_value_showing)+')'
                                }
                                promotion_discount_total+=  promotion_rec.discount_value_showing
           



                                datas.push({
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "",
                                            "width": 2,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": text_discount,
                                            "width": 6,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": discount_value_showing,
                                            "width": 4,
                                            "styles": {
                                                "align": "right"
                                            }
                                        }
                                    ]
                                });
                            }
                        })

                        if(line.promotion_gift){
                            line.promotion_stack_apply.forEach(function(promotion_rec){
                                if(promotion_rec.is_gift){
                                    datas.push({
                                        "type": "row",
                                        "data": [
                                            {
                                                "type": "column",
                                                "data": "",
                                                "width": 2,
                                                "styles": {
                                                    "align": "left"
                                                }
                                            },
                                            {
                                                "type": "column",
                                                "data": 'Free Item ('+ promotion_rec.name+')',
                                                "width": 10,
                                                "styles": {
                                                    "align": "left"
                                                }
                                            },
                                        ]
                                    });
                                }
                            })
                        }
                            
                    }
                    var other_discount = line.all_total_discount - promotion_discount_total
                    if(receipt_template.is_receipt_disc_in_orderline && other_discount  && receipt_template.is_show_discount_detail && Math.round(other_discount) != 0){
                        var text_discount = 'Discount'
                        if(line.pos_coupon_reward_discount){
                            text_discount+=' (Coupon)'
                        }
                        datas.push({
                            "type": "row",
                            "data": [
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 2,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": text_discount,
                                    "width": 6,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": self.pos.format_currency(other_discount),
                                    "width": 4,
                                    "styles": {
                                        "align": "right"
                                    }
                                }
                            ]
                        });
                    }

                    if(receipt_template.is_receipt_disc_in_orderline && !receipt_template.is_show_discount_detail && line.all_total_discount){
                        var text_discount = 'Discount'
                        if(line.pos_coupon_reward_discount){
                            text_discount+=' (Coupon)'
                        }
                        datas.push({
                            "type": "row",
                            "data": [
                                {
                                    "type": "column",
                                    "data": "",
                                    "width": 2,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": text_discount,
                                    "width": 6,
                                    "styles": {
                                        "align": "left"
                                    }
                                },
                                {
                                    "type": "column",
                                    "data": self.pos.format_currency(line.all_total_discount),
                                    "width": 4,
                                    "styles": {
                                        "align": "right"
                                    }
                                }
                            ]
                        });
                    }
                    


                    // Feed
                    datas.push({
                        "type": "feed",
                        "data": 1
                    });
                }); 

                
                /** ====================== End Order Line (per row and feed) ====================== **/

                // Total items
                datas.push(
                    {
                        "type": "text",
                        "data": "Total Items : " +total_item_line ,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    }
                );

                // Line break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        },
                    },

                );


                /** ====================== Start Calculation ====================== **/
                // Subtotal

                datas.push({
                    "type": "text",
                    "data": "Subtotal : " + self.pos.format_currency(subtotal),
                    "styles": {
                        "align": "right",
                        "fontType": "fontA"
                    }
                });

               if(receipt_order.taxdetails && Object.keys(receipt_order.taxdetails).length != 0){
                    for (let txo in receipt_order.taxdetails){
                        datas.push({
                            "type": "text",
                            "data": "Tax (" + txo + ") : " + self.pos.format_currency(receipt_order.taxdetails[txo]),
                            "styles": {
                                "align": "right",
                                "fontType": "fontA"
                            }
                        });
                    }
               }
               if(receipt_template.is_include_service_charge){
                        datas.push({
                            "type": "text",
                            "data": "Service Charge : " + self.pos.format_currency(receipt_order.service_charge),
                            "styles": {
                                "align": "right",
                                "fontType": "fontA"
                            }
                        });
               }
               if(!receipt_template.is_receipt_disc_in_orderline && receipt_order.total_discount_wo_pricelist){
                    datas.push({
                        "type": "text",
                        "data": "Discount : " + self.pos.format_currency(receipt_order.total_discount_wo_pricelist),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
               }
               if(receipt_order.rounding_order){
                    var amount_rounding_text = self.pos.format_currency(receipt_order.rounding_order)
                    if(receipt_order.rounding_order<0){
                        var amount_rounding_text = '('+self.pos.format_currency(receipt_order.rounding_order)+')'
                    }
                    datas.push({
                        "type": "text",
                        "data": "Rounding : " + amount_rounding_text,
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
               }
               if(receipt_order.mdr_customer){
                    datas.push({
                        "type": "text",
                        "data": "MDR : " + self.pos.format_currency(-receipt_order.mdr_customer),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
               }
                /** ====================== Start Calculation ====================== **/


                // Line break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
   
                );


                /** ====================== Start Grand total and payment ====================== **/
                // Grand total
                datas.push({
                    "type": "text",
                    "data": "Grand Total : " + self.pos.format_currency(receipt_order.total),
                    "styles": {
                        "align": "right",
                        "fontType": "fontA"
                    }
                });

                if(receipt_order.voucher_discount_amount && receipt_order.voucher_discount_amount > 0){
                    datas.push({
                        "type": "text",
                        "data": "Voucher : " + self.pos.format_currency(receipt_order.voucher_discount_amount),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                }
                // Payment → can have many payment
                receipt_order.paymentlines.forEach(function(pline){
                    datas.push({
                        "type": "text",
                        "data": pline.name + " : " + self.pos.format_currency(pline.amount),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                })

                // Change → if have change
                if(receipt_order.change){
                    datas.push({
                        "type": "text",
                        "data": "Change : " + self.pos.format_currency(receipt_order.change),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                }
                

                // Include tax → if tax included in orderline
                if(receipt_template.is_receipt_tax_include_orderline ){
                    datas.push({
                        "type": "text",
                        "data": "VAT Amount : " + self.pos.format_currency(receipt_order.taxtotal),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                }

                if(receipt_template.is_receipt_disc_in_orderline && receipt_order.total_discount_wo_pricelist ){
                    datas.push({
                        "type": "text",
                        "data": "Include Discount : " + self.pos.format_currency(receipt_order.total_discount_wo_pricelist),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                }
                if(receipt_template.is_show_tips && receipt_order.tips_amount ){
                    datas.push({
                        "type": "text",
                        "data": "Tips : " + self.pos.format_currency(receipt_order.tips_amount),
                        "styles": {
                            "align": "right",
                            "fontType": "fontA"
                        }
                    });
                }
                    
                /** ====================== End Grand total and payment ====================== **/


                // Line break
                datas.push(
           
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        }
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );


                /** ====================== Start Member information ====================== **/
                // Member name
                let client = receipt.get_client();
                if(client && receipt_template.is_receipt_member_info){
                    datas.push({
                        "type": "text",
                        "data": "Loyalty Member : " + client.name,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });

                    let member_opening_point = 0;
                    let member_current_point = 0;
                    if(receipt.member_opening_point){
                        member_opening_point = receipt.member_opening_point;
                    }
                    if(receipt.member_current_point){
                        member_current_point = receipt.member_current_point;
                    }
                    // Opening point
                    datas.push({
                        "type": "text",
                        "data": "Opening Points : " + Math.floor((member_opening_point)),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });

                    // Plus point
                    datas.push({
                        "type": "text",
                        "data": "Plus Points : " +Math.floor(( receipt.plus_point)),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });

                    // Redeem point
                    datas.push({
                        "type": "text",
                        "data": "Redeem Points : " + Math.floor((receipt.redeem_point)),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    })

                    // Current Point
                    datas.push({
                        "type": "text",
                        "data": "Current Points : " + Math.floor(member_current_point),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    });
                }
                /** ====================== End Member Information ====================== **/
                

                if(receipt_template.is_display_barcode_ean13){
                    // Barcode
                    datas.push({
                        "type": "barcode",
                        "barcode_type": "ean13",
                        "data": barcode_arr,
                    });

                    // Line break
                    datas.push(
                        {
                            "type": "feed",
                            "data": 1
                        },
                    );
                }
                
                if(receipt_template.is_qrcode_link && qrcodelink){
                    // QR Code
                    datas.push({
                        "type": "qrcode",
                        "data": qrcodelink,
                        "size": "Size4"
                    });

                    // Line break
                    datas.push(
                        {
                            "type": "feed",
                            "data": 1
                        },
                    );
                }

                
                

                // IF from reprint receipt
                if(receipt.is_from_reprint_receipt){
                    datas.push(
               
                        {
                            "type": "text",
                            "data": "Reprinted receipt",
                            "styles": {
                                "align": "left",
                                "fontType": "fontA"
                            }
                        },
      
                    );
                    datas.push(
                        {
                            "type": "feed",
                            "data": 1
                        },
                    );
                }

                // Include savings summary
                if(receipt_template.is_receipt_savings_summary && receipt_template.savings_summary_text){
                    let savings_amount = receipt.get_savings_amount();
                    if(savings_amount > 0){
                        let savings_summary = receipt_template.savings_summary_text.replace('()', self.pos.format_currency(savings_amount));
                        datas.push({
                            "type": "text",
                            "data": savings_summary,
                            "styles": {
                                "align": "center",
                                "fontType": "fontA"
                            }
                        });

                        // Line break
                        datas.push(
                            {
                                "type": "feed",
                                "data": 1
                            },
                        );
                    }
                }

                if (receipt_template.is_show_order_qrcode && qrcodelink) {
                    // QR Code
                    datas.push({
                        "type": "qrcode",
                        "data": qrcodelink,
                        "size": "Size4"
                    });

                    // Line break
                    datas.push(
                        {
                            "type": "feed",
                            "data": 1
                        },
                    );
                }

                if(receipt_order.arr_generate_voucher_template && receipt_order.arr_generate_voucher_template.length>0){
                    receipt_order.arr_generate_voucher_template.forEach(function(generate_voucher_template){
                        if(receipt_template.is_voucher_receipt && receipt_template.voucher_receipt_display=='Barcode' && generate_voucher_template.voucher_number_use){
                            datas.push({
                                "type": "barcode",
                                "barcode_type": "ean13",
                                "data": window.origin +'/report/barcode/?type=EAN13&value='+generate_voucher_template.voucher_number_use+'&width=150&height=50',
                            });

                            // Line break
                            datas.push(
           
                                {
                                    "type": "hr",
                                    "data": {
                                        "linesAfter": 1
                                    }
                                },
                                {
                                    "type": "feed",
                                    "data": 1
                                }
                            );
                        }
                        if(receipt_template.is_voucher_receipt && receipt_template.voucher_receipt_display=='QR Code' && generate_voucher_template.voucher_number_use){
                            datas.push({
                                "type": "qrcode",
                                "data":  window.origin +'/report/barcode/?type=QR&value='+generate_voucher_template.voucher_number_use+'&width=80&height=80',
                                "size": "Size4"
                            });

                            // Line break
                            datas.push(
           
                                {
                                    "type": "hr",
                                    "data": {
                                        "linesAfter": 1
                                    }
                                },
                                {
                                    "type": "feed",
                                    "data": 1
                                }
                            );
                        }
                        if( generate_voucher_template.voucher_number_use){
                            datas.push({
                                "type": "row",
                                "data": [
                                    {
                                        "type": "column",
                                        "data": "Voucher Code",
                                        "width": 6,
                                        "styles": {
                                            "align": "left"
                                        }
                                    },
                                    {
                                        "type": "column",
                                        "data": generate_voucher_template.voucher_number_use,
                                        "width": 6,
                                        "styles": {
                                            "align": "right"
                                        }
                                    },

                                ]
                            });

                            datas.push(
           
                                {
                                    "type": "hr",
                                    "data": {
                                        "linesAfter": 1
                                    }
                                },
                                {
                                    "type": "feed",
                                    "data": 1
                                }
                            );

                            datas.push({
                                "type": "row",
                                "data": [
                                    {
                                        "type": "column",
                                        "data": "Voucher Amount",
                                        "width": 6,
                                        "styles": {
                                            "align": "left"
                                        }
                                    },
                                    {
                                        "type": "column",
                                        "data": generate_voucher_template.generate_voucher_value,
                                        "width": 6,
                                        "styles": {
                                            "align": "right"
                                        }
                                    },

                                ]
                            });

                                

                            if(generate_voucher_template.voucher_min_amount){
                                datas.push(
               
                                    {
                                        "type": "hr",
                                        "data": {
                                            "linesAfter": 1
                                        }
                                    },
                                    {
                                        "type": "feed",
                                        "data": 1
                                    }
                                );

                                datas.push({
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "Minimum Purchase Amount",
                                            "width": 6,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": generate_voucher_template.voucher_min_amount,
                                            "width": 6,
                                            "styles": {
                                                "align": "right"
                                            }
                                        },

                                    ]
                                });
                            }

                            if(generate_voucher_template.brands_name_voucher){
                                datas.push(
               
                                    {
                                        "type": "hr",
                                        "data": {
                                            "linesAfter": 1
                                        }
                                    },
                                    {
                                        "type": "feed",
                                        "data": 1
                                    }
                                );
                                
                                datas.push({
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "Brands",
                                            "width": 6,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": generate_voucher_template.brands_name_voucher,
                                            "width": 6,
                                            "styles": {
                                                "align": "right"
                                            }
                                        },

                                    ]
                                });
                            }


                            if(generate_voucher_template.voucher_expired_date){
                                datas.push(
               
                                    {
                                        "type": "hr",
                                        "data": {
                                            "linesAfter": 1
                                        }
                                    },
                                    {
                                        "type": "feed",
                                        "data": 1
                                    }
                                );
                                
                                datas.push({
                                    "type": "row",
                                    "data": [
                                        {
                                            "type": "column",
                                            "data": "Expired Date",
                                            "width": 6,
                                            "styles": {
                                                "align": "left"
                                            }
                                        },
                                        {
                                            "type": "column",
                                            "data": generate_voucher_template.voucher_expired_date,
                                            "width": 6,
                                            "styles": {
                                                "align": "right"
                                            }
                                        },

                                    ]
                                });
                            }




                        }
                    })
                }

                // Footer
                if(receipt_template.receipt_footer_text){
                    datas.push({
                        "type": "text",
                        "data": receipt_template.receipt_footer_text,
                        "styles": {
                            "align": "center",
                            "fontType": "fontA"
                        }
                    });
                }
                // Custom line break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "feed",
                        "data": 1
                    }
                );

                datas.push(
                    {
                        "type": "cut",
                        "data": "full"
                    }
                );

                return { "type": "print_dynamic_receipt", "datas": datas };
            },

            getLoggerAppsCheckerReceiptObj(receipt, receiptTemplate=false){
                let self = this;
                let datas = [];
                if(!receiptTemplate){
                    // Return Error Directly
                    return Gui.showPopup('ErrorPopup', {
                        title: _t('No Receipt Template Found'),
                        body: _t('Please Set up your printer receipt template.'),
                    });
                }

                const floorAndTable = `${receipt?.table?.floor?.name} / ${receipt?.table?.name}`
                const orderNumber = `No Order: ${receipt?.name}`
                let date = new Date();
                if(receipt.date){
                    date = new Date(receipt.date.replace(" ", "T"));
                }
                const orderDateLocaleDate = date.toLocaleString('en-US', { day: "2-digit" }) + " " + date.toLocaleString('en-US', { month: "short" }) + " " + date.toLocaleString('en-US', { year: "numeric" })
                const orderDateLocaleTime = date.toLocaleString('en-US', { timeStyle: "short", hour12: true });
                const orderDate = `Date: ${orderDateLocaleDate} ${orderDateLocaleTime}`
                const orderServer = `Server: ${receipt.cashier.name}`
                datas.push(
                    {
                        "type": "text",
                        "data": String(floorAndTable),
                        "styles": {
                            "bold": true,
                            "align": "center",
                            "fontType": "fontA"
                        }
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 0
                        }
                    },
                    {
                        "type": "text",
                        "data": String(orderNumber),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    },
                    {
                        "type": "text",
                        "data": String(orderDate),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    },
                    {
                        "type": "text",
                        "data": String(orderServer),
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 0
                        }
                    },
                );

                /** ====================== Start Order Line (per row and feed) ====================== **/
                let totalItems = 0
                let existingProductCategory = []
                receipt.orderlines.each(function(orderline){
                    const kitchenReceiptLines = receipt?.screen_data?.value?.props?.orderReceipt?.new;
                    if (!kitchenReceiptLines) return;
                    kitchenReceiptLines.forEach(function(kitchenReceiptLine) {
                        if (orderline.uid === kitchenReceiptLine.uid) {
                            // Your logic here when the UID matches
                            // Example: console.log('Matched:', orderline, kitchenReceiptLine);
                            let lineProductCategoryName;
                            let line = orderline.export_for_printing();
                            let lineProductName = line.full_product_name;
                            let isShowProductCategory = true
                            let isShowProduct = receiptTemplate.is_show_checker_product
                            let isCombo = receiptTemplate.is_receipt_combo_info
                            // Check if this category is registered inside the receipt template
                            // [
                            //   100, 120
                            // ]
                            if (isShowProduct) {
                                lineProductName = `${line.quantity}X ${line.full_product_name}`
                            }
        
                            const registeredProductCategory = receiptTemplate.pos_product_category_id
                            if (line.pos_categ_id && registeredProductCategory && registeredProductCategory.length > 0) {
                                if (registeredProductCategory.includes(line.pos_categ_id[0])) {
                                    if (!isShowProduct) {
                                        lineProductCategoryName = `${line.quantity}X ${line.pos_categ_id[1]}`
                                    } else {
                                        lineProductCategoryName = `${line.pos_categ_id[1]}`
                                    }
                                } else {
                                    lineProductCategoryName = ''
                                    isShowProductCategory = false
                                }
                            }
                            if(!registeredProductCategory || registeredProductCategory.length==0){
                                if (!isShowProduct) {
                                    lineProductCategoryName = `${line.quantity}X ${line.pos_categ_id[1]}`
                                } else {
                                    lineProductCategoryName = `${line.pos_categ_id[1]}`
                                }
                            }
        
                            if (isShowProductCategory) {
                                totalItems += 1
                                if (!existingProductCategory.includes(lineProductCategoryName) || !isShowProduct) {
                                    datas.push({
                                        "type": "row",
                                        "data": [
                                            {
                                                "type": "column",
                                                "data": String(lineProductCategoryName),
                                                "width": 12,
                                                "styles": {
                                                    "align": "left"
                                                }
                                            },
                                        ]
                                    });
                                    existingProductCategory.push(lineProductCategoryName)
                                }
        
                                if (isShowProduct) {
                                    datas.push({
                                        "type": "row",
                                        "data": [
                                            {
                                                "type": "column",
                                                "data": String(lineProductName),
                                                "width": 12,
                                                "styles": {
                                                    "align": "left"
                                                }
                                            },
                                        ]
                                    });
                                }
                                if (isCombo && line.combo_items && line.combo_items.length) {
                                    for (let combo_item of line.combo_items) {
                                        totalItems += 1
                                        // let combo_item_name = `${combo_item.quantity}X ${combo_item.product_id[1]}`
                                        let combo_item_name = `1X ${combo_item.product_id[1]}`
                                        if (combo_item.modifiers && combo_item.modifiers.length > 0) {
                                            combo_item_name += ' (' + combo_item.modifiers.map(modifier => modifier.name).join(', ') + ')';
                                        }
                                        datas.push({
                                            "type": "row",
                                            "data": [
                                                {
                                                    "type": "column",
                                                    "data": String(combo_item_name),
                                                    "width": 10,
                                                    "styles": {
                                                        "align": "left"
                                                    }
                                                },
                                            ]
                                        });
                                    }
                                }
                                // Feed
                                datas.push({
                                    "type": "feed",
                                    "data": 1
                                });
                            }
                        }
                    });
                }); 
                /** ====================== End Order Line (per row and feed) ====================== **/

                // Total items
                datas.push(
                    {
                        "type": "text",
                        "data": "Total Items: " + totalItems,
                        "styles": {
                            "align": "left",
                            "fontType": "fontA"
                        }
                    }
                );

                // Line break
                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                    {
                        "type": "hr",
                        "data": {
                            "linesAfter": 1
                        },
                    },
                );

                // Footer
                if(receiptTemplate.receipt_footer_text){
                    datas.push({
                        "type": "text",
                        "data": receiptTemplate.receipt_footer_text,
                        "styles": {
                            "align": "center",
                            "fontType": "fontA"
                        }
                    });
                }

                datas.push(
                    {
                        "type": "feed",
                        "data": 1
                    },
                );

                datas.push(
                    {
                        "type": "cut",
                        "data": "full"
                    }
                );

                return { "type": "print_dynamic_receipt", "datas": datas };
            },
            async getBase64FromUrl(url) {
                const response = await fetch(url);
                const blob = await response.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }
    });


});