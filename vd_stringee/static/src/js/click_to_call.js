/** @odoo-module **/
/**
 * BÀN PHÍM GỌI TAY kiểu iPhone (user spec 2026-06-13).
 *
 * Trang danh sách KH (và mọi trang backend) có 1 nút điện thoại NỔI góc
 * phải-dưới. Bấm vào → mở keypad kiểu iPhone: gõ số HOẶC dán số → bấm nút
 * gọi xanh → gọi qua stringee service (tự normalize số VN, chống double-call).
 *
 * Đăng ký ở main_components nên nổi trên toàn web backend.
 */
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class VdDialpadFab extends Component {
    static template = "vd_stringee.DialpadFab";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        this.notification = useService("notification");
        // lookup: null = chưa tra; {found, text, type} sau khi tra số.
        this.state = useState({ open: false, number: "", calling: false, lookup: null });
        this.inputRef = useRef("numInput");
        this._lookupTimer = null;
        this._lookupSeq = 0;
        // Mở bằng hover → tự đóng khi rời chuột; mở bằng click → giữ nguyên.
        this._hoverOpened = false;
        this._hoverCloseTimer = null;
    }

    // iPhone keypad: chữ cái dưới số cho giống bàn phím gọi thật.
    get keys() {
        return [
            { d: "1", s: "" },
            { d: "2", s: "ABC" },
            { d: "3", s: "DEF" },
            { d: "4", s: "GHI" },
            { d: "5", s: "JKL" },
            { d: "6", s: "MNO" },
            { d: "7", s: "PQRS" },
            { d: "8", s: "TUV" },
            { d: "9", s: "WXYZ" },
            { d: "*", s: "" },
            { d: "0", s: "+" },
            { d: "#", s: "" },
        ];
    }

    toggle() {
        this._cancelHoverClose();
        this.state.open = !this.state.open;
        this._hoverOpened = false;   // mở bằng click → KHÔNG tự đóng khi rời chuột
        if (this.state.open) {
            setTimeout(() => this.inputRef.el && this.inputRef.el.focus(), 60);
        }
    }
    // Đưa chuột vào nút gọi → tự bật keypad ra (user spec 2026-06-14).
    openOnHover() {
        if (this.state.open) return;
        this._hoverOpened = true;
        this.state.open = true;
        setTimeout(() => this.inputRef.el && this.inputRef.el.focus(), 80);
    }
    close() {
        this._cancelHoverClose();
        this._hoverOpened = false;
        this.state.open = false;
    }

    _cancelHoverClose() {
        if (this._hoverCloseTimer) {
            clearTimeout(this._hoverCloseTimer);
            this._hoverCloseTimer = null;
        }
    }
    // Chuột vào lại panel/nút → huỷ lịch đóng (user spec 2026-06-14).
    onHoverEnter() { this._cancelHoverClose(); }
    // Rời chuột khỏi panel/nút: chỉ tự đóng nếu mở bằng HOVER và CHƯA nhập số
    // (đã gõ số / đang gọi thì giữ để khỏi mất thao tác).
    onHoverLeave() {
        if (!this._hoverOpened) return;
        if (this.state.number || this.state.calling) return;
        this._cancelHoverClose();
        this._hoverCloseTimer = setTimeout(() => this.close(), 240);
    }

    press(d) {
        if (this.state.number.length >= 15) return;
        this.state.number += d;
        this.scheduleLookup();
    }
    backspace() {
        this.state.number = this.state.number.slice(0, -1);
        this.scheduleLookup();
    }

    onInput(ev) {
        // Cho phép gõ/dán: chỉ giữ số + dấu + * #
        this.state.number = (ev.target.value || "").replace(/[^\d+*#]/g, "");
        this.scheduleLookup();
    }

    // ===== Tra số → hiện tên KH / cảnh báo NV khác quản lý (debounce) =====
    scheduleLookup() {
        if (this._lookupTimer) clearTimeout(this._lookupTimer);
        const digits = (this.state.number || "").replace(/\D/g, "");
        if (digits.length < 8) {
            this.state.lookup = null;
            return;
        }
        this._lookupTimer = setTimeout(() => this.doLookup(), 350);
    }

    async doLookup() {
        const num = (this.state.number || "").trim();
        const seq = ++this._lookupSeq;
        try {
            const res = await rpc("/stringee/lookup_number", { number: num });
            if (seq !== this._lookupSeq) return; // số đã đổi, bỏ kết quả cũ
            if (!res || !res.found) {
                this.state.lookup = { found: false, text: "Số mới — chưa có khách hàng.", type: "new" };
                return;
            }
            if (res.owned_by_other) {
                const who = res.owner_name || "NV khác";
                this.state.lookup = {
                    found: true,
                    text: `${res.lead_name} — ⚠ đã có ${who} quản lý`,
                    type: "warn",
                };
            } else {
                this.state.lookup = {
                    found: true,
                    text: `${res.lead_name}${res.is_mine ? " (KH của bạn)" : ""}`,
                    type: "mine",
                };
            }
        } catch (e) {
            if (seq === this._lookupSeq) this.state.lookup = null;
        }
    }

    async paste() {
        try {
            const txt = await navigator.clipboard.readText();
            const cleaned = (txt || "").replace(/[^\d+]/g, "");
            if (cleaned) {
                this.state.number = cleaned;
                this.scheduleLookup();
            } else {
                this.notification.add("Clipboard không có số.", { type: "warning" });
            }
        } catch (e) {
            this.notification.add(
                "Trình duyệt không cho đọc clipboard. Hãy bấm vào ô số rồi Ctrl+V.",
                { type: "warning" },
            );
            if (this.inputRef.el) this.inputRef.el.focus();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.callNow();
        }
    }

    async callNow() {
        const num = (this.state.number || "").trim();
        if (!num) {
            this.notification.add("Nhập số điện thoại trước khi gọi.", { type: "warning" });
            if (this.inputRef.el) this.inputRef.el.focus();
            return;
        }
        if (this.state.calling) return;
        this.state.calling = true;
        try {
            await this.stringee.call(num, "Gọi tay");
            // Số mới (chưa có KH) → tự lưu vào danh sách KH mới (tên = SĐT).
            this.ensureLeadSaved(num);
        } catch (e) {
            this.notification.add(e.message || "Gọi thất bại", { type: "danger" });
        } finally {
            setTimeout(() => { this.state.calling = false; }, 1500);
        }
    }

    async ensureLeadSaved(num) {
        try {
            const res = await rpc("/stringee/ensure_lead_for_dial", { number: num });
            if (res && res.created) {
                this.notification.add(
                    `Đã lưu số ${res.name} vào danh sách khách mới.`,
                    { type: "success" },
                );
            }
        } catch (e) {
            // Lỗi lưu KH không được chặn cuộc gọi — bỏ qua im lặng.
        }
    }
}

registry.category("main_components").add("vd_stringee.DialpadFab", { Component: VdDialpadFab });
