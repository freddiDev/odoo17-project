/** @odoo-module */
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {

    async _checkPromotionEligibility() {
        // Reset jika cart kosong
        if (!this.orderlines.length) {
            this.is_have_promotion = false;
            this._promotionLocked = false;
            return;
        }

        // Jangan cek jika reward masih ada di cart
        const hasReward = this.orderlines.some(
            l => l.extras?.is_promotion_reward
        );
        if (hasReward) {
            this.is_have_promotion = false;
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

    async add_product(product, options = {}) {
        const res = await super.add_product(product, options);
        if (!options?.extras?.is_promotion_reward) {
            await this._checkPromotionEligibility();
        }
        return res;
    },

    async remove_orderline(line) {
        await super.remove_orderline(line);
        await this._checkPromotionEligibility();
    },
});

patch(Orderline.prototype, {
    set_quantity(quantity, keep_price) {
        const res = super.set_quantity(quantity, keep_price);
        if (this.order) {
            this.order._checkPromotionEligibility();
        }
        return res;
    },

    get_display_name() {
        const name = super.get_display_name();
        if (this.extras?.is_promotion_reward) {
            return `${name} (FREE)`;
        }
        return name;
    },
});
