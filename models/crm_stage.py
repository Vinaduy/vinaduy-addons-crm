from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    sla_days = fields.Integer(
        string='SLA (ngày)',
        default=0,
        help='Số ngày tối đa lead được phép ở stage này. '
             '0 = không áp dụng SLA. '
             'Quá hạn → cron daily sẽ tạo activity cảnh báo cho NV phụ trách.',
    )
