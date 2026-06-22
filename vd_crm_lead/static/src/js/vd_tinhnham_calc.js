/** @odoo-module **/
/**
 * vd_tinhnham_calc — BẢNG BÁO GIÁ trên form khách (khu "Vấn đề").
 *
 * Hiển thị BẢNG ĐƠN GIÁ XÂY DỰNG chính thức của VINADUY (file
 * "Bảng báo giá/Đơn giá.pdf"). Mỗi miền = 1 bảng duy nhất gồm Móng / Sàn /
 * Mái, trình bày y như file. Trên cùng có 3 filter BẮC - TRUNG - NAM; đưa
 * chuột vào miền nào thì hiện bảng của miền đó (chỉ Móng + ghi chú đổi theo
 * miền; Sàn/Mái dùng chung).
 *
 * Gắn: <field name="vd_intake_total_m2" widget="vd_tinhnham_calc"/>
 * Widget CHỈ đọc, KHÔNG ghi gì vào record. Toàn bộ NV xem được;
 * ẩn khi đã chốt báo giá (vd_quote_locked) — xử lý ở view.
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const REGIONS = [
    { key: "bac", label: "BẮC" },
    { key: "trung", label: "TRUNG" },
    { key: "nam", label: "NAM" },
];

// ===== MÓNG: đổi theo miền (Trên 70m² | Dưới 70m²) =====
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
        note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
    },
    nam: {
        rows: [
            { name: "Móng cốc", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
            { name: "Móng băng", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
            { name: "Móng cọc", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
        ],
        note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
    },
};
const MONG_LUU_Y = "Hệ số móng cốc cộng thêm 10%; móng băng, móng cọc cộng thêm 15%.";

// ===== SÀN: đơn giá (đ/m²) theo diện tích — dùng chung 3 miền =====
const SAN_COLS = ["≥ 75m²", "65-75m²", "50-65m²", "40-50m²", "< 40m²"];
const SAN_ROWS = [
    { name: "Ô tô vào được", vals: ["6.400.000", "6.600.000", "6.800.000", "7.000.000", "7.500.000"] },
    { name: "Ô tô không vào được", vals: ["6.700.000", "6.900.000", "7.000.000", "7.500.000", "8.000.000"] },
];
const SAN_THO = { over: "5.000.000 đ/m²", under: "5.200.000 đ/m²" };

// ===== MÁI: dùng chung 3 miền (split = 2 cột Không đổ trần | Có đổ trần) =====
const MAI = [
    { name: "Mái bằng", val: "DT × 20% × Đơn giá" },
    { name: "Mái Nhật", left: "Không đổ trần: DT × 42%", right: "Có đổ trần: DT × 48%" },
    { name: "Mái Thái", left: "Không đổ trần: DT × 45%", right: "Có đổ trần: DT × 55%" },
    { name: "Thông tầng", val: "DT × 40% × Đơn giá" },
    { name: "Mái trang trí", val: "DT × 40% → 60% × Đơn giá" },
    { name: "Mái trang trí đổ trần", val: "DT × 100% × Đơn giá" },
    { name: "Mái tôn", val: "1 mặt: DT × 13%   ·   2 mặt: DT × 16%   ·   3 mặt: DT × 20%" },
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
