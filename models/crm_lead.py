from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    vinaduy_source_id = fields.Many2one(
        'vinaduy.crm.source',
        string='Nguồn VINADUY',
        tracking=True,
        help='Nguồn lead nội bộ VINADUY (OMICall, Zalo, Website...)',
    )

    project_type = fields.Selection(
        selection=[
            ('nha_pho', 'Nhà phố'),
            ('biet_thu', 'Biệt thự'),
            ('van_phong', 'Văn phòng'),
            ('nha_xuong', 'Nhà xưởng'),
            ('khac', 'Khác'),
        ],
        string='Loại công trình',
        tracking=True,
    )

    omicall_call_count = fields.Integer(
        string='Số cuộc gọi OMICall',
        default=0,
        readonly=True,
        help='Tổng số cuộc gọi qua OMICall liên quan tới lead này',
    )

    last_omicall_date = fields.Datetime(
        string='Cuộc gọi OMICall gần nhất',
        readonly=True,
    )
