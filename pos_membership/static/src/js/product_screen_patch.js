/** @odoo-module */
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PromotionPopup } from "@pos_membership/js/promotion_popup";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.env.bus.addEventListener("order-updated", () => this.render());
    },

    async showPromotionPopup() {
        const order = this.pos.get_order();
        if (!order) return;

        const orderLines = order.orderlines.map(l => ({
            product_id: l.product.id,
            price_subtotal: l.get_display_price(),
        }));

        const rewards = await this.orm.call(
            "loyalty.program",
            "get_pos_reward_products",
            [orderLines]
        );

        if (!rewards.length) return;

        const { confirmed, payload } = await this.popup.add(PromotionPopup, { rewards });
        if (!confirmed) return;

        const product = this.pos.db.get_product_by_id(payload.product_id);
        if (!product) return;

        await order.add_product(product, { price: 0, extras: { is_promotion_reward: true } });

        order.is_have_promotion = false;
        this.env.bus.trigger("order-updated");
        this.env.services.pos.showScreen("PaymentScreen");

    },
});
