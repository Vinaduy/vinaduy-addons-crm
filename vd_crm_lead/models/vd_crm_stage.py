from odoo import fields, models


class VdCrmStage(models.Model):
    _name = 'vd.crm.stage'
    _description = 'Trạng thái khách hàng'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True, copy=False, index=True,
        help='Mã ngắn để code lookup (new, potential, callback, quote, negotiate, won, lost).',
    )
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string='Gập trong kanban')
    is_won = fields.Boolean(string='Trạng thái chốt')
    is_lost = fields.Boolean(string='Trạng thái huỷ')
    color = fields.Integer(default=0)
    default_probability = fields.Float(
        string='Tỉ lệ chốt mặc định (%)', default=0,
        help='Base probability khi lead vào stage này. Lead.probability = base + activity modifiers.',
    )
    description = fields.Text()

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã trạng thái phải duy nhất.'),
    ]
