"""v202.1: Backfill vấn đề 'Cân đối ngân sách' (cost_diff) cho lead TỒN ĐỌNG.

Bug 2026-05-31: logic auto-sinh "Cân đối ngân sách" khi tầm tài chính KH < giá
báo > 15% mới ship trong commit 220f56f (2026-05-31 11:55) — gồm cả lời gọi
trong action_save_intake_done. Các lead đã CHỐT THÔNG TIN TRƯỚC thời điểm đó
KHÔNG chạy qua code này → dù chênh >15% vẫn không có vấn đề cân đối nào.

Backfill: chạy lại _vd_auto_budget_problem cho mọi lead quote/negotiate đang mở.
Idempotent — method tự update / resolve / create đúng trạng thái (won/lost đã
được bỏ qua bên trong method).
"""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    leads = env['crm.lead'].search([
        ('active', '=', True),
        ('stage_id.code', 'in', ('quote', 'negotiate')),
        ('vd_intake_locked', '=', True),
    ])
    if not leads:
        _logger.info("[v202.1] Khong co lead quote/negotiate de backfill cost_diff")
        return
    _logger.info("[v202.1] Backfill _vd_auto_budget_problem cho %s lead", len(leads))
    try:
        # vd_skip_intake_lock=True → bypass guard create() (lead da locked san).
        leads.with_context(vd_skip_intake_lock=True)._vd_auto_budget_problem()
    except Exception as e:
        _logger.exception("[v202.1] Backfill cost_diff loi: %s", e)
