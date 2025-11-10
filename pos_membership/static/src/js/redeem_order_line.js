/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/store/models";

patch(Orderline.prototype, {
    setup() {
        super.setup?.(...arguments);
        this.is_reward_redeem = this.is_reward_redeem ?? false;
        this.pts = this.pts ?? 0;
    },

    clone() {
        const newLine = super.clone?.(...arguments) ?? Object.create(this);
        newLine.is_reward_redeem = this.is_reward_redeem;
        newLine.pts = this.pts;
        return newLine;
    },

    export_as_JSON() {
        const json = super.export_as_JSON?.(...arguments) || {};
        json.is_reward_redeem = this.is_reward_redeem;
        json.pts = this.pts;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON?.(...arguments);
        this.is_reward_redeem = json.is_reward_redeem ?? false;
        this.pts = json.pts ?? 0;
    },

    isRewardLine() {
        return this.is_reward_redeem === true;
    },
});
