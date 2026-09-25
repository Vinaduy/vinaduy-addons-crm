/** @odoo-module **/
/**
 * vd_quote_table — BẢNG BÁO GIÁ GỐC (xanh) nhưng SỬA TRỰC TIẾP trong ô.
 *
 * User spec 2026-09-25: giữ NGUYÊN giao diện bảng báo giá cũ (header xanh
 * #5c8fb8, viền xanh #93c5fd, ô "Tổng Tiền" gộp bên phải) — KHÔNG dùng list thô
 * của Odoo. Chỉ cho SỬA trực tiếp Nội dung / Diện tích / Đơn giá; Thành tiền tự
 * tính = Số lượng × Đơn giá (Số lượng ẩn, giữ theo thông tin). KHÔNG thêm/xoá/kéo
 * dòng. Bấm "Lưu" (nút dưới bảng / nút Lưu của form) là ghi lại.
 *
 * Gắn: <field name="vd_quote_line_ids" widget="vd_quote_table" nolabel="1">
 *          <list create="0" delete="0"> ...fields... </list>
 *      </field>
 */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

function fmtVnd(x) {
    const n = Math.round(Number(x) || 0);
    try {
        return n.toLocaleString("vi-VN");
    } catch (_) {
        return String(n);
    }
}

export class VdQuoteTable extends Component {
    static template = "vd_crm_lead.VdQuoteTable";
    static props = { ...standardFieldProps };

    get list() {
        return this.props.record.data[this.props.name];
    }

    get lines() {
        // Model _order = 'sequence, id' → list.records giữ đúng thứ tự.
        return (this.list && this.list.records) || [];
    }

    lineAmount(line) {
        return (Number(line.data.qty) || 0) * (Number(line.data.unit_price) || 0);
    }

    get total() {
        return this.lines.reduce((s, l) => s + this.lineAmount(l), 0);
    }

    fmt(x) {
        return fmtVnd(x);
    }

    // Sửa Nội dung / Diện tích (char) — commit vào dòng khi rời ô (change).
    async onEditText(line, field, ev) {
        const val = ev.target.value;
        if (val === (line.data[field] || "")) {
            return;
        }
        await line.update({ [field]: val });
        this._save();
    }

    // Sửa Đơn giá (VNĐ, số nguyên) — bỏ mọi ký tự không phải số (kể cả dấu chấm
    // ngăn cách nghìn kiểu vi-VN "6.500.000").
    async onEditPrice(line, ev) {
        const digits = (ev.target.value || "").replace(/[^0-9]/g, "");
        const val = parseInt(digits, 10) || 0;
        if (val === (Number(line.data.unit_price) || 0)) {
            // vẫn re-format lại ô hiển thị cho gọn
            ev.target.value = this.fmt(val);
            return;
        }
        await line.update({ unit_price: val });
        ev.target.value = this.fmt(val);
        this._save();
    }

    // Lưu ngầm KHÔNG reload (đường lưu chung của form — xem vd_num_input.js).
    // Nút "Lưu" dưới bảng (action_save_quote_edit) cũng lưu form như thường.
    _save() {
        try {
            if (window.__vdScheduleIntakeSave) {
                window.__vdScheduleIntakeSave(this.props.record, "quote-table");
            }
        } catch (_) {
            /* im lặng — nút Lưu vẫn hoạt động */
        }
    }
}

export const vdQuoteTable = {
    component: VdQuoteTable,
    displayName: "Bảng báo giá (sửa trực tiếp, giao diện gốc)",
    supportedTypes: ["one2many"],
    relatedFields: () => [
        { name: "name", type: "char" },
        { name: "area_label", type: "char" },
        { name: "qty", type: "float" },
        { name: "unit_price", type: "float" },
        { name: "amount", type: "float" },
        { name: "sequence", type: "integer" },
        { name: "is_auto", type: "boolean" },
        { name: "line_key", type: "char" },
    ],
};

registry.category("fields").add("vd_quote_table", vdQuoteTable);
