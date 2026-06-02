/** @odoo-module **/
/**
 * vd_num_input — ô nhập số gọn cho form khai thác (intake).
 *
 *  - Chỉ nhận CHỮ SỐ (field Integer) hoặc số có 1 dấu thập phân (field Float).
 *  - TRỐNG khi giá trị = 0 (không hiện sẵn "0,0") → gõ là ăn ngay.
 *  - Dùng useInputField (hook chuẩn Odoo): KHÔNG reset input khi đang focus/gõ
 *    dở → gõ nhanh rồi nhảy ô khác KHÔNG mất chữ (kể cả khi có onchange/re-render
 *    do tính lại TỔNG). Commit value vào record lúc change/blur.
 *  - AUTOSAVE debounce + biết focus: chỉ thật lưu (kéo reload) khi NV đã rời hẳn
 *    khu nhập intake → reload không thể xoá chữ đang gõ.
 *
 * Gắn: <field name="..." widget="vd_num_input"/>  — backend KHÔNG đổi.
 */
import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";

// Debounce CHUNG cho mọi ô — chỉ thật lưu khi NV đã rời hẳn khu nhập.
let _vdNumSaveTimer = null;

export class VdNumInput extends Component {
    static template = "vd_crm_lead.VdNumInput";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.inputRef = useRef("input");
        // Hook chuẩn Odoo: tự set value từ record CHỈ khi input không dirty/không
        // focus, tự commit (record.update) lúc change. Tránh ghi đè chữ đang gõ.
        useInputField({
            getValue: () => {
                const v = this.props.record.data[this.props.name];
                return v ? String(v) : "";
            },
            refName: "input",
            parse: (value) => this._parse(value),
        });
    }

    get isInteger() {
        return this.props.record.fields[this.props.name].type === "integer";
    }

    _parse(value) {
        const s = (value || "").replace(/,/g, ".").replace(/[^0-9.]/g, "");
        if (!s) {
            return 0;
        }
        const v = this.isInteger ? parseInt(s, 10) : parseFloat(s);
        return isNaN(v) ? 0 : v;
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

    // useInputField đã commit value vào record. Ở đây chỉ lên lịch autosave.
    onChange() {
        const record = this.props.record;
        if (_vdNumSaveTimer) {
            clearTimeout(_vdNumSaveTimer);
        }
        _vdNumSaveTimer = setTimeout(() => {
            _vdNumSaveTimer = null;
            const ae = document.activeElement;
            if (ae && ae.closest && ae.closest(".o_vd_steps_panel")) {
                return;     // vẫn đang nhập ô intake khác → khoan lưu
            }
            record.save().catch(() => {});
        }, 450);
    }
}

export const vdNumInput = {
    component: VdNumInput,
    displayName: "Ô nhập số (autosave)",
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder }),
};

registry.category("fields").add("vd_num_input", vdNumInput);
