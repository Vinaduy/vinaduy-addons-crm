/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class VdElearningOverview extends Component {
    static template = "vd_elearning.Overview";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ zones: [], isAdmin: false, loading: true });
        this.dragData = null;
        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        const data = await this.orm.call("slide.channel", "vd_get_overview", []);
        this.state.zones = data.zones;
        this.state.isAdmin = data.is_admin;
        this.state.loading = false;
    }

    openCourse(course) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "slide.channel",
            res_id: course.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newCourse(zoneKey) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "slide.channel",
            views: [[false, "form"]],
            target: "current",
            context: { default_vd_role_zone: zoneKey },
        });
    }

    // ---------- KEO - THA (chi admin) ----------
    onDragStart(ev, course, zone) {
        if (!this.state.isAdmin) return;
        this.dragData = { zoneKey: zone.key, id: course.id };
        ev.dataTransfer.effectAllowed = "move";
        ev.currentTarget.classList.add("o_vd_dragging");
    }

    onDragEnd(ev) {
        ev.currentTarget.classList.remove("o_vd_dragging");
    }

    onDragOver(ev) {
        if (!this.state.isAdmin) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }

    async onDrop(ev, targetCourse, zone) {
        if (!this.state.isAdmin || !this.dragData) return;
        ev.preventDefault();
        if (this.dragData.zoneKey !== zone.key) return;
        const list = zone.courses;
        const from = list.findIndex((c) => c.id === this.dragData.id);
        const to = list.findIndex((c) => c.id === targetCourse.id);
        this.dragData = null;
        if (from < 0 || to < 0 || from === to) return;
        const [moved] = list.splice(from, 1);
        list.splice(to, 0, moved);
        await this.orm.call("slide.channel", "vd_save_order", [
            zone.key,
            list.map((c) => c.id),
        ]);
    }
}

registry.category("actions").add("vd_elearning_overview", VdElearningOverview);
