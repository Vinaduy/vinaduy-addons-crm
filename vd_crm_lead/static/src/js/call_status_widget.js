/** @odoo-module **/
/**
 * Call status widget for the lead form.
 *
 * Shows one of 4 states based on `vd_active_call_state` and lead.phone:
 *   idle      → "Sẵn sàng gọi"
 *   no_phone  → "Thiếu SĐT"
 *   ringing   → "Đang đổ chuông…"   (call started but customer hasn't answered)
 *   in_call   → "Đang gọi · M:SS"   (live timer, ticks every second)
 *
 * Realtime update: subscribes to bus.bus 'vd_stringee_call_state' and reloads
 * the record when a relevant notification arrives. Also polls every 2s while
 * a call is active as a safety net in case the bus push is lost.
 */
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class VdCallStatusWidget extends Component {
    static template = "vd_crm_lead.CallStatusWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.busService = useService("bus_service");
        this.state = useState({ elapsed: 0 });

        // Modern Odoo 18 bus API. Subscribe by type string.
        this._busCallback = this._onBusMessage.bind(this);
        this.busService.subscribe("vd_stringee_call_state", this._busCallback);
        this.busService.start();

        onMounted(() => {
            this._tick();
            this._tickerId = setInterval(() => this._tick(), 1000);
            // Polling fallback — refresh record every 2s while a call is active.
            this._pollerId = setInterval(() => this._maybePoll(), 2000);
        });
        onWillUnmount(() => {
            if (this._tickerId) clearInterval(this._tickerId);
            if (this._pollerId) clearInterval(this._pollerId);
            this.busService.unsubscribe("vd_stringee_call_state", this._busCallback);
        });
    }

    _tick() {
        const ans = this.props.record.data.vd_active_call_answer_time;
        if (!ans || this.statusType !== "in_call") {
            this.state.elapsed = 0;
            return;
        }
        const start = ans.ts ? ans.ts : new Date(ans).getTime();
        this.state.elapsed = Math.max(0, Math.floor((Date.now() - start) / 1000));
    }

    async _maybePoll() {
        // Only poll when we're showing a transient state — avoids load on idle records.
        const t = this.statusType;
        if (t === "ringing" || t === "in_call") {
            try {
                await this.props.record.load();
            } catch (e) {
                // Record might be unloading; ignore.
            }
        }
    }

    _onBusMessage(payload) {
        if (payload && payload.lead_id === this.props.record.resId) {
            this.props.record.load();
        }
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
        if (s === "answered") return "in_call";
        if (s === "draft" || s === "initiated" || s === "ringing") return "ringing";
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
