# -*- coding: utf-8 -*-
"""Vấn đề KH trong đàm phán — NV chọn các vấn đề KH đang gặp để có
giải pháp đàm phán phù hợp.

Một số vấn đề có rule auto-detect dựa trên intake data (vd_intake_dimensions
'chua_co_so' → tự suggest 'Chưa làm được sổ'). NV vẫn có thể tick thêm
manual những vấn đề không suy ra được từ data.
"""
from odoo import models, fields, api


class VdNegoProblem(models.Model):
    _name = 'vd.nego.problem'
    _description = 'Vấn đề KH trong đàm phán'
    _order = 'sequence, id'
    _rec_names_search = ['name', 'code']

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Tên vấn đề', required=True, translate=True)
    code = fields.Char(string='Mã', required=True, copy=False,
                       help='Mã code dùng cho auto-detect rule. Vd: no_red_book, low_budget.')
    color = fields.Integer(string='Màu badge', default=0,
                           help='Màu tag hiển thị (0-11, theo bảng màu Odoo).')
    icon = fields.Char(string='Icon', default='❓',
                       help='Emoji hiển thị trước tên vấn đề.')
    tip_html = fields.Html(
        string='Gợi ý xử lý',
        sanitize=False,
        help='Tips cho NV về cách xử lý đàm phán khi gặp vấn đề này.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Mã vấn đề phải duy nhất.'),
    ]

    @api.depends('name', 'icon')
    def _compute_display_name(self):
        """Dropdown hiển thị '💰 Tham khảo giá' thay vì chỉ 'Tham khảo giá'."""
        for rec in self:
            icon = rec.icon or '❓'
            rec.display_name = f"{icon} {rec.name}" if rec.name else icon
