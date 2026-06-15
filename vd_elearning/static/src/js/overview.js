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
        this.state = useState({ zones: [], loading: true });
        onWillStart(async () => {
            this.state.zones = await this.orm.call("slide.channel", "vd_get_overview", []);
            this.state.loading = false;
        });
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
}

registry.category("actions").add("vd_elearning_overview", VdElearningOverview);
