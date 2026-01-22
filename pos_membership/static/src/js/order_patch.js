/** @odoo-module */
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async _checkPromotionEligibility() {
        // HARD STOP: jika promo sudah dipakai
        if (this._promotionLocked) {
            return;
        }

        const lines = this.orderlines
            .filter(l => !l.extras?.is_promotion_reward)
            .map(l => ({
                product_id: l.product.id,
                price_subtotal: l.get_display_price(),
            }));

        if (!lines.length) {
            this.is_have_promotion = false;
            return;
        }

        const rewards = await this.pos.orm.call(
            "loyalty.program",
            "get_pos_reward_products",
            [lines]
        );

        this.is_have_promotion = !!rewards.length;
    },

    async add_product(product, options) {
        const res = await super.add_product(product, options);
        // JANGAN cek eligibility kalau reward promo
        if (!options?.extras?.is_promotion_reward) {
            await this._checkPromotionEligibility();
        }
        return res;
    },
});

patch(Orderline.prototype, {
    get_display_name() {
        const name = super.get_display_name();
        if (this.extras?.is_promotion_reward) {
            return `${name} (FREE)`;
        }
        return name;
    },
});
