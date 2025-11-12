from odoo import api, fields, models, _

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    pos_loyalty_type = fields.Selection([
        ('point', 'Plus Points'),
        ('reedem', 'Reedem'),],
        default='point', required=True,
    )
    expired_days = fields.Integer('Expired Days', default=30, help='Number of days after point creation when it will expire')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Warehouse',
        help='Warehouse used to manage the stock of loyalty products.',
    )

    reward_ids = fields.One2many(
        'loyalty.reward', 
        'program_id', 
        'Rewards', 
        copy=True, 
        readonly=False, 
        store=True,
        compute='_compute_from_program_type',
        domain=[('reward_type', '=', 'discount')],
    )

    reward_product_ids = fields.One2many(
        'loyalty.reward', 
        'program_id', 
        'Rewards', 
        copy=True, 
        readonly=False, 
        store=True,
        compute='_compute_from_program_type',
        domain=[('reward_type', '=', 'product')],
    )

    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        if self.warehouse_ids:
            configs = self.env['pos.config'].search([
                ('warehouse_id', 'in', self.warehouse_ids.ids)
            ])
            self.pos_config_ids = [(6, 0, configs.ids)]
        else:
            self.pos_config_ids = [(5, 0, 0)]

    @api.constrains('reward_ids')
    def _constrains_reward_ids(self):
        if self.env.context.get('loyalty_skip_reward_check'):
            return

        if self.pos_loyalty_type == 'point':
            return
            
        if any(not program.reward_ids for program in self):
            raise ValidationError(_('A program must have at least one reward.'))

            


class LoyaltyRules(models.Model):
    _inherit = 'loyalty.rule'

    def _get_loyalty_point_mode_selection(self):
        return [
            ('product', _('Products')),
            ('categories', _('Categories')),
            ('order_amount', _('Total Amount')),
        ]

    name = fields.Char(string='Rule Name', related='program_id.name', store=True, readonly=False)
    member_type_ids = fields.Many2many('member.type', string='Member Type')
    loyalty_point_mode = fields.Selection(selection=_get_loyalty_point_mode_selection, required=True, default='product', string="Type")

