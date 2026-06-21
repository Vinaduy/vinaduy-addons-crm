/** @odoo-module **/
/**
 * vd_tinhnham_calc — Bảng BÁO GIÁ TÍNH NHẨM trên form khách (khu "Vấn đề").
 *
 * Hiện khi khách CÒN MỚI (chưa khai thác đủ / chưa chốt báo giá) để NV tính
 * nhanh trong lúc tư vấn. Công thức (file "Tính nhẩm.pptx"):
 *      Tổng tiền ≈ Hệ số × Diện tích sàn tầng 1 × Đơn giá/m²
 * Hệ số lấy từ model vd.tinhnham.region (sửa trong CRM > Cấu hình > Hệ số tính nhẩm).
 *
 * Gắn: <field name="vd_intake_total_m2" widget="vd_tinhnham_calc"/>
 * Widget CHỈ đọc các field khác để prefill, KHÔNG ghi gì vào record.
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const COMBOS = [
    { key: "mb1", label: "1T Mái bằng" },
    { key: "mb2", label: "2T Mái bằng" },
    { key: "mn1", label: "1T Mái Nhật" },
    { key: "mn2", label: "2T Mái Nhật" },
    { key: "mt1", label: "1T Mái Thái" },
];
const FOUNDS = [
    { key: "don", label: "Móng cốc" },
    { key: "bang", label: "Móng băng" },
    { key: "coc", label: "Móng cọc" },
];
const REGIONS = [
    { key: "bac", label: "Bắc" },
    { key: "trung", label: "Trung" },
    { key: "nam", label: "Nam" },
];

export class VdTinhnhamCalc extends Component {
    static template = "vd_crm_lead.VdTinhnhamCalc";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.COMBOS = COMBOS;
        this.FOUNDS = FOUNDS;
        this.REGIONS = REGIONS;
        const d = this.props.record.data || {};
        // Diện tích sàn tầng 1 (móng): ưu tiên ngang×dài, rồi tầng 1, rồi tổng.
        let area = 0;
        const w = d.vd_intake_house_width_m || 0;
        const l = d.vd_intake_house_length_m || 0;
        if (w > 0 && l > 0) area = Math.round(w * l);
        else area = d.vd_intake_floor_1_m2 || d.vd_intake_total_m2 || 0;
        this.state = useState({
            table: {},
            loaded: false,
            region: d.vd_intake_region || "bac",
            combo: "mb1",
            found: "don",
            area: area,
            donGia: "",          // triệu/m²
            small: area > 0 && area < 70,
        });
        onWillStart(async () => {
            try {
                const t = await this.orm.call("vd.tinhnham.region", "vd_get_table", []);
                this.state.table = t || {};
            } catch (_e) {
                this.state.table = {};
            }
            if (!this.state.table[this.state.region]) {
                const first = Object.keys(this.state.table)[0];
                if (first) this.state.region = first;
            }
            this.state.loaded = true;
        });
    }

    get regionData() {
        return this.state.table[this.state.region] || null;
    }
    get baseCoef() {
        const rd = this.regionData;
        if (!rd) return 0;
        return rd.coefs[this.state.found + "_" + this.state.combo] || 0;
    }
    // DT < 70m² thì cộng thêm % vào hệ số (theo lưu ý của bảng).
    get coef() {
        let c = this.baseCoef;
        if (this.state.small) {
            const pct = (this.regionData && this.regionData.notes.small_pct) || 0;
            c = c * (1 + pct / 100);
        }
        return c;
    }
    get area() {
        return parseFloat(this.state.area) || 0;
    }
    get donGia() {
        return parseFloat((this.state.donGia + "").replace(/,/g, ".")) || 0;
    }
    get chargeable() {
        return this.coef * this.area;   // m² tính tiền
    }
    get totalTrieu() {
        return this.chargeable * this.donGia;   // triệu đồng
    }
    get notes() {
        return (this.regionData && this.regionData.notes) || null;
    }

    setRegion(k) { this.state.region = k; }
    setCombo(k) { this.state.combo = k; }
    setFound(k) { this.state.found = k; }
    toggleSmall() { this.state.small = !this.state.small; }
    onArea(ev) { this.state.area = ev.target.value; }
    onDonGia(ev) { this.state.donGia = ev.target.value; }

    // Format số: 1 chữ số thập phân, ngăn cách nghìn.
    fmt(n, dec = 0) {
        const v = Number(n) || 0;
        return v.toLocaleString("vi-VN", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    }
    get totalTrieuLabel() { return this.fmt(this.totalTrieu, 0); }
    get totalTyLabel() { return this.fmt(this.totalTrieu / 1000, 2); }
    get coefLabel() { return this.fmt(this.coef, 2); }
    get chargeableLabel() { return this.fmt(this.chargeable, 0); }
}

export const vdTinhnhamCalc = {
    component: VdTinhnhamCalc,
    displayName: "Bảng tính nhẩm báo giá",
    supportedTypes: ["integer", "float"],
};

registry.category("fields").add("vd_tinhnham_calc", vdTinhnhamCalc);
