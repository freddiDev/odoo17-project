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
        const products = await this.orm.call(
            "pos.session",
            "get_reward_products",
            [this.pos.pos_session.id],
            { partner_id }
        );
        if (!products.length) {
            await this.popup.add(ConfirmPopup, {
                title: _t("No Points and No Reward Products"),
                body: _t(
                    "There are no reward products available for redemption."
                ),
                confirmText: _t("OK"),
            });
            return;
        }

        for (const prd of products) {
            prd.rr_image_url = `${window.location.origin}${prd.image_url}`;
        }

        await this.popup.add(RedeemRewardPopupWidget, { products });
    }
}

ProductScreen.addControlButton({
    component: RedeemRewardButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return true;
    },
});
