/** @odoo-module **/
/**
 * BẢNG CHẤM CÔNG — UI mới (user 2026-10-12), thay list Odoo mặc định.
 *   • Cột: STT · Tên NV · Mã NV · Giờ vào · Giờ ra · Ngày · Số giờ · Thao tác.
 *   • Header: lọc THÁNG + Xuất Excel + Chấm bù (sửa tay cho NV quên chấm).
 *   • Chỉ Admin/Quản lý chấm công.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState, onWillStart } from "@odoo/owl";

export class VdAttendanceBoard extends Component {
    static template = "vd_face_attendance.Board";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        const now = new Date();
        this.state = useState({
            loading: true,
            month: now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0"),
            monthLabel: "",
            rows: [],
            totalHours: 0,
            search: "",
            users: [],
            form: null,       // popup chấm bù; null = đóng
            saving: false,
            exporting: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const d = await this.orm.call("vd.face.attendance", "vd_attendance_board", [this.state.month]);
            this.state.rows = d.rows || [];
            this.state.monthLabel = d.month_label || "";
            this.state.totalHours = d.total_hours || 0;
            this.state.month = d.month;
        } catch (e) {
            this.notification.add(this._err(e, "Không tải được bảng chấm công."), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    onMonthChange(ev) {
        this.state.month = ev.target.value || this.state.month;
        this.load();
    }

    get rows() {
        const q = this.state.search.trim().toLowerCase();
        if (!q) return this.state.rows;
        return this.state.rows.filter((r) => (r.name + " " + r.code).toLowerCase().includes(q));
    }

    fmtHours(h) {
        h = h || 0;
        const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
        return String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0");
    }

    async _ensureUsers() {
        if (this.state.users.length) return;
        try {
            this.state.users = await this.orm.call("vd.face.attendance", "vd_attendance_users", []);
        } catch (e) {
            this.notification.add(this._err(e, "Không tải được danh sách NV."), { type: "danger" });
        }
    }

    async openAdd() {
        await this._ensureUsers();
        this.state.form = {
            id: null, user_id: "", date: new Date().toISOString().slice(0, 10),
            in_hm: "08:00", out_hm: "17:30",
        };
    }

    async openEdit(r) {
        await this._ensureUsers();
        const p = (r.date || "").split("/");
        const dateIso = p.length === 3 ? `${p[2]}-${p[1]}-${p[0]}` : "";
        this.state.form = {
            id: r.id, user_id: String(r.user_id || ""), date: dateIso,
            in_hm: r.in_time || "", out_hm: r.out_time || "",
        };
    }

    closeForm() { this.state.form = null; }

    async save() {
        const f = this.state.form;
        if (!f.user_id) return this.notification.add("Chọn nhân viên.", { type: "warning" });
        if (!f.date) return this.notification.add("Chọn ngày.", { type: "warning" });
        if (!f.in_hm) return this.notification.add("Nhập giờ vào.", { type: "warning" });
        this.state.saving = true;
        try {
            await this.orm.call("vd.face.attendance", "vd_attendance_manual_save", [{
                id: f.id, user_id: parseInt(f.user_id, 10), date: f.date,
                in_hm: f.in_hm, out_hm: f.out_hm,
            }]);
            this.notification.add(f.id ? "Đã lưu chấm công." : "Đã chấm bù.", { type: "success" });
            this.state.form = null;
            await this.load();
        } catch (e) {
            this.notification.add(this._err(e, "Lưu thất bại."), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    removeRow(r) {
        this.dialog.add(ConfirmationDialog, {
            title: "Xoá bản ghi chấm công",
            body: `Xoá chấm công của "${r.name}" ngày ${r.date}? Không hoàn tác.`,
            confirmLabel: "Xoá",
            cancelLabel: "Huỷ",
            confirm: async () => {
                try {
                    await this.orm.call("vd.face.attendance", "vd_attendance_delete", [r.id]);
                    this.notification.add("Đã xoá.", { type: "success" });
                    await this.load();
                } catch (e) {
                    this.notification.add(this._err(e, "Không xoá được."), { type: "danger" });
                }
            },
            cancel: () => {},
        });
    }

    async exportExcel() {
        this.state.exporting = true;
        try {
            const r = await this.orm.call("vd.face.attendance", "vd_attendance_export", [this.state.month]);
            const a = document.createElement("a");
            a.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + r.data;
            a.download = r.filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (e) {
            this.notification.add(this._err(e, "Xuất Excel lỗi."), { type: "danger" });
        } finally {
            this.state.exporting = false;
        }
    }

    _err(e, f) { return (e && e.data && e.data.message) || f; }
}

registry.category("actions").add("vd_attendance_board", VdAttendanceBoard);
