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
            alerts: [],   // NV thiếu số sống theo mạng (báo admin)
            loading: true,
            search: "",
            busy: false,
            hover: null, // {number, top, left}
            // Popup chia số: open + map chọn số/NV theo id
            dist: { open: false, nums: {}, users: {} },
        });
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call(MODEL, "get_assignment_board", []);
        this.state.carriers = data.carriers;
        this.state.users = data.users;
        this.state.alerts = data.alerts || [];
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

    // Click vào số = COPY (giống click tên KH). Dùng action copy chế độ silent
    // (copy ngay trong user-gesture, không mở dialog).
    copyNumber(ev, num) {
        ev.stopPropagation();
        this.action.doAction({
            type: "ir.actions.client",
            tag: "vd_copy_to_clipboard",
            params: { text: num, silent: true, message: `Đã copy số ${num}` },
        });
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

    // ============ POPUP CHIA SỐ (chọn số → chọn NV → CHIA SỐ) ============
    openDistModal() {
        const nums = {};
        for (const c of this.state.carriers) {
            for (const n of c.numbers) {
                nums[n.id] = n.health === "alive"; // mặc định: chọn số CÒN SỐNG
            }
        }
        const users = {};
        for (const u of this.state.users) {
            users[u.id] = !u.no_share;             // mặc định: NV không bị loại
        }
        this.state.dist = { open: true, nums, users };
    }
    closeDistModal() {
        this.state.dist.open = false;
    }
    toggleDistNum(id) {
        this.state.dist.nums[id] = !this.state.dist.nums[id];
    }
    toggleDistUser(id) {
        this.state.dist.users[id] = !this.state.dist.users[id];
    }
    get distNumIds() {
        return Object.keys(this.state.dist.nums)
            .filter((id) => this.state.dist.nums[id])
            .map(Number);
    }
    get distUserIds() {
        return Object.keys(this.state.dist.users)
            .filter((id) => this.state.dist.users[id])
            .map(Number);
    }
    distSelectAlive() {
        for (const c of this.state.carriers) {
            for (const n of c.numbers) {
                this.state.dist.nums[n.id] = n.health === "alive";
            }
        }
    }
    distClearNums() {
        for (const k of Object.keys(this.state.dist.nums)) {
            this.state.dist.nums[k] = false;
        }
    }
    distSelectEligible() {
        for (const u of this.state.users) {
            this.state.dist.users[u.id] = !u.no_share;
        }
    }
    distClearUsers() {
        for (const k of Object.keys(this.state.dist.users)) {
            this.state.dist.users[k] = false;
        }
    }
    async doDistribute() {
        const numIds = this.distNumIds;
        const userIds = this.distUserIds;
        if (!numIds.length || !userIds.length) {
            this.notification.add("Chọn ít nhất 1 số và 1 nhân viên.", {
                type: "warning",
            });
            return;
        }
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const res = await this.orm.call(
                MODEL, "distribute_numbers_to_users", [numIds, userIds]
            );
            this.state.dist.open = false;
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
