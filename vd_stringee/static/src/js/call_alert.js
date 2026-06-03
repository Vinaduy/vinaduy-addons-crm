/** @odoo-module **/
/**
 * Popup cuộc gọi HỢP NHẤT — căn giữa trên cùng màn hình, thiết kế tinh tế.
 *
 * Một bảng duy nhất xử lý TOÀN BỘ vòng đời cuộc gọi (không còn rải rác trên
 * form "Thông tin tư vấn"):
 *   - LIVE  (state.inCall): cuộc gọi ĐẾN / ĐI, đang gọi, đổ chuông, đàm thoại
 *           → hiện tên/số/nhà mạng + đếm giây + nút CÚP MÁY.
 *   - OUTCOME (state.alertShow): kết quả cuộc (bận / từ chối / không nghe / số
 *           chết / lỗi...) → icon + tiêu đề + nội dung, tự tắt hoặc bấm đóng.
 *
 * Nguồn dữ liệu: reactive state của `stringee` service.
 */
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const CARRIER_LABEL = { viettel: "Viettel", vina: "Vinaphone", mobi: "MobiFone" };
const OUTCOME_ICON = {
    danger: "fa-exclamation-triangle",
    warning: "fa-exclamation-circle",
    info: "fa-info-circle",
    success: "fa-check-circle",
};

export class VdCallAlert extends Component {
    static template = "vd_stringee.CallAlert";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        this.s = useState(this.stringee.state);
        this.ui = useState({ elapsed: 0 });
        onMounted(() => {
            this._tick();
            this._timer = setInterval(() => this._tick(), 500);
        });
        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
        });
    }

    // ----- chế độ -----
    get live() { return this.s.inCall; }
    get incoming() { return this.s.callDirection === "in"; }
    get answered() {
        return this.s.callStatus === "ANSWERED" || !!this.s.answerStartedAt;
    }

    get statusLabel() {
        if (this.incoming) return this.answered ? "Cuộc gọi đến" : "Cuộc gọi đến…";
        if (this.answered) return "Đang nói chuyện";
        if (this.s.callStatus === "RINGING") return "Đang đổ chuông";
        return "Đang gọi";
    }

    get phaseClass() {
        if (this.answered) return "o_vd_cp_talk";
        if (this.incoming) return "o_vd_cp_incoming";
        if (this.s.callStatus === "RINGING") return "o_vd_cp_ringing";
        return "o_vd_cp_dialing";
    }

    get carrierLabel() { return CARRIER_LABEL[this.s.callCarrier] || ""; }

    get formatted() {
        const e = this.ui.elapsed;
        const m = Math.floor(e / 60);
        const s = e % 60;
        return `${m}:${s.toString().padStart(2, "0")}`;
    }

    // ----- outcome -----
    get outcomeIcon() { return OUTCOME_ICON[this.s.alertLevel] || OUTCOME_ICON.info; }

    _tick() {
        if (!this.s.inCall) {
            if (this.ui.elapsed !== 0) this.ui.elapsed = 0;
            return;
        }
        const start = this.s.answerStartedAt || this.s.callStartedAt || 0;
        this.ui.elapsed = start
            ? Math.max(0, Math.floor((Date.now() - start) / 1000))
            : 0;
    }

    onHangup() {
        try { this.stringee.hangup(); } catch (_e) { /* noop */ }
    }
    onClose() {
        this.stringee.hideCallAlert();
    }
}

registry.category("main_components").add("vd_stringee.CallAlert", {
    Component: VdCallAlert,
});
