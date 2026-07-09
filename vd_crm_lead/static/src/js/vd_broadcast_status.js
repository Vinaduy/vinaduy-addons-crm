/** @odoo-module **/
/**
 * Luồng theo dõi CHIẾN DỊCH SPAM ZALO cho admin (view widget trên form).
 * Hiển thị LIVE (tick 1s): trạng thái (Đang chờ / Đang chạy / Đã kết thúc),
 * đồng hồ đếm ngược, giờ bắt đầu → giờ kết thúc, thời gian đã chạy, và
 * % hoàn thành (đã báo cáo / tổng phải làm).
 * Đọc trực tiếp record.data nên tự đồng bộ khi admin bấm BẮT ĐẦU / KẾT THÚC.
 */
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class VdBroadcastStatus extends Component {
    static template = "vd_crm_lead.VdBroadcastStatus";
    static props = { ...standardWidgetProps };

    setup() {
        this.state = useState({ now: Date.now() });
        this._t = setInterval(() => { this.state.now = Date.now(); }, 1000);
        onWillUnmount(() => clearInterval(this._t));
    }

    get d() { return this.props.record.data; }
    get startMs() {
        const s = this.d.start_datetime;
        return s && s.toMillis ? s.toMillis() : null;
    }
    get windowMin() { return this.d.window_minutes || 30; }
    get endMs() {
        return this.startMs != null ? this.startMs + this.windowMin * 60000 : null;
    }
    get status() {
        if (!this.d.active) return "ended";
        if (this.startMs == null) return "waiting";
        return this.state.now < this.startMs ? "waiting" : "running";
    }
    get isOverdue() {
        return this.status === "running" && this.endMs != null && this.state.now >= this.endMs;
    }
    get countdownMs() {
        if (this.status === "waiting") return Math.max(0, this.startMs - this.state.now);
        if (this.status === "running") {
            return this.isOverdue
                ? this.state.now - this.endMs
                : Math.max(0, this.endMs - this.state.now);
        }
        return 0;
    }
    get countdownLabel() { return this._fmt(this.countdownMs); }
    get elapsedLabel() {
        if (this.startMs == null || this.state.now < this.startMs) return "0:00";
        return this._fmt(this.state.now - this.startMs);
    }
    _fmt(ms) {
        let s = Math.floor((ms || 0) / 1000);
        const h = Math.floor(s / 3600); s -= h * 3600;
        const m = Math.floor(s / 60); s -= m * 60;
        const pad = (n) => String(n).padStart(2, "0");
        return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
    }
    _fmtDt(dt) {
        return dt && dt.toFormat ? dt.toFormat("dd/MM HH:mm") : "—";
    }
    get startLabel() { return this._fmtDt(this.d.start_datetime); }
    get endLabel() {
        const s = this.d.start_datetime;
        return s && s.plus ? s.plus({ minutes: this.windowMin }).toFormat("dd/MM HH:mm") : "—";
    }
    get donePct() { return this.d.vd_progress_pct || 0; }
    get doneCount() { return this.d.done_count || 0; }
    get targetCount() { return this.d.target_count || 0; }
    get missingCount() { return this.d.vd_missing_count || 0; }
    get timePct() {
        if (this.status === "ended") return 100;
        if (this.status !== "running" || this.startMs == null || this.endMs == null) return 0;
        const p = (this.state.now - this.startMs) / (this.endMs - this.startMs) * 100;
        return Math.max(0, Math.min(100, Math.round(p)));
    }
}

registry.category("view_widgets").add("vd_broadcast_status", {
    component: VdBroadcastStatus,
});
