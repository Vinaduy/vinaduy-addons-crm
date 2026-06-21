# -*- coding: utf-8 -*-
from odoo import fields, models


class SlideChannelPartner(models.Model):
    """Luu ket qua thi gan nhat cua NV o tung khoa — phuc vu BANG LICH SU HOC trong
    popup 'Len lich hoc' (ai da thi / chua thi / diem bao nhieu)."""
    _inherit = 'slide.channel.partner'

    vd_exam_percent = fields.Integer(string='Diem thi (%)', default=0)
    vd_exam_passed = fields.Boolean(string='Da dat', default=False)
    vd_exam_attempts = fields.Integer(string='So lan thi', default=0)
    vd_exam_done_at = fields.Datetime(string='Lan thi gan nhat')
