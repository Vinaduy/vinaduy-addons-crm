/** @odoo-module **/
/**
 * vd_selection_inline — Selection field hiển thị LUÔN tất cả lựa chọn dạng chip
 * (không dropdown). Click chip = chọn; click chip đang chọn = bỏ chọn.
 * Phong cách giống chip trong BẢNG BÁO GIÁ TÍNH NHẨM.
 *
 * Dùng: <field name="vd_intake_house_type" widget="vd_selection_inline"/>
 */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VdSelectionInline extends Component {
    static template = "vd_crm_lead.VdSelectionInline";
    static props = { ...standardFieldProps };

    get options() {
        return this.props.record.fields[this.props.name].selection || [];
    }
    get value() {
        return this.props.record.data[this.props.name] || false;
    }
    async pick(val) {
        const nv = val === this.value ? false : val;
        await this.props.record.update({ [this.props.name]: nv });
        try {
            if (window.__vdScheduleIntakeSave) {
                window.__vdScheduleIntakeSave(this.props.record, "sel-inline:" + this.props.name);
            }
        } catch (_e) { /* ignore */ }
    }
}

export const vdSelectionInlineField = {
    component: VdSelectionInline,
    displayName: "Lựa chọn dạng chip (hiện hết)",
    supportedTypes: ["selection"],
};

registry.category("fields").add("vd_selection_inline", vdSelectionInlineField);
