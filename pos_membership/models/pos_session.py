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

    def _get_pos_ui_product_product(self, params):
        result = super()._get_pos_ui_product_product(params)
        redeem_product_id = self.config_id.redeem_product_id.id
        product_ids_set = {product['id'] for product in result}

        if self.config_id.redeem_product_id and (
                redeem_product_id) not in product_ids_set:
            product_model = self.env['product.product'].with_context(
                **params['context'])
            product = product_model.search_read([(
                'id', '=', redeem_product_id
            )], fields=params['search_params']['fields'])
            self._process_pos_ui_product_product(product)
            result.extend(product)
        return result
