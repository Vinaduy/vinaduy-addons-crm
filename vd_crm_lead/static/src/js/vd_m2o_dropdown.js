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

// ===== GLOBAL CLICK HANDLER (1 lần cho cả app) — bypass OWL t-on-click/mousedown =====
// OWL handler trên các button render động trong popup KHÔNG fire ổn định (đã
// verify ở vd_m2o_hover_picker / vd_selection_hover_picker). Bắt click ở
// document (capture phase), đọc data-rec-id, tìm component qua __vdM2od.
if (!window.__vdM2odClickHandlerInstalled) {
    window.__vdM2odClickHandlerInstalled = true;
    document.addEventListener("click", (ev) => {
        const target = ev.target;
        if (!(target instanceof Element)) return;
        // Chip chọn (nút × clear vẫn dùng t-on-click ở bar — không động vào đây)
        const chip = target.closest(".o_vd_m2od_chip");
        if (!chip) return;
        const el = chip.closest(".o_vd_m2od");
        const comp = el && el.__vdM2od;
        if (!comp) return;
        const id = parseInt(chip.dataset.recId, 10);
        if (!id) return;
        const rec = (comp.state.options || []).find((o) => o.id === id);
        if (!rec) return;
        ev.preventDefault();
        ev.stopPropagation();
        comp.selectRecord(rec, ev);
    }, true);
}

const FALLBACK_REL = {
    vd_intake_province_id: "res.country.state",
    vd_intake_district: "vd.district",
};

// ===== CACHE TÊN m2o (id -> display_name), DÙNG CHUNG mọi widget =====
// Fix "chọn Phường mất Tỉnh": sau khi chọn Phường, giá trị Tỉnh trong record đôi
// khi mất display_name (chỉ còn id) → widget không có tên để hiện → ô trống.
// Cache này giữ tên đã biết (từ options đã tải + từ state_id của Phường) để ô
// Tỉnh luôn tra được tên mà hiển thị, bất kể record.data thiếu tên.
const VD_M2OD_LABELS = window.__vdM2odLabels || (window.__vdM2odLabels = {});
function vdRememberLabel(id, label) {
    const nid = Array.isArray(id) ? id[0] : id;
    if (nid != null && nid !== false && label) VD_M2OD_LABELS[nid] = label;
}

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
        onMounted(() => {
            // Expose instance qua DOM → global click handler gọi selectRecord được.
            if (this.rootRef.el) this.rootRef.el.__vdM2od = this;
            document.addEventListener("click", this._onDocClick, true);
        });
        onWillUnmount(() => {
            if (this.rootRef.el) delete this.rootRef.el.__vdM2od;
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
            // Ghi nhớ tên vào cache toàn cục: option này + (nếu là Phường) TÊN TỈNH
            // qua state_id → ô Tỉnh luôn tra được tên dù record.data mất display_name.
            for (const o of recs) {
                vdRememberLabel(o.id, o.display_name || o.name);
                if (this.isDistrict && o.state_id) {
                    vdRememberLabel(o.state_id, Array.isArray(o.state_id) ? o.state_id[1] : "");
                }
            }
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

    // Tách {id, label} từ MỌI định dạng m2o có thể gặp trong record.data:
    // object {id, display_name}, array [id, name], hoặc id trần (number).
    _valueParts(v) {
        if (!v && v !== 0) return { id: null, label: "" };
        if (Array.isArray(v)) return { id: v[0] ?? null, label: v[1] || "" };
        if (typeof v === "object") {
            return { id: v.id ?? v.resId ?? null,
                     label: v.display_name || v.displayName || v.name || "" };
        }
        if (typeof v === "number") return { id: v, label: "" };
        return { id: null, label: "" };
    }

    get currentDisplay() {
        const { id, label } = this._valueParts(this.props.record.data[this.props.name]);
        if (label) { vdRememberLabel(id, label); return label; }
        if (id != null && id !== false) {
            // Thiếu tên trong record → tra options đã tải, rồi cache tên toàn cục.
            const opt = (this.state.options || []).find((o) => o.id === id);
            if (opt) return opt.display_name || opt.name || "";
            if (VD_M2OD_LABELS[id]) return VD_M2OD_LABELS[id];
        }
        return "";
    }

    get hasValue() {
        const { id } = this._valueParts(this.props.record.data[this.props.name]);
        return id != null && id !== false;
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
        // CHẶN bấm CHỒNG: đang xử lý 1 lựa chọn (await onchange server) mà bấm tiếp
        // → xếp chồng RPC = ĐƠ. Bỏ qua click mới cho tới khi xong.
        if (this._selecting) return;
        this._selecting = true;
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        const fname = this.props.name;
        const disp = rec.display_name || rec.name || "";
        // CHỈ set field đang chọn. KHÔNG tự nhét Tỉnh (field anh em) vào record.update:
        // trước đây nhét {id,display_name} cho Tỉnh → onchange server thấy Tỉnh "đã
        // đúng" nên không trả lại → record giữ object tự-nhét SAI định dạng → ô Tỉnh
        // render TRỐNG TRẮNG ("chọn Phường mất Tỉnh"). Nay để onchange server
        // (_onchange_intake_district_sync_province) tự set Tỉnh đúng định dạng native.
        // Bug fix 2026-08-09.
        const rawStateId = (this.isDistrict && rec.state_id)
            ? (Array.isArray(rec.state_id) ? rec.state_id[0] : this._extractId(rec.state_id))
            : false;
        // Nhớ tên vào cache: field vừa chọn + (nếu Phường) tên Tỉnh qua state_id.
        vdRememberLabel(rec.id, disp);
        if (this.isDistrict && rec.state_id) {
            vdRememberLabel(rec.state_id, Array.isArray(rec.state_id) ? rec.state_id[1] : "");
        }
        const vals = { [fname]: { id: rec.id, display_name: disp } };
        // ĐÓNG NGAY (trước await) → bấm là thấy dropdown đóng tức thì, hết cảm giác
        // "bấm không ăn". Giá trị vẫn set ở record.update phía dưới.
        this._close();
        try {
            let updated = false;
            try {
                await this.props.record.update(vals);
                updated = true;
            } catch (e) {
                console.warn("[vd_m2o_dropdown] record.update failed:", e);
            }
            // VERIFY giá trị đã vào record; chưa vào → ORM write thẳng (đảm bảo LƯU
            // đúng — fix 'bấm chọn tỉnh không lưu').
            // TUYỆT ĐỐI KHÔNG record.load() ở đây: load() VỨT SẠCH mọi thay đổi chưa
            // lưu của CẢ BẢNG (chip, ô số vừa gõ) — đây chính là 1 trong các đường
            // làm "chọn Tỉnh/Phường xong là mất hết trường đã điền trước đó".
            const curId = this._extractId(this.props.record.data[fname]);
            if (!updated || curId !== rec.id) {
                try {
                    const resId = this.props.record.resId;
                    if (resId) {
                        const wvals = { [fname]: rec.id };
                        // Chỉ ở fallback (record.update lỗi) mới ghi thẳng Tỉnh theo id.
                        if (rawStateId) {
                            wvals["vd_intake_province_id"] = rawStateId;
                        }
                        await this.orm.write(this.props.record.resModel, [resId], wvals);
                        updated = true;
                    } else {
                        console.warn("[vd_m2o_dropdown] no resId — can't ORM write");
                    }
                } catch (e) {
                    console.error("[vd_m2o_dropdown] ORM write fallback failed:", e);
                }
            }
            // Lưu-ngầm CÓ BẢO VỆ (KHÔNG reload khi đang nhập). Strategy ORM-write ở trên
            // đã đảm bảo lưu DB khi cần; ở đây chỉ lên lịch lưu form lúc user nghỉ tay.
            try { if (window.__vdCommitIntakeChange) window.__vdCommitIntakeChange(this.props.record, "m2o-dropdown"); } catch (_) {}
        } finally {
            this._selecting = false;
            try { this.render(true); } catch (_) {}
        }
    }

    async clearValue(ev) {
        if (ev) { try { ev.preventDefault(); ev.stopPropagation(); } catch (_) {} }
        try {
            await this.props.record.update({ [this.props.name]: false });
            try { if (window.__vdCommitIntakeChange) window.__vdCommitIntakeChange(this.props.record, "m2o-dropdown-clear"); } catch (_) {}
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
