"""Post-migrate: gom 22 detailed category về 3 folder phẳng + delete old.

Step:
1. Create/get 3 root folder: BG MB, BG MN, BG - Gói 5T9
2. Cho mỗi template, reassign category_id về 1 trong 3 folder:
   - region_ids contains 'nam' AND name contains 'Gói 5T9' → BG - Gói 5T9
   - region_ids contains 'nam' → BG MN
   - region_ids contains 'bac' or 'trung' AND name contains 'Gói 5T9' → BG - Gói 5T9
   - region_ids contains 'bac' or 'trung' → BG MB
   - không có region → BG MB (default fallback)
3. Delete (archive) 22 detailed category cũ
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cat = env['vd.quote.template.category']
    Tpl = env['vd.quote.template']

    # Create 3 root folders (skip nếu đã có)
    folders = {}
    for code, name in [('mb', 'BG MB'), ('mn', 'BG MN'), ('goi', 'BG - Gói 5T9')]:
        existing = Cat.search([('name', '=', name)], limit=1)
        if existing:
            folders[code] = existing
        else:
            folders[code] = Cat.create({'name': name, 'sequence': 10})
            _logger.info("[vd_crm_lead] Created folder %s (id=%d)", name, folders[code].id)

    # Reassign templates
    all_templates = Tpl.search([])
    for t in all_templates:
        region_codes = set(t.region_ids.mapped('code'))
        name_low = (t.name or '').lower()
        is_goi_5t9 = '5t9' in name_low or 'gói 5' in name_low or 'gói5' in name_low

        if is_goi_5t9:
            target = folders['goi']
        elif 'nam' in region_codes:
            target = folders['mn']
        else:
            # Bắc, Trung, hoặc không có region → MB (Bắc+Trung dùng chung)
            target = folders['mb']

        if t.category_id.id != target.id:
            t.category_id = target.id

    # Archive (don't delete — preserve history) các category detailed cũ
    # (category nào KHÔNG phải 3 folder mới + có name khớp pattern BT-/MN-)
    folder_ids = {f.id for f in folders.values()}
    old_cats = Cat.search([
        ('id', 'not in', list(folder_ids)),
        '|', ('name', '=ilike', 'BT %'),
        ('name', '=ilike', 'MN %'),
    ])
    if old_cats:
        # Delete vì không còn dùng + không có template ref tới (đã reassign)
        old_ids = old_cats.ids
        old_cats.unlink()
        _logger.info("[vd_crm_lead] Deleted %d detailed categories cũ: %s",
                      len(old_ids), old_ids)

    # Cũng xoá 4 category seed cũ (Mái Nhật/Thái/Miền Bắc/Miền Nam)
    legacy_seed = Cat.search([
        ('name', 'in', ['Mái Nhật', 'Mái Thái', 'Miền Bắc', 'Miền Nam']),
    ])
    if legacy_seed:
        legacy_seed.unlink()
        _logger.info("[vd_crm_lead] Deleted %d legacy seed categories", len(legacy_seed))
