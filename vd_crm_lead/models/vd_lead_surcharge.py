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
