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
 * Listens to bus channel `vd_stringee_call_state` and reloads the record
 * when a relevant notification arrives, so the UI updates without manual refresh.
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

        this._busHandler = this._onBusNotification.bind(this);
        this.busService.addEventListener("notification", this._busHandler);

        onMounted(() => {
            this._tick();
            this._intervalId = setInterval(() => this._tick(), 1000);
        });
        onWillUnmount(() => {
            if (this._intervalId) clearInterval(this._intervalId);
            this.busService.removeEventListener("notification", this._busHandler);
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

    _onBusNotification({ detail: notifs }) {
        const recId = this.props.record.resId;
        for (const { type, payload } of notifs || []) {
            if (type === "vd_stringee_call_state" && payload && payload.lead_id === recId) {
                this.props.record.load();
            }
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
