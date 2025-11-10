/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";

export class RedeemRewardPopupWidget extends AbstractAwaitablePopup {
    static template = "pos_membership.RedeemRewardPopupWidget";

    setup() {
        this.pos = usePos();
    }

    go_back_screen() {
        this.pos.showScreen("ProductScreen");
        this.env.posbus.trigger("close-popup", {
            popupId: this.props.id,
        });
    }

    get products() {
        const products = [];
        for (const prd of this.props.products || []) {
            prd.rr_image_url = `/web/image?model=product.product&field=image_128&id=${prd.id}&write_date=${prd.write_date || ""}&unique=1`;
            products.push(prd);
        }
        return products;
    }

    click_on_rr_product(event) {
        const product_id = parseInt(event.currentTarget.dataset.productId);
        const selectedReward = (this.props.products || []).find(p => p.id === product_id);
        const product = this.pos.db.get_product_by_id(product_id);
        if (product && selectedReward) {
            const order = this.pos.get_order();
            const line = order.add_product(product, {
                price: selectedReward.lst_price,
            });
        }
        this.pos.showScreen("ProductScreen");
        this.props.close({ confirmed: true });
    }
}
