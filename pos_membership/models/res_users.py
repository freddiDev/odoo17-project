from odoo import api, models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_pin = fields.Char(string="POS PIN", help="Personal Identification Number for POS user authentication.")