# -*- encoding: utf-8 -*-
from odoo import models, fields

class PosOrder(models.Model):
    _inherit='pos.order'

    def update_printed_receipt_counter(self, receipt_name, receipt_counter):
        receipt_obj = self.env['pos.order']
        receipt = receipt_obj.search([('pos_reference', '=', receipt_name)], limit=1)
        receipt.write({
            'printed_receipt_counter': receipt_counter
        })

class OrderLine(models.Model):
    _inherit='pos.order.line'

    def _export_for_ui(self, orderline):
        result= super()._export_for_ui(orderline)
        desc=orderline.full_product_name.split('(')
        if len(desc)>1:
            desc=desc[1].replace(')','').strip()
            result['description'] =desc
        return result
