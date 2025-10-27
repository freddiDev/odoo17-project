from odoo import models, fields, api
from odoo.tools import float_round


class PosOrder(models.Model):
    _inherit = 'pos.order'
    _description = 'Point of Sale Order with Double Book Keeping'


    def generate_book_keeping(self):
        for order in self:
            warehouse = order.config_id.warehouse_id
            total_paid = sum(order.payment_ids.mapped('amount'))
            if not total_paid:
                continue

            cv_line_map = {}
            for line in order.lines:
                product = line.product_id.product_tmpl_id
                cv_line = product.product_cv_template_ids.filtered(
                    lambda l: l.warehouse_id == warehouse
                )[:1]
                if not cv_line or not cv_line.cv_id:
                    continue

                cv = cv_line.cv_id
                cv_line_map.setdefault(cv.id, 0.0)
                cv_line_map[cv.id] += line.price_subtotal_incl 

            for payment in order.payment_ids:
                payment_ratio = payment.amount / total_paid  

                for cv_id, cv_amount in cv_line_map.items():
                    allocated_amount = payment_ratio * cv_amount
                    pm = payment
                    cv = self.env['product.cv'].browse(cv_id)

                    name = f"{pm.payment_method_id.name} {cv.name}"
                    existing = self.env['payment.book'].search([
                        ('session_id', '=', order.session_id.id),
                        ('pos_payment_method_id', '=', pm.payment_method_id.id),
                        ('cv_id', '=', cv.id),
                    ], limit=1)
                    if existing:
                        existing.amount += allocated_amount
                    else:
                        self.env['payment.book'].create({
                            'name': name,
                            'cv_id': cv.id,
                            'session_id': order.session_id.id,
                            'is_cash_count': pm.payment_method_id.is_cash_count,
                            'is_bank': not pm.payment_method_id.is_cash_count,
                            'pos_payment_id': pm.id,
                            'pos_payment_method_id': pm.payment_method_id.id,
                            'amount': float_round(allocated_amount, precision_digits=0),
                        })

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder, self)._process_order(order, draft, existing_order)
        pos_order = self.browse(res)
        pos_order.generate_book_keeping()
        return res
