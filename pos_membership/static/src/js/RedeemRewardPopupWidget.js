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

        this.state = {
            mode: "category",        // category | list
            selectedCategory: null,  // redeem_points | rewards
        };
    }

    // ------------- CATEGORY SET -------------
    get categories() {
        return [
            { code: "redeem_points", name: "Redeem Points" },
            { code: "rewards", name: "Rewards" },
        ];
    }

    // ------------- PRODUCTS -------------
    get products() {
        if (this.state.mode !== "list") return [];

        const normalize = (value) => {
            if (Array.isArray(value)) return value;
            if (value && typeof value === "object") return Object.values(value);
            return [];
        };

        if (this.state.selectedCategory === "rewards") {
            const arr = normalize(this.props.product_rewards);
            arr.forEach((p) => {
                p.rr_image_url =
                    `/web/image?model=product.product&field=image_128&id=${p.id}`;
            });
            return arr;
        }

        if (this.state.selectedCategory === "redeem_points") {
            const arr = normalize(this.props.discount_rewards);
            arr.forEach((p) => {
                p.rr_image_url =
                    `/web/image?model=product.product&field=image_128&id=${p.id}`;
            });
            return arr;
        }

        return [];
    }

    // ------------- CLICK CATEGORY -------------
    clickCategory(ev) {
        const cat = ev.currentTarget.dataset.cat;
        if (!cat) return;

        this.state.selectedCategory = cat;
        this.state.mode = "list";

        this.render();  // <= WAJIB pada popup Odoo 17
    }

    // ------------- CLICK PRODUCT -------------
    async click_on_rr_product(ev) {
        const product_id = Number(ev.currentTarget.dataset.productId);
        if (!product_id) return;

        const normalize = (val) =>
            Array.isArray(val) ? val : Object.values(val || {});

        const list =
            this.state.selectedCategory === "rewards"
                ? normalize(this.props.product_rewards)
                : normalize(this.props.discount_rewards);

        const selectedReward = list.find((p) => Number(p.id) === product_id);
        if (!selectedReward) return;

        const product = this.pos.db.get_product_by_id(product_id);
        const order = this.pos.get_order();

        const exists = order.get_orderlines().some((line) => {
            try {
                return (
                    Number(line.get_product().id) === Number(product.id) &&
                    line.is_reward_redeem
                );
            } catch {
                return false;
            }
        });

        if (exists) {
            await this.popup.add(ConfirmPopup, {
                title: _t("Duplicate Reward"),
                body: _t(
                    `Product "${product.display_name}" sudah diredeem.\n` +
                        `Hapus dari cart terlebih dahulu jika ingin menambah ulang.`
                ),
                confirmText: _t("OK"),
            });
            return;
        }

        const line = order.add_product(product, {
            price: selectedReward.lst_price,
            merge: false,
        });

        line.is_reward_redeem = true;
        line.pts = selectedReward.used_points || 0;

        this.props.close({ confirmed: true });
    }
}
