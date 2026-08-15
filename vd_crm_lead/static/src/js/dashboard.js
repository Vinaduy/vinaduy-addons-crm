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
import { Component, markup, onMounted, onPatched, onWillPatch, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { View } from "@web/views/view";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { VdHouseLibDialog } from "./vd_house_lib";
import { VdDriveLibDialog } from "./vd_nghiem_thu_lib";
import { Dialog } from "@web/core/dialog/dialog";

// ============ SỐ OMI — popup thẻ khách OMI + nút gọi (user 2026-07-21) ============
// Khách OMI KHÔNG tính vào số KH quản lý; gọi kết nối thành công thì server tự
// chuyển số về NV gọi (stringee_call._vd_omi_convert_on_answer). Thẻ (không cột),
// ưu tiên khách nhiều thông tin lên đầu (backend vd_omi_list order info_score).
// Popup CHỌN LÝ DO HỦY (bảng lựa chọn khi hủy — như hủy KH ở lead).
export class VdOmiCancelDialog extends Component {
    static template = "vd_crm_lead.OmiCancelDialog";
    static components = { Dialog };
    static props = {
        customer: Object, cats: Array, onConfirm: Function,
        close: { type: Function, optional: true },
    };
    setup() {
        this.state = useState({
            category: (this.props.cats[0] || {}).key || "", note: "",
        });
    }
    confirm() {
        this.props.onConfirm(this.state.category, this.state.note);
        this.props.close();
    }
}

export class VdOmiDialog extends Component {
    static template = "vd_crm_lead.OmiDialog";
    static components = { Dialog };
    static props = { onCall: Function, close: { type: Function, optional: true } };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({ loading: true, items: [], q: "", cats: [] });
        onWillStart(async () => {
            try {
                this.state.items = await this.orm.call(
                    "vd.imported.customer", "vd_omi_list", []);
                this.state.cats = await this.orm.call(
                    "vd.imported.customer", "vd_omi_cancel_categories", []);
            } catch (e) {
                this.state.items = [];
            }
            this.state.loading = false;
        });
    }
    get filtered() {
        let items = this.state.items;
        const q = (this.state.q || "").toLowerCase().trim();
        if (q) {
            items = items.filter(
                (i) => ((i.name || "") + " " + (i.phone || "")).toLowerCase().includes(q));
        }
        // Khách HỦY xuống CUỐI (giữ thứ tự còn lại).
        return [...items].sort((a, b) => (a.cancelled ? 1 : 0) - (b.cancelled ? 1 : 0));
    }
    call(item) {
        this.props.onCall(item.phone, item.name);
    }
    // HỦY khách OMI → mở bảng chọn lý do → đánh dấu hủy + xuống CUỐI (không xoá).
    cancelCustomer(c) {
        this.dialog.add(VdOmiCancelDialog, {
            customer: c,
            cats: this.state.cats,
            onConfirm: async (category, note) => {
                try {
                    await this.orm.call("vd.imported.customer", "vd_omi_cancel",
                        [c.id, category, note]);
                    const it = this.state.items.find((i) => i.id === c.id);
                    if (it) { it.cancelled = true; it.cancel_category = category; }
                    this.notification.add("Đã hủy khách — chuyển xuống cuối danh sách.",
                        { type: "success" });
                } catch (e) {
                    this.notification.add("Hủy khách lỗi.", { type: "danger" });
                }
            },
        });
    }
    // LẤY KHÁCH VỀ → tạo lead của NV (hiện ở bảng Khách mới) + bỏ khỏi SỐ OMI.
    async takeCustomer(c) {
        try {
            const r = await this.orm.call("vd.imported.customer", "vd_omi_take", [c.id]);
            if (r && r.ok) {
                this.state.items = this.state.items.filter((i) => i.id !== c.id);
                this.notification.add(
                    "Đã lấy khách về — xem ở bảng KHÁCH MỚI (tải lại trang nếu chưa thấy).",
                    { type: "success" });
            } else {
                this.notification.add("Không lấy được khách này.", { type: "warning" });
            }
        } catch (e) {
            this.notification.add("Lấy khách về lỗi.", { type: "danger" });
        }
    }
    // Gộp thông tin phụ thành 1 dòng gọn (khách = 1 dòng, sát nhau).
    infoLine(c) {
        // Bỏ "Thời gian" (trên 5 tháng...) và "Công năng" theo yêu cầu.
        const p = [];
        if (c.address) p.push(c.address);
        if (c.area) p.push("📐 " + c.area);
        if (c.house_type) p.push(c.house_type);
        if (c.floors) p.push(c.floors);
        if (c.budget) p.push("💰 " + c.budget);
        if (c.land_type) p.push(c.land_type);
        if (c.tags) p.push("🏷 " + c.tags);
        return p.join("  ·  ");
    }
}

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
        this.dialog = useService("dialog");
        // 🔔 Bus: nhận thông báo "có số đẩy lên" → kêu chuông to + thông báo.
        this.bus = useService("bus_service");

        // === Default date range: 90 ngày gần nhất → hôm nay ===
        const today = new Date();
        const past = new Date();
        past.setDate(past.getDate() - 90);
        const isoDate = (d) => d.toISOString().slice(0, 10);

        // Focus: 'customers' | 'employees' — chuyển qua nút toggle ở sidebar dọc.
        // Default = 'customers' (workflow KH-care thường mở trước).
        this.state = useState({
            loading: true,
            // 📢 Banner đỏ THÔNG BÁO ĐIỀU CHỈNH ĐƠN GIÁ (tự hiện 24h khi admin sửa giá).
            pricingNotice: { active: false },
            // Panel DANH SÁCH SĐT BỊ LOẠI khỏi chia số (mở từ dòng "đã gộp/loại").
            // {open, scope, loading, items, summary} | null.
            pkExcluded: null,
            // Tab CHIA SỐ: mở dropdown "➕ Thêm NV nhận số" (bật lại NV đang tắt).
            distAddOpen: false,
            // SỬA TAY số liệu 1 cột biểu đồ tỷ lệ — {iso,label,khach,xin} | null.
            rateEdit: null,
            // Bảng THƯỞNG treo (admin cấu hình) hiện trên trang cá nhân.
            bonusBoard: { personal: [], team: [], team_label: "" },
            // BẢO MẬT: buộc đổi mật khẩu (hết chu kỳ) — chặn dashboard tới khi đổi.
            must_change_password: false,
            pwForm: { old: "", new1: "", new2: "" },
            pwSaving: false,
            // 📢 CHIẾN DỊCH SPAM ZALO: chiến dịch đang khoá NV (chưa báo cáo) | null.
            // Khoá toàn bộ dashboard, hiện popup 3 bước tới khi NV nộp báo cáo.
            broadcast: null,
            broadcastStep: 1,
            broadcastShownAt: 0,
            broadcastDownloaded: false,
            broadcastForm: { sent: "", committed: false, note: "" },
            broadcastSubmitting: false,
            // Popover NHẮC NHỞ (hover TỔNG KH) — fixed, ghim sát phải; {nv, top} | null.
            reminderHover: null,
            // Popover GHI ÂM (hover TÊN NV) — fixed, hiện bên trái; {user_id, name,
            // top, left, loading, recordings} | null.
            recHover: null,
            // Popover GHI ÂM THAM KHẢO (hover filter to nhấp nháy dưới Báo cáo
            // cuộc gọi) — bảng ghi âm >5' của 3 NV mẫu; {rect, loading, people,
            // min_minutes} | null. Toàn công ty đều xem được.
            refRecHover: null,
            // Cache dữ liệu GHI ÂM THAM KHẢO — nạp SẴN lúc mở dashboard để hover
            // hiện NGAY, không trễ 1-2s. {people, min_minutes} | null.
            refRecData: null,
            // Bảng CUỘC GỌI HÔM NAY (hover nút "Cuộc gọi") — {user_id, name,
            // cx, cy, loading, summary, customers} | null.
            todayCallsHover: null,
            // Popover KHÁCH MỚI HÔM NAY (hover nút "KH mới") — fixed, hiện tại vị
            // trí chuột; {nv, cx, cy} | null.
            newTodayHover: null,
            // Popover 🗑️ KH HỦY CHỜ DUYỆT (hover thùng rác dòng NV) — render ở gốc
            // (fixed) để không bị che ở cuối bảng; {user_id, name, leads, rect} | null.
            cancelHover: null,
            cancelSel: {},   // id KH hủy được tick chọn (duyệt hàng loạt)
            user: { id: 0, name: "", is_all: false },
            is_manager: false,
            // Giám đốc (không phải admin) → mặc định mở chế độ CÁ NHÂN.
            is_director: false,
            // Trưởng nhóm (không phải manager): xem dashboard của CHÍNH MÌNH +
            // bảng NV dưới quyền (cùng phòng ban) để bấm xem từng người.
            is_team_leader: false,
            team_label: "",
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
            // LỌC NHANH theo SỐ NGÀY CHƯA GỌI (0 = tất cả; 3/5/8/15/25/40 = khoảng
            // riêng). dayFilter = cho 2 bảng TCG+XLVĐ; newDayFilter = cho bảng KHÁCH
            // MỚI (độc lập). (user 2026-08-06)
            dayFilter: 0,
            newDayFilter: 0,
            // KH đã hủy (stage_is_lost) — render thùng rác cuối cùng (count only)
            leadsLostAll: [],
            // Báo cáo KH mới vs Hủy (6 kỳ) cho popover thùng rác màn NV — đồng bộ
            // với bảng thống kê ở popover trưởng phòng.
            cancelReport: [],
            // KH "tham khảo": đã liên lạc được (answered ≥ 1) nhưng chưa báo giá
            leadsReferenceAll: [],
            // KH chưa gọi được (call_count=0, active) — render nửa phải bảng KHÁCH MỚI
            leadsNotCalledAll: [],
            // KH "BÁO GIÁ XONG MẤT TÍCH": đã sang stage Báo giá/Đàm phán nhưng
            // không liên lạc được — box cuối bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ
            leadsQuotedLostAll: [],
            // KH "GỬI HỢP ĐỒNG": đã đặt lịch ký HĐ (Làm hợp đồng - Hẹn gặp) chưa
            // ký xong — box cuối bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ (2026-06-12)
            leadsPlannedSignAll: [],
            // ===== ADMIN MODE (Manager + chọn "Tất cả NV") =====
            // Focus điều khiển section visibility — chuyển bằng nút sidebar.
            focus: "customers",
            // GIÁM ĐỐC: 2 filter to "CÁ NHÂN" / "NHÂN VIÊN" (user spec 2026-06-20).
            // dirTeamMode=true → GĐ xem dashboard CỦA MÌNH + bảng NV phòng mình.
            dirTeamMode: false,
            // empExpanded=true → bảng NV đang GIÃN hiện TOÀN BỘ NV (hover nút NHÂN
            // VIÊN); false → thu về NV phòng GĐ quản lý (user spec 2026-06-20 r2).
            empExpanded: false,
            // GĐ: NV TOÀN CÔNG TY (mọi phòng) cho lúc GIÃN — prefetch nền. Lúc THU
            // bảng vẫn chỉ hiện NV phòng GĐ (analytics.kh_by_team). Tách 2 nguồn để
            // KHÔNG nháy khi tải trang (user spec 2026-06-20 r11).
            allTeamGroups: [],
            allTeamLoading: false,
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
            // Chỉ DỰNG tooltip của pill đang hover (lazy) — trước đây MỖI pill (có
            // thể ~200) dựng sẵn 1 tooltip nặng trong DOM → ~5000 node vô hình +
            // hàng nghìn lời gọi getter mỗi lần render = "đơ". Giờ chỉ 1 tooltip.
            hoverPillId: 0,
            // Chỉ DỰNG bảng trong ô icon phải khi hover đúng ô đó (lazy). Trước đây
            // 5 ô dựng sẵn cả bảng (CHƯA GỌI 200 dòng, THAM KHẢO 85...) trong DOM →
            // mỗi lần render đều phải dựng lại hết. '' | 'reference' | 'notcalled' |
            // 'lost' | 'quoted_lost' | 'planned_sign'.
            hoverTile: "",
            // Ô mở bằng CLICK-ghim (KH HỦY): bấm mở, bấm lại / bấm ra ngoài đóng.
            pinnedTile: "",
            cbMoreOpen: "",
            rowGearOpen: 0,
            // ===== MENU 3 CHẤM (kebab) trên thanh chọn KH =====
            // open: mở dropdown; sub: '' | 'selectUser' | 'transferUser' | 'teamPick'
            // | 'teamRoster'; busy: đang chạy. team: phòng đang chọn; teamChecked:
            // {uid:true} người nhận đã tích trong phòng (chia đều).
            bulkMenu: { open: false, sub: "", busy: false, team: "", teamChecked: {} },
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
            // Bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ: thu gọn 15 dòng, nút mở rộng
            // (giống bảng Khách mới) — user spec 2026-07-07.
            urgentExpanded: false,
            xlvdExpanded: false,
            // Báo cáo tỷ lệ xin số: xem theo Ngày / Tuần / Tháng (user 2026-06-26).
            pancakeTrendPeriod: "day",
            // ===== LỊCH HỌC BẮT BUỘC (banner + đếm ngược trên đầu danh sách KH) =====
            // Mảng session áp dụng cho NV đang nhập (vd.training.session.vd_my_banner).
            // trainingNow = mốc thời gian hiện tại (ms) cập nhật mỗi giây để đếm ngược.
            trainingBanner: [],
            trainingNow: 0,
        });
        // Ref vùng pill KHÁCH MỚI để đếm số dòng (quyết định hiện nút mở rộng).
        this.newPillsRef = useRef("newPillsWrap");
        // Ref panel bảng NV (GĐ) — để timer thu RE-VERIFY :hover thật, miễn nhiễm
        // mouseleave nhiễu lúc bảng giãn (user spec r6).
        this.tlPanelRef = useRef("tlPanel");
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

        // GĐ vào dashboard lần đầu mà CHƯA chọn NV nào (selected_user_id=0) →
        // mặc định mở chế độ "CÁ NHÂN" (dashboard của GĐ + bảng NV phòng mình)
        // thay vì "Tất cả NV". Quyết định sau loadDashboard (mới biết role).
        this._dirDefaultPersonal = !this.state.selected_user_id;

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
            this._callPollEvery = 8000;
            this._callPollInterval = setInterval(() => this._refreshActiveCalls(), 8000);
            // LỊCH HỌC BẮT BUỘC: nạp banner + ticker đếm ngược 1s. Cứ 60s nạp lại
            // danh sách (lịch mới / đã hoàn thành rớt ra). Bỏ qua khi tab ẩn.
            this.state.trainingNow = Date.now();
            this._loadTrainingBanner();
            this._loadBroadcast();
            this._loadCourseStats();
            this._loadPricingNotice();
            // 🔔 CHUÔNG "CÓ SỐ ĐẨY LÊN": mở khoá âm thanh + lắng nghe bus.
            this._initPushAudio();
            this._onLeadsPushed = (payload) => this._handleLeadsPushed(payload);
            if (this.bus && this.bus.subscribe) {
                this.bus.subscribe("vd.leads.pushed", this._onLeadsPushed);
            }
            this._trainingTick = setInterval(() => {
                // 2026-08-05: Mỗi lần ghi trainingNow là 1 lần re-render TOÀN dashboard
                // (template RẤT lớn) + kích MutationObserver intake_select_fix →
                // main-thread giật. TRƯỚC ĐÂY tick 1s LIÊN TỤC kể cả khi KHÔNG có gì
                // đếm ngược → cả trang "đơ" cả ngày. Nay CHỈ bump trainingNow khi thật
                // sự cần đồng hồ chạy: (a) popup KH đóng, (b) tab đang xem, (c) có
                // buổi học đang trong cửa sổ đếm ngược HOẶC popup broadcast đang chờ
                // giờ. Ngoài ra để yên → 0 re-render → hết đơ.
                const previewOpen = !!(this.state.previewLead && this.state.previewLead.open);
                if (!previewOpen && !document.hidden && this._needsLiveTick()) {
                    this.state.trainingNow = Date.now();
                }
                this._trainingRefreshN = (this._trainingRefreshN || 0) + 1;
                if (this._trainingRefreshN % 60 === 0 && !document.hidden && !previewOpen) {
                    this._loadTrainingBanner();
                    this._loadBroadcast();
                }
            }, 1000);
            // Nút "Quay lại" trên navbar (vd_back_button.js) sẽ gọi handler này
            // TRƯỚC khi history.back(). Khi manager đang xem 1 NV cụ thể → pop về
            // danh sách NV thay vì rời khỏi dashboard (user spec 2026-05-31 r2).
            window.__vdDashBackHandler = () => this._vdBackToEmployeeList();
            // Predicate THUẦN (không side-effect) cho syncVisibility navbar:
            // còn back được = manager đang xem 1 NV cụ thể.
            // GĐ ở chính trang CÁ NHÂN (selected === current) thì KHÔNG có gì để
            // back → loại trừ để navbar không hiện nút thừa.
            window.__vdDashCanBack = () =>
                !!(this.isTeamManager && this.state.selected_user_id
                   && this.state.selected_user_id !== this.state.current_user_id);
            this._measureNewPills();
            // FIX (user 2026-06-21): popover "CUỘC GỌI THÁNG NÀY" (recHover) bị kẹt khi
            // BẤM mở 1 khách (preview phủ lên -> mouseleave trên tag KHÔNG kích hoạt).
            // Đóng NGAY khi pointerdown ra ngoài popover; cũng đóng khi cuộn / ẩn tab.
            this._onDocPointerDown = (ev) => {
                if (!this.state.recHover) return;
                const t = ev.target;
                if (t && t.closest && t.closest('.o_vd_rec_pop')) return; // bấm trong popover -> giữ
                this._closeRecNow();
            };
            this._onDocScrollClose = (ev) => {
                if (!this.state.recHover) return;
                // FIX (user 2026-07-08): CUỘN BÊN TRONG popover (danh sách ghi âm)
                // KHÔNG được đóng popup — trước đây scroll capture=true bắt cả cuộn
                // nội bộ nên popup biến mất khi kéo xem cuộc gọi dưới. Chỉ đóng khi
                // cuộn NỀN trang (target không thuộc popover).
                const t = ev && ev.target;
                if (t && t.closest && t.nodeType === 1 && t.closest('.o_vd_rec_pop')) return;
                this._closeRecNow();
            };
            window.addEventListener('pointerdown', this._onDocPointerDown, true);
            window.addEventListener('scroll', this._onDocScrollClose, true);
            document.addEventListener('visibilitychange', this._onDocScrollClose);
            // Đo độ trễ BẤM→cập nhật: ghi mốc ở capture-phase (trước handler OWL).
            this._onDocClickTimer = (ev) => {
                const t = ev.target;
                if (t && t.closest && t.closest('.o_vd_crm_dashboard')) {
                    this._clickT0 = performance.now();
                }
            };
            document.addEventListener('click', this._onDocClickTimer, true);
            // Đóng các popover CLICK khi bấm RA NGOÀI.
            this._onDocClickPin = (ev) => {
                const t = ev.target;
                const closest = t && t.closest ? (s) => t.closest(s) : () => null;
                // 5 ô filter (click-ghim) → đóng nếu bấm ngoài ô.
                if (this.state.pinnedTile && !closest('.o_vd_tile_clickable')) {
                    this.state.pinnedTile = "";
                }
                // GHI ÂM THAM KHẢO → đóng nếu bấm ngoài filter + popover.
                if (this.state.refRecHover && !closest('.o_vd_refrec_filter') && !closest('.o_vd_refrec_pop')) {
                    this.state.refRecHover = null;
                }
                // Menu "Xa hơn" của bộ lọc hẹn → đóng nếu bấm ngoài.
                if (this.state.cbMoreOpen && !closest('.o_vd_daymore')) {
                    this.state.cbMoreOpen = "";
                }
                // Menu bánh răng trên dòng → đóng nếu bấm ngoài.
                if (this.state.rowGearOpen && !closest('.o_vd_rowgear')) {
                    this.state.rowGearOpen = 0;
                }
            };
            document.addEventListener('click', this._onDocClickPin, false);
        });
        // Sau mỗi lần render lại (đổi NV / load data) → đo lại vùng pill KHÁCH MỚI.
        // + ĐO ĐỘ TRỄ THỰC: từ lúc BẤM (capture-phase, trước handler) → tới khi DOM
        //   cập nhật xong (onPatched) = handler + render(dựng vDOM+getter) + patch.
        //   Log MỌI lần bấm để thấy đúng con số "đơ" (kể cả khi pha render mới là thủ
        //   phạm — onWillPatch/onPatched cũ chỉ đo patch nên bỏ sót).
        onWillPatch(() => { this._patchT0 = performance.now(); });
        onPatched(() => {
            this._measureNewPills();
            const nowp = performance.now();
            if (this._patchT0) window.__vdLastPatchMs = Math.round(nowp - this._patchT0);
            if (this._clickT0) {
                const ms = Math.round(nowp - this._clickT0);
                window.__vdClickToPatchMs = ms;
                this._clickT0 = 0;
                try { console.warn("[VD dashboard] BẤM→cập nhật", ms, "ms (patch " + (window.__vdLastPatchMs||0) + "ms)"); } catch (_e) {}
            }
        });
        onWillUnmount(() => {
            window.removeEventListener('keydown', this._onKeydown);
            if (this._pillHoverTimer) { clearTimeout(this._pillHoverTimer); this._pillHoverTimer = null; }
            if (this._pillTipEl) { try { this._pillTipEl.remove(); } catch (_e) {} this._pillTipEl = null; }
            if (this._khShowTimer) { clearTimeout(this._khShowTimer); this._khShowTimer = null; }
            if (this._khHideTimer) { clearTimeout(this._khHideTimer); this._khHideTimer = null; }
            if (this._khInfoEl) { try { this._khInfoEl.remove(); } catch (_e) {} this._khInfoEl = null; }
            if (this._tileShowTimer) { clearTimeout(this._tileShowTimer); this._tileShowTimer = null; }
            if (this._tileHideTimer) { clearTimeout(this._tileHideTimer); this._tileHideTimer = null; }
            if (this._tilePopEl) { try { this._tilePopEl.remove(); } catch (_e) {} this._tilePopEl = null; }
            if (this._onDocClickPin) { document.removeEventListener('click', this._onDocClickPin, false); this._onDocClickPin = null; }
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
            if (this._trainingTick) {
                clearInterval(this._trainingTick);
                this._trainingTick = null;
            }
            if (this.bus && this.bus.unsubscribe && this._onLeadsPushed) {
                this.bus.unsubscribe("vd.leads.pushed", this._onLeadsPushed);
                this._onLeadsPushed = null;
            }
            if (this._onDocPointerDown) {
                window.removeEventListener('pointerdown', this._onDocPointerDown, true);
                this._onDocPointerDown = null;
            }
            if (this._onDocScrollClose) {
                window.removeEventListener('scroll', this._onDocScrollClose, true);
                document.removeEventListener('visibilitychange', this._onDocScrollClose);
                this._onDocScrollClose = null;
            }
            // Đảm bảo scroll lock + body class được dọn nếu navigate đi
            document.body.classList.remove('o_vd_preview_active');
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
        });

        onWillStart(async () => {
            // PERF r3 (user spec 2026-06-20): bootstrap NHẸ TRƯỚC → biết role + uid
            // để GĐ vào THẲNG chế độ cá nhân, KHÔNG load 'all' thừa (~750ms) rồi mới
            // load 'self'. Quyết định phạm vi xong mới gọi loadDashboard 1 LẦN.
            try {
                const sel0 = this.state.selected_user_id;
                if ((this._dirDefaultPersonal && !sel0) || sel0) {
                    const b = await this.orm.call("crm.lead", "dashboard_bootstrap", []);
                    if (b) {
                        const cur = b.current_user_id || 0;
                        if (b.is_manager
                            && ((b.is_director && this._dirDefaultPersonal && !sel0)
                                || (sel0 && sel0 === cur))) {
                            this.state.dirTeamMode = true;
                            this.state.selected_user_id = cur;
                        }
                    }
                }
            } catch (_e) { /* bootstrap lỗi → loadDashboard mặc định bên dưới */ }
            this._dirDefaultPersonal = false;

            await this.loadDashboard();
            // Nạp báo cáo CHIA SỐ Pancake 1 LẦN (nền) — tab CHIA SỐ + dialog chia số cần.
            this._maybeLoadPancakeReport();
            // Nạp bảng THƯỞNG treo (admin cấu hình) — chạy nền, không chặn dashboard.
            this.orm.call("vd.bonus.team", "vd_bonus_board", [this.state.selected_user_id || false])
                .then((d) => { this.state.bonusBoard = d || { personal: [], team: [] }; })
                .catch(() => {});
            // Nạp SẴN ghi âm tham khảo (global) → hover ra NGAY. Chạy nền.
            this.orm.call("crm.lead", "vd_reference_recordings", []).then((d) => {
                this.state.refRecData = {
                    people: (d && d.people) || [],
                    min_minutes: (d && d.min_minutes) || 5,
                };
            }).catch(() => {});
            if (this.isTeamManager) {
                // Danh sách NV cho picker (chạy NỀN — không chặn render).
                this._reloadDashUsers();
                // PERF: KHÔNG await analytics — dashboard render NGAY, insight đổ sau.
                if (this.isAdminView && this.state.adminTab === 'overview') {
                    this.loadAnalytics();
                } else if (this.state.is_team_leader) {
                    // Trưởng nhóm / GĐ cá nhân: AWAIT analytics (scope phòng, nhẹ) để
                    // bảng NV hiện CÙNG LÚC với các bảng khác, không trễ sau (user spec
                    // 2026-06-20 r9). Bảng THU chỉ hiện NV phòng mình.
                    await this.loadAnalytics();
                    // Nền: nạp sẵn NV toàn công ty để hover GIÃN hiện ngay (r11).
                    if (this.state.is_manager && this.state.dirTeamMode) {
                        this._prefetchAllEmployees();
                    }
                }
            } else {
                // NV thường: nạp analytics CHÍNH MÌNH (backend tự bó 1 dòng) để hiện
                // THANH TỔNG QUAN cá nhân trên cùng — DÙNG CHUNG template VdKhTeamList
                // với bảng danh sách NV (sửa 1 chỗ tự đồng bộ). Chạy nền.
                this.loadAnalytics();
            }
        });
    }

    // ===== BẢO MẬT: NV tự đổi mật khẩu khi bị buộc đổi (gate dashboard) =====
    async changeOwnPassword() {
        const f = this.state.pwForm;
        if (!f.old || !f.new1 || !f.new2) {
            this.notification.add("Vui lòng nhập đủ 3 ô mật khẩu.", { type: "warning" });
            return;
        }
        if (f.new1 !== f.new2) {
            this.notification.add("Mật khẩu mới nhập lại không khớp.", { type: "warning" });
            return;
        }
        if (f.new1.length < 6) {
            this.notification.add("Mật khẩu mới phải từ 6 ký tự.", { type: "warning" });
            return;
        }
        if (this.state.pwSaving) return;
        this.state.pwSaving = true;
        try {
            await this.orm.call("res.users", "vd_change_my_password", [f.old, f.new1]);
            this.notification.add("Đổi mật khẩu thành công! Vui lòng đăng nhập lại.",
                { type: "success" });
            this.state.must_change_password = false;
            this.state.pwForm = { old: "", new1: "", new2: "" };
            // Đổi mật khẩu của chính mình -> Odoo vô hiệu phiên cũ; tải lại để
            // về màn đăng nhập sạch (tránh lỗi 401 lửng lơ).
            browser.setTimeout(() => browser.location.reload(), 1200);
        } catch (e) {
            this.notification.add(
                "Đổi mật khẩu thất bại — kiểm tra lại mật khẩu cũ.", { type: "danger" });
        } finally {
            this.state.pwSaving = false;
        }
    }

    // ============ 🔔 CHUÔNG BÁO "CÓ SỐ ĐẨY LÊN" ============
    _initPushAudio() {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            if (!this._audioCtx) this._audioCtx = new Ctx();
            // Chính sách autoplay: mở khoá AudioContext theo cử chỉ đầu tiên.
            const unlock = () => {
                try {
                    if (this._audioCtx && this._audioCtx.state === "suspended") {
                        this._audioCtx.resume();
                    }
                } catch (e) { /* ignore */ }
            };
            window.addEventListener("pointerdown", unlock, { once: true });
            window.addEventListener("keydown", unlock, { once: true });
        } catch (e) { /* ignore */ }
    }

    _playPushChime() {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            if (!this._audioCtx) this._audioCtx = new Ctx();
            const ctx = this._audioCtx;
            if (ctx.state === "suspended") { try { ctx.resume(); } catch (e) {} }
            const t0 = ctx.currentTime;
            const beep = (dt, freq) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "triangle";
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.0001, t0 + dt);
                gain.gain.exponentialRampToValueAtTime(0.9, t0 + dt + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dt + 0.45);
                osc.connect(gain).connect(ctx.destination);
                osc.start(t0 + dt);
                osc.stop(t0 + dt + 0.5);
            };
            // "ding-ding-ding" cao + to, lặp 2 vòng cho NV dễ nghe.
            const notes = [880, 1174.7, 880, 1318.5];
            notes.forEach((f, i) => beep(i * 0.22, f));
            notes.forEach((f, i) => beep(1.0 + i * 0.22, f));
        } catch (e) { /* ignore */ }
    }

    _handleLeadsPushed(payload) {
        const cnt = (payload && payload.count) || 0;
        const from = (payload && payload.from) || "";
        this._playPushChime();
        this.notification.add(
            `Bạn vừa được đẩy ${cnt} số khách mới` +
                (from ? ` (từ ${from})` : "") +
                ". Kiểm tra bảng KHÁCH MỚI!",
            { type: "success", sticky: true, title: "🔔 CÓ SỐ MỚI ĐẨY LÊN" }
        );
        // Nạp lại dashboard để KH mới hiện ngay.
        try { this.loadDashboard(); } catch (e) { /* ignore */ }
    }

    async loadDashboard() {
        this.state.loading = true;
        this.state.recHover = null;   // đóng popover ghi âm khi đổi NV / load lại
        // Mỗi lần tải (đổi NV) → bảng KHÁCH MỚI về dạng thu gọn mặc định.
        this.state.newTableExpanded = false;
        // Reset coachmark CHỐT BÁO GIÁ → hiện lại nếu NV này vẫn đang bị khoá.
        this.state.quoteGuideDismissed = false;
        // arg2 team_scope: GĐ chế độ CÁ NHÂN → backend giữ is_team_leader (bảng NV
        // phòng mình) kể cả khi drill vào 1 NV trong phòng.
        const args = [this.state.selected_user_id || 0, !!this.state.dirTeamMode];
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

    // Tải báo cáo chia số Pancake (nặng ~1.5s) TÁCH khỏi tải chính. Gọi 1 LẦN lúc
    // mở trang (KHÔNG gọi sau mỗi reload — trước đây gọi trong loadDashboard làm cứ
    // ~1.5s sau mỗi thao tác lại có 1 cú vẽ-lại-toàn-trang bất ngờ = GIẬT). Chuyển
    // số thủ công không đổi tỷ lệ xin số nên không cần nạp lại. Throttle 60s phòng hờ.
    _maybeLoadPancakeReport(force) {
        if (!this.state.is_manager) return;
        const now = Date.now();
        if (!force && this._pkRepAt && now - this._pkRepAt < 60000) return;
        this._pkRepAt = now;
        this.orm.call("crm.lead", "vd_pancake_dist_reports", [])
            .then((rep) => { if (rep) Object.assign(this.state, rep); })
            .catch(() => {});
    }

    // ===== Mở/đóng dropdown "➕ Thêm NV nhận số" (bật lại NV đang tắt) =====
    toggleDistAdd() {
        this.state.distAddOpen = !this.state.distAddOpen;
    }

    // ===== BẬT/TẮT nhận số Pancake cho 1 NV (nút trên báo cáo chia số) =====
    async onTogglePancakeNV(uid) {
        if (!uid || this._pkToggling) return;
        this._pkToggling = true;
        try {
            await this.orm.call("res.users", "vd_toggle_pancake_receive", [uid]);
            // Tải lại 2 báo cáo để cập nhật ngay trạng thái bật/tắt + cân bằng.
            const rep = await this.orm.call("crm.lead", "vd_pancake_dist_reports", []);
            Object.assign(this.state, rep);
        } catch (e) {
            // Không có quyền / lỗi → bỏ qua, không phá dashboard.
            console.warn("Toggle Pancake NV lỗi:", e);
        } finally {
            this._pkToggling = false;
        }
    }

    // ===== SỬA TAY số liệu 1 cột (icon cây bút) — admin/quản lý =====
    onEditRate(d) {
        if (!d || !d.iso) return;
        this.state.rateEdit = {
            iso: d.iso,
            label: (d.label || "") + " " + (d.day || ""),
            khach: d.total || 0,
            xin: d.with_phone || 0,
        };
    }
    cancelRateEdit() {
        this.state.rateEdit = null;
    }
    async saveRateEdit() {
        const e = this.state.rateEdit;
        if (!e) return;
        try {
            await this.orm.call("vd.pancake.rate.override", "vd_save_rate_override",
                [e.iso, Number(e.khach) || 0, Number(e.xin) || 0]);
            const rep = await this.orm.call("crm.lead", "vd_pancake_dist_reports", []);
            Object.assign(this.state, rep);
            this.state.rateEdit = null;
        } catch (err) {
            console.warn("Lưu số liệu tay lỗi:", err);
        }
    }
    async clearRateEdit() {
        const e = this.state.rateEdit;
        if (!e) return;
        try {
            await this.orm.call("vd.pancake.rate.override", "vd_clear_rate_override", [e.iso]);
            const rep = await this.orm.call("crm.lead", "vd_pancake_dist_reports", []);
            Object.assign(this.state, rep);
            this.state.rateEdit = null;
        } catch (err) {
            console.warn("Xoá số liệu tay lỗi:", err);
        }
    }

    // ===== DANH SÁCH SĐT BỊ LOẠI khỏi chia số (kiểm tra logic gộp) =====
    setPancakeTrend(period) {
        this.state.pancakeTrendPeriod = period;
    }
    // Trả mảng dữ liệu biểu đồ tỷ lệ theo kỳ đang chọn (day/week/month).
    pancakeTrendData(rep) {
        const p = this.state.pancakeTrendPeriod;
        if (p === "week") return (rep && rep.rate_weeks) || [];
        if (p === "month") return (rep && rep.rate_months) || [];
        return (rep && rep.rate7) || [];
    }

    async openPancakeExcluded(scope) {
        this.state.pkExcluded = {
            open: true, scope, loading: true, items: [], summary: {},
        };
        try {
            const data = await this.orm.call(
                "crm.lead", "vd_pancake_excluded_list", [scope]);
            this.state.pkExcluded = {
                open: true, scope,
                loading: false,
                items: (data && data.items) || [],
                summary: (data && data.summary) || {},
            };
        } catch (e) {
            console.warn("Tải danh sách SĐT loại lỗi:", e);
            this.state.pkExcluded = {
                open: true, scope, loading: false, items: [], summary: {},
            };
        }
    }
    closePancakeExcluded() {
        this.state.pkExcluded = null;
    }

    // ===== 📊 BẢNG CHI TIẾT 30 NGÀY (mỗi cột 1 ngày, mỗi ô = TikTok | Facebook) =====
    async openPancakeMatrix() {
        this.state.pkMatrix = { open: true, loading: true, days: [], rows: [], totals: null };
        try {
            const data = await this.orm.call("crm.lead", "vd_pancake_30day_matrix", [30]);
            this.state.pkMatrix = {
                open: true, loading: false,
                days: (data && data.days) || [],
                rows: (data && data.rows) || [],
                totals: (data && data.totals) || null,
            };
        } catch (e) {
            console.warn("Tải bảng 30 ngày lỗi:", e);
            this.state.pkMatrix = { open: true, loading: false, days: [], rows: [], totals: null };
        }
    }
    closePancakeMatrix() {
        this.state.pkMatrix = null;
    }

    // ===== 📢 CHIẾN DỊCH SPAM ZALO (gate khoá dashboard) =====
    // Render HTML thô (nội dung admin soạn) an toàn qua markup.
    mk(s) {
        return markup(s || "");
    }
    async _loadBroadcast() {
        try {
            const c = await this.orm.call("vd.broadcast.campaign", "vd_my_broadcast", []);
            // Chỉ reset bước/form khi chuyển sang chiến dịch KHÁC (tránh xoá dữ liệu
            // NV đang gõ mỗi lần refresh 60s).
            const prevId = this.state.broadcast && this.state.broadcast.id;
            this.state.broadcast = c || null;
            if (c && c.id !== prevId) {
                this.state.broadcastStep = 1;
                this.state.broadcastForm = { sent: "", committed: false, note: "" };
            }
            // MỐC đếm 15 phút = lúc NV đã tải ≥1 file và bấm sang Bước 2 (KHÔNG phải
            // lúc popup hiện). Lưu sessionStorage theo chiến dịch → reload giữ nguyên.
            if (c) {
                let anchor = 0, dl = 0;
                try {
                    anchor = parseInt(browser.sessionStorage.getItem("vd_bc_anchor_" + c.id) || "0", 10);
                    dl = parseInt(browser.sessionStorage.getItem("vd_bc_dl_" + c.id) || "0", 10);
                } catch (_e) { /* ignore */ }
                this.state.broadcastShownAt = anchor || 0;   // 0 = chưa bắt đầu đếm
                this.state.broadcastDownloaded = !!dl;
            } else {
                this.state.broadcastShownAt = 0;
                this.state.broadcastDownloaded = false;
            }
        } catch (_e) {
            // Model chưa cài / lỗi → không chặn dashboard.
            this.state.broadcast = null;
        }
    }
    // Đang có chiến dịch chưa báo cáo → khoá toàn bộ trang.
    get broadcastLockActive() {
        return !!this.state.broadcast;
    }
    goBroadcastStep(n) {
        this.state.broadcastStep = n;
    }
    // NV bấm "Tải xuống" 1 file → đánh dấu đã tải (điều kiện để bắt đầu đếm giờ).
    markBroadcastDownloaded() {
        const c = this.state.broadcast;
        if (!c) return;
        this.state.broadcastDownloaded = true;
        try { browser.sessionStorage.setItem("vd_bc_dl_" + c.id, "1"); } catch (_e) {}
    }
    // Bấm "Đã tải video — Tiếp theo": phải tải ≥1 file trước; khi đó MỚI bắt đầu
    // đếm 15 phút (đặt mốc anchor = bây giờ, lưu sessionStorage).
    proceedFromDownloadStep() {
        const c = this.state.broadcast;
        if (!c) return;
        if (!this.state.broadcastDownloaded) {
            this.notification.add(
                "Bạn phải tải ít nhất 1 video/hình ảnh về máy trước khi sang bước tiếp theo.",
                { type: "warning" });
            return;
        }
        if (!this.state.broadcastShownAt) {
            const now = Date.now();
            this.state.broadcastShownAt = now;
            try { browser.sessionStorage.setItem("vd_bc_anchor_" + c.id, String(now)); } catch (_e) {}
        }
        this.goBroadcastStep(2);
    }
    // Số mili-giây còn phải chờ trước khi được bấm HOÀN THÀNH. Đếm từ mốc anchor
    // (lúc tải xong + sang bước 2). Chưa có anchor → coi như còn đủ full (chưa đếm).
    get broadcastWaitMs() {
        const c = this.state.broadcast;
        if (!c) return 0;
        const delayMin = c.finish_delay_minutes != null ? c.finish_delay_minutes : 15;
        if (!this.state.broadcastShownAt) return delayMin * 60000;
        const now = this.state.trainingNow || Date.now();
        return Math.max(0, this.state.broadcastShownAt + delayMin * 60000 - now);
    }
    get broadcastCanFinish() {
        return this.broadcastWaitMs <= 0;
    }
    get broadcastWaitLabel() {
        let sec = Math.ceil(this.broadcastWaitMs / 1000);
        const m = Math.floor(sec / 60);
        const s = sec - m * 60;
        return m + ":" + (s < 10 ? "0" : "") + s;
    }
    async submitBroadcast() {
        const c = this.state.broadcast;
        if (!c || this.state.broadcastSubmitting) return;
        const f = this.state.broadcastForm;
        const sent = parseInt(f.sent, 10);
        if (!sent || sent <= 0) {
            this.notification.add("Vui lòng nhập số nhóm Zalo đã gửi (lớn hơn 0).",
                { type: "warning" });
            return;
        }
        if (!f.committed) {
            this.notification.add("Bạn phải cam kết đã đăng bài lên trang Zalo cá nhân.",
                { type: "warning" });
            return;
        }
        this.state.broadcastSubmitting = true;
        try {
            await this.orm.call("vd.broadcast.campaign", "vd_submit_report",
                [c.id, sent, true, f.note || ""]);
            this.notification.add("Đã ghi nhận báo cáo. Chúc bạn một tuần bán hàng bùng nổ!",
                { type: "success" });
            this.state.broadcast = null;
            this.state.broadcastStep = 1;
            this.state.broadcastForm = { sent: "", committed: false, note: "" };
        } catch (e) {
            this.notification.add(
                "Gửi báo cáo thất bại. Vui lòng kiểm tra lại thông tin.", { type: "danger" });
        } finally {
            this.state.broadcastSubmitting = false;
        }
    }

    // ===== LỊCH HỌC BẮT BUỘC (banner + đếm ngược) =====
    async _loadTrainingBanner() {
        try {
            const list = await this.orm.call("vd.training.session", "vd_my_banner", []);
            this.state.trainingBanner = list || [];
        } catch (_e) {
            // Module eLearning chưa cài / lỗi → không hiện banner, không chặn dashboard.
            this.state.trainingBanner = [];
        }
    }
    // Các session ĐÃ ĐẾN GIỜ học (chưa hoàn thành) → dùng để KHOÁ dashboard.
    get openTrainingSessions() {
        return (this.state.trainingBanner || []).filter((s) => this.trainingState(s) === "open");
    }
    // Đến giờ học bắt buộc → khoá toàn bộ trang, chỉ để lại thông báo VÀO HỌC.
    // Hoàn thành (đạt) thì vd_my_banner không trả session đó nữa → tự mở khoá.
    get trainingLockActive() {
        return this.openTrainingSessions.length > 0;
    }
    // 'upcoming' (chưa tới giờ đếm ngược) | 'countdown' (còn ≤ lead phút) | 'open' (đã tới giờ)
    trainingState(s) {
        const now = this.state.trainingNow || Date.now();
        const start = s.start_ts || 0;
        const leadMs = (s.lead_minutes || 15) * 60000;
        if (now >= start) return "open";
        if (now >= start - leadMs) return "countdown";
        return "upcoming";
    }
    trainingCountdown(s) {
        const now = this.state.trainingNow || Date.now();
        let sec = Math.max(0, Math.round((s.start_ts - now) / 1000));
        const h = Math.floor(sec / 3600); sec -= h * 3600;
        const m = Math.floor(sec / 60); const ss = sec - m * 60;
        const p = (n) => (n < 10 ? "0" : "") + n;
        return h > 0 ? `${h}:${p(m)}:${p(ss)}` : `${m}:${p(ss)}`;
    }
    trainingWhen(s) {
        const d = new Date(s.start_ts);
        const p = (n) => (n < 10 ? "0" : "") + n;
        return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}/${p(d.getMonth() + 1)}`;
    }
    // Có cần đồng hồ chạy 1s (bump trainingNow → re-render) không? DÙNG Date.now()
    // THẬT (không phải trainingNow đã đóng băng) để không bỏ lỡ lúc buổi học vừa
    // bước vào cửa sổ đếm ngược. Trả true khi:
    //  - 1 buổi học đang trong cửa sổ đếm ngược (đã tới mốc "lead", chưa tới giờ), HOẶC
    //  - popup broadcast (Spam Zalo) đang chờ đủ thời gian (mm:ss còn > 0).
    // Ngoài các trường hợp đó KHÔNG đụng state → 0 re-render mỗi giây → hết đơ.
    _needsLiveTick() {
        const now = Date.now();
        const tnow = this.state.trainingNow || 0;
        for (const s of (this.state.trainingBanner || [])) {
            const start = s.start_ts || 0;
            const leadMs = (s.lead_minutes || 15) * 60000;
            // đang trong cửa sổ đếm ngược → chạy giây
            if (now >= start - leadMs && now < start) return true;
            // vừa tới giờ nhưng đồng hồ chưa vượt mốc → tick 1 nhịp để KHOÁ dashboard
            if (now >= start && tnow < start) return true;
        }
        const c = this.state.broadcast;
        if (c && this.state.broadcastShownAt) {
            const delayMin = c.finish_delay_minutes != null ? c.finish_delay_minutes : 15;
            if (this.state.broadcastShownAt + delayMin * 60000 - now > 0) return true;
        }
        return false;
    }
    // HỌC CÙNG VINADUY: mở trang khóa học (lộ trình học online của NV).
    openElearning() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "vd_elearning_overview",
            name: "Học cùng VINADUY",
        });
    }
    // 📢 Nạp thông báo điều chỉnh đơn giá (đỏ, 24h). An toàn nếu lỗi.
    async _loadPricingNotice() {
        try {
            const n = await this.orm.call("crm.lead", "vd_get_pricing_notice", []);
            this.state.pricingNotice = n || { active: false };
        } catch (_e) {
            this.state.pricingNotice = { active: false };
        }
    }

    // Báo cáo khóa học: tổng / đã học / chưa học (an toàn nếu eLearning chưa cài).
    async _loadCourseStats() {
        try {
            const s = await this.orm.call("crm.lead", "vd_my_course_stats", []);
            this.state.courseStats = s || null;
        } catch (_e) {
            this.state.courseStats = null;
        }
    }

    // VÀO HỌC: mở thẳng khóa học được chỉ định (không qua lộ trình / module học online).
    enterTraining(s) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "vd_elearning_overview",
            name: "Vào học",
            params: { vd_open_course_id: s.course_id, vd_open_course_name: s.course_name },
        });
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
    // "Quản lý" theo nghĩa rộng: manager (toàn công ty) HOẶC trưởng nhóm (cùng
    // nhóm) → đều được mở picker chọn NV + xem dashboard từng NV.
    get isTeamManager() {
        return this.state.is_manager || this.state.is_team_leader;
    }
    // NV dưới quyền trưởng nhóm (loại chính mình ra khỏi bảng "nhân viên dưới quyền").
    get teamMembers() {
        return (this.state.users || []).filter(
            (u) => u.id !== this.state.current_user_id);
    }
    // True khi trưởng nhóm đang xem dashboard của 1 NV trong nhóm (không phải của mình).
    get viewingTeamMember() {
        return !!(this.state.is_team_leader
            && this.state.selected_user_id
            && this.state.selected_user_id !== this.state.current_user_id);
    }

    // Trưởng nhóm bấm 1 NV trong bảng → xem dashboard của NV đó.
    async viewTeamUser(userId) {
        this.state.selected_user_id = userId;
        this._persistSelectedNv();
        this.state.nvDetail = null;
        await this.loadDashboard();
    }
    // Quay về dashboard của chính trưởng nhóm / Giám đốc.
    async backToMyDashboard() {
        // GĐ ở chế độ CÁ NHÂN: "của tôi" = chính GĐ (current_user_id), KHÔNG phải
        // selected_user_id=0 (vốn là "Tất cả NV" với manager).
        if (this.state.is_manager && this.state.dirTeamMode) {
            return this.goPersonal();
        }
        this.state.selected_user_id = 0;
        this._persistSelectedNv();
        this.state.nvDetail = null;
        await this.loadDashboard();
    }
    // True khi MANAGER đang xem "Tất cả NV" → render layout admin (menu dọc +
    // tab overview/team toàn công ty). Trưởng nhóm KHÔNG vào layout này (chỉ
    // xem dashboard từng NV trong nhóm qua picker).
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
        if (this.isTeamManager && this.state.selected_user_id) {
            // GĐ ở chế độ CÁ NHÂN → về bảng NV phòng mình (self), không phải all.
            if (this.state.is_manager && this.state.dirTeamMode) {
                this.goPersonal();
                return true;
            }
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
            ) || {};
            // CHỈ gán lại khi DỮ LIỆU ĐỔI THẬT. Trước đây gán mỗi 8s dù không đổi →
            // re-render TOÀN dashboard (DOM rất lớn) mỗi 8s = "lác màn hình". Đa số
            // thời điểm không ai đang gọi → data không đổi → bỏ qua → 0 re-render.
            const sig = JSON.stringify(data);
            if (sig !== this._activeCallsSig) {
                this._activeCallsSig = sig;
                this.state.activeCalls = data;
            }
            // GIÃN NHỊP THÍCH ỨNG (2026-08-14): đo trên log 24 ngày, cái này chạy
            // 176.416 lượt — NHIỀU HƠN cả số lần mở khách — trong khi tuyệt đại đa
            // số lượt trả về RỖNG (không ai đang gọi). Mỗi lượt vẫn chiếm 1 worker
            // trong 4 worker. Nay: đang có cuộc gọi -> 5s (nhạy như cũ, thậm chí
            // hơn); rỗng liên tiếp -> nới dần tới 30s. Có cuộc gọi mới là về 5s
            // ngay ở lượt kế. Giảm ~70% request mà NV không thấy khác biệt.
            const busy = Object.keys(data).length > 0;
            this._callPollIdle = busy ? 0 : (this._callPollIdle || 0) + 1;
            const next = busy ? 5000 : Math.min(30000, 8000 + this._callPollIdle * 4000);
            if (next !== this._callPollEvery) {
                this._callPollEvery = next;
                clearInterval(this._callPollInterval);
                this._callPollInterval = setInterval(() => this._refreshActiveCalls(), next);
            }
        } catch (err) {
            // Silent fail — không spam console khi WS đứt / restart server
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

    // ===== GIÁM ĐỐC: nút NHÂN VIÊN giãn/thu bảng NV (user spec 2026-06-20 r2) =====
    // Hiện nút khi là manager (Giám đốc / Admin). Mặc định bảng = NV PHÒNG GĐ;
    // hover nút → giãn ra TOÀN BỘ NV; rời chuột khỏi bảng / bấm lại → thu về phòng.
    get showDirFilters() { return !!this.state.is_manager; }
    // Reload danh sách NV theo scope hiện tại (team_scope khi GĐ ở chế độ CÁ NHÂN).
    async _reloadDashUsers() {
        if (!this.isTeamManager) return;
        const ts = this.state.is_manager && this.state.dirTeamMode;
        this.state.users = await this.orm.call(
            "crm.lead", "dashboard_users", [ts]);
    }
    // GĐ: dashboard của chính mình + bảng NV phòng mình (mặc định khi vào).
    async goPersonal() {
        if (this.state.dirTeamMode
            && this.state.selected_user_id === this.state.current_user_id
            && !this.state.empExpanded) return;
        this.state.dirTeamMode = true;
        this.state.empExpanded = false;
        this.state.selected_user_id = this.state.current_user_id;
        this._persistSelectedNv();
        this.state.nvDetail = null;
        this.state.analytics = null;
        await this.loadDashboard();
        this._reloadDashUsers();   // nền — không chặn
        // Analytics bó về phòng ban (scope='team') → bảng THU chỉ hiện NV phòng GĐ.
        await this.loadAnalytics('team');
        // Nền: nạp sẵn NV toàn công ty để hover GIÃN hiện ngay.
        if (this.state.is_manager && this.state.dirTeamMode) this._prefetchAllEmployees();
    }

    // Prefetch NV TOÀN CÔNG TY (scope=null) ở NỀN → state.allTeamGroups, để khi GĐ
    // hover GIÃN là hiện ngay toàn bộ NV mọi phòng (không chờ). Dedup bằng promise.
    _prefetchAllEmployees() {
        if (this.state.allTeamGroups.length || this._anaAllPromise) return this._anaAllPromise;
        this.state.allTeamLoading = true;
        this._anaAllPromise = this.orm.call("crm.lead", "dashboard_analytics",
            [this.state.analyticsFrom, this.state.analyticsTo, null])
            .then((d) => {
                if (d && d.kh_by_team) this.state.allTeamGroups = d.kh_by_team;
            })
            .catch(() => { this._anaAllPromise = null; })  // lỗi → cho thử lại
            .then(() => { this.state.allTeamLoading = false; });
        return this._anaAllPromise;
    }

    // Nguồn NV cho bảng team:
    //  - GĐ cá nhân + ĐANG GIÃN (hover) → TOÀN CÔNG TY (allTeamGroups), fallback
    //    phòng trong lúc tải.
    //  - còn lại (thu gọn / admin) → analytics.kh_by_team (phòng GĐ / toàn bộ admin).
    // Lúc THU luôn là phòng → KHÔNG nháy khi tải trang (user spec 2026-06-20 r11).
    // Thanh tổng quan cá nhân (trên cùng trang NV) = ĐÚNG 1 dòng của user đang
    // xem (NV đăng nhập, hoặc NV được quản lý chọn) — lọc từ khTeamGroups để DÙNG
    // CHUNG template VdKhTeamList (tự đồng bộ khi sửa giao diện danh sách NV).
    get selfTeamGroups() {
        const uid = this.state.selected_user_id || this.state.current_user_id;
        for (const grp of (this.khTeamGroups || [])) {
            const nv = (grp.nvs || []).find((n) => n.user_id === uid);
            if (nv) return [{ ...grp, nvs: [nv] }];
        }
        return [];
    }

    get khTeamGroups() {
        const a = this.state.analytics;
        const dept = (a && a.kh_by_team) || [];
        if (this.state.is_manager && this.state.dirTeamMode && this.state.empExpanded
            && this.state.allTeamGroups.length) {
            return this.state.allTeamGroups;
        }
        return dept;
    }

    // ===== GIÃN / THU bảng NV (GĐ) — chỉ đổi CHIỀU CAO (mép dưới trượt), KHÔNG
    // đổi dữ liệu (bảng đã luôn hiện đủ NV phòng).
    //  - HOVER nút NHÂN VIÊN → giãn xem nhanh; rời chuột → thu (nếu chưa ghim).
    //  - BẤM nút → GHIM mở (luôn xổ hết NV); bấm lần nữa → bỏ ghim + thu.
    // Tách "ghim" khỏi "giãn do hover" để bấm KHÔNG bị toggle-đóng sau khi hover
    // đã mở sẵn (lỗi 2026-06-20 r8). =====
    expandEmployees() {
        if (!this.state.is_manager || this.state.empExpanded) return;
        this.cancelCollapse();
        this.state.empExpanded = true;
        // Chưa có dữ liệu toàn công ty → nạp ngay (hiện spinner ở hint).
        if (!this.state.allTeamGroups.length) this._prefetchAllEmployees();
    }
    collapseEmployees() {
        if (!this.state.empExpanded) return;
        this.state.empExpanded = false;
    }
    // ===== GRACE-DELAY collapse (r6): mouseleave panel → hẹn 350ms; khi timer
    // chạy, RE-VERIFY bằng :hover THẬT của DOM — nếu chuột VẪN trong panel (vd
    // rê xuống danh sách NV, mouseleave là nhiễu do reflow) thì KHÔNG thu. Đây
    // là cách miễn nhiễm với mouseleave nhiễu (không phụ thuộc mouseenter bù). =====
    scheduleCollapse() {
        if (!this.state.empExpanded) return;
        browser.clearTimeout(this._empCollapseTimer);
        this._empCollapseTimer = browser.setTimeout(() => {
            const el = this.tlPanelRef.el;
            const stillInside = el && el.matches && el.matches(":hover");
            // Đang mở popover của bảng NV (hover tên NV / tổng KH / cuộc gọi) →
            // popover render NGOÀI panel (gốc dashboard) nên con trỏ "rời" panel =
            // mouseleave nhiễu. KHÔNG thu khi còn popover (user đang xem bảng).
            const popoverOpen = !!(this.state.recHover || this.state.reminderHover
                || this.state.newTodayHover || this.state.todayCallsHover
                || this.state.refRecHover || this.state.cancelHover);
            console.log("[VD emp] timer thu — trong panel?", !!stillInside,
                        "| popover mở?", popoverOpen);
            if (stillInside) return;            // chuột vẫn trong panel → giữ
            if (popoverOpen) {                  // đang xem popover → chờ, poll lại
                this.scheduleCollapse();
                return;
            }
            this.collapseEmployees();
        }, 350);
    }
    cancelCollapse() {
        browser.clearTimeout(this._empCollapseTimer);
    }

    setFocus(focus) {
        if (this.state.focus === focus) return;
        this.state.focus = focus;
        // Reset về tab overview khi đổi focus — tránh kẹt ở tab đã ẩn (vd
        // đang ở 'performance' rồi switch sang KH focus mà tab performance bị hide)
        this.state.adminTab = 'overview';
        this.state.nvDetail = null;
    }

    // Chỉ MANAGER/ADMIN được mở dashboard cá nhân của NV. Trưởng nhóm CHỈ xem
    // bảng tổng, KHÔNG bao giờ vào trang cá nhân NV (user spec 2026-06-14).
    get canDrillNv() {
        return !!this.state.is_manager;
    }

    // Click tên NV trong bảng → switch dashboard sang NV cụ thể đó
    async selectNvFromDashboard(userId) {
        if (!userId || !this.canDrillNv) return;
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
        // _silentStageLoad: refresh NGẦM sau khi đóng popup → KHÔNG bật loading
        // (tránh cảm giác "load trang" khi trở về). Dashboard vẫn hiện từ cache,
        // pill cập nhật im lặng khi data về.
        if (!this._silentStageLoad) this.state.leadsLoading = true;
        const args = [stageId];
        if (this.state.selected_user_id) {
            args.push(this.state.selected_user_id);
        }
        const stage = this.state.stages.find(s => s.id === stageId);

        // PERF 2026-08-14: TRƯỚC ĐÂY 9 RPC bắn SONG SONG bằng Promise.all. Song
        // song ở client nhưng server chỉ có 4 worker → 1 người vào dashboard là
        // chiếm sạch, người thứ hai/ba phải xếp hàng => "đơ/lác" giờ cao điểm.
        // GIỜ gọi 1 endpoint dashboard_page gộp cả 9 (xem crm_lead.py) → 1 worker,
        // 1 round-trip, và 9 bảng dùng chung ORM cache thay vì đọc DB 9 lượt.
        const call = (method, a) => this.orm.call("crm.lead", method, a).catch(() => []);

        if (stage?.code === 'new') {
            // Khi vào stage "Khách mới" → render thêm các bảng THI CÔNG GẤP /
            // XỬ LÝ VẤN ĐỀ / tham khảo / mất tích... → gộp tất cả query 1 lần.
            const p = await this.orm
                .call("crm.lead", "dashboard_page", args)
                .catch(() => ({}));
            this.state.leads = p.leads || [];
            this.state.leadsWithProblemsAll = this._markupBreakdown(p.withProblems || []);
            this.state.leadsUrgentConstructionAll = this._markupBreakdown(p.urgent || []);
            this.state.leadsLostAll = p.lost || [];
            this.state.cancelReport = Array.isArray(p.cancelReport) ? p.cancelReport : [];
            this.state.leadsNotCalledAll = p.notCalled || [];
            this.state.leadsReferenceAll = p.reference || [];
            this.state.leadsQuotedLostAll = p.quotedLost || [];
            this.state.leadsPlannedSignAll = p.plannedSign || [];
        } else {
            this.state.leads = await call("dashboard_leads", args);
            this.state.leadsWithProblemsAll = [];
            this.state.leadsUrgentConstructionAll = [];
            this.state.leadsLostAll = [];
            this.state.leadsNotCalledAll = [];
            this.state.leadsReferenceAll = [];
            this.state.leadsQuotedLostAll = [];
            this.state.leadsPlannedSignAll = [];
            this.state.cancelReport = [];
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
            // User spec 2026-06-11: BỎ 8 màu theo trạng thái gọi — thẻ TRƠN,
            // phân loại bằng 3 VÙNG (chưa gọi / cần Zalo / đã Zalo) thay cho màu.
            return 'o_vd_pill_plain';
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
            // TikTok + Zalo dùng CHUNG icon TikTok (user spec 2026-07-15)
            if (p === 'tiktok' || p === 'zalo') return '🎵';
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
    // Bản ĐÃ LỌC theo newDayFilter (dùng render pill KHÁCH MỚI). Bản gốc =
    // _leadsNoProblemsRaw (để ĐẾM số khách mỗi khoảng, không phụ thuộc lọc).
    get leadsNoProblems() {
        return this._dayBucketFilter(this._leadsNoProblemsRaw, this.state.newDayFilter || 0);
    }
    get _leadsNoProblemsRaw() {
        // User spec 2026-05-28 (round 2 — revert): chỉ loại lead trong
        // "CHƯA GỌI ĐƯỢC" bucket. KH có báo giá (complete=True) chưa CHỐT
        // VẪN ở KH MỚI (pill xanh lá + 💰) — KHÔNG loại trừ.
        const notCalledIds = new Set(
            (this.state.leadsNotCalledAll || []).map(l => l.id)
        );
        const base = (this.state.leads || []).filter(l => !notCalledIds.has(l.id));
        // User spec 2026-06-09 (r2): sắp theo SỐ NGÀY GỌI ÍT → NHIỀU. Chưa gọi (0
        // ngày) lên ĐẦU; gọi nhiều ngày (đỏ must_zalo, ~3 ngày) xuống CUỐI cùng.
        // 💰 đã báo giá pin đầu. Cùng số ngày: đỏ must_zalo xếp sau (đỏ gom cuối
        // nhóm, không lẫn xanh). Sort ỔN ĐỊNH (JS stable) → giữ thứ tự backend.
        const _hasQuote = (l) => l.intake_complete && !l.intake_locked && !l.quote_cancelled;
        const _key = (l) => {
            if (_hasQuote(l)) return -1;
            const days = (l.call_stats || {}).distinct_days || 0;
            return days * 2 + (l.must_zalo ? 1 : 0);
        };
        return [...base].sort((a, b) => _key(a) - _key(b));
    }

    // ===== 3 VÙNG cột KHÁCH MỚI (user spec 2026-06-11) — phễu rõ ràng, thay
    // cho tô sáng + 8 màu. Vùng 1: chưa gọi cuộc nào · Vùng 2: đã gọi nhưng
    // CHƯA kết bạn Zalo · Vùng 3: ĐÃ kết bạn Zalo (hoặc đã đánh dấu không tìm
    // thấy Zalo → coi như xong bước Zalo). KH điền đủ báo giá nằm YÊN trong
    // vùng của nó (chỉ gắn badge 💰), KHÔNG tách vùng riêng. =====
    get newPillsZones() {
        const z1 = [], z2 = [], z3 = [];
        for (const l of (this.leadsNoProblems || [])) {
            const total = (l.call_stats || {}).total || 0;
            if (total === 0) { z1.push(l); continue; }   // chưa gọi
            if (l.zalo_consulted || l.zalo_not_found) z3.push(l);  // đã xong bước Zalo
            else z2.push(l);                              // đã gọi, chưa Zalo
        }
        return [
            { key: 'z1', icon: '📞', label: 'CHƯA GỌI', hint: 'Gọi ngay', leads: z1 },
            { key: 'z2', icon: '💬', label: 'CẦN KẾT BẠN ZALO', hint: 'Đã gọi — kết bạn Zalo để chăm', leads: z2 },
            { key: 'z3', icon: '✅', label: 'ĐÃ KẾT BẠN ZALO', hint: 'Đang chăm → đẩy lên Báo giá', leads: z3 },
        ];
    }
    // KHI THU GỌN: mỗi vùng chỉ DỰNG 25 pill đầu (thay vì cả 300+ rồi cắt bằng CSS)
    // → DOM nhẹ hẳn, render nhanh; vẫn giữ cả 3 vùng + SỐ THẬT ở header. Bấm "XEM
    // TẤT CẢ" → dựng đủ. `count` = số thật của vùng (dùng cho header, không phải số
    // pill đã cắt).
    get newPillsZonesCapped() {
        const expanded = this.state.newTableExpanded;
        return this.newPillsZones.map((z) => ({
            ...z,
            count: z.leads.length,
            leads: expanded ? z.leads : z.leads.slice(0, 25),
        }));
    }
    get newPillsHasMore() {
        if (this.state.newTableExpanded) return false;
        return this.newPillsZones.some((z) => z.leads.length > 25);
    }

    // CẦN GỌI LẠI HÔM NAY (user spec 2026-06-12, Logic B) — badge ⏰, thay cho
    // viền glow cũ. Đơn giản: đã gọi rồi (total>0) + CHƯA đủ 3 ngày gọi khác
    // nhau + HÔM NAY chưa gọi cuộc nào. Gọi 1 cuộc hôm nay hoặc đủ 3 ngày → tắt.
    // Vùng 1 (total=0) không bao giờ dính → badge chỉ hiện ở vùng 2 & 3.
    needsCallToday(lead) {
        if (this.selectedStage?.code !== 'new') return false;
        const s = lead.call_stats || {};
        if ((s.total || 0) === 0) return false;          // chưa gọi → thuộc vùng 1
        if ((s.distinct_days || 0) >= 3) return false;   // đủ 3 ngày → thôi
        if (s.has_call_today) return false;              // hôm nay gọi rồi → thôi
        return true;
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
    // KH ở bảng Khách mới CHƯA GỌI cuộc nào VÀ đã SANG NGÀY MỚI (tạo từ hôm qua
    // trở về trước) → hover chỉ hiện 1 dòng chữ TO "X NGÀY RỒI CHƯA GỌI".
    isUncalledStale(lead) {
        const s = this.selectedStage;
        if (!s || s.code !== 'new') return false;
        const uncalled = !lead.call_stats || (lead.call_stats.total || 0) === 0;
        return uncalled && (lead.create_calendar_days || 0) >= 1;
    }
    // "ngày thứ N" = số ngày lịch đã trải qua kể cả hôm tạo: hôm qua tạo = 2 ngày.
    uncalledDaysLabel(lead) {
        return (lead.create_calendar_days || 0) + 1;
    }
    // Section 2 dùng list riêng (mọi stage, không chỉ stage 'new').
    get leadsWithProblems() {
        return this._applyDayFilter(this.state.leadsWithProblemsAll || []);
    }

    get leadsUrgentConstruction() {
        return this._applyDayFilter(this.state.leadsUrgentConstructionAll || []);
    }
    // LỌC theo số ngày chưa gọi — MỖI khách chỉ thuộc 1 KHOẢNG (loại trừ nhau):
    // 3=[3,5) · 5=[5,8) · 8=[8,15) · 15=[15,25) · 25=[25,40) · 40=[40,∞). KH gọi
    // trong 3 ngày gần đây KHÔNG thuộc khoảng nào (đã gọi gần đây).
    get dayFilterOptions() { return [3, 5, 8, 15, 25, 40]; }
    _dayUpper(n) {
        const opts = this.dayFilterOptions;
        const i = opts.indexOf(n);
        return (i >= 0 && i < opts.length - 1) ? opts[i + 1] : Infinity;
    }
    _todayKey() { const d = new Date(); return d.getFullYear() + "-" + d.getMonth() + "-" + d.getDate(); }
    // Số NGÀY LỊCH từ HÔM NAY tới ngày hẹn gọi lại (âm = quá hạn, 0 = hôm nay,
    // 1 = ngày mai...). null = KH chưa đặt hẹn. TỰ XOAY theo ngày hiện tại: hẹn
    // "ngày mai" hôm nay = 1; sang hôm sau = 0 (hôm nay).
    // CACHE theo (id, ngày, callback_date) — tránh parse Date lặp lại mỗi render
    // (nguyên nhân đơ khi bấm lọc). Lưu ở Map ngoài object lead (không đụng reactive).
    _cbDaysFromNow(l) {
        if (!l || !l.callback_date) return null;
        const today = this._todayKey();
        if (this.__cbCacheDay !== today) { this.__cbCache = new Map(); this.__cbCacheDay = today; }
        const hit = this.__cbCache.get(l.id);
        if (hit && hit.cd === l.callback_date) return hit.v;
        const t = new Date(String(l.callback_date).replace(" ", "T") + "Z");
        let v = null;
        if (!isNaN(t.getTime())) {
            const now = new Date(); now.setHours(0, 0, 0, 0);
            const cbd = new Date(t); cbd.setHours(0, 0, 0, 0);
            v = Math.round((cbd.getTime() - now.getTime()) / 86400000);
        }
        this.__cbCache.set(l.id, { cd: l.callback_date, v });
        return v;
    }
    // Token ổn định theo THAM CHIẾU mảng (WeakMap) — mảng bị gán lại (reload data) →
    // token mới → memo đếm tính lại; bấm lọc (không đụng data) → giữ token → memo trúng.
    _refToken(obj) {
        if (!obj) return "0";
        if (!this.__refTokens) { this.__refTokens = new WeakMap(); this.__refSeq = 0; }
        let t = this.__refTokens.get(obj);
        if (t === undefined) { t = ++this.__refSeq; this.__refTokens.set(obj, t); }
        return String(t);
    }
    // ĐẾM 1 LƯỢT tất cả nhóm (thay vì mỗi thẻ 1 lượt × 26 thẻ). Memoize theo scope.
    _dayStats(pool) {
        const opts = this.dayFilterOptions;
        const uppers = opts.map((n) => this._dayUpper(n));
        const cb = { cb_today: 0, cb_tomorrow: 0, cb_2d: 0, cb_3d: 0, cb_week: 0, cb_nextweek: 0,
            cb_month: 0, cb_nextmonth: 0, cb_3month: 0, cb_4month: 0, cb_6month: 0, cb_1year: 0 };
        const days = {}; for (const n of opts) days[n] = 0;
        let none = 0, moigoi = 0;
        for (const l of (pool || [])) {
            // DÒNG "CHƯA GỌI" — phân theo SỐ NGÀY kể từ cuộc gọi gần nhất cho MỌI
            // khách (kể cả khách ĐÃ có hẹn: vẫn tính "bao lâu chưa gọi").
            const dd = l.days_since_call || 0;
            if (dd < opts[0]) moigoi++;  // [0,3) = VỪA GỌI
            else { for (let i = 0; i < opts.length; i++) { if (dd >= opts[i] && dd < uppers[i]) { days[opts[i]]++; break; } } }
            // DÒNG "LỊCH HẸN GỌI" — phân theo ngày hẹn (chỉ khách có hẹn).
            if (!l.callback_date) { none++; continue; }
            const d = this._cbDaysFromNow(l);
            if (d === null) continue;
            if (d <= 0) cb.cb_today++;
            else if (d === 1) cb.cb_tomorrow++;
            else if (d === 2) cb.cb_2d++;
            else if (d === 3) cb.cb_3d++;
            else if (d <= 7) cb.cb_week++;
            else if (d <= 14) cb.cb_nextweek++;
            else if (d <= 30) cb.cb_month++;
            else if (d <= 60) cb.cb_nextmonth++;
            else if (d <= 90) cb.cb_3month++;
            else if (d <= 120) cb.cb_4month++;
            else if (d <= 180) cb.cb_6month++;
            else cb.cb_1year++;
        }
        return { all: (pool || []).length, cb, none, moigoi, days };
    }
    _dayStatsCached(scope) {
        // Chữ ký RẺ trước (chỉ token tham chiếu + ngày) — KHÔNG đụng pool nặng.
        const sig = scope === "new"
            ? "new|" + this._todayKey() + "|" + this._refToken(this.state.leads) + "|" + this._refToken(this.state.leadsNotCalledAll)
            : "prob|" + this._todayKey() + "|" + this._refToken(this.state.leadsWithProblemsAll) + "|" + this._refToken(this.state.leadsUrgentConstructionAll);
        const cache = this.__dsCache || (this.__dsCache = {});
        if (cache[scope] && cache[scope].sig === sig) return cache[scope].stats;
        // Cache TRƯỢT (đổi data / sang ngày) → mới lọc+sort pool + đếm 1 lượt.
        const pool = scope === "new" ? this._leadsNoProblemsRaw : this._dayFilterPool;
        const stats = this._dayStats(pool);
        cache[scope] = { sig, stats };
        return stats;
    }
    // Nhóm lọc LỊCH HẸN GỌI — CỬA SỔ TRƯỢT theo số ngày tới ngày hẹn (tự xoay mỗi
    // ngày). Hôm nay gồm cả quá hạn (d<=0 = cần gọi hôm nay).
    get cbBucketOptions() {
        return [
            { k: "cb_today", l: "Hôm nay gọi" },
            { k: "cb_tomorrow", l: "Ngày mai gọi" },
            { k: "cb_2d", l: "2 Ngày nữa gọi" },
            { k: "cb_3d", l: "3 Ngày nữa gọi" },
            { k: "cb_week", l: "Tuần này gọi" },
            { k: "cb_nextweek", l: "Tuần sau gọi" },
            { k: "cb_month", l: "Tháng này gọi" },
        ];
    }
    // Các mốc XA — ẩn trong menu xổ xuống.
    get cbMoreOptions() {
        return [
            { k: "cb_nextmonth", l: "Tháng sau gọi" },
            { k: "cb_3month", l: "3 Tháng sau gọi" },
            { k: "cb_4month", l: "4 Tháng sau gọi" },
            { k: "cb_6month", l: "6 Tháng sau gọi" },
            { k: "cb_1year", l: "1 Năm sau gọi" },
        ];
    }
    _cbMatch(l, key) {
        if (key === "cb_none") return !(l && l.callback_date);
        const d = this._cbDaysFromNow(l);
        if (d === null) return false;
        switch (key) {
            case "cb_today": return d <= 0;
            case "cb_tomorrow": return d === 1;
            case "cb_2d": return d === 2;
            case "cb_3d": return d === 3;
            case "cb_week": return d >= 4 && d <= 7;
            case "cb_nextweek": return d >= 8 && d <= 14;
            case "cb_month": return d >= 15 && d <= 30;
            case "cb_nextmonth": return d >= 31 && d <= 60;
            case "cb_3month": return d >= 61 && d <= 90;
            case "cb_4month": return d >= 91 && d <= 120;
            case "cb_6month": return d >= 121 && d <= 180;
            case "cb_1year": return d >= 181;
            default: return false;
        }
    }
    // ===== Helper dùng CHUNG cho 2 thanh lọc (scope: 'new' = KHÁCH MỚI · 'prob' = TCG/XLVĐ)
    setFilter(scope, n) { scope === "new" ? this.setNewDayFilter(n) : this.setDayFilter(n); }
    filterVal(scope) { return scope === "new" ? this.state.newDayFilter : this.state.dayFilter; }
    filterCount(scope, k) {
        const s = this._dayStatsCached(scope);
        if (k === "cb_none") return s.none;
        if (k === "moigoi") return s.moigoi;
        if (typeof k === "string") return s.cb[k] || 0;
        return s.days[k] || 0;
    }
    filterAllCount(scope) { return this._dayStatsCached(scope).all; }
    toggleCbMore(scope) { this.state.cbMoreOpen = this.state.cbMoreOpen === scope ? "" : scope; }
    setFilterMore(scope, k) { this.setFilter(scope, k); this.state.cbMoreOpen = ""; }
    cbMoreActive(scope) { const v = this.filterVal(scope); return this.cbMoreOptions.some((o) => o.k === v); }
    // Lọc list. n=0 → tất cả; n='cb_*' → nhóm theo ngày hẹn; n số → "chưa gọi X ngày"
    // (CHỈ KH CHƯA đặt hẹn — KH có hẹn nằm ở nhóm cb_* tương ứng).
    _dayBucketFilter(list, n) {
        if (!n) return list || [];
        // Nhóm số ngày CHƯA GỌI — TẤT CẢ khách (kể cả có hẹn). Nhóm cb_* = theo lịch hẹn.
        if (n === "moigoi") return (list || []).filter((l) => (l.days_since_call || 0) < this.dayFilterOptions[0]);
        if (typeof n === "string") return (list || []).filter((l) => this._cbMatch(l, n));
        const upper = this._dayUpper(n);
        return (list || []).filter((l) => {
            const d = l.days_since_call || 0; return d >= n && d < upper;
        });
    }
    _dayBucketCount(list, n) {
        if (typeof n === "string") {
            let c = 0; for (const l of (list || [])) if (this._cbMatch(l, n)) c++; return c;
        }
        const upper = this._dayUpper(n);
        let c = 0;
        for (const l of (list || [])) {
            const dd = l.days_since_call || 0; if (dd >= n && dd < upper) c++;
        }
        return c;
    }
    dayNumLabel(d) {
        const opts = this.dayFilterOptions;
        return d === opts[opts.length - 1] ? ("TRÊN " + d + " NGÀY") : (d + " NGÀY");
    }
    dayRangeTitle(d) {
        const up = this._dayUpper(d);
        return up === Infinity ? `KH chưa gọi từ ${d} ngày trở lên` : `KH chưa gọi ${d}–${up} ngày`;
    }
    // ===== BỘ LỌC 2 bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ =====
    _applyDayFilter(list) { return this._dayBucketFilter(list, this.state.dayFilter || 0); }
    setDayFilter(n) { this.state.dayFilter = this.state.dayFilter === n ? 0 : n; }
    get _dayFilterPool() {
        const seen = new Set();
        const out = [];
        for (const l of [...(this.state.leadsWithProblemsAll || []),
                         ...(this.state.leadsUrgentConstructionAll || [])]) {
            if (l && l.id != null && !seen.has(l.id)) { seen.add(l.id); out.push(l); }
        }
        return out;
    }
    dayFilterCount(d) { return this._dayBucketCount(this._dayFilterPool, d); }
    get dayFilterAllCount() { return this._dayFilterPool.length; }
    // ===== BỘ LỌC bảng KHÁCH MỚI (độc lập) =====
    setNewDayFilter(n) { this.state.newDayFilter = this.state.newDayFilter === n ? 0 : n; }
    newDayFilterCount(d) { return this._dayBucketCount(this._leadsNoProblemsRaw, d); }
    get newDayFilterAllCount() { return this._leadsNoProblemsRaw.length; }

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
        // User spec 2026-06-13: 'Mới nhất'/'Sắp hết hạn' giờ chỉ SẮP XẾP (KH CHƯA
        // có vấn đề lên TRÊN), KHÔNG ẩn KH đã có vấn đề — tránh KH "biến mất" ngay
        // sau khi vừa tạo vấn đề (chip bật do lỡ rê chuột).
        if (f === 'newest' || f === 'expiring') {
            const dir = f === 'newest' ? 1 : -1;
            return [...list].sort((a, b) => {
                const pa = hasProblem(a) ? 1 : 0;
                const pb = hasProblem(b) ? 1 : 0;
                if (pa !== pb) return pa - pb;          // chưa có vấn đề lên trước
                return dir * (qd(a) - qd(b));
            });
        }
        return list;
    }
    setProblemSort(f) { this.state.problemSort = f; }
    // Box cuối 2 bảng — KH đã báo giá rồi mất tích (không liên lạc được).
    get leadsQuotedLost() {
        return this.state.leadsQuotedLostAll || [];
    }
    // Box "KHÁCH GỬI HỢP ĐỒNG" — đã đặt lịch ký HĐ (Làm hợp đồng - Hẹn gặp).
    get leadsPlannedSign() {
        return this.state.leadsPlannedSignAll || [];
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
    // Hover pill: hiện tooltip qua 1 ô DÙNG CHUNG cấp trang, điều khiển TRỰC TIẾP
    // bằng DOM (KHÔNG đổi state OWL) → dashboard KHÔNG vẽ lại → hover cực nhẹ. Delay
    // 90ms để rê chuột lướt qua nhiều pill không bật liên tục.
    onPillEnter(lead, ev) {
        const el = ev && ev.currentTarget;
        if (this._pillHoverTimer) clearTimeout(this._pillHoverTimer);
        this._pillHoverTimer = setTimeout(() => {
            this._pillHoverTimer = null;
            this._showPillTip(lead, el);
        }, 90);
    }
    onPillLeave() {
        if (this._pillHoverTimer) { clearTimeout(this._pillHoverTimer); this._pillHoverTimer = null; }
        this._hidePillTip();
    }
    _ensurePillTip() {
        if (this._pillTipEl && document.body.contains(this._pillTipEl)) return this._pillTipEl;
        const d = document.createElement("div");
        d.className = "o_vd_ptip";
        d.style.display = "none";
        document.body.appendChild(d);
        this._pillTipEl = d;
        return d;
    }
    _escHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"]/g,
            (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    }
    _pillTipHtml(lead) {
        const e = (s) => this._escHtml(s);
        if (this.isUncalledStale(lead)) {
            return `<div class="o_vd_ptip_big">${this.uncalledDaysLabel(lead)} NGÀY RỒI CHƯA GỌI</div>`;
        }
        const isNew = this.selectedStage && this.selectedStage.code === "new";
        const cs = lead.call_stats || {};
        // Số ngày từ ngày tạo → hôm nay (create_calendar_days = số ngày lịch đã qua).
        const createdDays = (lead.create_calendar_days != null ? lead.create_calendar_days
            : (lead.create_days != null ? lead.create_days : 0));
        if (isNew) {
            const p = [];
            // 1) DÒNG THỐNG KÊ CUỘC GỌI (dòng cuối cũ — GIỮ).
            if ((cs.total || 0) > 0) {
                let line = `📊 ${cs.total} cuộc · ${cs.distinct_days || 0} ngày`;
                if (cs.answered > 0) line += ` · 🟢 ${cs.answered} nghe`;
                p.push(`<div class="o_vd_ptip_row">${line}</div>`);
            } else {
                p.push(`<div class="o_vd_ptip_row">📊 Chưa gọi cuộc nào</div>`);
            }
            // 2) SỐ NGÀY TỪ LÚC TẠO ĐẾN HÔM NAY.
            p.push(`<div class="o_vd_ptip_row">📅 Khách đã tạo <b>${createdDays}</b> ngày</div>`);
            // 3) TỶ LỆ GỌI THÀNH CÔNG (nghe máy) = answered / tổng cuộc.
            const rate = (cs.total || 0) > 0 ? Math.round((cs.answered || 0) / cs.total * 100) : 0;
            p.push(`<div class="o_vd_ptip_row">✅ Tỷ lệ nghe máy: <b>${rate}%</b> (${cs.answered || 0}/${cs.total || 0})</div>`);
            return p.join("");
        }
        // Stage khác (won...) — giữ Tên / SĐT / NV + thông tin ký HĐ.
        const p = [];
        p.push(`<div class="o_vd_ptip_row"><b>👤</b> ${e(lead.name)}</div>`);
        p.push(`<div class="o_vd_ptip_row"><b>📞</b> ${e(lead.phone || "—")}</div>`);
        if (this.state.is_manager && lead.user_name) {
            p.push(`<div class="o_vd_ptip_row"><b>👔</b> ${e(lead.user_name)}</div>`);
        }
        if (this.selectedStage && this.selectedStage.code === "won") {
            if (lead.planned_sign_location) p.push(`<div class="o_vd_ptip_row"><b>📍</b> ${e(lead.planned_sign_location)}</div>`);
            if (lead.quote_price) p.push(`<div class="o_vd_ptip_row"><b>💰</b> ${e(this.formatVnd(lead.quote_price))}đ</div>`);
        }
        return p.join("");
    }
    _showPillTip(lead, el) {
        if (!lead || !el || !document.body.contains(el)) return;
        const d = this._ensurePillTip();
        d.innerHTML = this._pillTipHtml(lead);
        d.style.display = "block";
        const r = el.getBoundingClientRect();
        const tw = d.offsetWidth, th = d.offsetHeight;
        const vw = window.innerWidth, vh = window.innerHeight;
        let left = r.left + r.width / 2 - tw / 2;
        if (left < 6) left = 6;
        if (left + tw > vw - 6) left = vw - 6 - tw;
        let top = r.bottom + 8;
        if (top + th > vh - 6) top = r.top - th - 8;   // không đủ chỗ dưới → lật lên
        d.style.left = Math.max(6, left) + "px";
        d.style.top = Math.max(6, top) + "px";
    }
    _hidePillTip() {
        if (this._pillTipEl) this._pillTipEl.style.display = "none";
    }
    // ===== BẢNG THÔNG TIN KHÁCH HÀNG dùng CHUNG (append body — hover KHÔNG vẽ lại
    // trang). Thay panel inline o_vd_kh_info_panel ở mỗi dòng THI CÔNG GẤP / XLVĐ. =====
    onNameEnter(lead, ev) {
        const el = ev && ev.currentTarget;
        if (this._khHideTimer) { clearTimeout(this._khHideTimer); this._khHideTimer = null; }
        if (this._khShowTimer) clearTimeout(this._khShowTimer);
        this._khShowTimer = setTimeout(() => { this._khShowTimer = null; this._showKhInfo(lead, el); }, 90);
    }
    onNameLeave() {
        if (this._khShowTimer) { clearTimeout(this._khShowTimer); this._khShowTimer = null; }
        this._khHideTimer = setTimeout(() => { this._khHideTimer = null; this._hideKhInfo(); }, 140);
    }
    _ensureKhInfo() {
        if (this._khInfoEl && document.body.contains(this._khInfoEl)) return this._khInfoEl;
        const d = document.createElement("div");
        d.className = "o_vd_khs";
        d.style.display = "none";
        // Vào bảng → giữ mở (đọc/kéo bảng báo giá); rời bảng → ẩn.
        d.addEventListener("mouseenter", () => { if (this._khHideTimer) { clearTimeout(this._khHideTimer); this._khHideTimer = null; } });
        d.addEventListener("mouseleave", () => this._hideKhInfo());
        document.body.appendChild(d);
        this._khInfoEl = d;
        return d;
    }
    _khInfoHtml(lead) {
        const e = (s) => this._escHtml(s);
        // Chênh lệch báo giá vs tài chính → ĐƯA LÊN TIÊU ĐỀ (user 2026-08-08).
        let diffBadge = "";
        if (lead.quote_vs_budget_diff_fmt) {
            const over = lead.quote_over_budget;
            diffBadge = `<span class="o_vd_khs_hdiff ${over ? "o_vd_khs_hover" : "o_vd_khs_hunder"}">`
                + `${over ? "⚠️ VƯỢT tài chính " : "✅ CÒN DƯ "}`
                + `${over ? "+" : "−"}${e(lead.quote_vs_budget_diff_fmt)} đ</span>`;
        }
        let h = "";
        h += `<div class="o_vd_khs_head">`
            + `<span class="o_vd_khs_head_ttl">👤 ${e(lead.name)}</span>${diffBadge}</div>`;
        const bd = String(lead.quote_breakdown_html || "");
        if (bd) {
            h += `<div class="o_vd_khs_breakdown">${bd}</div>`;
        } else {
            h += `<div class="o_vd_khs_nobd">Khách chưa có bảng báo giá chi tiết.</div>`;
        }
        h += `<div class="o_vd_khs_foot">📋 Click vào tên để copy</div>`;
        return h;
    }
    _showKhInfo(lead, el) {
        if (!lead || !el || !document.body.contains(el)) return;
        const d = this._ensureKhInfo();
        d.innerHTML = this._khInfoHtml(lead);
        d.style.display = "block";
        const r = el.getBoundingClientRect();
        // Bảng scale(0.7) → kích thước THẬT (nhìn thấy) = offset × 0.7. Dùng cỡ này
        // để canh viewport cho đúng.
        const tw = d.offsetWidth * 0.7, th = d.offsetHeight * 0.7;
        const vw = window.innerWidth, vh = window.innerHeight;
        let left = r.left;
        if (left + tw > vw - 8) left = vw - 8 - tw;
        if (left < 8) left = 8;
        let top = r.bottom + 6;
        if (top + th > vh - 8) top = r.top - th - 6;   // không đủ chỗ dưới → lật lên
        d.style.left = Math.max(8, left) + "px";
        d.style.top = Math.max(8, top) + "px";
    }
    _hideKhInfo() {
        if (this._khInfoEl) this._khInfoEl.style.display = "none";
    }
    // Hover ô icon phải → sau 70ms mới dựng bảng trong ô (lazy). Rời ô → gỡ ngay.
    // Danh sách ô ĐÃ chuyển sang "ô dùng chung + hover" (không vẽ lại trang). Ô nào
    // ở đây thì hover dựng popover trực tiếp bằng DOM (nút bên trong vẫn bấm được
    // qua event-delegation). Ô KHÁC vẫn dùng OWL lazy (state.hoverTile) như cũ.
    _tileSharedKeys() { return new Set(["notcalled", "reference", "quoted_lost", "planned_sign"]); }
    onTileEnter(key, ev) {
        if (this._tileSharedKeys().has(key)) {
            const el = ev && ev.currentTarget;
            if (this._tileHideTimer) { clearTimeout(this._tileHideTimer); this._tileHideTimer = null; }
            if (this._tileShowTimer) clearTimeout(this._tileShowTimer);
            this._tileShowTimer = setTimeout(() => { this._tileShowTimer = null; this._showTilePop(key, el); }, 70);
            return;
        }
        if (this._tileHoverTimer) clearTimeout(this._tileHoverTimer);
        this._tileHoverTimer = setTimeout(() => {
            this._tileHoverTimer = null;
            if (this.state.hoverTile !== key) this.state.hoverTile = key;
        }, 70);
    }
    onTileLeave(key) {
        if (this._tileSharedKeys().has(key)) {
            if (this._tileShowTimer) { clearTimeout(this._tileShowTimer); this._tileShowTimer = null; }
            this._hideTilePopSoon();
            return;
        }
        if (this._tileHoverTimer) { clearTimeout(this._tileHoverTimer); this._tileHoverTimer = null; }
        if (this.state.hoverTile === key) this.state.hoverTile = "";
    }
    // KH HỦY mở bằng CLICK-ghim: bấm ô mở/đóng; bấm ra ngoài đóng (xử lý ở
    // _onDocClickPin gắn lúc onMounted).
    togglePinTile(key) {
        const open = this.state.pinnedTile !== key;
        this.state.pinnedTile = open ? key : "";
        if (open) {
            // Định vị popover SAU khi render (giống onTrashPopoverMove — có xử lý
            // zoom:0.7 — nhưng neo theo Ô thay vì con trỏ).
            requestAnimationFrame(() => this._positionPinnedPopover());
        }
    }
    _positionPinnedPopover() {
        const box = document.querySelector(".o_vd_tile_pinned");
        if (!box) return;
        const pop = box.querySelector(".o_vd_trash_popover");
        if (!pop) return;
        const rect = box.getBoundingClientRect();
        const z = box.offsetWidth ? (rect.width / box.offsetWidth) : 1;
        const edge = 10;
        const vw = window.innerWidth / z, vh = window.innerHeight / z;
        const pw = pop.offsetWidth || 560, ph = pop.offsetHeight || 320;
        const bx = rect.left / z, by = rect.top / z, bw = rect.width / z;
        let x = bx - pw - 10;                       // bên TRÁI ô (panel ở mép phải)
        if (x < edge) x = bx + bw + 10;             // không đủ → bên phải
        if (x + pw > vw - edge) x = Math.max(edge, vw - pw - edge);
        let y = by;
        if (y + ph > vh - edge) y = vh - ph - edge; // tràn dưới → đẩy lên
        if (y < edge) y = edge;
        pop.style.position = "fixed";
        pop.style.left = x + "px";
        pop.style.top = y + "px";
        pop.style.right = "auto";
        pop.style.bottom = "auto";
        pop.style.margin = "0";
        pop.style.transform = "none";
    }
    noop() {}
    // ===== Ô DÙNG CHUNG cho popover ô icon (hover KHÔNG vẽ lại trang) =====
    _ensureTilePop() {
        if (this._tilePopEl && document.body.contains(this._tilePopEl)) return this._tilePopEl;
        const d = document.createElement("div");
        d.className = "o_vd_tilepop";
        d.style.display = "none";
        // Giữ mở khi chuột di vào popover (để bấm nút); rời popover → ẩn.
        d.addEventListener("mouseenter", () => {
            if (this._tileHideTimer) { clearTimeout(this._tileHideTimer); this._tileHideTimer = null; }
        });
        d.addEventListener("mouseleave", () => this._hideTilePopSoon());
        // EVENT DELEGATION: nút/hàng bên trong vẫn bấm được dù popover là DOM thuần.
        d.addEventListener("click", (ev) => {
            const t = ev.target.closest("[data-act]");
            if (!t) return;
            const id = parseInt(t.getAttribute("data-id"), 10);
            const act = t.getAttribute("data-act");
            if (!id) return;
            if (act === "call") { ev.stopPropagation(); this.callLeadDirect(ev, id); }
            else if (act === "contacted") { ev.stopPropagation(); this.markContactedQuotedLost(ev, id); }
            else if (act === "open") { this._hideTilePop(); this.openLead(id); }
        });
        document.body.appendChild(d);
        this._tilePopEl = d;
        return d;
    }
    _tilePopHtml(key) {
        const e = (s) => this._escHtml(s);
        const callBtn = (ld) => ld.phone
            ? `<button class="o_vd_tilepop_btn" data-act="call" data-id="${ld.id}"><i class="fa fa-phone"></i> Gọi lại</button>` : "";
        const wrap = (title, list, rowFn) => {
            const head = `<div class="o_vd_tilepop_head">${title} (${list.length})</div>`;
            if (!list.length) return head + `<div class="o_vd_tilepop_empty">✓ Không có KH nào</div>`;
            return head + `<div class="o_vd_tilepop_body">${list.map(rowFn).join("")}</div>`;
        };
        const base = (ld, extra) => `<div class="o_vd_tilepop_row" data-act="open" data-id="${ld.id}">`
            + `<span class="o_vd_tilepop_nm">${e(ld.name)}</span>`
            + `<span class="o_vd_tilepop_ph"><i class="fa fa-phone"></i> ${e(ld.phone || "—")}</span>`
            + (extra || "") + callBtn(ld) + `</div>`;
        if (key === "notcalled") {
            return wrap("📵 CHƯA GỌI ĐƯỢC", this.leadsNotCalled || [], (ld) => {
                const cs = ld.call_stats || {};
                return base(ld, `<span class="o_vd_tilepop_st">📞 ${cs.total || 0} · 📅 ${cs.distinct_days || 0}N</span>`);
            });
        }
        if (key === "reference") {
            return wrap("👀 THAM KHẢO", this.leadsReference || [], (ld) => {
                let cb = "";
                if (ld.no_quote_callback_due) cb = `<span class="o_vd_tilepop_st" style="color:#e03131">🔥 gọi lại</span>`;
                else if (ld.no_quote_callback_days != null) cb = `<span class="o_vd_tilepop_st">⏳ ${ld.no_quote_callback_days}N</span>`;
                return base(ld, cb);
            });
        }
        if (key === "quoted_lost") {
            return wrap("📵 BÁO GIÁ XONG MẤT TÍCH", this.leadsQuotedLost || [], (ld) => {
                const d = ld.quote_days != null ? `<span class="o_vd_tilepop_st">📅 ${ld.quote_days}N</span>` : "";
                const contacted = `<button class="o_vd_tilepop_btn" style="background:#1971c2" data-act="contacted" data-id="${ld.id}"><i class="fa fa-check"></i> Đã LL</button>`;
                return `<div class="o_vd_tilepop_row" data-act="open" data-id="${ld.id}">`
                    + `<span class="o_vd_tilepop_nm">${e(ld.name)}</span>`
                    + `<span class="o_vd_tilepop_ph"><i class="fa fa-phone"></i> ${e(ld.phone || "—")}</span>`
                    + d + callBtn(ld) + contacted + `</div>`;
            });
        }
        if (key === "planned_sign") {
            return wrap("📝 KHÁCH GỬI HỢP ĐỒNG", this.leadsPlannedSign || [], (ld) => base(ld, ""));
        }
        return "";
    }
    _showTilePop(key, tileEl) {
        if (!tileEl || !document.body.contains(tileEl)) return;
        const html = this._tilePopHtml(key);
        if (!html) return;
        const d = this._ensureTilePop();
        d.innerHTML = html;
        d.style.display = "block";
        // Neo BÊN TRÁI ô (panel nằm mép phải màn hình).
        const r = tileEl.getBoundingClientRect();
        const tw = d.offsetWidth, th = d.offsetHeight;
        let left = r.left - tw - 10;
        if (left < 6) left = 6;
        let top = r.top;
        if (top + th > window.innerHeight - 6) top = window.innerHeight - 6 - th;
        d.style.left = Math.max(6, left) + "px";
        d.style.top = Math.max(6, top) + "px";
    }
    _hideTilePopSoon() {
        if (this._tileHideTimer) clearTimeout(this._tileHideTimer);
        this._tileHideTimer = setTimeout(() => this._hideTilePop(), 200);
    }
    _hideTilePop() {
        if (this._tileHideTimer) { clearTimeout(this._tileHideTimer); this._tileHideTimer = null; }
        if (this._tilePopEl) this._tilePopEl.style.display = "none";
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
        // CHẶN ÉP-LAYOUT THỪA: đọc offsetTop/scrollHeight = ép browser layout ĐỒNG
        // BỘ. Hàm này chạy trong onPatched = MỖI lần render (bấm kebab, mở KH, poll,
        // chọn KH...) dù danh sách pill KHÔNG đổi → thrash layout, làm mọi thao tác
        // "đơ". Chỉ đo lại khi số pill / mở-rộng / stage ĐỔI (chỉ đọc children.length
        // — KHÔNG ép layout).
        const sig = el.children.length + '|' +
            (this.state.newTableExpanded ? 1 : 0) + '|' +
            (this.state.selectedStageId || 0);
        if (sig === this._measSig) return;
        this._measSig = sig;
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
    toggleUrgentTable() {
        this.state.urgentExpanded = !this.state.urgentExpanded;
    }
    toggleXlvdTable() {
        this.state.xlvdExpanded = !this.state.xlvdExpanded;
    }

    // ===== BÁO GIÁ XONG MẤT TÍCH — chuyển KH thủ công (nút + kéo-thả) =====
    _leadById(leadId) {
        return [...(this.leadsUrgentConstruction || []),
                ...(this.leadsWithProblems || [])].find(l => l.id === leadId);
    }
    async _doMoveToQuotedLost(leadId) {
        try {
            await this.orm.call("crm.lead", "dashboard_move_to_quoted_lost", [leadId]);
            this.notification.add("Đã chuyển KH vào BÁO GIÁ XONG MẤT TÍCH", { type: "success" });
            await this.selectStage(this.state.selectedStageId);
        } catch (e) {
            this.notification.add("Không chuyển được KH này", { type: "danger" });
        }
    }
    // ⚙️ Menu bánh răng trên dòng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ.
    toggleRowGear(ev, leadId) {
        if (ev) { ev.stopPropagation(); }
        this.state.rowGearOpen = this.state.rowGearOpen === leadId ? 0 : leadId;
    }
    // "Huỷ khách" → mở wizard nhập lý do (đặt vd_cancel_state='proposed' chờ admin duyệt).
    async cancelLead(ev, leadId) {
        if (ev) { ev.stopPropagation(); }
        this.state.rowGearOpen = 0;
        try {
            const action = await this.orm.call("crm.lead", "action_mark_no_demand", [leadId]);
            await this.action.doAction(action, {
                onClose: () => { if (this.state.selectedStageId) this.selectStage(this.state.selectedStageId); },
            });
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Không huỷ được khách này.";
            this.notification.add(msg, { type: "danger" });
        }
    }
    // Nút trên dòng → popup XÁC NHẬN trước khi chuyển.
    confirmMoveToQuotedLost(ev, leadId) {
        if (ev) { ev.stopPropagation(); }
        this.state.rowGearOpen = 0;
        const lead = this._leadById(leadId);
        this.dialog.add(ConfirmationDialog, {
            title: "BÁO GIÁ XONG MẤT TÍCH",
            body: `Bạn đồng ý chuyển khách "${lead ? lead.name : ''}" vào bảng BÁO GIÁ XONG MẤT TÍCH?`,
            confirmLabel: "Đồng ý chuyển",
            cancelLabel: "Huỷ",
            confirm: () => this._doMoveToQuotedLost(leadId),
        });
    }
    // Nút "Đã liên lạc được" trong box → LÔI KH ra khỏi BÁO GIÁ XONG MẤT TÍCH,
    // trả về luồng 2 bảng bình thường.
    async markContactedQuotedLost(ev, leadId) {
        if (ev) { ev.stopPropagation(); }
        try {
            await this.orm.call("crm.lead", "dashboard_unmark_quoted_lost", [leadId]);
            this.notification.add("Đã lôi KH ra khỏi Báo giá xong mất tích", { type: "success" });
            await this.selectStage(this.state.selectedStageId);
        } catch (e) {
            this.notification.add("Không thao tác được", { type: "danger" });
        }
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
                await this._reloadDashUsers();
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg,
                { type: "danger", title: "Không chuyển được KH" });
        } finally {
            this.state.reassignBusy = false;
        }
    }

    // ============ MENU 3 CHẤM (kebab) — thao tác theo NGUYÊN 1 NHÂN VIÊN ========
    // Gom 3 chức năng vào 1 dropdown (không rải nút): (1) chọn 1 phát toàn bộ KH
    // của 1 NV, (2) xuất KH đã chọn ra Excel, (3) chuyển 1 phát toàn bộ KH đã chọn
    // sang 1 NV khác.
    toggleBulkMenu() {
        const open = !this.state.bulkMenu.open;
        this.state.bulkMenu = { open, sub: "", busy: false, team: "", teamChecked: {} };
    }
    closeBulkMenu() {
        if (this.state.bulkMenu.open || this.state.bulkMenu.sub) {
            this.state.bulkMenu = { open: false, sub: "", busy: false, team: "", teamChecked: {} };
        }
    }
    openBulkSub(sub) {
        // Mở bảng cấp 2/3 tương ứng ('selectUser'|'transferUser'|'teamPick'|'teamRoster').
        this.state.bulkMenu = { ...this.state.bulkMenu, sub, open: true };
    }
    // Danh sách NV để chọn trong menu — kèm tổng KH (state.users từ dashboard_users).
    get bulkMenuUsers() {
        return (this.state.users || [])
            .filter((u) => u && u.id)
            .slice()
            .sort((a, b) => (b.total || 0) - (a.total || 0));
    }
    // Bấm 1 NV trong bảng cấp 2 → điều hướng theo chức năng đang mở.
    onBulkUserPick(bu) {
        if (!bu || !bu.id) return;
        if (this.state.bulkMenu.sub === "transferUser") {
            this.bulkTransferAllTo(bu.id, bu.name);
        } else {
            this.bulkSelectAllOfUser(bu.id, bu.name);
        }
    }
    // (1) Chọn 1 phát TOÀN BỘ khách của 1 NV → nạp hết id vào vùng đã chọn.
    async bulkSelectAllOfUser(userId, userName) {
        this.state.bulkMenu = { ...this.state.bulkMenu, busy: true };
        try {
            const ids = await this.orm.call(
                "crm.lead", "dashboard_user_lead_ids", [userId]);
            const next = {};
            for (const id of (ids || [])) next[id] = true;
            this.state.selectedLeadIds = next;
            this.state.selectMode = true;
            this.notification.add(
                `Đã chọn ${ids.length} khách của "${userName}".`,
                { type: "success", title: "Chọn toàn bộ KH" });
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Không chọn được" });
        } finally {
            this.state.bulkMenu = { open: false, sub: "", busy: false, team: "", teamChecked: {} };
        }
    }
    // (2) Xuất TOÀN BỘ khách đã chọn ra Excel (.xlsx) → tải file về.
    async bulkExportExcel() {
        const ids = this.selectedLeadIdList;
        if (!ids.length) {
            this.notification.add("Chưa chọn khách hàng nào để xuất.",
                { type: "warning" });
            return;
        }
        this.state.bulkMenu = { ...this.state.bulkMenu, busy: true };
        try {
            const res = await this.orm.call(
                "crm.lead", "dashboard_export_leads_xlsx", [ids]);
            if (res && res.url) {
                const a = document.createElement("a");
                a.href = res.url;
                a.download = res.name || "khach_hang.xlsx";
                document.body.appendChild(a);
                a.click();
                a.remove();
                this.notification.add(
                    `Đã xuất ${res.count} khách ra Excel.`,
                    { type: "success", title: "Xuất Excel" });
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Không xuất được" });
        } finally {
            this.state.bulkMenu = { open: false, sub: "", busy: false, team: "", teamChecked: {} };
        }
    }
    // (3) Chuyển 1 phát TOÀN BỘ khách đã chọn sang 1 NV khác.
    async bulkTransferAllTo(userId, userName) {
        const ids = this.selectedLeadIdList;
        if (!ids.length) {
            this.notification.add("Chưa chọn khách hàng nào để chuyển.",
                { type: "warning" });
            return;
        }
        const ok = window.confirm(
            `Chuyển ${ids.length} khách hàng sang nhân viên "${userName}"?`);
        if (!ok) return;
        this.state.bulkMenu = { ...this.state.bulkMenu, busy: true };
        try {
            const moved = await this.orm.call(
                "crm.lead", "dashboard_bulk_reassign", [ids, userId]);
            this.notification.add(
                `Đã chuyển ${moved} khách hàng sang "${userName}".`,
                { type: "success", title: "Chuyển KH thành công" });
            this.state.selectedLeadIds = {};
            this.state.selectMode = false;
            await this.loadDashboard();
            if (this.state.is_manager) {
                await this._reloadDashUsers();
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Không chuyển được KH" });
        } finally {
            this.state.bulkMenu = { open: false, sub: "", busy: false, team: "", teamChecked: {} };
        }
    }

    // ===== (4) CHIA TOÀN BỘ KH ĐÃ CHỌN CHO 1 PHÒNG — chia đều cho NV được tích ==
    // Phòng = tiền tố tên NV (dùng _userTeamLabel, khớp báo cáo). Ẩn NV đang TẮT
    // nhận số (_distributeOffIds). Chia đều = round-robin qua các NV đã tích.
    get bulkMenuTeams() {
        // CHỈ NV đang BẬT nhận số — lọc theo CỜ THẬT `can_receive` (vd_can_receive
        // _pancake) do dashboard_users trả về. KHÔNG dùng _distributeOffIds (đọc báo
        // cáo Pancake HÔM NAY) vì báo cáo chỉ liệt kê NV có số hôm nay → NV đã tắt mà
        // hôm nay không có số (vd Sen/Quy) lọt lưới, vẫn hiện. Cờ user thì luôn đúng.
        const src = (this.state.users || []).filter((u) => u.id && u.can_receive);
        const m = {};
        for (const u of src) {
            const t = this._userTeamLabel(u);
            (m[t] = m[t] || []).push(u);
        }
        return Object.keys(m).sort().map((t) => ({
            team: t,
            members: m[t].slice().sort((a, b) => (b.total || 0) - (a.total || 0)),
            count: m[t].length,
        }));
    }
    get bulkCurrentTeamMembers() {
        const t = this.state.bulkMenu.team;
        const found = this.bulkMenuTeams.find((x) => x.team === t);
        return found ? found.members : [];
    }
    get bulkTeamCheckedIds() {
        const ck = this.state.bulkMenu.teamChecked || {};
        return this.bulkCurrentTeamMembers.filter((m) => ck[m.id]).map((m) => m.id);
    }
    // Chọn 1 phòng ở cấp 2 → mở cấp 3, mặc định TÍCH HẾT người trong phòng.
    openBulkTeamRoster(tm) {
        const checked = {};
        for (const m of (tm.members || [])) checked[m.id] = true;
        this.state.bulkMenu = {
            ...this.state.bulkMenu, sub: "teamRoster", team: tm.team,
            teamChecked: checked, open: true,
        };
    }
    toggleBulkTeamMember(uid) {
        const ck = { ...(this.state.bulkMenu.teamChecked || {}) };
        if (ck[uid]) delete ck[uid]; else ck[uid] = true;
        this.state.bulkMenu = { ...this.state.bulkMenu, teamChecked: ck };
    }
    bulkTeamSetAll(on) {
        const ck = {};
        if (on) for (const m of this.bulkCurrentTeamMembers) ck[m.id] = true;
        this.state.bulkMenu = { ...this.state.bulkMenu, teamChecked: ck };
    }
    async bulkDistributeToTeam() {
        const leadIds = this.selectedLeadIdList;
        const uids = this.bulkTeamCheckedIds;
        const team = this.state.bulkMenu.team;
        if (!leadIds.length) {
            this.notification.add("Chưa chọn khách hàng nào.", { type: "warning" });
            return;
        }
        if (!uids.length) {
            this.notification.add("Chưa tích người nhận nào.", { type: "warning" });
            return;
        }
        const ok = window.confirm(
            `Chia đều ${leadIds.length} khách cho ${uids.length} nhân viên phòng "${team}"?`);
        if (!ok) return;
        // Round-robin: KH thứ i -> NV uids[i % N] → chia đều tuyệt đối.
        const assignments = leadIds.map((lid, i) => [lid, uids[i % uids.length]]);
        this.state.bulkMenu = { ...this.state.bulkMenu, busy: true };
        try {
            const moved = await this.orm.call(
                "crm.lead", "dashboard_bulk_distribute", [assignments]);
            this.notification.add(
                `Đã chia ${moved} khách cho ${uids.length} nhân viên phòng "${team}".`,
                { type: "success", title: "Chia số theo phòng" });
            this.state.selectedLeadIds = {};
            this.state.selectMode = false;
            await this.loadDashboard();
            if (this.state.is_manager) {
                await this._reloadDashUsers();
            }
        } catch (e) {
            const msg = e?.data?.message || e?.message || "Lỗi không xác định.";
            this.notification.add(msg, { type: "danger", title: "Không chia được" });
        } finally {
            this.state.bulkMenu = { open: false, sub: "", busy: false, team: "", teamChecked: {} };
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
            recs = await this.orm.read("crm.lead", ids, ["name", "phone", "mobile", "call_count", "user_id"]);
        } catch (e) {
            recs = ids.map((id) => ({ id, name: "KH #" + id, phone: "" }));
        }
        this.state.distribute = {
            open: true,
            mode: "",
            busy: false,
            oneUserId: 0,
            oneTeam: "",
            lines: recs.map((r) => ({
                lead_id: r.id,
                name: r.name || ("KH #" + r.id),
                phone: r.phone || r.mobile || "",
                user_id: 0,
                // CHỦ hiện tại của KH — loại khỏi vòng nhận khi chia lại (không gán
                // ngược cho chính người đang giữ KH đó).
                owner_id: (r.user_id && r.user_id[0]) || 0,
                // KH MỚI chưa gọi (call_count=0) — chỉ dòng này ăn "sức chứa" NV.
                uncalled: (r.call_count || 0) === 0,
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
    // CHIA HẾT CHO 1 NV: chọn 1 người → tất cả KH đã chọn dồn về người đó.
    applyDistributeOne(ev) {
        const uid = parseInt(ev.target.value, 10) || 0;
        this.state.distribute.oneUserId = uid;
        this.state.distribute.oneTeam = "";
        if (!uid) {
            this.state.distribute.mode = "";
            return;
        }
        for (const ln of (this.state.distribute.lines || [])) ln.user_id = uid;
        this.state.distribute.mode = "one_user";
    }
    // PHÒNG của 1 NV = tiền tố TÊN trước " - " (khớp đúng tên hiển thị trong
    // báo cáo, vd "HCM2 - Lê Xuân Hưng" -> "HCM2"). Không dùng thẻ vd_team vì
    // thẻ này hay sai/cũ (đẻ ra nhóm rác "BÁN HÀ"/"CTV").
    _userTeamLabel(u) {
        const name = (u && u.name) || "";
        const idx = name.indexOf(" - ");
        if (idx > 0) return name.slice(0, idx).trim().toUpperCase();
        return (u && u.team) || "KHÁC";
    }
    // Roster ĐÚNG = NV đang BẬT nhận số trong báo cáo chia số (khớp đúng bảng
    // người dùng nhìn thấy). Không dùng state.users vì tập đó rộng hơn (mọi NV
    // có lead) -> đếm phòng bị phồng lên.
    // NV bị LOẠI khỏi vòng nhận khi chia lại = CHỦ hiện tại của các KH đang chia
    // (không gán ngược KH về chính người đang giữ) + chính người đang thao tác.
    // Nhờ vậy: admin lấy KH của NV A chia cho phòng thì A bị loại; NV tự chia KH
    // của mình thì chính NV đó bị loại.
    _distributeExcludeIds() {
        const s = new Set();
        for (const ln of (this.state.distribute?.lines || [])) {
            if (ln.owner_id) s.add(ln.owner_id);
        }
        if (this.state.current_user_id) s.add(this.state.current_user_id);
        return s;
    }
    _reportRoster() {
        const rep = this.state.pancake_report;
        const rows = (rep && rep.today && rep.today.rows) || [];
        const excl = this._distributeExcludeIds();
        return rows.filter((r) => r.can_receive && !excl.has(r.uid));
    }
    // uid các NV đang TẮT nhận số (can_receive=false) trong báo cáo chia số.
    // TẮT nhận số auto -> ẩn khỏi MỌI ô chọn khi chia (yêu cầu user 2026-07-25).
    _distributeOffIds() {
        const rep = this.state.pancake_report;
        const rows = (rep && rep.today && rep.today.rows) || [];
        const s = new Set();
        for (const r of rows) { if (!r.can_receive) s.add(r.uid); }
        return s;
    }
    // NV được phép hiện trong các ô chọn chia (đã bỏ NV đang TẮT nhận số).
    get distributeEligibleUsers() {
        const off = this._distributeOffIds();
        return (this.state.users || []).filter((u) => u.id && !off.has(u.id));
    }
    // Danh sách PHÒNG (team) + số NV mỗi phòng, để chia đều trong 1 phòng.
    get distributeTeams() {
        const excl = this._distributeExcludeIds();
        const roster = this._reportRoster();
        const src = roster.length
            ? roster.map((r) => ({ id: r.uid, name: r.name }))
            : (this.state.users || []).filter((u) => u.id && !excl.has(u.id));
        const m = {};
        for (const u of src) {
            if (!u.id) continue;
            const t = this._userTeamLabel(u);
            m[t] = (m[t] || 0) + 1;
        }
        return Object.keys(m).sort().map((t) => ({ team: t, count: m[t] }));
    }
    // CHIA ĐỀU trong 1 PHÒNG: chỉ vòng chia cho NV thuộc phòng được chọn.
    applyDistributeTeam(ev) {
        const team = ev.target.value || "";
        this.state.distribute.oneTeam = team;
        this.state.distribute.oneUserId = 0;
        if (!team) {
            this.state.distribute.mode = "";
            return;
        }
        const roster = this._reportRoster();
        let users;
        if (roster.length) {
            // Lấy đúng NV đang bật nhận thuộc phòng; ghép dữ liệu tải từ state.users.
            const byId = {};
            for (const u of (this.state.users || [])) byId[u.id] = u;
            users = roster
                .filter((r) => this._userTeamLabel(r) === team)
                .map((r) => byId[r.uid] || { id: r.uid, name: r.name, new_total: 0, new_not_called: 0 });
        } else {
            const excl = this._distributeExcludeIds();
            const off = this._distributeOffIds();
            users = (this.state.users || []).filter(
                (u) => u.id && !excl.has(u.id) && !off.has(u.id)
                    && this._userTeamLabel(u) === team);
        }
        if (!users.length) {
            this.notification.add(
                "Phòng này không có NV khác đang bật nhận số để chia.", { type: "warning" });
            return;
        }
        this._distributeEvenAmong(users);
        this.state.distribute.mode = "team";
    }
    distributeUserLoad(userId) {
        const u = (this.state.users || []).find((x) => x.id === userId);
        if (!u) return "";
        return `📋 ${u.new_total || 0} mới · 📵 ${u.new_not_called || 0} chưa gọi`;
    }
    // ===== CHẶN CHIA SỐ — sức chứa NV theo KH mới chưa gọi (user spec 2026-06-12) =====
    get distributeThreshold() {
        return this.state.distribute_block_threshold || 0;
    }
    _userUncalled(userId) {
        const u = (this.state.users || []).find((x) => x.id === userId);
        return u ? (u.new_not_called || 0) : 0;
    }
    // {userId: số dòng CHƯA GỌI đang gán cho NV đó trong popup}
    get distributeAssignedUncalled() {
        const m = {};
        for (const ln of (this.state.distribute?.lines || [])) {
            if (ln.user_id && ln.uncalled) m[ln.user_id] = (m[ln.user_id] || 0) + 1;
        }
        return m;
    }
    // {userId: {current, cap}} cho NV bị VƯỢT sức chứa
    get distributeOverUsers() {
        const th = this.distributeThreshold;
        if (!th) return {};
        const assigned = this.distributeAssignedUncalled;
        const over = {};
        for (const k of Object.keys(assigned)) {
            const id = parseInt(k, 10);
            const cur = this._userUncalled(id);
            if (cur + assigned[k] > th) over[id] = { current: cur, cap: Math.max(0, th - cur) };
        }
        return over;
    }
    isDistributeLineOver(ln) {
        return !!(ln && ln.user_id && this.distributeOverUsers[ln.user_id]);
    }
    get distributeHasOver() {
        return Object.keys(this.distributeOverUsers).length > 0;
    }
    // Nhãn sức chứa cho dropdown NV
    distributeCapLabel(userId) {
        const th = this.distributeThreshold;
        if (!th) return "";
        const cur = this._userUncalled(userId);
        return ` — còn ${Math.max(0, th - cur)}/${th}`;
    }
    // Vòng chia ĐỀU danh sách KH cho tập NV truyền vào (round-robin theo tải,
    // tôn trọng sức chứa của dòng CHƯA gọi). Dùng cho "đều TẤT CẢ NV" và "đều 1 phòng".
    _distributeEvenAmong(users) {
        const lines = this.state.distribute.lines || [];
        if (!users.length) return;
        const th = this.distributeThreshold;
        const remain = {};
        users.forEach((u) => {
            remain[u.id] = th > 0 ? Math.max(0, th - (u.new_not_called || 0)) : Infinity;
        });
        const load = {};
        users.forEach((u) => { load[u.id] = u.new_total || 0; });
        const order = [...users].sort((a, b) => load[a.id] - load[b.id]);
        let i = 0;
        for (const ln of lines) {
            // dòng CHƯA gọi: bỏ qua NV hết chỗ; dòng đã gọi: gán bình thường
            if (ln.uncalled && th > 0) {
                let guard = 0;
                while (remain[order[i % order.length].id] <= 0 && guard < order.length) { i++; guard++; }
            }
            const u = order[i % order.length];
            ln.user_id = u.id;
            if (ln.uncalled && th > 0 && remain[u.id] > 0) remain[u.id] -= 1;
            i++;
        }
    }
    applyDistributeMode(mode) {
        const lines = this.state.distribute.lines || [];
        const users = this.distributeEligibleUsers;  // đã bỏ NV tắt nhận số
        if (!users.length) {
            this.notification.add("Không có nhân viên đang bật nhận số để chia.", { type: "warning" });
            return;
        }
        this.state.distribute.mode = mode;
        this.state.distribute.oneUserId = 0;  // rời chế độ "1 NV"
        this.state.distribute.oneTeam = "";   // rời chế độ "1 phòng"
        if (mode === "per_line") return;  // để NV tự chọn từng dòng
        const th = this.distributeThreshold;
        // sức chứa còn lại (theo KH mới chưa gọi); tắt → vô hạn
        const remain = {};
        users.forEach((u) => {
            remain[u.id] = th > 0 ? Math.max(0, th - (u.new_not_called || 0)) : Infinity;
        });
        const load = {};
        users.forEach((u) => { load[u.id] = u.new_total || 0; });
        const order = [...users].sort((a, b) => load[a.id] - load[b.id]);
        if (mode === "even_all") {
            this._distributeEvenAmong(users);
        } else if (mode === "least") {
            for (const ln of lines) {
                let avail = users;
                if (ln.uncalled && th > 0) {
                    const withCap = users.filter((u) => remain[u.id] > 0);
                    if (withCap.length) avail = withCap;   // hết chỗ hẳn → vẫn gán (đỏ)
                }
                let best = avail[0].id, bestv = load[avail[0].id];
                for (const u of avail) { if (load[u.id] < bestv) { best = u.id; bestv = load[u.id]; } }
                ln.user_id = best;
                load[best] += 1;
                if (ln.uncalled && th > 0 && remain[best] > 0) remain[best] -= 1;
            }
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
        // CHẶN CHIA SỐ (user spec 2026-06-12): có NV vượt ngưỡng → bắt chọn NV khác.
        if (this.distributeHasOver) {
            const names = Object.keys(this.distributeOverUsers).map((id) => {
                const u = (this.state.users || []).find((x) => x.id === parseInt(id, 10));
                const o = this.distributeOverUsers[id];
                return `• ${u ? u.name : "NV"} — đang tồn ${o.current}, chỉ nhận thêm ${o.cap} (ngưỡng ${this.distributeThreshold})`;
            }).join("\n");
            this.notification.add(
                "🚫 Vượt ngưỡng khách mới chưa gọi — hãy CHỌN NV KHÁC cho các dòng ĐỎ:\n" + names,
                { type: "danger", title: "Không chia được — NV đã đầy" },
            );
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
        // Admin có thể MIỄN khoá riêng 1 NV (vd_quote_chot_lock_exempt).
        return !!(this.state.selected_user_id
            && !this.state.quote_chot_lock_exempt
            && this.quoteUnchotLeads.length > 3);
    }
    // Chỉ các KH báo giá chưa chốt mới được phép mở khi đang khoá.
    get quoteChotAllowedIds() {
        return new Set(this.quoteUnchotLeads.map(l => l.id));
    }
    // ===== KHOÁ "KẾT BẠN ZALO" (user spec 2026-06-09) =====
    // > 10 KH CHƯA KẾT BẠN ZALO (must_zalo = đã gọi nhiều lần không nghe) → khoá
    // cả bảng KHÁCH MỚI, CHỈ cho mở các KH chưa kết bạn để ép NV kết bạn + tư vấn
    // Zalo. Khi còn ≤ 10 thì tự gỡ. Chỉ khi xem 1 NV cụ thể.
    get zaloUnfriendedLeads() {
        return (this.leadsNoProblems || []).filter(l => l.must_zalo);
    }
    get zaloFriendLockActive() {
        // Công tắc cấu hình (user spec 2026-06-10): khoá cứng "chưa nhắn Zalo"
        // hay gây phản tác dụng (backlog lớn → khoá sạch) → mặc định TẮT, giữ pill
        // đỏ hướng dẫn thôi. Bật lại qua System Parameter zalo_lock_enabled=1.
        return !!(this.state.zalo_lock_enabled
            && this.state.selected_user_id
            && this.zaloUnfriendedLeads.length > 10);
    }
    get zaloFriendAllowedIds() {
        return new Set(this.zaloUnfriendedLeads.map(l => l.id));
    }
    // Set id các KH thuộc BẢNG KHÁCH MỚI (để khoá chỉ áp đúng bảng này).
    get _newTableLeadIds() {
        return new Set((this.leadsNoProblems || []).map(l => l.id));
    }
    // KH bị NHẮC (chưa gọi đủ) — vẫn được mở khi khoá "chưa gọi đủ" để NV gọi.
    get callWatchAllowedIds() {
        return new Set(this.state.call_watch?.allowed_ids || []);
    }
    // KH CẦN GỌI hôm nay (chưa gọi đủ) — để TÔ SÁNG việc cần làm (user spec
    // 2026-06-11). Tập này CO LẠI khi NV gọi → gọi xong là tắt tô sáng (KHÔNG
    // khoá khách đó). Gọi hết là khoá tự gỡ.
    get callWatchUncalledIds() {
        return new Set((this.state.call_watch?.uncalled_leads || []).map((l) => l.id));
    }
    isLeadToCall(leadId) {
        return !!(this.state.call_watch?.enabled
            && this.callWatchUncalledIds.has(leadId));
    }
    // True nếu lead đang bị khoá mở (làm mờ pill + chặn click). CẢ 3 khoá Khách
    // mới CHỈ áp cho lead THUỘC bảng Khách mới — KHÔNG lan sang Thi công gấp /
    // Xử lý vấn đề (user spec 2026-06-10). Mỗi khoá chừa loại KH cần xử lý:
    //   - chưa gọi đủ → chừa KH bị nhắc (gọi để gỡ)
    //   - chốt báo giá → chừa KH đã báo giá (chốt để gỡ)
    //   - nhắn Zalo → chừa KH chưa nhắn (nhắn để gỡ)
    isLeadLocked(leadId) {
        if (!this._newTableLeadIds.has(leadId)) return false;
        // User spec 2026-06-12: BỎ khoá "chưa gọi đủ" — 3 vùng + badge ⏰ đã thay
        // vai trò nhắc, không làm mờ/chặn nữa. CHỈ giữ khoá chốt báo giá (+ Zalo).
        if (this.quoteChotLockActive && !this.quoteChotAllowedIds.has(leadId)) return true;
        if (this.zaloFriendLockActive && !this.zaloFriendAllowedIds.has(leadId)) return true;
        return false;
    }
    dismissQuoteGuide() {
        this.state.quoteGuideDismissed = true;
    }

    // KHOÁ TOÀN BỘ (user spec 2026-06-12): NV tồn > ngưỡng KH mới CHƯA GỌI →
    // khoá MỌI bảng, chỉ cho mở chính các KH mới chưa gọi (vùng CHƯA GỌI) để ép
    // gọi. Admin xem NV đó cũng thấy khoá. Gọi cho ≤ ngưỡng → tự mở.
    get uncalledNewLockActive() {
        const u = this.state.uncalled_new_lock;
        return !!(u && u.locked && this.state.selected_user_id);
    }
    // KH "mới chưa gọi" = đang ở bảng KHÁCH MỚI và chưa có cuộc gọi nào (total=0).
    _isUncalledNewLead(leadId) {
        if (this.selectedStage?.code !== "new") return false;
        const lead = (this.state.leads || []).find((l) => l.id === leadId);
        return !!lead && (((lead.call_stats || {}).total || 0) === 0);
    }

    openLead(leadId) {
        // KHOÁ TOÀN BỘ — chặn mở MỌI KH trừ KH mới chưa gọi (vùng CHƯA GỌI).
        // FIX (user spec 2026-07-15): khi KHOÁ TOÀN BỘ + KHOÁ CHỐT BÁO GIÁ cùng
        // bật, 4 KH 💰 chưa chốt (ĐÃ gọi rồi nên KHÔNG thuộc vùng CHƯA GỌI) bị
        // KHOÁ TOÀN BỘ chặn → NV không vào chốt được để gỡ khoá kia = DEADLOCK.
        // Cho KHOÁ TOÀN BỘ chừa LỐI THOÁT của khoá khác: vẫn mở KH cần CHỐT báo
        // giá / cần NHẮN Zalo (các KH này không tính vào số "chưa gọi" nên không
        // phá mục đích khoá).
        const isOtherLockEscape =
            (this.quoteChotLockActive && this.quoteChotAllowedIds.has(leadId))
            || (this.zaloFriendLockActive && this.zaloFriendAllowedIds.has(leadId));
        if (this.uncalledNewLockActive && !this._isUncalledNewLead(leadId)
                && !isOtherLockEscape) {
            const u = this.state.uncalled_new_lock;
            this.notification.add(
                "🔒 KHOÁ TOÀN BỘ: còn " + (u.count || 0) + " khách MỚI CHƯA GỌI "
                + "(cần ≤ " + (u.threshold || 0) + "). Vào bảng KHÁCH MỚI → mở các "
                + "khách ở vùng CHƯA GỌI và GỌI cho đủ — gọi bớt xuống là TỰ MỞ.",
                { type: "warning", title: "Khoá toàn bộ — khách mới chưa gọi quá nhiều" },
            );
            return;
        }
        // KHOÁ "KẾT BẠN ZALO" (user spec 2026-06-09): > 10 KH chưa kết bạn Zalo
        // → chỉ cho mở các KH CHƯA KẾT BẠN (viền đỏ) để ép NV kết bạn + tư vấn Zalo.
        // CHỈ áp cho lead thuộc bảng Khách mới (user spec 2026-06-10).
        if (this.zaloFriendLockActive && this._newTableLeadIds.has(leadId)
                && !this.zaloFriendAllowedIds.has(leadId)) {
            this.notification.add(
                "🔒 Bạn có HƠN 10 khách CHƯA NHẮN ZALO. Hãy mở từng khách VIỀN ĐỎ "
                + "→ NHẮN tin Zalo (kết bạn khi khách trả lời). Khi còn ≤ 10 khách "
                + "chưa nhắn, các khách khác sẽ mở lại bình thường.",
                { type: "warning", title: "Khoá — chưa NHẮN ZALO" },
            );
            return;
        }
        // KHOÁ "CHỐT BÁO GIÁ" (user spec 2026-06-03): > 3 KH báo giá chưa CHỐT
        // → chỉ cho mở các KH báo giá (để vào CHỐT), khoá mở mọi KH khác.
        // CHỈ áp cho lead thuộc bảng Khách mới (user spec 2026-06-10).
        if (this.quoteChotLockActive && this._newTableLeadIds.has(leadId)
                && !this.quoteChotAllowedIds.has(leadId)) {
            this.notification.add(
                "🔒 Bạn có hơn 3 khách đã BÁO GIÁ nhưng CHƯA CHỐT. Hãy mở từng "
                + "khách MÀU XANH LÁ (💰) → vào THÔNG TIN TƯ VẤN → bấm "
                + "🔒 CHỐT BÁO GIÁ. Khi còn ≤ 3 khách chưa chốt, các khách khác "
                + "sẽ mở lại bình thường.",
                { type: "warning", title: "Khoá — chưa CHỐT báo giá" },
            );
            return;
        }
        // KHOÁ "CHƯA GỌI ĐỦ" đã BỎ (user spec 2026-06-12) — không chặn mở KH nữa;
        // 3 vùng + badge ⏰ thay vai trò nhắc. Khoá theo bảng còn lại: TCG/XLVĐ.
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

    // Popover 3 nút (Tham khảo / Chưa gọi được / Hủy) BÁM theo con trỏ chuột
    // (user spec 2026-06-12) — position:fixed theo clientX/Y, kẹp trong màn hình
    // để KHÔNG bị che mép. Khi chuột vào trong popover thì NGỪNG bám để bấm được.
    onTrashPopoverMove(ev) {
        const box = ev.currentTarget;
        const pop = box.querySelector(".o_vd_trash_popover");
        if (!pop) return;
        if (pop.contains(ev.target)) return;   // đang rê trong popover → giữ yên
        // FIX (user spec 2026-06-12): dashboard có zoom:0.7 → position:fixed nằm
        // trong hệ toạ độ ĐÃ ZOOM, còn clientX/Y là toạ độ THẬT của màn hình →
        // popover lệch. Quy đổi: chia cho hệ số zoom (= rect.width / offsetWidth).
        const rect = box.getBoundingClientRect();
        const z = box.offsetWidth ? (rect.width / box.offsetWidth) : 1;
        const pad = 14, edge = 10;
        const cx = ev.clientX / z, cy = ev.clientY / z;          // con trỏ (hệ zoom)
        const vw = window.innerWidth / z, vh = window.innerHeight / z;
        const pw = pop.offsetWidth || 520;
        const ph = pop.offsetHeight || 300;
        let x = cx + pad;
        let y = cy + pad;
        if (x + pw > vw - edge) x = cx - pw - pad;            // lật trái nếu tràn phải
        if (x < edge) x = edge;
        if (y + ph > vh - edge) y = vh - ph - edge;          // đẩy lên nếu tràn dưới
        if (y < edge) y = edge;
        pop.style.position = "fixed";
        pop.style.left = x + "px";
        pop.style.top = y + "px";
        pop.style.right = "auto";
        pop.style.bottom = "auto";
        pop.style.margin = "0";
        pop.style.transform = "none";
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
            page: 1,
            total: 0,
            pageSize: 100,
        };
        try {
            const data = await this.orm.call("res.users", "vd_recent_recordings", [nv.user_id]);
            if (this.state.recHover && this.state.recHover.user_id === nv.user_id) {
                this.state.recHover.recordings = (data && data.recordings) || [];
                this.state.recHover.stats = (data && data.stats) || {};
                this.state.recHover.total = (data && data.total) || 0;
                this.state.recHover.pageSize = (data && data.page_size) || 100;
                this.state.recHover.loading = false;
            }
        } catch (e) {
            if (this.state.recHover && this.state.recHover.user_id === nv.user_id) {
                this.state.recHover.loading = false;
            }
        }
    }
    // Gom ghi âm theo NGÀY (đã sort desc từ backend) → header đậm mỗi ngày +
    // đếm số cuộc trong ngày (user spec 2026-07-08).
    get recGroups() {
        const recs = (this.state.recHover && this.state.recHover.recordings) || [];
        const groups = [];
        let cur = null;
        for (const r of recs) {
            const key = r.day_key || '';
            if (!cur || cur.key !== key) {
                cur = { key, days_ago: r.days_ago || 0, dm: r.day_dm || '', recs: [] };
                groups.push(cur);
            }
            cur.recs.push(r);
        }
        return groups;
    }
    recDayLabel(daysAgo) {
        const d = daysAgo || 0;
        if (d <= 0) return 'HÔM NAY';
        if (d === 1) return 'HÔM QUA';
        if (d === 2) return 'HÔM KIA';
        return d + ' NGÀY TRƯỚC';
    }
    // Phân trang ghi âm (mỗi trang 100). Giữ popover mở khi đổi trang.
    async goRecPage(page) {
        const h = this.state.recHover;
        if (!h || h.loading) return;
        const totalPages = Math.max(1, Math.ceil((h.total || 0) / (h.pageSize || 100)));
        if (page < 1 || page > totalPages || page === h.page) return;
        h.loading = true;
        const uid = h.user_id;
        try {
            const data = await this.orm.call("res.users", "vd_recent_recordings",
                [uid, h.pageSize || 100, 180, (page - 1) * (h.pageSize || 100)]);
            if (this.state.recHover && this.state.recHover.user_id === uid) {
                this.state.recHover.recordings = (data && data.recordings) || [];
                this.state.recHover.total = (data && data.total) || 0;
                this.state.recHover.page = page;
                this.state.recHover.loading = false;
            }
        } catch (e) {
            if (this.state.recHover && this.state.recHover.user_id === uid) {
                this.state.recHover.loading = false;
            }
        }
    }
    get recTotalPages() {
        const h = this.state.recHover;
        if (!h) return 1;
        return Math.max(1, Math.ceil((h.total || 0) / (h.pageSize || 100)));
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
    // Đóng NGAY popover ghi âm (bấm ra ngoài / mở khách / cuộn).
    _closeRecNow() {
        if (this._recTimer) {
            clearTimeout(this._recTimer);
            this._recTimer = null;
        }
        this.state.recHover = null;
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

    // ===== 🗑️ THÙNG RÁC KH HỦY CHỜ DUYỆT (hover thùng rác dòng NV) =====
    // Dữ liệu đã có sẵn trong nv.cancel_leads → không cần RPC. Render ở gốc +
    // _popAtRect tự lật LÊN khi NV ở cuối bảng → không bị che.
    onCancelEnter(ev, nv) {
        if (this._cancelTimer) { clearTimeout(this._cancelTimer); this._cancelTimer = null; }
        if (this.state.cancelHover && this.state.cancelHover.user_id === nv.user_id) {
            return;
        }
        this.state.cancelHover = {
            user_id: nv.user_id,
            name: nv.full_name,
            leads: nv.cancel_leads || [],
            report: nv.newcancel_report || null,
            rect: this._elRect(ev),
        };
    }
    onCancelLeave() {
        if (this._cancelTimer) { clearTimeout(this._cancelTimer); }
        this._cancelTimer = setTimeout(() => {
            this.state.cancelHover = null;
            this._cancelTimer = null;
        }, 320);
    }
    onCancelPopEnter() {
        if (this._cancelTimer) { clearTimeout(this._cancelTimer); this._cancelTimer = null; }
    }
    get cancelPopStyle() {
        const h = this.state.cancelHover;
        if (!h) return "display:none;";
        return this._popAtRect(h.rect, 1280);
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

    // ===== GHI ÂM THAM KHẢO (hover filter to nhấp nháy) — bảng ghi âm >5'
    // của 3 NV mẫu cho toàn công ty tham khảo. =====
    async onRefRecEnter(ev) {
        if (this._refRecTimer) {
            clearTimeout(this._refRecTimer);
            this._refRecTimer = null;
        }
        // Đã mở rồi → giữ nguyên (tránh nạp lại + nhảy).
        if (this.state.refRecHover) {
            return;
        }
        // Đã nạp sẵn → hiện NGAY, không loading.
        if (this.state.refRecData) {
            this.state.refRecHover = {
                rect: this._elRect(ev),
                loading: false,
                people: this.state.refRecData.people,
                min_minutes: this.state.refRecData.min_minutes,
            };
            return;
        }
        // Chưa kịp nạp xong (hover quá sớm) → hiện spinner rồi nạp.
        this.state.refRecHover = {
            rect: this._elRect(ev),
            loading: true,
            people: [],
            min_minutes: 5,
        };
        try {
            const data = await this.orm.call("crm.lead", "vd_reference_recordings", []);
            this.state.refRecData = {
                people: (data && data.people) || [],
                min_minutes: (data && data.min_minutes) || 5,
            };
            if (this.state.refRecHover) {
                this.state.refRecHover.people = this.state.refRecData.people;
                this.state.refRecHover.min_minutes = this.state.refRecData.min_minutes;
                this.state.refRecHover.loading = false;
            }
        } catch (e) {
            if (this.state.refRecHover) {
                this.state.refRecHover.loading = false;
            }
        }
    }
    onRefRecLeave() {
        if (this._refRecTimer) {
            clearTimeout(this._refRecTimer);
        }
        this._refRecTimer = setTimeout(() => {
            this.state.refRecHover = null;
            this._refRecTimer = null;
        }, 320);
    }
    // GHI ÂM THAM KHẢO mở bằng CLICK (bảng to): bấm mở/đóng; bấm ra ngoài đóng
    // (xử lý ở _onDocClickPin).
    toggleRefRec(ev) {
        if (this.state.refRecHover) { this.state.refRecHover = null; return; }
        this.onRefRecEnter(ev);
    }
    onRefRecPopEnter() {
        if (this._refRecTimer) {
            clearTimeout(this._refRecTimer);
            this._refRecTimer = null;
        }
    }
    get refRecPopStyle() {
        const h = this.state.refRecHover;
        if (!h) {
            return "display:none;";
        }
        return this._popAtRect(h.rect, 560);
    }

    get recPopStyle() {
        const h = this.state.recHover;
        if (!h) {
            return "display:none;";
        }
        return this._popAtRect(h.rect, 720);
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
            // User spec 2026-06-21: KHÔNG reload trang. Đổi TẠI CHỖ button -> chip
            // "✓ Đã duyệt" (cancel_state='approved'). KH chỉ biến mất (vào thùng
            // rác công ty) khi user F5/tải lại trang.
            this._markCancelState(leadId, "approved");
        } catch (e) {
            console.error("[dashboard] approveCancel failed:", e);
            this.notification.add("Không duyệt được. " + (e.message || ""), {
                type: "danger",
            });
        }
    }

    // ===== CHỌN NHIỀU + DUYỆT HÀNG LOẠT KH hủy (admin/trưởng phòng) =====
    isPendingCancel(ld) {
        return !!ld && ld.cancel_state !== 'approved' && ld.cancel_state !== 'rejected';
    }
    _pendingCancel(leads) {
        return (leads || []).filter((l) => this.isPendingCancel(l));
    }
    // Hiện cột tick + thanh duyệt hàng loạt: có quyền duyệt + còn KH chờ duyệt.
    showCancelBulk(leads) {
        return (this.state.is_manager || this.state.is_team_leader)
            && this._pendingCancel(leads).length > 0;
    }
    isCancelSel(id) { return !!this.state.cancelSel[id]; }
    toggleCancelSel(id) {
        if (this.state.cancelSel[id]) delete this.state.cancelSel[id];
        else this.state.cancelSel[id] = true;
    }
    cancelSelCount(leads) {
        return this._pendingCancel(leads).filter((l) => this.state.cancelSel[l.id]).length;
    }
    allCancelSelected(leads) {
        const p = this._pendingCancel(leads);
        return p.length > 0 && p.every((l) => this.state.cancelSel[l.id]);
    }
    toggleCancelSelectAll(leads) {
        const p = this._pendingCancel(leads);
        if (this.allCancelSelected(leads)) {
            for (const l of p) delete this.state.cancelSel[l.id];
        } else {
            for (const l of p) this.state.cancelSel[l.id] = true;
        }
    }
    // Duyệt hủy TẤT CẢ KH đã chọn trong 1 lần gọi (server lặp for rec in self).
    async approveSelectedCancel(leads) {
        const ids = this._pendingCancel(leads)
            .filter((l) => this.state.cancelSel[l.id]).map((l) => l.id);
        if (!ids.length) return;
        if (!window.confirm(`Duyệt hủy ${ids.length} khách đã chọn?`)) return;
        try {
            await this.orm.call("crm.lead", "action_approve_cancel", [ids]);
            this.notification.add(`✓ Đã duyệt hủy ${ids.length} KH.`, { type: "success" });
            for (const id of ids) {
                this._markCancelState(id, "approved");
                delete this.state.cancelSel[id];
            }
        } catch (e) {
            console.error("[dashboard] approveSelectedCancel failed:", e);
            this.notification.add("Không duyệt được. " + (e.message || ""), { type: "danger" });
        }
    }

    // Duyệt hủy TẤT CẢ KH đang chờ trong danh sách (không cần tick từng cái).
    async approveAllCancel(leads) {
        const ids = this._pendingCancel(leads).map((l) => l.id);
        if (!ids.length) return;
        if (!window.confirm(`Duyệt hủy TẤT CẢ ${ids.length} khách đang chờ?`)) return;
        try {
            await this.orm.call("crm.lead", "action_approve_cancel", [ids]);
            this.notification.add(`✓ Đã duyệt hủy ${ids.length} KH.`, { type: "success" });
            for (const id of ids) {
                this._markCancelState(id, "approved");
                delete this.state.cancelSel[id];
            }
        } catch (e) {
            console.error("[dashboard] approveAllCancel failed:", e);
            this.notification.add("Không duyệt được. " + (e.message || ""), { type: "danger" });
        }
    }

    /**
     * TỪ CHỐI hủy 1 KH → trả về pipeline. KHÔNG reload: đổi tại chỗ sang chip
     * "↩ Đã trả về". KH biến mất khỏi danh sách khi F5.
     */
    async rejectCancel(ev, leadId) {
        try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {}
        try {
            await this.orm.call("crm.lead", "action_reject_cancel", [[leadId]]);
            this.notification.add("↩️ Đã từ chối hủy — KH trả về Khách mới.", { type: "success" });
            this._markCancelState(leadId, "rejected");
        } catch (e) {
            console.error("[dashboard] rejectCancel failed:", e);
            this.notification.add("Không từ chối được. " + (e.message || ""), { type: "danger" });
        }
    }

    /**
     * Đánh dấu 1 KH đã duyệt hủy TẠI CHỖ (không reload) ở mọi nơi đang giữ ref:
     * popover thùng rác (cancelHover), bảng KH hủy màn NV (leadsLostAll), và
     * nv.cancel_leads trong bảng analytics → button đổi sang chip "✓ Đã duyệt".
     */
    _markCancelState(leadId, newState) {
        const mark = (arr) => {
            if (!arr) return;
            for (const l of arr) {
                if (l && l.id === leadId) l.cancel_state = newState;
            }
        };
        if (this.state.cancelHover) mark(this.state.cancelHover.leads);
        mark(this.state.leadsLostAll);
        const groups = (this.state.analytics && this.state.analytics.kh_by_team) || [];
        for (const g of groups) {
            for (const nv of (g.nvs || [])) mark(nv.cancel_leads);
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
            // vd_dashboard_zalo_friend: kết bạn (Ngày 1) + trả tiến độ hạn mức/ngày
            // (đã chặn nếu vượt hạn mức → ném UserError, bắt ở catch bên dưới).
            const r = await this.orm.call(
                "crm.lead", "vd_dashboard_zalo_friend", [[leadId]],
            );
            const done = (r && r.done) || 0;
            const cap = (r && r.cap) || 0;
            const warn = (r && r.warn) || 0;
            const near = warn && done >= warn;
            this.notification.add(
                `Đã kết bạn Zalo (${done}/${cap} hôm nay).`
                + (near
                    ? ` ⚠️ Gần hạn mức — còn ${Math.max(cap - done, 0)} lượt. Đừng `
                      + `kết bạn dồn dập kẻo Zalo KHOÁ tài khoản; nhắn/gọi tiếp các `
                      + `khách đã kết bạn.`
                    : ""),
                { type: near ? "warning" : "success" },
            );
            await this.loadDashboard();
        } catch (e) {
            console.error("[dashboard] confirmZaloFriend failed:", e);
            const msg = (e && e.data && e.data.message) || e.message
                || "Không xác nhận được kết bạn Zalo.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    // Lưu form intake (nếu dirty) TRƯỚC khi đóng / chuyển KH. Cần vì chip/picker nay
    // KHÔNG save() tức thì (lưu-ngầm debounce) → phải flush + save 1 lần khi rời để
    // không mất thao tác cuối. Flush ô số đang gõ trước để không nuốt số in-flight.
    async _saveIntakeBeforeLeave() {
        let rec = null;
        try { rec = window.__vdGetIntakeRecord && window.__vdGetIntakeRecord(); } catch (_e) {}
        if (!rec) return;
        let dirty = true;
        try {
            if (typeof rec.isDirty === "boolean") dirty = rec.isDirty;
            else if (typeof rec.dirty === "boolean") dirty = rec.dirty;
        } catch (_e) {}
        if (!dirty) return;
        // Lưu KHÔNG RELOAD (form sắp bị gỡ, reload chỉ tổ chậm + nuốt thao tác cuối).
        try {
            if (window.__vdSaveIntakeNow) {
                await window.__vdSaveIntakeNow(rec, "leave-preview");
                return;
            }
        } catch (_e) {}
        try { if (window.__vdFlushIntakeInputs) await window.__vdFlushIntakeInputs("leave-preview"); } catch (_e) {}
        try { await rec.save({ reload: false }); } catch (_e) {}
    }

    async closePreview() {
        // Lưu thao tác intake cuối cùng trước khi gỡ form nhúng (nếu không sẽ mất).
        await this._saveIntakeBeforeLeave();
        // ĐÓNG NGAY → về dashboard tức thì (user spec 2026-08-15: đóng popup KHÔNG
        // được "load trang"). KHÔNG gọi loadDashboard() nặng nữa. Chỉ khi CÓ lưu
        // trong lúc popup mở (chốt/huỷ báo giá... → _vdNeedRefreshAfterPreview) mới
        // refresh NHẸ ĐÚNG 1 stage (selectStage) để pill cập nhật màu — chạy nền,
        // dashboard đã hiện lại ngay từ cache nên không thấy "load".
        this.state.previewLead = { ...this.state.previewLead, open: false };
        this._unlockScroll();
        if (this._vdNeedRefreshAfterPreview) {
            this._vdNeedRefreshAfterPreview = false;
            this.refreshAfterPreview();
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
        this._setupPreviewAutoFit();
    }
    _unlockScroll() {
        document.body.classList.remove('o_vd_preview_active');
        document.documentElement.style.overflow = '';
        document.body.style.overflow = '';
        this._teardownPreviewAutoFit();
    }

    // ===== AUTO-FIT popup: tự SCALE nội dung để VỪA KHÍT chiều cao viewport ở MỌI
    // mức zoom trình duyệt (mặc định 100%) → KHÔNG phải cuộn, KHÔNG cắt. Thêm/bớt
    // trường (tầng, công năng...) → tự tính lại. User spec 2026-08-15. =====
    _fitPreviewToViewport() {
        const modal = document.querySelector('.o_vd_preview_modal');
        if (!modal) return;
        const body = modal.querySelector('.o_vd_preview_body_form');
        const inner = body && body.firstElementChild;
        if (!inner) return;
        // Ngừng observe trong lúc thao tác zoom → thao tác của chính fit KHÔNG tự
        // kích hoạt ResizeObserver (chống vòng lặp).
        if (this._previewFitRO) { try { this._previewFitRO.disconnect(); } catch (_e) {} }
        // Đo TRỰC TIẾP: chiều cao khả dụng của body (cố định vì modal height cố định)
        // và chiều cao THẬT của nội dung (bỏ zoom trước khi đo → buộc reflow).
        inner.style.zoom = '';
        const availH = body.clientHeight - 6;   // trừ đệm nhỏ để không lòi
        const contentH = inner.scrollHeight;     // chiều cao thật của nội dung
        if (availH > 20 && contentH > 20) {
            let z = availH / contentH;
            if (z > 1) z = 1;        // nội dung ngắn → giữ nguyên (không phóng to)
            if (z < 0.25) z = 0.25;  // sàn rất thấp → luôn nhét vừa 1 màn hình
            inner.style.zoom = z >= 0.999 ? '' : String(z);
        }
        // Observe lại sau 1 frame (bỏ qua các thay đổi do chính fit vừa gây ra).
        if (this._previewFitRO) {
            requestAnimationFrame(() => {
                try { this._previewFitRO && this._previewFitRO.observe(inner); } catch (_e) {}
            });
        }
    }
    _setupPreviewAutoFit() {
        this._teardownPreviewAutoFit();
        const attach = () => {
            const body = document.querySelector('.o_vd_preview_modal .o_vd_preview_body_form');
            const inner = body && body.firstElementChild;
            if (!inner) { this._previewFitRaf = requestAnimationFrame(attach); return; }
            this._fitPreviewToViewport();
            try {
                this._previewFitRO = new ResizeObserver(() => this._fitPreviewToViewport());
                this._previewFitRO.observe(inner);
            } catch (_e) { /* noop */ }
            this._previewFitOnResize = () => this._fitPreviewToViewport();
            window.addEventListener('resize', this._previewFitOnResize);
            // Gọi lại vài lần cho chắc (form nhúng + bảng báo giá render bất đồng bộ).
            this._previewFitT1 = setTimeout(() => this._fitPreviewToViewport(), 250);
            this._previewFitT2 = setTimeout(() => this._fitPreviewToViewport(), 700);
            this._previewFitT3 = setTimeout(() => this._fitPreviewToViewport(), 1400);
        };
        this._previewFitRaf = requestAnimationFrame(attach);
    }
    _teardownPreviewAutoFit() {
        if (this._previewFitRaf) { cancelAnimationFrame(this._previewFitRaf); this._previewFitRaf = null; }
        if (this._previewFitRO) { try { this._previewFitRO.disconnect(); } catch (_e) {} this._previewFitRO = null; }
        if (this._previewFitOnResize) { window.removeEventListener('resize', this._previewFitOnResize); this._previewFitOnResize = null; }
        if (this._previewFitT1) { clearTimeout(this._previewFitT1); this._previewFitT1 = null; }
        if (this._previewFitT2) { clearTimeout(this._previewFitT2); this._previewFitT2 = null; }
        if (this._previewFitT3) { clearTimeout(this._previewFitT3); this._previewFitT3 = null; }
    }

    async prevPreview() {
        const p = this.state.previewLead;
        if (!p.open || p.index <= 0) return;
        // Chuyển sang KH khác = gỡ form nhúng hiện tại → lưu thao tác cuối trước.
        await this._saveIntakeBeforeLeave();
        this.state.previewLead.index = p.index - 1;
        this._setupPreviewAutoFit();   // form remount → tính lại auto-fit cho KH mới
    }

    async nextPreview() {
        const p = this.state.previewLead;
        if (!p.open || p.index >= p.ids.length - 1) return;
        await this._saveIntakeBeforeLeave();
        this.state.previewLead.index = p.index + 1;
        this._setupPreviewAutoFit();
    }

    // Props cho component <View/> embedded trong popup — render full form view
    // của crm.lead nhưng KHÔNG kèm Dialog wrapper / breadcrumb / action overhead
    // → load nhanh hơn so với FormViewDialog hoặc navigate trang.
    get previewViewProps() {
        const p = this.state.previewLead;
        if (!p.open || !p.ids.length) return null;
        const resId = p.ids[p.index];
        // ===== MEMOIZE (fix mất dữ liệu khi đang nhập) =====
        // Dashboard re-render MỖI 1s (training tick trainingNow) + poll 8s. Nếu
        // getter này trả về object props MỚI mỗi render (hàm onRecordSaved cũng
        // mới), OWL coi như props đổi → <View/> willUpdateProps → RELOAD form
        // nhúng → nuốt dữ liệu intake đang gõ dở (bệnh "nhập xong 2-5s tự mất").
        // Cache theo resId: chỉ tạo props mới khi ĐỔI sang KH khác → re-render
        // định kỳ không sinh props mới → form không reload → giữ nguyên chữ đang gõ.
        const cache = this._previewViewPropsCache;
        if (!cache || cache.resId !== resId) {
            this._previewViewPropsCache = {
                resId,
                props: {
                    type: "form",
                    resModel: "crm.lead",
                    resId,
                    mode: "edit",
                    // FORM RÚT GỌN (2026-08-14): ẩn panel VẤN ĐỀ, nhờ đó mỗi lần
                    // đổi khách không phải dựng lại nguyên một kanban con lồng
                    // trong form. Mở khách theo đường thường vẫn là form đầy đủ.
                    // 0/undefined -> bỏ qua, dùng form mặc định như trước.
                    ...(this.state.preview_view_id
                        ? { viewId: this.state.preview_view_id } : {}),
                    // BẬT control panel để có nút Lưu/Huỷ — TRƯỚC đây controlPanel:false
                    // khiến form KHÔNG có nút Save => intake (Tỉnh/Huyện...) KHÔNG bao giờ
                    // lưu xuống DB (log: 0 web_save cả ngày). Đó là gốc của "nó không lưu".
                    // CSS .o_vd_preview_modal sẽ thu gọn breadcrumb, chỉ giữ nút Lưu cho gọn.
                    display: { controlPanel: true },
                    // Sau khi save → refresh cached leads để pill update màu/data.
                    // NHƯNG khi popup CÒN MỞ thì KHÔNG refresh: mỗi lần lưu ngầm
                    // (NV bấm 1 chip là lưu 1 lần) sẽ kéo theo 1 RPC nạp lại toàn
                    // bộ dashboard → treo main-thread → "bấm rất khó bấm". Dồn
                    // lại, refresh 1 lần khi đóng popup.
                    onRecordSaved: () => {
                        if (this.state.previewLead && this.state.previewLead.open) {
                            this._vdNeedRefreshAfterPreview = true;
                            return;
                        }
                        this.refreshAfterPreview();
                    },
                },
            };
        }
        return this._previewViewPropsCache.props;
    }

    // CHUYỂN KH cho NV khác — nút trên topbar preview (chỉ admin/người chia số).
    // Mở wizard vd.lead.reassign.wizard (dialog) cho KH đang xem.
    async openReassignFromPreview() {
        const p = this.state.previewLead;
        if (!p.open || !p.ids.length) return;
        const leadId = p.ids[p.index];
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Chuyển khách cho nhân viên khác",
            res_model: "vd.lead.reassign.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: { default_lead_id: leadId },
        }, {
            onClose: () => this.refreshAfterPreview(),
        });
    }

    async refreshAfterPreview() {
        if (this.state.selectedStageId) {
            // Refresh NGẦM (không bật loading) → đóng popup về dashboard tức thì,
            // pill tự cập nhật khi data về, không thấy "load trang".
            this._silentStageLoad = true;
            try {
                await this.selectStage(this.state.selectedStageId);
            } catch (_e) {
            } finally {
                this._silentStageLoad = false;
            }
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
    // SỐ OMI: hover nút → popup thẻ khách OMI (90% màn hình). Guard mở 1 lần.
    openOmi() {
        if (this._omiOpen) return;
        this._omiOpen = true;
        this.dialog.add(VdOmiDialog, {
            onCall: (phone, name) => this.callOmiNumber(phone, name),
        }, { onClose: () => { this._omiOpen = false; } });
    }
    callOmiNumber(phone, name) {
        if (!phone) {
            this.notification.add("Khách chưa có SĐT.", { type: "warning" });
            return;
        }
        this.stringee.call(phone, name || "").catch(
            (e) => this.notification.add(e.message || "Gọi thất bại", { type: "danger" }));
    }

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

    // Bấm 1 khách trong bảng ghi âm (hover THÁNG NÀY) → mở thẳng form khách đó.
    openRecLead(leadId) {
        if (!leadId) return;
        this._closeRecNow();
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'crm.lead',
            res_id: leadId,
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

    // Mở màn "Cuộc gọi đến" (lịch sử khách gọi vào tổng đài).
    openInboundCalls() {
        this.action.doAction("vd_crm_lead.action_stringee_inbound");
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
                + "Khách kiểu này thường KHÔNG bắt máy số lạ. NÊN NHẮN TIN ZALO "
                + "(kết bạn khi khách trả lời) thay vì gọi tiếp.\n\n"
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

    // ===== 2 nút THƯ VIỆN nổi trên dashboard (trang khách hàng NV) =====
    // Mở 1 popup THƯ VIỆN — KHÓA chống mở nhiều popup khi bấm liên tục / lúc đang
    // tải chậm (user spec 2026-07-17: bấm nhiều lần rồi bung ra hàng loạt popup).
    _openLibDialog(Comp, props) {
        if (!Comp || this._libDialogOpen) return;
        this._libDialogOpen = true;
        this.dialog.add(Comp, props || {}, {
            onClose: () => { this._libDialogOpen = false; },
        });
    }
    openHardLibrary() {
        const Comp = registry.category("vd_dialogs").get("hard_library", null);
        if (Comp) {
            this._openLibDialog(Comp);
        } else {
            this.notification.add("Chưa cài thư viện câu hỏi khó.", { type: "warning" });
        }
    }
    openHouseLibrary() {
        this._openLibDialog(VdHouseLibDialog);
    }
    // 3 THƯ VIỆN tài liệu Drive — hiện trên DANH SÁCH khách (khi không mở preview).
    get driveLibs() {
        return [
            { key: "3d", title: "THƯ VIỆN - 3D", icon: "fa-cube", cls: "o_vd_3d_lib_filter" },
            { key: "nghiem_thu", title: "THƯ VIỆN - Video nghiệm thu", icon: "fa-film", cls: "o_vd_nt_lib_filter" },
            { key: "cong_nang_3d", title: "THƯ VIỆN - Công năng", icon: "fa-th-large", cls: "o_vd_cn3d_lib_filter" },
            { key: "hop_dong", title: "THƯ VIỆN - Hợp đồng", icon: "fa-file-text-o", cls: "o_vd_hd_lib_filter" },
        ];
    }
    openDriveLib(lib) {
        this._openLibDialog(VdDriveLibDialog, { libKey: lib.key, libTitle: lib.title });
    }

    bonusTier(n) {
        // Đọc từ CẤU HÌNH 'Thưởng cá nhân' (bonusBoard.personal) — match Python.
        const cfg = (this.state.bonusBoard && this.state.bonusBoard.personal) || [];
        if (cfg.length) {
            const map = {};
            for (const b of cfg) { map[b.contract_no] = b.amount; }
            const maxNo = Math.max(...cfg.map((b) => b.contract_no));
            return map[n] !== undefined ? map[n] : map[maxNo];
        }
        // Fallback khi chưa cấu hình.
        const TIERS = { 1: 3_500_000, 2: 5_500_000, 3: 7_500_000, 4: 8_500_000, 5: 9_500_000 };
        return TIERS[n] || 9_500_000;
    }

    formatVnd(n) {
        if (n === null || n === undefined) return "0";
        return new Intl.NumberFormat('vi-VN').format(Math.round(n));
    }

    // Tháng thực tế hiện tại (1-12) cho tiêu đề "THƯỞNG THÁNG N".
    get currentMonth() {
        return new Date().getMonth() + 1;
    }

    formatDate(s) {
        if (!s) return "";
        return s.replace("T", " ").slice(0, 16);
    }

    // ============================================================
    // 📊 ANALYTICS BI — Date filter + 4 Chart.js charts
    // ============================================================
    async loadAnalytics(scope) {
        // scope='team' (GĐ chế độ CÁ NHÂN) → backend bó về NV phòng mình. Mặc
        // định lấy theo dirTeamMode để các chỗ gọi cũ tự đúng scope.
        const sc = scope || (this.state.dirTeamMode ? 'team' : null);
        this.state.analyticsLoading = true;
        try {
            const data = await this.orm.call("crm.lead", "dashboard_analytics", [
                this.state.analyticsFrom, this.state.analyticsTo, sc,
            ]);
            this.state.analytics = data;
            // KHÔNG reset empExpanded/empPinned ở đây nữa: analytics có thể tải lại
            // nền và sẽ XOÁ cú bấm NHÂN VIÊN của user (lỗi r9). Việc reset trạng thái
            // giãn khi đổi chế độ do goPersonal() lo.
        } catch (e) {
            // NV thường (self-only) lỗi thì im lặng — chỉ báo cho quản lý.
            if (this.isTeamManager) {
                this.notification.add(e.message || "Lỗi tải insights", { type: "danger" });
            }
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
