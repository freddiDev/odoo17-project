/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { RedeemRewardPopupWidget } from "@pos_membership/js/RedeemRewardPopupWidget";

export class RedeemRewardButton extends Component {
    static template = "pos_membership.RedeemRewardButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    async onClick() {
        const selectedOrder = this.pos.get_order();
        const redeem_product_id = this.pos.config.redeem_product_id;

        if (redeem_product_id) {
            console.log("Redeem Product IDs:", redeem_product_id);

            // Pastikan array
            const products = Array.isArray(redeem_product_id) ? redeem_product_id : [redeem_product_id];

            if (products.length === 1) {
                const product = this.pos.db.get_product_by_id(products[0]);
                if (product) {
                    selectedOrder.add_product(product);
                    this.pos.set_order(selectedOrder);
                    this.pos.showScreen("ProductScreen");
                }
            } else {
                // Untuk multiple produk
                const productObjs = [];
                for (const prdId of products) {
                    const prd = this.pos.db.get_product_by_id(prdId);
                    if (prd) {
                        prd.image_url = `${window.location.origin}/web/binary/image?model=product.product&field=image_medium&id=${prd.id}`;
                        productObjs.push(prd);
                    }
                }
                await this.popup.add(RedeemRewardPopupWidget, { products: productObjs });
            }
        }
    }
}

ProductScreen.addControlButton({
    component: RedeemRewardButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return this.pos.config.redeem_product_id;
    },
});
