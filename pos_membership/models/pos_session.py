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

            # do not mutate remaining_points here. show all product rewards that are affordable
            lines = product_rewards.mapped('loyalry_reward_product_ids').sorted(
                lambda l: l.reedem_points or 0, reverse=True
            )

            for line in lines:
                rp = int(line.reedem_points or 0)
                # only show if partner has minimal points for that product
                if remaining_points < rp:
                    continue

                product = line.product_id
                if product:
                    result_products["product_rewards"].append({
                        "id": product.id,
                        "display_name": f"{product.display_name} (Free)",
                        "lst_price": 0.0,
                        "used_points": rp,
                        "required_points": rp,
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
                # Note: if multiple discount_rewards found, iterate them (but typical setup has one)
                for dr in discount_rewards:
                    req = int(getattr(dr, 'required_points', 0) or 0)
                    max_amt = float(getattr(dr, 'discount_max_amount', 0.0) or 0.0)

                    # only allow discount option if at least minimal required points satisfied
                    if req and remaining_points >= req and config.redeem_product_id:
                        redeem_product = config.redeem_product_id
                        # Provide metadata for frontend to compute variable discount based on user input
                        # default used_points = 0 (frontend will ask user how many points to use)
                        # lst_price default 0 (frontend sets negative price)
                        result_products["discount_rewards"].append({
                            "id": redeem_product.id,
                            "display_name": f"{redeem_product.display_name} (Discount)",
                            "lst_price": 0.0,
                            "used_points": 0,
                            "required_points": req,
                            "discount_max_amount": max_amt,
                            "max_points": remaining_points,
                            "image_url": f"/web/image?model=product.product&id={redeem_product.id}&field=image_128",
                        })

        return result_products






