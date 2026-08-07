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
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.s = useState(this.stringee.state);
        this.ui = useState({ elapsed: 0 });
        this.tf = useState({ open: false, busy: false, targets: [] });
        this.cb = useState({ busy: false });
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
    // Cuộc gọi ĐẾN đang RUNG chờ (chưa bấm nghe) → hiện nút Nghe máy / Từ chối.
    get ringingIncoming() {
        return this.incoming && !this.answered && !!this.s.pendingIncoming;
    }
    onAnswer() {
        try { this.stringee.answerIncoming(); } catch (_e) { /* noop */ }
    }
    onReject() {
        try { this.stringee.rejectIncoming(); } catch (_e) { /* noop */ }
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

    // ----- CHUYỂN MÁY -----
    async onToggleTransfer() {
        this.tf.open = !this.tf.open;
        if (this.tf.open && !this.tf.targets.length) {
            this.tf.targets = await this.stringee.transferTargets();
        }
    }
    async onTransferTo(userId, userName) {
        if (this.tf.busy) return;
        this.tf.busy = true;
        const res = await this.stringee.transfer(userId);
        this.tf.busy = false;
        this.tf.open = false;
        if (res && res.error) {
            this.notification.add(res.error, { type: "danger", title: "Chuyển máy thất bại" });
        } else {
            this.notification.add(`Đã chuyển máy sang ${userName}.`, {
                type: "success", title: "Chuyển máy",
            });
        }
    }
    onClose() {
        this.stringee.hideCallAlert();
    }

    // ----- HẸN GỌI LẠI (sau khi cúp máy cuộc gọi ĐI) -----
    get callbackShow() { return !!this.s.callbackPrompt && !this.s.inCall; }
    get callbackName() {
        const p = this.s.callbackPrompt;
        return p ? (p.name || p.phone || "") : "";
    }
    // 16 mốc theo yêu cầu user 2026-08-06.
    get callbackOptions() {
        return [
            { k: "4h", l: "4 Tiếng" }, { k: "eod", l: "Cuối ngày" },
            { k: "tomorrow", l: "Ngày mai" }, { k: "2d", l: "2 Ngày" },
            { k: "3d", l: "3 Ngày" }, { k: "5d", l: "5 Ngày" },
            { k: "weekend", l: "Cuối tuần" }, { k: "1w", l: "1 Tuần" },
            { k: "2w", l: "2 Tuần" }, { k: "3w", l: "3 Tuần" },
            { k: "1mo", l: "1 Tháng" }, { k: "2mo", l: "2 Tháng" },
            { k: "3mo", l: "3 Tháng" }, { k: "4mo", l: "4 Tháng" },
            { k: "6mo", l: "6 Tháng" }, { k: "1y", l: "1 Năm" },
        ];
    }
    async pickCallback(key) {
        const p = this.s.callbackPrompt;
        if (!p || this.cb.busy) return;
        this.cb.busy = true;
        try {
            const res = await this.orm.call("crm.lead", "vd_set_callback_by_phone", [p.phone, key]);
            if (res && res.ok) {
                this.notification.add(
                    key === "none" ? "Đã bỏ hẹn gọi lại." : `Đã hẹn gọi lại lúc ${res.when}.`,
                    { type: "success", title: "Hẹn gọi lại" });
            } else {
                this.notification.add(
                    "Không đặt được hẹn (không tìm thấy khách theo số này).",
                    { type: "warning" });
            }
        } catch (_e) {
            this.notification.add("Lỗi khi đặt hẹn gọi lại.", { type: "danger" });
        } finally {
            this.cb.busy = false;
            this.s.callbackPrompt = null;
        }
    }
    dismissCallback() { this.s.callbackPrompt = null; }
}

registry.category("main_components").add("vd_stringee.CallAlert", {
    Component: VdCallAlert,
});
