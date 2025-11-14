/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { RedeemRewardPopupWidget } from "@pos_membership/js/RedeemRewardPopupWidget";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";

export class RedeemRewardButton extends Component {
    static template = "pos_membership.RedeemRewardButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
    }

    async onClick() {
        const partner = this.pos.get_order().get_partner();
        const partner_id = partner ? partner.id : false;

        // call backend
        const result = await this.orm.call(
            "pos.session",
            "get_reward_products",
            [this.pos.pos_session.id],
            { partner_id }
        );

        // Normalize backend result that is expected to be an object:
        // { product_rewards: [...], discount_rewards: [...] }
        const productRewards = Array.isArray(result?.product_rewards)
            ? result.product_rewards
            : Object.values(result?.product_rewards || {});

        const discountRewards = Array.isArray(result?.discount_rewards)
            ? result.discount_rewards
            : Object.values(result?.discount_rewards || {});

        // If both empty -> show message
        if ((!productRewards || productRewards.length === 0) &&
            (!discountRewards || discountRewards.length === 0)) {
            await this.popup.add(ConfirmPopup, {
                title: _t("No Rewards Available"),
                body: _t("Tidak ada reward maupun redeem points."),
                confirmText: _t("OK"),
            });
            return;
        }

        // Pass both lists to single popup which will show categories first
        await this.popup.add(RedeemRewardPopupWidget, {
            product_rewards: productRewards,
            discount_rewards: discountRewards,
        });
    }
}

ProductScreen.addControlButton({
    component: RedeemRewardButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: () => true,
});
