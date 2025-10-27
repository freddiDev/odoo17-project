from odoo import models, fields, api
from odoo.exceptions import UserError

class UpdateSalePriceWizard(models.TransientModel):
    _name = 'update.sale.price.wizard'
    _description = 'Update Harga Jual Wizard'

    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    motif_id = fields.Many2one('product.motif', string='Motif')
    model_id = fields.Many2one('product.model', string='Model')
    color_id = fields.Many2one('product.color', string='Warna')
    size_id = fields.Many2one('product.size', string='Size')
    po_date = fields.Date(string='PO Start Date')
    product_grid = fields.Char(string='Product List', default='', readonly=True)
    line_ids = fields.One2many('update.sale.price.line', 'wizard_id', string='Product Lines')

    def action_search_products(self):
        self.ensure_one()
        fields_filled = any([
            self.supplier_id, self.motif_id, self.model_id, self.color_id, self.size_id, self.po_date
        ])
        self.line_ids.unlink()
        lines = []

        if not fields_filled:
            # Semua field kosong → cari semua product dengan list_price = 0
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pt.list_price = 1
            """
            self.env.cr.execute(query)
            result = self.env.cr.fetchall()

        elif self.supplier_id and not self.po_date:
            # Supplier diisi, PO date kosong → cari product_template.supplier_id
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pt.partner_id = %s
            """
            params = [self.supplier_id.id]
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()

        elif self.supplier_id and self.po_date:
            # supplier & po_date → cari produk dari PO pada tanggal tertentu dan vendor
            query = """
                SELECT DISTINCT pp.id, pp.default_code, pt.name, pt.list_price
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE po.partner_id = %s
                AND po.date_order::date = %s
                AND po.state = 'done'
            """
            params = [self.supplier_id.id, self.po_date]
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()
        else:
            # Field motif/model/color/size saja
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE TRUE
            """
            params = []
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()

        if not result:
            raise UserError("Tidak ditemukan produk untuk kriteria yang dipilih.")

        for pid, code, name, price in result:
            lines.append((0, 0, {
                'product_id': pid,
                'default_code': code,
                'product_name': name,
                'sale_price': price,
            }))
        self.line_ids = lines

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': 'Update Harga Jual',
        }

    def action_update_price(self):
        self.ensure_one()
        for line in self.line_ids:
            query = """
                UPDATE product_template
                SET list_price = %s
                WHERE id = (
                    SELECT product_tmpl_id FROM product_product WHERE id = %s
                )
            """
            self.env.cr.execute(query, (line.sale_price, line.product_id.id))


class UpdateSalePriceLine(models.TransientModel):
    _name = 'update.sale.price.line'
    _description = 'Update Sale Price Line'

    wizard_id = fields.Many2one('update.sale.price.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    default_code = fields.Char(string='Kode Product', readonly=True)
    product_name = fields.Char(string='Nama Product', readonly=True)
    sale_price = fields.Float(string='Harga Jual')

    def action_search_products(self):
        self.ensure_one()
        fields_filled = any([
            self.supplier_id, self.motif_id, self.model_id, self.color_id, self.size_id, self.po_date
        ])
        self.line_ids.unlink()
        lines = []

        if not fields_filled:
            # Semua field kosong -> cari semua product dengan list_price = 0
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pt.list_price = 0
            """
            self.env.cr.execute(query)
            result = self.env.cr.fetchall()

        elif self.supplier_id and not self.po_date:
            # Supplier diisi, PO date kosong -> cari product_template.supplier_id
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pt.supplier_id = %s
            """
            params = [self.supplier_id.id]
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()

        elif self.supplier_id and self.po_date:
            # supplier & po_date -> cari produk dari PO pada tanggal tertentu dan vendor
            query = """
                SELECT DISTINCT pp.id, pp.default_code, pt.name, pt.list_price
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE po.partner_id = %s
                AND po.date_order::date = %s
                AND po.state = 'done'
            """
            params = [self.supplier_id.id, self.po_date]
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()
        else:
            query = """
                SELECT pp.id, pp.default_code, pt.name, pt.list_price
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE TRUE
            """
            params = []
            if self.motif_id:
                query += " AND pt.motif_id = %s"
                params.append(self.motif_id.id)
            if self.model_id:
                query += " AND pt.model_id = %s"
                params.append(self.model_id.id)
            if self.color_id:
                query += " AND pt.color_id = %s"
                params.append(self.color_id.id)
            if self.size_id:
                query += " AND pt.size_id = %s"
                params.append(self.size_id.id)
            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()

        if not result:
            raise UserError("Tidak ditemukan produk untuk kriteria yang dipilih.")

        for pid, code, name, price in result:
            lines.append((0, 0, {
                'product_id': pid,
                'default_code': code,
                'product_name': name,
                'sale_price': price,
            }))
        self.line_ids = lines

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': 'Update Harga Jual',
        }

    def action_update_price(self):
        self.ensure_one()
        for line in self.line_ids:
            query = """
                UPDATE product_template
                SET list_price = %s
                WHERE id = (
                    SELECT product_tmpl_id FROM product_product WHERE id = %s
                )
            """
            self.env.cr.execute(query, (line.sale_price, line.product_id.id))


class UpdateSalePriceLine(models.TransientModel):
    _name = 'update.sale.price.line'
    _description = 'Update Sale Price Line'

    wizard_id = fields.Many2one('update.sale.price.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    default_code = fields.Char(string='Kode Product', readonly=True)
    product_name = fields.Char(string='Nama Product', readonly=True)
    sale_price = fields.Float(string='Harga Jual')