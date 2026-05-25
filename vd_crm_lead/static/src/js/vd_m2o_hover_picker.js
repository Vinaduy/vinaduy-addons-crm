/** @odoo-module **/
/**
 * Many2one hover picker — UX hệt button "Thêm vấn đề":
 *   - Bar gọn hiển thị giá trị đã chọn (hoặc placeholder).
 *   - HOVER vào bar → menu xổ ra với TẤT CẢ options của model relation
 *     (lọc theo domain trên field hoặc theo logic riêng cho field này).
 *   - Click option → set giá trị (single-select m2o).
 *   - Click × → xoá.
 *
 * Dùng cho Tỉnh / Thành + Huyện / Quận. District tự refetch khi Province đổi.
 *
 * <field name="vd_intake_province_id" widget="vd_m2o_hover_picker" placeholder="..."/>
 */

import { Component, useState, useRef, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class VdM2oHoverPicker extends Component {
    static template = "vd_crm_lead.VdM2oHoverPicker";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false, options: [], loadedKey: "" });
        this.rootRef = useRef("root");
        this.relation = this.props.record.fields[this.props.name].relation;

        this._closeTimer = null;
        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };

        onWillStart(async () => { await this._fetchIfNeeded(); });
        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => {
            document.removeEventListener("click", this._onDocClick, true);
            if (this._closeTimer) clearTimeout(this._closeTimer);
        });
    }

    _extractId(v) {
        if (!v) return false;
        if (typeof v === "number") return v;
        if (Array.isArray(v)) return v[0] || false;
        if (typeof v === "object") return v.id || v.resId || false;
        return false;
    }

    get fetchDomain() {
        if (this.props.name === "vd_intake_district") {
            const prov = this.props.record.data["vd_intake_province_id"];
            const provId = this._extractId(prov);
            if (provId) return [["state_id", "=", provId]];
            return false; // signal empty
        }
        // Province: fetch all (Odoo base data is small) — bỏ filter country_id để
        // tránh fail khi country_id null. Sort theo name.
        return [];
    }

    get domainKey() {
        return `${this.relation}|${JSON.stringify(this.fetchDomain)}`;
    }

    async _fetchIfNeeded() {
        const dom = this.fetchDomain;
        const key = this.domainKey;
        if (key === this.state.loadedKey) return;
        // District khi province chưa chọn → empty
        if (dom === false) {
            this.state.options = [];
            this.state.loadedKey = key;
            return;
        }
        try {
            const recs = await this.orm.searchRead(
                this.relation,
                dom,
                ["id", "display_name"],
                { order: "display_name", limit: 1000 }
            );
            this.state.options = recs || [];
            this.state.loadedKey = key;
        } catch (e) {
            console.error("vd_m2o_hover_picker fetch error:", e);
            this.state.options = [];
            this.state.loadedKey = key;
        }
    }

    get currentDisplay() {
        const v = this.props.record.data[this.props.name];
        if (!v) return "";
        if (typeof v === "object") return v.display_name || "";
        if (Array.isArray(v)) return v[1] || "";
        return "";
    }

    get hasValue() {
        return Boolean(this.props.record.data[this.props.name]);
    }

    async onMouseEnter() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        // Lazy fetch khi domain thay đổi (district refetch khi province đổi)
        await this._fetchIfNeeded();
        this.state.open = true;
    }

    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => { this.state.open = false; }, 180);
    }

    async selectRecord(rec, ev) {
        ev.stopPropagation();
        await this.props.record.update({
            [this.props.name]: { id: rec.id, display_name: rec.display_name },
        });
        this.state.open = false;
    }

    async clearValue(ev) {
        ev.stopPropagation();
        await this.props.record.update({ [this.props.name]: false });
    }
}

export const vdM2oHoverPickerField = {
    component: VdM2oHoverPicker,
    displayName: "M2o hover picker (Thêm vấn đề style)",
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder || "",
    }),
};

registry.category("fields").add("vd_m2o_hover_picker", vdM2oHoverPickerField);
