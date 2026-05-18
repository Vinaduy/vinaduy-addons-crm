"""Tag library cho công năng từng tầng.

Mỗi tag = 1 phòng / công năng phổ biến trong nhà ở dân dụng VN.
NV chọn nhiều tag cho mỗi tầng qua widget many2many_tags (dropdown nhanh).
"""
from odoo import fields, models


class VdFloorFunctionTag(models.Model):
    _name = 'vd.floor.function.tag'
    _description = 'Công năng tầng (tag)'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char(string='Tên công năng', required=True, translate=False)
    sequence = fields.Integer(string='Thứ tự', default=10,
        help='Sắp xếp trong dropdown — số nhỏ hiện trên')
    color = fields.Integer(string='Màu badge', default=0)
    icon = fields.Char(string='Emoji icon',
        help='Vd: 🛏️ cho phòng ngủ, 🍳 cho bếp')
    # Filter dropdown theo tầng: 'all' = mọi tầng, hoặc comma-list
    # 'f1,f2,...,f7,tum'. Vd "Phòng khách" → "f1" (chỉ trệt).
    # "Sân phơi" → "tum,f1" (tum hoặc trệt sân vườn).
    fit_floors = fields.Char(
        string='Tầng phù hợp', default='all',
        help='"all" = chọn được mọi tầng. Hoặc list code phân cách dấu phẩy: '
             'f1, f2, f3, f4, f5, f6, f7, tum. Vd "Phòng khách" chỉ tầng trệt → "f1".')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Tên công năng đã tồn tại'),
    ]
