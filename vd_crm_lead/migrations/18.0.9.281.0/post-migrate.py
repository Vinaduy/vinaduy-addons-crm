# -*- coding: utf-8 -*-
"""Fix 2026-07-01: template báo giá bị gắn SAI móng/mái/tầng.

Bệnh: _compute_quote_template_id_auto CŨ chỉ gán template khi field TRỐNG và
KHÔNG BAO GIỜ chọn lại. NV auto-đoán móng (vd ≥2 tầng → Móng băng) rồi đổi sang
Cọc thì template DÍNH file băng cũ → chốt báo giá ra file móng SAI (trang data
ghi Cọc nhưng trang minh hoạ là Băng).

Code mới re-pick khi template hiện tại rớt khỏi danh sách gợi ý. Migration này
CHỮA DỮ LIỆU CŨ: recompute suggested + template cho các lead ĐANG mismatch,
CHỈ với báo giá CHƯA CHỐT (vd_quote_locked=False) để không đụng bản đã gửi KH.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Lead = env['crm.lead']

    leads = Lead.search([
        ('vd_quote_template_id', '!=', False),
        ('vd_quote_locked', '=', False),
    ])
    if not leads:
        _logger.info('vd 281: khong co lead can kiem tra template')
        return

    # Recompute suggested trước (đọc intake hiện tại) rồi để _compute auto
    # re-pick. Gọi trực tiếp method compute trên recordset.
    leads._compute_quote_template_suggested()

    fixed = []
    for rec in leads:
        old = rec.vd_quote_template_id
        sugg = rec.vd_quote_template_suggested_ids
        # Chỉ sửa khi template hiện tại MÂU THUẪN intake (rớt khỏi suggested)
        # và có gợi ý thay thế.
        if sugg and old and old.id not in sugg.ids:
            rec.vd_quote_template_id = sugg[0]
            fixed.append((rec.id, old.display_name, sugg[0].display_name))

    _logger.info('vd 281: da sua template cho %s lead mismatch', len(fixed))
    for lid, o, n in fixed[:80]:
        _logger.info('  lead %s: [%s] -> [%s]', lid, o, n)
