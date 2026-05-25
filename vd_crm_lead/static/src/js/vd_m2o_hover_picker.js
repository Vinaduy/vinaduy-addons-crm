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
        this.state = useState({ open: false, options: [], loadedKey: "", debugMsg: "" });
        this.rootRef = useRef("root");

        const fieldDef = this.props.record && this.props.record.fields
            ? this.props.record.fields[this.props.name] : null;
        // Fallback hardcode relation theo tên field nếu auto-detect lỗi
        const FALLBACK_REL = {
            "vd_intake_province_id": "res.country.state",
            "vd_intake_district": "vd.district",
        };
        this.relation = (fieldDef && fieldDef.relation) || FALLBACK_REL[this.props.name] || null;
        console.log("[vd_m2o_hover_picker] mount", this.props.name, "relation:", this.relation);

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
            return false;
        }
        if (this.props.name === "vd_intake_province_id") {
            // Restore VN filter — chỉ tỉnh/thành Việt Nam (36 sau sát nhập 2025).
            return [["country_id.code", "=", "VN"]];
        }
        return [];
    }

    get domainKey() {
        return `${this.relation}|${JSON.stringify(this.fetchDomain)}`;
    }

    /** Ưu tiên thành phố lớn + tỉnh giàu lên đầu danh sách Tỉnh/Thành */
    _sortProvinces(recs) {
        // Order: TP trực thuộc TW → tỉnh kinh tế trọng điểm → còn lại theo tên
        const PRIORITY = [
            "Hà Nội", "Hồ Chí Minh", "TP Hồ Chí Minh", "Thành phố Hồ Chí Minh",
            "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Huế", "Thừa Thiên Huế",
            "Quảng Ninh", "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu", "Bà Rịa Vũng Tàu",
            "Bắc Ninh", "Hưng Yên", "Vĩnh Phúc", "Hải Dương",
            "Khánh Hòa", "Long An", "Tiền Giang", "Quảng Nam",
        ];
        const priorityIdx = (name) => {
            const norm = (name || "").trim();
            for (let i = 0; i < PRIORITY.length; i++) {
                if (norm.includes(PRIORITY[i]) || PRIORITY[i].includes(norm)) {
                    return i;
                }
            }
            return PRIORITY.length;
        };
        return recs.slice().sort((a, b) => {
            const pa = priorityIdx(a.display_name || a.name);
            const pb = priorityIdx(b.display_name || b.name);
            if (pa !== pb) return pa - pb;
            return (a.display_name || a.name || "").localeCompare(b.display_name || b.name || "", "vi");
        });
    }

    async _fetchIfNeeded() {
        if (!this.relation) {
            this.state.debugMsg = "Không có relation";
            return;
        }
        const dom = this.fetchDomain;
        const key = this.domainKey;
        if (key === this.state.loadedKey) return;
        if (dom === false) {
            this.state.options = [];
            this.state.loadedKey = key;
            return;
        }
        try {
            console.log("[vd_m2o_hover_picker] fetch", this.relation, "domain:", dom);
            let recs = await this.orm.searchRead(
                this.relation,
                dom,
                ["id", "display_name", "name"],
                { limit: 1000 }
            );
            recs = recs || [];
            console.log("[vd_m2o_hover_picker] got", recs.length, "records");
            // Sort Province: ưu tiên thành phố lớn + tỉnh giàu lên đầu
            if (this.props.name === "vd_intake_province_id") {
                recs = this._sortProvinces(recs);
            }
            this.state.options = recs;
            this.state.loadedKey = key;
            this.state.debugMsg = "";
        } catch (e) {
            console.error("vd_m2o_hover_picker fetch error:", e);
            this.state.options = [];
            this.state.loadedKey = key;
            this.state.debugMsg = `Lỗi tải: ${e.message || e}`;
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
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        this.state.open = false; // đóng ngay để tránh re-render race
        console.log("[vd_m2o_hover_picker] select", rec.id, rec.display_name || rec.name);
        try {
            await this.props.record.update({
                [this.props.name]: {
                    id: rec.id,
                    display_name: rec.display_name || rec.name || "",
                },
            });
        } catch (e) {
            console.error("[vd_m2o_hover_picker] update error:", e);
        }
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
