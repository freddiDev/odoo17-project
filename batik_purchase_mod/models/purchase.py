from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone, UTC

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_reference_id = fields.Many2one('purchase.order', string="PO Reference")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    purchase_revision_id = fields.Many2one('purchase.order', string="Purchase Rev", domain=lambda self: self._get_done_purchase())
    purchase_total_qty = fields.Float(string='PO qty Total', compute='_compute_purchase_total_qty', store=True)
    summary_id = fields.Many2one('purchase.summary', string="Purchase Summary")
    date_order = fields.Datetime('RFQ Deadline', required=True,index=True, copy=False,
        help="Depicts the date within which the Quotation should be confirmed and converted into a purchase order.")
    date_planned = fields.Datetime(string='Estimasi Pengiriman', compute='_compute_date_planned', readonly=False, store=True)
    effective_date = fields.Datetime("Tanggal Terima", store=True)
    received_leadtime = fields.Float(string='Lama Pengiriman (Hari)',compute='_compute_received_leadtime', store=True, copy=False)
    purchase_remarks = fields.Text(string='Remarks')
    leadtime_plan = fields.Float(string='Leadtime Plan', compute='_compute_partner_data')
    leadtime_actual = fields.Float(string='Leadtime Actual', compute='_compute_partner_data')
    leadtime_status = fields.Selection([
        ('tepat_waktu', 'TEPAT WAKTU'),
        ('lebih_cepat', 'LEBIH CEPAT'),
        ('telat', 'TERLAMBAT'),
        ('unknown', 'unknown')
    ], string='Leadtime Status', compute='_compute_leadtime_status', store=True)
    
    def action_purchase_ref_wiz(self):
        """Open Purchase Reference Wizard."""
        return {
            'name': _('Purchase Reference'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.ref.wiz',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_puchase_id': self.id,
                'default_name': 'PO Ref' + '/' + self.name,
                'default_date': fields.Date.context_today(self),
            }
        }

    @api.depends('partner_id')
    def _compute_date_planned(self):
        for order in self:
            if order.partner_id:
                lead_days = order.partner_id.leadtime_plan or 0.0
                planned_date = datetime.now() + timedelta(days=lead_days)
                order.date_planned = fields.Datetime.to_string(planned_date)

    @api.depends('date_planned', 'effective_date', 'partner_id.leadtime_plan')
    def _compute_received_leadtime(self):
        for order in self:
            if order.date_planned and order.effective_date and order.partner_id.leadtime_plan:
                user_tz_name = self.env.user.tz or 'UTC'
                user_tz = timezone(user_tz_name)

                # Konversi ke timezone lokal user
                date_planned = order.date_planned
                effective_date = order.effective_date

                if date_planned.tzinfo is None:
                    date_planned = UTC.localize(date_planned)
                if effective_date.tzinfo is None:
                    effective_date = UTC.localize(effective_date)

                planned_local = date_planned.astimezone(user_tz).date()
                effective_local = effective_date.astimezone(user_tz).date()

                # Hitung expected_date & delay
                expected_date = planned_local + timedelta(days=order.partner_id.leadtime_plan)
                delay_days = (effective_local - expected_date).days

                order.received_leadtime = order.partner_id.leadtime_plan + delay_days
            else:
                order.received_leadtime = 0

    @api.depends('date_planned', 'effective_date')
    def _compute_leadtime_status(self):
        for rec in self:
            status = 'unknown'
            if rec.date_planned and rec.effective_date:
                try:
                    planned = rec.date_planned if isinstance(rec.date_planned, datetime) else fields.Datetime.from_string(rec.date_planned)
                    received = rec.effective_date if isinstance(rec.effective_date, datetime) else fields.Datetime.from_string(rec.effective_date)

                    if received > planned:
                        status = 'telat'
                    elif received < planned:
                        status = 'lebih_cepat'
                    else:
                        status = 'tepat_waktu'
                except Exception:
                    status = 'unknown'
            rec.leadtime_status = status

    @api.depends('order_line.product_qty')
    def _compute_purchase_total_qty(self):
        for order in self:
            order.purchase_total_qty = sum(line.product_qty for line in order.order_line)

    @api.depends('partner_id')
    def _compute_partner_data(self):
        for order in self:
            if order.partner_id:
                order.leadtime_plan = order.partner_id.leadtime_plan
                order.leadtime_actual = order.partner_id.leadtime_actual
            else:
                order.leadtime_plan = 0.0
                order.leadtime_actual = 0.0
                
    @api.model
    def group_by_cv(self):
        grouped_lines = {}
        for line in self.order_line:
            cv_id = line.cv_id.id
            if cv_id not in grouped_lines:
                grouped_lines[cv_id] = []
            grouped_lines[cv_id].append(line)
        return grouped_lines


    @api.constrains('partner_id', 'warehouse_id')
    def _check_vendor_and_warehouse_code(self):
        """Constrain Vendor Code and Warehouse Code.
        This function ensures that the vendor code and warehouse code are valid.
        It validates the presence of these codes to guarantee that the sequence number 
        follows the correct format.
        """
        for record in self:
            if (record.partner_id and not record.partner_id.code) \
                or (record.warehouse_id and not record.warehouse_id.code):
                raise ValidationError(_('Vendor Code or Warehouse Code is required!'))


    @api.model_create_multi
    def create(self, vals_list):
        """Create Function.
        Inherit root function to custom sequences number
        of Request for Quotation.
        Return string => 'RFQ/VENDOR/WAREHOUSE/TAHUNBULANTANGGALl/running number'
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vendor = self.env['res.partner'].browse(vals.get('partner_id'))
                warehouse = self.env['stock.warehouse'].browse(vals.get('warehouse_id'))
                seq_number = self.env['ir.sequence'].next_by_code('purchase.order.rfq')
                date_str = fields.Date.context_today(self).strftime('%y%m%d')

                if vals.get('state', 'draft') == 'draft':
                    vals['name'] = f"RFQ/{vendor.code}/{warehouse.code}/{date_str}/{seq_number}"   
        return super(PurchaseOrder, self).create(vals_list)
    

    def write(self, vals):
        """Write Method.
        This the root function, and we need to inheritance
        It make sure the presence of the sequence number 
        follows the correct format.
        """
        res = super(PurchaseOrder, self).write(vals)
        for order in self:
            if vals.get('state') == 'purchase' and 'RFQ' in order.name:
                vendor_code = order.partner_id.code
                warehouse_code = order.warehouse_id.code
                date_str = fields.Date.context_today(self).strftime('%y%m%d')
                seq_number = self.env['ir.sequence'].next_by_code('purchase.order.batik.seq')
                order.name = f"PO/{vendor_code}/{warehouse_code}/{date_str}/{seq_number}"
        return res


    @api.model
    def _get_done_purchase(self):
        self.env.cr.execute("""
            SELECT DISTINCT po.id
            FROM purchase_order po
            JOIN purchase_order_line pol ON pol.order_id = po.id
            JOIN stock_move sm ON sm.purchase_line_id = pol.id
            JOIN stock_picking sp ON sp.id = sm.picking_id
            WHERE sp.state = 'done'
        """)

        purchase_ids = [row[0] for row in self.env.cr.fetchall()] \
            if self.env.cr.rowcount > 0 else []
        return [('id', 'in', purchase_ids)]


    @api.onchange('order_line')
    def _onchange_order_line(self):
        """Order Line Onchange
        call onchange function on purchase orde line
        to auto-fill vendor and warehose.
        """
        self.partner_id = False
        for line in self.order_line:
            data = line.compute_datas_product_cv()
            if data:
                self.partner_id = data.product_template_id.partner_id.id

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.picking_type_id = self.warehouse_id.in_type_id.id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    cv_id = fields.Many2one('product.cv', string="CV")
    product_domain_ids = fields.Many2many('product.product', string='Product Domain', compute="_compute_domain_product_selected_warehouse_id")

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """Stock Moves Prepared.
        Inherit root function prepared product move
        to add cv id value to movec.
        """
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        res['cv_id'] = self.cv_id.id if self.cv_id else False
        return res
 

    def compute_datas_product_cv(self):
        if self.product_id and self.order_id.warehouse_id:
            product_template = self.product_id.product_tmpl_id

            #Do query to find data and limit only catch one record.
            cv_line = self.env['product.template.cv.line'].search([
                ('warehouse_id', '=', self.order_id.warehouse_id.id),
                ('product_template_id', '=', product_template.id)
            ], limit=1)
            self.cv_id = cv_line.cv_id.id if cv_line and cv_line.cv_id else False
            return cv_line


    @api.onchange('product_id')
    def onchange_product_id(self):
        """Inherit Onchange.
        Inherit root function to onchange Product to auto-fill CV.
        """
        res = super(PurchaseOrderLine, self).onchange_product_id()
        self.compute_datas_product_cv()
        return res

    
    @api.depends('order_id.warehouse_id')
    def _compute_domain_product_selected_warehouse_id(self):
        """Compute domain selected warehouse.
        This function will add dynamic domain for product id
        base on selected warehouse in order.
        """
        for line in self:
            if line.order_id.warehouse_id:
                products = []
                datas = self.env['product.template.cv.line'].search([
                    ('warehouse_id', '=', self.order_id.warehouse_id.id)
                ])
                
                if datas:
                    products = datas.mapped('product_template_id.product_variant_id')
                    line.product_domain_ids = products    
            else:
                line.product_domain_ids = False    

    
    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id, values, po)
        for cv_line in product_id.product_cv_template_ids:
            if cv_line.warehouse_id.id == po.warehouse_id.id:
                res['cv_id'] = cv_line.cv_id.id
                break   
        return res
