/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

// Kich thuoc mot "o" tren ban do game.
const CELL_W = 230;
const CELL_H = 168;
const MAX_COLS = 6;

export class VdElearningOverview extends Component {
    static template = "vd_elearning.Overview";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ zones: [], isAdmin: false, selectedEmp: null, loading: true });
        this.dragData = null;
        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        const data = await this.orm.call("slide.channel", "vd_get_overview", []);
        this.state.zones = data.zones;
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

    // ---------- DUNG BAN DO GAME (serpentine) ----------
    // employees: danh sach NV co {id, name, course_id} de gan avatar vao node.
    buildMap(courses, employees) {
        const n = courses.length;
        const cols = Math.max(1, Math.min(MAX_COLS, n));
        const rows = Math.ceil(n / cols) || 1;
        const byCourse = {};
        for (const e of employees || []) {
            if (!e.courseId && e.course_id) {
                e = { ...e, courseId: e.course_id };
            }
            const cid = e.courseId !== undefined ? e.courseId : e.course_id;
            if (!cid) continue;
            (byCourse[cid] = byCourse[cid] || []).push(e);
        }
        const nodes = courses.map((c, i) => {
            const row = Math.floor(i / cols);
            const inRow = i % cols;
            const col = row % 2 === 0 ? inRow : cols - 1 - inRow;
            return {
                course: c,
                idx: i,
                n: i + 1,
                kind: i === 0 ? "start" : i === n - 1 ? "boss" : "normal",
                x: col * CELL_W + CELL_W / 2,
                y: row * CELL_H + CELL_H / 2,
                employees: byCourse[c.id] || [],
            };
        });
        const path = nodes
            .map((nd, i) => `${i === 0 ? "M" : "L"} ${nd.x} ${nd.y}`)
            .join(" ");
        return {
            nodes,
            path,
            width: cols * CELL_W,
            height: rows * CELL_H,
        };
    }

    zoneMap(zone) {
        return this.buildMap(zone.courses, zone.employees);
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
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "slide.channel",
            views: [[false, "form"]],
            target: "current",
            context: { default_vd_role_zone: zoneKey },
        });
    }

    selectEmp(zone, ev) {
        const id = parseInt(ev.target.value, 10);
        if (!id) {
            return;
        }
        const emp = zone.employees.find((e) => e.id === id);
        this.state.selectedEmp = {
            id,
            name: emp ? emp.name : "",
            courseId: emp ? emp.course_id : false,
            courses: zone.courses,
            locked: false,
        };
    }

    backToAdmin() {
        this.state.selectedEmp = null;
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
