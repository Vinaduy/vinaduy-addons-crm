/** @odoo-module **/
/**
 * CHIA SỐ KH ĐÃ CHỌN — dialog đơn giản (user 2026-10-07).
 *
 * Dùng cho KH chọn bằng KÉO CHUỘT trên dashboard: chọn NV → đổi NV phụ trách
 * (giữ nguyên dữ liệu). UI + style giống hệt bước chia số lúc tải file.
 */
import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class VdNvPickerDialog extends Component {
    static template = "vd_crm_lead.NvPickerDialog";
    static components = { Dialog };
    static props = {
        leadIds: Array,
        onDone: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, nvs: [], selected: {}, nvSearch: "", busy: false,
        });
        onWillStart(async () => {
            try {
                const meta = await this.orm.call("crm.lead", "vd_quickadd_meta", []);
                this.state.nvs = meta.nvs || [];
            } catch (e) {
                this.notification.add("Không tải được danh sách nhân viên.", { type: "danger" });
            }
            this.state.loading = false;
        });
    }

    get nvList() {
        const q = (this.state.nvSearch || "").toLowerCase().trim();
        return this.state.nvs.filter(
            (n) => n.on && (!q || (n.name || "").toLowerCase().includes(q)));
    }
    get selectedCount() {
        return Object.values(this.state.selected).filter(Boolean).length;
    }
    toggleNv(id) {
        this.state.selected[id] = !this.state.selected[id];
    }

    async submit(forceAll) {
        if (this.state.busy) return;
        const ids = forceAll ? [] : Object.keys(this.state.selected)
            .filter((k) => this.state.selected[k]).map((k) => parseInt(k, 10));
        this.state.busy = true;
        try {
            const r = await this.orm.call(
                "crm.lead", "vd_quickadd_distribute", [this.props.leadIds, ids]);
            this.notification.add(
                `✅ Đã chia ${r.moved} khách` + (r.detail ? ` → ${r.detail}` : ""),
                { type: "success" });
            if (this.props.onDone) this.props.onDone(r);
            this.props.close();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Chia số lỗi.", { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }
}
