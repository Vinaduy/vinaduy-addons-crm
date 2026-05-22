/** @odoo-module **/
/**
 * Custom Selection widget — render giống Many2one (input + custom dropdown)
 * thay vì native <select>. Mục đích:
 *   - Empty state: input hiển thị placeholder mờ italic native
 *   - Click → dropdown CHỈ hiện options thật, KHÔNG có dòng kịch bản
 *   - Chọn → đóng dropdown, value hiển thị trong input
 *
 * Dùng: <field name="vd_intake_position" widget="vd_selection_dropdown"
 *              placeholder="Vị trí công trình là mặt tiền hay trong hẻm ạ?"/>
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class VdSelectionDropdown extends Component {
    static template = "vd_crm_lead.VdSelectionDropdown";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        // filterField: tên field khác trên record. Dựa vào value của field đó,
        //              ta lookup filterMap để lấy danh sách option keys cho phép.
        filterField: { type: String, optional: true },
        // filterMap: { kindValue: [allowedSubtypeKey, ...], ... }
        filterMap: { type: Object, optional: true },
        // extensible: cho phép user gõ value mới + bấm "+ Thêm" → tạo record
        //             vd.field.option mới rồi auto-select.
        extensible: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({ open: false, search: "", localExtras: [] });
        this.rootRef = useRef("root");
        this.orm = useService("orm");
        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick, true));
    }

    get options() {
        const fieldDef = this.props.record.fields[this.props.name];
        const base = fieldDef && fieldDef.selection ? [...fieldDef.selection] : [];
        // Merge local extras (vừa thêm qua "+ Thêm mới" trong session)
        for (const [k, l] of this.state.localExtras) {
            if (!base.find(([kk]) => kk === k)) base.push([k, l]);
        }

        // Lọc options theo filter_field + filter_map
        if (this.props.filterField && this.props.filterMap) {
            const parentVal = this.props.record.data[this.props.filterField];
            const allowed = this.props.filterMap[parentVal];
            if (Array.isArray(allowed)) {
                return base.filter(([key, _]) => allowed.includes(key));
            }
            return [];
        }
        return base;
    }

    get canAddNew() {
        if (!this.props.extensible) return false;
        const q = (this.state.search || "").trim();
        if (q.length < 2) return false;
        const lower = q.toLowerCase();
        // Ẩn nếu label trùng với option đã có
        return !this.options.some(
            ([_, l]) => (l || "").toLowerCase() === lower,
        );
    }

    async onAddNew() {
        const label = (this.state.search || "").trim();
        if (!label) return;
        try {
            const result = await this.orm.call(
                "vd.field.option",
                "quick_add",
                [this.props.record.resModel, this.props.name, label],
            );
            if (result && result.key) {
                this.state.localExtras.push([result.key, result.label]);
                this.selectOption(result.key);
            }
        } catch (e) {
            console.error("vd_selection_dropdown quick_add failed", e);
        }
    }

    get filteredOptions() {
        const q = (this.state.search || "").toLowerCase().trim();
        if (!q) return this.options;
        return this.options.filter(([_, label]) =>
            (label || "").toLowerCase().includes(q)
        );
    }

    get currentValue() {
        return this.props.record.data[this.props.name];
    }

    get currentLabel() {
        const opt = this.options.find((o) => o[0] === this.currentValue);
        return opt ? opt[1] : "";
    }

    get hasValue() {
        return Boolean(this.currentValue);
    }

    toggleOpen() {
        this.state.open = !this.state.open;
        if (this.state.open) this.state.search = "";
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
        if (!this.state.open) this.state.open = true;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.state.open = false;
            ev.target.blur();
        } else if (ev.key === "Enter") {
            const filtered = this.filteredOptions;
            if (filtered.length > 0) {
                this.selectOption(filtered[0][0]);
                ev.preventDefault();
            }
        } else if (ev.key === "ArrowDown") {
            this.state.open = true;
        }
    }

    selectOption(value) {
        this.props.record.update({ [this.props.name]: value });
        this.state.open = false;
        this.state.search = "";
    }

    clearValue(ev) {
        ev.stopPropagation();
        this.props.record.update({ [this.props.name]: false });
    }
}

export const vdSelectionDropdownField = {
    component: VdSelectionDropdown,
    displayName: "Selection (dropdown như Many2one)",
    supportedTypes: ["selection"],
    extractProps: ({ attrs, options }) => ({
        placeholder: attrs.placeholder || "",
        filterField: (options && options.filter_field) || null,
        filterMap: (options && options.filter_map) || null,
        extensible: Boolean(options && options.extensible),
    }),
};

registry.category("fields").add("vd_selection_dropdown", vdSelectionDropdownField);
