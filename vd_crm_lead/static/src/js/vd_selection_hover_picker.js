/** @odoo-module **/
/**
 * Selection hover picker — UX hệt vd_m2o_hover_picker nhưng cho Selection field.
 *   - Bar gọn hiển thị label đã chọn (hoặc placeholder).
 *   - HOVER bar → menu xổ ra danh sách 1 cột tất cả options.
 *   - Click option → set value (single-select).
 *   - Click × → xoá (set false).
 *
 * Dùng cho Mẫu nhà / Móng / Loại đất / Đất móng / Ô tô / Sổ đỏ.
 *
 * Bypass OWL t-on-click (đã verify không bind reliably trong context popup):
 * dùng document.addEventListener capture phase đọc data-opt-key.
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// ===== GLOBAL CAPTURE CLICK HANDLER (1 lần cho toàn app) =====
if (!window.__vdShpClickHandlerInstalled) {
    window.__vdShpClickHandlerInstalled = true;
    document.addEventListener("click", (ev) => {
        const target = ev.target;
        if (!(target instanceof Element)) return;

        // Clear button
        const clearBtn = target.closest(".o_vd_shp_clear");
        if (clearBtn) {
            const pickerEl = clearBtn.closest(".o_vd_selection_hover_picker");
            const comp = pickerEl && pickerEl.__vdShp;
            if (comp) {
                ev.preventDefault();
                ev.stopPropagation();
                comp.clearValue(ev);
            }
            return;
        }

        // Option item button
        const itemBtn = target.closest(".o_vd_shp_item");
        if (!itemBtn) return;
        const pickerEl = itemBtn.closest(".o_vd_selection_hover_picker");
        const comp = pickerEl && pickerEl.__vdShp;
        if (!comp) return;
        const key = itemBtn.dataset.optKey;
        if (key == null) return;
        ev.preventDefault();
        ev.stopPropagation();
        comp.selectOption(key, ev);
    }, true);
}

export class VdSelectionHoverPicker extends Component {
    static template = "vd_crm_lead.VdSelectionHoverPicker";
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

        onMounted(() => {
            if (this.rootRef.el) this.rootRef.el.__vdShp = this;
            document.addEventListener("click", this._onDocClick, true);
        });
        onWillUnmount(() => {
            if (this.rootRef.el) delete this.rootRef.el.__vdShp;
            document.removeEventListener("click", this._onDocClick, true);
            if (this._closeTimer) clearTimeout(this._closeTimer);
        });
    }

    get options() {
        // Odoo 18 selection field: [[key, label], ...]
        const fieldDef = this.props.record && this.props.record.fields
            ? this.props.record.fields[this.props.name] : null;
        return (fieldDef && fieldDef.selection) || [];
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || false;
    }

    get currentLabel() {
        const v = this.currentValue;
        if (!v) return "";
        const opt = this.options.find((o) => o[0] === v);
        return opt ? opt[1] : "";
    }

    get hasValue() {
        return Boolean(this.currentValue);
    }

    onMouseEnter() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        this.state.open = true;
    }

    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => { this.state.open = false; }, 180);
    }

    async selectOption(key, ev) {
        if (ev) { try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {} }
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        try {
            await this.props.record.update({ [this.props.name]: key });
        } catch (e) {
            console.error("[vd_shp] update failed:", e);
        }
        // FLUSH ô số đang gõ (Ngang/Dài, m² tầng) RỒI LƯU NGAY — giống pattern an
        // toàn của vd_selection_inline / m2o picker. Trước đây chỉ scheduleSave (hoãn,
        // không flush) nên số vừa gõ ở ô khác bị mất khi chọn picker này.
        try {
            if (window.__vdFlushIntakeInputs) await window.__vdFlushIntakeInputs("shp:" + this.props.name);
            await this.props.record.save();
        } catch (e) { console.error("[vd_shp] save failed:", e); }
        try { this.render(true); } catch (_) {}
        this.state.open = false;
    }

    async clearValue(ev) {
        if (ev) { try { ev.stopPropagation(); } catch (_) {} }
        try {
            await this.props.record.update({ [this.props.name]: false });
        } catch (e) {
            console.error("[vd_shp] clear failed:", e);
        }
        try { this.render(true); } catch (_) {}
    }
}

export const vdSelectionHoverPickerField = {
    component: VdSelectionHoverPicker,
    displayName: "Selection hover picker (dropdown 1-cột)",
    supportedTypes: ["selection"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder || "",
    }),
};

registry.category("fields").add("vd_selection_hover_picker", vdSelectionHoverPickerField);
