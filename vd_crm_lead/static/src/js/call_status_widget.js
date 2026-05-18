/** @odoo-module **/
/**
 * Call status widget for the lead form.
 *
 * State machine on the UI side:
 *   idle      → "Sẵn sàng gọi"               (no active call)
 *   no_phone  → "Thiếu SĐT"                  (no phone, no active call)
 *   ringing   → "Đang đổ chuông…"            (state ∈ {draft, initiated, ringing})
 *   in_call   → "Đang gọi · M:SS"            (state == answered AND answer_time set)
 *
 * Timer only ticks during in_call. When state moves to a terminal value,
 * fires a toast (decline / no-answer / busy / etc.) using the message that
 * the server-side broadcast included.
 */
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const RINGING_STATES = new Set(["draft", "initiated", "ringing"]);
const TERMINAL_STATES = new Set([
    "ended", "no_answer", "busy", "declined", "cancelled", "failed",
]);

export class VdCallStatusWidget extends Component {
    static template = "vd_crm_lead.CallStatusWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.busService = useService("bus_service");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({ elapsed: 0 });
        this._lastSeenState = null;
        this._ringStartedAt = null;

        this._busCallback = this._onBusMessage.bind(this);
        this.busService.subscribe("vd_stringee_call_state", this._busCallback);
        this.busService.start();

        onMounted(() => {
            this._lastSeenState = this.callState;
            this._tick();
            this._tickerId = setInterval(() => this._tick(), 1000);
            this._pollerId = setInterval(() => this._maybePoll(), 2000);
        });
        onWillUnmount(() => {
            if (this._tickerId) clearInterval(this._tickerId);
            if (this._pollerId) clearInterval(this._pollerId);
            this.busService.unsubscribe("vd_stringee_call_state", this._busCallback);
        });
    }

    _tick() {
        // CRITICAL: timer only runs when state is exactly "answered" AND we
        // actually have an answer_time. Never count seconds during ringing.
        const data = this.props.record.data;
        if (data.vd_active_call_state !== "answered" || !data.vd_active_call_answer_time) {
            if (this.state.elapsed !== 0) this.state.elapsed = 0;
            return;
        }
        const ans = data.vd_active_call_answer_time;
        const start = ans.ts ? ans.ts : new Date(ans).getTime();
        this.state.elapsed = Math.max(0, Math.floor((Date.now() - start) / 1000));
    }

    async _maybePoll() {
        // Only poll while there's a transient active call — avoids load on idle records.
        const s = this.callState;
        if (RINGING_STATES.has(s) || s === "answered") {
            try {
                await this.props.record.load();
            } catch (e) {
                // record might be unloading
            }
            // SAFETY: nếu kẹt RINGING > 60s (Stringee timeout = 50s + buffer 10s)
            // → call orm để force finalize (chặn UI kẹt "Đang đổ chuông")
            if (RINGING_STATES.has(s)) {
                const ringStart = this._ringStartedAt || Date.now();
                if (!this._ringStartedAt) this._ringStartedAt = ringStart;
                if (Date.now() - ringStart > 60_000) {
                    this._ringStartedAt = null;
                    try {
                        await this.orm.call(
                            "stringee.call", "cron_finalize_stale_calls", [],
                        );
                        await this.props.record.load();
                    } catch (_e) {}
                }
            } else {
                this._ringStartedAt = null;
            }
        } else {
            this._ringStartedAt = null;
        }
    }

    _onBusMessage(payload) {
        if (!payload || payload.lead_id !== this.props.record.resId) {
            return;
        }
        // Show end-reason toast on transition to terminal
        if (TERMINAL_STATES.has(payload.state) && payload.terminal_message) {
            const type = payload.state === "ended" ? "info"
                       : payload.state === "declined" ? "warning"
                       : "warning";
            this.notification.add(payload.terminal_message, { type, sticky: false });
        }
        this.props.record.load();
    }

    get callState() {
        return this.props.record.data.vd_active_call_state || "";
    }

    get hasPhone() {
        const d = this.props.record.data;
        return !!(d.phone || d.mobile);
    }

    get statusType() {
        const s = this.callState;
        if (s === "answered" && this.props.record.data.vd_active_call_answer_time) {
            return "in_call";
        }
        if (RINGING_STATES.has(s)) return "ringing";
        if (!this.hasPhone) return "no_phone";
        return "idle";
    }

    get formatted() {
        const m = Math.floor(this.state.elapsed / 60);
        const s = this.state.elapsed % 60;
        return `${m}:${s.toString().padStart(2, "0")}`;
    }
}

registry.category("fields").add("vd_call_status", {
    component: VdCallStatusWidget,
    supportedTypes: ["char", "boolean", "selection"],
});

/* ============ COMPACT TIMER: chỉ hiện "M:SS" tăng dần khi đã answered ============
   Dùng inline trong banner popup hoặc bất kỳ nơi nào muốn chỉ thấy đếm giây. */
export class VdCallTimerWidget extends Component {
    static template = "vd_crm_lead.CallTimer";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ elapsed: 0 });
        onMounted(() => {
            this._tick();
            this._tickerId = setInterval(() => this._tick(), 1000);
        });
        onWillUnmount(() => {
            if (this._tickerId) clearInterval(this._tickerId);
        });
    }

    _tick() {
        const data = this.props.record.data;
        if (data.vd_active_call_state !== "answered" || !data.vd_active_call_answer_time) {
            if (this.state.elapsed !== 0) this.state.elapsed = 0;
            return;
        }
        const ans = data.vd_active_call_answer_time;
        const start = ans.ts ? ans.ts : new Date(ans).getTime();
        this.state.elapsed = Math.max(0, Math.floor((Date.now() - start) / 1000));
    }

    get formatted() {
        const m = Math.floor(this.state.elapsed / 60);
        const s = this.state.elapsed % 60;
        return `${m}:${s.toString().padStart(2, "0")}`;
    }
}

registry.category("fields").add("vd_call_timer", {
    component: VdCallTimerWidget,
    supportedTypes: ["char", "boolean", "selection"],
});
