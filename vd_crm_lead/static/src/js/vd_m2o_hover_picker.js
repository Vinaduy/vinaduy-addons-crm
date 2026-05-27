/** @odoo-module **/
/**
 * Many2one hover picker — UX hệt button "Thêm vấn đề":
 *   - Bar gọn hiển thị giá trị đã chọn (hoặc placeholder).
 *   - HOVER vào bar → menu xổ ra với TẤT CẢ options của model relation.
 *   - Click option → set giá trị (single-select m2o).
 *   - Click × → xoá.
 *
 * IMPORTANT: t-on-click trong OWL template KHÔNG fire trong context này
 * (đã test debug: click tới DOM nhưng OWL handler không chạy). Workaround:
 * gắn 1 listener CAPTURE-phase ở document, đọc data-rec-id trên button,
 * tìm component qua reference lưu trên rootRef.el → gọi selectRecord thẳng.
 */

import { Component, useState, useRef, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

// ===== GLOBAL CLICK HANDLER (1 lần cho cả app) — bypass OWL t-on-click =====
if (!window.__vdMhpClickHandlerInstalled) {
    window.__vdMhpClickHandlerInstalled = true;
    document.addEventListener("click", (ev) => {
        const target = ev.target;
        if (!(target instanceof Element)) return;

        // Clear button (×)
        const clearBtn = target.closest(".o_vd_mhp_clear");
        if (clearBtn) {
            const pickerEl = clearBtn.closest(".o_vd_m2o_hover_picker");
            const comp = pickerEl && pickerEl.__vdPicker;
            if (comp) {
                ev.preventDefault();
                ev.stopPropagation();
                comp.clearValue(ev);
            }
            return;
        }

        // Item button
        const itemBtn = target.closest(".o_vd_mhp_item");
        if (!itemBtn) return;
        const pickerEl = itemBtn.closest(".o_vd_m2o_hover_picker");
        const comp = pickerEl && pickerEl.__vdPicker;
        if (!comp) return;
        const id = parseInt(itemBtn.dataset.recId, 10);
        if (!id) return;
        const rec = (comp.state.options || []).find((o) => o.id === id);
        if (!rec) return;
        ev.preventDefault();
        ev.stopPropagation();
        comp.selectRecord(rec, ev);
    }, true);  // CAPTURE — fire trước OWL render race
}

export class VdM2oHoverPicker extends Component {
    static template = "vd_crm_lead.VdM2oHoverPicker";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false, options: [], loadedKey: "", search: "" });
        this.rootRef = useRef("root");
        this.searchInputRef = useRef("searchInput");

        const fieldDef = this.props.record && this.props.record.fields
            ? this.props.record.fields[this.props.name] : null;
        const FALLBACK_REL = {
            "vd_intake_province_id": "res.country.state",
            "vd_intake_district": "vd.district",
        };
        this.relation = (fieldDef && fieldDef.relation) || FALLBACK_REL[this.props.name] || null;

        this._closeTimer = null;
        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };

        onWillStart(async () => { await this._fetchIfNeeded(); });
        onMounted(() => {
            // Expose component instance qua DOM element → global click handler gọi được
            if (this.rootRef.el) this.rootRef.el.__vdPicker = this;
            document.addEventListener("click", this._onDocClick, true);
        });
        onWillUnmount(() => {
            if (this.rootRef.el) delete this.rootRef.el.__vdPicker;
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
            return [["country_id.code", "=", "VN"]];
        }
        return [];
    }

    get domainKey() {
        return `${this.relation}|${JSON.stringify(this.fetchDomain)}`;
    }

    _sortProvinces(recs) {
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
        if (!this.relation) return;
        const dom = this.fetchDomain;
        const key = this.domainKey;
        if (key === this.state.loadedKey) return;
        if (dom === false) {
            this.state.options = [];
            this.state.loadedKey = key;
            return;
        }
        try {
            let recs = await this.orm.searchRead(
                this.relation, dom,
                ["id", "display_name", "name"],
                { limit: 1000 }
            );
            recs = recs || [];
            if (this.props.name === "vd_intake_province_id") {
                recs = this._sortProvinces(recs);
            }
            this.state.options = recs;
            this.state.loadedKey = key;
        } catch (e) {
            console.error("vd_m2o_hover_picker fetch error:", e);
            this.state.options = [];
            this.state.loadedKey = key;
        }
    }

    _normalize(s) {
        return (s || "").toLowerCase()
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "")
            .replace(/đ/g, "d").replace(/Đ/g, "D");
    }

    get filteredOptions() {
        const q = this._normalize(this.state.search).trim();
        const opts = this.state.options || [];
        if (!q) return opts;
        const starts = [];
        const contains = [];
        for (const o of opts) {
            const n = this._normalize(o.display_name || o.name || "");
            if (!n) continue;
            if (n.startsWith(q)) {
                starts.push(o);
            } else if (n.includes(q)) {
                contains.push(o);
            } else {
                // Cũng match từng từ — vd "duy" match "Vĩnh Duy"
                const words = n.split(/[\s\-_\/]+/);
                if (words.some((w) => w.startsWith(q))) {
                    contains.push(o);
                }
            }
        }
        return starts.concat(contains);
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
    }

    onSearchKeydown(ev) {
        // Enter → chọn item đầu tiên trong filteredOptions
        if (ev.key === "Enter") {
            const first = this.filteredOptions[0];
            if (first) {
                ev.preventDefault();
                this.selectRecord(first, ev);
            }
        } else if (ev.key === "Escape") {
            this.state.open = false;
        }
    }

    get currentDisplay() {
        const v = this.props.record.data[this.props.name];
        if (!v) return "";
        if (Array.isArray(v)) return v[1] || "";
        if (typeof v === "object") {
            // Odoo 18: cả display_name (snake_case) và displayName (camelCase) đều dùng
            return v.display_name || v.displayName || v.name || "";
        }
        return "";
    }

    get hasValue() {
        return Boolean(this.props.record.data[this.props.name]);
    }

    async onMouseEnter() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        const wasOpen = this.state.open;
        await this._fetchIfNeeded();
        this.state.open = true;
        // Auto-focus search input lần đầu mở menu để NV gõ ngay
        if (!wasOpen) {
            setTimeout(() => {
                try { this.searchInputRef.el && this.searchInputRef.el.focus(); } catch (_) {}
            }, 50);
        }
    }

    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => { this.state.open = false; }, 180);
    }

    async selectRecord(rec, ev) {
        if (ev) { try { ev.stopPropagation(); ev.preventDefault(); } catch (_) {} }
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        const fname = this.props.name;
        const dispName = rec.display_name || rec.name || "";
        console.log("[vd_m2o_picker] selectRecord", fname, "→", rec.id, dispName);

        // STRATEGY 1: thử record.update format object (Odoo 18 standard)
        let updated = false;
        try {
            await this.props.record.update({ [fname]: { id: rec.id, display_name: dispName } });
            updated = true;
            console.log("[vd_m2o_picker] update OBJECT OK, data=", this.props.record.data[fname]);
        } catch (e) {
            console.warn("[vd_m2o_picker] update OBJECT failed:", e);
        }

        // STRATEGY 2: nếu chưa thành công, thử format mảng [id, name]
        if (!updated) {
            try {
                await this.props.record.update({ [fname]: [rec.id, dispName] });
                updated = true;
                console.log("[vd_m2o_picker] update ARRAY OK, data=", this.props.record.data[fname]);
            } catch (e) {
                console.warn("[vd_m2o_picker] update ARRAY failed:", e);
            }
        }

        // STRATEGY 3: nếu vẫn fail (hoặc data không phản ánh), gọi ORM write thẳng
        // rồi reload record. Brute force, đảm bảo lưu DB.
        const curData = this.props.record.data[fname];
        const curId = this._extractId(curData);
        if (!updated || curId !== rec.id) {
            try {
                const resId = this.props.record.resId;
                if (resId) {
                    await this.orm.write(this.props.record.resModel, [resId], { [fname]: rec.id });
                    await this.props.record.load();
                    updated = true;
                    console.log("[vd_m2o_picker] ORM WRITE OK, data=", this.props.record.data[fname]);
                } else {
                    console.warn("[vd_m2o_picker] no resId — can't ORM write");
                }
            } catch (e) {
                console.error("[vd_m2o_picker] ORM WRITE failed:", e);
            }
        }

        // Auto-save form → trigger backend compute vd_intake_complete + auto-lock
        try { await this.props.record.save(); } catch (_) {}
        // Force render để UI bar cập nhật ngay
        try { this.render(true); } catch (_) {}
        this.state.open = false;
        this.state.search = "";
    }

    async clearValue(ev) {
        if (ev) { try { ev.stopPropagation(); } catch (_) {} }
        try {
            await this.props.record.update({ [this.props.name]: false });
        } catch (e) {
            console.error("[vd_m2o_hover_picker] clear failed:", e);
        }
    }
}

export const vdM2oHoverPickerField = {
    component: VdM2oHoverPicker,
    displayName: "M2o hover picker",
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder || "",
    }),
};

registry.category("fields").add("vd_m2o_hover_picker", vdM2oHoverPickerField);
