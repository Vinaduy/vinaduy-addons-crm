"""Pool số tổng đài Stringee — admin quản lý, assign cho từng NV.

Mỗi NV chỉ dùng 1 hotline (res.users.stringee_from_number_id).
Khi NV gọi ra:
- Ưu tiên dùng số hotline assign cho NV
- Fallback global config 'vd_stringee.from_number' nếu NV chưa assign

Đặt model trong vd_stringee để không phụ thuộc vd_crm_lead.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def _digits_only(s):
    return ''.join(c for c in (s or '') if c.isdigit())


class VdStringeeHotline(models.Model):
    _name = 'vd.stringee.hotline'
    _description = 'Số tổng đài Stringee'
    _order = 'team_label, carrier, name'

    name = fields.Char(
        string='Tên gọi', required=True,
        help='Label nội bộ. Vd: "HCM1 - Viettel hotline".',
    )
    number = fields.Char(
        string='Số tổng đài', required=True,
        help='Số phone đã mua trên Stringee (format E.164, vd: 84917690625).',
    )
    carrier = fields.Selection([
        ('viettel', 'Viettel'),
        ('mobi', 'MobiFone'),
        ('vina', 'Vinaphone'),
        ('vietnamobile', 'Vietnamobile'),
        ('gmobile', 'Gmobile'),
        ('itelecom', 'iTel'),
        ('other', 'Khác'),
    ], required=True, default='viettel', string='Nhà mạng')
    team_label = fields.Char(
        string='Team',
        help='HCM1/HCM2/HN/QN... — chỉ để admin filter, không ràng buộc logic.',
    )
    note = fields.Text(string='Ghi chú nội bộ')
    active = fields.Boolean(default=True)

    user_ids = fields.One2many(
        'res.users', 'stringee_from_number_id', string='NV đang dùng',
    )
    user_count = fields.Integer(
        string='Số NV dùng', compute='_compute_user_count',
    )

    _sql_constraints = [
        ('number_unique', 'unique(number)',
         'Số tổng đài này đã được tạo trước đó — kiểm tra lại danh sách.'),
    ]

    @api.depends('user_ids')
    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.user_ids)

    @api.constrains('number')
    def _check_number_e164(self):
        for rec in self:
            digits = _digits_only(rec.number)
            if len(digits) < 9:
                raise ValidationError(_(
                    'Số tổng đài "%s" không hợp lệ — cần ít nhất 9 chữ số.'
                ) % rec.number)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number'):
                # Normalize: chỉ giữ chữ số
                vals['number'] = _digits_only(vals['number'])
        return super().create(vals_list)

    def write(self, vals):
        if 'number' in vals and vals['number']:
            vals['number'] = _digits_only(vals['number'])
        return super().write(vals)
