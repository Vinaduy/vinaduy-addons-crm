/** @odoo-module **/
/**
 * Bảng quản lý nhân viên — CHIA TAB (user spec 2026-09-05):
 *   - Tab "Đang hoạt động" | Tab "Nghỉ việc / Tạm dừng"
 * Bấm 1 NV → POPUP sửa: tên, đăng nhập, email, chức vụ, phòng ban, mật khẩu
 * + nút cho nghỉ / kích hoạt lại (thay drag-drop cũ). KHÔNG nhảy trang mới.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useState, onWillStart } from "@odoo/owl";

export class VdUserBoard extends Component {
    static template = "vd_crm_lead.VdUserBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            working: [],
            off: [],
            loading: true,
            search: "",
            tab: "working",       // tab đang xem: 'working' | 'off'
            edit: null,           // dữ liệu NV đang sửa (popup)
            saving: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("res.users", "vd_user_board_data", []);
            this.state.working = data.working || [];
            this.state.off = data.off || [];
        } finally {
            this.state.loading = false;
        }
    }

    setTab(t) { this.state.tab = t; }

    _filter(list) {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) return list;
        return list.filter((c) =>
            (c.name + " " + c.code + " " + c.team + " " + c.login).toLowerCase().includes(q)
        );
    }
    get workingList() { return this._filter(this.state.working); }
    get offList() { return this._filter(this.state.off); }

    // Gom theo PHÒNG BAN thành các cột; trưởng nhóm/lãnh đạo đứng đầu mỗi cột.
    _groupByTeam(list) {
        const ORDER = ["HCM1", "HCM2", "HCM3", "HN", "QN", "CTV", "VINADUY", "Lọc số", "KHÁC"];
        const map = {};
        for (const c of list) {
            const t = c.team || "KHÁC";
            (map[t] = map[t] || []).push(c);
        }
        const teams = Object.keys(map).sort((a, b) => {
            const ia = ORDER.indexOf(a), ib = ORDER.indexOf(b);
            return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || (a < b ? -1 : 1);
        });
        return teams.map((t) => {
            const cards = map[t].slice().sort((a, b) => {
                if (a.is_leader !== b.is_leader) return a.is_leader ? -1 : 1;
                return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1;
            });
            return { team: t, color: (cards[0] && cards[0].team_color) || "#868e96", cards };
        });
    }
    get workingGroups() { return this._groupByTeam(this.workingList); }
    get offGroups() { return this._groupByTeam(this.offList); }
    get activeGroups() { return this.state.tab === "working" ? this.workingGroups : this.offGroups; }

    // ===== POPUP SỬA NV =====
    async openUser(card) {
        try {
            const data = await this.orm.call("res.users", "vd_board_load_user", [card.id]);
            if (!data || !data.id) {
                this.notification.add("Không mở được nhân viên.", { type: "danger" });
                return;
            }
            this.state.edit = {
                id: data.id,
                name: data.name || "",
                login: data.login || "",
                email: data.email || "",
                role: data.role || "employee",
                team: data.team || "",
                active: !!data.active,
                admin_password: data.admin_password || "",
                new_password: "",
                role_options: data.role_options || [],
                team_options: data.team_options || [],
            };
        } catch (e) {
            const msg = (e && e.data && e.data.message) || "Không mở được nhân viên.";
            this.notification.add(msg, { type: "danger" });
        }
    }
    closeEdit() { this.state.edit = null; }

    async saveUser() {
        const e = this.state.edit;
        if (!e) return;
        if (!(e.name || "").trim()) {
            this.notification.add("Nhập tên nhân viên.", { type: "warning" });
            return;
        }
        if (!(e.login || "").trim()) {
            this.notification.add("Nhập tên đăng nhập.", { type: "warning" });
            return;
        }
        const creating = !e.id;
        if (creating && (e.new_password || "").trim().length < 6) {
            this.notification.add("Nhập mật khẩu đăng nhập (tối thiểu 6 ký tự).",
                { type: "warning" });
            return;
        }
        const payload = {
            name: e.name, login: e.login, email: e.email,
            role: e.role, team: e.team, new_password: e.new_password,
        };
        this.state.saving = true;
        try {
            if (creating) {
                await this.orm.call("res.users", "vd_board_create_user", [payload]);
                this.notification.add("Đã thêm nhân viên mới.", { type: "success" });
            } else {
                await this.orm.call("res.users", "vd_board_save_user", [e.id, payload]);
                this.notification.add("Đã lưu thông tin nhân viên.", { type: "success" });
            }
            this.state.edit = null;
            await this.load();
        } catch (err) {
            const msg = (err && err.data && err.data.message) || "Lưu thất bại.";
            this.notification.add(msg, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    // XÓA HẲN 1 NV (có xác nhận). Còn khách → backend chặn, báo dùng "Cho nghỉ".
    deleteUser() {
        const e = this.state.edit;
        if (!e || !e.id) return;
        this.dialog.add(ConfirmationDialog, {
            title: "Xóa nhân viên",
            body: `Xóa hẳn tài khoản "${e.name}"? Thao tác KHÔNG hoàn tác được. ` +
                `Nếu NV còn khách thì sẽ không xóa được — hãy dùng "Cho nghỉ việc".`,
            confirmLabel: "Xóa hẳn",
            cancelLabel: "Huỷ",
            confirm: async () => {
                this.state.saving = true;
                try {
                    await this.orm.call("res.users", "vd_board_delete_user", [e.id]);
                    this.notification.add("Đã xóa nhân viên.", { type: "success" });
                    this.state.edit = null;
                    await this.load();
                } catch (err) {
                    const msg = (err && err.data && err.data.message) || "Không xóa được.";
                    this.notification.add(msg, { type: "danger" });
                } finally {
                    this.state.saving = false;
                }
            },
            cancel: () => {},
        });
    }

    // Bật/tắt trạng thái làm việc TỪ TRONG popup (thay drag-drop cũ).
    async toggleActive() {
        const e = this.state.edit;
        if (!e) return;
        const want = !e.active;
        this.state.saving = true;
        try {
            await this.orm.call("res.users", "vd_set_user_active", [e.id, want]);
            e.active = want;
            this.notification.add(
                want ? "Đã kích hoạt lại nhân viên." : "Đã cho nhân viên nghỉ việc.",
                { type: "success" });
            this.state.edit = null;
            await this.load();
        } catch (err) {
            const msg = (err && err.data && err.data.message) || "Không đổi được trạng thái.";
            this.notification.add(msg, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    // THÊM NV mới → mở CÙNG popup (chế độ tạo: id = null).
    async openNew() {
        try {
            const d = await this.orm.call("res.users", "vd_board_new_defaults", []);
            this.state.edit = {
                id: null, name: "", login: "", email: "",
                role: "employee", team: "", active: true,
                admin_password: "", new_password: "",
                role_options: d.role_options || [],
                team_options: d.team_options || [],
            };
        } catch (e) {
            const msg = (e && e.data && e.data.message) || "Không mở được form thêm NV.";
            this.notification.add(msg, { type: "danger" });
        }
    }
}

registry.category("actions").add("vd_user_board", VdUserBoard);
