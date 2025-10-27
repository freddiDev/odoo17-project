from odoo import models, fields, api

class PurchaseAnalystReport(models.TransientModel):
    _name = 'purchase.analyst.report'
    _description = 'Purchase Analyst Report Result'

    name = fields.Char(string="Name")
    product_code = fields.Char(string="Product Code", related="product_id.default_code")
    product_id = fields.Many2one("product.product", string="Product")
    qty_po = fields.Float(required=True, digits=(16, 2), default=0.0, string="Qty PO")
    qty_sale = fields.Float(required=True, digits=(16, 2), default=0.0, string="Qty Sale")
    partner_id = fields.Many2one("res.partner", string="Vendor")
    currency_id = fields.Many2one("res.currency", string="Currency")
    subtotal = fields.Monetary(string="Subtotal")
    price = fields.Monetary(string="Price")
    user_id = fields.Many2one("res.users", string="User")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    date_order = fields.Datetime(string="Order Date")

