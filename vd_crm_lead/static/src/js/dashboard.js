/** @odoo-module **/
/**
 * VD CRM Dashboard — single-screen view of: who needs attention, today's work,
 * error reports, and a stage-by-stage queue.
 *
 * Data flow:
 *   onWillStart → dashboard_data() → renders 4 panels + stage tabs
 *   selectStage → dashboard_leads(stage_id) → fills right pane
 *
 * Click a lead row to open it (form view), click "Gọi" to dial via vd_stringee.
 */
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class VdCrmDashboard extends Component {
    static template = "vd_crm_lead.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.stringee = useService("stringee");

        this.state = useState({
            loading: true,
            user: { id: 0, name: "" },
            is_manager: false,
            users: [],
            // 0 = "Tất cả NV" (manager view); otherwise the chosen user's id.
            selectedUserId: 0,
            kpi: {},
            errors: {},
            stages: [],
            selectedStageId: null,
            leads: [],
            leadsLoading: false,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;
        const userParam = this.state.selectedUserId || "all";
        const [data, users] = await Promise.all([
            this.orm.call("crm.lead", "dashboard_data", [userParam]),
            this.state.users.length
                ? Promise.resolve(this.state.users)
                : this.orm.call("crm.lead", "dashboard_users", []),
        ]);
        Object.assign(this.state, data);
        this.state.users = users;
        this.state.selectedUserId = data.selected_user_id || 0;
        const firstActive = data.stages.find((s) => !s.is_lost && s.count > 0)
            || data.stages.find((s) => !s.is_lost)
            || data.stages[0];
        if (firstActive) {
            await this.selectStage(firstActive.id);
        } else {
            this.state.leads = [];
            this.state.selectedStageId = null;
        }
        this.state.loading = false;
    }

    async onUserChange(ev) {
        const val = ev.target.value;
        this.state.selectedUserId = val === "all" ? 0 : parseInt(val, 10);
        await this.loadDashboard();
    }

    async selectStage(stageId) {
        this.state.selectedStageId = stageId;
        this.state.leadsLoading = true;
        const userParam = this.state.selectedUserId || "all";
        this.state.leads = await this.orm.call(
            "crm.lead", "dashboard_leads", [stageId, userParam],
        );
        this.state.leadsLoading = false;
    }

    get selectedStage() {
        return this.state.stages.find((s) => s.id === this.state.selectedStageId);
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

    async callLead(lead, ev) {
        ev.stopPropagation();
        if (!lead.phone) {
            this.notification.add("KH chưa có SĐT.", { type: "warning" });
            return;
        }
        try {
            await this.stringee.call(lead.phone);
            this.notification.add(`Đang gọi ${lead.name} (${lead.phone})`, { type: "info" });
        } catch (e) {
            this.notification.add(e.message || "Gọi thất bại", { type: "danger" });
        }
    }

    probabilityClass(prob) {
        if (prob >= 75) return "bg-success";
        if (prob >= 50) return "bg-info";
        if (prob >= 25) return "bg-warning";
        return "bg-secondary";
    }

    formatDate(s) {
        if (!s) return "";
        return s.replace("T", " ").slice(0, 16);
    }
}

registry.category("actions").add("vd_crm_lead.dashboard", VdCrmDashboard);
