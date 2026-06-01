# -*- coding: utf-8 -*-
"""Cấu hình CRM — ngưỡng 'Yêu cầu tìm vấn đề' (user spec 2026-06-01).

Lưu qua ir.config_parameter để hàm backend + cron đọc:
  - vd_crm_lead.problem_find_enabled   (bool)  bật/tắt cảnh báo + auto-khoá
  - vd_crm_lead.problem_find_pct       (int)   ngưỡng % KH chưa có vấn đề
  - vd_crm_lead.problem_find_grace_days(int)   số ngày gia hạn trước khi khoá
"""
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vd_problem_find_enabled = fields.Boolean(
        string='Bật cảnh báo "Yêu cầu tìm vấn đề"',
        config_parameter='vd_crm_lead.problem_find_enabled',
        default=True,
        help='Khi bật: dashboard hiện banner nếu > ngưỡng % KH chưa có vấn đề, '
             'và tự khoá NV sau số ngày gia hạn nếu không xử lý.',
    )
    vd_problem_find_pct = fields.Integer(
        string='Ngưỡng % KH chưa có vấn đề',
        config_parameter='vd_crm_lead.problem_find_pct',
        default=20,
        help='Nếu tỷ lệ KH chưa có vấn đề trong bảng THI CÔNG GẤP hoặc XỬ LÝ '
             'VẤN ĐỀ vượt mức này → hiện banner cảnh báo.',
    )
    vd_problem_find_grace_days = fields.Integer(
        string='Số ngày gia hạn trước khi khoá',
        config_parameter='vd_crm_lead.problem_find_grace_days',
        default=3,
        help='NV vượt ngưỡng liên tục quá số ngày này mà chưa xử lý → tự động '
             'khoá: không bấm mở được KHÁCH MỚI tới khi xử lý xong.',
    )
