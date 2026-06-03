/** @odoo-module **/
/**
 * Bảng nổi trạng thái cuộc gọi — góc phải-dưới, hiện ở MỌI trang.
 *
 * Nguồn dữ liệu: reactive state của `stringee` service (vd_stringee/stringee_sdk.js).
 * Hiện khi có cuộc đang diễn ra (state.inCall), tự ẩn khi cúp/kết thúc.
 *
 * Trạng thái + đếm giây:
 *   - "Đang gọi…" / "Đang đổ chuông…" : đếm giây CHỜ (từ lúc bấm gọi).
 *   - "Đang nói chuyện"               : đếm giây ĐÀM THOẠI (từ lúc KH bắt máy).
 * Có nút "Cúp máy" để kết thúc ngay từ bảng.
 */
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const CARRIER_LABEL = { viettel: "Viettel", vina: "Vinaphone", mobi: "MobiFone" };

export class VdCallPanel extends Component {
    static template = "vd_stringee.CallPanel";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        // useState bọc reactive state của service → bảng tự re-render khi
        // call lifecycle đổi (inCall / callStatus / answerStartedAt…).
        this.call = useState(this.stringee.state);
        this.ui = useState({ elapsed: 0 });
        onMounted(() => {
            this._tick();
            this._timer = setInterval(() => this._tick(), 500);
        });
        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
        });
    }

    _tick() {
        const s = this.call;
        if (!s.inCall) {
            if (this.ui.elapsed !== 0) this.ui.elapsed = 0;
            return;
        }
        // KH đã bắt máy → đếm giây đàm thoại; chưa → đếm giây chờ đổ chuông.
        const start = s.answerStartedAt || s.callStartedAt || 0;
        this.ui.elapsed = start
            ? Math.max(0, Math.floor((Date.now() - start) / 1000))
            : 0;
    }

    get answered() {
        return this.call.callStatus === "ANSWERED" || !!this.call.answerStartedAt;
    }

    get statusLabel() {
        if (this.answered) return "Đang nói chuyện";
        if (this.call.callStatus === "RINGING") return "Đang đổ chuông…";
        return "Đang gọi…";
    }

    get carrierLabel() {
        return CARRIER_LABEL[this.call.callCarrier] || "";
    }

    get formatted() {
        const e = this.ui.elapsed;
        const m = Math.floor(e / 60);
        const s = e % 60;
        return `${m}:${s.toString().padStart(2, "0")}`;
    }

    onHangup() {
        try {
            this.stringee.hangup();
        } catch (_e) {
            /* noop */
        }
    }
}

registry.category("main_components").add("vd_stringee.CallPanel", {
    Component: VdCallPanel,
});
