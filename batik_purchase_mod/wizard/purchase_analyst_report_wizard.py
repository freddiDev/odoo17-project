from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class PurchaseAnalystReportWizard(models.TransientModel):
    _name = 'purchase.analyst.report.wiz'
    _description = 'Purchase Report Analyst Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    partner_id = fields.Many2one("res.partner", string="Vendor")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    product_id = fields.Many2one("product.product", string="Products")
    category_id = fields.Many2one("product.category", string="Product Category")
    generated_type = fields.Selection([
        ('product', 'Product'),
        ('product_category', 'Product Category'),
    ], string="Search by")

    
    def _create_report_table(self):
        query = """
                DROP FUNCTION IF EXISTS generate_purchase_analyst_report(DATE, DATE, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER);
                CREATE OR REPLACE FUNCTION generate_purchase_analyst_report(
                    IN start_date DATE,
                    IN end_date DATE,
                    IN vendor_id INTEGER,
                    IN v_warehouse_id INTEGER,
                    IN v_product_id INTEGER,
                    IN category_id INTEGER,
                    IN v_user_id INTEGER,
                    IN v_currency_id INTEGER
                )
                RETURNS VOID AS $$
                BEGIN
                    DELETE FROM purchase_analyst_report WHERE user_id = v_user_id;

                    INSERT INTO purchase_analyst_report (
                        date_order, partner_id, product_id, name, qty_po, qty_sale, price, subtotal, user_id, currency_id, warehouse_id
                    )
                    SELECT
                        po_data.date_order,
                        po_data.partner_id,
                        po_data.product_id,
                        po_data.product_name,
                        po_data.qty_po,
                        COALESCE(pos_data.qty_sales, 0.0) AS qty_sales,
                        po_data.price,
                        po_data.subtotal,
                        v_user_id,
                        v_currency_id,
                        po_data.warehouse_id
                    FROM (
                        SELECT
                            po.date_order::DATE AS date_order,
                            po.partner_id,
                            pp.id AS product_id,
                            pol.name AS product_name,
                            SUM(pol.product_qty) AS qty_po,
                            SUM(pol.price_unit) AS price,
                            SUM(pol.price_subtotal) AS subtotal,
                            po.warehouse_id
                        FROM purchase_order_line pol
                        LEFT JOIN purchase_order po ON po.id = pol.order_id
                        LEFT JOIN product_product pp ON pp.id = pol.product_id
                        WHERE po.date_order BETWEEN start_date AND end_date
                        AND (vendor_id IS NULL OR po.partner_id = vendor_id)
                        AND (v_warehouse_id IS NULL OR po.warehouse_id = v_warehouse_id)
                        AND (v_product_id IS NULL OR pp.id = v_product_id)
                        GROUP BY po.date_order, po.partner_id, pp.id, pol.name, po.warehouse_id    
                    ) po_data
                    LEFT JOIN (
                        SELECT
                            pp.id AS product_id,
                            SUM(pl.qty) AS qty_sales
                        FROM pos_order_line pl
                        JOIN pos_order pos ON pos.id = pl.order_id
                        JOIN product_product pp ON pp.id = pl.product_id
                        WHERE pos.date_order BETWEEN start_date AND end_date
                        AND (v_product_id IS NULL OR pp.id = v_product_id)
                        GROUP BY pp.id
                    ) pos_data ON pos_data.product_id = po_data.product_id;
                END;
                $$ LANGUAGE plpgsql;"""
        return query


    def action_generate_report(self):
        vendor_id = self.partner_id.id if self.partner_id else None
        warehouse_id = self.warehouse_id.id if self.warehouse_id else None
        product_id = self.product_id.id or None
        category_id = self.category_id.id or None
        user_id = self.env.uid
        currency = self.env.company.currency_id.id
        report = self._create_report_table()
        self.env.cr.execute(report)
        domain_range = self.start_date + relativedelta(months=+6)
        if self.end_date > domain_range:
            raise UserError("Cannot be more than 6 months from today.")
        
        self.env.cr.execute("""
            SELECT generate_purchase_analyst_report(
                %s::DATE, %s::DATE,
                %s::INTEGER, %s::INTEGER, %s::INTEGER, %s::INTEGER, %s::INTEGER, %s::INTEGER
            )
        """, [
            self.start_date,
            self.end_date,
            vendor_id,
            warehouse_id,
            product_id,
            category_id,
            user_id,
            currency
        ])

        return {
            'name': 'Filtered Purchase Analyst Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.analyst.report',
            'view_mode': 'tree',
            'domain': [('user_id', '=', user_id)],
            'target': 'current',
             'context': {
                'group_by': 'warehouse_id',
            }
        }
