/** @odoo-module **/
/**
 * vd_house_extra_picker — nút "KHÁC" ở cuối dòng Mẫu nhà. Đưa chuột vào hiện
 * popup nhỏ với các tùy chọn; bật xong hiện chip ở giữa dòng.
 *
 * Trong popup có 2 loại mục:
 *   - Kiểu nhà phụ (field='house'): "Nhà mái tôn" -> set vd_intake_house_type
 *     (đơn chọn; đưa vào đây cho gọn hàng chính). Bấm lại = bỏ chọn.
 *   - Phụ phí (field='extra'): cộng thêm vào ĐƠN GIÁ sàn (model _vd_san_unit_for),
 *     lưu CSV token ở field `vd_house_extra` ("2mt,tcd_nang"):
 *       Nhà 2 mặt tiền +300k · Tân cổ điển nhẹ +300k · Tân cổ điển nặng +500k
 *     (Tân cổ điển nhẹ / nặng loại trừ nhau.)
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const HOUSE_TYPE_FIELD = "vd_intake_house_type";

const VD_HOUSE_EXTRA_OPTS = [
    { key: "mai_ton", label: "Nhà mái tôn", note: "", field: "house" },
    { key: "2mt", label: "Nhà 2 mặt tiền", note: "+300k", field: "extra" },
    { key: "tcd_nhe", label: "Tân cổ điển nhẹ", note: "+300k", field: "extra" },
    { key: "tcd_nang", label: "Tân cổ điển nặng", note: "+500k", field: "extra" },
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
    isOn(o) {
        if (o.field === "house") {
            return this.props.record.data[HOUSE_TYPE_FIELD] === o.key;
        }
        return this.tokens.includes(o.key);
    }
    activeOpts() {
        return this.opts.filter((o) => this.isOn(o));
    }

    async _afterSave() {
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

    async _saveTokens(tokens) {
        await this.props.record.update({ [this.props.name]: tokens.join(",") });
        await this._afterSave();
    }

    async toggle(o) {
        if (o.field === "house") {
            const cur = this.props.record.data[HOUSE_TYPE_FIELD];
            await this.props.record.update({
                [HOUSE_TYPE_FIELD]: cur === o.key ? false : o.key,
            });
            await this._afterSave();
            return;
        }
        let t = this.tokens;
        if (t.includes(o.key)) {
            t = t.filter((x) => x !== o.key);
        } else {
            // Tân cổ điển nhẹ / nặng loại trừ nhau.
            if (o.key === "tcd_nhe") t = t.filter((x) => x !== "tcd_nang");
            if (o.key === "tcd_nang") t = t.filter((x) => x !== "tcd_nhe");
            t.push(o.key);
        }
        await this._saveTokens(t);
    }

    async removeChip(o) {
        if (o.field === "house") {
            await this.props.record.update({ [HOUSE_TYPE_FIELD]: false });
            await this._afterSave();
            return;
        }
        await this._saveTokens(this.tokens.filter((x) => x !== o.key));
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
