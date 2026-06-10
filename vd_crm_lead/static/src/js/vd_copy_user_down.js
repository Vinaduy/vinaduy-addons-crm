/** @odoo-module **/
/**
 * Nút "Sao chép NHÂN VIÊN xuống các dòng dưới" cho wizard Thêm KH mới.
 * Client-side: KHÔNG cần lưu — copy thẳng vào các dòng đã nhập (có tên) ngay.
 * User spec 2026-06-10.
 */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

class VdCopyUserDown extends Component {
    static template = "vd_crm_lead.CopyUserDown";
    static props = { ...standardFieldProps };

    setup() {
        this.notification = useService("notification");
    }

    get hasUser() {
        return !!this.props.record.data.user_id;
    }

    async onCopyDown() {
        const rec = this.props.record;
        const uval = rec.data.user_id;
        if (!uval) return;
        // Danh sách dòng (one2many line_ids) của wizard gốc.
        const list = rec.model.root.data.line_ids;
        const records = (list && list.records) || [];
        const myIdx = records.findIndex((r) => r.id === rec.id);
        if (myIdx < 0) return;
        let count = 0;
        for (let i = myIdx + 1; i < records.length; i++) {
            const r = records[i];
            if (r.data && r.data.name) {
                try {
                    await r.update({ user_id: uval });
                    count++;
                } catch (e) {
                    console.warn("copy user down failed", e);
                }
            }
        }
        this.notification.add(
            count
                ? `Đã sao chép nhân viên xuống ${count} khách bên dưới.`
                : "Chưa có khách (đã nhập tên) ở các dòng dưới để sao chép.",
            { type: count ? "success" : "warning" },
        );
    }
}

registry.category("fields").add("vd_copy_user_down", { component: VdCopyUserDown });
