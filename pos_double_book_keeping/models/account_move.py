from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_double_book_keeping_id = fields.Many2one(
        "payment.book",
        string="POS Double Book Keeping",
    )
    

class BankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    account_cv = fields.Many2one('product.cv', string="CV")

    