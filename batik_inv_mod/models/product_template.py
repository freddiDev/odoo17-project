from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


def _get_active_model_from_context(env):
    ctx = env.context
    active_model = ctx.get('model', False)
    if active_model:
        return active_model
    return False

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    related_partner_id = fields.Many2one(
        related='product_tmpl_id.partner_id',
        string="Related Partner",
        store=True
    )



class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.model
    def create(self, vals):
        """Override Create Method.
        This function will call _compute_prodct_cv method to update product_cv_template_ids"""
        ctx = self.env.context
        model = _get_active_model_from_context(self.env)
        is_multiple = ctx.get('is_multiple', False)
        if not is_multiple and model != 'loyalty_reward':
            if 'product_cv_template_ids' not in vals:
                raise ValidationError(_("Anda harus isi product CV."))

            if 'seller_ids' not in vals:
                raise ValidationError(_("Anda harus isi product supplier."))
        return super(ProductTemplate, self).create(vals)



    def write(self, vals):
        ctx = self.env.context
        model = _get_active_model_from_context(self.env)
        for record in self:
            sellers = vals.get('seller_ids', record.seller_ids)
            if not sellers and model != 'loyalty_reward':
                raise ValidationError(_("Anda harus isi product supplier."))

            res = super(ProductTemplate, self).write(vals)

            if 'product_cv_template_ids' not in vals:
                record._compute_prodct_cv()
        return res


    def _compute_prodct_cv(self):
        datas = []
        if not self.categ_id.cv_ids:
            raise ValidationError(_("Anda harus isi product CV di Product Category."))

        for line in self.categ_id.cv_ids:
            vals = {
                'product_template_id': self.id,
                'warehouse_id': line.warehouse_id.id,
                'cv_id': line.cv_id.id, 
            }
            datas.append(vals)
        self.product_cv_template_ids = [(5, 0, 0)]
        self.product_cv_template_ids = [(0, 0, data) for data in datas]


    @api.onchange('categ_id')
    def onchange_categ_id(self):
        """Onchange Product CV.
        This function will add dynamic domain to cvID field.
        return [('warehouse_id', '=', self.warehouse_id.id)]
        """
        if self.categ_id:
            self._compute_prodct_cv()
           

    @api.constrains('product_cv_template_ids')
    def _check_unique_warehouse_cv_per_product(self):
        """Check Unique Warehouse and CV.
        This constrains will be blocking any duplicate data warehouse,
        return => string('Message')
        """
        for product in self:
            warehouse_cv_map = {}
            for line in product.product_cv_template_ids:
                if line.warehouse_id.id in warehouse_cv_map:
                    if warehouse_cv_map[line.warehouse_id.id] != line.cv_id.id or warehouse_cv_map[line.warehouse_id.id] == line.cv_id.id:
                        raise ValidationError("Maaf Hanya Dapat Mendaftarkan 1 Cabang 1 CV saja")
                else:
                    warehouse_cv_map[line.warehouse_id.id] = line.cv_id.id

    model_id = fields.Many2one('product.model', string="Model")
    motif_id = fields.Many2one('product.motif', string='Motif')
    size_id = fields.Many2one('product.size', string='Size')
    color_id = fields.Many2one('product.color', string='Color')
    not_returnable = fields.Boolean('Not Returnable', default=False)
    partner_id = fields.Many2one('res.partner', string="Vendor", domain=[('supplier_rank', '>', 0)], required=True)
    product_cv_template_ids = fields.One2many('product.template.cv.line', 'product_template_id', string='Lines')


class ProductTemplateCVLine(models.Model):
    _name = 'product.template.cv.line'
    _description = 'Product CV Line'

    name = fields.Char('Name')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    cv_id = fields.Many2one('product.cv', string="CV")
    product_template_id = fields.Many2one('product.template', string="Product")
    product_cv_filter_ids = fields.Many2many('product.cv', string='VC Domain')
    

    def _computer_domain_product_cv(self):
        datas = self.env['product.cv'].search([('warehouse_id', '=', self.warehouse_id.id)])
        if datas:
            self.product_cv_filter_ids = [(6, 0, datas.ids)]


    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """Onchange Product CV.
        This function will add dynamic domain to cvID field.
        return [('warehouse_id', '=', self.warehouse_id.id)]
        """
        if self.warehouse_id:
            self.cv_id = False
            self._computer_domain_product_cv()
    


    

