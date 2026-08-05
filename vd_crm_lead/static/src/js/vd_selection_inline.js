/** @odoo-module **/
/**
 * vd_selection_inline — Selection field hiển thị LUÔN tất cả lựa chọn dạng chip
 * (không dropdown). Click chip = chọn; click chip đang chọn = bỏ chọn.
 * Phong cách giống chip trong BẢNG BÁO GIÁ TÍNH NHẨM.
 *
 * Dùng: <field name="vd_intake_house_type" widget="vd_selection_inline"/>
 */
import { Component, useState } from "@odoo/owl";
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

    setup() {
        // pending = giá trị vừa bấm, hiện sáng NGAY trong lúc chờ onchange server.
        // Không có nó, chip mất 0,3-1s mới sáng → NV tưởng hụt, bấm lại lần 2 →
        // lần 2 rơi vào nhánh "bấm lại chip đang chọn = BỎ CHỌN" → mất dữ liệu.
        this.state = useState({ pending: null });
        this._lastPickTs = 0;
        this._lastPickVal = null;
    }

    get options() {
        const all = this.props.record.fields[this.props.name].selection || [];
        const ex = this.props.exclude || [];
        return ex.length ? all.filter((o) => !ex.includes(o[0])) : all;
    }
    get value() {
        if (this.state.pending !== null) return this.state.pending;
        return this.props.record.data[this.props.name] || false;
    }
    async pick(val) {
        const now = Date.now();
        // Bấm lại CÙNG 1 chip trong 1,2s = bấm sốt ruột, KHÔNG phải ý định bỏ chọn.
        if (val === this._lastPickVal && now - this._lastPickTs < 1200) return;
        this._lastPickVal = val;
        this._lastPickTs = now;
        const nv = val === this.value ? false : val;
        this.state.pending = nv;   // sáng/tắt ngay, không chờ server
        try {
            await this.props.record.update({ [this.props.name]: nv });
            // Tắt tay → cấm onchange server tự điền lại (và ngược lại khi chọn lại).
            if (window.__vdMarkManualOff) {
                await window.__vdMarkManualOff(this.props.record, this.props.name, nv === false);
            }
        } finally {
            this.state.pending = null;
        }
        // Lưu ngầm qua đường DUY NHẤT: record.save({reload:false}) — xuống DB
        // ngay nhưng KHÔNG đọc lại/dựng lại form nên không nuốt gì.
        try { if (window.__vdCommitIntakeChange) window.__vdCommitIntakeChange(this.props.record, "sel-inline:" + this.props.name); } catch (_) {}
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
