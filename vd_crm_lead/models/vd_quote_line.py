# -*- coding: utf-8 -*-
"""Dòng báo giá chi tiết EDITABLE (user spec 2026-09-24).

Cho phép NV sửa TRỰC TIẾP từng dòng báo giá (Nội dung / Diện tích / Đơn giá /
Thành tiền) — kể cả các dòng chính (Móng, Tầng, Mái). Khi có dòng thì báo giá
(bảng + PDF) DÙNG các dòng này thay cho công thức tự động. Bấm "Tạo lại từ
thông tin" để dựng lại từ intake (bỏ sửa tay).
"""
from odoo import models, fields, api


class VdQuoteLine(models.Model):
    _name = 'vd.quote.line'
    _description = 'Dòng báo giá chi tiết (sửa tay được)'
    _order = 'sequence, id'

    lead_id = fields.Many2one(
        'crm.lead', string='Lead', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nội dung', required=True)
    area_label = fields.Char(
        string='Diện tích', help='Chữ hiển thị, vd "120 M2 x 45%" hoặc "120 M2".')
    # SỐ LƯỢNG/diện tích quy đổi — cơ sở để TỰ TÍNH Thành tiền (user spec 2026-09-24).
    qty = fields.Float(string='Số lượng', default=1.0, digits=(12, 2))
    unit_price = fields.Float(string='Đơn giá (VNĐ)', digits=(16, 0))
    # Thành tiền TỰ ĐỘNG = SL × Đơn giá (sửa SL/Đơn giá là tính lại ngay).
    amount = fields.Float(
        string='Thành tiền (VNĐ)', digits=(16, 0),
        compute='_compute_amount', store=True, readonly=True)
    # is_auto=True: dòng TỰ SINH từ thông tin (Móng/Tầng/Mái) → đổi thông tin là
    # tự nhảy theo. NV sửa dòng nào → dòng đó thành is_auto=False (giữ số tay,
    # không bị ghi đè khi đổi diện tích). (user spec 2026-09-24)
    is_auto = fields.Boolean(default=True, copy=False)
    # Khoá slot (found/floor_1/roof...) — để khi đồng bộ, dòng auto trùng slot với
    # dòng NV đã sửa tay thì BỎ QUA (tránh trùng dòng). copy=False.
    line_key = fields.Char(copy=False)

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for l in self:
            l.amount = (l.qty or 0.0) * (l.unit_price or 0.0)

    @api.onchange('name', 'area_label', 'qty', 'unit_price')
    def _onchange_mark_manual(self):
        """NV sửa tay dòng nào → dòng đó KHÔNG bị ghi đè khi đổi thông tin nữa."""
        for l in self:
            l.is_auto = False
