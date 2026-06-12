# -*- coding: utf-8 -*-
"""Cài đặt KHOÁ — cấu hình khoá 3 bảng dashboard (user spec 2026-06-05).

Lưu qua ir.config_parameter để backend + cron đọc.

KHÁCH MỚI (chưa gọi đủ):
  - vd_crm_lead.callwatch_enabled        (bool)
  - vd_crm_lead.callwatch_required_days  (int)  cần gọi ở >= N ngày làm việc
  - vd_crm_lead.callwatch_window_workdays(int)  trong cửa sổ W ngày làm việc

THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ (quá hạn tìm vấn đề):
  - vd_crm_lead.problem_find_enabled        (bool)  bật/tắt chung 2 bảng
  - vd_crm_lead.problem_find_urgent_pct     (int)   ngưỡng % chưa có vấn đề
  - vd_crm_lead.problem_find_urgent_grace   (int)   số ngày gia hạn rồi khoá
  - vd_crm_lead.problem_find_xlvd_pct       (int)
  - vd_crm_lead.problem_find_xlvd_grace     (int)
(Giữ problem_find_pct / problem_find_grace_days cũ làm default fallback.)
"""
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ===== KHÁCH MỚI (chưa gọi đủ) =====
    vd_callwatch_enabled = fields.Boolean(
        string='Bật khoá "Khách mới chưa gọi"',
        config_parameter='vd_crm_lead.callwatch_enabled',
        default=True,
        help='Khi bật: NV không gọi đủ số ngày yêu cầu cho khách mới → khoá bảng '
             'KHÁCH MỚI.',
    )
    vd_callwatch_required_days = fields.Integer(
        string='Khách mới — số ngày phải gọi',
        config_parameter='vd_crm_lead.callwatch_required_days',
        default=3,
        help='Mỗi KH mới cần có cuộc gọi đi ở ít nhất N ngày làm việc khác nhau.',
    )
    vd_callwatch_window_workdays = fields.Integer(
        string='Khách mới — cửa sổ (ngày làm việc)',
        config_parameter='vd_crm_lead.callwatch_window_workdays',
        default=7,
        help='Tính trong W ngày làm việc kể từ ngày thêm khách.',
    )
    # User spec 2026-06-12: KHOÁ TOÀN BỘ bảng khi tồn quá nhiều KH mới CHƯA gọi.
    vd_uncalled_new_lock_threshold = fields.Integer(
        string='Khoá toàn bộ khi KH mới CHƯA GỌI vượt số',
        config_parameter='vd_crm_lead.uncalled_new_lock_threshold',
        default=15,
        help='Khi 1 NV tồn HƠN N khách MỚI chưa có cuộc gọi nào → KHOÁ TẤT CẢ '
             'bảng (trừ chính các khách mới đó) ép NV gọi cho đến khi còn ≤ N thì '
             'tự mở. Admin xem NV đó cũng thấy khoá. Đặt 0 = TẮT tính năng.',
    )
    # User spec 2026-06-12: CHẶN chia/up thêm số mới cho NV đang tồn nhiều KH chưa gọi.
    vd_distribute_block_uncalled = fields.Integer(
        string='Chặn chia thêm số khi KH mới CHƯA GỌI vượt',
        config_parameter='vd_crm_lead.distribute_block_uncalled',
        default=20,
        help='KHÔNG cho chia/up thêm số mới cho 1 NV nếu TỔNG dự kiến (đang tồn + '
             'sắp chia) khách MỚI chưa gọi VƯỢT N. Mỗi NV chỉ nhận tới khi đủ N. '
             'Đặt 0 = TẮT tính năng.',
    )

    # ===== THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ (tìm vấn đề) =====
    vd_problem_find_enabled = fields.Boolean(
        string='Bật khoá "Yêu cầu tìm vấn đề"',
        config_parameter='vd_crm_lead.problem_find_enabled',
        default=True,
        help='Khi bật: 2 bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ tự khoá nếu quá hạn.',
    )
    vd_pf_urgent_pct = fields.Integer(
        string='Thi công gấp — ngưỡng % chưa có vấn đề',
        config_parameter='vd_crm_lead.problem_find_urgent_pct',
        default=20,
        help='% KH chưa có vấn đề ở bảng THI CÔNG GẤP vượt mức này → cảnh báo.',
    )
    vd_pf_urgent_grace = fields.Integer(
        string='Thi công gấp — số ngày gia hạn rồi khoá',
        config_parameter='vd_crm_lead.problem_find_urgent_grace',
        default=3,
        help='Vượt ngưỡng liên tục quá số ngày này → khoá bảng THI CÔNG GẤP.',
    )
    vd_pf_xlvd_pct = fields.Integer(
        string='Xử lý vấn đề — ngưỡng % chưa có vấn đề',
        config_parameter='vd_crm_lead.problem_find_xlvd_pct',
        default=20,
        help='% KH chưa có vấn đề ở bảng XỬ LÝ VẤN ĐỀ vượt mức này → cảnh báo.',
    )
    vd_pf_xlvd_grace = fields.Integer(
        string='Xử lý vấn đề — số ngày gia hạn rồi khoá',
        config_parameter='vd_crm_lead.problem_find_xlvd_grace',
        default=3,
        help='Vượt ngưỡng liên tục quá số ngày này → khoá bảng XỬ LÝ VẤN ĐỀ.',
    )

    # ===== HẠN XỬ LÝ VẤN ĐỀ (deadline + gia hạn) — user spec 2026-06-06 =====
    vd_problem_deadline_days = fields.Integer(
        string='Hạn xử lý mỗi vấn đề (ngày)',
        config_parameter='vd_crm_lead.problem_deadline_days',
        default=7,
        help='Khi tạo vấn đề mới → tự đặt hạn xử lý = ngày tạo + N ngày.',
    )
    vd_problem_extension_days = fields.Integer(
        string='Mỗi lần gia hạn thêm (ngày)',
        config_parameter='vd_crm_lead.problem_extension_days',
        default=7,
        help='Mỗi lần bấm "Gia hạn" → cộng thêm N ngày vào hạn xử lý.',
    )
    vd_problem_extension_max = fields.Integer(
        string='Số lần gia hạn không cần duyệt',
        config_parameter='vd_crm_lead.problem_extension_max',
        default=3,
        help='NV được tự gia hạn tối đa N lần. Vượt quá phải trưởng phòng/admin duyệt.',
    )
