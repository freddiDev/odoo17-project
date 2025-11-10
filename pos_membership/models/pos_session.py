from odoo import api, fields, models, _


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

    @api.model
    def get_reward_products(self, partner_id=False):
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        config = self.env['pos.config'].search([], limit=1)
        result_products = []
        programs = self.env['loyalty.program'].search([
            ('pos_loyalty_type', '=', 'reedem'),
            ('active', '=', True),
        ])
        for program in programs:
            if program.reward_ids and partner:
                discount_rewards = self.env['loyalty.reward'].search([
                    ('member_type_ids', 'in', partner.member_type_id.id if partner and partner.member_type_id else []),
                    ('program_id', '=', program.id),
                    ('reward_type', '=', 'discount'),
                    ('program_id.active', '=', True),
                ])
                if discount_rewards and partner.pos_loyal_point and partner.pos_loyal_point > 0:
                    required_points = getattr(discount_rewards, 'required_points', 0)
                    discount_max_amount = getattr(discount_rewards, 'discount_max_amount', 0.0)
                    if required_points and partner.pos_loyal_point >= required_points:
                        discount_value = (partner.pos_loyal_point / required_points) * discount_max_amount
                        redeem_product = config.redeem_product_id
                        if redeem_product:
                            result_products.append({
                                'id': redeem_product.id,
                                'display_name': f"{redeem_product.display_name} (Discount Rp {discount_value:,.0f})",
                                'lst_price': -abs(discount_value),
                                'image_url': f"/web/image?model=product.product&id={redeem_product.id}&field=image_128",
                            })
            product_rewards = self.env['loyalty.reward'].search([
                ('member_type_ids', 'in', partner.member_type_id.id if partner and partner.member_type_id else []),
                ('program_id', '=', program.id),
                ('reward_type', '=', 'product'),
                ('program_id.active', '=', True),
            ])
            if not product_rewards:
                continue
            all_lines = product_rewards.mapped('loyalry_reward_product_ids')
            reward_lines = all_lines.sorted(lambda l: l.reedem_points or 0, reverse=True)
            remaining_points = int(partner.pos_loyal_point or 0)
            for reward_line in reward_lines:
                if remaining_points <= 0:
                    break
                rp = int(reward_line.reedem_points or 0)
                if remaining_points < rp:
                    continue
                product = reward_line.product_id
                if product:
                    result_products.append({
                        'id': product.id,
                        'display_name': f"{product.display_name} (Free)",
                        'lst_price': 0.0,
                        'image_url': f"/web/image?model=product.product&id={product.id}&field=image_128",
                    })
                    remaining_points -= rp
                    break
        return result_products


