/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";

export class PromotionPopup extends AbstractAwaitablePopup {
    static template = "PromotionPopup";

    selectProduct(product) {
        this.props.resolve({
            confirmed: true,
            payload: product,
        });
        this.props.close();
    }

    cancel() {
        this.props.resolve({ confirmed: false });
        this.props.close();
    }
}
