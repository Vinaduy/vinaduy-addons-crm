/** @odoo-module **/
/**
 * vd_tinhnham_calc — BẢNG BÁO GIÁ trên form khách (khu "Vấn đề").
 *
 * Hiển thị BẢNG ĐƠN GIÁ XÂY DỰNG chính thức của VINADUY (file
 * "Bảng báo giá/Đơn giá.pdf"): Móng × Sàn × Mái × Phát sinh.
 * Trên cùng có 3 filter BẮC - TRUNG - NAM; đưa chuột vào miền nào thì
 * hiện bảng báo giá của miền đó (Móng đổi theo miền; Sàn/Mái/Phát sinh
 * dùng chung).
 *
 * Gắn: <field name="vd_intake_total_m2" widget="vd_tinhnham_calc"/>
 * Widget CHỈ đọc, KHÔNG ghi gì vào record.
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const REGIONS = [
    { key: "bac", label: "BẮC" },
    { key: "trung", label: "TRUNG" },
    { key: "nam", label: "NAM" },
];

// ===== MÓNG: đổi theo miền (Trên 70m² / Dưới 70m²) =====
const MONG = {
    bac: {
        rows: [
            { name: "Móng đơn", over: "DT × 30% × Đơn giá", under: "DT × 35% × Đơn giá" },
            { name: "Móng băng", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
            { name: "Móng cọc", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
        ],
        note: "Toàn tỉnh: Lai Châu, Sơn La, Điện Biên, Cao Bằng, Bắc Kạn tăng 300k/m². Các huyện của tỉnh Hà Giang, Lạng Sơn tăng 300k.",
    },
    trung: {
        rows: [
            { name: "Móng đơn", over: "DT × 35% × Đơn giá", under: "DT × 40% × Đơn giá" },
            { name: "Móng băng", over: "DT × 45% × Đơn giá", under: "DT × 50% × Đơn giá" },
            { name: "Móng cọc", over: "DT × 45% × Đơn giá", under: "DT × 50% × Đơn giá" },
        ],
        note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, bao gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
    },
    nam: {
        rows: [
            { name: "Móng cốc", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
            { name: "Móng băng", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
            { name: "Móng cọc", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
        ],
        note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, bao gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
    },
};
const MONG_LUU_Y = "Hệ số móng cốc cộng thêm 10%; móng băng, móng cọc cộng thêm 15%.";

// ===== SÀN: đơn giá (đ/m²) theo diện tích — dùng chung 3 miền =====
const SAN_COLS = ["≥ 75m²", "65 - 75m²", "50 - 65m²", "40 - 50m²", "< 40m²"];
const SAN_ROWS = [
    { name: "Ô tô vào được", vals: ["6.400.000", "6.600.000", "6.800.000", "7.000.000", "7.500.000"] },
    { name: "Ô tô không vào được", vals: ["6.700.000", "6.900.000", "7.000.000", "7.500.000", "8.000.000"] },
];
const SAN_THO = [
    { name: "Trên 70m²", val: "5.000.000 đ/m²" },
    { name: "Dưới 70m²", val: "5.200.000 đ/m²" },
];

// ===== MÁI: dùng chung 3 miền =====
const MAI = [
    { name: "Mái bằng", val: "DT × 20% × Đơn giá" },
    { name: "Mái Nhật", val: "Không đổ trần: DT × 42% · Có đổ trần: DT × 48%" },
    { name: "Mái Thái", val: "Không đổ trần: DT × 45% · Có đổ trần: DT × 55%" },
    { name: "Thông tầng", val: "DT × 40% × Đơn giá" },
    { name: "Mái trang trí", val: "DT × 40% → 60% × Đơn giá" },
    { name: "Mái trang trí đổ trần", val: "DT × 100% × Đơn giá" },
    { name: "Mái tôn 1 mặt", val: "DT × 13% × Đơn giá" },
    { name: "Mái tôn 2 mặt", val: "DT × 16% × Đơn giá" },
    { name: "Mái tôn 3 mặt", val: "DT × 20% × Đơn giá" },
];

// ===== PHÁT SINH (nhà 100m²) — dùng chung 3 miền =====
const PHAT_SINH = [
    { name: "Đường lớn - có chỗ tập kết", val: "0 đ/m²" },
    { name: "Đường lớn - không chỗ tập kết", val: "200.000 đ/m²" },
    { name: "Ngõ nhỏ - có chỗ tập kết", val: "250.000 đ/m²" },
    { name: "Ngõ nhỏ - không chỗ tập kết", val: "350.000 đ/m²" },
    { name: "Có chỗ để đất", val: "0 đ/m²" },
    { name: "Không có chỗ để đất + đổ thải + mua đất", val: "300.000 đ/m²" },
    { name: "Đất yếu - đào sâu - gia cố", val: "250.000 đ/m²" },
];

export class VdTinhnhamCalc extends Component {
    static template = "vd_crm_lead.VdTinhnhamCalc";
    static props = { ...standardFieldProps };

    setup() {
        this.REGIONS = REGIONS;
        this.SAN_COLS = SAN_COLS;
        this.SAN_ROWS = SAN_ROWS;
        this.SAN_THO = SAN_THO;
        this.MAI = MAI;
        this.PHAT_SINH = PHAT_SINH;
        this.MONG_LUU_Y = MONG_LUU_Y;
        const d = this.props.record.data || {};
        this.state = useState({
            region: MONG[d.vd_intake_region] ? d.vd_intake_region : "bac",
        });
    }

    get mong() {
        return MONG[this.state.region] || MONG.bac;
    }

    setRegion(k) {
        if (MONG[k]) this.state.region = k;
    }
}

export const vdTinhnhamCalc = {
    component: VdTinhnhamCalc,
    displayName: "Bảng báo giá",
    supportedTypes: ["integer", "float"],
};

registry.category("fields").add("vd_tinhnham_calc", vdTinhnhamCalc);
