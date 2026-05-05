/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STAGE_COLORS = {
    "Khách mới": "#0dcaf0",
    "Có tiềm năng": "#0d6efd",
    "Báo giá": "#fd7e14",
    "Tiềm năng đàm phán": "#6f42c1",
    "Tiềm năng hợp đồng": "#0a58ca",
    "Tiềm năng gấp": "#dc3545",
    "Chốt": "#198754",
    "Khách không có nhu cầu": "#343a40",
};

class VinaduyTracker extends Component {
    static template = "vinaduy_crm.Tracker";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ data: null, loading: true, error: null, search: "" });

        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("vinaduy.crm.dashboard", "get_tracker_data", []);
            this.state.error = null;
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.loading = false;
        }
    }

    stageColor(name) {
        return STAGE_COLORS[name] || "#6c757d";
    }

    openLead(leadId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: leadId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async advanceStage(ev, leadId) {
        ev.stopPropagation();
        const res = await this.orm.call("vinaduy.crm.dashboard", "tracker_advance_stage", [leadId]);
        if (res.success) {
            this.notification.add(`✅ Đã chuyển sang ${res.stage_name}`, { type: "success" });
            await this.reload();
        } else {
            this.notification.add(`⚠️ ${res.message}`, { type: "warning" });
        }
    }

    async postponeCallback(ev, leadId, days) {
        ev.stopPropagation();
        const res = await this.orm.call("vinaduy.crm.dashboard", "tracker_postpone_callback", [leadId, days]);
        if (res.success) {
            this.notification.add(`⏰ Đã dời lịch sang ${res.new_date}`, { type: "info" });
            await this.reload();
        }
    }

    callPhone(ev, phone) {
        ev.stopPropagation();
        if (phone) {
            window.location.href = `tel:${phone.replace(/\s/g, "")}`;
        }
    }

    filterBySearch(list) {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) return list;
        return list.filter(
            (l) =>
                (l.name || "").toLowerCase().includes(q) ||
                (l.phone || "").includes(q) ||
                (l.user_name || "").toLowerCase().includes(q) ||
                (l.stage_name || "").toLowerCase().includes(q)
        );
    }
}

registry.category("actions").add("vinaduy_tracker", VinaduyTracker);
