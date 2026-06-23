/** @odoo-module **/
/**
 * Bảng quản lý nhân viên — 2 cột kéo thả:
 *   - Đang hoạt động (active)
 *   - Nghỉ việc / Tạm dừng (archived)
 * Kéo thẻ giữa 2 cột → archive/unarchive NV (RPC vd_set_user_active).
 * Mỗi NV = 1 thẻ gọn: mã icon (chữ cái đầu), tên, phòng ban, vai trò.
 * Trưởng nhóm = viền vàng. Màu thẻ theo phòng ban (giống danh sách NV).
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class VdUserBoard extends Component {
    static template = "vd_crm_lead.VdUserBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            working: [],
            off: [],
            loading: true,
            search: "",
            dragUid: null,
            dragFrom: null,
            overCol: null,
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

    _filter(list) {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) return list;
        return list.filter((c) =>
            (c.name + " " + c.code + " " + c.team + " " + c.login).toLowerCase().includes(q)
        );
    }
    get workingList() { return this._filter(this.state.working); }
    get offList() { return this._filter(this.state.off); }

    _sortCards(arr) {
        arr.sort((a, b) => {
            const ka = (a.team + a.name).toLowerCase();
            const kb = (b.team + b.name).toLowerCase();
            return ka < kb ? -1 : ka > kb ? 1 : 0;
        });
    }

    onDragStart(ev, card, from) {
        this.state.dragUid = card.id;
        this.state.dragFrom = from;
        ev.dataTransfer.effectAllowed = "move";
        try { ev.dataTransfer.setData("text/plain", String(card.id)); } catch (e) { /* noop */ }
    }
    onDragOver(ev, col) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        this.state.overCol = col;
    }
    onDragLeave(col) {
        if (this.state.overCol === col) this.state.overCol = null;
    }

    async onDrop(ev, toCol) {
        ev.preventDefault();
        const uid = this.state.dragUid;
        const from = this.state.dragFrom;
        this.state.overCol = null;
        this.state.dragUid = null;
        this.state.dragFrom = null;
        if (!uid || !from || from === toCol) return;

        const working = toCol === "working";
        const srcArr = from === "working" ? this.state.working : this.state.off;
        const dstArr = working ? this.state.working : this.state.off;
        const idx = srcArr.findIndex((c) => c.id === uid);
        if (idx < 0) return;
        // Di chuyển ngay trên UI (optimistic), rollback nếu RPC lỗi.
        const [card] = srcArr.splice(idx, 1);
        card.active = working;
        dstArr.push(card);
        this._sortCards(dstArr);
        try {
            await this.orm.call("res.users", "vd_set_user_active", [uid, working]);
        } catch (e) {
            const j = dstArr.findIndex((c) => c.id === uid);
            if (j >= 0) {
                const [back] = dstArr.splice(j, 1);
                back.active = !working;
                srcArr.push(back);
                this._sortCards(srcArr);
            }
            const msg = (e && e.data && e.data.message) || "Không đổi được trạng thái nhân viên.";
            this.notification.add(msg, { type: "danger" });
        }
    }

    openUser(card) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: card.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            views: [[false, "form"]],
            target: "current",
        });
    }
    openStandard() {
        this.action.doAction("base.action_res_users");
    }
}

registry.category("actions").add("vd_user_board", VdUserBoard);
