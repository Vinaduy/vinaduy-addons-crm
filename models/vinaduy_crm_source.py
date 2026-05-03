from odoo import fields, models


class VinaduyCrmSource(models.Model):
    _name = 'vinaduy.crm.source'
    _description = 'Nguồn lead VINADUY'
    _order = 'sequence, id'

    name = fields.Char(string='Tên nguồn', required=True, translate=True)
    code = fields.Char(string='Mã', help='Mã ngắn dùng cho tích hợp (vd: omicall, zalo)')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Mã nguồn phải duy nhất'),
    ]
