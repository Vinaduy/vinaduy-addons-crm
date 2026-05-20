"""Vùng miền seed cho phân loại template báo giá.

3 record cố định: Miền Bắc / Miền Trung / Miền Nam. Dùng làm Many2many
trên vd.quote.template.category để 1 nhóm template có thể áp dụng cho
nhiều vùng (vd Bắc + Trung dùng chung templates).
"""
from odoo import fields, models


class VdQuoteRegion(models.Model):
    _name = 'vd.quote.region'
    _description = 'Vùng miền (cho template báo giá)'
    _order = 'sequence, id'

    code = fields.Char(string='Code', required=True, index=True)
    name = fields.Char(string='Tên', required=True, translate=False)
    sequence = fields.Integer(default=10)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Code vùng đã tồn tại.'),
    ]
