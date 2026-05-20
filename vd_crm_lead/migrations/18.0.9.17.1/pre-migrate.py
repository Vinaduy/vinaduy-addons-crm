"""Pre-migrate: rename column pct_mong_coc → pct_mong_don và
pct_mong_bang → pct_mong_bang_coc trên vd_pricing_region.

Giá trị hiện tại đã đúng (10% và 15%), chỉ tên field bị gán nhầm semantic
(coc thay vì đơn). ALTER TABLE RENAME giữ nguyên giá trị, Odoo tự update
schema còn lại.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'vd_pricing_region'
          AND column_name IN ('pct_mong_coc', 'pct_mong_bang', 'pct_mong_don', 'pct_mong_bang_coc')
    """)
    cols = {r[0] for r in cr.fetchall()}

    if 'pct_mong_coc' in cols and 'pct_mong_don' not in cols:
        cr.execute("""
            ALTER TABLE vd_pricing_region
            RENAME COLUMN pct_mong_coc TO pct_mong_don
        """)
        _logger.info("[vd_crm_lead] Renamed pct_mong_coc → pct_mong_don")

    if 'pct_mong_bang' in cols and 'pct_mong_bang_coc' not in cols:
        cr.execute("""
            ALTER TABLE vd_pricing_region
            RENAME COLUMN pct_mong_bang TO pct_mong_bang_coc
        """)
        _logger.info("[vd_crm_lead] Renamed pct_mong_bang → pct_mong_bang_coc")
