/** @odoo-module **/
/**
 * QUẢN LÝ NHÂN VIÊN — viết mới hoàn toàn (user 2026-10-07), đơn giản nhất:
 *   • Chia theo PHÒNG BAN (cột), 2 tab Đang hoạt động / Nghỉ việc.
 *   • Popup Thêm / Sửa: tên, đăng nhập, email, chức vụ, phòng ban, mật khẩu.
 *   • Nút Xóa (có xác nhận) + nút Tắt (cho nghỉ việc) / Bật lại.
 * Tầng dữ liệu: res.users.vd_* (data / new_defaults / create / save / delete / set_active).
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState, onWillStart } from "@odoo/owl";

const TEAM_ORDER = ["HCM1", "HCM2", "HCM3", "HN", "QN", "CTV", "VINADUY", "Lọc số", "KHÁC"];

export class VdUserBoard extends Component {
    static template = "vd_crm_lead.VdUserBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: true,
            working: [],      // chỉ NV đang làm việc
            search: "",
            form: null,       // popup thêm/sửa; null = đóng
            saving: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const d = await this.orm.call("res.users", "vd_user_board_data", []);
            this.state.working = d.working || [];
        } finally {
            this.state.loading = false;
        }
    }

    get list() {
        const q = this.state.search.trim().toLowerCase();
        if (!q) return this.state.working;
        return this.state.working.filter((u) =>
            (u.name + " " + u.code + " " + u.team + " " + u.login).toLowerCase().includes(q));
    }

    // Gom theo phòng ban → các cột; trưởng nhóm lên đầu mỗi cột.
    get groups() {
        const map = {};
        for (const u of this.list) {
            const t = u.team || "KHÁC";
            (map[t] = map[t] || []).push(u);
        }
        const teams = Object.keys(map).sort((a, b) => {
            const ia = TEAM_ORDER.indexOf(a), ib = TEAM_ORDER.indexOf(b);
            return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
        });
        return teams.map((t) => ({
            team: t,
            color: (map[t][0] && map[t][0].team_color) || "#868e96",
            users: map[t].slice().sort(
                (a, b) => (b.is_leader - a.is_leader) || a.name.localeCompare(b.name)),
        }));
    }

    // ===== POPUP =====
    async openAdd() {
        try {
            const d = await this.orm.call("res.users", "vd_board_new_defaults", []);
            this.state.form = {
                id: null, name: "", login: "", email: "", role: "employee", team: "",
                active: true, admin_password: "", password: "",
                roles: d.role_options || [], teams: d.team_options || [],
            };
        } catch (e) {
            this.notification.add(this._err(e, "Không mở được."), { type: "danger" });
        }
    }

    async openEdit(u) {
        try {
            const d = await this.orm.call("res.users", "vd_board_load_user", [u.id]);
            if (!d || !d.id) {
                this.notification.add("Không mở được nhân viên.", { type: "danger" });
                return;
            }
            this.state.form = {
                id: d.id, name: d.name || "", login: d.login || "", email: d.email || "",
                role: d.role || "employee", team: d.team || "", active: !!d.active,
                admin_password: d.admin_password || "", password: "",
                roles: d.role_options || [], teams: d.team_options || [],
            };
        } catch (e) {
            this.notification.add(this._err(e, "Không mở được nhân viên."), { type: "danger" });
        }
    }

    closeForm() { this.state.form = null; }

    async save() {
        const f = this.state.form;
        if (!f.name.trim()) return this.notification.add("Nhập tên nhân viên.", { type: "warning" });
        if (!f.login.trim()) return this.notification.add("Nhập tên đăng nhập.", { type: "warning" });
        if (!f.id && f.password.trim().length < 6) {
            return this.notification.add("Nhập mật khẩu đăng nhập (tối thiểu 6 ký tự).",
                { type: "warning" });
        }
        const payload = {
            name: f.name, login: f.login, email: f.email,
            role: f.role, team: f.team, new_password: f.password,
        };
        this.state.saving = true;
        try {
            if (f.id) {
                await this.orm.call("res.users", "vd_board_save_user", [f.id, payload]);
                this.notification.add("Đã lưu thông tin nhân viên.", { type: "success" });
            } else {
                await this.orm.call("res.users", "vd_board_create_user", [payload]);
                this.notification.add("Đã thêm nhân viên mới.", { type: "success" });
            }
            this.state.form = null;
            await this.load();
        } catch (e) {
            this.notification.add(this._err(e, "Lưu thất bại."), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async toggleActive() {
        const f = this.state.form;
        this.state.saving = true;
        try {
            await this.orm.call("res.users", "vd_set_user_active", [f.id, !f.active]);
            this.notification.add(
                f.active ? "Đã cho nhân viên nghỉ việc." : "Đã kích hoạt lại nhân viên.",
                { type: "success" });
            this.state.form = null;
            await this.load();
        } catch (e) {
            this.notification.add(this._err(e, "Không đổi được trạng thái."), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    remove() {
        const f = this.state.form;
        this.dialog.add(ConfirmationDialog, {
            title: "Xóa nhân viên",
            body: `Xóa hẳn tài khoản "${f.name}"? Thao tác KHÔNG hoàn tác. ` +
                `Nếu NV còn khách sẽ không xóa được — hãy dùng "Cho nghỉ việc".`,
            confirmLabel: "Xóa hẳn",
            cancelLabel: "Huỷ",
            confirm: async () => {
                this.state.saving = true;
                try {
                    await this.orm.call("res.users", "vd_board_delete_user", [f.id]);
                    this.notification.add("Đã xóa nhân viên.", { type: "success" });
                    this.state.form = null;
                    await this.load();
                } catch (e) {
                    this.notification.add(this._err(e, "Không xóa được."), { type: "danger" });
                } finally {
                    this.state.saving = false;
                }
            },
            cancel: () => {},
        });
    }

    _err(e, fallback) {
        return (e && e.data && e.data.message) || fallback;
    }
}

registry.category("actions").add("vd_user_board", VdUserBoard);
