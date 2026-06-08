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
import { Component, markup, onMounted, onPatched, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { View } from "@web/views/view";

// User spec 2026-05-31: nhớ NV manager đang xem qua F5 (sessionStorage, theo tab).
const VD_DASH_NV_KEY = "vd_dash_selected_nv";

// Phân biệt "F5 / page reload" vs "click menu Dashboard NV trong SPA".
// Module-scope flag chỉ reset khi bundle JS chạy lại = full page reload (F5).
// Click menu = SPA soft-nav → flag đã false → KHÔNG restore, về danh sách NV.
// (User spec 2026-05-31 round 2: menu Dashboard NV phải ra danh sách NV, không
//  kẹt ở NV cũ; "Quay lại" cũng phải về danh sách NV — xem _vdBackToEmployeeList.)
let VD_DASH_FIRST_MOUNT = true;

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
            // Popover NHẮC NHỞ (hover TỔNG KH) — fixed, ghim sát phải; {nv, top} | null.
            reminderHover: null,
            // Popover GHI ÂM (hover TÊN NV) — fixed, hiện bên trái; {user_id, name,
            // top, left, loading, recordings} | null.
            recHover: null,
            // Bảng CUỘC GỌI HÔM NAY (hover nút "Cuộc gọi") — {user_id, name,
            // cx, cy, loading, summary, customers} | null.
            todayCallsHover: null,
            // Popover KHÁCH MỚI HÔM NAY (hover nút "KH mới") — fixed, hiện tại vị
            // trí chuột; {nv, cx, cy} | null.
            newTodayHover: null,
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
            // KH có thời gian thi công GẤP (≤3 tháng / càng sớm) — section "THI CÔNG GẤP"
            leadsUrgentConstructionAll: [],
            // Filter/sort hover cho 2 bảng TCG + XLVD (null = thứ tự gốc)
            problemSort: null,
            // KH đã hủy (stage_is_lost) — render thùng rác cuối cùng (count only)
            leadsLostAll: [],
            // KH "tham khảo": đã liên lạc được (answered ≥ 1) nhưng chưa báo giá
            leadsReferenceAll: [],
            // KH chưa gọi được (call_count=0, active) — render nửa phải bảng KHÁCH MỚI
            leadsNotCalledAll: [],
            // KH "BÁO GIÁ XONG MẤT TÍCH": đã sang stage Báo giá/Đàm phán nhưng
            // không liên lạc được — box cuối bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ
            leadsQuotedLostAll: [],
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
            // ===== LIVE CALL STATUS — user spec 2026-05-29 =====
            // {user_id: {is_calling, since_min, state}} — poll mỗi 5s
            activeCalls: {},
            // ===== CHỌN NHIỀU KH + CHUYỂN NV (admin/người chia số/giám đốc) =====
            // can_reassign: từ payload dashboard_data — quyết định có hiện nút
            // "Chọn KH" hay không. selectMode: đang bật chế độ tick chọn.
            // selectedLeadIds: {leadId: true}. reassignTargetId: NV nhận.
            can_reassign: false,
            selectMode: false,
            selectedLeadIds: {},
            reassignTargetId: 0,
            reassignBusy: false,
            // ===== HƯỚNG DẪN NÚT SOS (coachmark tự hiện) =====
            // {show, count} — payload dashboard_data; ẩn sau 3 lần "Đã đọc"
            // trên 3 ngày khác nhau.
            sos_guide: { show: false, count: 0 },
            // Thùng rác CÔNG TY — tổng KH ĐÃ DUYỆT hủy (chỉ Admin + Giám đốc).
            company_trash_count: 0,
            can_see_company_trash: false,
            // Popup thùng rác công ty (full màn hình): danh sách KH đã duyệt hủy.
            companyTrash: { open: false, loading: false, leads: [] },
            // ===== KHOÁ "CHỐT BÁO GIÁ" — > 3 KH báo giá chưa chốt =====
            // Coachmark hướng dẫn ẩn trong phiên khi NV bấm "Đã hiểu" (reset
            // mỗi lần loadDashboard → hiện lại nếu vẫn đang khoá).
            quoteGuideDismissed: false,
            // ===== BẢNG KHÁCH MỚI — thu gọn tối đa ~10 dòng + nút mở rộng =====
            // newPillsOverflow: đo bằng JS, chỉ hiện nút khi nội dung thực sự tràn.
            newTableExpanded: false,
            newPillsOverflow: false,
        });
        // Ref vùng pill KHÁCH MỚI để đếm số dòng (quyết định hiện nút mở rộng).
        this.newPillsRef = useRef("newPillsWrap");
        this._searchDebounce = null;

        // User spec 2026-05-31: khôi phục NV đang xem sau khi F5 (trước đây luôn
        // reset về "Tất cả NV" = trang đầu). Lưu trong sessionStorage theo tab.
        // Backend _dashboard_resolve_scope đã ép NV thường về chính họ nếu truyền
        // id NV khác → khôi phục giá trị này an toàn (không lộ dữ liệu).
        // CHỈ restore khi đây là lần mount đầu của bundle (= F5 / page reload).
        // Click menu "Dashboard NV" trong SPA = mount lại nhưng flag đã false →
        // bỏ qua restore + xoá key → manager về thẳng danh sách NV (admin view).
        const isPageReload = VD_DASH_FIRST_MOUNT;
        VD_DASH_FIRST_MOUNT = false;
        try {
            if (isPageReload) {
                const savedNv = parseInt(browser.sessionStorage.getItem(VD_DASH_NV_KEY) || "0", 10);
                if (savedNv) {
                    this.state.selected_user_id = savedNv;
                }
            } else {
                // Vào lại qua menu → reset về danh sách NV cho đồng bộ với F5 sau đó.
                browser.sessionStorage.removeItem(VD_DASH_NV_KEY);
            }
        } catch (_e) { /* sessionStorage bị chặn → bỏ qua, dùng mặc định */ }

        // Keyboard handler cho preview popup: ESC đóng, ←/→ chuyển KH
        this._onKeydown = (ev) => {
            if (!this.state.previewLead.open) return;
            // Bỏ qua nếu user đang gõ trong iframe (Odoo SPA chạy bên trong)
            if (ev.key === 'Escape')     { ev.preventDefault(); this.closePreview(); }
            else if (ev.key === 'ArrowLeft')  { ev.preventDefault(); this.prevPreview(); }
            else if (ev.key === 'ArrowRight') { ev.preventDefault(); this.nextPreview(); }
        };
        onMounted(() => {
            window.addEventListener('keydown', this._onKeydown);
            // User spec 2026-05-29: poll trạng thái cuộc gọi LIVE mỗi 5s
            this._refreshActiveCalls();
            // Tối ưu tải cho nhiều NV (2026-06-03): 5s -> 8s, và bỏ poll khi
            // tab ẩn (_refreshActiveCalls tự skip nếu document.hidden) → 20+ NV
            // mở tab nền không còn spam request.
            this._callPollInterval = setInterval(() => this._refreshActiveCalls(), 8000);
            // Nút "Quay lại" trên navbar (vd_back_button.js) sẽ gọi handler này
            // TRƯỚC khi history.back(). Khi manager đang xem 1 NV cụ thể → pop về
            // danh sách NV thay vì rời khỏi dashboard (user spec 2026-05-31 r2).
            window.__vdDashBackHandler = () => this._vdBackToEmployeeList();
            // Predicate THUẦN (không side-effect) cho syncVisibility navbar:
            // còn back được = manager đang xem 1 NV cụ thể.
            window.__vdDashCanBack = () =>
                !!(this.state.is_manager && this.state.selected_user_id);
            this._measureNewPills();
        });
        // Sau mỗi lần render lại (đổi NV / load data) → đo lại vùng pill KHÁCH MỚI.
        onPatched(() => this._measureNewPills());
        onWillUnmount(() => {
            window.removeEventListener('keydown', this._onKeydown);
            if (window.__vdDashBackHandler) {
                delete window.__vdDashBackHandler;
            }
            if (window.__vdDashCanBack) {
                delete window.__vdDashCanBack;
            }
            if (this._callPollInterval) {
                clearInterval(this._callPollInterval);
                this._callPollInterval = null;
            }
            // Đảm bảo scroll lock + body class được dọn nếu navigate đi
            document.body.classList.remove('o_vd_preview_active');
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
        });

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
        // Mỗi lần tải (đổi NV) → bảng KHÁCH MỚI về dạng thu gọn mặc định.
        this.state.newTableExpanded = false;
        // Reset coachmark CHỐT BÁO GIÁ → hiện lại nếu NV này vẫn đang bị khoá.
        this.state.quoteGuideDismissed = false;
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
        this._persistSelectedNv();
        // Đóng NV detail panel nếu đang mở
        this.state.nvDetail = null;
        await this.loadDashboard();
    }

    // Lưu NV đang xem để giữ nguyên màn hình sau F5 (user spec 2026-05-31).
    _persistSelectedNv() {
        try {
            const id = this.state.selected_user_id || 0;
            if (id) {
                browser.sessionStorage.setItem(VD_DASH_NV_KEY, String(id));
            } else {
                browser.sessionStorage.removeItem(VD_DASH_NV_KEY);
            }
        } catch (_e) { /* sessionStorage bị chặn → bỏ qua */ }
    }

    // ===== ADMIN VIEW HELPERS =====
    // True khi manager đang xem "Tất cả NV" → render layout admin (menu dọc + content).
    get isAdminView() {
        return this.state.is_manager && !this.state.selected_user_id;
    }

    /**
     * Handler cho nút "Quay lại" navbar (vd_back_button.js gọi qua
     * window.__vdDashBackHandler). Khi manager đang drill-in 1 NV cụ thể →
     * trả về danh sách NV (admin view) và báo "đã xử lý" (return true) để
     * navbar KHÔNG history.back() rời khỏi dashboard. Ngược lại trả false →
     * navbar dùng hành vi back mặc định.
     */
    _vdBackToEmployeeList() {
        if (this.state.is_manager && this.state.selected_user_id) {
            this.state.selected_user_id = 0;
            this._persistSelectedNv();
            this.state.nvDetail = null;
            this.loadDashboard();
            return true;
        }
        return false;
    }

    // Focus helpers: dùng trong XML để show/hide section theo nút sidebar
    get isCustomerFocus() { return this.state.focus === 'customers'; }
    get isEmployeeFocus() { return this.state.focus === 'employees'; }
    get showKhSection()   { return this.state.focus !== 'employees'; }
    get showNvSection()   { return this.state.focus !== 'customers'; }

    setDashSubView(mode) {
        if (this.state.dashSubView !== mode) this.state.dashSubView = mode;
    }

    /**
     * User spec 2026-05-29: poll backend mỗi 5s lấy trạng thái call LIVE
     * → update badge "Đang gọi / Không gọi" cuối row NV không cần reload.
     */
    async _refreshActiveCalls() {
        // Bỏ qua khi tab ẩn (NV để dashboard ở tab nền) → giảm tải server.
        if (typeof document !== "undefined" && document.hidden) return;
        try {
            const data = await this.orm.call(
                "crm.lead", "vd_dashboard_active_calls", []
            );
            this.state.activeCalls = data || {};
        } catch (err) {
            // Silent fail — không spam console khi WS đứt / restart server
        }
        // User spec 2026-06-01: SOS phải LIVE — poll trạng thái hỗ trợ mỗi 5s
        // rồi ghi thẳng vào nv trong analytics (không cần F5 mới hiện).
        if (this.state.is_manager) {
            try {
                const help = await this.orm.call(
                    "crm.lead", "vd_dashboard_help_live", []
                );
                this._applyLiveHelp(help || {});
            } catch (err) { /* silent */ }
        }
    }

    /** Ghi đè help_count/help_waiting/help_leads của từng NV bằng dữ liệu LIVE. */
    _applyLiveHelp(help) {
        const ana = this.state.analytics;
        if (!ana || !ana.kh_by_team) return;
        for (const grp of ana.kh_by_team) {
            for (const nv of grp.nvs) {
                const h = help[nv.user_id];
                if (h) {
                    nv.help_count = h.count;
                    nv.help_waiting = h.waiting;
                    nv.help_leads = h.leads;
                } else if (nv.help_count) {
                    nv.help_count = 0;
                    nv.help_waiting = 0;
                    nv.help_leads = [];
                }
            }
        }
    }

    /** Helper cho XML: lấy info call live của 1 NV. */
    callInfo(userId) {
        return this.state.activeCalls[userId] || null;
    }

    /**
     * User spec 2026-05-29: ALL khách hàng = flatten kh_by_team
     * → 1 list duy nhất bao gồm KH mới + chưa có vấn đề + đang xử lý + đang chốt
     * của TOÀN BỘ NV / team trong khoảng lọc. Sort theo team, NV.
     */
    get allLeadsFlat() {
        const ana = this.state.analytics;
        if (!ana || !ana.kh_by_team) return [];
        const out = [];
        const stageLabel = {
            new: '🆕 Khách mới',
            no_problem: '📋 Chưa có vấn đề',
            in_progress: '⏳ Đang xử lý',
            resolved: '🏆 Đang chốt',
        };
        for (const grp of ana.kh_by_team) {
            for (const nv of grp.nvs) {
                const push = (leads, bucket) => {
                    for (const ld of leads || []) {
                        out.push({
                            ...ld,
                            team: grp.team,
                            team_color: grp.color,
                            nv_id: nv.user_id,
                            nv_name: nv.name,
                            bucket,
                            bucket_label: stageLabel[bucket] || bucket,
                        });
                    }
                };
                push(nv.new_leads, 'new');
                push(nv.no_problem_leads, 'no_problem');
                push(nv.in_progress_leads, 'in_progress');
                push(nv.resolved_leads, 'resolved');
            }
        }
        return out;
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
        this._persistSelectedNv();
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
        const stage = this.state.stages.find(s => s.id === stageId);
        const probArgs = this.state.selected_user_id ? [this.state.selected_user_id] : [];

        // User spec 2026-05-31 (tốc độ): TRƯỚC ĐÂY 7 lệnh RPC await TUẦN TỰ
        // (mỗi cái chờ cái trước xong) → vào màn hình NV mất vài giây + xoay tròn.
        // GIỜ bắn SONG SONG bằng Promise.all → chỉ còn ~1 round-trip. Mỗi call có
        // .catch riêng nên 1 cái lỗi không kéo sập các cái khác.
        const call = (method, a) => this.orm.call("crm.lead", method, a).catch(() => []);

        if (stage?.code === 'new') {
            // Khi vào stage "Khách mới" → render thêm các bảng THI CÔNG GẤP /
            // XỬ LÝ VẤN ĐỀ / tham khảo / mất tích... → gộp tất cả query 1 lần.
            const [
                leads, withProblems, urgent, lost, notCalled, reference, quotedLost,
            ] = await Promise.all([
                call("dashboard_leads", args),
                call("dashboard_leads_with_problems", probArgs),
                call("dashboard_leads_urgent_construction", probArgs),
                call("dashboard_leads_lost", probArgs),
                call("dashboard_leads_not_called", probArgs),
                call("dashboard_leads_reference", probArgs),
                call("dashboard_leads_quoted_lost", probArgs),
            ]);
            this.state.leads = leads;
            this.state.leadsWithProblemsAll = this._markupBreakdown(withProblems);
            this.state.leadsUrgentConstructionAll = this._markupBreakdown(urgent);
            this.state.leadsLostAll = lost;
            this.state.leadsNotCalledAll = notCalled;
            this.state.leadsReferenceAll = reference;
            this.state.leadsQuotedLostAll = quotedLost;
        } else {
            this.state.leads = await call("dashboard_leads", args);
            this.state.leadsWithProblemsAll = [];
            this.state.leadsUrgentConstructionAll = [];
            this.state.leadsLostAll = [];
            this.state.leadsNotCalledAll = [];
            this.state.leadsReferenceAll = [];
            this.state.leadsQuotedLostAll = [];
        }
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
     * Trả CSS class màu cho pill KH MỚI — quy định mới theo user 2026-05-27:
     *   1. ⚪ trắng (no class): chưa gọi cuộc nào (total=0)
     *   2. 🔵 xanh dương (o_vd_pill_call_blue): có phát sinh cuộc gọi
     *      (sort theo số cuộc ASC trong cùng tier)
     *   3. 🟢 xanh lá (o_vd_pill_call_answered): có ≥1 cuộc thành công >2 phút
     *   4. 🔴 đỏ xẫm (o_vd_pill_call_darkred): 3 ngày khác nhau gọi không nghe máy
     *      (≥4 ngày sẽ bị auto-archive backend → không hiện ở đây nữa)
     */
    pillCallClass(lead) {
        // User spec 2026-05-27: KH có báo giá (complete=True) nhưng chưa CHỐT
        // → pill xanh lá ĐẬM (o_vd_pill_has_quote), ưu tiên hơn các màu khác.
        // 2026-06-03: KH bấm HUỶ BÁO GIÁ (quote_cancelled) → coi như chưa báo giá.
        if (lead.intake_complete && !lead.intake_locked && !lead.quote_cancelled) {
            return 'o_vd_pill_has_quote';
        }
        const s = lead.call_stats || {};
        const total = s.total || 0;
        if (total === 0) return '';
        if ((s.days_no_answer || 0) >= 3 && (s.answered || 0) === 0) {
            return 'o_vd_pill_call_darkred';
        }
        // ANY answered call → green
        if ((s.answered || 0) > 0) return 'o_vd_pill_call_answered';
        return 'o_vd_pill_call_blue';
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

    // Split leads cho UI "Khách mới" — sort priority (user 2026-05-27):
    //   1. ⚪ Chưa gọi (total=0)                                 — đầu
    //   2. 🔵 Có cuộc gọi — sort theo total ASC (ít → nhiều)
    //   3. 🟢 Có cuộc gọi thành công ≥ 120s                       — kế
    //   4. 🔴 Đỏ xẫm: 3 ngày khác nhau không nghe máy (answered=0) — cuối
    get leadsNoProblems() {
        // User spec 2026-05-28 (round 2 — revert): chỉ loại lead trong
        // "CHƯA GỌI ĐƯỢC" bucket. KH có báo giá (complete=True) chưa CHỐT
        // VẪN ở KH MỚI (pill xanh lá + 💰) — KHÔNG loại trừ.
        const notCalledIds = new Set(
            (this.state.leadsNotCalledAll || []).map(l => l.id)
        );
        // User spec 2026-06-08: GIỮ NGUYÊN thứ tự backend (sắp theo LẦN GỌI gần
        // nhất — chưa gọi / lâu chưa gọi lên ĐẦU, gọi mới nhất xuống CUỐI). KHÔNG
        // re-sort theo tier+số cuộc gọi nữa vì nó làm KH nhảy lung tung sau mỗi
        // cuộc gọi, rất khó tìm.
        return (this.state.leads || []).filter(l => !notCalledIds.has(l.id));
    }

    // KH "có thể tư vấn Zalo" (user spec 2026-06-07): trong KHÁCH MỚI, đã tạo
    // ≥2 ngày, đã có ≥1 cuộc gọi THẬT, và CHƯA kết bạn Zalo → nên kết bạn để
    // gọi + tư vấn qua Zalo.
    _hasRealCall(lead) {
        const s = lead.call_stats || {};
        return ((s.answered || 0) + (s.no_answer || 0)
                + (s.busy_like || 0) + (s.subscriber || 0)) > 0;
    }
    get zaloFriendCandidates() {
        return (this.leadsNoProblems || []).filter(
            l => (l.create_days || 0) >= 2
                && this._hasRealCall(l)
                && !l.zalo_consulted
                && !l.intake_complete
        );
    }

    // Trả label trạng thái cuộc gọi cho header tooltip
    pillCallStatusLabel(lead) {
        const cls = this.pillCallClass(lead);
        if (cls === 'o_vd_pill_call_blue')     return { icon: '🔵', text: 'ĐÃ PHÁT SINH CUỘC GỌI' };
        if (cls === 'o_vd_pill_call_darkred')  return { icon: '🔴', text: '3 NGÀY KHÔNG NGHE MÁY' };
        if (cls === 'o_vd_pill_call_answered') return { icon: '🟢', text: 'GỌI THÀNH CÔNG (CÓ NGHE MÁY)' };
        return { icon: '⚪', text: 'CHƯA GỌI LẦN NÀO' };
    }
    // Section 2 dùng list riêng (mọi stage, không chỉ stage 'new').
    get leadsWithProblems() {
        return this._applyProblemFilter(this.state.leadsWithProblemsAll || []);
    }

    get leadsUrgentConstruction() {
        return this._applyProblemFilter(this.state.leadsUrgentConstructionAll || []);
    }

    // Filter/sort 2 bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ theo chip hover (user spec
    // 2026-05-31). null = giữ thứ tự gốc.
    //  - 'newest'  : KH CHƯA có vấn đề, mới báo giá lên trước (quote_days nhỏ trước)
    //  - 'expiring': KH CHƯA có vấn đề, sắp hết hạn lên trước (quote_days lớn trước)
    //  - 'problem' : KH ĐÃ có vấn đề
    _applyProblemFilter(list) {
        const f = this.state.problemSort;
        if (!f) return list;
        const hasProblem = (l) => !!(l.problems_non_urgent && l.problems_non_urgent.length);
        const qd = (l) => (l.quote_days != null && l.quote_days !== undefined ? l.quote_days : 0);
        if (f === 'problem') return list.filter(hasProblem);
        const noProb = list.filter((l) => !hasProblem(l));
        if (f === 'newest')   return [...noProb].sort((a, b) => qd(a) - qd(b));
        if (f === 'expiring') return [...noProb].sort((a, b) => qd(b) - qd(a));
        return list;
    }
    setProblemSort(f) { this.state.problemSort = f; }
    // Box cuối 2 bảng — KH đã báo giá rồi mất tích (không liên lạc được).
    get leadsQuotedLost() {
        return this.state.leadsQuotedLostAll || [];
    }
    // Thùng rác cuối cùng — count KH đã hủy (mọi stage lost). Không hiện chips.
    get leadsLost() {
        return this.state.leadsLostAll || [];
    }
    // Nửa PHẢI bảng KHÁCH MỚI — KH chưa gọi được (call_count=0)
    get leadsNotCalled() {
        return this.state.leadsNotCalledAll || [];
    }
    // KH tham khảo: đã liên lạc, chưa báo giá
    get leadsReference() {
        return this.state.leadsReferenceAll || [];
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

    // ========================================================================
    // CHỌN NHIỀU KH → CHUYỂN SANG NV KHÁC (admin / người chia số / giám đốc)
    // ========================================================================
    // Quyền hiển thị nút: manager đang xem dashboard + backend cho phép reassign.
    get canBulkReassign() {
        return !!(this.state.is_manager && this.state.can_reassign);
    }
    // Click 1 pill KH: ở chế độ chọn → tick/bỏ tick; bình thường → mở thẻ.
    onPillClick(leadId) {
        if (this.state.selectMode) {
            this.toggleLeadSelect(leadId);
            return;
        }
        this.openLead(leadId);
    }
    toggleSelectMode() {
        this.state.selectMode = !this.state.selectMode;
        if (!this.state.selectMode) {
            // Thoát chế độ chọn → xoá hết lựa chọn cho sạch.
            this.state.selectedLeadIds = {};
        }
    }
    isLeadSelected(leadId) {
        return !!this.state.selectedLeadIds[leadId];
    }
    toggleLeadSelect(leadId) {
        // Gán object mới để OWL reactive bắt được thay đổi.
        const next = Object.assign({}, this.state.selectedLeadIds);
        if (next[leadId]) {
            delete next[leadId];
        } else {
            next[leadId] = true;
        }
        this.state.selectedLeadIds = next;
    }
    // Chọn tất cả KH trong 1 cột/lane (truyền mảng id). Nếu đã chọn hết rồi
    // thì bỏ chọn hết (toggle) → 1 nút làm cả "chọn" lẫn "bỏ" cho gọn.
    toggleSelectAll(leadIds) {
        const ids = (leadIds || []).filter((x) => x != null);
        if (!ids.length) return;
        const next = Object.assign({}, this.state.selectedLeadIds);
        const allSelected = ids.every((id) => next[id]);
        for (const id of ids) {
            if (allSelected) delete next[id];
            else next[id] = true;
        }
        this.state.selectedLeadIds = next;
    }
    clearSelection() {
        this.state.selectedLeadIds = {};
    }
    // ===== BẢNG KHÁCH MỚI — thu gọn ĐÚNG 10 dòng + nút mở rộng =====
    // Đếm SỐ DÒNG pill thực tế qua offsetTop (pill cùng dòng có cùng top).
    // Chỉ hiện nút "Mở rộng" khi > 10 dòng; cắt chính xác sau dòng thứ 10.
    _measureNewPills() {
        const el = this.newPillsRef.el;
        if (!el) {
            if (this.state.newPillsOverflow) this.state.newPillsOverflow = false;
            return;
        }
        const rowTops = [];
        for (const p of el.children) {
            const t = p.offsetTop;
            if (rowTops.every(x => Math.abs(x - t) > 4)) rowTops.push(t);
        }
        rowTops.sort((a, b) => a - b);
        const over = rowTops.length > 10;   // chỉ "tràn" khi QUÁ 10 dòng
        if (over !== this.state.newPillsOverflow) {
            this.state.newPillsOverflow = over;
        }
        // Điều khiển max-height bằng inline (chính xác theo dòng), KHÔNG dựa CSS:
        //  - thu gọn + tràn → cắt tại đầu dòng 11 (hiện đúng 10 dòng)
        //  - còn lại → full chiều cao nội dung.
        if (!this.state.newTableExpanded && over) {
            el.style.maxHeight = rowTops[10] + 'px';
        } else {
            el.style.maxHeight = el.scrollHeight + 'px';
        }
    }
    toggleNewTable() {
        this.state.newTableExpanded = !this.state.newTableExpanded;
    }

    // 🗑️ Thùng rác CÔNG TY — popup FULL màn hình, danh sách KH đã DUYỆT hủy.
    async openCompanyTrash() {
        this.state.companyTrash = { open: true, loading: true, leads: [] };
        this._lockScroll();
        try {
            const leads = await this.orm.call("crm.lead", "dashboard_company_trash", []);
            this.state.companyTrash.leads = leads || [];
            this.state.companyTrash.loading = false;
        } catch (e) {
            this.state.companyTrash.loading = false;
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Thùng rác công ty" });
        }
    }
    closeCompanyTrash() {
        this.state.companyTrash = { open: false, loading: false, leads: [] };
        this._unlockScroll();
    }
    async trashRestore(lead) {
        if (this.state.companyTrash.loading) return;
        this.state.companyTrash.loading = true;
        try {
            const res = await this.orm.call(
                "crm.lead", "dashboard_trash_restore", [[lead.id]]);
            this.notification.add(res.message || "Đã khôi phục",
                { type: res.ok ? "success" : "warning" });
            if (res.ok) {
                this.state.companyTrash.leads =
                    this.state.companyTrash.leads.filter((l) => l.id !== lead.id);
                if (this.state.company_trash_count > 0) this.state.company_trash_count -= 1;
            }
        } finally {
            this.state.companyTrash.loading = false;
        }
    }
    async trashDelete(lead) {
        if (this.state.companyTrash.loading) return;
        const ok = window.confirm(
            `Xoá VĨNH VIỄN khách "${lead.name || ""}"? Không khôi phục được.`);
        if (!ok) return;
        this.state.companyTrash.loading = true;
        try {
            const res = await this.orm.call(
                "crm.lead", "dashboard_trash_delete", [[lead.id]]);
            this.notification.add(res.message || "Đã xoá",
                { type: res.ok ? "success" : "warning" });
            if (res.ok) {
                this.state.companyTrash.leads =
                    this.state.companyTrash.leads.filter((l) => l.id !== lead.id);
                if (this.state.company_trash_count > 0) this.state.company_trash_count -= 1;
            }
        } finally {
            this.state.companyTrash.loading = false;
        }
    }
    get selectedLeadIdList() {
        return Object.keys(this.state.selectedLeadIds)
            .filter((k) => this.state.selectedLeadIds[k])
            .map((k) => parseInt(k, 10));
    }
    get selectedCount() {
        return this.selectedLeadIdList.length;
    }
    onChangeReassignTarget(ev) {
        this.state.reassignTargetId = parseInt(ev.target.value, 10) || 0;
    }
    // Tên NV nhận (để hiện trong câu xác nhận).
    get reassignTargetName() {
        const u = (this.state.users || []).find(
            (x) => x.id === this.state.reassignTargetId);
        return u ? u.name : "";
    }
    async doBulkReassign() {
        const ids = this.selectedLeadIdList;
        const targetId = this.state.reassignTargetId;
        if (!ids.length) {
            this.notification.add("Chưa chọn khách hàng nào.",
                { type: "warning" });
            return;
        }
        if (!targetId) {
            this.notification.add("Chưa chọn nhân viên nhận.",
                { type: "warning" });
            return;
        }
        const ok = window.confirm(
            `Chuyển ${ids.length} khách hàng sang nhân viên "${this.reassignTargetName}"?`
        );
        if (!ok) return;
        this.state.reassignBusy = true;
        try {
            const moved = await this.orm.call(
                "crm.lead", "dashboard_bulk_reassign", [ids, targetId],
            );
            this.notification.add(
                `Đã chuyển ${moved} khách hàng sang "${this.reassignTargetName}".`,
                { type: "success", title: "Chuyển KH thành công" },
            );
            // Reset chọn + tắt chế độ + tải lại dashboard (KH đã chuyển sẽ
            // biến mất khỏi màn NV hiện tại).
            this.state.selectedLeadIds = {};
            this.state.selectMode = false;
            this.state.reassignTargetId = 0;
            await this.loadDashboard();
            // Cập nhật lại số liệu (chưa gọi / tổng mới) trên dropdown NV.
            if (this.state.is_manager) {
                this.state.users = await this.orm.call("crm.lead", "dashboard_users", []);
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg,
                { type: "danger", title: "Không chuyển được KH" });
        } finally {
            this.state.reassignBusy = false;
        }
    }

    // ====================== CHIA SỐ (user spec 2026-06-08) ===================
    // Mở bảng giống "Thêm KH mới", đổ sẵn KH đã chọn, chia mỗi KH cho 1 NV.
    async openDistribute() {
        const ids = this.selectedLeadIdList;
        if (!ids.length) {
            this.notification.add("Chưa chọn khách hàng nào.", { type: "warning" });
            return;
        }
        let recs = [];
        try {
            recs = await this.orm.read("crm.lead", ids, ["name", "phone", "mobile"]);
        } catch (e) {
            recs = ids.map((id) => ({ id, name: "KH #" + id, phone: "" }));
        }
        this.state.distribute = {
            open: true,
            mode: "",
            busy: false,
            lines: recs.map((r) => ({
                lead_id: r.id,
                name: r.name || ("KH #" + r.id),
                phone: r.phone || r.mobile || "",
                user_id: 0,
            })),
        };
        this._lockScroll();
    }
    closeDistribute() {
        this.state.distribute = { open: false, mode: "", busy: false, lines: [] };
        this._unlockScroll();
    }
    setDistributeLineUser(idx, ev) {
        const uid = parseInt(ev.target.value, 10) || 0;
        if (this.state.distribute.lines[idx]) {
            this.state.distribute.lines[idx].user_id = uid;
            this.state.distribute.mode = "";  // NV tự chọn → bỏ chế độ tự động
        }
    }
    distributeUserLoad(userId) {
        const u = (this.state.users || []).find((x) => x.id === userId);
        if (!u) return "";
        return `📋 ${u.new_total || 0} mới · 📵 ${u.new_not_called || 0} chưa gọi`;
    }
    applyDistributeMode(mode) {
        const lines = this.state.distribute.lines || [];
        const users = (this.state.users || []).filter((u) => u.id);
        if (!users.length) {
            this.notification.add("Không có nhân viên để chia.", { type: "warning" });
            return;
        }
        this.state.distribute.mode = mode;
        if (mode === "per_line") return;  // để NV tự chọn từng dòng
        if (mode === "even_all") {
            lines.forEach((ln, i) => { ln.user_id = users[i % users.length].id; });
        } else if (mode === "least") {
            // Dồn cho NV đang ÍT SỐ nhất (cân theo new_total + số vừa gán).
            const load = {};
            users.forEach((u) => { load[u.id] = u.new_total || 0; });
            lines.forEach((ln) => {
                let best = users[0].id, bestv = load[users[0].id];
                for (const u of users) {
                    if (load[u.id] < bestv) { best = u.id; bestv = load[u.id]; }
                }
                ln.user_id = best;
                load[best] += 1;
            });
        }
    }
    get distributeAssignedCount() {
        return (this.state.distribute?.lines || []).filter((l) => l.user_id).length;
    }
    async confirmDistribute() {
        const lines = this.state.distribute.lines || [];
        const assignments = lines
            .filter((l) => l.user_id)
            .map((l) => [l.lead_id, l.user_id]);
        if (!assignments.length) {
            this.notification.add("Chưa chia KH nào cho NV.", { type: "warning" });
            return;
        }
        this.state.distribute.busy = true;
        try {
            const moved = await this.orm.call(
                "crm.lead", "dashboard_bulk_distribute", [assignments],
            );
            this.notification.add(
                `Đã chia ${moved} khách hàng cho các nhân viên (giữ nguyên dữ liệu).`,
                { type: "success", title: "Chia số thành công" },
            );
            this.state.selectedLeadIds = {};
            this.state.selectMode = false;
            this.closeDistribute();
            await this.loadDashboard();
            if (this.state.is_manager) {
                this.state.users = await this.orm.call("crm.lead", "dashboard_users", []);
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Không chia được số" });
            if (this.state.distribute) this.state.distribute.busy = false;
        }
    }

    // ========================================================================
    // HƯỚNG DẪN NÚT SOS — coachmark neo vào 1 nút SOS, NV bấm "Đã đọc"
    // ========================================================================
    // Lead đầu tiên có nút SOS để neo coachmark (ưu tiên bảng THI CÔNG GẤP).
    get firstSosLeadId() {
        const u = this.leadsUrgentConstruction;
        if (u && u.length) return u[0].id;
        const p = this.leadsWithProblems;
        if (p && p.length) return p[0].id;
        return null;
    }
    async ackSosGuide() {
        try {
            const res = await this.orm.call("res.users", "vd_sos_guide_ack", []);
            this.state.sos_guide = res || { show: false, count: 0 };
        } catch (_e) {
            // Lỗi mạng → vẫn ẩn trong phiên này, lần sau payload quyết định lại.
            this.state.sos_guide = { ...this.state.sos_guide, show: false };
        }
    }

    // ========================================================================
    // KHOÁ "CHỐT BÁO GIÁ" — ép NV chốt khi có > 3 KH đã báo giá mà chưa CHỐT
    // ========================================================================
    // KH đã có báo giá chi tiết (intake_complete) nhưng CHƯA CHỐT (intake_locked
    // = false) → pill xanh lá + 💰.
    get quoteUnchotLeads() {
        return (this.leadsNoProblems || []).filter(
            l => l.intake_complete && !l.intake_locked && !l.quote_cancelled);
    }
    // Khoá khi xem 1 NV cụ thể có > 3 KH báo giá chưa chốt (user spec 2026-06-05:
    // ADMIN cũng THẤY ổ khoá + chịu khoá; KHÔNG có nút gỡ — chỉ CHỐT BÁO GIÁ
    // để bớt khách xuống <= 3 mới tự gỡ). Màn "Tất cả NV" (selected=0) không khoá.
    get quoteChotLockActive() {
        return !!(this.state.selected_user_id
            && this.quoteUnchotLeads.length > 3);
    }
    // Chỉ các KH báo giá chưa chốt mới được phép mở khi đang khoá.
    get quoteChotAllowedIds() {
        return new Set(this.quoteUnchotLeads.map(l => l.id));
    }
    // True nếu lead đang bị khoá mở (để làm mờ pill/row + chặn click).
    isLeadLocked(leadId) {
        return this.quoteChotLockActive && !this.quoteChotAllowedIds.has(leadId);
    }
    dismissQuoteGuide() {
        this.state.quoteGuideDismissed = true;
    }

    openLead(leadId) {
        // KHOÁ "CHỐT BÁO GIÁ" (user spec 2026-06-03): > 3 KH báo giá chưa CHỐT
        // → chỉ cho mở các KH báo giá (để vào CHỐT), khoá mở mọi KH khác.
        if (this.isLeadLocked(leadId)) {
            this.notification.add(
                "🔒 Bạn có hơn 3 khách đã BÁO GIÁ nhưng CHƯA CHỐT. Hãy mở từng "
                + "khách MÀU XANH LÁ (💰) → vào THÔNG TIN TƯ VẤN → bấm "
                + "🔒 CHỐT BÁO GIÁ. Khi còn ≤ 3 khách chưa chốt, các khách khác "
                + "sẽ mở lại bình thường.",
                { type: "warning", title: "Khoá — chưa CHỐT báo giá" },
            );
            return;
        }
        // KHOÁ THEO TỪNG BẢNG (user spec 2026-06-05): "bảng nào vi phạm khoá
        // bảng đó". Chặn bấm KH thuộc bảng đang khoá. Chỉ áp khi NV xem dashboard
        // CHÍNH MÌNH (admin xem hộ vẫn mở + có nút gỡ). Chỉ admin gỡ khoá.
        if (this.isTableLockedForSelf('new')
                && (this.leadsNoProblems || []).some(l => l.id === leadId)) {
            this.notification.add(
                "🔒 Bảng KHÁCH MỚI đang bị KHOÁ do chưa gọi đủ. "
                + (this.state.call_watch?.reason || "")
                + " Liên hệ quản lý để được mở khoá.",
                { type: "warning", title: "Khoá bảng Khách mới" },
            );
            return;
        }
        if (this.isTableLockedForSelf('urgent')
                && (this.leadsUrgentConstruction || []).some(l => l.id === leadId)) {
            this.notification.add(
                "🔒 Bảng THI CÔNG GẤP đang bị KHOÁ do quá hạn tìm vấn đề. "
                + "Liên hệ quản lý để được mở khoá.",
                { type: "warning", title: "Khoá bảng Thi công gấp" },
            );
            return;
        }
        if (this.isTableLockedForSelf('xlvd')
                && (this.leadsWithProblems || []).some(l => l.id === leadId)) {
            this.notification.add(
                "🔒 Bảng XỬ LÝ VẤN ĐỀ đang bị KHOÁ do quá hạn tìm vấn đề. "
                + "Liên hệ quản lý để được mở khoá.",
                { type: "warning", title: "Khoá bảng Xử lý vấn đề" },
            );
            return;
        }
        // Mở preview INLINE — render từ data đã cache → 0 RPC, mở instantly.
        let ids;
        if (this.isNewStageSplit) {
            if (this.leadsNoProblems.some(l => l.id === leadId)) {
                ids = this.leadsNoProblems.map(l => l.id);
            } else if (this.leadsUrgentConstruction.some(l => l.id === leadId)) {
                ids = this.leadsUrgentConstruction.map(l => l.id);
            } else if (this.leadsWithProblems.some(l => l.id === leadId)) {
                ids = this.leadsWithProblems.map(l => l.id);
            } else if ((this.state.leadsReferenceAll || []).some(l => l.id === leadId)) {
                ids = this.state.leadsReferenceAll.map(l => l.id);
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
        this._lockScroll();
    }

    /**
     * Mở preview popup với danh sách KH explicit (dùng cho click icon thùng rác /
     * tham khảo / chưa gọi). Cho phép user ← → duyệt qua tất cả KH trong nhóm.
     */
    openCategoryList(leads) {
        if (!leads || !leads.length) return;
        const ids = leads.map(l => l.id);
        this.state.previewLead = { open: true, ids, index: 0 };
        this._lockScroll();
    }

    // ===== KHOÁ THEO BẢNG (user spec 2026-06-05) =====
    // which: 'new' (Khách mới ← chưa gọi) | 'urgent' (Thi công gấp) | 'xlvd'
    // (Xử lý vấn đề ← quá hạn tìm vấn đề). isTableLocked = có khoá (hiện icon ổ
    // khoá + chặn). isTableLockedForSelf = khoá VÀ NV đang xem chính mình (chặn
    // bấm; admin xem hộ vẫn mở + có nút gỡ).
    isTableLocked(which) {
        if (which === 'new') return !!this.state.call_watch?.locked;
        if (which === 'urgent') return !!this.state.problem_find?.urgent?.locked;
        if (which === 'xlvd') return !!this.state.problem_find?.xlvd?.locked;
        return false;
    }
    isTableLockedForSelf(which) {
        return this.isTableLocked(which)
            && !!this.state.selected_user_id
            && this.state.current_user_id === this.state.selected_user_id;
    }
    // Quản lý đang drill-in 1 NV → được phép bấm nút gỡ khoá.
    get canAdminUnlock() {
        return !!(this.state.is_manager && this.state.selected_user_id);
    }

    // ===== CẢNH BÁO CUỘC GỌI HÔM NAY (user spec 2026-06-05) =====
    // Người gọi nhiều nhất hôm nay (toàn bộ NV) — mốc so sánh.
    get maxCallsToday() {
        let mx = 0;
        for (const grp of (this.state.analytics?.kh_by_team || [])) {
            for (const nv of (grp.nvs || [])) {
                mx = Math.max(mx, nv.calls_today_total || 0);
            }
        }
        return mx;
    }
    // Tỷ lệ % cuộc gọi có nghe máy (dùng cho cả thẻ Hôm nay + Tháng này).
    answeredPct(total, success) {
        const t = total || 0, s = success || 0;
        return t > 0 ? Math.round(s / t * 100) : 0;
    }

    // Báo đỏ khi: KHÔNG gọi (0 cuộc) HOẶC < 50% so với người gọi cao nhất.
    isCallTodayWeak(nv) {
        const c = (nv && nv.calls_today_total) || 0;
        if (c === 0) return true;
        const mx = this.maxCallsToday;
        return mx > 0 && c < mx * 0.5;
    }

    // Mô tả NGUYÊN NHÂN khoá (coachmark cạnh ổ khoá). which: new|urgent|xlvd.
    lockReason(which) {
        if (which === 'new') {
            return this.state.call_watch?.reason
                || "Chưa gọi đủ số ngày yêu cầu cho khách mới.";
        }
        const pf = this.state.problem_find?.[which];
        const name = which === 'urgent' ? 'THI CÔNG GẤP' : 'XỬ LÝ VẤN ĐỀ';
        const pct = pf ? pf.pct : 0;
        const np = pf ? pf.no_problem : 0;
        const tot = pf ? pf.total : 0;
        return `Bảng ${name}: ${np}/${tot} khách (${pct}%) CHƯA có vấn đề — `
            + `quá hạn xử lý nên bị khoá.`;
    }

    // ADMIN gỡ khoá bảng cho NV đang xem. which: 'new' | 'urgent' | 'xlvd'.
    // Cập nhật state tại chỗ để icon ổ khoá tắt ngay không cần F5.
    async adminClearTableLock(which) {
        const uid = this.state.selected_user_id;
        if (!uid) return;
        try {
            if (which === 'new') {
                await this.orm.call("crm.lead", "vd_admin_clear_call_lock", [uid]);
                if (this.state.call_watch) {
                    this.state.call_watch.locked = false;
                    this.state.call_watch.reason = "";
                }
            } else {
                await this.orm.call(
                    "crm.lead", "vd_admin_clear_problem_lock", [uid, which],
                );
                if (this.state.problem_find?.[which]) {
                    this.state.problem_find[which].locked = false;
                }
            }
            this.notification.add("✅ Đã mở khoá bảng cho NV.", { type: "success" });
        } catch (err) {
            this.notification.add("Không mở khoá được (cần quyền quản lý).",
                { type: "danger" });
        }
    }

    // ADMIN gỡ khoá thẻ ngay trên BẢNG TỔNG (chỉ rõ NV qua nv.user_id).
    // which: 'new' | 'urgent' | 'xlvd'. Cập nhật nv tại chỗ để thẻ mở ngay.
    async adminClearTableLockFor(nv, which) {
        if (!nv || !nv.user_id) return;
        try {
            if (which === 'new') {
                await this.orm.call("crm.lead", "vd_admin_clear_call_lock", [nv.user_id]);
                nv.lock_new = false;
            } else {
                await this.orm.call(
                    "crm.lead", "vd_admin_clear_problem_lock", [nv.user_id, which],
                );
                if (which === 'urgent') nv.lock_urgent = false;
                else nv.lock_xlvd = false;
            }
            this.notification.add("✅ Đã mở khoá bảng cho NV.", { type: "success" });
        } catch (err) {
            this.notification.add("Không mở khoá được (cần quyền quản lý).",
                { type: "danger" });
        }
    }

    // ===== NHẮC NHỞ NHÂN VIÊN (user spec 2026-06-01) =====
    // Admin tick "Lần N" → lưu mức nhắc vào res.users; hiện ✓ + câu nhắc kèm
    // số liệu tồn đọng để admin chụp gửi NV. "Gỡ" = về 0.
    async setReminderLevel(nv, level) {
        try {
            const newLevel = await this.orm.call(
                "res.users", "vd_set_reminder_level", [nv.user_id, level],
            );
            nv.reminder_level = newLevel;   // mutate reactive analytics → re-render
        } catch (err) {
            this.notification.add("Không lưu được mức nhắc nhở.", { type: "danger" });
        }
    }

    // Chỉ các nhóm VƯỢT NGƯỠNG (backend tính over=True khi pct > ngưỡng, mặc
    // định 20%). Nhóm =0 hoặc dưới ngưỡng bị ẩn → popover chỉ nêu số gấp.
    reminderOverItems(nv) {
        const items = (nv && nv.reminder_items) || [];
        return items.filter((it) => it && it.over);
    }

    // Hover ô tên NV → mở popover NHẮC NHỞ (fixed, thoát khung cắt). Chỉ mở khi
    // có nhóm vượt ngưỡng để khỏi nhắc vô nghĩa.
    onReminderEnter(ev, nv) {
        if (this._remTimer) {
            clearTimeout(this._remTimer);
            this._remTimer = null;
        }
        if (!this.reminderOverItems(nv).length) {
            this.state.reminderHover = null;
            return;
        }
        // Neo theo MÉP THẺ NV — quy đổi sang local theo zoom trong reminderPopStyle.
        this.state.reminderHover = { nv, rect: this._rowRect(ev) };
    }
    // Đóng có TRỄ để chuột kịp di từ tên NV xuống popover (bấm nút Lần/Gỡ).
    onReminderLeave() {
        if (this._remTimer) {
            clearTimeout(this._remTimer);
        }
        this._remTimer = setTimeout(() => {
            this.state.reminderHover = null;
            this._remTimer = null;
        }, 280);
    }
    onReminderPopEnter() {
        if (this._remTimer) {
            clearTimeout(this._remTimer);
            this._remTimer = null;
        }
    }
    // NHẮC NHỞ hiện NGAY VỊ TRÍ CHUỘT (user spec 2026-06-03).
    get reminderPopStyle() {
        const h = this.state.reminderHover;
        if (!h) {
            return "display:none;";
        }
        return this._popAtRect(h.rect, 720);
    }

    // ===== GHI ÂM (hover tên NV) — hiện BÊN TRÁI, nghe + tải ngay =====
    async onRecEnter(ev, nv) {
        if (this._recTimer) {
            clearTimeout(this._recTimer);
            this._recTimer = null;
        }
        this.state.recHover = {
            user_id: nv.user_id,
            name: nv.full_name,
            rect: this._elRect(ev),   // neo theo THẺ "Tháng này" được hover
            loading: true,
            recordings: [],
            stats: {},
        };
        try {
            const data = await this.orm.call("res.users", "vd_recent_recordings", [nv.user_id]);
            if (this.state.recHover && this.state.recHover.user_id === nv.user_id) {
                this.state.recHover.recordings = (data && data.recordings) || [];
                this.state.recHover.stats = (data && data.stats) || {};
                this.state.recHover.loading = false;
            }
        } catch (e) {
            if (this.state.recHover && this.state.recHover.user_id === nv.user_id) {
                this.state.recHover.loading = false;
            }
        }
    }
    onRecLeave() {
        if (this._recTimer) {
            clearTimeout(this._recTimer);
        }
        this._recTimer = setTimeout(() => {
            this.state.recHover = null;
            this._recTimer = null;
        }, 320);
    }

    // Dashboard có zoom:0.7. Popup position:fixed NẰM TRONG vùng zoom nên toạ
    // độ style của nó ở hệ LOCAL (sẽ được nhân zoom khi render), trong khi
    // getBoundingClientRect() trả VISUAL → phải CHIA cho zoom để ra local.
    // Đo trực tiếp tỷ lệ render (rect/offsetWidth) — chắc chắn, không phụ thuộc
    // getComputedStyle (vốn hay trả rỗng cho `zoom`).
    _dashZoom() {
        const host = document.querySelector(".o_vd_crm_dashboard");
        if (host && host.offsetWidth) {
            const ratio = host.getBoundingClientRect().width / host.offsetWidth;
            if (ratio > 0.2 && ratio <= 1.05) return ratio;
        }
        return 0.7;
    }

    // Lấy rect (VISUAL px) của THẺ NV chứa phần tử hover — để popup dính mép thẻ.
    _rowRect(ev) {
        const el = ev.currentTarget;
        const row = (el.closest && el.closest(".o_vd_kh_nv_row")) || el;
        const r = row.getBoundingClientRect();
        return { left: r.left, top: r.top, bottom: r.bottom };
    }

    // Rect của CHÍNH phần tử hover (không phải cả hàng) — để popup neo đúng vị trí
    // thẻ được rê chuột (vd thẻ "Tháng này"), không nhảy về tên NV.
    _elRect(ev) {
        const r = ev.currentTarget.getBoundingClientRect();
        return { left: r.left, top: r.top, bottom: r.bottom };
    }

    // Định vị popup position:fixed DÍNH MÉP thẻ NV (rect = hệ VISUAL).
    // Dashboard có zoom → popup fixed trong vùng zoom bị nhân zoom khi render →
    // style phải tính ở hệ LOCAL (chia zoom).
    // - Còn chỗ bên dưới ≥ bên trên → bung XUỐNG, mép trên dính ĐÁY thẻ.
    // - Ngược lại → neo bằng `bottom` (dính ĐỈNH thẻ) để bung LÊN. Dùng `bottom`
    //   nên KHÔNG phụ thuộc chiều cao popup → không bao giờ che thẻ → hết nhảy/nháy
    //   ở các NV cuối bảng.
    _popAtRect(rect, W) {
        const z = this._dashZoom();
        const vw = (window.innerWidth || 1280) / z;
        const vh = (window.innerHeight || 800) / z;
        const elTop = rect.top / z;
        const elBottom = rect.bottom / z;
        let left = rect.left / z;
        if (left + W > vw - 8) {
            left = Math.max(8, vw - W - 8);
        }
        if (left < 8) {
            left = 8;
        }
        if ((vh - elBottom) >= elTop) {
            return `top:${Math.round(elBottom + 4)}px; left:${Math.round(left)}px; width:${W}px;`;
        }
        return `bottom:${Math.round(vh - elTop + 4)}px; left:${Math.round(left)}px; width:${W}px;`;
    }

    // ===== BẢNG CUỘC GỌI HÔM NAY (hover icon 📞 ô HÔM NAY) =====
    async onTodayCallsEnter(ev, nv) {
        if (this._todayCallsTimer) {
            clearTimeout(this._todayCallsTimer);
            this._todayCallsTimer = null;
        }
        // Đã mở đúng NV này rồi → chỉ giữ, KHÔNG dựng lại + nạp lại (tránh nhảy/nháy).
        if (this.state.todayCallsHover
                && this.state.todayCallsHover.user_id === nv.user_id) {
            return;
        }
        // Neo theo MÉP THẺ NV (visual); quy đổi sang local theo zoom trong popStyle.
        this.state.todayCallsHover = {
            user_id: nv.user_id,
            name: nv.full_name,
            rect: this._rowRect(ev),
            loading: true,
            summary: {},
            customers: [],
        };
        try {
            const data = await this.orm.call(
                "crm.lead", "dashboard_nv_today_calls", [nv.user_id]);
            if (this.state.todayCallsHover
                    && this.state.todayCallsHover.user_id === nv.user_id) {
                this.state.todayCallsHover.summary = (data && data.summary) || {};
                this.state.todayCallsHover.customers = (data && data.customers) || [];
                this.state.todayCallsHover.loading = false;
            }
        } catch (e) {
            if (this.state.todayCallsHover
                    && this.state.todayCallsHover.user_id === nv.user_id) {
                this.state.todayCallsHover.loading = false;
            }
        }
    }
    onTodayCallsLeave() {
        if (this._todayCallsTimer) {
            clearTimeout(this._todayCallsTimer);
        }
        this._todayCallsTimer = setTimeout(() => {
            this.state.todayCallsHover = null;
            this._todayCallsTimer = null;
        }, 320);
    }
    onTodayCallsPopEnter() {
        if (this._todayCallsTimer) {
            clearTimeout(this._todayCallsTimer);
            this._todayCallsTimer = null;
        }
    }
    get todayCallsPopStyle() {
        const h = this.state.todayCallsHover;
        if (!h) return "display:none;";
        return this._popAtRect(h.rect, 760);
    }

    // ===== KHÁCH MỚI HÔM NAY (hover nút "KH mới") — popover fixed dính mép thẻ
    // NV (dữ liệu đã có sẵn trong nv → không cần nạp). =====
    onNewTodayEnter(ev, nv) {
        if (this._newTodayTimer) {
            clearTimeout(this._newTodayTimer);
            this._newTodayTimer = null;
        }
        if (!nv.new_count && !nv.new_today_count) {
            this.state.newTodayHover = null;
            return;
        }
        this.state.newTodayHover = { nv, rect: this._rowRect(ev) };
    }
    onNewTodayLeave() {
        if (this._newTodayTimer) {
            clearTimeout(this._newTodayTimer);
        }
        this._newTodayTimer = setTimeout(() => {
            this.state.newTodayHover = null;
            this._newTodayTimer = null;
        }, 320);
    }
    onNewTodayPopEnter() {
        if (this._newTodayTimer) {
            clearTimeout(this._newTodayTimer);
            this._newTodayTimer = null;
        }
    }
    get newTodayPopStyle() {
        const h = this.state.newTodayHover;
        if (!h) return "display:none;";
        return this._popAtRect(h.rect, 420);
    }
    // mm:ss từ giây
    fmtMmSs(sec) {
        const s = Math.max(0, parseInt(sec || 0, 10));
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}:${r < 10 ? "0" : ""}${r}`;
    }
    onRecPopEnter() {
        if (this._recTimer) {
            clearTimeout(this._recTimer);
            this._recTimer = null;
        }
    }
    get recPopStyle() {
        const h = this.state.recHover;
        if (!h) {
            return "display:none;";
        }
        return this._popAtRect(h.rect, 440);
    }
    fmtDur(sec) {
        const s = Math.max(0, parseInt(sec || 0, 10));
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}:${r < 10 ? "0" : ""}${r}`;
    }

    // Tên gọi NGẮN cho tiêu đề (lấy từ cuối tên, viết HOA). Vd "HN - Lâm Văn Hậu" → "HẬU".
    reminderName(nv) {
        const f = ((nv && nv.full_name) || "").trim();
        const last = f.split(/\s+/).filter(Boolean).pop() || f;
        return last.toUpperCase();
    }

    // Câu nhắc đầy đủ (admin copy gửi NV nếu cần). Khớp nội dung popover.
    reminderSentence(nv) {
        const items = this.reminderOverItems(nv);
        if (!items.length) return "";
        const lines = items.map(
            (it) => `${it.icon} ${it.count}/${it.total} khách (${it.pct}%) ${it.label}`
        );
        const lvl = nv.reminder_level || 0;
        const lvlTxt = lvl ? ` Anh đã nhắc lần ${lvl}.` : "";
        return (
            `ANH YÊU CẦU BẠN "${nv.full_name}" PHẢI XỬ LÝ NGAY CÁC KHÁCH HÀNG SAU:\n` +
            `${lines.join("\n")}\n⏰ Thời hạn: HẾT HÔM NAY.${lvlTxt}`
        );
    }

    /**
     * Duyệt đề xuất hủy KH → archive (active=False). Admin only (server check).
     * User spec round 7 phase 2: NV đề xuất → admin duyệt → KH chính thức hủy.
     */
    async approveCancel(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call("crm.lead", "action_approve_cancel", [[leadId]]);
            this.notification.add("✓ Đã duyệt hủy KH.", { type: "success" });
            // Refresh full dashboard để reload tất cả buckets (bao gồm leadsLost).
            await this.loadDashboard();
        } catch (e) {
            console.error("[dashboard] approveCancel failed:", e);
            this.notification.add("Không duyệt được. " + (e.message || ""), {
                type: "danger",
            });
        }
    }

    /**
     * Gọi lại trực tiếp KH từ popover "CHƯA GỌI ĐƯỢC" — không cần mở form lead.
     * Server action_call returns client action vd_stringee_call để trigger SDK.
     */
    async callLeadDirect(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            const action = await this.orm.call(
                "crm.lead", "action_call", [[leadId]],
            );
            if (action) {
                await this.action.doAction(action);
            }
        } catch (e) {
            console.error("[dashboard] callLeadDirect failed:", e);
            this.notification.add("Không gọi được KH. Kiểm tra cấu hình Stringee.", {
                type: "danger",
            });
        }
    }

    // Xác nhận KẾT BẠN Zalo (Ngày 1) thẳng từ dashboard — giống nút Zalo trong
    // form (user spec 2026-06-07). Sau Ngày 1, KH vào quy trình chăm Zalo (Ngày
    // 2/3 xử lý tiếp trong form KH).
    async confirmZaloFriend(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call(
                "crm.lead", "action_vd_zalo_confirm_day", [[leadId], 1],
            );
            this.notification.add(
                "Đã xác nhận KẾT BẠN Zalo (Ngày 1). Ngày 2 & 3 chăm tiếp trong KH.",
                { type: "success" },
            );
            await this.loadDashboard();
        } catch (e) {
            console.error("[dashboard] confirmZaloFriend failed:", e);
            const msg = (e && e.data && e.data.message) || e.message
                || "Không xác nhận được kết bạn Zalo.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    closePreview() {
        // Ở view KHÁCH MỚI (có pill xanh "đã báo giá"): NV có thể vừa bấm CHỐT /
        // HUỶ BÁO GIÁ trong preview → tải lại để pill cập nhật màu ngay (mất/ra
        // xanh) + gỡ khoá CHỐT nếu còn ≤ 3.
        const needReload = this.quoteChotLockActive || this.isNewStageSplit;
        this.state.previewLead = { ...this.state.previewLead, open: false };
        this._unlockScroll();
        if (needReload) {
            this.loadDashboard();
        }
    }

    /**
     * Lock document scroll khi popup mở.
     * QUAN TRỌNG cho Popper: Odoo's usePosition tính boundary dựa trên
     * documentElement.scrollTop. Nếu document scroll != 0, math sẽ shift menu
     * sai vị trí khi placement near edge. Lock scroll → scrollTop = 0 stable.
     */
    _lockScroll() {
        document.body.classList.add('o_vd_preview_active');
        document.documentElement.style.overflow = 'hidden';
        document.body.style.overflow = 'hidden';
    }
    _unlockScroll() {
        document.body.classList.remove('o_vd_preview_active');
        document.documentElement.style.overflow = '';
        document.body.style.overflow = '';
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
            // BẬT control panel để có nút Lưu/Huỷ — TRƯỚC đây controlPanel:false
            // khiến form KHÔNG có nút Save => intake (Tỉnh/Huyện...) KHÔNG bao giờ
            // lưu xuống DB (log: 0 web_save cả ngày). Đó là gốc của "nó không lưu".
            // CSS .o_vd_preview_modal sẽ thu gọn breadcrumb, chỉ giữ nút Lưu cho gọn.
            display: { controlPanel: true },
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
            this.state.leadsUrgentConstructionAll || [],
            this.state.leadsNotCalledAll || [],
            this.state.leadsLostAll || [],
            this.state.leadsQuotedLostAll || [],
            // Fix 2026-05-30: thiếu list THAM KHẢO → bấm KH tham khảo topbar hiện
            // "(KH)" trống vì không resolve được data cached.
            this.state.leadsReferenceAll || [],
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

    // ============ COPY tên / SĐT từ topbar preview (click chip → clipboard) ============
    async _copyToClipboard(text, okMsg, emptyMsg) {
        if (!text) {
            this.notification.add(emptyMsg, { type: "warning" });
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            this.notification.add(okMsg, { type: "success" });
        } catch (_e) {
            // Fallback: dùng textarea ẩn (cho browser cũ / không có permission clipboard API)
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand("copy"); this.notification.add(okMsg, { type: "success" }); }
            catch (_e2) { this.notification.add("Không thể copy — trình duyệt chặn clipboard.", { type: "danger" }); }
            document.body.removeChild(ta);
        }
    }
    copyPreviewName() {
        const L = this.previewLeadObj;
        if (!L) return;
        this._copyToClipboard(L.name, `Đã copy tên: ${L.name}`, "Chưa có tên KH.");
    }

    // Lưu tên KH sửa trực tiếp ở topbar preview → ghi xuống crm.lead qua ORM.
    // Sửa được ở MỌI trạng thái (name không nằm trong intake locked fields).
    async savePreviewName(ev) {
        const p = this.state.previewLead;
        if (!p.open || !p.ids.length) return;
        const id = p.ids[p.index];
        const newName = (ev.target.value || "").trim();
        const L = this.previewLeadObj;
        if (!newName) {
            this.notification.add("Tên KH không được để trống.", { type: "warning" });
            if (L) ev.target.value = L.name || "";
            return;
        }
        if (L && newName === L.name) return;
        // Thử tối đa 2 lần — phòng lỗi DB "could not serialize" tạm thời.
        let lastErr = null;
        for (let attempt = 0; attempt < 2; attempt++) {
            try {
                await this.orm.call("crm.lead", "write", [[id], { name: newName }]);
                if (L) L.name = newName;     // cập nhật cache → topbar + pill re-render
                this.notification.add(`Đã đổi tên KH → ${newName}`, { type: "success" });
                this.refreshAfterPreview();
                return;
            } catch (e) {
                lastErr = e;
            }
        }
        console.error("[dashboard] savePreviewName failed:", lastErr);
        this.notification.add("Không lưu được tên KH — thử lại sau.", { type: "danger" });
        if (L) ev.target.value = L.name || "";
    }

    onPreviewNameKeydown(ev) {
        if (ev.key === "Enter") { ev.preventDefault(); ev.target.blur(); }
        else if (ev.key === "Escape") {
            const L = this.previewLeadObj;
            if (L) ev.target.value = L.name || "";
            ev.target.blur();
        }
    }
    copyPreviewPhone() {
        const L = this.previewLeadObj;
        if (!L) return;
        this._copyToClipboard(L.phone, `Đã copy SĐT: ${L.phone}`, "Chưa có số điện thoại.");
    }

    // Click tên KH (pill ở bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ) → copy tên,
    // KHÔNG mở lead (stopPropagation để không trigger row openLead).
    copyLeadName(ev, name, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        // Ở chế độ CHỌN KH: click tên = tick chọn (không copy) để chọn được
        // KH ngay trên 2 bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ.
        if (this.state.selectMode && leadId != null) {
            this.toggleLeadSelect(leadId);
            return;
        }
        this._copyToClipboard(name, `Đã copy tên: ${name}`, "Chưa có tên KH.");
    }
    // 🆘 NV gửi yêu cầu hỗ trợ. scope: 'today' (trong ngày) | 'multi' (đến khi chốt).
    // Đã gửi KHÔNG huỷ được; tối đa 3 KH/NV. Cấp trên thấy ngay (hàng highlight đỏ).
    async requestHelp(ev, leadId, scope) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call(
                "crm.lead", "vd_request_help", [[leadId]],
                { context: { help_scope: scope } },
            );
            if (this.state.selectedStageId) await this.selectStage(this.state.selectedStageId);
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Không thực hiện được.";
            this.notification.add(msg, { type: "warning" });
        }
    }
    // Refresh sau khi thao tác cờ hỗ trợ: cập nhật cả bảng NV (admin analytics)
    // lẫn list theo stage (NV view) tuỳ màn hình đang mở.
    async _refreshAfterHelp() {
        if (this.state.analytics) await this.loadAnalytics();
        if (this.state.selectedStageId) await this.selectStage(this.state.selectedStageId);
    }
    // Cấp trên: 🔴 chờ → 🟢 đang hỗ trợ
    async ackHelp(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call("crm.lead", "vd_ack_help", [[leadId]]);
            await this._refreshAfterHelp();
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || "Lỗi", { type: "warning" });
        }
    }
    // Cấp trên: hoàn tất hỗ trợ → xoá cờ
    async doneHelp(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call("crm.lead", "vd_done_help", [[leadId]]);
            await this._refreshAfterHelp();
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || "Lỗi", { type: "warning" });
        }
    }
    // Bọc HTML bảng báo giá chi tiết bằng markup() → t-out render raw (không escape).
    // Panel THÔNG TIN KHÁCH HÀNG (hover tên KH ở THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ).
    _markupBreakdown(rows) {
        for (const r of (rows || [])) {
            if (typeof r.quote_breakdown_html === "string") {
                r.quote_breakdown_html = markup(r.quote_breakdown_html);
            }
            // Ghi âm: chỉ giữ cuộc kết nối > 1 phút (duration > 60s) + có file.
            const cs = r.call_stats;
            if (cs && Array.isArray(cs.recent_calls)) {
                cs.recent_calls_long = cs.recent_calls.filter(
                    (c) => (c.duration || 0) > 60 && c.recording_url
                );
            }
        }
        return rows || [];
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
            // User spec 2026-05-29: search KHÔNG DẤU theo tên + SĐT.
            // Backend Python normalize NFD strip diacritics + match substring.
            const uid = this.state.selected_user_id || null;
            const rows = await this.orm.call(
                "crm.lead", "vd_dashboard_search_leads",
                [q, uid, 30],
            );
            this.state.searchResults = rows || [];
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
        // ÉP ZALO (user spec 2026-06-09): KH đã ≥2 lần đổ chuông không nghe →
        // cảnh báo MẠNH nên gửi kết bạn Zalo, nhưng KHÔNG chặn (vẫn cho gọi nếu
        // NV xác nhận muốn gọi tiếp).
        if (lead.must_zalo) {
            const ok = window.confirm(
                "⚠️ Khách này đã GỌI 2+ LẦN ĐỔ CHUÔNG NHƯNG KHÔNG NGHE MÁY.\n\n"
                + "Khách kiểu này thường KHÔNG bắt máy số lạ. NÊN bấm "
                + "\"💬 KẾT BẠN ZALO\" để tư vấn qua Zalo thay vì gọi tiếp.\n\n"
                + "Bạn VẪN muốn gọi điện?"
            );
            if (!ok) return;
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
            await this.stringee.call(lead.phone, lead.name || "");
            // KHÔNG toast "Đang gọi" — popup cuộc gọi đã hiện đầy đủ trạng thái.
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
