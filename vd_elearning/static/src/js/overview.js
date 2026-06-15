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
        this.state = useState({
            zones: [],
            report: [],
            isAdmin: false,
            tab: "sales",
            selectedEmp: null,
            loading: true,
        });
        this.dragData = null;
        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        const data = await this.orm.call("slide.channel", "vd_get_overview", []);
        this.state.zones = data.zones;
        this.state.report = data.report || [];
        this.state.isAdmin = data.is_admin;
        if (!data.is_admin && data.me && data.me.zone_key) {
            const z = data.zones.find((zn) => zn.key === data.me.zone_key);
            this.state.selectedEmp = {
                id: data.me.id,
                name: data.me.name,
                courseId: data.me.course_id,
                courses: z ? z.courses : [],
                locked: true,
            };
        }
        this.state.loading = false;
    }

    // ---------- DUNG NODE THEO DONG (flex-wrap) ----------
    // employees: danh sach NV co {id, name, course_id} de gan avatar vao node.
    trackNodes(courses, employees) {
        const byCourse = {};
        for (const e of employees || []) {
            const cid = e.courseId !== undefined ? e.courseId : e.course_id;
            if (!cid) continue;
            (byCourse[cid] = byCourse[cid] || []).push({ id: e.id, name: e.name });
        }
        const n = courses.length;
        return courses.map((c, i) => {
            const all = byCourse[c.id] || [];
            return {
                course: c,
                n: i + 1,
                kind: i === n - 1 ? "boss" : "normal",
                riders: all.slice(0, 3),
                moreRiders: Math.max(0, all.length - 3),
            };
        });
    }

    get studentNodes() {
        const s = this.state.selectedEmp;
        return this.trackNodes(s.courses, [
            { id: s.id, name: s.name, courseId: s.courseId },
        ]);
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    get activeZone() {
        return this.state.zones.find((z) => z.key === this.state.tab);
    }

    viewEmployee(row) {
        const z = this.state.zones.find((zn) => zn.key === row.zone_key);
        this.state.selectedEmp = {
            id: row.id,
            name: row.name,
            courseId: false,
            courses: z ? z.courses : [],
            locked: false,
        };
    }

    studentMap() {
        const s = this.state.selectedEmp;
        return this.buildMap(s.courses, [
            { id: s.id, name: s.name, courseId: s.courseId },
        ]);
    }

    // ---------- DIEU HUONG ----------
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
        const z = this.state.zones.find((zn) => zn.key === zoneKey);
        const firstPath = z && z.paths && z.paths.length ? z.paths[0].id : false;
        const ctx = { default_vd_role_zone: zoneKey };
        if (firstPath) {
            ctx.default_vd_path_id = firstPath;
        }
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "slide.channel",
                views: [[false, "form"]],
                target: "current",
                context: ctx,
            },
            { onClose: () => this.reload() }
        );
    }

    newPath(zoneKey) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: "Lộ trình mới",
                res_model: "vd.learning.path",
                views: [[false, "form"]],
                target: "new",
                context: { default_zone: zoneKey },
            },
            { onClose: () => this.reload() }
        );
    }

    // dropdown chon nhan vien (toan cuc, theo state.report)
    selectEmpGlobal(ev) {
        const id = parseInt(ev.target.value, 10);
        ev.target.value = "";
        if (!id) {
            return;
        }
        const row = this.state.report.find((r) => r.id === id);
        if (row) {
            this.viewEmployee(row);
        }
    }

    backToAdmin() {
        this.state.selectedEmp = null;
    }

    // ---------- KEO - THA trong 1 lo trinh (chi admin) ----------
    onDragStart(ev, course, zoneKey) {
        if (!this.state.isAdmin) return;
        this.dragData = { zoneKey, id: course.id };
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

    async onDrop(ev, targetCourse, list, zoneKey) {
        if (!this.state.isAdmin || !this.dragData) return;
        ev.preventDefault();
        if (this.dragData.zoneKey !== zoneKey) return;
        const from = list.findIndex((c) => c.id === this.dragData.id);
        const to = list.findIndex((c) => c.id === targetCourse.id);
        this.dragData = null;
        if (from < 0 || to < 0 || from === to) return;
        const [moved] = list.splice(from, 1);
        list.splice(to, 0, moved);
        await this.orm.call("slide.channel", "vd_save_order", [
            zoneKey,
            list.map((c) => c.id),
        ]);
    }
}

registry.category("actions").add("vd_elearning_overview", VdElearningOverview);
