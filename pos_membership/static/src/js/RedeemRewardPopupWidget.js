/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class RedeemRewardPopupWidget extends AbstractAwaitablePopup {
    static template = "pos_membership.RedeemRewardPopupWidget";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    get products() {
        const products = [];
        for (const prd of this.props.products || []) {
            prd.rr_image_url = `/web/image?model=product.product&field=image_128&id=${prd.id}&write_date=${prd.write_date || ""}&unique=1`;
            products.push(prd);
        }
        return products;
    }

    async click_on_rr_product(event) {
        const product_id = parseInt(event.currentTarget.dataset.productId, 10);
        const selectedReward = (this.props.products || []).find((p) => Number(p.id) === product_id);
        const product = this.pos.db.get_product_by_id(product_id);
        if (!product || !selectedReward) return;

        const order = this.pos.get_order();

        const already = order.get_orderlines().some((line) => {
            try {
                return Number(line.get_product().id) === Number(product.id) && line.is_reward_redeem === true;
            } catch (e) {
                return false;
            }
        });

        if (already) {
            await this.popup.add(ConfirmPopup, {
                title: _t("Duplicate Reward"),
                body: _t(
                    `Product "${product.display_name}" sudah diredeem.\nHapus dari cart terlebih dahulu jika ingin menambah ulang.`
                ),
                confirmText: _t("OK"),
            });
            return;
        }

        const line = order.add_product(product, {
            price: selectedReward.lst_price,
            merge: false,
        });

        // set properti di order line yang sebenarnya
        let targetLine = line;
        try {
            const lines = order.get_orderlines();
            for (let i = lines.length - 1; i >= 0; i--) {
                const l = lines[i];
                const pid = Number(l.get_product().id);
                const lprice = Number(typeof l.get_unit_price === 'function' ? l.get_unit_price() : (l.price ?? l.get_price?.() ?? 0));
                const selPrice = Number(selectedReward.lst_price || selectedReward.price || 0);
                if (pid === Number(product.id) && Math.abs(lprice - selPrice) < 0.0001 && !l.is_reward_redeem) {
                    targetLine = l;
                    break;
                }
            }
        } catch (err) {
            targetLine = line;
        }

        targetLine.is_reward_redeem = true;
        targetLine.pts = selectedReward.used_points || 0;

        this.props.close({ confirmed: true });
    }
}
