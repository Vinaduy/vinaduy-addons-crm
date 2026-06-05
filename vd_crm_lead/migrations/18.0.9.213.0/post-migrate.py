"""v213.0: HẠN XỬ LÝ vấn đề + HỢP NHẤT bản tự động Cân đối ngân sách.

User spec 2026-06-06:
1. Hợp nhất bản TỰ ĐỘNG (code='cost_diff') với bản THỦ CÔNG (tag budget_balance):
   gán tag 'budget_balance' cho mọi cost_diff cũ chưa có tag → bản tự động
   cũng hiện đầy đủ section SỬA THÔNG TIN BÁO GIÁ (diện tích/móng/tầng).
   Bỏ qua nếu lead đã có sẵn 1 thẻ budget_balance (tránh phạm unique).
2. MỌI vấn đề có hạn xử lý: backfill deadline cho vấn đề cũ chưa có hạn =
   NOW + cấu hình (mặc định 7 ngày) — đặt mốc tươi từ lúc nâng cấp để tránh
   loạt vấn đề tồn đọng bị tính "quá hạn" ngay → spam báo trưởng phòng.
"""
import logging
from datetime import timedelta

from odoo import api, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Problem = env['vd.lead.problem']

    # ===== 1. Backfill tag budget_balance cho cost_diff cũ =====
    budget_tag = env.ref(
        'vd_crm_lead.nego_problem_budget_balance', raise_if_not_found=False)
    if budget_tag:
        probs = Problem.search([('code', '=', 'cost_diff'), ('tag_id', '=', False)])
        done = 0
        for p in probs:
            # Bỏ qua nếu lead đã có thẻ budget_balance khác (unique lead_id, tag_id)
            if p.lead_id.vd_lead_problem_ids.filtered(
                    lambda x: x.id != p.id and x.tag_id.id == budget_tag.id):
                continue
            try:
                with cr.savepoint():
                    p.tag_id = budget_tag.id
                done += 1
            except Exception as e:
                _logger.warning("[v213.0] Khong gan tag cho problem %s: %s", p.id, e)
        _logger.info("[v213.0] Gan tag budget_balance cho %s/%s cost_diff cu",
                     done, len(probs))

    # ===== 2. Backfill deadline cho mọi vấn đề chưa có hạn =====
    dd = int(env['ir.config_parameter'].sudo().get_param(
        'vd_crm_lead.problem_deadline_days', 7) or 7)
    fresh = fields.Datetime.now() + timedelta(days=dd)
    no_dl = Problem.search([('deadline', '=', False)])
    if no_dl:
        no_dl.write({'deadline': fresh})
    _logger.info("[v213.0] Backfill deadline (NOW+%s ngay) cho %s van de",
                 dd, len(no_dl))
