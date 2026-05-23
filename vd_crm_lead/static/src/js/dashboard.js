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
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

export class VdCrmDashboard extends Component {
    static template = "vd_crm_lead.Dashboard";
    static components = { View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.stringee = useService("stringee");

        // === Default date range: 90 ngày gần nhất → hôm nay ===
        const today = new Date();
        const past = new Date();
        past.setDate(past.getDate() - 90);
        const isoDate = (d) => d.toISOString().slice(0, 10);

        // Focus: 'customers' | 'employees' — chuyển qua nút toggle ở sidebar dọc.
        // Default = 'customers' (workflow KH-care thường mở trước).
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
            // KH có vấn đề mở (mọi stage active) — section "ĐANG XỬ LÝ VẤN ĐỀ"
            leadsWithProblemsAll: [],
            // KH đã hủy (stage_is_lost) — render thùng rác cuối cùng (count only)
            leadsLostAll: [],
            // KH chưa gọi được (call_count=0, active) — render nửa phải bảng KHÁCH MỚI
            leadsNotCalledAll: [],
            // ===== ADMIN MODE (Manager + chọn "Tất cả NV") =====
            // Focus điều khiển section visibility — chuyển bằng nút sidebar.
            focus: "customers",
            dashSubView: "nv",      // 'nv' (bảng NV) | 'kh' (KH có vấn đề) — hover chip để switch
            adminTab: "overview",
            nvDetail: null,
            nvDetailLoading: false,
            // ===== ANALYTICS BI (tab overview) =====
            analytics: null,           // payload từ dashboard_analytics
            analyticsLoading: false,
            analyticsFrom: isoDate(past),
            analyticsTo: isoDate(today),
            // ===== SEARCH KH (live search dropdown) =====
            searchQuery: "",
            searchResults: [],
            searchLoading: false,
            searchOpen: false,
            // ===== PREVIEW LEAD POPUP (fullscreen iframe + prev/next) =====
            previewLead: { open: false, ids: [], index: 0 },
        });
        this._searchDebounce = null;

        // Keyboard handler cho preview popup: ESC đóng, ←/→ chuyển KH
        this._onKeydown = (ev) => {
            if (!this.state.previewLead.open) return;
            // Bỏ qua nếu user đang gõ trong iframe (Odoo SPA chạy bên trong)
            if (ev.key === 'Escape')     { ev.preventDefault(); this.closePreview(); }
            else if (ev.key === 'ArrowLeft')  { ev.preventDefault(); this.prevPreview(); }
            else if (ev.key === 'ArrowRight') { ev.preventDefault(); this.nextPreview(); }
        };
        onMounted(() => window.addEventListener('keydown', this._onKeydown));
        onWillUnmount(() => window.removeEventListener('keydown', this._onKeydown));

        onWillStart(async () => {
            await this.loadDashboard();
            if (this.state.is_manager) {
                this.state.users = await this.orm.call("crm.lead", "dashboard_users", []);
                // Manager + xem "Tất cả NV" → auto load insights cho tab overview
                if (this.isAdminView && this.state.adminTab === 'overview') {
                    await this.loadAnalytics();
                }
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

    // Focus helpers: dùng trong XML để show/hide section theo nút sidebar
    get isCustomerFocus() { return this.state.focus === 'customers'; }
    get isEmployeeFocus() { return this.state.focus === 'employees'; }
    get showKhSection()   { return this.state.focus !== 'employees'; }
    get showNvSection()   { return this.state.focus !== 'customers'; }

    setDashSubView(mode) {
        if (this.state.dashSubView !== mode) this.state.dashSubView = mode;
    }

    setFocus(focus) {
        if (this.state.focus === focus) return;
        this.state.focus = focus;
        // Reset về tab overview khi đổi focus — tránh kẹt ở tab đã ẩn (vd
        // đang ở 'performance' rồi switch sang KH focus mà tab performance bị hide)
        this.state.adminTab = 'overview';
        this.state.nvDetail = null;
    }

    // Click tên NV trong bảng → switch dashboard sang NV cụ thể đó
    async selectNvFromDashboard(userId) {
        if (!userId) return;
        this.state.selected_user_id = userId;
        this.state.nvDetail = null;
        await this.loadDashboard();
    }

    // Map code team → tên đầy đủ để hiện ở thanh dọc bên trái nhóm
    teamFullName(code) {
        const m = {
            'HN': 'Hà Nội',
            'HCM1': 'HCM 1',
            'HCM2': 'HCM 2',
            'HCM3': 'HCM 3',
            'QN': 'QN',
            'KHÁC': 'Khác',
        };
        return m[code] || code;
    }

    async selectAdminTab(tab) {
        this.state.adminTab = tab;
        // Đóng NV detail khi đổi tab
        this.state.nvDetail = null;
        // Tab overview = insights dashboard — load lazily
        if (tab === "overview" && !this.state.analytics) {
            await this.loadAnalytics();
        }
        // Tab "alerts" dùng leads list → load default stage nếu chưa có
        if (tab === "alerts" && !this.state.leads.length && !this.state.selectedStageId) {
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
        // Khi vào stage "Khách mới" → cũng fetch list KH có vấn đề (mọi stage)
        // để render section 2 "ĐANG XỬ LÝ VẤN ĐỀ" bên dưới.
        const stage = this.state.stages.find(s => s.id === stageId);
        if (stage?.code === 'new') {
            const probArgs = this.state.selected_user_id ? [this.state.selected_user_id] : [];
            try {
                this.state.leadsWithProblemsAll = await this.orm.call(
                    "crm.lead", "dashboard_leads_with_problems", probArgs
                );
            } catch (_e) {
                this.state.leadsWithProblemsAll = [];
            }
            // Fetch song song KH đã hủy (cho thùng rác cuối — count only).
            try {
                this.state.leadsLostAll = await this.orm.call(
                    "crm.lead", "dashboard_leads_lost", probArgs
                );
            } catch (_e) {
                this.state.leadsLostAll = [];
            }
            // Fetch KH chưa gọi được → nửa phải bảng KHÁCH MỚI
            try {
                this.state.leadsNotCalledAll = await this.orm.call(
                    "crm.lead", "dashboard_leads_not_called", probArgs
                );
            } catch (_e) {
                this.state.leadsNotCalledAll = [];
            }
        } else {
            this.state.leadsWithProblemsAll = [];
            this.state.leadsLostAll = [];
            this.state.leadsNotCalledAll = [];
        }
    }

    get selectedStage() {
        return this.state.stages.find((s) => s.id === this.state.selectedStageId);
    }

    get isWonStage() {
        const s = this.selectedStage;
        return !!s && s.code === 'won';
    }

    pillSourceClass(lead) {
        // Khách mới — màu hoàn toàn theo call status (white/green/blue/red).
        const code = this.selectedStage?.code;
        if (code === 'won') {
            return 'o_vd_won_urg_' + (lead.planned_sign_urgency || 'none')
                + (lead.contract_signed ? ' o_vd_won_signed' : '');
        }
        if (code === 'new') {
            const callCls = this.pillCallClass(lead);
            if (callCls) return callCls;
            // Chưa gọi → pill trắng neutral (KHÔNG fallback Pancake color)
            return 'o_vd_pill_call_white';
        }
        return 'o_vd_pill_neutral';
    }

    /**
     * Trả CSS class màu cho pill KH MỚI theo trạng thái cuộc gọi:
     *   - ⚪ trắng (no class): chưa gọi cuộc nào (total=0)
     *   - 🟢 xanh lá (o_vd_pill_call_answered): có ≥1 cuộc đã liên lạc được
     *   - 🔵 xanh dương (o_vd_pill_call_blue): chuông không bắt / máy bận
     *   - 🔴 đỏ (o_vd_pill_call_red): thuê bao (state='failed')
     *
     * Ưu tiên: answered > subscriber > no_answer/busy > white.
     */
    pillCallClass(lead) {
        const s = lead.call_stats || {};
        if ((s.total || 0) === 0) return '';   // trắng = chưa gọi
        if ((s.answered || 0) > 0) return 'o_vd_pill_call_answered';
        if ((s.subscriber || 0) > 0) return 'o_vd_pill_call_red';
        if ((s.no_answer || 0) > 0 || (s.busy_like || 0) > 0) {
            return 'o_vd_pill_call_blue';
        }
        return '';
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

    // Split leads cho UI "Khách mới" — top section pills, bottom section rows.
    // Sort priority (ưu tiên KH cần gọi trước):
    //   ⚪ chưa gọi → 🔵 chuông/bận → 🔴 thuê bao → 🟢 đã liên lạc
    get leadsNoProblems() {
        const base = (this.state.leads || []).filter(l => !l.problem_open_count);
        const rank = (l) => {
            const cls = this.pillCallClass(l);
            if (cls === '' || cls === 'o_vd_pill_call_white') return 0;
            if (cls === 'o_vd_pill_call_blue')               return 1;
            if (cls === 'o_vd_pill_call_red')                return 2;
            if (cls === 'o_vd_pill_call_answered')           return 3;
            return 4;
        };
        return [...base].sort((a, b) => rank(a) - rank(b));
    }

    // Trả label trạng thái cuộc gọi cho header tooltip
    pillCallStatusLabel(lead) {
        const cls = this.pillCallClass(lead);
        if (cls === 'o_vd_pill_call_blue')     return { icon: '🔵', text: 'CHUÔNG KHÔNG BẮT / MÁY BẬN' };
        if (cls === 'o_vd_pill_call_red')      return { icon: '🔴', text: 'THUÊ BAO' };
        if (cls === 'o_vd_pill_call_answered') return { icon: '🟢', text: 'ĐÃ LIÊN LẠC ĐƯỢC' };
        return { icon: '⚪', text: 'CHƯA GỌI LẦN NÀO' };
    }
    // Section 2 dùng list riêng (mọi stage, không chỉ stage 'new').
    get leadsWithProblems() {
        return this.state.leadsWithProblemsAll || [];
    }
    // Thùng rác cuối cùng — count KH đã hủy (mọi stage lost). Không hiện chips.
    get leadsLost() {
        return this.state.leadsLostAll || [];
    }
    // Nửa PHẢI bảng KHÁCH MỚI — KH chưa gọi được (call_count=0)
    get leadsNotCalled() {
        return this.state.leadsNotCalledAll || [];
    }
    get isNewStageSplit() {
        // Chỉ split khi đang ở stage "Khách mới" và KHÔNG đang filter alert.
        return this.selectedStage?.code === 'new' && !this.state.alertFilter;
    }

    get leadGroups() {
        // Trả về [{key, label, icon, color, leads}] để render columns.
        // Stage 'new' → group theo nguồn Pancake.
        // Stage 'won' → group theo urgency.
        // Stage khác → return null (caller dùng flex wrap).
        const code = this.selectedStage?.code;
        // Khi stage='new', section top chỉ render KH chưa có vấn đề.
        const leads = this.isNewStageSplit
            ? this.leadsNoProblems
            : (this.state.leads || []);

        if (code === 'new') {
            // Group theo NV (user_name) — mỗi NV 1 column liệt kê toàn bộ KH mới
            // của họ. Header label = "Team | NV name", color theo team.
            const TEAM_COLORS = {
                'HCM1': '#228be6', 'HCM2': '#15aabf', 'HCM3': '#0ca678', 'HCM': '#228be6',
                'HN': '#fa5252', 'QN': '#f59f00', 'ĐN': '#e64980', 'DN': '#e64980',
                'KHÁC': '#868e96',
            };
            const TEAM_ORDER = ['HCM1', 'HCM2', 'HCM3', 'HCM', 'HN', 'QN', 'ĐN', 'DN', 'KHÁC'];
            const groupMap = {};
            for (const ld of leads) {
                const team = ld.team_label || 'KHÁC';
                const nv = ld.user_name || 'Chưa gán';
                const k = `${team}::${nv}`;
                if (!groupMap[k]) {
                    groupMap[k] = {
                        key: k,
                        label: nv,
                        sublabel: team,
                        team: team,
                        cssColor: TEAM_COLORS[team] || '#495057',
                        leads: [],
                    };
                }
                groupMap[k].leads.push(ld);
            }
            // Sort: team theo preset order, trong team sort theo NV name
            return Object.values(groupMap).sort((a, b) => {
                const ai = TEAM_ORDER.indexOf(a.team);
                const bi = TEAM_ORDER.indexOf(b.team);
                if (ai !== bi) {
                    if (ai === -1) return 1;
                    if (bi === -1) return -1;
                    return ai - bi;
                }
                return (a.label || '').localeCompare(b.label || '');
            });
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
        // Pill title (đậm, lớn) — won = ngày ký, khác = tên KH (strip prefix + VINADUY pattern)
        const code = this.selectedStage?.code;
        if (code === 'won') {
            return lead.planned_sign_date ? this.formatSignDate(lead.planned_sign_date) : 'Chưa hẹn';
        }
        // Stage 'new' & KH chưa báo giá → BẮT BUỘC strip pattern VINADUY/team-code
        // và chỉ hiện tên ngắn ('Anh Hải', 'Chị Minh', họ tên đầy đủ).
        // Stage khác hoặc đã có quote → vẫn strip để pill gọn (popup hiện tên đầy đủ).
        return this.shortLeadName(lead);
    }

    /**
     * Chuẩn hoá tên KH cho pill: chỉ giữ "Anh Hải" / "Chị Minh" / tên đầy đủ.
     * Strip:
     *   - Prefix nguồn: (Fanpage), [Pancake], [FB], [TT]...
     *   - Pattern 'VINADUY - <X> - <code>'
     *   - Prefix số-gạch: "21-", "6-", "8-"
     *   - Suffix date pair dính liền: "Phúc12/5" → "Phúc"
     *   - Suffix gạch + code: " - HCM2", " - T5/26"
     *   - Token cuối toàn caps Việt: "HT", "LĐ", "ĐNA", "AG", "HCM", "HCM2", "BN"...
     *   - Token cuối là cặp số: "19/3", "30-12", "1-11", "8/5", "T5/26"
     */
    shortLeadName(lead) {
        let name = (lead.name || '').trim();
        if (!name) return 'KH';
        // 1. Prefix nguồn
        name = name.replace(/^\((Fanpage|Tiktok|Instagram|Pancake)\)\s*/i, '');
        name = name.replace(/^\[(Pancake|FB|TT|IG|Zalo|Hotline|GT)\]\s*/i, '');
        // 2. Pattern VINADUY - <X> - <code> → giữ <X>
        const m = name.match(/^VINADUY\s*[-–—]\s*(.+?)\s*[-–—]\s*[^-–—]+\s*$/i);
        if (m) name = m[1].trim();
        // 3. Prefix số-gạch: "21-Nguyễn..." → "Nguyễn..."
        name = name.replace(/^\d+\s*[-–—]\s*/, '');
        // 4. Date pair dính liền cuối: "Phúc12/5" → "Phúc"
        name = name.replace(/(\D)\d+[-/]\d+\s*$/, '$1');
        // 5. Gạch + code cuối: " - HCM2", " - T5/26"
        name = name.replace(/\s*[-–—]\s*[A-ZĐ][A-ZĐ\d]{0,4}\s*$/, '');
        // 6. Lặp: strip token cuối nếu là caps-code hoặc cặp số
        const UPPER = /^[A-ZĐ][A-ZĐ\d]{1,4}$/;        // 2-5 chars caps Việt (Đ + A-Z + số)
        const NUM_PAIR = /^T?\d{1,2}[-/]\d{1,4}$/;
        let parts = name.split(/\s+/).filter(Boolean);
        while (parts.length > 1) {
            const last = parts[parts.length - 1];
            if (UPPER.test(last) || NUM_PAIR.test(last)) parts.pop();
            else break;
        }
        return parts.join(' ').trim() || 'KH';
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
        // Mở preview INLINE — render từ data đã cache → 0 RPC, mở instantly.
        let ids;
        if (this.isNewStageSplit) {
            if (this.leadsNoProblems.some(l => l.id === leadId)) {
                ids = this.leadsNoProblems.map(l => l.id);
            } else if (this.leadsWithProblems.some(l => l.id === leadId)) {
                ids = this.leadsWithProblems.map(l => l.id);
            } else {
                ids = [leadId];
            }
        } else {
            const list = this.state.leads || [];
            ids = list.length ? list.map(l => l.id) : [leadId];
        }
        const idx = ids.indexOf(leadId);
        this.state.previewLead = {
            open: true,
            ids,
            index: idx >= 0 ? idx : 0,
        };
    }

    closePreview() {
        this.state.previewLead = { ...this.state.previewLead, open: false };
    }

    prevPreview() {
        const p = this.state.previewLead;
        if (!p.open || p.index <= 0) return;
        this.state.previewLead.index = p.index - 1;
    }

    nextPreview() {
        const p = this.state.previewLead;
        if (!p.open || p.index >= p.ids.length - 1) return;
        this.state.previewLead.index = p.index + 1;
    }

    // Props cho component <View/> embedded trong popup — render full form view
    // của crm.lead nhưng KHÔNG kèm Dialog wrapper / breadcrumb / action overhead
    // → load nhanh hơn so với FormViewDialog hoặc navigate trang.
    get previewViewProps() {
        const p = this.state.previewLead;
        if (!p.open || !p.ids.length) return null;
        return {
            type: "form",
            resModel: "crm.lead",
            resId: p.ids[p.index],
            mode: "edit",
            display: { controlPanel: false },
            // Sau khi save → refresh cached leads để pill update màu/data
            onRecordSaved: () => this.refreshAfterPreview(),
        };
    }

    async refreshAfterPreview() {
        if (this.state.selectedStageId) {
            try {
                await this.selectStage(this.state.selectedStageId);
            } catch (_e) {}
        }
    }

    // Lấy lead object hiện đang preview — lookup từ data đã cache (instant, 0 RPC).
    get previewLeadObj() {
        const p = this.state.previewLead;
        if (!p.open || !p.ids.length) return null;
        const id = p.ids[p.index];
        const sources = [
            this.state.leads || [],
            this.state.leadsWithProblemsAll || [],
            this.state.leadsNotCalledAll || [],
            this.state.leadsLostAll || [],
        ];
        for (const list of sources) {
            const found = list.find(l => l.id === id);
            if (found) return found;
        }
        return { id, name: '(KH)', phone: '', user_name: '' };
    }

    // Mở form Odoo đầy đủ (navigate trang) — khi user cần edit nâng cao
    openLeadFullForm() {
        const p = this.state.previewLead;
        const id = p.open ? p.ids[p.index] : null;
        if (!id) return;
        this.closePreview();
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'crm.lead',
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    onPreviewBackdropClick(ev) {
        if (ev.target.classList.contains('o_vd_preview_backdrop')) {
            this.closePreview();
        }
    }

    createNewLead() {
        // Mở wizard popup nhỏ chỉ điền Tên + SĐT.
        // Sau khi tạo, wizard sẽ navigate đến form lead đầy đủ để bổ sung intake.
        this.action.doAction("vd_crm_lead.action_vd_lead_quick_add_wizard");
    }

    // ============ SEARCH KH LIVE (topbar) ============
    onSearchInput(ev) {
        const q = ev.target.value || "";
        this.state.searchQuery = q;
        this.state.searchOpen = true;
        if (this._searchDebounce) clearTimeout(this._searchDebounce);
        if (!q.trim()) {
            this.state.searchResults = [];
            this.state.searchLoading = false;
            return;
        }
        this.state.searchLoading = true;
        this._searchDebounce = setTimeout(() => this._runSearch(q.trim()), 250);
    }

    async _runSearch(q) {
        try {
            const domain = [
                ["active", "=", true],
                "|", "|", "|",
                ["name", "ilike", q],
                ["partner_name", "ilike", q],
                ["phone", "ilike", q],
                ["mobile", "ilike", q],
            ];
            const rows = await this.orm.searchRead(
                "crm.lead",
                domain,
                ["id", "name", "partner_name", "phone", "stage_id", "user_id"],
                { limit: 20, order: "write_date desc" },
            );
            this.state.searchResults = rows.map(r => ({
                id: r.id,
                name: r.partner_name || r.name || "(không tên)",
                phone: r.phone || "",
                stage_name: r.stage_id ? r.stage_id[1] : "",
                user_name: r.user_id ? r.user_id[1] : "",
            }));
        } catch (e) {
            console.error("[VD] search lead failed", e);
            this.state.searchResults = [];
        } finally {
            this.state.searchLoading = false;
        }
    }

    onSearchFocus() {
        if (this.state.searchQuery && this.state.searchResults.length) {
            this.state.searchOpen = true;
        }
    }

    onSearchBlur() {
        // Delay để click mousedown bắt được trước khi dropdown ẩn
        setTimeout(() => { this.state.searchOpen = false; }, 200);
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.searchResults = [];
        this.state.searchOpen = false;
    }

    selectSearchResult(leadId) {
        this.clearSearch();
        this.openLead(leadId);
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

    // ============================================================
    // 📊 ANALYTICS BI — Date filter + 4 Chart.js charts
    // ============================================================
    async loadAnalytics() {
        this.state.analyticsLoading = true;
        try {
            const data = await this.orm.call("crm.lead", "dashboard_analytics", [
                this.state.analyticsFrom, this.state.analyticsTo,
            ]);
            this.state.analytics = data;
        } catch (e) {
            this.notification.add(e.message || "Lỗi tải insights", { type: "danger" });
        }
        this.state.analyticsLoading = false;
    }

    async onApplyAnalyticsFilter() {
        await this.loadAnalytics();
    }

    onAnalyticsDateChange(field, ev) {
        this.state[field] = ev.target.value;
    }

    get analyticsNow() {
        const d = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        return `${pad(d.getHours())}:${pad(d.getMinutes())} ${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}`;
    }

}

registry.category("actions").add("vd_crm_lead.dashboard", VdCrmDashboard);
