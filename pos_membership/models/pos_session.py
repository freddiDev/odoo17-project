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
    def get_reward_products(self, pos_session=False, partner_id=False):
        partner = self.env['res.partner'].browse(partner_id)
        session = self.env['pos.session'].browse(pos_session)
        config = session.config_id
        result_products = {
            "product_rewards": [],
            "discount_rewards": [],
        }

        if not partner:
            return result_products

        programs = self.env['loyalty.program'].search([
            ('pos_loyalty_type', '=', 'reedem'),
            ('active', '=', True),
        ])
        remaining_points = int(partner.pos_loyal_point or 0)

        # ---- PRODUCT REWARDS ----
        for program in programs:
            product_rewards = self.env['loyalty.reward'].search([
                ('member_type_ids', 'in', partner.member_type_id.id),
                ('program_id', '=', program.id),
                ('reward_type', '=', 'product'),
            ])

            lines = product_rewards.mapped('loyalry_reward_product_ids').sorted(
                lambda l: l.reedem_points or 0, reverse=True
            )

            for line in lines:
                rp = int(line.reedem_points)
                if remaining_points < rp:
                    continue

                product = line.product_id
                if product:
                    result_products["product_rewards"].append({
                        "id": product.id,
                        "display_name": f"{product.display_name} (Free)",
                        "lst_price": 0.0,
                        "used_points": rp,
                        "image_url": f"/web/image?model=product.product&id={product.id}&field=image_128",
                    })

        # ---- DISCOUNT REWARDS ----
        for program in programs:
            discount_rewards = self.env['loyalty.reward'].search([
                ('member_type_ids', 'in', partner.member_type_id.id),
                ('program_id', '=', program.id),
                ('reward_type', '=', 'discount'),
            ])

            if discount_rewards and remaining_points > 0:
                req = getattr(discount_rewards, 'required_points', 0)
                max_amt = getattr(discount_rewards, 'discount_max_amount', 0.0)

                if req and remaining_points >= req:
                    val = (remaining_points / req) * max_amt

                    redeem_product = config.redeem_product_id
                    if redeem_product:
                        result_products["discount_rewards"].append({
                            "id": redeem_product.id,
                            "display_name": f"{redeem_product.display_name} (Discount Rp {val:,.0f})",
                            "lst_price": -abs(val),
                            "used_points": remaining_points,
                            "image_url": f"/web/image?model=product.product&id={redeem_product.id}&field=image_128",
                        })

        return result_products






