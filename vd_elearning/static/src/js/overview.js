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

// ---- Popup gan nhan vien vao lo trinh (tich chon) ----
export class VdAssignDialog extends Component {
    static template = "vd_elearning.AssignDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        candidates: Array,
        onConfirm: Function,
    };
    setup() {
        const sel = {};
        for (const c of this.props.candidates) {
            sel[c.id] = !!c.assigned;
        }
        this.state = useState({ search: "", sel });
    }
    get filtered() {
        const q = this.state.search.trim().toLowerCase();
        if (!q) {
            return this.props.candidates;
        }
        return this.props.candidates.filter(
            (c) =>
                (c.name || "").toLowerCase().includes(q) ||
                (c.team || "").toLowerCase().includes(q)
        );
    }
    get selCount() {
        return Object.values(this.state.sel).filter(Boolean).length;
    }
    toggle(id) {
        this.state.sel[id] = !this.state.sel[id];
    }
    confirm() {
        const ids = this.props.candidates
            .filter((c) => this.state.sel[c.id])
            .map((c) => c.id);
        this.props.onConfirm(ids);
        this.props.close();
    }
}

// ---- Popup full man hinh: soan noi dung + cau hoi thi cua khoa hoc ----
export class VdCourseDialog extends Component {
    static template = "vd_elearning.CourseDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        channelId: Number,
        editable: Boolean,
        data: Object,
        onSaved: Function,
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._k = 0;
        const data = this.props.data || {};
        this.state = useState({
            contents: (data.contents || []).map((c) => ({
                _k: this.key(), id: c.id, name: c.name, body: c.body,
            })),
            questions: (data.questions || []).map((q) => ({
                _k: this.key(), id: q.id, text: q.text,
                answers: (q.answers || []).map((a) => ({
                    _k: this.key(), id: a.id, text: a.text, is_correct: a.is_correct,
                })),
            })),
            saving: false,
        });
    }
    key() {
        return "k" + this._k++;
    }
    addContent() {
        this.state.contents.push({ _k: this.key(), id: false, name: "", body: "" });
    }
    delContent(c) {
        const i = this.state.contents.indexOf(c);
        if (i >= 0) this.state.contents.splice(i, 1);
    }
    addQuestion() {
        this.state.questions.push({
            _k: this.key(), id: false, text: "",
            answers: [
                { _k: this.key(), id: false, text: "", is_correct: true },
                { _k: this.key(), id: false, text: "", is_correct: false },
            ],
        });
    }
    delQuestion(q) {
        const i = this.state.questions.indexOf(q);
        if (i >= 0) this.state.questions.splice(i, 1);
    }
    addAnswer(q) {
        q.answers.push({ _k: this.key(), id: false, text: "", is_correct: false });
    }
    delAnswer(q, a) {
        const i = q.answers.indexOf(a);
        if (i >= 0) q.answers.splice(i, 1);
    }
    toggleCorrect(a) {
        a.is_correct = !a.is_correct;
    }
    async save() {
        if (this.state.saving) return;
        for (const q of this.state.questions) {
            if (!q.text.trim()) continue;
            const corr = q.answers.filter((a) => a.is_correct).length;
            if (q.answers.length < 2 || corr === 0 || corr === q.answers.length) {
                this.notification.add(
                    "Mỗi câu hỏi cần ít nhất 1 đáp án đúng và 1 đáp án sai: " + q.text,
                    { type: "danger" }
                );
                return;
            }
        }
        this.state.saving = true;
        try {
            await this.orm.call("slide.channel", "vd_course_save", [
                this.props.channelId,
                this.state.contents.map((c) => ({ id: c.id, name: c.name, body: c.body })),
                this.state.questions.map((q) => ({
                    id: q.id, text: q.text,
                    answers: q.answers.map((a) => ({
                        id: a.id, text: a.text, is_correct: a.is_correct,
                    })),
                })),
            ]);
            await this.props.onSaved();
            this.props.close();
        } catch (e) {
            this.state.saving = false;
            throw e;
        }
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
                paths: z ? z.paths : [],
                locked: true,
            };
        }
        this.state.loading = false;
    }

    // ---------- node theo dong ----------
    // hideCourseId: khoa khong hien rider (vd. khoa dau "Co ban" o giao dien admin)
    trackNodes(courses, employees, hideCourseId) {
        const byCourse = {};
        for (const e of employees || []) {
            const cid = e.courseId !== undefined ? e.courseId : e.course_id;
            if (!cid || cid === hideCourseId) continue;
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

    // khoa dau cua lo trinh dau (entry) — an rider tren day o giao dien admin
    zoneEntryId(zone) {
        const p0 = (zone.paths || [])[0];
        const c0 = p0 && p0.courses[0];
        return c0 ? c0.id : 0;
    }

    get studentEmp() {
        const s = this.state.selectedEmp;
        return [{ id: s.id, name: s.name, courseId: s.courseId }];
    }
    studentPathNodes(path) {
        return this.trackNodes(path.courses, this.studentEmp);
    }
    get studentCourseCount() {
        return (this.state.selectedEmp.paths || []).reduce(
            (n, p) => n + p.courses.length, 0
        );
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
            courseId: row.current_id || false,
            paths: z ? z.paths : [],
            locked: false,
        };
    }

    async openCourse(course) {
        const data = await this.orm.call("slide.channel", "vd_course_load", [course.id]);
        this.dialog.add(VdCourseDialog, {
            title: "Khóa học - " + course.name,
            channelId: course.id,
            editable: this.state.isAdmin,
            data,
            onSaved: async () => {
                await this.reload();
            },
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

    async openAssign(path) {
        const candidates = await this.orm.call(
            "slide.channel", "vd_path_candidates", [path.id]
        );
        this.dialog.add(VdAssignDialog, {
            title: "Gán nhân viên - " + path.name,
            candidates,
            onConfirm: async (userIds) => {
                await this.orm.call("slide.channel", "vd_set_path_members", [
                    path.id,
                    userIds,
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
