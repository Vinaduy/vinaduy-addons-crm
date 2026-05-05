from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vinaduy_auto_assign_enabled = fields.Boolean(
        string='Tự động phân bổ lead cho nhân viên (round-robin global)',
        config_parameter='vinaduy_crm.auto_assign_enabled',
        default=True,
        help='Khi bật: lead mới chưa có nhân viên sẽ tự động được gán cho '
             'nhân viên kế tiếp trong vòng tròn 18 NV (HCM1+HCM2+HCM3+HN). '
             'Khi tắt: lead mới sẽ giữ trống user_id, cần gán thủ công.',
    )
