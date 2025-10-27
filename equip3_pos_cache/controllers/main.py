# -*- coding: utf-8 -*

import odoo
from odoo import http
from odoo.http import request
from odoo.addons.equip3_pos_general.controllers.PosWeb import pos_controller as PosGeneralController

class PosCacheController(PosGeneralController):

    def get_pos_config_info_fields(self, *args, **kw):
        res = super(PosCacheController, self).get_pos_config_info_fields(*args, **kw)
        res += ['is_pos_load_data_from_pos_cache_sdk']
        return res