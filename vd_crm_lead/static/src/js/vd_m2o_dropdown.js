/** @odoo-module **/
/**
 * Single-select Many2one dropdown — THIẾT KẾ GIỐNG Ô "THỜI GIAN"
 * (vd_timeline_chips) để ĐỠ LỖI mạng:
 *
 *   1. Options TẢI 1 LẦN rồi CACHE client-side → mở dropdown KHÔNG gọi server
 *      (mạng yếu/chập vẫn mở + chọn được, không "trắng vì rớt mạng").
 *   2. Bar gọn (hiện giá trị / placeholder) + dropdown 1 CỘT sạch (không
 *      double-box như picker cũ). Có ô gõ lọc nhanh (huyện nhiều).
 *   3. Chọn Huyện → set luôn Tỉnh = huyện.state_id NGAY TẠI CLIENT (không chờ
 *      onchange server) → hết cảnh "chọn Huyện mất Tỉnh".
 *   4. Vẫn là m2o thật (lưu đúng id) → không phá domain lọc / báo cáo.
 *
 * Dùng: <field name="vd_intake_province_id" widget="vd_m2o_dropdown"/>
 *       <field name="vd_intake_district"   widget="vd_m2o_dropdown"/>
 *
 * Chống race chọn-option-khi-có-ô-search: BIND TRÊN mousedown (fire TRƯỚC khi
 * input blur) + KHÔNG đóng dropdown theo input-blur. Chỉ đóng khi: click ra
 * ngoài / rời chuột / đã chọn xong.
 */

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const FALLBACK_REL = {
    vd_intake_province_id: "res.country.state",
    vd_intake_district: "vd.district",
};

// Tỉnh/TP lớn lên đầu cho NV chọn nhanh.
const PROVINCE_PRIORITY = [
    "Hà Nội", "Hồ Chí Minh", "TP Hồ Chí Minh", "Thành phố Hồ Chí Minh",
    "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Huế", "Thừa Thiên Huế",
    "Quảng Ninh", "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu",
    "Bắc Ninh", "Hưng Yên", "Vĩnh Phúc", "Hải Dương",
    "Khánh Hòa", "Long An", "Tiền Giang", "Quảng Nam",
];

export class VdM2oDropdown extends Component {
    static template = "vd_crm_lead.VdM2oDropdown";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false, options: [], loadedKey: "", search: "" });
        this.rootRef = useRef("root");
        this.searchRef = useRef("search");
        this._closeTimer = null;

        const fieldDef = this.props.record && this.props.record.fields
            ? this.props.record.fields[this.props.name] : null;
        this.relation = (fieldDef && fieldDef.relation) || FALLBACK_REL[this.props.name] || null;
        this.isDistrict = this.props.name === "vd_intake_district";
        this.isProvince = this.props.name === "vd_intake_province_id";

        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this._close();
            }
        };

        onWillStart(async () => { await this._fetchIfNeeded(); });
        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => {
            document.removeEventListener("click", this._onDocClick, true);
            if (this._closeTimer) clearTimeout(this._closeTimer);
        });
    }

    // ---------- data ----------
    _extractId(v) {
        if (!v) return false;
        if (typeof v === "number") return v;
        if (Array.isArray(v)) return v[0] || false;
        if (typeof v === "object") return v.id || v.resId || false;
        return false;
    }

    get _provinceId() {
        return this._extractId(this.props.record.data["vd_intake_province_id"]);
    }

    get fetchDomain() {
        if (this.isDistrict) {
            const provId = this._provinceId;
            if (!provId) return false;            // chưa chọn Tỉnh → chưa load
            return [["state_id", "=", provId]];
        }
        if (this.isProvince) {
            return [["country_id.code", "=", "VN"], ["vd_is_active_2025", "=", true]];
        }
        return [];
    }

    get domainKey() {
        return `${this.relation}|${JSON.stringify(this.fetchDomain)}`;
    }

    _sortProvinces(recs) {
        const idx = (name) => {
            const norm = (name || "").trim();
            for (let i = 0; i < PROVINCE_PRIORITY.length; i++) {
                if (norm.includes(PROVINCE_PRIORITY[i]) || PROVINCE_PRIORITY[i].includes(norm)) {
                    return i;
                }
            }
            return PROVINCE_PRIORITY.length;
        };
        return recs.slice().sort((a, b) => {
            const pa = idx(a.display_name || a.name);
            const pb = idx(b.display_name || b.name);
            if (pa !== pb) return pa - pb;
            return (a.display_name || a.name || "").localeCompare(b.display_name || b.name || "", "vi");
        });
    }

    async _fetchIfNeeded() {
        if (!this.relation) return;
        const dom = this.fetchDomain;
        const key = this.domainKey;
        if (key === this.state.loadedKey) return;       // CACHE — không gọi lại
        if (dom === false) {                            // district chưa có tỉnh
            this.state.options = [];
            this.state.loadedKey = key;
            return;
        }
        // District cần state_id để set lại Tỉnh client-side khi chọn.
        const fields = this.isDistrict
            ? ["id", "display_name", "name", "state_id"]
            : ["id", "display_name", "name"];
        try {
            let recs = await this.orm.searchRead(this.relation, dom, fields, { limit: 1000 });
            recs = recs || [];
            if (this.isProvince) recs = this._sortProvinces(recs);
            this.state.options = recs;
            this.state.loadedKey = key;
        } catch (e) {
            // Mạng rớt khi tải: GIỮ options cache cũ (nếu có) để vẫn chọn được.
            console.warn("[vd_m2o_dropdown] fetch failed, keep cache:", e);
        }
    }

    // ---------- display / filter ----------
    _normalize(s) {
        return (s || "").toLowerCase()
            .normalize("NFD").replace(/[̀-ͯ]/g, "")
            .replace(/đ/g, "d").replace(/Đ/g, "D");
    }

    get currentDisplay() {
        const v = this.props.record.data[this.props.name];
        if (!v) return "";
        if (Array.isArray(v)) return v[1] || "";
        if (typeof v === "object") return v.display_name || v.displayName || v.name || "";
        return "";
    }

    get hasValue() {
        return Boolean(this.props.record.data[this.props.name]);
    }

    get filteredOptions() {
        const q = this._normalize(this.state.search).trim();
        const opts = this.state.options || [];
        if (!q) return opts;
        const starts = [], contains = [];
        for (const o of opts) {
            const n = this._normalize(o.display_name || o.name || "");
            if (!n) continue;
            if (n.startsWith(q)) starts.push(o);
            else if (n.includes(q) || n.split(/[\s\-_/]+/).some((w) => w.startsWith(q))) contains.push(o);
        }
        return starts.concat(contains);
    }

    isCurrent(rec) {
        return this._extractId(this.props.record.data[this.props.name]) === rec.id;
    }

    // ---------- open/close ----------
    async _open() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        await this._fetchIfNeeded();
        this.state.open = true;
        setTimeout(() => { try { this.searchRef.el && this.searchRef.el.focus(); } catch (_) {} }, 30);
    }
    _close() {
        this.state.open = false;
        this.state.search = "";
    }
    toggleBar(ev) {
        if (ev) ev.stopPropagation();
        if (this.state.open) this._close();
        else this._open();
    }
    onMouseEnter() { this._open(); }
    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => this._close(), 180);
    }
    onSearchInput(ev) { this.state.search = ev.target.value || ""; this.state.open = true; }
    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            const first = this.filteredOptions[0];
            if (first) { ev.preventDefault(); this.selectRecord(first, ev); }
        } else if (ev.key === "Escape") {
            this._close();
        }
    }

    // ---------- commit ----------
    async selectRecord(rec, ev) {
        if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (_) {} }
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        const fname = this.props.name;
        const disp = rec.display_name || rec.name || "";
        try {
            const vals = { [fname]: { id: rec.id, display_name: disp } };
            // Chọn Huyện → set luôn Tỉnh = huyện.state_id (client-side, không
            // chờ onchange server) → không bao giờ "mất Tỉnh" khi rớt mạng.
            if (this.isDistrict && rec.state_id) {
                const sid = Array.isArray(rec.state_id) ? rec.state_id[0] : this._extractId(rec.state_id);
                const sname = Array.isArray(rec.state_id) ? rec.state_id[1] : "";
                if (sid) vals["vd_intake_province_id"] = { id: sid, display_name: sname };
            }
            await this.props.record.update(vals);
        } catch (e) {
            console.error("[vd_m2o_dropdown] update failed:", e);
        }
        this._close();
        // Auto-save → backend compute vd_intake_complete + auto-lock. Lỗi mạng
        // ở bước này KHÔNG làm mất hiển thị (giá trị đã nằm trong record).
        try { await this.props.record.save(); } catch (_) {}
    }

    async clearValue(ev) {
        if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (_) {} }
        try {
            await this.props.record.update({ [this.props.name]: false });
            await this.props.record.save();
        } catch (e) {
            console.error("[vd_m2o_dropdown] clear failed:", e);
        }
    }
}

export const vdM2oDropdownField = {
    component: VdM2oDropdown,
    displayName: "M2o dropdown (preload, giống ô Thời gian)",
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder || "" }),
};

registry.category("fields").add("vd_m2o_dropdown", vdM2oDropdownField);
