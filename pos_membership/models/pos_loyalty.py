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

    partner_id = fields.Many2one('res.partner', 'Member', required=True, index=1)
    member_point = fields.Float('Member Points',related='partner_id.pos_loyal_point')
    member_phone = fields.Char(string='Member Phone', related='partner_id.phone')
    point = fields.Float('Reward Point')
    redeemed_point = fields.Float('Redeemed' , help='Deduct Plus Point')
    order_id = fields.Many2one('pos.order', 'POS Order Ref', index=1, ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', 'Sale Order Ref', index=1, ondelete='cascade')
    end_date = fields.Datetime('Expired Date')
    type = fields.Selection([
        ('plus', 'Plus'),
        ('redeem', 'Redeem Point'),
        ('void', 'Void'),
        ('return', 'Refund'),
    ], string='Type', default='plus', required=True)
    state = fields.Selection([
        ('ready', 'Ready to use'),
        ('expired', 'Expired')
    ], string='State', default='ready')
    description = fields.Char('Description')
    is_return = fields.Boolean('Is Return',)
    loyalty_id = fields.Many2one('loyalty.program', 'Loyalty Program')
    product_redeemed_ids = fields.Many2many('product.product',
        'pos_loyalty_point_product_product_rel', 'loyalty_point_id', 'product_id', string='Product Redeemed')
    is_all_redeemed = fields.Boolean('All redeemed ?',copy=False)
    remaining_point = fields.Float('Remaining Point',compute='_compute_remaining_point')
    company_id = fields.Many2one('res.company','Company',related="partner_id.company_id")
    source_loyalty_point_id = fields.Many2one('pos.loyalty.point','Source Loyalty Point',copy=False)
    apply_to = fields.Selection(related='loyalty_id.pos_loyalty_type')

    def cron_check_expired_points(self):
        today = fields.Datetime.now()
        points_to_expire = self.search([('state', '=', 'ready'), ('type', '=', 'plus'), ('end_date', '<', today)])
        points_to_expire.write({'state': 'expired'})
        return True

    def _compute_remaining_point(self):
        for loyalty in self:
            remaining_point = 0
            not_expired = (not loyalty.end_date or fields.Datetime.now() < loyalty.end_date)
            if not_expired and loyalty.type == 'plus':
                remaining_point = loyalty.point - abs(loyalty.redeemed_point)
            loyalty.remaining_point = remaining_point

    def set_ready(self):
        return self.write({'state': 'ready'})

    def set_redeem_in_plus_point(self, total_point_cut):
        point_to_redeem = abs(total_point_cut) if total_point_cut is not None else 0.0
        
        for point_plus in self:
            plus_point_left = point_plus.point - abs(point_plus.redeemed_point)
            plus_point_redeemed = abs(point_plus.redeemed_point)
            if plus_point_left <= 0:
                continue
            point_residual = (point_plus.point or 0.0) - (point_plus.redeemed_point or 0.0)

            redeem_now = min(point_residual, point_to_redeem or 0.0)
            is_full_redemption = False
            if plus_point_left <= point_to_redeem:
                is_full_redemption = True

            if point_plus.point == point_plus.redeemed_point:
                point_plus.write({ 'is_all_redeemed':True })

            if is_full_redemption:
                point_plus.write({
                    'redeemed_point': plus_point_left,
                })
                point_to_redeem -= plus_point_left
                continue

            point_plus.write({
                'redeemed_point': point_to_redeem + plus_point_redeemed,
            })
            point_to_redeem -= point_to_redeem

            if not point_to_redeem or point_to_redeem == 0:
                break

        return point_to_redeem
