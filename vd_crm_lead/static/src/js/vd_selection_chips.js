/** @odoo-module **/
/**
 * Single-select chip widget cho Selection field — UX hệt vd_floor_function_chips
 * nhưng single-value (set/unset 1 option).
 *
 * Bar gọn: chip giá trị hiện tại + caret. Hover bar → panel mở với MỌI option
 * dạng chip → click chip = set value (replace previous).
 *
 * Selection options đọc từ this.props.record.fields[name].selection.
 *
 * Dùng: <field name="vd_intake_house_type" widget="vd_selection_chips"
 *                placeholder="Mái bằng / Mái Thái...?"/>
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VdSelectionChips extends Component {
    static template = "vd_crm_lead.VdSelectionChips";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.state = useState({ open: false });
        this.rootRef = useRef("root");

        this._closeTimer = null;
        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };

        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => {
            document.removeEventListener("click", this._onDocClick, true);
            if (this._closeTimer) clearTimeout(this._closeTimer);
        });
    }

    get options() {
        // Odoo 18: field.selection = [[value, label], ...]
        return this.props.record.fields[this.props.name].selection || [];
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || false;
    }

    get currentLabel() {
        const opt = this.options.find((o) => o[0] === this.currentValue);
        return opt ? opt[1] : "";
    }

    get hasValue() {
        return Boolean(this.currentValue);
    }

    isSelected(value) {
        return value === this.currentValue;
    }

    onMouseEnter() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        this.state.open = true;
    }

    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => { this.state.open = false; }, 380);
    }

    async onChipClick(value, ev) {
        ev.stopPropagation();
        // Bấm lại CÙNG chip trong 1,2s = sốt ruột chờ server, KHÔNG phải muốn bỏ
        // chọn → bỏ qua (trước đây lần bấm thứ 2 xoá luôn lựa chọn vừa chọn).
        const now = Date.now();
        if (value === this._lastPickVal && now - this._lastPickTs < 1200) return;
        this._lastPickVal = value;
        this._lastPickTs = now;
        // Click vào chip đang chọn → bỏ chọn (clear). Click khác → set value mới.
        const newVal = (value === this.currentValue) ? false : value;
        await this.props.record.update({ [this.props.name]: newVal });
        // Tắt tay → cấm onchange server tự điền lại.
        try {
            if (window.__vdMarkManualOff) {
                await window.__vdMarkManualOff(this.props.record, this.props.name, newVal === false);
            }
        } catch (_) {}
        // KHÔNG save() ngay (reload nuốt ô số/lựa chọn đang nhập). Lưu-ngầm có bảo vệ.
        try { if (window.__vdCommitIntakeChange) window.__vdCommitIntakeChange(this.props.record, "sel-chip:" + this.props.name); } catch (_) {}
        this.state.open = false;
    }

    async clearValue(ev) {
        ev.stopPropagation();
        await this.props.record.update({ [this.props.name]: false });
        try {
            if (window.__vdMarkManualOff) {
                await window.__vdMarkManualOff(this.props.record, this.props.name, true);
            }
        } catch (_) {}
        try { if (window.__vdCommitIntakeChange) window.__vdCommitIntakeChange(this.props.record, "sel-chip-clear"); } catch (_) {}
    }
}

export const vdSelectionChipsField = {
    component: VdSelectionChips,
    displayName: "Selection chips (single-select hover panel)",
    supportedTypes: ["selection"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder || "",
    }),
};

registry.category("fields").add("vd_selection_chips", vdSelectionChipsField);
