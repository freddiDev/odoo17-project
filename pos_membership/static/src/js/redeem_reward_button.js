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

    _getUsedPoints() {
        const order = this.pos.get_order();
        if (!order) return 0;

        let usedPoints = 0;
        order.get_orderlines().forEach((line) => {
            const isReward = line.is_reward_redeem || line.isRewardLine?.() || false;
            const points = Number(line.pts) || 0;
            if (isReward && points > 0) {
                usedPoints += points;
            }
        });
        return usedPoints;
    }

    async onClick() {
        const order = this.pos.get_order();
        const totalOrder = order.get_total_with_tax();
        const partner = order.get_partner();
        const partner_id = partner ? partner.id : false;

        if(totalOrder <= 0){
            await this.popup.add(ConfirmPopup, {
                title: _t("Invalid Order Total"),
                body: _t("Total order harus lebih besar dari 0 untuk menggunakan fitur Redeem/Reward."),
                confirmText: _t("OK"),
            });
            return;
        }

        if (!partner) {
            await this.popup.add(ConfirmPopup, {
                title: _t("No Customer Selected"),
                body: _t("Pilih pelanggan terlebih dahulu untuk menggunakan fitur Redeem/Reward."),
                confirmText: _t("OK"),
            });
            return;
        }

        const usedPoints = this._getUsedPoints();
        const result = await this.orm.call(
            "pos.session",
            "get_reward_products",
            [this.pos.pos_session.id],
            { partner_id, used_points: usedPoints }
        );

        const minAmount = result?.product_rewards?.[0]?.min_order_amount || 0;

        let productRewards = Array.isArray(result?.product_rewards)
            ? result.product_rewards
            : Object.values(result?.product_rewards || {});

        if (totalOrder < minAmount) {
            productRewards = [];
        }

        const discountRewards = Array.isArray(result?.discount_rewards)
            ? result.discount_rewards
            : Object.values(result?.discount_rewards || {});

        const remaining_points = partner.pos_loyal_point - usedPoints;
        if ((!productRewards || productRewards.length === 0) &&
            (!discountRewards || discountRewards.length === 0)) {

            await this.popup.add(ConfirmPopup, {
                title: _t("No Rewards Available"),
                body: _t(`Tidak ada reward maupun redeem points yang tersedia.\nSisa Poin Anda: ${remaining_points}`),
                confirmText: _t("OK"),
            });
            return;
        }

        await this.popup.add(RedeemRewardPopupWidget, {
            product_rewards: productRewards,
            discount_rewards: discountRewards,
            available_points: remaining_points,
        });
    }
}

ProductScreen.addControlButton({
    component: RedeemRewardButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: () => true,
});
