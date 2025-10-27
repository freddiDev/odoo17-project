odoo.define('equip3_pos_cache.Database', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB'); 
    const big_data = require('equip3_pos_masterdata.big_data');
    const retail_db = require('equip3_pos_masterdata.database');
    var _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);

        // TODO: activate load masterdata/sync from POS Cache Database (Pos Cache SDK)
        this.pos_load_data_from_pos_cache_sdk = odoo.session_info.config.is_pos_load_data_from_pos_cache_sdk;
        this.pos_cache_sdk_localhost_link = 'http://localhost:8080';
    };
});