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

export class VdDialpadFab extends Component {
    static template = "vd_stringee.DialpadFab";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        this.notification = useService("notification");
        this.state = useState({ open: false, number: "", calling: false });
        this.inputRef = useRef("numInput");
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
        this.state.open = !this.state.open;
        if (this.state.open) {
            setTimeout(() => this.inputRef.el && this.inputRef.el.focus(), 60);
        }
    }
    close() { this.state.open = false; }

    press(d) {
        if (this.state.number.length >= 15) return;
        this.state.number += d;
    }
    backspace() { this.state.number = this.state.number.slice(0, -1); }

    onInput(ev) {
        // Cho phép gõ/dán: chỉ giữ số + dấu + * #
        this.state.number = (ev.target.value || "").replace(/[^\d+*#]/g, "");
    }

    async paste() {
        try {
            const txt = await navigator.clipboard.readText();
            const cleaned = (txt || "").replace(/[^\d+]/g, "");
            if (cleaned) {
                this.state.number = cleaned;
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
        } catch (e) {
            this.notification.add(e.message || "Gọi thất bại", { type: "danger" });
        } finally {
            setTimeout(() => { this.state.calling = false; }, 1500);
        }
    }
}

registry.category("main_components").add("vd_stringee.DialpadFab", { Component: VdDialpadFab });
