/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class RedeemPointsInputPopup extends AbstractAwaitablePopup {
    static template = "pos_membership.RedeemPointsInputPopup";

    setup() {
        this.popup = useService("popup");
        this.state = {
            points: 0,
        };

        const req = Number(this.props.reward.required_points || 0);
        const maxp = Number(this.props.reward.max_points || 0);

        this.state.points = req > 0 ? Math.min(req, maxp) : Math.min(0, maxp);
    }

    get computed_discount() {
        const points = Number(this.state.points || 0);
        const req = Number(this.props.reward.required_points || 0);
        const max_amt = Number(this.props.reward.discount_max_amount || 0);
        if (!req || points < req) {
            return 0;
        }
        return Math.ceil((points / req) * max_amt);
    }

    onChangePoints(ev) {
        let v = Number(ev.target.value || 0);
        const maxp = Number(this.props.reward.max_points || 0);
        const req = Number(this.props.reward.required_points || 0);

        if (v < 0) v = 0;
        if (maxp && v > maxp) v = maxp;

        this.state.points = v;
        this.render();
    }

    async confirm() {
        const points = Number(this.state.points || 0);
        const req = Number(this.props.reward.required_points || 0);

        if (!req || points < req) {
            await this.popup.add("ConfirmPopup", {
                title: _t("Invalid Points"),
                body: _t("Masukkan poin minimal sesuai konfigurasi."),
                confirmText: _t("OK"),
            });
            return;
        }

        this.props.close({ confirmed: true, points });
    }

    cancel() {
        this.props.close({ confirmed: false });
    }
}
