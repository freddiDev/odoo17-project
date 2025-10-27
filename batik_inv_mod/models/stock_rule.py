from odoo import api, fields, models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):        
        
        res = super()._prepare_purchase_order(company_id, origins, values)
        value = values[0]
        warehouse_id = value.get('warehouse_id', False)
        res['warehouse_id'] = warehouse_id.id if warehouse_id else False
        return res

