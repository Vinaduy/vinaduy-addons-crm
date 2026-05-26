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

// ============= GLOBAL DEBUG: bắt mọi click ở body trong CAPTURE phase =============
// Mục đích: xác định click có tới được button .o_vd_mhp_item hay không, và
// nếu KHÔNG thì handler nào / element nào chặn (stopPropagation / pointer-events).
if (!window.__vdMhpDebugInstalled) {
    window.__vdMhpDebugInstalled = true;
    const showBanner = (text, color) => {
        let b = document.getElementById("__vd_mhp_debug_banner");
        if (!b) {
            b = document.createElement("div");
            b.id = "__vd_mhp_debug_banner";
            b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999999;padding:8px 16px;font:bold 13px monospace;color:#fff;white-space:pre-wrap;max-height:30vh;overflow:auto;";
            document.body.appendChild(b);
        }
        b.style.background = color;
        b.textContent = text;
    };
    document.addEventListener("click", (ev) => {
        const t = ev.target;
        if (!(t instanceof Element)) return;
        const inMenu = t.closest(".o_vd_mhp_menu");
        const inItem = t.closest(".o_vd_mhp_item");
        const inPicker = t.closest(".o_vd_m2o_hover_picker");
        if (inMenu || inItem || inPicker) {
            const path = [];
            let el = t;
            while (el && el !== document.body && path.length < 8) {
                path.push(`${el.tagName.toLowerCase()}${el.className ? "." + String(el.className).split(" ").slice(0, 2).join(".") : ""}`);
                el = el.parentElement;
            }
            showBanner(
                `🟢 CLICK CAPTURED @body\n` +
                `target: ${t.tagName} ${t.className}\n` +
                `inMenu=${!!inMenu} inItem=${!!inItem} inPicker=${!!inPicker}\n` +
                `path: ${path.join(" > ")}`,
                "#16a34a"
            );
            // tự xoá sau 4s
            setTimeout(() => {
                const b = document.getElementById("__vd_mhp_debug_banner");
                if (b) b.remove();
            }, 4000);
        }
    }, true);
    // Capture mousedown cũng để check
    document.addEventListener("mousedown", (ev) => {
        const t = ev.target;
        if (!(t instanceof Element)) return;
        if (t.closest(".o_vd_mhp_item")) {
            console.log("[vd_mhp_debug] mousedown on item:", t);
        }
    }, true);
    console.log("[vd_mhp_debug] Global capture listeners installed");
}

export class VdM2oHoverPicker extends Component {
    static template = "vd_crm_lead.VdM2oHoverPicker";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false, options: [], loadedKey: "", debugMsg: "", lastError: "" });
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
        console.log("[vd_m2o_hover_picker] SELECT START", this.props.name, "→", rec.id, rec.display_name || rec.name);
        this.state.lastError = "";
        // Update TRƯỚC, đóng menu SAU — tránh re-render xoá button giữa mousedown-mouseup
        try {
            const payload = { id: rec.id, display_name: rec.display_name || rec.name || "" };
            await this.props.record.update({ [this.props.name]: payload });
            const after = this.props.record.data[this.props.name];
            console.log("[vd_m2o_hover_picker] SELECT OK", this.props.name, "data=", after);
            this.state.open = false;
        } catch (e) {
            const msg = (e && (e.message || e.data?.message)) || String(e);
            console.error("[vd_m2o_hover_picker] SELECT FAIL:", e);
            this.state.lastError = msg;
            // Thử format mảng [id, display_name] (Odoo cũ) làm fallback
            try {
                console.warn("[vd_m2o_hover_picker] retry với format mảng [id, name]");
                await this.props.record.update({
                    [this.props.name]: [rec.id, rec.display_name || rec.name || ""],
                });
                console.log("[vd_m2o_hover_picker] RETRY OK");
                this.state.lastError = "";
                this.state.open = false;
            } catch (e2) {
                const msg2 = (e2 && (e2.message || e2.data?.message)) || String(e2);
                console.error("[vd_m2o_hover_picker] RETRY FAIL:", e2);
                this.state.lastError = `Lỗi cập nhật: ${msg2}`;
            }
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
