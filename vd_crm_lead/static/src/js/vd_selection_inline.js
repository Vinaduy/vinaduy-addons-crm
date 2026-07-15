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
    static props = {
        ...standardFieldProps,
        // options="{'exclude': ['mai_ton']}" -> ẩn các option này khỏi hàng chip
        // (vd Nhà mái tôn đã chuyển vào popup KHÁC).
        exclude: { type: Array, optional: true },
    };

    get options() {
        const all = this.props.record.fields[this.props.name].selection || [];
        const ex = this.props.exclude || [];
        return ex.length ? all.filter((o) => !ex.includes(o[0])) : all;
    }
    get value() {
        return this.props.record.data[this.props.name] || false;
    }
    async pick(val) {
        const nv = val === this.value ? false : val;
        await this.props.record.update({ [this.props.name]: nv });
        // LƯU NGAY (không debounce) để KHÔNG mất dữ liệu khi bấm ra ngoài.
        // Flush các ô số đang gõ TRƯỚC để reload-sau-save không nuốt số in-flight
        // (xem memory: intake_save_wipes_inflight_number).
        try {
            if (window.__vdFlushIntakeInputs) {
                await window.__vdFlushIntakeInputs("sel-inline:" + this.props.name);
            }
        } catch (_e) { /* ignore */ }
        try {
            await this.props.record.save();
        } catch (e) {
            console.error("[vd_selinline] save failed:", e);
        }
    }
}

export const vdSelectionInlineField = {
    component: VdSelectionInline,
    displayName: "Lựa chọn dạng chip (hiện hết)",
    supportedTypes: ["selection"],
    extractProps: ({ options }) => ({
        exclude: (options && options.exclude) || [],
    }),
};

registry.category("fields").add("vd_selection_inline", vdSelectionInlineField);
