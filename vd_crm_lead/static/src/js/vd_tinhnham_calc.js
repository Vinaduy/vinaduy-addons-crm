/** @odoo-module **/
/**
 * vd_tinhnham_calc — BẢNG BÁO GIÁ trên form khách (khu "Vấn đề").
 *
 * Hiển thị bảng báo giá (hệ số theo vùng) lấy từ Cấu hình. Trên cùng có 3
 * filter BẮC - TRUNG - NAM; đưa chuột vào miền nào thì hiện bảng báo giá của
 * miền đó (ma trận: Loại móng × Kiểu nhà).
 * Hệ số lấy từ model vd.tinhnham.region (CRM > Cấu hình > Hệ số tính nhẩm).
 *
 * Gắn: <field name="vd_intake_total_m2" widget="vd_tinhnham_calc"/>
 * Widget CHỈ đọc cấu hình, KHÔNG ghi gì vào record.
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
    { key: "bac", label: "BẮC" },
    { key: "trung", label: "TRUNG" },
    { key: "nam", label: "NAM" },
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
        this.state = useState({
            table: {},
            loaded: false,
            region: d.vd_intake_region || "bac",
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
    get notes() {
        return (this.regionData && this.regionData.notes) || null;
    }

    setRegion(k) {
        if (this.state.table[k]) this.state.region = k;
    }

    // Hệ số 1 ô (loại móng × combo nhà), format 2 chữ số thập phân.
    coefLabel(found, combo) {
        const rd = this.regionData;
        if (!rd) return "-";
        const v = rd.coefs[found + "_" + combo] || 0;
        if (!v) return "-";
        return Number(v).toLocaleString("vi-VN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

export const vdTinhnhamCalc = {
    component: VdTinhnhamCalc,
    displayName: "Bảng báo giá",
    supportedTypes: ["integer", "float"],
};

registry.category("fields").add("vd_tinhnham_calc", vdTinhnhamCalc);
