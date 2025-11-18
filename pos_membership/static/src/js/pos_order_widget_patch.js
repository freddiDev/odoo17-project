/** @odoo-module **/

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";


patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get EstimatedPoint() {
        const order = this.pos.get_order();

        if (!order) return 0;

        const v = order.getEstimatedPoint();

        return v;
    },
});
