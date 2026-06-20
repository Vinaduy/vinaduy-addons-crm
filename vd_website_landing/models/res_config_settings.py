# -*- coding: utf-8 -*-
"""Cấu hình Google Ads conversion cho trang landing (admin sửa được).

Lưu vào ir.config_parameter để admin chỉnh trong Cài đặt mà không cần sửa code.
Controller serve landing đọc các tham số này để chèn mã gtag.
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Bật/tắt toàn bộ tracking Google Ads trên landing.
    vd_gads_enabled = fields.Boolean(
        string="Bật Google Ads tracking (landing)",
        config_parameter='vd_website_landing.gads_enabled',
    )
    # ID thẻ Google Ads, dạng AW-XXXXXXXXXX.
    vd_gads_conversion_id = fields.Char(
        string="Google Ads Conversion ID",
        help="Dạng AW-XXXXXXXXXX (lấy trong Code 1 của Google Ads).",
        config_parameter='vd_website_landing.gads_conversion_id',
    )
    # Nhãn chuyển đổi 'Nhấp để gọi', phần sau dấu '/' trong send_to.
    vd_gads_call_label = fields.Char(
        string="Nhãn chuyển đổi - Nhấp để gọi",
        help="Phần sau dấu '/' trong send_to của Code 2, "
             "ví dụ mH4ICIqqs8IcEMKdvORD.",
        config_parameter='vd_website_landing.gads_call_label',
    )
