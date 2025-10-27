from odoo import models, fields, api

class PaymentBook(models.Model):
    _name = 'payment.book'
    _description = 'Payment Book'

    name = fields.Char(string='Payment Book Name')
    session_id = fields.Many2one('pos.session', string='POS Session')
    pos_payment_id = fields.Many2one('pos.payment', string='POS Payment')
    pos_payment_method_id = fields.Many2one('pos.payment.method', string='POS Payment')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    is_cash_count = fields.Boolean(string='Is Cash Count', readonly=True)
    is_bank = fields.Boolean(string='Is Bank', readonly=True)
    cv_id = fields.Many2one('product.cv', string='Cost/Value', readonly=True)