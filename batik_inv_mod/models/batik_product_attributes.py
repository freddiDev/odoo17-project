from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductMotif(models.Model):
    _name = 'product.motif'
    _description = 'Attributes motif of products'

    name = fields.Char('Name', required=True)
    warna = fields.Many2many('product.color', 'product_color_product_motif_rel', 'product_motif_id', 'product_color_id', string='Warna', required=True)
    code = fields.Char('Code Motif', required=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        """Create Method.
        Inherit root function, to modifi sequence number
        return => string {'y%m%001'}
        """
        if vals.get('code', 'New') == 'New':
            seq_number = self.env['ir.sequence'].next_by_code('batik.code.seq.motif')
            date_str = fields.Date.context_today(self).strftime('%y%m')
            vals['code'] = f"{date_str}{seq_number}"   

        return super(ProductMotif, self).create(vals)


class ProductSize(models.Model):
    _name = 'product.size'
    _description = 'Attributes sizes of products'

    name = fields.Char('Name', required=True)
    size = fields.Char('Size', required=True, unique=True)


class ProductColor(models.Model):
    _name = 'product.color'
    _description = 'Attributes colors of products'

    name = fields.Char('Name', required=True)
    color= fields.Char('Color', required=True)
    code = fields.Char('Color Code', required=True, unique=True)

class ProductModel(models.Model):
    _name = 'product.model'
    _description = 'Attribute models of products'

    kode_model = fields.Char('Kode Model', readonly=True)
    logo = fields.Binary(string='Logo Model')
    name = fields.Char('Name', required=True)
    size = fields.Many2many('product.size', 'product_model_size_rel', 'product_model_id', 'product_size_id', required=True)
    category = fields.Many2one('product.category', 'Category', required=True)
    descriptions = fields.Text('Descriptions')

    @api.onchange('category')
    def _onchange_category_set_kode_model(self):
        if self.category:
            if not self.category.model_code:
                raise UserError(_("Code Model pada kategori belum diisi. Silakan isi terlebih dahulu."))
            self.kode_model = self.category.model_code
            
    def action_set_kode_model_from_category(self):
        for rec in self:
            if rec.category:
                if not rec.category.model_code:
                    raise UserError(_("Code Model pada kategori belum diisi. Silakan isi terlebih dahulu."))
                rec.kode_model = rec.category.model_code

class ProductCV(models.Model):
    _name = 'product.cv'
    _description = 'Attributes CV of products'

    name = fields.Char('Name', required=True)
    warehouse_id= fields.Many2one('stock.warehouse', string="Warehouse", required=True)
    persentase_double_book_Keeping = fields.Float('Persentase Double Book Keeping', digits=(16,2), default=0.0)
    expedition_cash_bank_account = fields.Many2one('account.account', string='Akun Cash/Bank expedisi')
    category_id = fields.Many2one('product.category', string='Category', required=True)

    def _sync_category_cv_lines(self, previous_categories=None):
        """Ensure product category CV lines reflect the Product CV configuration."""
        previous_categories = previous_categories or {}
        line_model = self.env['categ.product.cv.line']

        for record in self:
            prev_category_id = previous_categories.get(record.id)

            # Remove linkage from old category when it changed or was cleared.
            if prev_category_id and prev_category_id != record.category_id.id:
                old_lines = line_model.search([
                    ('category_id', '=', prev_category_id),
                    ('cv_id', '=', record.id),
                ])
                if old_lines:
                    old_lines.unlink()

            if record.category_id:
                line_values = {
                    'name': record.name,
                    'category_id': record.category_id.id,
                    'warehouse_id': record.warehouse_id.id,
                    'cv_id': record.id,
                }
                existing_lines = line_model.search([
                    ('category_id', '=', record.category_id.id),
                    ('cv_id', '=', record.id),
                ])

                if existing_lines:
                    # Update the first line and remove duplicates, if any.
                    existing_lines[0].write(line_values)
                    if len(existing_lines) > 1:
                        existing_lines[1:].unlink()
                else:
                    line_model.create(line_values)

    @api.model
    def create(self, vals):
        record = super(ProductCV, self).create(vals)
        record._sync_category_cv_lines()
        return record

    def write(self, vals):
        category_changes = {}
        if 'category_id' in vals:
            category_changes = {rec.id: rec.category_id.id for rec in self}

        res = super(ProductCV, self).write(vals)

        fields_to_sync = {'category_id', 'warehouse_id', 'name'}
        if fields_to_sync.intersection(vals.keys()):
            self._sync_category_cv_lines(previous_categories=category_changes)

        return res

    def unlink(self):
        lines = self.env['categ.product.cv.line'].search([('cv_id', 'in', self.ids)])
        if lines:
            lines.unlink()
        return super(ProductCV, self).unlink()


