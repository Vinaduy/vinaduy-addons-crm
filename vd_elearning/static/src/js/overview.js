/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, useState } from "@odoo/owl";

// ---- Popup nhap ten (dung cho them khoa hoc / them - doi ten lo trinh) ----
export class VdInputDialog extends Component {
    static template = "vd_elearning.InputDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        label: String,
        name: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        confirmLabel: { type: String, optional: true },
        withPath: { type: Boolean, optional: true },
        paths: { type: Array, optional: true },
        onConfirm: Function,
    };
    setup() {
        this.state = useState({ name: this.props.name || "", pathId: false });
    }
    get canConfirm() {
        return !!(this.state.name || "").trim() && (!this.props.withPath || !!this.state.pathId);
    }
    confirm() {
        if (!this.canConfirm) {
            return;
        }
        this.props.onConfirm({
            name: this.state.name.trim(),
            pathId: parseInt(this.state.pathId, 10) || false,
        });
        this.props.close();
    }
}

export class VdElearningOverview extends Component {
    static template = "vd_elearning.Overview";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
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
                courses: z ? this._flatCourses(z) : [],
                locked: true,
            };
        }
        this.state.loading = false;
    }

    _flatCourses(zone) {
        return (zone.paths || []).reduce((acc, p) => acc.concat(p.courses), []);
    }

    // ---------- node theo dong ----------
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

    // NV dang hoc trong 1 lo trinh (theo khoa hien tai cua ho)
    pathLearners(path, zone) {
        const ids = new Set(path.courses.map((c) => c.id));
        return (zone.employees || [])
            .filter((e) => ids.has(e.course_id))
            .map((e) => {
                const cur = path.courses.find((c) => c.id === e.course_id);
                return {
                    id: e.id,
                    name: e.name,
                    current: cur ? cur.name : "",
                    start: e.start || "-",
                    end: e.end || "-",
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
            courses: z ? this._flatCourses(z) : [],
            locked: false,
        };
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

    // ---------- POPUP ----------
    openAddCourse(zone) {
        this.dialog.add(VdInputDialog, {
            title: "Thêm khóa học",
            label: "Tên khóa học",
            placeholder: "VD: A3 - Thi công",
            confirmLabel: "Tạo khóa học",
            withPath: true,
            paths: zone.paths,
            onConfirm: async ({ name, pathId }) => {
                await this.orm.create("slide.channel", [
                    {
                        name,
                        channel_type: "training",
                        vd_role_zone: zone.key,
                        vd_path_id: pathId,
                    },
                ]);
                await this.reload();
            },
        });
    }

    openAddPath(zoneKey) {
        this.dialog.add(VdInputDialog, {
            title: "Thêm lộ trình",
            label: "Tên lộ trình",
            placeholder: "VD: Lộ trình nâng cao",
            confirmLabel: "Tạo lộ trình",
            onConfirm: async ({ name }) => {
                await this.orm.create("vd.learning.path", [
                    { name, zone: zoneKey, sequence: 99 },
                ]);
                await this.reload();
            },
        });
    }

    renamePath(path) {
        this.dialog.add(VdInputDialog, {
            title: "Đổi tên lộ trình",
            label: "Tên lộ trình",
            name: path.name,
            confirmLabel: "Lưu",
            onConfirm: async ({ name }) => {
                await this.orm.write("vd.learning.path", [path.id], { name });
                await this.reload();
            },
        });
    }

    // ---------- KEO - THA (trong & giua cac lo trinh) ----------
    onDragStart(ev, course, zoneKey, pathId) {
        if (!this.state.isAdmin) return;
        this.dragData = { zoneKey, id: course.id, pathId };
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

    async onDrop(ev, targetCourse, zoneKey, pathId) {
        if (!this.state.isAdmin || !this.dragData) return;
        ev.preventDefault();
        ev.stopPropagation();
        const d = this.dragData;
        this.dragData = null;
        if (d.zoneKey !== zoneKey || d.id === targetCourse.id) return;
        await this._applyMove(d, zoneKey, pathId, targetCourse.id);
    }

    async onTrackDrop(ev, zoneKey, pathId) {
        if (!this.state.isAdmin || !this.dragData) return;
        ev.preventDefault();
        const d = this.dragData;
        this.dragData = null;
        if (d.zoneKey !== zoneKey) return;
        await this._applyMove(d, zoneKey, pathId, null);
    }

    async _applyMove(d, zoneKey, targetPathId, targetCourseId) {
        const zone = this.state.zones.find((z) => z.key === zoneKey);
        if (!zone) return;
        const srcPath = zone.paths.find((p) => p.id === d.pathId);
        const tgtPath = zone.paths.find((p) => p.id === targetPathId);
        if (!srcPath || !tgtPath) return;
        const from = srcPath.courses.findIndex((c) => c.id === d.id);
        if (from < 0) return;
        const [moved] = srcPath.courses.splice(from, 1);
        let to = tgtPath.courses.length;
        if (targetCourseId) {
            const ti = tgtPath.courses.findIndex((c) => c.id === targetCourseId);
            to = ti < 0 ? tgtPath.courses.length : ti;
        }
        tgtPath.courses.splice(to, 0, moved);
        const crossPath = d.pathId !== targetPathId;
        if (crossPath) {
            await this.orm.write("slide.channel", [moved.id], { vd_path_id: targetPathId });
        }
        await this.orm.call("slide.channel", "vd_save_order", [
            zoneKey,
            tgtPath.courses.map((c) => c.id),
        ]);
        if (crossPath) {
            await this.orm.call("slide.channel", "vd_save_order", [
                zoneKey,
                srcPath.courses.map((c) => c.id),
            ]);
        }
    }
}

registry.category("actions").add("vd_elearning_overview", VdElearningOverview);
