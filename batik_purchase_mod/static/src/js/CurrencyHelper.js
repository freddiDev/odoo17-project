/** @odoo-module **/

import { formatFloat } from "@web/core/utils/numbers";

export function CurrencyHelper(env) {
    const rpc = env.services.rpc;
    const user = env.services.user;
    let cachedCurrency = null;

    async function loadCurrency() {
        if (cachedCurrency) return cachedCurrency;
        const company = await rpc.query({
            model: "res.company",
            method: "read",
            args: [[user.context.allowed_company_ids[0]], ["currency_id"]],
        });

        if (company.length) {
            const currency = await rpc.query({
                model: "res.currency",
                method: "read",
                args: [[company[0].currency_id[0]], ["name", "symbol", "position", "decimal_places"]],
            });
            cachedCurrency = currency[0];
        }
        return cachedCurrency;
    }

    async function format(value) {
        const currency = await loadCurrency();
        return formatFloat(value || 0, {
            currency: currency.name,
            digits: [0, currency.decimal_places || 0],
            position: currency.position,
            symbol: currency.symbol,
        });
    }

    return { loadCurrency, format };
}
