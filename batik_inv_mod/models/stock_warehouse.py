from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    location_count = fields.Integer(string='Locations', compute='_compute_location_count')
    subsequence = fields.Integer('Subsequence', required=True,
        help='This field is used to generate the branch code. It is a sequence of characters that will be appended to the branch code.')


    @api.constrains('subsequence')
    def _check_unique_subsequence(self):
        for rec in self:
            if rec.subsequence and self.search_count([
                ('subsequence', '=', rec.subsequence),
                ('id', '!=', rec.id)
            ]) > 0:
                raise ValidationError("The branch subsequence must be unique.")



    def _create_transit_location(self):
        """
        Create a transit location for the warehouse.
        """
        location_obj = self.env['stock.location']
        location_vals = {
            'name': _('Transit Location'),
            'usage': 'transit',
            'location_id': self.lot_stock_id.location_id.id,
            'warehouse_id': self.id,
            'active': True,
        }
        transit_location = location_obj.create(location_vals)
        return transit_location


    @api.model
    def create(self, vals):
        """
        Override the create method to set the name of the location
        based on the warehouse name.
        """
        res = super(StockWarehouse, self).create(vals)
        location_obj = self.env['stock.location']
        if res:
            res.lot_stock_id.warehouse_id = res.id
            res._create_transit_location()
        return res 

    def _compute_location_count(self):
        for warehouse in self:
            location_count = self.env['stock.location'].search_count([('warehouse_id', '=', warehouse.id)])
            warehouse.location_count = location_count


    def action_view_locations(self):
        self.ensure_one()
        action = self.env.ref('stock.action_location_form').read()[0]
        action['domain'] = [('warehouse_id', '=', self.id)] 
        action['context'] = {
            'create': False,
            'edit': False,
            'delete': False,
            'search_default_warehouse_id': self.id,
        }
        action['res_model'] = 'stock.location'
        action['view_type'] = 'form'
        action['view_mode'] = 'tree'
        action['target'] = 'current'
        return action