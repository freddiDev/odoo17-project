# -*- coding: utf-8 -*-

from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_pos_load_data_from_pos_cache_sdk = fields.Boolean('Is POS load from POS Cache SDK')