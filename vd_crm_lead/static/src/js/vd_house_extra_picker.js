/** @odoo-module **/
/**
 * vd_house_extra_picker — nút "KHÁC" ở cuối dòng Mẫu nhà. Đưa chuột vào hiện
 * popup nhỏ với 3 tùy chọn BẬT/TẮT; bật xong hiện chip ở giữa dòng. Mỗi tùy
 * chọn CỘNG phụ phí vào ĐƠN GIÁ sàn (xử lý ở model _vd_san_unit_for):
 *   - Nhà 2 mặt tiền   (+300k)
 *   - Tân cổ điển nhẹ  (+300k)
 *   - Tân cổ điển nặng (+500k)
 * Lưu vào field Char `vd_house_extra` dạng CSV token: "2mt,tcd_nang".
 * (Tân cổ điển nhẹ / nặng loại trừ nhau.)
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const VD_HOUSE_EXTRA_OPTS = [
    { key: "2mt", label: "Nhà 2 mặt tiền", note: "+300k" },
    { key: "tcd_nhe", label: "Tân cổ điển nhẹ", note: "+300k" },
    { key: "tcd_nang", label: "Tân cổ điển nặng", note: "+500k" },
];

export class VdHouseExtraPicker extends Component {
    static template = "vd_crm_lead.VdHouseExtraPicker";
    static props = { ...standardFieldProps };

    setup() {
        this.opts = VD_HOUSE_EXTRA_OPTS;
        this.ui = useState({ open: false });
    }

    get tokens() {
        return String(this.props.record.data[this.props.name] || "")
            .split(",").map((s) => s.trim()).filter(Boolean);
    }
    isOn(key) {
        return this.tokens.includes(key);
    }
    activeOpts() {
        return this.opts.filter((o) => this.isOn(o.key));
    }

    async _save(tokens) {
        await this.props.record.update({ [this.props.name]: tokens.join(",") });
        // Flush ô số intake đang gõ TRƯỚC để reload-sau-save không nuốt số
        // in-flight (xem memory: intake_save_wipes_inflight_number).
        try {
            if (window.__vdFlushIntakeInputs) {
                await window.__vdFlushIntakeInputs("hextra");
            }
        } catch (_e) { /* ignore */ }
        try {
            await this.props.record.save();
        } catch (e) {
            console.error("[vd_hextra] save failed:", e);
        }
    }

    async toggle(key) {
        let t = this.tokens;
        if (t.includes(key)) {
            t = t.filter((x) => x !== key);
        } else {
            // Tân cổ điển nhẹ / nặng loại trừ nhau.
            if (key === "tcd_nhe") t = t.filter((x) => x !== "tcd_nang");
            if (key === "tcd_nang") t = t.filter((x) => x !== "tcd_nhe");
            t.push(key);
        }
        await this._save(t);
    }

    async removeChip(key) {
        await this._save(this.tokens.filter((x) => x !== key));
    }

    openPop() { this.ui.open = true; }
    closePop() { this.ui.open = false; }
}

export const vdHouseExtraPickerField = {
    component: VdHouseExtraPicker,
    displayName: "Mẫu nhà - tùy chọn thêm (KHÁC)",
    supportedTypes: ["char"],
};

registry.category("fields").add("vd_house_extra_picker", vdHouseExtraPickerField);
