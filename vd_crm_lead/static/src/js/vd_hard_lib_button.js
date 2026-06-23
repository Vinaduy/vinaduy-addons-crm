/** @odoo-module **/
/**
 * Nút nổi "THƯ VIỆN - Câu hỏi khó" trên TRANG THÔNG TIN KHÁCH HÀNG (form crm.lead).
 * (user spec 2026-06-24)
 *  - Vị trí giữa-phải màn hình (dùng chung class o_vd_lib_filter của vd_elearning)
 *    để KHÔNG che nút gọi điện ở góc dưới.
 *  - ẨN sau khi CHỐT báo giá (stage_is_won = true).
 *  - Mở dialog THƯ VIỆN câu hỏi khó của vd_elearning qua registry chung
 *    (vd_dialogs) — không cần phụ thuộc cứng module học.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class VdHardLibButton extends Component {
    static template = "vd_crm_lead.HardLibButton";
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }

    get available() {
        return registry.category("vd_dialogs").contains("hard_library");
    }
    get hidden() {
        // Chốt báo giá (stage won) -> ẩn. Không có module học -> ẩn.
        const d = this.props.record.data;
        if (d.stage_is_won) return true;
        return !this.available;
    }
    open() {
        const Comp = registry.category("vd_dialogs").get("hard_library", null);
        if (Comp) {
            this.dialog.add(Comp, {});
        } else {
            this.notification.add("Chưa cài module học (THƯ VIỆN câu hỏi).", { type: "warning" });
        }
    }
}

registry.category("fields").add("vd_hard_lib_btn", {
    component: VdHardLibButton,
    supportedTypes: ["boolean"],
});
