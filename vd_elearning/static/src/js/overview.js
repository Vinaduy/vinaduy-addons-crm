/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState, markup } from "@odoo/owl";

// ---- Luu/khoi phuc phien thi (localStorage) de tai lai trang van giu nguyen ----
// Khoa theo channel; bo dem chay theo endsAt (moc thoi gian tuyet doi) nen reload
// van dem tiep chinh xac. contentLocked = con phien (now < endsAt) va chua dat.
const VD_EXAM_PREFIX = "vd_exam_";
function vdExamKey(cid) {
    return VD_EXAM_PREFIX + cid;
}
function vdLoadExam(cid) {
    try {
        return JSON.parse(window.localStorage.getItem(vdExamKey(cid)) || "null");
    } catch (_) {
        return null;
    }
}
function vdSaveExam(cid, data) {
    try {
        window.localStorage.setItem(vdExamKey(cid), JSON.stringify(data));
    } catch (_) {}
}
function vdClearExam(cid) {
    try {
        window.localStorage.removeItem(vdExamKey(cid));
    } catch (_) {}
}
// Tim phien thi DANG dien ra (con thoi gian) de tu mo lai khi reload trang.
function vdFindActiveExam() {
    try {
        const now = Date.now();
        for (let i = 0; i < window.localStorage.length; i++) {
            const k = window.localStorage.key(i);
            if (!k || !k.startsWith(VD_EXAM_PREFIX)) continue;
            const v = JSON.parse(window.localStorage.getItem(k) || "null");
            if (v && v.endsAt && now < v.endsAt) return v;
        }
    } catch (_) {}
    return null;
}

// ---- Ve GIAY CHUNG NHAN ra canvas + tai ve file PNG (user spec 2026-06-24) ----
function _vdRoundRect(x, rx, ry, w, h, r) {
    if (x.roundRect) { x.beginPath(); x.roundRect(rx, ry, w, h, r); return; }
    x.beginPath();
    x.moveTo(rx + r, ry);
    x.arcTo(rx + w, ry, rx + w, ry + h, r);
    x.arcTo(rx + w, ry + h, rx, ry + h, r);
    x.arcTo(rx, ry + h, rx, ry, r);
    x.arcTo(rx, ry, rx + w, ry, r);
    x.closePath();
}
function vdDownloadCertImage(data) {
    const W = 1000, H = 680, cx = W / 2;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const x = cv.getContext("2d");
    // Nen + vien navy + khung vien dut vang
    x.fillStyle = "#1d3a8a"; x.fillRect(0, 0, W, H);
    x.fillStyle = "#ffffff"; x.fillRect(16, 16, W - 32, H - 32);
    x.strokeStyle = "#c9ad6a"; x.lineWidth = 2; x.setLineDash([9, 6]);
    x.strokeRect(36, 36, W - 72, H - 72); x.setLineDash([]);
    // Sao 4 goc
    x.fillStyle = "#9aa3b2"; x.font = "20px Arial"; x.textAlign = "center";
    x.fillText("★", 60, 64); x.fillText("★", W - 60, 64);
    x.fillText("★", 60, H - 50); x.fillText("★", W - 60, H - 50);
    // Logo + cong ty
    x.fillStyle = "#c0392b"; x.font = "900 46px Arial";
    x.fillText("VINADUY", cx, 116);
    x.fillStyle = "#6b7280"; x.font = "600 16px Arial";
    x.fillText(data.companyName || "", cx, 144);
    // Tieu de
    x.fillStyle = "#1d3a8a"; x.font = "900 52px Arial";
    x.fillText("GIẤY CHỨNG NHẬN", cx, 214);
    x.fillStyle = "#c0392b"; x.font = "800 24px Arial";
    x.fillText("HOÀN THÀNH KHÓA HỌC", cx, 252);
    // Ten khoa
    if (data.courseName) {
        x.fillStyle = "#16407a"; x.font = "800 24px Arial";
        x.fillText(data.courseName, cx, 300);
    }
    // Ten NV (chu ky)
    x.fillStyle = "#7a1f2b";
    x.font = "italic 62px 'Brush Script MT','Segoe Script','Lucida Handwriting',cursive";
    x.fillText(data.empName || "", cx, 392);
    // Vai tro
    x.fillStyle = "#2f5fae"; x.font = "700 22px Arial";
    x.fillText((data.roleLabel || "").toUpperCase(), cx, 432);
    // Huy hieu diem (vien tron vang)
    const sw = 280, sh = 48, sx = cx - sw / 2, sy = 470;
    x.fillStyle = "#ffe066"; _vdRoundRect(x, sx, sy, sw, sh, 24); x.fill();
    x.strokeStyle = "#f1c40f"; x.lineWidth = 2; _vdRoundRect(x, sx, sy, sw, sh, 24); x.stroke();
    x.fillStyle = "#8a5a00"; x.font = "800 25px Arial";
    x.fillText("ĐẠT " + (data.percent || 0) + " ĐIỂM", cx, sy + 33);
    // Ngay
    x.fillStyle = "#6b7280"; x.font = "italic 18px Arial";
    x.fillText("Ngày " + (data.dateStr || ""), cx, 560);

    const safe = (s) => (s || "").replace(/[\\/:*?"<>|\s]+/g, "_");
    cv.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ChungNhan_" + safe(data.empName) + "_" + safe(data.courseName) + ".png";
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
    }, "image/png");
}

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
        paths: { type: Array, optional: true },     // tat ca lo trinh cua khu (cho popup vi tri hoc)
        defaultPathId: { type: Number, optional: true },
        onConfirm: Function,
        onChanged: { type: Function, optional: true }, // bao cho cha reload sau khi gan vi tri
    };
    setup() {
        this.dialog = useService("dialog");
        const sel = {};
        for (const c of this.props.candidates) {
            sel[c.id] = !!c.assigned;
        }
        this.state = useState({ search: "", sel });
    }
    // Mo popup "Vi tri hoc" cho 1 NV: gan vao khoa hoc / lo trinh cu the.
    openPosition(c) {
        this.dialog.add(VdMemberPositionDialog, {
            title: "Vị trí học - " + c.name,
            userId: c.id,
            paths: this.props.paths || [],
            defaultPathId: this.props.defaultPathId || ((this.props.paths || [])[0] || {}).id || false,
            onSaved: async () => {
                this.state.sel[c.id] = true;   // gan vi tri => coi nhu da chon
                if (this.props.onChanged) await this.props.onChanged();
            },
        });
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

// ---- Popup "Vi tri hoc": gan 1 NV vao khoa hoc / lo trinh cu the ----
// Danh cho NV cu da hoc nhieu khoa: chon khoa DANG hoc -> moi khoa truoc = hoan thanh.
export class VdMemberPositionDialog extends Component {
    static template = "vd_elearning.MemberPositionDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        userId: Number,
        paths: Array,
        defaultPathId: [Number, Boolean],
        onSaved: Function,
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            pathId: this.props.defaultPathId || (this.props.paths[0] || {}).id || false,
            choice: "none",   // 'none' | 'all' | <courseId>
            loading: true,
            saving: false,
        });
        onWillStart(async () => {
            await this._loadPosition();
        });
    }
    get curPath() {
        return this.props.paths.find((p) => p.id === this.state.pathId) || null;
    }
    get curCourses() {
        return (this.curPath && this.curPath.courses) || [];
    }
    setChoice(v) {
        this.state.choice = v;
    }
    async onPathChange(ev) {
        this.state.pathId = parseInt(ev.target.value, 10) || false;
        await this._loadPosition();
    }
    // Lay vi tri hien tai cua NV trong lo trinh dang chon de preselect.
    async _loadPosition() {
        this.state.loading = true;
        try {
            const pid = parseInt(this.state.pathId, 10);
            const res = await this.orm.call("slide.channel", "vd_member_position", [
                pid, this.props.userId,
            ]);
            // res: {current_id, completed_count, total}
            if (res && res.total && res.completed_count >= res.total) {
                this.state.choice = "all";
            } else if (res && res.current_id) {
                this.state.choice = res.current_id;
            } else {
                this.state.choice = "none";
            }
        } finally {
            this.state.loading = false;
        }
    }
    async save() {
        if (this.state.saving) return;
        const pid = parseInt(this.state.pathId, 10);
        if (!pid) {
            this.notification.add("Chưa chọn lộ trình.", { type: "warning" });
            return;
        }
        let currentId = false, completedAll = false;
        if (this.state.choice === "all") {
            completedAll = true;
        } else if (this.state.choice !== "none") {
            currentId = parseInt(this.state.choice, 10) || false;
        }
        this.state.saving = true;
        try {
            await this.orm.call("slide.channel", "vd_set_member_position", [
                pid, this.props.userId, currentId, completedAll,
            ]);
            await this.props.onSaved();
            this.notification.add("Đã lưu vị trí học.", { type: "success" });
            this.props.close();
        } catch (e) {
            this.state.saving = false;
            throw e;
        }
    }
}

// ---- Popup LEN LICH HOC BAT BUOC: chon NV + gio vao hoc cho 1 khoa ----
// NV se thay banner + dem nguoc tren dashboard CRM, den gio bam "VAO HOC".
export class VdScheduleDialog extends Component {
    static template = "vd_elearning.ScheduleDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        channelId: Number,
        courseName: String,
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, saving: false,
            id: false, message: "", startLocal: "", lead: 15, open: 0,
            search: "", sel: {}, candidates: [], history: [],
        });
        onWillStart(async () => {
            const d = await this.orm.call("vd.training.session", "vd_schedule_load", [
                this.props.channelId,
            ]);
            this.state.candidates = d.candidates || [];
            this.state.history = d.history || [];
            this.state.id = d.id || false;
            this.state.message = d.message || "";
            this.state.lead = d.lead_minutes == null ? 15 : d.lead_minutes;
            this.state.open = d.open_minutes || 0;
            this.state.startLocal = d.start_ts ? this._toLocalInput(d.start_ts) : "";
            const sel = {};
            for (const uid of (d.user_ids || [])) sel[uid] = true;
            this.state.sel = sel;
            this.state.loading = false;
        });
    }
    get doneCount() {
        return this.state.history.filter((h) => h.done).length;
    }
    histWhen(ts) {
        if (!ts) return "-";
        const d = new Date(ts);
        const p = (n) => (n < 10 ? "0" : "") + n;
        return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}/${p(d.getMonth() + 1)}`;
    }
    // epoch ms -> chuoi cho <input type=datetime-local> (gio dia phuong).
    _toLocalInput(ms) {
        const d = new Date(ms);
        const p = (n) => (n < 10 ? "0" : "") + n;
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
    }
    get filtered() {
        const q = this.state.search.trim().toLowerCase();
        if (!q) return this.state.candidates;
        return this.state.candidates.filter(
            (c) => (c.name || "").toLowerCase().includes(q) ||
                   (c.team || "").toLowerCase().includes(q)
        );
    }
    get selCount() {
        return Object.values(this.state.sel).filter(Boolean).length;
    }
    toggle(id) {
        this.state.sel[id] = !this.state.sel[id];
    }
    selectAll() {
        const sel = {};
        for (const c of this.state.candidates) sel[c.id] = true;
        this.state.sel = sel;
    }
    clearAll() {
        this.state.sel = {};
    }
    async save() {
        if (this.state.saving) return;
        if (!this.state.startLocal) {
            this.notification.add("Chưa chọn giờ vào học.", { type: "warning" });
            return;
        }
        const ids = this.state.candidates.filter((c) => this.state.sel[c.id]).map((c) => c.id);
        if (!ids.length) {
            this.notification.add("Chưa chọn nhân viên áp dụng.", { type: "warning" });
            return;
        }
        const ts = new Date(this.state.startLocal).getTime();
        this.state.saving = true;
        try {
            await this.orm.call("vd.training.session", "vd_schedule_save", [
                this.props.channelId,
                {
                    id: this.state.id,
                    message: this.state.message,
                    start_ts: ts,
                    lead_minutes: parseInt(this.state.lead, 10) || 0,
                    open_minutes: parseInt(this.state.open, 10) || 0,
                    user_ids: ids,
                },
            ]);
            this.notification.add("Đã lưu lịch học bắt buộc.", { type: "success" });
            this.props.close();
        } catch (e) {
            this.state.saving = false;
            throw e;
        }
    }
    async disable() {
        if (!this.state.id) {
            this.props.close();
            return;
        }
        await this.orm.call("vd.training.session", "vd_schedule_disable", [
            this.props.channelId,
        ]);
        this.notification.add("Đã tắt lịch học.", { type: "success" });
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

// ---- GIAY CHUNG NHAN hoan thanh khoa hoc (phao hoa + diem + ten khoa) ----
export class VdCertificateDialog extends Component {
    static template = "vd_elearning.CertificateDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        empName: String,
        roleLabel: String,
        companyName: String,
        courseName: String,
        percent: Number,
        dateStr: { type: String, optional: true },
    };
    setup() {
        const colors = ["#ff5252", "#ffb300", "#42a5f5", "#66bb6a", "#ab47bc",
                        "#ff7043", "#26c6da", "#ec407a"];
        // Pháo hoa/confetti: sinh sẵn vị trí + màu + thời gian ngẫu nhiên.
        this.pieces = Array.from({ length: 80 }, (_, i) => ({
            left: Math.round(Math.random() * 100),
            delay: (Math.random() * 1.5).toFixed(2),
            dur: (2.4 + Math.random() * 2).toFixed(2),
            color: colors[i % colors.length],
            rot: Math.round(Math.random() * 360),
            size: 6 + Math.round(Math.random() * 9),
            round: i % 3 === 0,
        }));
        const d = new Date();
        const p = (n) => (n < 10 ? "0" : "") + n;
        this.dateStr = this.props.dateStr ||
            `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
    }
    download() {
        // Tải giấy chứng nhận về dưới dạng FILE ẢNH (PNG).
        vdDownloadCertImage({
            empName: this.props.empName,
            roleLabel: this.props.roleLabel,
            companyName: this.props.companyName,
            courseName: this.props.courseName,
            percent: this.props.percent,
            dateStr: this.dateStr,
        });
    }
}

// ---- POPOVER giay chung nhan (hien khi HOVER node khoa hoc) — cert + phao hoa ----
export class VdCertPopover extends Component {
    static template = "vd_elearning.CertPopover";
    static props = {
        close: { type: Function, optional: true },
        empName: String, roleLabel: String, companyName: String,
        courseName: String, percent: [Number, String],
        onEnter: Function, onLeave: Function, onDownload: Function,
    };
    setup() {
        const colors = ["#ff5252", "#ffb300", "#42a5f5", "#66bb6a", "#ab47bc",
                        "#ff7043", "#26c6da", "#ec407a"];
        this.pieces = Array.from({ length: 60 }, (_, i) => ({
            left: Math.round(Math.random() * 100),
            delay: (Math.random() * 1.3).toFixed(2),
            dur: (2.2 + Math.random() * 1.8).toFixed(2),
            color: colors[i % colors.length],
            rot: Math.round(Math.random() * 360),
            size: 5 + Math.round(Math.random() * 7),
            round: i % 3 === 0,
        }));
    }
}

// ---- Popup full man hinh: soan noi dung + cau hoi thi cua khoa hoc ----
export class VdCourseDialog extends Component {
    static template = "vd_elearning.CourseDialog";
    static components = { Dialog, VdRichEditor, VdConfigDialog, VdScheduleDialog, VdCertificateDialog };
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
            examEndsAt: 0,                 // moc ket thuc (ms) - de reload dem tiep
            contentLocked: false,          // khoa noi dung tới khi het gio thi
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
        // Khoi phuc phien thi dang do (vd. vua reload trang) - hoc vien thi.
        if (!this.props.editable) {
            this._restoreExam();
        }
    }
    key() {
        return "k" + this._k++;
    }

    // ---- BO DEM THOI GIAN THI (theo moc ket thuc tuyet doi endsAt) ----
    _stopTimer() {
        if (this._examTimer) {
            clearInterval(this._examTimer);
            this._examTimer = null;
        }
    }
    _tick() {
        const left = Math.max(0, Math.round((this.state.examEndsAt - Date.now()) / 1000));
        this.state.secondsLeft = left;
        if (left <= 0) {
            this._stopTimer();
            // Het gio: tu dong nop neu chua nop, va MO khoa noi dung.
            if (!this.state.examResult) {
                this.submitExam(true);
            }
            this.state.contentLocked = false;
            vdClearExam(this.props.channelId);
        }
    }
    _startTimerTo(endsAt) {
        this._stopTimer();
        this.state.examEndsAt = endsAt;
        this._tick();
        if (this.state.secondsLeft > 0) {
            this._examTimer = setInterval(() => this._tick(), 500);
        }
    }
    // Luu phien thi vao localStorage (de reload giu nguyen + dem tiep).
    _persistExam() {
        const answers = {};
        for (const q of this.state.questions) {
            answers[String(q.id)] = q.answers.filter((a) => a.chosen).map((a) => a.id);
        }
        vdSaveExam(this.props.channelId, {
            channelId: this.props.channelId,
            courseName: this.state.courseName,
            endsAt: this.state.examEndsAt,
            attempt: this.state.attemptCount,
            result: this.state.examResult,
            answers,
        });
    }
    _restoreExam() {
        const sess = vdLoadExam(this.props.channelId);
        if (!sess || !sess.endsAt) return;
        const now = Date.now();
        if (now >= sess.endsAt) {
            // Het gio tu truoc -> bo phien, khong khoa nua.
            vdClearExam(this.props.channelId);
            return;
        }
        // Con thoi gian -> khoi phuc dung trang thai dang thi.
        this.state.attemptCount = sess.attempt || 0;
        this.state.examStarted = true;
        this.state.contentLocked = true;
        this.state.tab = "exam";
        if (sess.answers) {
            for (const q of this.state.questions) {
                const chosen = sess.answers[String(q.id)] || [];
                for (const a of q.answers) a.chosen = chosen.includes(a.id);
            }
        }
        if (sess.result) {
            this.state.examResult = sess.result;  // da nop nhung chua het gio -> cho
        }
        this._startTimerTo(sess.endsAt);
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
        // Admin luon xem duoc. Hoc vien: KHOA noi dung khi dang thi / chua het gio.
        return this.props.editable || !this.state.contentLocked;
    }
    setTab(t) {
        if (t === "content" && !this.showContentTab) return;
        this.state.tab = t;
    }

    // ---- HOC VIEN: lam bai thi ----
    // Fisher-Yates: tra ve mang MOI da xao tron (khong sua mang goc).
    _shuffle(arr) {
        const a = arr.slice();
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }
    startExam() {
        this.state.examStarted = true;
        this.state.examResult = null;
        for (const q of this.state.questions) {
            // DAO VI TRI DAP AN moi lan vao thi: moi lan thi lai + moi NV khac
            // nhau. Cham diem theo answer_id (vd_course_grade) nen doi thu tu
            // hien thi KHONG anh huong ket qua.
            q.answers = this._shuffle(q.answers);
            for (const a of q.answers) a.chosen = false;
        }
        this.state.tab = "exam";
        this.state.contentLocked = true;
        const endsAt = Date.now() + (this.state.examMinutes || 0) * 60 * 1000;
        this._persistExam();          // luu truoc (co endsAt set trong _startTimerTo)
        this._startTimerTo(endsAt);
        this._persistExam();
    }
    chooseAnswer(q, a) {
        if (this.props.editable || this.state.examResult) return;
        a.chosen = !a.chosen;
        this._persistExam();
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
            if (res.passed) {
                // Dat -> mo khoa noi dung ngay, ket thuc phien.
                this._stopTimer();
                this.state.contentLocked = false;
                vdClearExam(this.props.channelId);
                // GIAY CHUNG NHAN: hien ngay khi DAT (phao hoa + diem + ten khoa).
                const cert = res.cert || {};
                this.dialog.add(VdCertificateDialog, {
                    empName: cert.emp_name || "",
                    roleLabel: cert.role_label || "NHÂN VIÊN KINH DOANH",
                    companyName: cert.company_name || "CÔNG TY CỔ PHẦN VINADUY",
                    courseName: cert.course_name || this.props.title || "",
                    percent: res.percent,
                });
            } else {
                // Chua dat -> van khoa noi dung, dong ho tiep tuc dem den het gio.
                this._persistExam();
            }
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
    // ---- Len lich hoc bat buoc cho khoa nay (banner + dem nguoc tren dashboard CRM) ----
    openSchedule() {
        this.dialog.add(VdScheduleDialog, {
            channelId: this.props.channelId,
            courseName: this.state.courseName,
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
        if (this.state.contentLocked) return;  // chua het gio -> khong cho xem noi dung
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

// ---- THƯ VIỆN - Câu hỏi khó: kho câu hỏi + 3 kịch bản trả lời cho sale ----
export class VdHardLibraryDialog extends Component {
    static template = "vd_elearning.HardLibraryDialog";
    static components = { Dialog };
    static props = { close: Function };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            items: [],
            topics: [],
            difficulties: [],
            situations: [],
            search: "",
            topic: "",        // '' = tất cả chủ đề
            difficulty: "",
            situation: "",
            openId: null,     // câu đang mở rộng xem 3 câu trả lời
        });
        onWillStart(async () => {
            const d = await this.orm.call("vd.hard.question", "vd_library_load", []);
            this.state.items = d.items || [];
            this.state.topics = d.topics || [];
            this.state.difficulties = d.difficulties || [];
            this.state.situations = d.situations || [];
            this.state.loading = false;
        });
    }
    get filtered() {
        const q = this.state.search.trim().toLowerCase();
        return this.state.items.filter((it) => {
            if (this.state.topic && it.topic !== this.state.topic) return false;
            if (this.state.difficulty && it.difficulty !== this.state.difficulty) return false;
            if (this.state.situation && it.situation !== this.state.situation) return false;
            if (!q) return true;
            const hay = (
                it.question + " " + it.keywords + " " + it.intent + " " +
                it.a1 + " " + it.a2 + " " + it.a3
            ).toLowerCase();
            return hay.includes(q);
        });
    }
    topicCount(key) {
        return this.state.items.filter((it) => it.topic === key).length;
    }
    setTopic(k) {
        this.state.topic = this.state.topic === k ? "" : k;
    }
    setDiff(k) {
        this.state.difficulty = this.state.difficulty === k ? "" : k;
    }
    setSit(k) {
        this.state.situation = this.state.situation === k ? "" : k;
    }
    toggleOpen(id) {
        this.state.openId = this.state.openId === id ? null : id;
    }
    clearFilters() {
        this.state.search = "";
        this.state.topic = "";
        this.state.difficulty = "";
        this.state.situation = "";
    }
    diffClass(d) {
        return "o_vd_hq_d_" + (d || "trungbinh");
    }
    async copyText(text) {
        try {
            await navigator.clipboard.writeText(text || "");
            this.notification.add("Đã sao chép câu trả lời.", { type: "success" });
        } catch (_) {
            this.notification.add("Không sao chép được (trình duyệt chặn).", { type: "warning" });
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
        this.notification = useService("notification");
        // Popover giấy chứng nhận khi hover node khóa (thoát khỏi vùng bị cắt).
        this.certPop = usePopover(VdCertPopover, {
            position: "top", popoverClass: "o_vd_certpop_wrap",
        });
        this._certPopTimer = null;
        this.state = useState({
            zones: [],
            report: [],
            isAdmin: false,
            tab: "sales",
            selectedEmp: null,
            loading: true,
            myCerts: null,   // {emp_name, role_label, company_name, items:[...]}
            riderDragging: false,  // admin keo avatar NV de gan vao khoa chua hoan thanh
        });
        this.dragData = null;
        this.pathDragData = null;
        this.riderDragData = null;
        onWillStart(async () => {
            await this.reload();
            // "VAO HOC" tu dashboard CRM: mo THANG khoa hoc duoc chi dinh (khong qua lo trinh).
            const params = (this.props.action && this.props.action.params) || {};
            if (params.vd_open_course_id) {
                this.openCourse({
                    id: params.vd_open_course_id,
                    name: params.vd_open_course_name || "",
                });
                return;
            }
            // Reload trang giua chung khi DANG THI -> tu mo lai bai thi, dem tiep.
            const sess = vdFindActiveExam();
            if (sess && sess.channelId) {
                this.openCourse({ id: sess.channelId, name: sess.courseName || "" });
            }
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
            // Giấy chứng nhận đã đạt của NV (lưu bền vững) — cho mục "của tôi".
            try {
                this.state.myCerts = await this.orm.call(
                    "slide.channel", "vd_my_certificates", []);
            } catch (e) {
                this.state.myCerts = null;
            }
        }
        this.state.loading = false;
    }

    // Giấy chứng nhận của khóa (CHỈ giao diện của chính mình + đã đạt). Dùng cho
    // popup hover trên node khóa học (user spec 2026-06-24).
    certForCourse(courseId) {
        const e = this.state.selectedEmp;
        if (!e || !e.locked) return null;          // chỉ xem của mình
        const c = this.state.myCerts;
        if (!c || !c.items) return null;
        return c.items.find((it) => it.channel_id === courseId) || null;
    }
    _certDate() {
        const d = new Date();
        const p = (n) => (n < 10 ? "0" : "") + n;
        return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
    }
    // Tải giấy chứng nhận của 1 khóa về dưới dạng ảnh PNG.
    downloadCert(course) {
        const c = this.state.myCerts || {};
        const item = this.certForCourse(course.id);
        vdDownloadCertImage({
            empName: c.emp_name || (this.state.selectedEmp && this.state.selectedEmp.name) || "",
            roleLabel: c.role_label || "NHÂN VIÊN KINH DOANH",
            companyName: c.company_name || "CÔNG TY CỔ PHẦN VINADUY",
            courseName: course.name || "",
            percent: (item && item.percent) || 100,
            dateStr: this._certDate(),
        });
    }
    // Hover vào node khóa ĐÃ ĐẠT -> hiện popover giấy chứng nhận + pháo hoa.
    onCertEnter(ev, course) {
        const item = this.certForCourse(course.id);
        if (!item) return;
        clearTimeout(this._certPopTimer);
        const c = this.state.myCerts || {};
        this.certPop.open(ev.currentTarget, {
            empName: c.emp_name || (this.state.selectedEmp && this.state.selectedEmp.name) || "",
            roleLabel: c.role_label || "NHÂN VIÊN KINH DOANH",
            companyName: c.company_name || "CÔNG TY CỔ PHẦN VINADUY",
            courseName: course.name || "",
            percent: (item && item.percent) || 100,
            onEnter: () => clearTimeout(this._certPopTimer),
            onLeave: () => this._scheduleCertClose(),
            onDownload: () => this.downloadCert(course),
        });
    }
    onCertLeave() {
        this._scheduleCertClose();
    }
    _scheduleCertClose() {
        clearTimeout(this._certPopTimer);
        this._certPopTimer = setTimeout(() => {
            try { this.certPop.close(); } catch (_e) { /* noop */ }
        }, 220);
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

    async viewEmployee(row) {
        const z = this.state.zones.find((zn) => zn.key === row.zone_key);
        this.state.selectedEmp = {
            id: row.id,
            name: row.name,
            courseId: row.current_id || false,
            completedIds: row.completed_ids || [],
            paths: z ? z.paths : [],
            locked: false,
            examHistory: [],
        };
        // Lich su thi BEN VUNG cua NV (doc tu vd.exam.result).
        try {
            const hist = await this.orm.call(
                "vd.exam.result", "vd_user_history", [row.id]
            );
            if (this.state.selectedEmp && this.state.selectedEmp.id === row.id) {
                this.state.selectedEmp.examHistory = hist || [];
            }
        } catch (e) {
            // Khong chan giao dien neu loi doc lich su.
        }
    }

    // epoch ms -> "HH:MM DD/MM" (gio dia phuong) cho bang lich su thi NV.
    examWhen(ts) {
        if (!ts) return "-";
        const d = new Date(ts);
        const p = (n) => (n < 10 ? "0" : "") + n;
        return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}/${p(d.getMonth() + 1)}`;
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

    // THƯ VIỆN - Câu hỏi khó: mở kho câu hỏi + kịch bản trả lời (cạnh khóa học).
    openHardLibrary() {
        this.dialog.add(VdHardLibraryDialog, {});
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

    // Xoa khoa hoc RONG (chua co noi dung + chua co bai thi). Chi admin.
    async deleteCourse(course) {
        if (!this.state.isAdmin || course.has_content) return;
        if (!window.confirm('Xóa khóa học "' + (course.name || '') + '"?\nChỉ xóa được khóa chưa có nội dung và chưa có bài thi.')) {
            return;
        }
        await this.orm.call("slide.channel", "vd_course_delete", [course.id]);
        await this.reload();
    }

    async openAssign(path, zone) {
        const candidates = await this.orm.call(
            "slide.channel", "vd_path_candidates", [path.id]
        );
        this.dialog.add(VdAssignDialog, {
            title: "Gán nhân viên - " + path.name,
            candidates,
            paths: (zone && zone.paths) || [path],   // cho popup "Vi tri hoc" chon lo trinh khac
            defaultPathId: path.id,
            onConfirm: async (userIds) => {
                await this.orm.call("slide.channel", "vd_set_path_members", [
                    path.id,
                    userIds,
                ]);
                await this.reload();
            },
            onChanged: async () => {
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

    // ---------- KEO - THA NV VAO KHOA (admin: dua NV vao khoa chua hoan thanh) ----------
    // Chi o man "Hanh trinh chinh phuc cua [NV]" (selectedEmp) + la admin.
    _isDone(courseId) {
        const e = this.state.selectedEmp;
        return !!(e && (e.completedIds || []).includes(courseId));
    }
    onRiderDragStart(ev, rider) {
        if (!this.state.isAdmin || !this.state.selectedEmp) return;
        this.riderDragData = { id: rider.id, name: rider.name };
        this.state.riderDragging = true;
        ev.dataTransfer.effectAllowed = "move";
        try { ev.dataTransfer.setData("text/plain", "rider:" + rider.id); } catch (_e) { /* noop */ }
        ev.stopPropagation();
    }
    onRiderDragEnd() {
        this.state.riderDragging = false;
        this.riderDragData = null;
    }
    onRiderDragOver(ev, node) {
        if (!this.state.isAdmin || !this.riderDragData) return;
        if (this._isDone(node.course.id)) return;   // khoa da hoan thanh -> khong cho tha
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }
    async onRiderDrop(ev, course) {
        if (!this.state.isAdmin || !this.state.selectedEmp || !this.riderDragData) return;
        ev.preventDefault();
        ev.stopPropagation();
        const emp = this.riderDragData;
        this.riderDragData = null;
        this.state.riderDragging = false;
        if (this._isDone(course.id)) {
            this.notification.add(
                `${emp.name} đã hoàn thành khóa "${course.name}" rồi.`,
                { type: "warning" });
            return;
        }
        try {
            await this.orm.call("slide.channel", "vd_assign_course_to_user",
                [emp.id, course.id]);
            this.notification.add(
                `Đã đưa ${emp.name} vào khóa "${course.name}".`,
                { type: "success" });
            await this.reload();
            // reload (cho admin) khong tu giu selectedEmp -> mo lai hanh trinh NV.
            const row = this.state.report.find((r) => r.id === emp.id);
            if (row) { await this.viewEmployee(row); }
        } catch (e) {
            this.notification.add("Không gán được khóa cho nhân viên.",
                { type: "danger" });
        }
    }

    // ---------- KEO - THA LO TRINH (doi thu tu ca lo trinh, khoa hoc theo cung) ----------
    onPathDragStart(ev, zoneKey, pathId) {
        if (!this.state.isAdmin) return;
        this.pathDragData = { zoneKey, pathId };
        ev.dataTransfer.effectAllowed = "move";
        ev.currentTarget.classList.add("o_vd_path_dragging");
        ev.stopPropagation();
    }
    onPathDragEnd(ev) {
        ev.currentTarget.classList.remove("o_vd_path_dragging");
    }
    onPathDragOver(ev) {
        if (!this.state.isAdmin || !this.pathDragData) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }
    async onPathDrop(ev, zoneKey, targetPathId) {
        if (!this.state.isAdmin || !this.pathDragData) return;
        ev.preventDefault();
        ev.stopPropagation();
        const d = this.pathDragData;
        this.pathDragData = null;
        if (d.zoneKey !== zoneKey || d.pathId === targetPathId) return;
        const zone = this.state.zones.find((z) => z.key === zoneKey);
        if (!zone) return;
        const from = zone.paths.findIndex((p) => p.id === d.pathId);
        const to = zone.paths.findIndex((p) => p.id === targetPathId);
        if (from < 0 || to < 0) return;
        const [moved] = zone.paths.splice(from, 1);
        zone.paths.splice(to, 0, moved);
        await this.orm.call("slide.channel", "vd_save_path_order", [
            zoneKey,
            zone.paths.map((p) => p.id),
        ]);
    }
}

registry.category("actions").add("vd_elearning_overview", VdElearningOverview);

// Cho module khac (vd_crm_lead - form khach hang) mo THU VIEN cau hoi kho ma
// KHONG can phu thuoc cung vd_elearning: lay component qua registry chung.
registry.category("vd_dialogs").add("hard_library", VdHardLibraryDialog);
