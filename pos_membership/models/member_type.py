from odoo import _, api, fields, models

class MemberType(models.Model):
    _name = 'member.type'
    _description = 'Member Type'

    name = fields.Char(string='Name', required=True)
    point_from = fields.Float(string='Point From', required=True, default=0.0, digits='16, 2')
    point_to = fields.Float(string='Point To', required=True, default=0.0, digits='16, 2')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)