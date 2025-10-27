from datetime import timedelta
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.tools.misc import split_every
import json



class ReorderingRulesWiz(models.TransientModel):
    _name = 'reordering.rules.wiz'
    _description = 'Reordering Rules Wizard'

    name = fields.Char(string='Name')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    line_ids = fields.One2many('reordering.rules.wiz.line', 'wizard_id', string='Lines')
    is_show = fields.Boolean(string='Show', default=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True,
        domain="[('supplier_rank', '>', 0)]",
        help="Select a vendor to determine the leadtime status.")
    leadtime_status = fields.Selection([
        ('tepat_waktu', 'TEPAT WAKTU'),
        ('lebih_cepat', 'LEBIH CEPAT'),
        ('telat', 'TERLAMBAT'),
        ('unknown', 'unknown')
    ], string='Leadtime Status')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse', required=True)


    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        if (not self.warehouse_ids and len(self.warehouse_ids) == 0) and self.is_show:
            self.line_ids.unlink()
            self.warehouse_ids = False
            self.is_show = False


    def write_warehouse_json(self, datas):
        """Write warehouse JSON values to the wizard lines based on the provided qty_data."""
        if not self.exists():
            return False

        for line in self.line_ids:
            orderpoint = line.orderpoint_id
            if not orderpoint:
                continue

            qty = datas.get(str(orderpoint.id), 0.0)

            self.env.cr.execute(
                "SELECT id FROM stock_warehouse_orderpoint WHERE id = %s FOR UPDATE NOWAIT",
                (orderpoint.id,)
            )

            orderpoint.write({
                'qty_to_order': orderpoint.qty_to_order - qty,
                'remain_to_order': qty,
            })

        company_id = self.env.company.id
        orderpoints_to_procure = self.line_ids.filtered(
            lambda l: l.orderpoint_id and l.orderpoint_id.remain_to_order > 0
            ).mapped('orderpoint_id')

        if orderpoints_to_procure:
            self.env.cr.execute(
                "SELECT id FROM stock_warehouse_orderpoint WHERE id IN %s FOR UPDATE",
                [tuple(orderpoints_to_procure.ids)]
            )

            orderpoints_to_procure.sudo()._procure_orderpoint_confirm(
                use_new_cursor=False,
                company_id=company_id,
                raise_user_error=False,
            )

        domain = self._get_moves_to_assign_domain(company_id)
        moves_to_assign = self.env['stock.move'].search(
            domain, 
            limit=None,
            order='priority desc, date asc'
        )

        for moves_chunk in split_every(100, moves_to_assign.ids):
            self.env['stock.move'].browse(moves_chunk).sudo()._action_assign()

        self.env['stock.quant']._quant_tasks()
        return True


    @api.model
    def get_table_lines(self, wizard_id):
        wizard = self.browse(wizard_id)
        lines_data = []
        for i, line in enumerate(wizard.line_ids, 1):
            qty_per_warehouse = {}
            for warehouse in wizard.warehouse_ids:
                qty = line._get_qty_to_order_for_warehouse(warehouse.id)
                qty_per_warehouse[str(warehouse.id)] = qty

            lines_data.append({
                'id': line.id,
                'no': i,
                'name': line.product_id.display_name,
                'product': line.product_id.id,
                'orderpoint_id': line.orderpoint_id.id if line.orderpoint_id else False,
                'receiving_avg': line.receiving_avg or 0,
                'qty_to_order': qty_per_warehouse,
            })
        return lines_data


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.leadtime_status = self.partner_id.leadtime_status


    @api.model
    def _get_moves_to_assign_domain(self, company_id):
        moves_domain = [
            ('state', 'in', ['confirmed', 'partially_available']),
            ('product_uom_qty', '!=', 0.0)
        ]
        if company_id:
            moves_domain = expression.AND([[('company_id', '=', company_id)], moves_domain])
        return moves_domain


    @api.model
    def _get_orderpoint_domain(self, company_id=False):
        domain = [('trigger', '=', 'auto'), ('product_id.active', '=', True)]
        if company_id:
            domain += [('company_id', '=', company_id)]
        return domain

    
    def _compute_receiving_avg(self):
        StockMoveLine = self.env['stock.move.line']
        date_90_days_ago = fields.Datetime.now() - timedelta(days=90)

        for record in self:
            product_ids = record.line_ids.mapped('product_id').ids

            if not product_ids:
                continue

            domain = [
                ('product_id', 'in', product_ids),
                ('state', '=', 'done'),
                ('date', '>=', date_90_days_ago),
                ('location_dest_id.usage', '=', 'internal'),
            ]
            move_lines = StockMoveLine.search(domain)

            product_move_map = {}
            for line in move_lines:
                product_move_map.setdefault(line.product_id.id, []).append(line.quantity)

            for line in record.line_ids:
                qty_list = product_move_map.get(line.product_id.id, [])
                total_qty = sum(qty_list)
                count = len(qty_list)
                line.receiving_avg = (total_qty / count) if count else 0.0


    def procure_calculation(self):
        """This method is called to trigger the procurement calculation for reordering rules."""
        company_id = self.env.company.id
        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints = self.env['stock.warehouse.orderpoint'].search(domain)
        self._compute_receiving_avg()
        datas = orderpoints.filtered(
            lambda op: op.qty_to_order > 0 
            and op.warehouse_id.id in self.warehouse_ids.ids
            and op.product_id.seller_ids
            and op.product_id.seller_ids[0].partner_id.id == self.partner_id.id
        ).mapped(lambda op: {
            'product_id': op.product_id.id, 
            'qty_to_order': op.qty_to_order,
            'orderpoint_id': op.id
        })  
        if datas:
            self.is_show = True
            lines = []
            for data in datas:
                lines.append((0, 0, {
                    'product_id': data.get('product_id'),
                    'qty_to_order': data.get('qty_to_order'),
                    'orderpoint_id': data.get('orderpoint_id', False)
                }))
            self.line_ids = lines
            self._compute_receiving_avg()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


    def action_create_rfq(self):
        """This method is called to create RFQs based on the reordering rules."""
        return True


class ReorderingRulesWizLine(models.TransientModel):
    _name = 'reordering.rules.wiz.line'
    _description = 'Reordering Rules Wizard Lines'

    name = fields.Char(string='Name')
    wizard_id = fields.Many2one('reordering.rules.wiz', string='Wizard Reference')
    product_id = fields.Many2one('product.product', string='Product')
    reference = fields.Char(string='Reference')
    qty_to_order = fields.Float(string='Qty to Order', digits='Product Unit of Measure')
    receiving_avg = fields.Float(string='Receiving Avg', digits='Product Unit of Measure')
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string="Orderpoint")
    warehouse_json_val = fields.Text('Warehouse Value')

    def _get_qty_to_order_for_warehouse(self, warehouse_id):
        self.ensure_one()
        if self.orderpoint_id and self.orderpoint_id.warehouse_id.id == warehouse_id:
            return self.qty_to_order or 0.0
        return 0.0


        

