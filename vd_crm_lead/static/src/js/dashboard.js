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
            user: { id: 0, name: "", is_all: false },
            is_manager: false,
            current_user_id: 0,
            selected_user_id: 0,   // 0 = "all"
            users: [],             // [{id, name, login}] — NV để manager chọn
            kpi: {},
            errors: {},
            stages: [],
            selectedStageId: null,
            alertFilter: null,     // 'overdue_callback' | 'new_not_called' | ... | null
            leads: [],
            leadsLoading: false,
            // ===== ADMIN MODE (Manager + chọn "Tất cả NV") =====
            // Tab đang chọn trong vertical menu của admin view.
            adminTab: "overview",  // 'overview' | 'performance' | 'alerts' | 'today'
            // Slide-in panel chi tiết 1 NV (mở từ tab Thành tích).
            nvDetail: null,        // null hoặc payload dashboard_data của NV đó
            nvDetailLoading: false,
        });

        onWillStart(async () => {
            await this.loadDashboard();
            // Manager có thêm dropdown chọn NV — load danh sách NV 1 lần
            if (this.state.is_manager) {
                this.state.users = await this.orm.call("crm.lead", "dashboard_users", []);
            }
        });
    }

    async loadDashboard() {
        this.state.loading = true;
        const args = this.state.selected_user_id ? [this.state.selected_user_id] : [];
        const data = await this.orm.call("crm.lead", "dashboard_data", args);
        Object.assign(this.state, data);
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

    async onChangeUser(ev) {
        const val = ev.target.value;
        this.state.selected_user_id = val === "all" ? 0 : parseInt(val, 10);
        // Đóng NV detail panel nếu đang mở
        this.state.nvDetail = null;
        await this.loadDashboard();
    }

    // ===== ADMIN VIEW HELPERS =====
    // True khi manager đang xem "Tất cả NV" → render layout admin (menu dọc + content).
    get isAdminView() {
        return this.state.is_manager && !this.state.selected_user_id;
    }

    async selectAdminTab(tab) {
        this.state.adminTab = tab;
        // Đóng NV detail khi đổi tab
        this.state.nvDetail = null;
        // Tab "alerts" hoặc "overview" dùng leads list → load default stage nếu chưa có
        if ((tab === "overview" || tab === "alerts") && !this.state.leads.length && !this.state.selectedStageId) {
            const firstActive = this.state.stages.find((s) => !s.is_lost && s.count > 0)
                || this.state.stages.find((s) => !s.is_lost)
                || this.state.stages[0];
            if (firstActive) {
                await this.selectStage(firstActive.id);
            }
        }
    }

    async openNvDetail(userId) {
        // Slide-in panel: lấy dashboard_data scoped theo userId này (BACKEND đã có sẵn).
        this.state.nvDetailLoading = true;
        this.state.nvDetail = { loading: true };
        try {
            const data = await this.orm.call("crm.lead", "dashboard_data", [userId]);
            // Kèm danh sách KH active của NV này (limit 30) để admin nắm tổng quan
            const leads = await this.orm.call("crm.lead", "dashboard_nv_active_leads", [userId]);
            this.state.nvDetail = { ...data, active_leads: leads };
        } catch (e) {
            this.notification.add(e.message || "Lỗi tải chi tiết NV", { type: "danger" });
            this.state.nvDetail = null;
        }
        this.state.nvDetailLoading = false;
    }

    closeNvDetail() {
        this.state.nvDetail = null;
    }

    async selectStage(stageId) {
        this.state.selectedStageId = stageId;
        this.state.leadsLoading = true;
        const args = [stageId];
        if (this.state.selected_user_id) {
            args.push(this.state.selected_user_id);
        }
        this.state.leads = await this.orm.call("crm.lead", "dashboard_leads", args);
        this.state.leadsLoading = false;
    }

    get selectedStage() {
        return this.state.stages.find((s) => s.id === this.state.selectedStageId);
    }

    get isWonStage() {
        const s = this.selectedStage;
        return !!s && s.code === 'won';
    }

    pillSourceClass(lead) {
        // Khách mới — màu theo nguồn Pancake
        const code = this.selectedStage?.code;
        if (code === 'won') {
            return 'o_vd_won_urg_' + (lead.planned_sign_urgency || 'none')
                + (lead.contract_signed ? ' o_vd_won_signed' : '');
        }
        if (code === 'new') {
            return 'o_vd_pill_src_' + (lead.pancake_platform || 'manual');
        }
        // Stage khác — neutral
        return 'o_vd_pill_neutral';
    }

    pillIcon(lead) {
        const code = this.selectedStage?.code;
        if (code === 'won') {
            if (lead.contract_signed) return '🏆';
            const u = lead.planned_sign_urgency;
            if (u === 'past') return '🚨';
            if (u === 'today') return '🔥';
            if (u === 'soon') return '⏰';
            if (u === 'far') return '📅';
            return '⚠️';
        }
        if (code === 'new') {
            const p = lead.pancake_platform;
            if (p === 'facebook') return '📘';   // FB blue
            if (p === 'tiktok')   return '🎵';   // TikTok
            if (p === 'instagram') return '📷';
            return '👤';  // manual
        }
        // Default chip
        return '•';
    }

    get leadGroups() {
        // Trả về [{key, label, icon, color, leads}] để render columns.
        // Stage 'new' → group theo nguồn Pancake.
        // Stage 'won' → group theo urgency.
        // Stage khác → return null (caller dùng flex wrap).
        const code = this.selectedStage?.code;
        const leads = this.state.leads || [];

        if (code === 'new') {
            // Group theo team_label (HCM1/HCM2/HCM3/HN/QN/KHÁC)
            const PRESET_ORDER = ['HCM1', 'HCM2', 'HCM3', 'HCM', 'HN', 'QN', 'ĐN', 'DN'];
            const COLORS = {
                'HCM1': '#228be6', 'HCM2': '#15aabf', 'HCM3': '#0ca678', 'HCM': '#228be6',
                'HN': '#fa5252', 'QN': '#f59f00', 'ĐN': '#e64980', 'DN': '#e64980',
                'KHÁC': '#868e96',
            };
            const groupMap = {};
            for (const ld of leads) {
                const k = ld.team_label || 'KHÁC';
                if (!groupMap[k]) {
                    groupMap[k] = {
                        key: k, label: k, cssColor: COLORS[k] || '#495057', leads: [],
                    };
                }
                groupMap[k].leads.push(ld);
            }
            // Sort: preset order trước, rồi alphabet, KHÁC cuối
            const sorted = Object.values(groupMap).sort((a, b) => {
                if (a.key === 'KHÁC') return 1;
                if (b.key === 'KHÁC') return -1;
                const ai = PRESET_ORDER.indexOf(a.key);
                const bi = PRESET_ORDER.indexOf(b.key);
                if (ai !== -1 && bi !== -1) return ai - bi;
                if (ai !== -1) return -1;
                if (bi !== -1) return 1;
                return a.key.localeCompare(b.key);
            });
            return sorted;
        }

        if (code === 'won') {
            const groups = {
                past:   { key: 'past',   label: '🚨 Quá hạn',  cssColor: '#c92a2a', leads: [] },
                today:  { key: 'today',  label: '🔥 Hôm nay',  cssColor: '#d9480f', leads: [] },
                soon:   { key: 'soon',   label: '⏰ Sắp đến',  cssColor: '#f59f00', leads: [] },
                far:    { key: 'far',    label: '📅 Đã hẹn',   cssColor: '#2b8a3e', leads: [] },
                signed: { key: 'signed', label: '🏆 Đã ký',    cssColor: '#2b8a3e', leads: [] },
                none:   { key: 'none',   label: '⚠️ Chưa hẹn', cssColor: '#868e96', leads: [] },
            };
            for (const ld of leads) {
                if (ld.contract_signed) {
                    groups.signed.leads.push(ld);
                    continue;
                }
                const k = ld.planned_sign_urgency || 'none';
                if (groups[k]) groups[k].leads.push(ld);
                else groups.none.leads.push(ld);
            }
            // Filter empty groups so UI gọn
            return Object.values(groups).filter(g => g.leads.length > 0);
        }

        return null;
    }

    pillTitle(lead) {
        // Pill title (đậm, lớn) — won = ngày ký, khác = tên KH (strip prefix)
        const code = this.selectedStage?.code;
        if (code === 'won') {
            return lead.planned_sign_date ? this.formatSignDate(lead.planned_sign_date) : 'Chưa hẹn';
        }
        // Strip prefix (Fanpage)/(Tiktok)/(Instagram)/(Pancake)/[Pancake]
        let name = lead.name || '';
        name = name.replace(/^\((Fanpage|Tiktok|Instagram|Pancake)\)\s*/i, '');
        name = name.replace(/^\[Pancake\]\s*/i, '');
        return name || 'KH';
    }

    formatSignDate(s) {
        // Format datetime string → "HH:MM dd/mm/yyyy" cho card title
        if (!s) return "Chưa đặt lịch";
        try {
            const dt = new Date(s.replace(' ', 'T') + 'Z');
            // Convert to local tz
            const d = new Date(dt.getTime() - dt.getTimezoneOffset() * 60000);
            const pad = (n) => String(n).padStart(2, '0');
            return `${pad(d.getHours())}:${pad(d.getMinutes())} ${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}`;
        } catch (_e) {
            return s.slice(0, 16).replace('T', ' ');
        }
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

    createNewLead() {
        // Mở wizard popup nhỏ chỉ điền Tên + SĐT.
        // Sau khi tạo, wizard sẽ navigate đến form lead đầy đủ để bổ sung intake.
        this.action.doAction("vd_crm_lead.action_vd_lead_quick_add_wizard");
    }

    async openAlertLeads(kind) {
        // Filter lead table BÊN PHẢI theo loại cảnh báo, KHÔNG navigate trang mới.
        // Clear stage selection để cảnh báo filter thay thế.
        this.state.alertFilter = kind;
        this.state.selectedStageId = null;
        this.state.leadsLoading = true;
        const args = [kind];
        if (this.state.selected_user_id) args.push(this.state.selected_user_id);
        this.state.leads = await this.orm.call("crm.lead", "dashboard_leads_by_alert", args);
        this.state.leadsLoading = false;
    }

    async clearAlertFilter() {
        // Quay lại view stage mặc định
        this.state.alertFilter = null;
        const firstActive = this.state.stages.find((s) => !s.is_lost && s.count > 0)
            || this.state.stages.find((s) => !s.is_lost)
            || this.state.stages[0];
        if (firstActive) {
            await this.selectStage(firstActive.id);
        }
    }

    get alertTitle() {
        const TITLES = {
            overdue_callback: "⚠️ KH quá hạn gọi lại — cần gọi gấp",
            new_not_called: "🆕 KH mới chưa gọi",
            potential_no_quote: "💡 KH tiềm năng chưa báo giá",
            stale: "💤 KH chưa gọi 14+ ngày",
        };
        return TITLES[this.state.alertFilter] || "Danh sách KH";
    }

    async callLead(lead, ev) {
        ev.stopPropagation();
        if (!lead.phone) {
            this.notification.add("KH chưa có SĐT.", { type: "warning" });
            return;
        }
        // Debounce: chặn double-click cùng button trong 2s
        const btn = ev.currentTarget;
        if (btn && btn.dataset.vdCalling === "1") {
            return;
        }
        if (btn) {
            btn.dataset.vdCalling = "1";
            btn.disabled = true;
            setTimeout(() => {
                btn.dataset.vdCalling = "0";
                btn.disabled = false;
            }, 2000);
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

    funnelStepClass(stage) {
        // Màu funnel theo stage code hoặc % probability.
        if (stage.is_won)  return "o_vd_funnel_won";       // xanh lá
        if (stage.is_lost) return "o_vd_funnel_lost_clr";  // xám
        const code = stage.code || "";
        if (code === "new")       return "o_vd_funnel_cold";  // xanh dương nhạt
        if (code === "quote")     return "o_vd_funnel_warm";  // vàng
        if (code === "negotiate") return "o_vd_funnel_hot";   // cam
        if (code === "lead")      return "o_vd_funnel_lead";  // xanh dương
        // Fallback theo probability
        const p = stage.default_probability || 0;
        if (p >= 100) return "o_vd_funnel_won";
        if (p >= 75)  return "o_vd_funnel_hot";
        if (p >= 50)  return "o_vd_funnel_warm";
        if (p >= 25)  return "o_vd_funnel_lead";
        return "o_vd_funnel_cold";
    }

    perfBarClass(pct) {
        // Bar color theo % hoàn thành chỉ tiêu
        if (pct >= 100) return "o_vd_perf_bar_success";  // xanh lá
        if (pct >= 50)  return "o_vd_perf_bar_info";     // xanh dương
        if (pct >= 25)  return "o_vd_perf_bar_warn";     // vàng
        return "o_vd_perf_bar_low";                       // đỏ
    }

    bonusTier(n) {
        // Bậc thang thưởng cho HĐ thứ N theo cơ cấu chỉ tiêu 2026.
        // Phải match Python: ResUsers._vd_calc_nv_bonus tiers.
        const TIERS = {
            1: 3_500_000,
            2: 5_500_000,
            3: 7_500_000,
            4: 8_500_000,
            5: 9_500_000,
        };
        return TIERS[n] || 9_500_000;  // HĐ 6+ giữ mức 9.5M
    }

    formatVnd(n) {
        if (n === null || n === undefined) return "0";
        return new Intl.NumberFormat('vi-VN').format(Math.round(n));
    }

    formatDate(s) {
        if (!s) return "";
        return s.replace("T", " ").slice(0, 16);
    }
}

registry.category("actions").add("vd_crm_lead.dashboard", VdCrmDashboard);
