/** @odoo-module */
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async _checkPromotionEligibility() {
        if (!this.orderlines.length) {
            if (this.is_have_promotion) {
                this.is_have_promotion = false;
                this._promotionRewards = [];
                this.env.bus.trigger("order-updated");
            }
            return;
        }

        const lines = this.orderlines.map(l => ({
            product_id: l.product.id,
            price_subtotal: l.get_display_price(),
        }));

        const rewards = await this.pos.orm.call(
            "loyalty.program",
            "get_pos_reward_products",
            [lines]
        );

        const newValue = !!rewards.length;
        if (this.is_have_promotion !== newValue) {
            this.is_have_promotion = newValue;
            this._promotionRewards = rewards;
            this.env.bus.trigger("order-updated");
        }
    },

    async add_product(product, options) {
        const res = await super.add_product(product, options);
        await this._checkPromotionEligibility();
        return res;
    },

    async removeOrderline(line) {
        super.removeOrderline(line);
        await this._checkPromotionEligibility();
    },
});

patch(Orderline.prototype, {
    set_quantity(quantity, keep_price) {
        const res = super.set_quantity(quantity, keep_price);
        this.order?._checkPromotionEligibility();
        return res;
    },
});
