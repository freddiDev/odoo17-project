/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";

export class PromotionPopup extends AbstractAwaitablePopup {
    static template = "PromotionPopup";

    constructor() {
        super(...arguments);
        this.selectedProduct = null; 
    }

    selectProduct(product) {
        if (!product) return;
        this.selectedProduct = product;
    }

    confirm() {
        if (!this.selectedProduct) return;
        this.props.resolve({
            confirmed: true,
            payload: this.selectedProduct,
        });
        this.props.close();
    }
}
