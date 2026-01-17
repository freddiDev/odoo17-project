from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'


    is_membership = fields.Boolean(string='Is Membership', default=False)
    member_type = fields.Selection([
        ('point', 'Points'),
        ('promo', 'Promo'),
        ('rombongan', 'Rombongan'),
    ], string='Member Category', default='point', required=True)
    membership_date = fields.Date(string='Membership Date', default=fields.Date.context_today)
    member_type_id = fields.Many2one('member.type', string='Membership Type', compute='_compute_member_type_id')
    pos_loyal_point = fields.Float(string='Member Points', default=0.0, readonly=True, compute="_get_point")
    total_earned_point = fields.Float(string='Member Deposit', default=0.0, readonly=True)
    pos_loyalty_point_ids = fields.One2many(
        'pos.loyalty.point',
        'partner_id',
        'Point Histories')

    pos_loyalty_rule_id = fields.Many2one(
        'loyalty.rule',
        compute='_compute_pos_membership_rule',
        store=True
    )

    pos_minimum_amount = fields.Float(
        compute='_compute_pos_membership_rule',
        store=True
    )

    pos_reward_point_amount = fields.Float(
        compute='_compute_pos_membership_rule',
        store=True
    )

    @api.depends('member_type_id')
    def _compute_pos_membership_rule(self):
        LoyaltyRule = self.env['loyalty.rule']

        for partner in self:
            partner.pos_loyalty_rule_id = False
            partner.pos_minimum_amount = 0
            partner.pos_reward_point_amount = 0

            if not partner.member_type_id:
                continue

            rule = LoyaltyRule.search([
                ('program_id.pos_loyalty_type', '=', 'point'),
                ('program_id.active', '=', True),
                ('member_type_ids', 'in', partner.member_type_id.id),
            ], limit=1)
            
            if rule:
                partner.pos_loyalty_rule_id = rule.id
                partner.pos_minimum_amount = rule.minimum_amount
                partner.pos_reward_point_amount = rule.reward_point_amount


    @api.depends('is_membership', 'pos_loyal_point')
    def _compute_member_type_id(self):
        member_types = self.env['member.type'].search([])
        
        for partner in self:
            partner.member_type_id = False
            if partner.is_membership and partner.pos_loyal_point >= 0:
                matching_types = member_types.filtered(
                    lambda mt: mt.point_from <= partner.pos_loyal_point <= mt.point_to
                )
                partner.member_type_id = matching_types[0] if matching_types else False

    def _get_point(self):
        for partner in self:
            total_points = 0
            for loyalty_transaction in partner.pos_loyalty_point_ids:
                transaction_type = loyalty_transaction.type
                state = loyalty_transaction.state

                if transaction_type == 'plus':
                    if state == 'ready':
                        total_points += loyalty_transaction.point
                    else:
                        total_points -= abs(loyalty_transaction.point)

                elif transaction_type == 'redeem':
                    total_points -= abs(loyalty_transaction.redeemed_point)
            partner.pos_loyal_point = total_points


    @api.model
    def create_from_ui(self, partner):
        partner_id = super().create_from_ui(partner)
        partner_rec = self.browse(partner_id)
        if not partner.get('id') and partner_rec.exists():
            partner_rec.is_membership = True
            partner_rec.company_id = self.env.company
        return partner_id
