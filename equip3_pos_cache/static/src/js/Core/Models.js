odoo.define('equip3_pos_cache.Models', function (require) {
"use strict";

    const models = require('point_of_sale.models');
    const pos_masterdata_models = require('equip3_pos_masterdata.model');
    const pos_general_models = require('equip3_pos_general.models');
    const rpc = require('pos.rpc');
    const core = require('web.core');
    const _t = core._t;
    const {posbus} = require('point_of_sale.utils');

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);
        },

        showPopupLoadPosError(val){
            let $popup = $(`<div>
                <div class="popups">
                    <div role="dialog" class="modal-dialog">
                        <div class="popup popup-error">
                            <p class="title">${val.title}</p>
                            <p class="body" style="min-height:170px;display:flex;align-items:center;justify-content:center;">
                                <span>${val.body}</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>`);
            $('body .pos').append($popup);
            setTimeout(()=>{ location.reload(); }, 10000);
        },

        get_pos_cache_model_data: async function (params){
            /** TODO: make request to POS Cache SDK
                e.g: params
                { 
                    model: 'product.product', 
                    domain:[], 
                    offest: 0, 
                    limit: 0, 
                    order: 'id asc' 
                }
            */
            let url = this.db.pos_cache_sdk_localhost_link + '/model'; 
            let dataJSON = JSON.stringify(params);
            return new Promise(function (resolve, reject) {
                let xhr = new XMLHttpRequest();
                xhr.open('POST', url);
                xhr.onload = function () {
                    if (this.status >= 200 && this.status < 300) {
                        if(xhr.response && JSON.parse(xhr.response).status == 'success'){
                            return resolve(xhr.response);
                        }
                    }
                    if(xhr.statusText == ''){
                        console.error(_t("Failed connect to POS Cache SDK.\nPlease start service first!"));
                    }
                    return resolve({
                        'status': 'error',
                        'message': 'Cannot connect to POS Cache SDK: \n' + xhr.statusText,
                        'result': [],
                        'response': {
                            status: this.status,
                            statusText: xhr.statusText
                        }
                    });
                };
                xhr.onerror = function () {
                    if(xhr.statusText == ''){
                        console.error(_t("Failed connect to POS Cache SDK.\nPlease start service first!"));
                    }
                    resolve({
                        'status': 'error',
                        'message': 'Cannot connect to POS Cache SDK! \n' + xhr.statusText,
                        'result': [],
                        'response': {
                            status: this.status,
                            statusText: xhr.statusText
                        }
                    });
                };
                xhr.send(dataJSON);
            });
        },

        pos_cache_filter_base_on_domain: function(model, result){
            let self = this;
            // TODO: filter result
            if(model.model == 'res.company'){
                result = result.filter(o=>o.id==self.session.user_context.allowed_company_ids[0]);
            }
            if(model.model == 'account.tax'){
                result = result.filter(o=>!o.company_id || (o.company_id && o.company_id[0] == self.company.id));
            }
            if(model.model == 'pos.session'){
                if(model.label == 'POS Sessions'){
                    result = result.filter(function(o){
                        if(o.rescue && o.rescue == true && ['opening_control','opened'].includes(o.state) == false){
                            return false
                        }
                        if(odoo.session_info.config.pos_session_id == o.id){
                            return true;
                        }
                        return false;
                    });
                } else {
                    result = result.filter(function(o){
                        if(o.rescue && o.rescue == true && ['opening_control','opened'].includes(o.state) == false){
                            return false
                        }
                        if(odoo.session_info.config.pos_session_id == o.id && o.state == odoo.session_info.config.pos_session_state){
                            return true;
                        }
                        return false;
                    });
                }
            }
            if(model.model == 'pos.config'){
                if(model.label == 'POS Configuration'){
                    //pass
                }else{
                    result = result.filter(o=>o.id==odoo.session_info.config.id && moment(o.write_date).isSame(odoo.session_info.config.write_date));
                }
            }
            if(model.model == 'stock.picking.type'){
                if(model.label == 'Stock Picking Type'){
                    result = result.filter(o=>o.id==self.config.picking_type_id[0] || self.config.multi_stock_operation_type_ids.includes(o.id));
                }else{
                    result = result.filter(o=>o.id==self.config.picking_type_id[0]);
                }
            }
            if(model.model == 'stock.picking'){ 
                result = result.filter(o=>o.is_picking_combo==true && o.pos_order_id!=null);
            }
            if(model.model == 'stock.location'){
                result = result.filter(o=>o.id==self.config.stock_location_id[0] || self.config.stock_location_ids.includes(o.id) || self.default_location_src_of_picking_type_ids.includes(o.id));
            }
            if(model.model == 'stock.move'){
                result = result.filter(o=>self.combo_picking_ids.includes(o.picking_id[0]));
            }
            if(model.model == 'product.pricelist'){
                if (self.config.use_pricelist) {
                    result = result.filter(o=>self.config.available_pricelist_ids.includes(o.id));
                } else {
                    result = result.filter(o=>o.id==self.config.pricelist_id[0]);
                }
            }
            if(model.model == 'account.bank.statement'){
                result = result.filter(o=>o.id==self.pos_session.cash_register_id[0]);
            }

            if(model.model == 'product.pricelist.item'){
                result = result.filter(o=>_.pluck(self.pricelists, 'id').includes(o.pricelist_id[0]));
            }
            if(model.model == 'res.users'){
                if(model.label == 'Sellers'){
                    result = result.filter(o=>[...self.config.user_ids, ...self.config.assigned_user_ids].includes(o.id));
                }else{
                    result = result.filter(function(o){
                        let value = o.company_ids.includes(self.config.company_id[0]);
                        if(value){
                            if(o.groups_id.includes(self.config.group_pos_manager_id[0]) || o.groups_id.includes(self.config.group_pos_user_id[0])){
                                value = true;
                            }
                        }
                        if(self.config.module_pos_hr && self.config.user_ids && self.config.user_ids.length){
                            if(self.config.user_ids.includes(o.id)==false){
                                value = false
                            }
                        }
                        return value;
                    });
                }
            }
            if(model.model == 'res.currency'){
                if(model.label == 'Multi Currency'){
                    // result = result.filter(o=>o.active);
                }else{
                    // result = result.filter(o=>[self.config.currency_id[0],self.company.currency_id[0]].includes(o.id));
                }
            }
            if(model.model == 'res.partner.group'){
                //pass
            }
            if(model.model == 'res.partner.title'){
                //pass
            }
            if(model.model == 'uom.uom'){
                if(model.label == 'Units of Measure'){
                    result = result;
                }else{
                    result = result;
                }
            }

            if(model.model == 'pos.category'){
                if(self.config.limit_categories && self.config.iface_available_categ_ids.length){
                    result = result.filter(o=>self.config.iface_available_categ_ids.includes(o.id));
                }
            }
            if(model.model == 'product.product'){
                result = result.filter(function(o){
                    let value = false;
                    if(o.available_in_pos==true && (!o.company_id||o.company_id&&o.company_id[0]==self.config.company_id[0])){
                        value = true;
                        if (self.config.limit_categories &&  self.config.iface_available_categ_ids.length) {
                            if(!self.config.iface_available_categ_ids.includes(o.pos_categ_id[0])){
                                value = false;
                            }
                        }
                        if (self.config.iface_tipproduct){
                            if(o.id==self.config.tip_product_id[0]){
                                value = true;
                            }
                        }
                    }
                    return value;
                });
            }
            if(model.model == 'product.attribute'){
                if(model.label == 'Product Attributes'){
                    result = result;
                }else{
                    result = result.filter(o=>o.create_variant=='no_variant');
                }
            }
            if(model.model == 'product.attribute.value'){
                if(model.label == 'Product Attributes'){
                    result = result;
                }else{
                    result = result.filter(o=>_.keys(self.tmp.product_attributes_by_id).map(parseFloat).includes(o.attribute_id[0]));
                }
            }
            if(model.model == 'product.template.attribute.value'){
                if(model.label == 'Product Attributes'){
                    result = result.filter(o=>o.product_tmpl_id != null);
                }else if(model.label == 'Product Template Attribute Value'){
                    result = result;
                }else{
                    result = result.filter(o=>_.keys(self.tmp.product_attributes_by_id).map(parseFloat).includes(o.attribute_id[0]));
                }
            }
            if(model.model == 'pos.product.attribute'){
                if(model.label == 'Attribute Values Modifiers'){
                    result = result;
                }
            }
            if(model.model == 'product.uom.price'){
                if(model.label == 'Price by Unit'){
                    result = result;
                }
            }
            if(model.model == 'product.price.quantity'){
                //pass
            }
            if(model.model == 'product.cross'){
                //pass
            }
            if(model.model == 'pos.combo.limit'){
                //pass
            }
            if(model.model == 'account.cash.rounding'){
                result = result.filter(o=>o.id==self.config.rounding_method[0]);
            }
            if(model.model == 'account.fiscal.position'){
                result = result.filter(o=>self.config.fiscal_position_ids.includes(o.id));
            }
            if(model.model == 'account.payment.term'){
                //pass
            }
            if(model.model == 'account.journal'){
                result = result.filter(o=>(o.company_id[0]==self.company.id) && (['cash','bank'].includes(o.type) || self.config.payment_journal_ids.includes(o.id)));
            }
            if(model.model == 'account.fiscal.position.tax'){
                var fiscal_position_tax_ids = [];
                self.fiscal_positions.forEach(function (fiscal_position) {
                    fiscal_position.tax_ids.forEach(function (tax_id) {
                        fiscal_position_tax_ids.push(tax_id);
                    });
                });
                result = result.filter(o=>fiscal_position_tax_ids.includes(o.id));
            }
            if(model.model == 'pos.payment.method'){
                //pass
            }
            if(model.model == 'pos.payment'){
                result = result.filter(o=>self.order_ids.includes(o.pos_order_id[0]));
            }
            if(model.model == 'pos.pack.operation.lot'){
                result = result.filter(o=>self.orderline_ids.includes(o.pos_order_line_id[0]));
            }
            if(model.model == 'sale.order'){
                result = result.filter(o=>o.pos_order_id == false);
            }
            if(model.model == 'sale.order.line'){
                result = result.filter(o=>self.booking_ids.includes(o.order_id[0]));
            }
            if(model.model == 'coupon.program'){
                result = result.filter(o=>!o.company_id || (o.company_id && o.company_id[0] == self.company.id));
            }
            if(model.model == 'coupon.coupon'){
                if(self.couponProgram_ids){
                    result = result.filter(o=>self.couponProgram_ids.includes(o.program_id[0]) && ['new','sent'].includes(o.state));
                }else{
                    result = [];
                }
            }
            if(model.model == 'coupon.rule'){
                if(self.couponRule_ids){
                    result = result.filter(o=>self.couponRule_ids.includes(o.id));
                }else{
                    result = [];
                }
            }
            if(model.model == 'coupon.reward'){
                if(self.couponReward_ids){
                    result = result.filter(o=>self.couponReward_ids.includes(o.id));
                }else{
                    result = [];
                }
            }
            if(model.model == 'pos.voucher'){
                result = result.filter(function(o){
                    let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                    return o.state == 'active' && moment(o.end_date).isAfter(current_date);
                });
            }
            if(model.model == 'pos.order'){
                //pass
            }
            if(model.model == 'pos.tag'){
                //pass
            }
            if(model.model == 'pos.note'){
                //pass
            }
            if(model.model == 'pos.combo.item'){
                //pass
            }
            if(model.model == 'pos.order.line'){
                result = result.filter(o=>self.order_ids.includes(o.order_id[0]));
            }
            if(model.model == 'account.move'){
                //pass
            }
            if(model.model == 'account.move.line'){
                //pass
            }
            if(model.model == 'pos.epson'){
                //pass
            }
            if(model.model == 'pos.service.charge'){
                // result = result.filter(o=>self.config.service_charge_ids.includes(o.id));
                result = result.filter(o=>self.config.service_charge_id == o.id)
            }
            if(model.model == 'res.bank'){
                //pass
            }
            if(model.model == 'res.lang'){
                //pass
            }
            if(model.model == 'pos.coupon'){
                result = result.filter(function(o){
                    let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                    return o.state == 'active' && moment(o.end_date).isAfter(current_date);
                });
            }
            if(model.model == 'pos.promotion'){
                result = result.filter(function(o){
                    let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                    return o.state == 'active' && moment(o.end_date).isAfter(current_date) && self.config.promotion_ids.includes(o.id);
                });
            }
            let promotion_childs = [
                'pos.promotion.discount.order', 
                'pos.promotion.discount.category', 
                'pos.promotion.discount.quantity', 
                'pos.promotion.gift.condition', 
                'pos.promotion.gift.free', 
                'pos.promotion.discount.condition', 
                'pos.promotion.discount.apply', 
                'pos.promotion.price', 
                'pos.promotion.special.category', 
                'pos.promotion.selected.brand', 
                'pos.promotion.tebus.murah.selected.brand', 
                'pos.promotion.specific.product', 
                'pos.promotion.multi.buy', 
                'pos.promotion.tebus.murah', 
                'pos.promotion.multilevel.condition', 
                'pos.promotion.multilevel.gift',
            ]
            if(promotion_childs.includes(model.model)){
                result = result.filter(o=>self.promotion_ids.includes(o.promotion_id[0]));
            }
            if(model.model == 'pos.global.discount'){
                if(model.label == 'Global Discount'){
                    result = result.filter(o=>self.config.discount_ids.includes(o.id));
                }
            }
            return result
        },

        pos_cache_validate_data(model, result){
            let required_models = [
                'res.company',
                'res.users', 
                'res.currency',  
                'account.tax', 
                'pos.config', 
                'pos.session', 
                'stock.picking.type', 
                'stock.location', 
                'pos.category', 
                'product.pricelist', 
                'product.product', 
                'product.template', 
                'product.uom.price', 
                'uom.uom',
                'pos.payment.method'
            ];
            if(required_models.includes(model.model)){
                if(result.length == 0){
                    console.warn('Load Data ', model.model,' Result:', result);
                    this.showPopupLoadPosError({
                        title: _t("Warning - Failed Load Data ") + '(' + model.model + ')' ,
                        body: _t("Please Synchronize POS Cache Masterdata!")
                    });
                    return false;
                }
            }
            return true;
        },

        load_server_data_from_pos_cache_sdk: async function (refeshCache = false, needLoaded = false) {
            console.warn('--***--   BEGIN load_server_data_from_pos_cache_sdk ---***---');
            var self = this;
            var progress = 0;
            var progress_step = 1.0 / self.models.length;
            var tmp = {}; // this is used to share a temporary state between models loaders

            //TODO: change sequence loaded models
            self.models = [...self.models.filter(i=>i.model=='res.currency'), ...self.models.filter(i=>i.model!='res.currency')];
            self.models = [...self.models.filter(i=>i.model=='res.company'), ...self.models.filter(i=>i.model!='res.company')];
            self.models = [...self.models.filter(i=>i.model=='pos.config'), ...self.models.filter(i=>i.model!='pos.config')];
            self.models = [...self.models.filter(i=>i.model=='pos.session'), ...self.models.filter(i=>i.model!='pos.session')];

            let store_write_date_models = [
                'account.move','account.move.line','sale.order','sale.order.line','product.brand','product.product',
                'product.template','product.template.barcode','product.pricelist.item','pos.voucher','res.partner',
                'stock.quant','stock.production.lot','pos.order','pos.order.line','pos.payment','pos.coupon','pos.promotion',
                'pos.promotion.discount.order','pos.promotion.discount.category','pos.promotion.discount.quantity',
                'pos.promotion.gift.condition','pos.promotion.gift.free','pos.promotion.discount.condition',
                'pos.promotion.discount.apply','pos.promotion.special.category','pos.promotion.selected.brand',
                'pos.promotion.tebus.murah.selected.brand','pos.promotion.specific.product','pos.promotion.multi.buy',
                'pos.promotion.price','pos.promotion.tebus.murah','pos.promotion.multilevel.condition',
                'pos.promotion.multilevel.gift', 'pos.product.promotion'
            ];

            var loaded = new Promise(function (resolve, reject) {
                function load_model(index) {
                    if (index >= self.models.length) {
                        resolve();
                    } else {
                        var model = self.models[index];
                        self.setLoadingMessage(_t('Loading')+' '+(model.label || model.model || ''), progress);

                        var cond = typeof model.condition === 'function'  ? model.condition(self,tmp) : true;
                        if (!cond) {
                            load_model(index+1);
                            return;
                        }
    
                        var fields = typeof model.fields === 'function' ? model.fields(self, tmp) : model.fields;
                        var domain = typeof model.domain === 'function' ? model.domain(self, tmp) : model.domain;
                        var context = typeof model.context === 'function' ? model.context(self, tmp) : model.context || {};
                        var ids = typeof model.ids === 'function' ? model.ids(self, tmp) : model.ids;
                        var order = typeof model.order === 'function' ? model.order(self, tmp) : model.order;
                        if(!order){
                            order = '';
                        }
                        progress += progress_step;

                        if( model.model ){

                            /** TODO: make request to POS Cache SDK **/
                            var url = self.db.pos_cache_sdk_localhost_link + '/model'; 
                            var dataJSON = JSON.stringify({
                                model: model.model,
                                domain: [],
                            });
                            var xhr = new XMLHttpRequest();
                            xhr.open('POST', url);
                            xhr.onload = function () { 
                                if (this.status >= 200 && this.status < 300 && xhr.response){
                                    var response = JSON.parse(xhr.response);
                                    try { // catching exceptions in model.loaded(...)
                                        var result = self.pos_cache_filter_base_on_domain(model, response['result']);
                                        var is_valid = self.pos_cache_validate_data(model, result);
                                        if(!is_valid){
                                            return;
                                        }
                                        if(store_write_date_models.includes(model.model)){
                                            self.db.set_last_write_date_by_model(model.model, result);
                                        }
                                        Promise.resolve(model.loaded(self, result, tmp))
                                            .then(function () { load_model(index + 1); },
                                                function (err) { reject(err); });
                                    } catch (err) {
                                        console.error(err.message, err.stack);
                                        reject(err);
                                    }
                                } else {
                                    reject(xhr.statusText);
                                }
                            };
                            xhr.onerror = function () { 
                                if(xhr.statusText == ''){
                                    console.error(_t("Failed connect to POS Cache SDK.\nPlease start service first!"));
                                    self.showPopupLoadPosError({
                                        title: _t("Warning - Failed connect to POS Cache SDK"),
                                        body: _t("Please start service first!")
                                    });
                                    return;
                                }
                                reject(xhr.statusText); 
                            };
                            xhr.send(dataJSON);

                        } else if (model.loaded) {
                            try { // catching exceptions in model.loaded(...)
                                Promise.resolve(model.loaded(self, tmp))
                                    .then(function () { load_model(index +1); },
                                        function (err) { reject(err); });
                            } catch (err) {
                                reject(err);
                            }
                        } else {
                            load_model(index + 1);
                        }
                    }
                }

                try {
                    return load_model(0);
                } catch (err) {
                    return Promise.reject(err);
                }
            });

            return loaded;
        },

        // OVERRIDE
        async search_model_datas(method, vals){
            let self = this;
            if(!self.db.pos_load_data_from_pos_cache_sdk){
                return _super_PosModel.search_model_datas.call(self, method, vals);
            }
            if(method == 'auto_sync_product_stock'){
                return await self.search_model_datas_product_stock(vals);
            }
            if(method == 'auto_sync_products'){
                return await self.search_model_datas_products(vals);
            }
            if(method == 'auto_sync_pricelist'){
                return await self.search_model_datas_pricelist(vals);
            }
            if(method == 'auto_sync_promotion'){
                return await self.search_model_datas_promotion(vals);
            }
            if(method == 'auto_sync_coupon'){
                return await self.search_model_datas_coupon(vals);
            }
        },

        async search_model_datas_product_stock(vals){
            let domain = [];
            let last_write_date = vals['stock.quant'];
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result = await this.get_pos_cache_model_data({
                model: 'stock.quant',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'product_stock',
            });
            if (result){
                try{
                    return {
                        'stock_quant': JSON.parse(result)['result'],
                        'stock_quant_count': 1 // hardcode 1 to skip pagination
                    }
                } catch (err) {
                    console.error(err.message, err.stack);
                    return [];
                }
            }
        },

        async search_model_datas_products(vals){
            let domain = [];
            let last_write_date = vals['product.product'];
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result = await this.get_pos_cache_model_data({
                model: 'product.product',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'product_stock',
            });
            if (result){
                try{
                    return {
                        'product_product': JSON.parse(result)['result'],
                        'product_product_count': 1 // hardcode 1 to skip pagination
                    }
                } catch (err) {
                    console.error(err.message, err.stack);
                    return [];
                }
            }
        },

        async search_model_datas_coupon(vals){
            let domain = [];
            let last_write_date = vals['pos.coupon'];
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result = await this.get_pos_cache_model_data({
                model: 'pos.coupon',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'coupon',
            });
            if (result){
                try{
                    return {
                        'pos_coupon': JSON.parse(result)['result'],
                        'pos_coupon_count': 1 // hardcode 1 to skip pagination
                    }
                } catch (err) {
                    console.error(err.message, err.stack);
                    return [];
                }
            }
        },

        async search_model_datas_pricelist(vals){
            let domain = [];
            let last_write_date = vals['product.pricelist.item'];
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result = await this.get_pos_cache_model_data({
                model: 'product.pricelist.item',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'pricelist',
            });
            if (result){
                try{
                    let pricelist_ids = this.pricelists.map(o=>o.id);
                    let records = JSON.parse(result)['result'];
                    records = records.filter(o=>pricelist_ids.includes(o.pricelist_id[0]));
                    return {
                        'product_pricelist_item': records,
                        'product_pricelist_item_count': 1 // hardcode 1 to skip pagination
                    }
                } catch (err) {
                    console.error(err.message, err.stack);
                    return [];
                }
            }
            return [];
        },

        async search_model_datas_promotion(vals){
            let self = this;
            let domain = [];
            let last_write_date = vals['product.pricelist.item'];
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result = {
                'pos.promotion': [],
                'pos_promotion_count': 0,
            }
            let promotion_childs = [
                'pos.promotion.discount.order', 
                'pos.promotion.discount.category', 
                'pos.promotion.discount.quantity', 
                'pos.promotion.gift.condition', 
                'pos.promotion.gift.free', 
                'pos.promotion.discount.condition', 
                'pos.promotion.discount.apply', 
                'pos.promotion.price', 
                'pos.promotion.special.category', 
                'pos.promotion.selected.brand', 
                'pos.promotion.tebus.murah.selected.brand', 
                'pos.promotion.specific.product', 
                'pos.promotion.multi.buy', 
                'pos.promotion.tebus.murah', 
                'pos.promotion.multilevel.condition', 
                'pos.promotion.multilevel.gift',
                'pos.product.promotion',
            ]
            for(let promotion_child of promotion_childs){
                result[promotion_child] = [];
            }

            async function doAjax(params) {
                let result = await self.get_pos_cache_model_data(params);
                if (result){
                    try{
                        return JSON.parse(result)['result']
                    } catch (err) { console.error(err.message, err.stack); }
                }
                return [];
            }

            let result_promotions = await doAjax({
                model: 'pos.promotion',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'promotion',
            })

            if(result_promotions.length){
                result['pos_promotion_count'] = 1; // hardcode 1 to skip pagination
                result['pos.promotion'] = result_promotions;
                let promotion_ids = result_promotions.map(o=>o.id);
                let result_promotion_childs = [];
                for(let promotion_child of promotion_childs){
                    let result_promotion_childs = await doAjax({
                        model: promotion_child,
                        domain: domain,
                        order: 'write_date desc',
                        auto_sync: 'promotion_' + promotion_child,
                    })
                    if(result_promotion_childs.length){
                        result[promotion_child] = result_promotion_childs.filter(o=>promotion_ids.includes(o.promotion_id[0]));
                    }
                }
            }
            return result;
        },


        async syncPOSOrdersFromPosCache(){
            // TODO: sync pos.order and pos.order.line and pos.payment
            let self = this;
            async function doAjax(params) {
                let result = await self.get_pos_cache_model_data(params);
                if (result){
                    try{
                        return JSON.parse(result)['result']
                    } catch (err) {
                        console.error(err.message, err.stack);
                        return [];
                    }
                }
                return [];
            }

            let result = null;
            let domain = [];
            let last_write_date = self.db.write_date_by_model['pos.order']
            if(last_write_date){
                domain = [[ ['write_date','>',last_write_date] ]];
            }
            let result_pos_order = await doAjax({
                model: 'pos.order',
                domain: domain,
                order: 'write_date desc',
                auto_sync: 'pos_order',
            });
            if(result_pos_order.length){
                result = {};
                result_pos_order = result_pos_order.filter(o=>!o.company_id || (o.company_id && o.company_id[0]==self.config.company_id[0]));
                result['pos_order'] = result_pos_order;
                let pos_order_ids = result_pos_order.map(o=>o.id);

                domain = [];
                last_write_date = self.db.write_date_by_model['pos.order.line'];
                if(last_write_date){
                    domain = [[ ['write_date','>',last_write_date] ]];
                }
                let result_pos_order_line = await doAjax({
                    model: 'pos.order.line',
                    domain: domain,
                    order: 'write_date desc',
                    auto_sync: 'pos_order-line',
                });
                if(result_pos_order_line.length){
                    result['pos_order_line'] = result_pos_order_line.filter(o=>pos_order_ids.includes(o.order_id[0]));
                }

                domain = [];
                last_write_date = self.db.write_date_by_model['pos.payment'];
                if(last_write_date){
                    domain = [[ ['write_date','>',last_write_date] ]];
                }
                let result_pos_payment = await doAjax({
                    model: 'pos.payment',
                    domain: domain,
                    order: 'write_date desc',
                    auto_sync: 'pos_order-payment',
                });
                if(result_pos_payment.length){
                    result['pos_payment'] = result_pos_payment.filter(o=>pos_order_ids.includes(o.pos_order_id[0]));
                }
            }
            
            if (result != null) {
                let pos_order_rec = result['pos_order'];
                let pos_order_line_rec = result['pos_order_line'];
                console.log('[syncPOSOrdersFromPosCache] ~ result:', result);
                let pos_payment_rec = result['pos_payment'];
                if(pos_order_rec.length){
                    console.log('[syncPOSOrdersFromPosCache] ~ Updating variable pos.order');
                    var active_records = pos_order_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.pos_order_model.loaded(self, pos_order_rec);
                    }
                    self.save_results('pos.order', pos_order_rec);
                    console.log('[syncPOSOrdersFromPosCache] ~ Finish variable pos.order');
                }
                if(pos_order_line_rec.length){
                    console.log('[syncPOSOrdersFromPosCache] ~ Updating variable pos.order.line');
                    var active_records = pos_order_line_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.pos_order_line_model.loaded(self, pos_order_line_rec);
                    }
                    self.save_results('pos.order.line', pos_order_line_rec);
                    console.log('[syncPOSOrdersFromPosCache] ~ Finish variable pos.order.line');
                }
                if(pos_payment_rec.length){
                    if(!self.pos_payment_by_order_id){
                        self.pos_payment_by_order_id = {}
                    }
                    for (let payment of pos_payment_rec){
                        let order_id = payment.pos_order_id[0];
                        let order = self.db.order_by_id[order_id];
                        order['payments'].push(payment);
                        if (!self.pos_payment_by_order_id[order_id]) {
                            self.pos_payment_by_order_id[order_id] = [payment];
                        } else {
                            self.pos_payment_by_order_id[order_id].push(payment);
                        }
                    }
                    console.log('[syncPOSOrdersFromPosCache] ~ Finish variable pos.payment');
                }
            }else{
                console.log('[syncPOSOrdersFromPosCache] ~ Results: 0');
            }

            posbus.trigger('reload-orders');
        },

    });
});

