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
    pos_loyal_point = fields.Float(string='Member Points', default=0.0, readonly=True)
    total_earned_point = fields.Float(string='Member Deposit', default=0.0, readonly=True)


    @api.depends('member_type', 'is_membership', 'pos_loyal_point')
    def compute_member_type_id(self):
        member_types = self.env['member.type'].search([])
        for record in self.filtered(lambda r: r.is_membership and r.member_type == 'point'):
            mt = next(
                (m for m in member_types if m.point_from <= record.pos_loyal_point <= m.point_to),
                False
            )
            record.member_type_id = mt.id if mt else False
