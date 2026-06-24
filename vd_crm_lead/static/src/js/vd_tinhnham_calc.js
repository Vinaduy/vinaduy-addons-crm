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
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// Bảng giá mặc định (fallback) khi chưa tải được từ server. Khi có dữ liệu từ
// vd.pricing.region thì state.data được thay -> ĐỒNG BỘ với cấu hình đơn giá.
const FALLBACK = {
    regions: [
        {
            key: "bac", label: "BẮC",
            rows: [
                { name: "Móng đơn", over: "DT × 30% × Đơn giá", under: "DT × 35% × Đơn giá" },
                { name: "Móng băng", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
                { name: "Móng cọc", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
            ],
            note: "Toàn tỉnh: Lai Châu, Sơn La, Điện Biên, Cao Bằng, Bắc Kạn tăng 300k/m². Các huyện của tỉnh Hà Giang, Lạng Sơn tăng 300k.",
        },
        {
            key: "trung", label: "TRUNG",
            rows: [
                { name: "Móng đơn", over: "DT × 35% × Đơn giá", under: "DT × 40% × Đơn giá" },
                { name: "Móng băng", over: "DT × 45% × Đơn giá", under: "DT × 50% × Đơn giá" },
                { name: "Móng cọc", over: "DT × 45% × Đơn giá", under: "DT × 50% × Đơn giá" },
            ],
            note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
        },
        {
            key: "nam", label: "NAM",
            rows: [
                { name: "Móng cốc", over: "DT × 40% × Đơn giá", under: "DT × 45% × Đơn giá" },
                { name: "Móng băng", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
                { name: "Móng cọc", over: "DT × 50% × Đơn giá", under: "DT × 55% × Đơn giá" },
            ],
            note: "Diện tích sàn tầng 1 tính theo diện tích mái đua tầng 1, gồm cả bậc tam cấp. Nhà tân cổ điển nhẹ tăng 400k, tân cổ điển nặng tăng 800k. Gửi cấp trên duyệt.",
        },
    ],
    san_cols: ["≥ 75m²", "65-75m²", "50-65m²", "40-50m²", "< 40m²"],
    san_rows: [
        { name: "Ô tô vào được", vals: ["6.400.000", "6.600.000", "6.800.000", "7.000.000", "7.500.000"] },
        { name: "Ô tô không vào được", vals: ["6.700.000", "6.900.000", "7.000.000", "7.500.000", "8.000.000"] },
    ],
    san_tho: { over: "5.000.000 đ/m²", under: "5.200.000 đ/m²" },
    mai: [
        { name: "Mái bằng", val: "DT × 20% × Đơn giá" },
        { name: "Mái Nhật", left: "Không đổ trần: DT × 42%", right: "Có đổ trần: DT × 48%" },
        { name: "Mái Thái", left: "Không đổ trần: DT × 45%", right: "Có đổ trần: DT × 55%" },
        { name: "Thông tầng", val: "DT × 40% × Đơn giá" },
        { name: "Mái trang trí", val: "DT × 40% → 60% × Đơn giá" },
        { name: "Mái trang trí đổ trần", val: "DT × 100% × Đơn giá" },
        { name: "Mái tôn", val: "1 mặt: DT × 13%   ·   2 mặt: DT × 16%   ·   3 mặt: DT × 20%" },
    ],
    luu_y: "Hệ số móng đơn cộng thêm 10%; móng băng, móng cọc cộng thêm 15%.",
};

export class VdTinhnhamCalc extends Component {
    static template = "vd_crm_lead.VdTinhnhamCalc";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        const d = this.props.record.data || {};
        this.state = useState({ region: "bac", data: FALLBACK });
        if (d.vd_intake_region && FALLBACK.regions.some((r) => r.key === d.vd_intake_region)) {
            this.state.region = d.vd_intake_region;
        }
        // Tải đơn giá từ cấu hình (vd.pricing.region) -> đồng bộ với khóa học + báo giá.
        onWillStart(async () => {
            try {
                const t = await this.orm.call("vd.pricing.region", "vd_get_price_table", []);
                if (t && t.regions && t.regions.length) {
                    this.state.data = t;
                }
            } catch (e) {
                // giữ FALLBACK
            }
        });
    }

    get regions() { return this.state.data.regions; }
    get sanCols() { return this.state.data.san_cols; }
    get sanRows() { return this.state.data.san_rows; }
    get sanTho() { return this.state.data.san_tho; }
    get mai() { return this.state.data.mai; }
    get luuY() { return this.state.data.luu_y; }

    get mong() {
        const rs = this.state.data.regions || [];
        return rs.find((r) => r.key === this.state.region) || rs[0] || { rows: [], note: "" };
    }

    setRegion(k) {
        if ((this.state.data.regions || []).some((r) => r.key === k)) {
            this.state.region = k;
        }
    }
}

export const vdTinhnhamCalc = {
    component: VdTinhnhamCalc,
    displayName: "Bảng báo giá",
    supportedTypes: ["integer", "float"],
};

registry.category("fields").add("vd_tinhnham_calc", vdTinhnhamCalc);
