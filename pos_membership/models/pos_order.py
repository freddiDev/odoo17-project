from odoo import api, fields, models, _
import math
from datetime import timedelta, datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    plus_point = fields.Float('Plus Point', readonly=True, copy=False)

    def _create_loyalty_redeem(self):
        for order in self.filtered(lambda o: o.state in ['paid', 'done'] and o.partner_id):
            redeemed_pts = sum(order.lines.filtered(lambda l: l.is_reward_redeem).mapped('pts'))
            if redeemed_pts > 0:
                self.env['pos.loyalty.point'].create({
                    'partner_id': order.partner_id.id,
                    'order_id': order.id,
                    'point': 0,
                    'redeemed_point': redeemed_pts,
                    'type': 'redeem',
                    'company_id': order.company_id.id,
                    'state': 'ready',
                    'description': _('Redeemed loyalty points from POS Order %s') % order.name,
                })
    
    def _create_loyalty_point(self):
        for order in self.filtered(lambda o: o.state in ['paid', 'done'] and o.partner_id and o.partner_id.is_membership):
            partner = order.partner_id
            if partner.member_type != 'point' or not partner.member_type_id:
                continue

            rule = self.env['loyalty.rule'].search([
                ('member_type_ids', 'in', partner.member_type_id.id),
                ('program_id.pos_loyalty_type', '=', 'point'),
                ('program_id.active', '=', True)
            ], limit=1)
            if not rule:
                continue

            min_amount = rule.minimum_amount or 0
            reward_per_amount = rule.reward_point_amount or 0
            if min_amount <= 0 or reward_per_amount <= 0:
                continue

            earned_point = math.ceil(order.amount_total / min_amount) * reward_per_amount
            if earned_point <= 0:
                continue

            end_date = fields.Datetime.now() + timedelta(days=rule.program_id.expired_days)
            self.env['pos.loyalty.point'].create({
                'partner_id': partner.id,
                'order_id': order.id,
                'point': earned_point,
                'type': 'plus',
                'company_id': self.env.company.id,
                'state': 'ready',
                'description': _('Loyalty point from POS Order %s') % order.name,
                'loyalty_id': rule.program_id.id,
                'end_date':end_date
            })
            order.plus_point = earned_point

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self._create_loyalty_point()
        self._create_loyalty_redeem()
        return res

    @api.model
    def get_loyalty_rules_for_pos(self):
        rules = self.env['loyalty.rule'].search([
            ('program_id.pos_loyalty_type', '=', 'point'),
            ('program_id.active', '=', True)
        ])
        result = []
        for r in rules:
            result.append({
                'id': r.id,
                'program_id': r.program_id.id,
                'member_type_ids': r.member_type_ids.ids,
                'minimum_amount': r.minimum_amount,
                'reward_point_amount': r.reward_point_amount,
            })
        return result

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    pts = fields.Float('Used Points')
    is_reward_redeem = fields.Boolean('Reward Redeem')


