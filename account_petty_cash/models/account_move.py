from odoo import models, fields, api,_

class AccountMove(models.Model):
    _inherit = "account.move"

    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash")
