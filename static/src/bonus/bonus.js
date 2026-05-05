/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class VinaduyBonus extends Component {
    static template = "vinaduy_crm.Bonus";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const today = new Date();
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            year: today.getFullYear(),
            month: today.getMonth() + 1,
        });

        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "vinaduy.crm.dashboard",
                "get_bonus_data",
                [this.state.year, this.state.month]
            );
            this.state.error = null;
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.loading = false;
        }
    }

    async changeMonth(delta) {
        let m = this.state.month + delta;
        let y = this.state.year;
        if (m < 1) { m = 12; y -= 1; }
        if (m > 12) { m = 1; y += 1; }
        this.state.month = m;
        this.state.year = y;
        await this.reload();
    }

    formatVND(amount) {
        if (!amount) return "0 ₫";
        return new Intl.NumberFormat("vi-VN").format(amount) + " ₫";
    }

    medal(idx) {
        if (idx === 0) return "🥇";
        if (idx === 1) return "🥈";
        if (idx === 2) return "🥉";
        return `${idx + 1}.`;
    }

    openUserLeads(userId) {
        const start = `${this.state.year}-${String(this.state.month).padStart(2, "0")}-01 00:00:00`;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "KH chốt của NV",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["user_id", "=", userId],
                ["stage_id.is_won", "=", true],
                ["create_date", ">=", start],
            ],
            target: "current",
        });
    }
}

registry.category("actions").add("vinaduy_bonus", VinaduyBonus);
