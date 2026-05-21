# -*- coding: utf-8 -*-
"""Custom field framework cho phiếu khai thác KH.

Admin định nghĩa trường tuỳ chọn (label + help text). NV nhập giá trị
trên từng lead. Lưu trữ qua model bridge vd.lead.custom.value (One2many
trên crm.lead) để hiển thị dynamic list trong form.
"""
from odoo import models, fields, api


class VdIntakeCustomField(models.Model):
    _name = 'vd.intake.custom.field'
    _description = 'Trường khai thác tuỳ chọn (admin tự thêm)'
    _order = 'sequence, id'

    name = fields.Char(string='Tên trường', required=True,
                       help='Vd: "Mong muốn KH", "WC", "Cầu thang phụ"...')
    help_text = fields.Char(string='Gợi ý', help='Placeholder/help hiện cho NV.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    # Nếu trường này có đơn giá > 0 → khi NV nhập số (qty) vào cột tương ứng,
    # tự tạo dòng phát sinh trong báo giá: name × qty × unit_price.
    unit_price = fields.Float(
        string='Đơn giá (VNĐ)', digits=(16, 0),
        help='Set > 0 nếu trường này tính theo số lượng × đơn giá '
             '(vd "WC" = 15M/cái). Để 0 nếu chỉ là text ghi chú.',
    )
    unit_label = fields.Char(
        string='Đơn vị',
        help='Vd "cái", "phòng", "m²" — hiển thị trong báo giá.',
    )


class VdLeadCustomValue(models.Model):
    _name = 'vd.lead.custom.value'
    _description = 'Giá trị trường khai thác tuỳ chọn (per lead)'
    _order = 'field_id'
    _rec_name = 'field_id'

    lead_id = fields.Many2one(
        'crm.lead', required=True, ondelete='cascade', index=True,
    )
    field_id = fields.Many2one(
        'vd.intake.custom.field', required=True, ondelete='cascade',
        domain="[('active', '=', True)]",
        string='Trường',
    )
    value = fields.Text(string='Giá trị')
    # Read-through cho display
    field_help = fields.Char(related='field_id.help_text', string='Gợi ý', readonly=True)

    _sql_constraints = [
        ('uniq_lead_field', 'unique(lead_id, field_id)',
         'Mỗi lead chỉ có 1 giá trị cho 1 trường khai thác.'),
    ]
