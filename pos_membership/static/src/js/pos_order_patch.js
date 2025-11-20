/** @odoo-module **/

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(Order.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.estimated_point = this.estimated_point || 0;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.estimated_point = json.estimated_point || 0;
    },

    setEstimatedPoint(value) {
        this.estimated_point = value || 0;
        this.env.bus.trigger("order-updated");
    },

    getEstimatedPoint() {
        return this.estimated_point || 0;
    },
});

patch(Orderline.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.is_reward_redeem = this.is_reward_redeem || false;
        json.pts = this.pts || 0;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.is_reward_redeem = json.is_reward_redeem || false;
        this.pts = json.pts || 0;
    },
});

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        this.rpc = useService("rpc");
        this.pos = usePos();

        const order = this.pos.get_order();
        if (order) this.patchOrder(order);

        this.pos.orderHooks = this.pos.orderHooks || [];
        this.pos.orderHooks.push((newOrder) => this.patchOrder(newOrder));

        this.env.bus.addEventListener("order-updated", () => this.render());
    },

    patchOrder(order) {
        if (!order || order._membershipPatched) return;

        const origAdd = order.add_product?.bind(order);
        if (origAdd) {
            order.add_product = async (...args) => {
                const res = await origAdd(...args);
                this.updateEstimatedPoints(order);
                return res;
            };
        }

        const origRemove = order.removeOrderline?.bind(order);
        if (origRemove) {
            order.removeOrderline = (...args) => {
                const res = origRemove(...args);
                this.updateEstimatedPoints(order);
                return res;
            };
        }

        const origSetPartner = order.set_partner?.bind(order);
        if (origSetPartner) {
            order.set_partner = (...args) => {
                const res = origSetPartner(...args);
                this.updateEstimatedPoints(order);
                return res;
            };
        }

        order._membershipPatched = true;
        this.updateEstimatedPoints(order);
    },

    async updateEstimatedPoints(order) {
        if (!order) return;

        const partner = order.partner;
        if (!partner) {
            order.setEstimatedPoint(0);
            return;
        }

        const minimum_amount = partner.pos_minimum_amount || 0;
        const reward_amount = partner.pos_reward_point_amount || 0;

        if (minimum_amount <= 0 || reward_amount <= 0) {
            order.setEstimatedPoint(0);
            return;
        }

        const total = order.get_total_with_tax?.() || 0;
        const estimated = Math.ceil(total / minimum_amount) * reward_amount;

        order.setEstimatedPoint(estimated);
    },
});
