/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StringeeDialer extends Component {
    static template = "vd_stringee.Dialer";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        this.notification = useService("notification");
        this.state = useState({ open: false, number: "", inCall: false });
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    async onCall() {
        const number = (this.state.number || "").trim();
        if (!number) {
            return;
        }
        try {
            await this.stringee.call(number);
            this.state.inCall = true;
        } catch (e) {
            this.notification.add(e.message || "Call failed", { type: "danger" });
        }
    }

    onHangup() {
        this.stringee.hangup();
        this.state.inCall = false;
    }
}

export const systrayItem = { Component: StringeeDialer };
registry.category("systray").add("vd_stringee.dialer", systrayItem, { sequence: 100 });
