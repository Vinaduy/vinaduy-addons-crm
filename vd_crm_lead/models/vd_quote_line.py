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
        string='Diện tích', help='Vd "120 M2 x 45%" hoặc "120 M2".')
    unit_price = fields.Float(string='Đơn giá (VNĐ)', digits=(16, 0))
    # Thành tiền: NV sửa được TRỰC TIẾP (không compute cứng) — để override thoải
    # mái. Default gợi ý = đơn giá (NV chỉnh lại theo diện tích/%).
    amount = fields.Float(string='Thành tiền (VNĐ)', digits=(16, 0))
