# -*- coding: utf-8 -*-
import json
from odoo import fields, api, models, api, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.http  import request  
from lxml import etree
import json as simplejson


class PosLoyaltyPoint(models.Model):
    _name = 'pos.loyalty.point'
    _rec_name = 'partner_id'
    _order = 'id desc'
    _description = 'Model Management all points plus or redeem of customer'

    partner_id = fields.Many2one('res.partner', 'Member', required=1, index=1)
    member_phone = fields.Char(string='Member Phone', related='partner_id.phone')
    point = fields.Float('Reward Point')
    redeemed_point = fields.Float('Redeemed' , help='Deduct Plus Point')
    order_id = fields.Many2one('pos.order', 'POS Order Ref', index=1, ondelete='cascade')
    end_date = fields.Datetime('Expired Date')
    type = fields.Selection([
        ('plus', 'Plus'),
        ('redeem', 'Redeem Point'),
    ], string='Type', default='plus', required=1)
    state = fields.Selection([
        ('ready', 'Ready to use'),
        ('expired', 'Expired')
    ], string='State', default='ready')
    description = fields.Char('Description')
    loyalty_id = fields.Many2one('loyalty.program', 'Loyalty Program')
    is_all_redeemed = fields.Boolean('All redeemed ?',copy=False)
    company_id = fields.Many2one('res.company','Company',related="partner_id.company_id")

    def cron_check_expired_points(self):
        today = fields.Datetime.now()
        points_to_expire = self.search([('state', '=', 'ready'), ('type', '=', 'plus'), ('end_date', '<', today)])
        points_to_expire.write({'state': 'expired'})
        return True

   
    def set_ready(self):
        return self.write({'state': 'ready'})

