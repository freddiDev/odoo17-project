from odoo import models, fields, api
from itertools import product


class WizProductMultiple(models.TransientModel):
    _name = 'wiz.product.multiple'
    _description = 'Wizard for Multiple Product Creation'

    name = fields.Char(string='Name')
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True)
    motif_id = fields.Many2one(
        'product.motif', string='Product Motif', required=True)
    model_id = fields.Many2one('product.model', string='Product Model', required=True)
    line_ids = fields.One2many(
        'wiz.product.multiple.line', 'wizard_id', string='Product Lines'
    )

    def action_confirm(self):
        self.ensure_one()
        seq = self.env['ir.sequence']

        vendor_code = self.partner_id.code or "X"
        motif = self.motif_id
        model = self.model_id or "X"
        created_product_ids = []

        for line in self.line_ids:
            colors = line.color_ids
            sizes = line.size_ids
            category = line.category_id
            name = line.product_name
            is_auto = line.is_automated

            combinations = product(colors, sizes)

            for color, size in combinations:
                if is_auto:
                    code = f"{vendor_code}{motif.code}-{model.name}{color.code}{size.size}"
                else:
                    code = ""

                product_vals = {
                    'name': f"{name}-{color.name} {size.name}",
                    'type': 'product',
                    'default_code': code,
                    'barcode': code,
                    'model_id': self.model_id.id,
                    'categ_id': category.id,
                    'color_id': color.id,
                    'size_id': size.id,
                    'motif_id': motif.id,
                    'partner_id': self.partner_id.id,
                    'seller_ids': [(0, 0, {
                        'partner_id': self.partner_id.id,
                    })],
                }
                product_generated = self.env['product.template'].with_context(is_multiple=True).create(product_vals)
                for item in product_generated:
                    item._compute_prodct_cv()
                created_product_ids.append(product_generated.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Products',
            'view_mode': 'kanban,form',
            'res_model': 'product.template',
            'domain': [('id', 'in', created_product_ids)],
            'context': self.env.context,
        }


class WizProductMultipleLine(models.TransientModel):
    _name = 'wiz.product.multiple.line'
    _description = 'Wizard Product Multiple Line'

    name = fields.Char(string='Name')
    wizard_id = fields.Many2one(
        'wiz.product.multiple', string='Wizard Reference', required=True
    )
    category_id = fields.Many2one(
        'product.category', string='Product Category', required=True
    )
    color_ids = fields.Many2many(
        'product.color', string='Product Colors', required=True
    )
    size_ids = fields.Many2many(
        'product.size', string='Product Sizes', required=True
    )
    is_automated = fields.Boolean(string='Auto Generate', default=False)
    product_name = fields.Char(string='Product Name', required=True)