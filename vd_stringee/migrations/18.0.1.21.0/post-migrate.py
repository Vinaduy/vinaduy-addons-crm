"""v1.21.0: Backfill Stringee User ID cho NV nội bộ đang TRỐNG.

User spec 2026-06-06: tự động hoá — NV mới auto có stringee_user_id; đồng thời
gán luôn cho NV hiện hữu đang trống (vd Khiết Anh/ctv.2) để gọi được ngay.
ID = 'vduser_<id>' (duy nhất theo record id, ổn định khi đổi login).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    users = env['res.users'].search([
        ('share', '=', False),
        ('id', '!=', SUPERUSER_ID),
        '|', ('stringee_user_id', '=', False), ('stringee_user_id', '=', ''),
    ])
    done = 0
    for u in users:
        u.stringee_user_id = 'vduser_%d' % u.id
        done += 1
    _logger.info("[v1.21.0] Backfill stringee_user_id cho %s NV noi bo", done)
