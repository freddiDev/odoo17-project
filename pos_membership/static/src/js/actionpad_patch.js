/** @odoo-module */
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PromotionPopup } from "@pos_membership/js/promotion_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(ActionpadWidget.prototype, {

	setup() {
        if (super.setup) super.setup();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.pos = usePos(); 
    },

    get isMembershipActive() {
        return true;
    },

    async onClickPromotion() {
        const order = this.pos.get_order();
        if (!order) return;

        const lines = order.orderlines
            .filter(l => !l.extras?.is_promotion_reward)
            .map(l => ({
                product_id: l.product.id,
                price_subtotal: l.get_display_price(),
            }));

        const rewards = await this.orm.call(
            "loyalty.program",
            "get_pos_reward_products",
            [lines]
        );

        if (!rewards.length) return;

        const { confirmed, payload } = await this.popup.add(PromotionPopup, {
            rewards,
        });

        if (!confirmed) return;

        const product = this.pos.db.get_product_by_id(payload.product_id);
        if (!product) return;

        order._promotionLocked = true;
        order.is_have_promotion = false;

        await order.add_product(product, {
            price: 0,
            extras: { is_promotion_reward: true },
        });

        this.env.services.pos.showScreen("PaymentScreen");
    },


    
});
