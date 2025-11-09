//** @odoo-module */
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ActionpadWidget.prototype, {

    get isMembershipActive() {
        return true;
    },

    
});
