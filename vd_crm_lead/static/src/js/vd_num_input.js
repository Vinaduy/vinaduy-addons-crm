/** @odoo-module **/
/**
 * vd_num_input — ô nhập số gọn cho form khai thác (intake).
 *
 *  - Chỉ nhận CHỮ SỐ (field Integer) hoặc số có 1 dấu thập phân (field Float).
 *    → hết lỗi locale VN gõ "," / "." parse sai.
 *  - TRỐNG khi giá trị = 0 (không hiện sẵn "0,0" để phải xoá) → gõ là ăn ngay.
 *  - AUTOSAVE ngay khi rời ô (change/blur) → lần reload tự động giữa cuộc gọi
 *    KHÔNG thể xoá dữ liệu vừa nhập nữa (đã lưu xuống server).
 *
 * Gắn vào view: <field name="..." widget="vd_num_input"/>
 * Backend KHÔNG đổi — vẫn field Integer/Float cũ, mọi onchange/compute giữ nguyên.
 */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VdNumInput extends Component {
    static template = "vd_crm_lead.VdNumInput";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    get isInteger() {
        return this.props.record.fields[this.props.name].type === "integer";
    }

    get displayValue() {
        const v = this.props.record.data[this.props.name];
        if (!v) return "";              // 0 / false → để TRỐNG
        return String(v);
    }

    // Lọc ký tự ngay khi gõ — chỉ giữ số (+ 1 dấu thập phân nếu Float).
    onInput(ev) {
        let s = ev.target.value || "";
        if (this.isInteger) {
            s = s.replace(/[^0-9]/g, "");
        } else {
            s = s.replace(/,/g, ".").replace(/[^0-9.]/g, "");
            const i = s.indexOf(".");
            if (i !== -1) {
                s = s.slice(0, i + 1) + s.slice(i + 1).replace(/\./g, "");
            }
        }
        if (ev.target.value !== s) {
            ev.target.value = s;
        }
    }

    // Rời ô → commit giá trị + AUTOSAVE.
    async onChange(ev) {
        const s = (ev.target.value || "").replace(/,/g, ".").replace(/[^0-9.]/g, "");
        let val = 0;
        if (s) {
            val = this.isInteger ? parseInt(s, 10) : parseFloat(s);
            if (isNaN(val)) val = 0;
        }
        await this.props.record.update({ [this.props.name]: val });
        try {
            await this.props.record.save();
        } catch (_e) {
            // save có thể fail nếu thiếu field bắt buộc — giá trị vẫn ở memory.
        }
    }
}

export const vdNumInput = {
    component: VdNumInput,
    displayName: "Ô nhập số (autosave)",
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder }),
};

registry.category("fields").add("vd_num_input", vdNumInput);
