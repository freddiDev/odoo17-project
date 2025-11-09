from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'] += [
            'is_membership',
            'member_type',
            'pos_loyal_point'
        ]
        return result
