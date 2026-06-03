/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODEL = "vd.stringee.hotline";

/**
 * Bảng phân bổ số tổng đài theo NV — KÉO-THẢ.
 * Trái: kho số gom theo nhà mạng (mỗi số = 1 chip kéo được).
 * Phải: mỗi NV 1 ô; kéo số từ kho thả vào ô NV để gán.
 *   - Thả số cùng mạng NV đã có → backend tự thay số cũ (1 mạng 1 số).
 *   - Bấm × trên chip trong ô NV để gỡ.
 */
export class VdStringeeAssignmentBoard extends Component {
    static template = "vd_stringee.AssignmentBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            carriers: [],
            users: [],
            loading: true,
            search: "",
            busy: false,
            hover: null, // {number, top, left}
        });
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call(MODEL, "get_assignment_board", []);
        this.state.carriers = data.carriers;
        this.state.users = data.users;
        this.state.loading = false;
    }

    get filteredUsers() {
        const s = (this.state.search || "").trim().toLowerCase();
        if (!s) {
            return this.state.users;
        }
        return this.state.users.filter(
            (u) =>
                (u.name || "").toLowerCase().includes(s) ||
                (u.login || "").toLowerCase().includes(s)
        );
    }

    onDragStart(ev, number, carrier) {
        this.state.hover = null; // ẩn popover khi bắt đầu kéo
        ev.dataTransfer.setData(
            "text/plain",
            JSON.stringify({ id: number.id, carrier })
        );
        ev.dataTransfer.effectAllowed = "copy";
    }

    // ---- Hover popover: bảng chi tiết số (NV / dùng từ / phút gọi / cuộc) ----
    onChipEnter(ev, number) {
        const r = ev.currentTarget.getBoundingClientRect();
        // position:fixed theo viewport → không bị cắt bởi vùng cuộn của kho số.
        this.state.hover = { number, top: Math.round(r.bottom + 6), left: Math.round(r.left) };
    }
    onChipLeave() {
        this.state.hover = null;
    }
    get popStyle() {
        const h = this.state.hover;
        if (!h) {
            return "";
        }
        return `top:${h.top}px; left:${h.left}px;`;
    }

    // ---- Chia đều số Viettel còn sống cho NV đủ điều kiện ----
    async distributeViettel() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const res = await this.orm.call(
                MODEL, "distribute_carrier_evenly", ["viettel"]
            );
            await this.load();
            this.notification.add(res.message || "Đã chia số", {
                type: res.ok ? "success" : "warning",
                sticky: !res.ok,
            });
        } finally {
            this.state.busy = false;
        }
    }

    // ---- Bật/tắt cờ "không chia số" cho 1 NV ----
    async toggleNoShare(user) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "toggle_user_no_share", [user.id, !user.no_share]);
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }

    // ---- Nút mở popup (full màn hình) ----
    openDistribute() {
        this.action.doAction("vd_stringee.action_vd_stringee_distribute_wizard", {
            onClose: () => this.load(),
        });
    }
    openLookup() {
        this.action.doAction("vd_stringee.action_users_stringee_matrix", {
            onClose: () => this.load(),
        });
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
        ev.currentTarget.classList.add("o_vd_drop_hover");
    }

    onDragLeave(ev) {
        ev.currentTarget.classList.remove("o_vd_drop_hover");
    }

    async onDrop(ev, user) {
        ev.preventDefault();
        ev.currentTarget.classList.remove("o_vd_drop_hover");
        if (this.state.busy) {
            return;
        }
        let payload;
        try {
            payload = JSON.parse(ev.dataTransfer.getData("text/plain"));
        } catch (e) {
            return;
        }
        if (!payload || !payload.id) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "assign_user_hotline", [user.id, payload.id]);
            await this.load();
            this.notification.add(`Đã gán số cho ${user.name}`, { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async onRemove(user, hotline) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call(MODEL, "unassign_user_hotline", [user.id, hotline.id]);
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
}

registry
    .category("actions")
    .add("vd_stringee_assignment_board", VdStringeeAssignmentBoard);
