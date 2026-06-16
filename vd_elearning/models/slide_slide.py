# -*- coding: utf-8 -*-
from odoo import fields, models


class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    # Noi dung soan tu trinh WYSIWYG cua Vinaduy - KHONG sanitize de giu nguyen
    # bang, anh, video (iframe), style inline... (html_content goc bi cat cac the nay).
    vd_body = fields.Html('Noi dung Vinaduy', sanitize=False)
