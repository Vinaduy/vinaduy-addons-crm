# -*- coding: utf-8 -*-
"""Tiền quảng cáo Facebook theo ngày (user 2026-10-10).

Nhập chi phí QC FB/ngày → báo cáo chi phí/1 data (tiền ÷ số data FB về trong ngày)
trên tab Chia số. Chỉ FB có chạy quảng cáo (TikTok/Zalo không)."""
from odoo import api, fields, models


class VdAdSpend(models.Model):
    _name = 'vd.ad.spend'
    _description = 'Tiền quảng cáo Facebook theo ngày'
    _order = 'date desc'

    date = fields.Date(string='Ngày', required=True, index=True)
    fb_amount = fields.Float(string='Tiền QC Facebook (đồng)')

    _sql_constraints = [
        ('uniq_date', 'unique(date)', 'Mỗi ngày chỉ nhập 1 dòng tiền quảng cáo.'),
    ]

    @api.model
    def vd_adspend_set(self, date_iso, fb_amount):
        """Lưu tiền QC FB cho 1 ngày (tạo mới hoặc cập nhật)."""
        d = fields.Date.from_string(date_iso)
        rec = self.sudo().search([('date', '=', d)], limit=1)
        amt = float(fb_amount or 0)
        if rec:
            rec.fb_amount = amt
        else:
            rec = self.sudo().create({'date': d, 'fb_amount': amt})
        return {'date': date_iso, 'fb_amount': rec.fb_amount}
