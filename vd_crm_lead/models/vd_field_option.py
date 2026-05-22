# -*- coding: utf-8 -*-
"""User-added options for any extensible Selection field.

Bất kỳ Selection field nào marked "extensible" sẽ dùng callable selection
đọc base list + records của model này. Widget JS phía client cung cấp
"+ Thêm mới" để user tạo option mà không cần code.
"""
import re
import unicodedata

from odoo import api, fields, models


def _slug(text):
    """Convert label → ASCII slug để dùng làm Selection key.
    Vd: 'Mái Nhật' → 'mai_nhat'."""
    if not text:
        return ''
    s = unicodedata.normalize('NFD', text)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_').lower()
    return s or 'opt'


class VdFieldOption(models.Model):
    _name = 'vd.field.option'
    _description = 'Lựa chọn người dùng tự thêm cho Selection field'
    _order = 'model_name, field_name, sequence, id'
    _sql_constraints = [
        ('model_field_key_unique',
         'unique(model_name, field_name, key)',
         'Key đã tồn tại cho field này.'),
    ]

    model_name = fields.Char(string='Model', required=True, index=True,
                             help='Tên kỹ thuật của model. Vd: crm.lead.')
    field_name = fields.Char(string='Field', required=True, index=True,
                             help='Tên kỹ thuật của field. Vd: vd_intake_house_type.')
    key = fields.Char(string='Key', required=True,
                      help='Giá trị nội bộ. Auto từ label nếu để trống.')
    label = fields.Char(string='Tên hiển thị', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    created_uid = fields.Many2one(
        'res.users', string='Người tạo',
        default=lambda self: self.env.user, readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('key') and vals.get('label'):
                vals['key'] = _slug(vals['label'])
            if vals.get('key'):
                # Tránh đụng key base selection (vd 'mai_bang') — append _ếu trùng.
                existing = self.search_count([
                    ('model_name', '=', vals.get('model_name')),
                    ('field_name', '=', vals.get('field_name')),
                    ('key', '=', vals['key']),
                ])
                if existing:
                    base = vals['key']
                    n = 2
                    while self.search_count([
                        ('model_name', '=', vals.get('model_name')),
                        ('field_name', '=', vals.get('field_name')),
                        ('key', '=', f'{base}_{n}'),
                    ]):
                        n += 1
                    vals['key'] = f'{base}_{n}'
        return super().create(vals_list)

    @api.model
    def quick_add(self, model_name, field_name, label):
        """RPC endpoint cho JS widget — tạo option, trả về (key, label)."""
        if not (model_name and field_name and label):
            return False
        opt = self.create({
            'model_name': model_name,
            'field_name': field_name,
            'label': label.strip(),
        })
        return {'key': opt.key, 'label': opt.label}

    @api.model
    def get_options(self, model_name, field_name):
        """Trả list (key, label) cho 1 field — dùng trong selection callable."""
        recs = self.search([
            ('model_name', '=', model_name),
            ('field_name', '=', field_name),
            ('active', '=', True),
        ])
        return [(r.key, r.label) for r in recs]
