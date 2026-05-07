from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    code = fields.Char(
        index=True, copy=False,
        help='Mã ngắn dùng cho code lookup (new, potential, callback, quote, negotiate, won, lost).',
    )
    default_probability = fields.Float(
        string='Tỉ lệ chốt mặc định (%)', default=0,
        help='Base probability của heuristic — lead.probability = base + activity modifiers.',
    )
    is_lost = fields.Boolean(
        string='Trạng thái huỷ',
        help='Nếu bật, lead chuyển sang stage này sẽ tự archive (active=False).',
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã trạng thái phải duy nhất.'),
    ]
