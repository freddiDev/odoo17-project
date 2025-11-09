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
    member_type_id = fields.Many2one('member.type', string='Membership Type', compute='compute_member_type_id')
    pos_loyal_point = fields.Float(string='Member Points', default=0.0, readonly=True, compute="_get_point")
    total_earned_point = fields.Float(string='Member Deposit', default=0.0, readonly=True)
    pos_loyalty_point_ids = fields.One2many(
        'pos.loyalty.point',
        'partner_id',
        'Point Histories')


    @api.depends('member_type', 'is_membership', 'pos_loyal_point')
    def compute_member_type_id(self):
        member_types = self.env['member.type'].search([])
        for record in self.filtered(lambda r: r.is_membership and r.member_type == 'point'):
            mt = next(
                (m for m in member_types if m.point_from <= record.pos_loyal_point <= m.point_to),
                False
            )
            record.member_type_id = mt.id if mt else False

    def _get_point(self):
        for partner in self:
            total_points = 0
            for loyalty_transaction in partner.pos_loyalty_point_ids:
                transaction_type = loyalty_transaction.type
                if loyalty_transaction.state != 'ready' and transaction_type not in ['plus']:
                    continue
                if transaction_type in ['plus']:
                    if loyalty_transaction.state != 'ready':
                        total_points += abs(loyalty_transaction.redeemed_point)
                    else:
                        total_points += loyalty_transaction.point
                elif transaction_type in ['void', 'return']:
                    total_points += loyalty_transaction.point
                elif transaction_type == 'redeem':
                    total_points += loyalty_transaction.point
            partner.pos_loyal_point = total_points

    @api.model
    def create_from_ui(self, partner):
        partner_id = super().create_from_ui(partner)
        partner_rec = self.browse(partner_id)
        if not partner.get('id') and partner_rec.exists():
            partner_rec.is_membership = True

        return partner_id
