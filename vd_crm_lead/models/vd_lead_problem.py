# -*- coding: utf-8 -*-
"""Vấn đề từng KH gặp phải khi đàm phán — tracker dạng row.

Mỗi lead có 1 hoặc nhiều vấn đề. Mỗi vấn đề là 1 row: tên + cách xử lý + tiến độ.
Mục đích: ép NV phải XỬ LÝ TỪNG VẤN ĐỀ cụ thể, không nói chung chung.
2 vấn đề mặc định auto-tạo khi lead vào stage Đàm phán:
- CHÊNH LỆCH CHI PHÍ
- THỜI GIAN KHỞI CÔNG
NV có thể thêm vấn đề khác qua nút "+ Thêm vấn đề".
"""
from odoo import models, fields, api


class VdLeadProblem(models.Model):
    _name = 'vd.lead.problem'
    _description = 'Vấn đề KH trong đàm phán'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    lead_id = fields.Many2one(
        'crm.lead', string='KH', required=True, ondelete='cascade', index=True,
    )
    tag_id = fields.Many2one(
        'vd.nego.problem', string='Thẻ vấn đề', ondelete='set null',
        help='Thẻ chọn từ catalog 12 vấn đề mẫu (NV bấm "+ Tạo vấn đề" để pick).',
    )
    name = fields.Char(
        string='Tên vấn đề', required=True,
        help='Tự fill từ tag_id khi chọn từ catalog. Có thể custom cho 2 row mặc định.',
    )
    tag_display = fields.Char(
        string='Thẻ vấn đề', compute='_compute_tag_display', store=False,
        help='Hiển thị "icon name" gộp — dùng cho cột hiển thị trong list view.',
    )
    tag_tip_html = fields.Html(
        string='Tips gợi ý',
        related='tag_id.tip_html', sanitize=False, readonly=True,
        help='Mẹo xử lý đàm phán theo tag — đọc từ catalog vd.nego.problem.',
    )
    code = fields.Char(
        string='Mã (built-in)', copy=False,
        help='Mã cho vấn đề mặc định (cost_diff, start_time). Custom row để trống.',
    )
    nv_handling = fields.Text(
        string='Cách xử lý / Tiến độ',
        help='NV ghi rõ đã làm gì để giải quyết vấn đề này: gọi KH N lần, gửi phương án X, '
             'thương lượng giảm Y đồng, hẹn gặp ngày Z...',
    )
    status = fields.Selection([
        ('open', '🔴 Chưa xử lý'),
        ('in_progress', '🟡 Đang xử lý'),
        ('resolved', '🟢 Đã giải quyết'),
    ], string='Trạng thái', default='open', required=True, index=True)
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)
    is_default = fields.Boolean(
        string='Mặc định', default=False,
        help='True nếu là 1 trong 2 vấn đề mặc định (không cho xoá).',
    )

    _sql_constraints = [
        ('lead_tag_uniq', 'unique(lead_id, tag_id)',
         'Mỗi vấn đề chỉ được thêm 1 lần cho 1 KH.'),
    ]

    @api.depends('tag_id', 'tag_id.icon', 'tag_id.name', 'name')
    def _compute_tag_display(self):
        for rec in self:
            if rec.tag_id:
                icon = rec.tag_id.icon or '❓'
                rec.tag_display = f"{icon} {rec.tag_id.name}"
            else:
                rec.tag_display = rec.name or ''

    @api.onchange('tag_id')
    def _onchange_tag_id(self):
        """Khi NV pick tag → tự fill name từ tag để hiển thị nhất quán."""
        if self.tag_id:
            self.name = self.tag_id.name
