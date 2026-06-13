# -*- coding: utf-8 -*-
"""Backfill res.users.vd_team từ tiền tố TÊN cho NV hiện có (user spec 2026-06-13).

Trước đây phòng ban suy tự động từ tiền tố tên ("HCM1 - Tên" → HCM1). Giờ phòng
ban là thẻ chọn được (vd_team). Để NV cũ hiện đúng thẻ ngay sau upgrade, gán
vd_team = tiền tố tên nếu khớp 1 trong các phòng ban có sẵn. Tiền tố lạ → để trống
(vd_team_label vẫn tự suy từ tên như cũ).
"""
import re

from odoo import SUPERUSER_ID, api

_VALID = {'HCM1', 'HCM2', 'HN', 'CTV', 'VINADUY'}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    users = env['res.users'].with_context(active_test=False).search(
        [('share', '=', False)])
    for u in users:
        if u.vd_team:
            continue
        m = re.match(r'^([A-ZĐ]+\d*)\s*[-–—]\s*', u.name or '')
        prefix = m.group(1) if m else ''
        if prefix in _VALID:
            u.vd_team = prefix
