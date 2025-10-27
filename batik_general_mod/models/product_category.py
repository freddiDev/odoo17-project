from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    cv_ids = fields.One2many('categ.product.cv.line', 'category_id', string="CV")
    model_code = fields.Char(string="Kode Model")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    @api.constrains('cv_ids')
    def _check_unique_warehouse_id_cv_per_product(self):
        """Check Unique warehouse_id and CV.
        This constrains will be blocking any duplicate data warehouse,
        return => string('Message')
        """
        for cv in self:
            warehouse_cv_map = {}
            for line in cv.cv_ids:
                if line.warehouse_id.id in warehouse_cv_map:
                    if warehouse_cv_map[line.warehouse_id.id] != line.cv_id.id or warehouse_cv_map[line.warehouse_id.id] == line.cv_id.id:
                        raise ValidationError("Maaf Hanya Dapat Mendaftarkan 1 Cabang 1 CV saja")
                else:
                    warehouse_cv_map[line.warehouse_id.id] = line.cv_id.id


    def write(self, vals):
        """Override write method to update product.template.cv.line when categ.product.cv.line is updated."""
        res = super(ProductCategory, self).write(vals)

        if 'cv_ids' in vals:
            for category in self:
                products = self.env['product.template'].search([('categ_id', '=', category.id)])
                for product in products:
                    for cv_line in category.cv_ids:
                        existing_lines = product.product_cv_template_ids.filtered(
                            lambda l: l.warehouse_id == cv_line.warehouse_id
                        )
                        if existing_lines:
                            existing_lines.write({
                                'cv_id': cv_line.cv_id.id,
                            })
                        else:
                            product.product_cv_template_ids.create({
                                'product_template_id': product.id,
                                'warehouse_id': cv_line.warehouse_id.id,
                                'cv_id': cv_line.cv_id.id,
                            })

        return res

        

    class CategProductCV(models.Model):
        _name = 'categ.product.cv.line'
        _description = 'Category Product CV Line'

        name = fields.Char(string="Name")
        category_id = fields.Many2one('product.category', string="Category")
        warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
        cv_id = fields.Many2one('product.cv', string="CV")
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