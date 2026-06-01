# -*- coding: utf-8 -*-
"""v1.12.0 — Gọi CÙNG MẠNG (user spec 2026-06-01).

1) Phân loại lại `carrier` cho MỌI số tổng đài theo đầu số (sửa 20 số đang 'other').
2) Seed m2m stringee_hotline_ids từ số đơn cũ (stringee_from_number_id).
3) Tự gán đủ 3 mạng (Viettel + Vinaphone + MobiFone) cho từng NV sales —
   round-robin trên pool để cân tải. Giữ nguyên số NV đã có sẵn cho mạng đó.
"""
import logging

from odoo import api, SUPERUSER_ID
from odoo.addons.vd_stringee.models.vd_stringee_hotline import vd_carrier_from_number

_logger = logging.getLogger(__name__)
_CARRIERS = ['viettel', 'vina', 'mobi']


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Hotline = env['vd.stringee.hotline'].with_context(active_test=False)

    # 1) Phân loại lại nhà mạng theo đầu số
    fixed = 0
    for h in Hotline.search([]):
        c = vd_carrier_from_number(h.number)
        if h.carrier != c:
            h.carrier = c
            fixed += 1
    _logger.info("[v1.12.0] Re-classified carrier cho %s số tổng đài", fixed)

    # NV sales eligible
    sales = env['res.users'].search([
        ('share', '=', False),
        ('active', '=', True),
        ('groups_id', 'in', env.ref('sales_team.group_sale_salesman').id),
    ])

    # 2) Seed m2m từ số đơn cũ
    for u in sales:
        old = u.stringee_from_number_id
        if old and old not in u.stringee_hotline_ids:
            u.stringee_hotline_ids = [(4, old.id)]

    # 3) Auto-gán đủ 3 mạng/NV — round-robin
    pools = {c: Hotline.search([('active', '=', True), ('carrier', '=', c)]) for c in _CARRIERS}
    counters = {c: 0 for c in _CARRIERS}
    assigned = 0
    for u in sales:
        have = set(u.stringee_hotline_ids.mapped('carrier'))
        add_ids = []
        for c in _CARRIERS:
            if c in have:
                continue
            pool = pools[c]
            if not pool:
                _logger.warning("[v1.12.0] Pool %s rỗng — NV %s không được gán mạng này", c, u.login)
                continue
            hl = pool[counters[c] % len(pool)]
            counters[c] += 1
            add_ids.append(hl.id)
        if add_ids:
            u.stringee_hotline_ids = [(4, hid) for hid in add_ids]
            assigned += 1
    _logger.info("[v1.12.0] Auto-gán mạng cho %s/%s NV sales", assigned, len(sales))
