/** @odoo-module **/
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODEL = "vd.stringee.hotline";

/**
 * Bảng phân bổ số tổng đài theo NV — KÉO-THẢ.
 * Trái: kho số gom theo nhà mạng (mỗi số = 1 chip kéo được).
 * Phải: mỗi NV 1 ô; kéo số từ kho thả vào ô NV để gán.
 *   - Thả số cùng mạng NV đã có → backend tự thay số cũ (1 mạng 1 số).
 *   - Bấm × trên chip trong ô NV để gỡ.
 */
export class VdStringeeAssignmentBoard extends Component {
    static template = "vd_stringee.AssignmentBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.stringee = useService("stringee");
        this.state = useState({
            carriers: [],
            users: [],
            alerts: [],   // NV thiếu số sống theo mạng (báo admin)
            loading: true,
            search: "",
            busy: false,
            hover: null, // {number, top, left}
            daily: null, // báo cáo 15 ngày của số đang hover (null = đang tải)
            // Popup chia số: open + map chọn số/NV theo id
            dist: { open: false, nums: {}, users: {} },
            // Popup GỌI THỬ 1 số (nút điện thoại trên mỗi chip)
            test: {
                open: false, hotline: null, phone: "",
                phase: "idle",   // idle | calling | rang | answered | nores | error
                msg: "", lastId: 0, secs: 0,
            },
        });
        onWillStart(() => this.load());
        onWillUnmount(() => this._stopTestPoll());
    }

    async load() {
        this._dailyCache = {};   // số liệu ngày có thể đã đổi (vừa gọi thử / chốt)
        const data = await this.orm.call(MODEL, "get_assignment_board", []);
        this.state.carriers = data.carriers;
        this.state.users = data.users;
        this.state.alerts = data.alerts || [];
        this.state.loading = false;
    }

    get filteredUsers() {
        const s = (this.state.search || "").trim().toLowerCase();
        if (!s) {
            return this.state.users;
        }
        return this.state.users.filter(
            (u) =>
                (u.name || "").toLowerCase().includes(s) ||
                (u.login || "").toLowerCase().includes(s)
        );
    }

    // Click vào số = COPY (giống click tên KH). Dùng action copy chế độ silent
    // (copy ngay trong user-gesture, không mở dialog).
    copyNumber(ev, num) {
        ev.stopPropagation();
        this.action.doAction({
            type: "ir.actions.client",
            tag: "vd_copy_to_clipboard",
            params: { text: num, silent: true, message: `Đã copy số ${num}` },
        });
    }

    onDragStart(ev, number, carrier) {
        this.state.hover = null; // ẩn popover khi bắt đầu kéo
        ev.dataTransfer.setData(
            "text/plain",
            JSON.stringify({ id: number.id, carrier })
        );
        ev.dataTransfer.effectAllowed = "copy";
    }

    // ---- Hover popover: bảng chi tiết số (NV / dùng từ / phút gọi / cuộc) ----
    onChipEnter(ev, number) {
        const r = ev.currentTarget.getBoundingClientRect();
        // position:fixed theo viewport → không bị cắt bởi vùng cuộn của kho số.
        this.state.hover = { number, top: Math.round(r.bottom + 6), left: Math.round(r.left) };
        this._loadDaily(number);
    }
    onChipLeave() {
        this.state.hover = null;
    }

    // Báo cáo 15 ngày (neo vào lần đổ chuông cuối) — nạp LƯỜI lúc hover, cache
    // theo id để rê chuột qua lại không bắn lại RPC.
    async _loadDaily(number) {
        this._dailyCache = this._dailyCache || {};
        if (this._dailyCache[number.id]) {
            this.state.daily = this._dailyCache[number.id];
            return;
        }
        this.state.daily = null;   // hiện "Đang tải…"
        let res;
        try {
            res = await this.orm.call(MODEL, "vd_number_daily_report", [number.id]);
        } catch (_e) {
            res = { rows: [], anchor: false };
        }
        this._dailyCache[number.id] = res;
        // Chuột đã rời/đổi sang số khác trong lúc chờ → bỏ kết quả cũ.
        if (this.state.hover && this.state.hover.number.id === number.id) {
            this.state.daily = res;
        }
    }
    get popStyle() {
        const h = this.state.hover;
        if (!h) {
            return "";
        }
        // Popover nay cao hơn (thêm bảng 15 ngày) → kẹp lại để không tràn đáy
        // màn hình khi hover chip nằm cuối danh sách.
        const maxTop = Math.max(8, window.innerHeight - 620);
        const top = Math.max(8, Math.min(h.top, maxTop));
        return `top:${top}px; left:${h.left}px;`;
    }

    // ============ POPUP CHIA SỐ (chọn số → chọn NV → CHIA SỐ) ============
    openDistModal() {
        const nums = {};
        for (const c of this.state.carriers) {
            for (const n of c.numbers) {
                nums[n.id] = n.health === "alive"; // mặc định: chọn số CÒN SỐNG
            }
        }
        const users = {};
        for (const u of this.state.users) {
            users[u.id] = !u.no_share;             // mặc định: NV không bị loại
        }
        this.state.dist = { open: true, nums, users };
    }
    closeDistModal() {
        this.state.dist.open = false;
    }
    toggleDistNum(id) {
        this.state.dist.nums[id] = !this.state.dist.nums[id];
    }
    toggleDistUser(id) {
        this.state.dist.users[id] = !this.state.dist.users[id];
    }
    get distNumIds() {
        return Object.keys(this.state.dist.nums)
            .filter((id) => this.state.dist.nums[id])
            .map(Number);
    }
    get distUserIds() {
        return Object.keys(this.state.dist.users)
            .filter((id) => this.state.dist.users[id])
            .map(Number);
    }
    distSelectAlive() {
        for (const c of this.state.carriers) {
            for (const n of c.numbers) {
                this.state.dist.nums[n.id] = n.health === "alive";
            }
        }
    }
    distClearNums() {
        for (const k of Object.keys(this.state.dist.nums)) {
            this.state.dist.nums[k] = false;
        }
    }
    distSelectEligible() {
        for (const u of this.state.users) {
            this.state.dist.users[u.id] = !u.no_share;
        }
    }
    distClearUsers() {
        for (const k of Object.keys(this.state.dist.users)) {
            this.state.dist.users[k] = false;
        }
    }
    async doDistribute() {
        const numIds = this.distNumIds;
        const userIds = this.distUserIds;
        if (!numIds.length || !userIds.length) {
            this.notification.add("Chọn ít nhất 1 số và 1 nhân viên.", {
                type: "warning",
            });
            return;
        }
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const res = await this.orm.call(
                MODEL, "distribute_numbers_to_users", [numIds, userIds]
            );
            this.state.dist.open = false;
            await this.load();
            this.notification.add(res.message || "Đã chia số", {
                type: res.ok ? "success" : "warning",
                sticky: !res.ok,
            });
        } finally {
            this.state.busy = false;
        }
    }

    // ==================== GỌI THỬ 1 SỐ (nút điện thoại) ====================
    // Vì sao cần: sức khoẻ số tự tính theo lịch sử gọi, mà số bị nhà mạng chặn
    // nằm im vài ngày là cửa sổ đánh giá rỗng → tự xanh lại → chia cho NV → NV
    // gọi vào hư không. Admin bấm gọi thử 1 cuộc là biết CHẮC, rồi chốt tay.
    async openTest(ev, hotline) {
        ev.stopPropagation();
        this.state.hover = null;
        this.state.test = {
            open: true, hotline, phone: "",
            phase: "idle", msg: "", lastId: 0, secs: 0,
            // Gợi ý số KH CÙNG MẠNG — test nội mạng mới đúng cái NV gặp phải.
            cands: [], candLabel: "", candLoading: true, candSearch: "",
        };
        try {
            const res = await this.orm.call(
                MODEL, "vd_test_call_candidates", [hotline.id]);
            if (!this.state.test.open || this.state.test.hotline.id !== hotline.id) {
                return;   // admin đã đóng / mở số khác trong lúc chờ
            }
            this.state.test.cands = res.leads || [];
            this.state.test.candLabel = res.label || "";
        } catch (_e) {
            this.state.test.cands = [];
        } finally {
            this.state.test.candLoading = false;
        }
    }

    get testCandidates() {
        const t = this.state.test;
        const s = (t.candSearch || "").trim().toLowerCase();
        if (!s) {
            return t.cands;
        }
        return t.cands.filter(
            (c) => (c.name || "").toLowerCase().includes(s)
                || (c.phone || "").includes(s)
        );
    }

    onCandSearch(ev) {
        this.state.test.candSearch = ev.target.value || "";
    }

    pickCandidate(c) {
        this.state.test.phone = (c.phone || "").replace(/[^0-9+]/g, "");
    }

    closeTest() {
        this._stopTestPoll();
        // Còn đang đổ chuông mà đóng popup → cúp luôn, không để nó reo tiếp.
        if (this.state.test.phase === "calling") {
            try { this.stringee.hangup(); } catch (_e) {}
        }
        this.state.test.open = false;
    }

    onTestPhoneInput(ev) {
        this.state.test.phone = (ev.target.value || "").replace(/[^0-9+]/g, "");
    }

    _stopTestPoll() {
        if (this._testTimer) {
            clearInterval(this._testTimer);
            this._testTimer = null;
        }
    }

    get testCanCall() {
        const t = this.state.test;
        return t.phone.replace(/[^0-9]/g, "").length >= 9 && t.phase !== "calling";
    }

    async doTestCall() {
        const t = this.state.test;
        if (!this.testCanCall || !t.hotline) {
            return;
        }
        this._stopTestPoll();
        t.phase = "calling";
        t.msg = "Đang gọi… chờ đổ chuông";
        t.secs = 0;
        try {
            const begin = await this.orm.call(
                MODEL, "vd_test_call_begin", [t.hotline.id]);
            if (begin.error) {
                t.phase = "error";
                t.msg = begin.error;
                return;
            }
            t.lastId = begin.last_id || 0;
            // Gọi ĐÚNG đường NV vẫn gọi (Web SDK, fallback REST) nhưng ÉP đầu số
            // đang kiểm tra → kết quả phản ánh đúng trải nghiệm của NV.
            // KHÔNG await: promise này chỉ xong khi cuộc gọi kết thúc, trong khi
            // vòng soi kết quả phải chạy NGAY từ giây đầu.
            this.stringee.call(t.phone, `Gọi thử ${t.hotline.number}`, {
                forceFrom: t.hotline.number,
            }).catch((e) => {
                const t3 = this.state.test;
                if (t3.phase === "calling") {
                    t3.phase = "error";
                    t3.msg = (e && e.message) || "Không gọi được.";
                    this._stopTestPoll();
                }
            });
        } catch (e) {
            t.phase = "error";
            t.msg = (e && e.message) || "Không khởi tạo được cuộc gọi thử.";
            return;
        }
        // Soi kết quả từ SERVER (raw_events) — cùng nguồn với cron sức khoẻ, nên
        // kết luận ở đây khớp đúng với cái cron sẽ chấm.
        this._testTimer = setInterval(async () => {
            const t2 = this.state.test;
            if (!t2.open) {
                this._stopTestPoll();
                return;
            }
            t2.secs += 2;
            let res;
            try {
                res = await this.orm.call(
                    MODEL, "vd_test_call_status", [t2.hotline.id, t2.lastId]);
            } catch (_e) {
                return;
            }
            if (res && res.found) {
                if (res.answered) {
                    t2.phase = "answered";
                    t2.msg = "ĐÃ NGHE MÁY — số này gọi ra bình thường.";
                    this._stopTestPoll();
                    return;
                }
                if (res.rang) {
                    t2.phase = "rang";
                    t2.msg = "CÓ ĐỔ CHUÔNG — số còn sống (khách chưa bắt máy).";
                }
                const done = ["ended", "declined", "no_answer", "failed", "busy"]
                    .includes(res.state);
                if (done && !res.rang) {
                    t2.phase = "nores";
                    t2.msg = "KHÔNG hề đổ chuông"
                        + (res.hangup_cause ? ` (${res.hangup_cause})` : "")
                        + " — nhiều khả năng nhà mạng đã chặn số này.";
                    this._stopTestPoll();
                    return;
                }
            }
            if (t2.secs >= 46) {
                this._stopTestPoll();
                if (t2.phase === "calling") {
                    t2.phase = "nores";
                    t2.msg = "Hết 45 giây vẫn KHÔNG đổ chuông — coi như số chặn.";
                }
            }
        }, 2000);
    }

    async testVerdict(rang) {
        const t = this.state.test;
        if (!t.hotline || this.state.busy) {
            return;
        }
        this._stopTestPoll();
        this.state.busy = true;
        try {
            const res = await this.orm.call(
                MODEL, "vd_test_call_verdict", [t.hotline.id, !!rang]);
            this.state.test.open = false;
            await this.load();
            this.notification.add(res.message || "Đã ghi kết quả", {
                type: rang ? "success" : "warning",
                sticky: !rang,
            });
        } finally {
            this.state.busy = false;
        }
    }

    // ---- Bật/tắt cờ "không chia số" cho 1 NV ----
    async toggleNoShare(user) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "toggle_user_no_share", [user.id, !user.no_share]);
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }

    // ---- Nút mở popup (full màn hình) ----
    openDistribute() {
        this.action.doAction("vd_stringee.action_vd_stringee_distribute_wizard", {
            onClose: () => this.load(),
        });
    }
    openLookup() {
        this.action.doAction("vd_stringee.action_users_stringee_matrix", {
            onClose: () => this.load(),
        });
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
        ev.currentTarget.classList.add("o_vd_drop_hover");
    }

    onDragLeave(ev) {
        ev.currentTarget.classList.remove("o_vd_drop_hover");
    }

    async onDrop(ev, user) {
        ev.preventDefault();
        ev.currentTarget.classList.remove("o_vd_drop_hover");
        if (this.state.busy) {
            return;
        }
        let payload;
        try {
            payload = JSON.parse(ev.dataTransfer.getData("text/plain"));
        } catch (e) {
            return;
        }
        if (!payload || !payload.id) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "assign_user_hotline", [user.id, payload.id]);
            await this.load();
            this.notification.add(`Đã gán số cho ${user.name}`, { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async onRemove(user, hotline) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "unassign_user_hotline", [user.id, hotline.id]);
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
}

registry
    .category("actions")
    .add("vd_stringee_assignment_board", VdStringeeAssignmentBoard);
