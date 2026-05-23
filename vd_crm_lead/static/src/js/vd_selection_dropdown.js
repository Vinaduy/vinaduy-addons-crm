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
        onMounted(() => {
            document.addEventListener("click", this._onDocClick, true);
            // KHÔNG auto-open trên mount — sẽ trigger cho TẤT CẢ widgets cùng row
            // khi user add line / chọn row, gây menu stack chồng chéo.
            // Mở dropdown chỉ qua interaction explicit: onWrapperClick (user click)
            // hoặc quick_add_hover_open.js (hover cell trong wizard).
        });
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick, true));
    }

    /** Inline style cho menu — position:fixed neo theo bounding rect của root,
     *  thoát mọi overflow:hidden của parent (table cell / modal body). */
    get menuStyle() {
        if (!this.state.open || !this.rootRef.el) return "";
        const rect = this.rootRef.el.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const menuMaxH = 320;
        // Nếu không đủ chỗ phía dưới → flip lên trên
        const flipUp = spaceBelow < 200 && rect.top > spaceBelow;
        const top = flipUp ? `${rect.top - Math.min(menuMaxH, rect.top - 8)}px` : `${rect.bottom + 2}px`;
        const minWidth = Math.max(rect.width, 200);
        return `position: fixed; top: ${top}; left: ${rect.left}px; min-width: ${minWidth}px; max-width: calc(100vw - 32px); max-height: ${menuMaxH}px; z-index: 10000;`;
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

    onWrapperClick(ev) {
        // Click bất kỳ vị trí nào trên wrapper (input, arrow, padding) → mở dropdown.
        // Skip nếu click vào button clear (nó tự xoá value).
        if (ev.target.closest(".o_vd_select_dd_clear")) return;
        if (!this.state.open) {
            this.state.open = true;
            this.state.search = "";
            // Focus input sau khi state update (đợi 1 tick để readonly attr bị remove)
            Promise.resolve().then(() => {
                const inp = this.rootRef.el?.querySelector(".o_vd_select_dd_input");
                inp?.focus();
            });
        }
    }

    onArrowClick(ev) {
        ev.stopPropagation();
        this.toggleOpen();
        if (this.state.open) {
            Promise.resolve().then(() => {
                const inp = this.rootRef.el?.querySelector(".o_vd_select_dd_input");
                inp?.focus();
            });
        }
    }

    onInputFocus() {
        // Khi list editable cell trao focus cho input (Tab key / autoEnter) → mở dropdown.
        if (!this.state.open) {
            this.state.open = true;
            this.state.search = "";
        }
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
            } else if (this.canAddNew) {
                ev.preventDefault();
                this.onAddNew();
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
