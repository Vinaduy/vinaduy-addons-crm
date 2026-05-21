# -*- coding: utf-8 -*-
"""Phát sinh (extra items) per lead — append vào báo giá chi tiết.
Vd: Thêm WC × 2 × 15M = 30M.
"""
from odoo import models, fields, api


class VdLeadSurcharge(models.Model):
    _name = 'vd.lead.surcharge'
    _description = 'Phát sinh trong báo giá'
    _order = 'sequence, id'

    lead_id = fields.Many2one(
        'crm.lead', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nội dung', required=True,
                       help='Vd: "Thêm WC", "Thêm cầu thang", "Đào móng sâu hơn"...')
    quantity = fields.Float(string='Số lượng', default=1.0, digits=(10, 2))
    quantity_label = fields.Char(
        string='Mô tả số lượng',
        help='Vd: "Số lượng 02", "1 cái", "2 phòng" — hiển thị trong báo giá.',
    )
    unit_price = fields.Float(string='Đơn giá (VNĐ)', digits=(16, 0))
    total = fields.Float(
        string='Thành tiền', compute='_compute_total', store=True, digits=(16, 0),
    )

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.quantity or 0) * (rec.unit_price or 0)


class VdLeadSurchargePreset(models.Model):
    """Preset phát sinh: admin tạo 1 lần (Thêm WC, Cầu thang, ...), NV pick
    trong wizard và nhập quantity → tự tạo vd.lead.surcharge trên lead."""
    _name = 'vd.lead.surcharge.preset'
    _description = 'Preset phát sinh báo giá'
    _order = 'sequence, id'

    name = fields.Char(string='Tên phát sinh', required=True,
                       help='Vd: "Thêm WC", "Cầu thang phụ", "Đào móng sâu"...')
    unit_price = fields.Float(string='Đơn giá (VNĐ)', digits=(16, 0))
    unit_label = fields.Char(string='Đơn vị tính',
                             help='Vd: "cái", "phòng", "m²" — hiển thị trong báo giá.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
