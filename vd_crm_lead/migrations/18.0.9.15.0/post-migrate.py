"""Migrate vd.quote.template.category region (Selection) → region_ids (M2M).

- Bắc → region_ids = [bac, trung], rename "MB - " → "BT - "
- Trung → region_ids = [trung]
- Nam → region_ids = [nam], giữ tên "MN - "
- Drop old region column sau khi migrate xong (giữ data tạm trước cho safe).
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Check old column còn tồn tại không (nếu module mới install lần đầu thì
    # không có column này → skip migration)
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'vd_quote_template_category' AND column_name = 'region'
    """)
    if not cr.fetchone():
        _logger.info("[vd_crm_lead] Cột 'region' không tồn tại — skip migrate region → region_ids")
        return

    Region = env['vd.quote.region']
    bac = Region.search([('code', '=', 'bac')], limit=1)
    trung = Region.search([('code', '=', 'trung')], limit=1)
    nam = Region.search([('code', '=', 'nam')], limit=1)
    if not (bac and trung and nam):
        _logger.warning("[vd_crm_lead] Seed regions chưa load — skip migrate")
        return

    Cat = env['vd.quote.template.category']
    # Đọc raw data từ column region cũ
    cr.execute("SELECT id, region, name FROM vd_quote_template_category WHERE region IS NOT NULL")
    rows = cr.fetchall()
    _logger.info("[vd_crm_lead] Migrate %d category record(s) từ region → region_ids", len(rows))

    for cat_id, region_code, name in rows:
        cat = Cat.browse(cat_id)
        if not cat.exists():
            continue
        if region_code == 'bac':
            cat.region_ids = [(6, 0, [bac.id, trung.id])]
            # Rename MB → BT
            if name and name.startswith('MB '):
                cat.name = 'BT ' + name[3:]
            elif name and name.startswith('MB-'):
                cat.name = 'BT-' + name[3:]
        elif region_code == 'trung':
            cat.region_ids = [(6, 0, [trung.id])]
        elif region_code == 'nam':
            cat.region_ids = [(6, 0, [nam.id])]
        _logger.info("[vd_crm_lead]   cat %d (%s) region=%s → ids=%s", cat_id, name, region_code,
                      cat.region_ids.mapped('code'))

    # Drop column region cũ (cleanup)
    try:
        cr.execute("ALTER TABLE vd_quote_template_category DROP COLUMN IF EXISTS region")
        _logger.info("[vd_crm_lead] Dropped column vd_quote_template_category.region")
    except Exception as e:
        _logger.warning("[vd_crm_lead] Could not drop region column: %s", e)
