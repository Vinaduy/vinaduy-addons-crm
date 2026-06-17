/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState, markup } from "@odoo/owl";

// ---- Trinh soan thao van ban (WYSIWYG) kieu Word/PowerPoint ----
export class VdRichEditor extends Component {
    static template = "vd_elearning.RichEditor";
    static props = { html: String, onChange: Function };
    setup() {
        this.ref = useRef("editable");
        onMounted(() => {
            this.ref.el.innerHTML = this.props.html || "";
        });
    }
    exec(cmd, val = null) {
        this.ref.el.focus();
        document.execCommand(cmd, false, val);
        this.emit();
    }
    emit() {
        this.props.onChange(this.ref.el.innerHTML);
    }
    block(ev) {
        const v = ev.target.value;
        if (v) this.exec("formatBlock", v);
        ev.target.value = "";
    }
    fontSize(ev) {
        const v = ev.target.value;
        if (v) this.exec("fontSize", v);
        ev.target.value = "";
    }
    color(ev) {
        this.exec("foreColor", ev.target.value);
    }
    highlight(ev) {
        this.exec("hiliteColor", ev.target.value);
    }
    addLink() {
        const url = window.prompt("Nhập đường dẫn (URL):", "https://");
        if (url) this.exec("createLink", url);
    }
    addTable() {
        const cols = parseInt(window.prompt("Số cột?", "3"), 10) || 0;
        const rows = parseInt(window.prompt("Số dòng (gồm dòng tiêu đề)?", "3"), 10) || 0;
        if (!cols || !rows) return;
        let h = '<table style="width:100%;border-collapse:collapse;margin:10px 0;border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(32,36,58,.1);">';
        for (let r = 0; r < rows; r++) {
            h += "<tr>";
            for (let c = 0; c < cols; c++) {
                if (r === 0) {
                    h += '<th style="border:1px solid #e2dcce;padding:8px 10px;background:linear-gradient(135deg,#2b3350,#3a4063);color:#fff;text-align:left;font-size:13px;">Tiêu đề</th>';
                } else {
                    h += '<td style="border:1px solid #e6e1d3;padding:7px 10px;' + (r % 2 === 0 ? 'background:#faf9f3;' : '') + '">&#8203;</td>';
                }
            }
            h += "</tr>";
        }
        h += "</table><p>&#8203;</p>";
        this.exec("insertHTML", h);
    }
    insertImage(ev) {
        const file = ev.target.files[0];
        ev.target.value = "";
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            this.ref.el.focus();
            document.execCommand(
                "insertHTML", false,
                '<img src="' + reader.result + '" style="max-width:100%;border-radius:10px;margin:8px 0;box-shadow:0 4px 14px rgba(32,36,58,.15);"/><p>&#8203;</p>'
            );
            this.emit();
        };
        reader.readAsDataURL(file);
    }
    insertVideo() {
        const url = window.prompt("Dán link video (YouTube / Vimeo / MP4):", "");
        if (!url) return;
        let html;
        const yt = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|shorts\/))([\w-]+)/);
        const vm = url.match(/vimeo\.com\/(\d+)/);
        if (yt) {
            html = '<div style="position:relative;padding-top:56.25%;margin:10px 0;border-radius:10px;overflow:hidden;"><iframe src="https://www.youtube.com/embed/' + yt[1] + '" style="position:absolute;inset:0;width:100%;height:100%;border:0;" allowfullscreen="allowfullscreen"></iframe></div>';
        } else if (vm) {
            html = '<div style="position:relative;padding-top:56.25%;margin:10px 0;border-radius:10px;overflow:hidden;"><iframe src="https://player.vimeo.com/video/' + vm[1] + '" style="position:absolute;inset:0;width:100%;height:100%;border:0;" allowfullscreen="allowfullscreen"></iframe></div>';
        } else {
            html = '<video controls="controls" src="' + url + '" style="max-width:100%;border-radius:10px;margin:8px 0;"></video>';
        }
        this.exec("insertHTML", html + "<p>&#8203;</p>");
    }
    template(ev) {
        const v = ev.target.value;
        ev.target.value = "";
        const T = {
            banner:
                '<div style="background:linear-gradient(135deg,#5b4be6,#7c3aed);color:#fff;padding:18px 22px;border-radius:14px;margin:10px 0;box-shadow:0 8px 22px rgba(91,75,230,.3);"><div style="font-size:12px;letter-spacing:2px;opacity:.85;font-weight:700;">CHƯƠNG</div><div style="font-size:22px;font-weight:900;">Tiêu đề chương lớn</div></div>',
            note:
                '<div style="background:#eaf7ef;border-left:5px solid #2e9b54;padding:12px 16px;border-radius:8px;margin:10px 0;"><b>💡 Ghi nhớ:</b> Nhập nội dung quan trọng cần nhấn mạnh ở đây.</div>',
            warn:
                '<div style="background:#fdf2e0;border-left:5px solid #caa14a;padding:12px 16px;border-radius:8px;margin:10px 0;"><b>⚠️ Lưu ý:</b> Nhập điều cần cảnh báo ở đây.</div>',
            two:
                '<div style="display:flex;gap:14px;margin:10px 0;flex-wrap:wrap;"><div style="flex:1;min-width:200px;background:#f6f5ff;border:1px solid #ddd7f5;border-radius:12px;padding:14px;"><b>Cột trái</b><br/>Nội dung...</div><div style="flex:1;min-width:200px;background:#fff8ee;border:1px solid #f0e3c8;border-radius:12px;padding:14px;"><b>Cột phải</b><br/>Nội dung...</div></div>',
            compare:
                '<table style="width:100%;border-collapse:collapse;margin:10px 0;border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(32,36,58,.1);"><tr><th style="border:1px solid #e2dcce;padding:8px 10px;background:linear-gradient(135deg,#2b3350,#3a4063);color:#fff;">Tiêu chí</th><th style="border:1px solid #e2dcce;padding:8px 10px;background:linear-gradient(135deg,#2b3350,#3a4063);color:#fff;">Phương án A</th><th style="border:1px solid #e2dcce;padding:8px 10px;background:linear-gradient(135deg,#2b3350,#3a4063);color:#fff;">Phương án B</th></tr><tr><td style="border:1px solid #e6e1d3;padding:7px 10px;"><b>...</b></td><td style="border:1px solid #e6e1d3;padding:7px 10px;background:#faf9f3;">...</td><td style="border:1px solid #e6e1d3;padding:7px 10px;background:#faf9f3;">...</td></tr></table>',
        };
        if (T[v]) this.exec("insertHTML", T[v] + "<p>&#8203;</p>");
    }
}

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

// ---- Popup nho: cau hinh bai thi (ty le dat, so lan thi lai) ----
export class VdConfigDialog extends Component {
    static template = "vd_elearning.ConfigDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        channelId: Number,
        passPercent: Number,
        maxAttempts: Number,
        examMinutes: Number,
        totalQuestions: Number,
        onSaved: Function,
    };
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            pass: this.props.passPercent,
            max: this.props.maxAttempts,
            minutes: this.props.examMinutes,
        });
    }
    get passCount() {
        const n = this.props.totalQuestions || 0;
        return Math.ceil((n * (parseInt(this.state.pass, 10) || 0)) / 100);
    }
    // Thoi gian hieu luc hien thi: 0 = tu dong 1 phut/cau.
    get effMinutes() {
        const m = parseInt(this.state.minutes, 10) || 0;
        return m > 0 ? m : (this.props.totalQuestions || 0);
    }
    async save() {
        const pass = Math.max(0, Math.min(100, parseInt(this.state.pass, 10) || 0));
        const max = Math.max(0, parseInt(this.state.max, 10) || 0);
        const minutes = Math.max(0, parseInt(this.state.minutes, 10) || 0);
        await this.orm.call("slide.channel", "vd_course_config_save", [
            this.props.channelId, pass, max, minutes,
        ]);
        this.props.onSaved(pass, max, minutes);
        this.props.close();
    }
}

// ---- Popup full man hinh: soan noi dung + cau hoi thi cua khoa hoc ----
export class VdCourseDialog extends Component {
    static template = "vd_elearning.CourseDialog";
    static components = { Dialog, VdRichEditor, VdConfigDialog };
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
        this.dialog = useService("dialog");
        this._k = 0;
        const data = this.props.data || {};
        this.state = useState({
            tab: "content",
            courseName: data.name || "",
            editingName: false,            // dang sua ten khoa hoc (nut but)
            passPercent: data.pass_percent || 80,
            maxAttempts: data.max_attempts || 0,
            examMinutesCfg: data.exam_minutes_cfg || 0,  // cau hinh (0 = auto)
            examMinutes: data.exam_minutes || (data.questions || []).length || 0, // hieu luc
            secondsLeft: 0,                // bo dem nguoc khi thi
            attemptCount: 0,
            editingContent: null, // content dang soan (full man hinh)
            examStarted: false,
            examResult: null, // {score,total,percent,passed, map:{qid:bool}, correct:{qid:[ids]}}
            contents: (data.contents || []).map((c) => ({
                _k: this.key(), id: c.id, name: c.name, body: c.body,
            })),
            questions: (data.questions || []).map((q) => ({
                _k: this.key(), id: q.id, text: q.text,
                answers: (q.answers || []).map((a) => ({
                    _k: this.key(), id: a.id, text: a.text,
                    is_correct: a.is_correct, chosen: false,
                })),
            })),
            saving: false,
        });
        this._examTimer = null;
        onWillUnmount(() => this._stopTimer());
    }
    key() {
        return "k" + this._k++;
    }

    // ---- BO DEM THOI GIAN THI ----
    _stopTimer() {
        if (this._examTimer) {
            clearInterval(this._examTimer);
            this._examTimer = null;
        }
    }
    _startTimer() {
        this._stopTimer();
        const total = (this.state.examMinutes || 0) * 60;
        this.state.secondsLeft = total;
        if (!total) return;
        this._examTimer = setInterval(() => {
            this.state.secondsLeft -= 1;
            if (this.state.secondsLeft <= 0) {
                this.state.secondsLeft = 0;
                this._stopTimer();
                // Het gio -> tu dong nop bai.
                this.submitExam(true);
            }
        }, 1000);
    }
    get timeLeftLabel() {
        const s = Math.max(0, this.state.secondsLeft || 0);
        const m = Math.floor(s / 60);
        const r = s % 60;
        return `${m}:${r < 10 ? "0" : ""}${r}`;
    }
    get timeLow() {
        return (this.state.secondsLeft || 0) <= 60;
    }
    get answeredCount() {
        return this.state.questions.filter((q) => q.answers.some((a) => a.chosen)).length;
    }
    qAnswered(q) {
        return q.answers.some((a) => a.chosen);
    }
    get attemptLabel() {
        const cur = this.state.attemptCount + 1;
        return this.state.maxAttempts
            ? `${cur} / ${this.state.maxAttempts}`
            : `${cur} / không giới hạn`;
    }

    // ---- dieu huong tab ----
    get showContentTab() {
        // hoc vien dang thi (chua nop) -> AN tab noi dung
        return this.props.editable || !this.state.examStarted || !!this.state.examResult;
    }
    setTab(t) {
        if (t === "content" && !this.showContentTab) return;
        this.state.tab = t;
    }

    // ---- HOC VIEN: lam bai thi ----
    startExam() {
        this.state.examStarted = true;
        this.state.examResult = null;
        for (const q of this.state.questions) {
            for (const a of q.answers) a.chosen = false;
        }
        this.state.tab = "exam";
        this._startTimer();
    }
    chooseAnswer(q, a) {
        if (this.props.editable || this.state.examResult) return;
        a.chosen = !a.chosen;
    }
    async submitExam(auto = false) {
        if (this.state.saving || this.state.examResult) return;
        const unanswered = this.state.questions.filter(
            (q) => !q.answers.some((a) => a.chosen)
        ).length;
        // Het gio (auto=true) thi nop luon du con cau trong; nguoc lai canh bao.
        if (unanswered && auto !== true) {
            this.notification.add(
                "Còn " + unanswered + " câu chưa chọn đáp án.", { type: "warning" }
            );
            return;
        }
        this._stopTimer();
        this.state.saving = true;
        try {
            const payload = {};
            for (const q of this.state.questions) {
                payload[String(q.id)] = q.answers.filter((a) => a.chosen).map((a) => a.id);
            }
            const res = await this.orm.call("slide.channel", "vd_course_grade", [
                this.props.channelId, payload,
            ]);
            const map = {}, correct = {};
            for (const r of res.results) {
                map[r.qid] = r.correct;
                correct[r.qid] = r.correct_ids;
            }
            this.state.attemptCount += 1;
            this.state.examResult = {
                score: res.score, total: res.total, percent: res.percent,
                passed: res.passed, passPercent: res.pass_percent, map, correct,
            };
        } finally {
            this.state.saving = false;
        }
    }
    get canRetry() {
        if (this.state.examResult && this.state.examResult.passed) return false;
        return this.state.maxAttempts === 0 || this.state.attemptCount < this.state.maxAttempts;
    }
    openConfig() {
        this.dialog.add(VdConfigDialog, {
            channelId: this.props.channelId,
            passPercent: this.state.passPercent,
            maxAttempts: this.state.maxAttempts,
            examMinutes: this.state.examMinutesCfg,
            totalQuestions: this.state.questions.length,
            onSaved: (pass, max, minutes) => {
                this.state.passPercent = pass;
                this.state.maxAttempts = max;
                this.state.examMinutesCfg = minutes;
                // Hieu luc: 0 -> 1 phut/cau.
                this.state.examMinutes = minutes > 0 ? minutes : this.state.questions.length;
            },
        });
    }
    // ---- Doi ten khoa hoc (nut but tren tieu de) ----
    async saveName() {
        const nm = (this.state.courseName || "").trim();
        if (!nm) {
            this.notification.add("Tên khóa học không được để trống.", { type: "warning" });
            return;
        }
        try {
            await this.orm.call("slide.channel", "vd_course_rename", [this.props.channelId, nm]);
            this.state.courseName = nm;
            this.state.editingName = false;
            await this.props.onSaved();
            this.notification.add("Đã lưu tên khóa học.", { type: "success" });
        } catch (e) {
            this.notification.add("Lưu tên thất bại.", { type: "danger" });
            throw e;
        }
    }
    reviewContent() {
        this.state.examStarted = false;
        this.state.tab = "content";
    }
    retryExam() {
        this.startExam();
    }
    isAnswerCorrect(q, a) {
        const c = this.state.examResult && this.state.examResult.correct[q.id];
        return c ? c.includes(a.id) : false;
    }
    // render noi dung: HTML giu nguyen, text thuong thi xuong dong
    bodyHtml(body) {
        const s = body || "";
        if (/<\/?[a-z][\s\S]*>/i.test(s)) {
            return markup(s);
        }
        const esc = s
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br/>");
        return markup(esc);
    }
    addContent() {
        // Mỗi khóa chỉ 1 nội dung — chỉ tạo khi chưa có (user spec 2026-06-18).
        if (this.state.contents.length) {
            this.state.editingContent = this.state.contents[0];
            return;
        }
        const c = { _k: this.key(), id: false, name: "Nội dung khóa học", body: "" };
        this.state.contents.push(c);
        this.state.editingContent = c;
    }
    openEditor(c) {
        this.state.editingContent = c;
    }
    closeEditor() {
        this.state.editingContent = null;
    }
    onEditorChange(html) {
        if (this.state.editingContent) this.state.editingContent.body = html;
    }
    delContent(c) {
        const i = this.state.contents.indexOf(c);
        if (i >= 0) this.state.contents.splice(i, 1);
        if (this.state.editingContent === c) this.state.editingContent = null;
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
                this.state.courseName,
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
                completedIds: data.me.completed_ids || [],
                paths: z ? z.paths : [],
                locked: true,
            };
        }
        this.state.loading = false;
    }

    // ---------- node theo dong ----------
    // hideCourseId: khoa khong hien rider (vd. khoa dau "Co ban" o giao dien admin)
    // statusMap: {courseId: 'done'|'current'|'locked'} cho giao dien nhan vien
    trackNodes(courses, employees, hideCourseId, statusMap) {
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
                status: (statusMap && statusMap[c.id]) || "",
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
        const s = this.state.selectedEmp;
        const done = new Set(s.completedIds || []);
        const map = {};
        for (const c of path.courses) {
            if (done.has(c.id)) map[c.id] = "done";
            else if (c.id === s.courseId) map[c.id] = "current";
            else map[c.id] = "locked";
        }
        return this.trackNodes(path.courses, this.studentEmp, 0, map);
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
            completedIds: row.completed_ids || [],
            paths: z ? z.paths : [],
            locked: false,
        };
    }

    clickNode(node) {
        // NV: khoa chua den luot (locked) thi khong mo
        if (node.status === "locked") {
            return;
        }
        this.openCourse(node.course);
    }

    async openCourse(course) {
        const data = await this.orm.call("slide.channel", "vd_course_load", [course.id]);
        this.dialog.add(VdCourseDialog, {
            title: "Khóa học - " + course.name,
            channelId: course.id,
            // CHI admin (o giao dien quan tri) moi duoc sua/thiet ke.
            // Khi xem theo nhan vien (selectedEmp) thi luon chi-doc.
            editable: this.state.isAdmin && !this.state.selectedEmp,
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
