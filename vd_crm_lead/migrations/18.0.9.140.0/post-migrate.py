"""Reload vd.district = HUYỆN CŨ (705) map ve tinh moi via merge map.

User spec 2026-05-27 (revert ward approach):
- Tinh/Thanh: GIU 34 moi (khong doi)
- Xa/Phuong: BO 5-city ward data + Reload toan bo huyen cu (vn_districts.py)
  voi state_id moi via VN_PROVINCE_MERGE_MAP.

Vi du: Tuyen Quang moi = Tuyen Quang cu + Ha Giang cu.
→ Cac huyen cua Ha Giang + huyen cua Tuyen Quang deu the hien duoi
  state_id = "Tuyen Quang" moi.

Strategy:
1. DELETE all vd.district (lead FK -> set null tu dong)
2. INSERT moi tu VN_DISTRICTS (cu) voi state_id = NEW province (qua mapping)
3. Dedup (state_id, name) trong cung 1 tinh moi
"""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        from odoo.addons.vd_crm_lead.data.vn_districts import VN_DISTRICTS
        from odoo.addons.vd_crm_lead.data.vn_admin_2025 import VN_PROVINCE_MERGE_MAP
    except Exception:
        _logger.exception("[vd_crm_lead 9.140] Cannot import data files")
        return

    State = env['res.country.state'].sudo()
    District = env['vd.district'].sudo()
    vn_country = env.ref('base.vn', raise_if_not_found=False)
    if not vn_country:
        _logger.warning("[vd_crm_lead 9.140] base.vn not found")
        return

    # ===== Step 1: Wipe all existing districts =====
    existing = District.search([])
    if existing:
        existing.unlink()
        _logger.info("[vd_crm_lead 9.140] Deleted %d existing wards", len(existing))

    # ===== Step 2: Build state lookup (34 new provinces by name) =====
    new_states = State.search([
        ('country_id', '=', vn_country.id),
        ('vd_is_active_2025', '=', True),
    ])
    by_new_name = {s.name: s for s in new_states}

    # ===== Step 3: Insert old huyen mapped to new province =====
    to_create = []
    seen = set()  # (state_id, huyen_name) dedup
    skipped = 0
    for old_province, huyens in VN_DISTRICTS.items():
        new_name = VN_PROVINCE_MERGE_MAP.get(old_province, old_province)
        new_state = by_new_name.get(new_name)
        if not new_state:
            _logger.warning(
                "[vd_crm_lead 9.140] No new state for old=%s new=%s",
                old_province, new_name,
            )
            skipped += len(huyens)
            continue
        for huyen in huyens:
            key = (new_state.id, huyen)
            if key in seen:
                continue
            seen.add(key)
            to_create.append({'name': huyen, 'state_id': new_state.id})

    if to_create:
        District.create(to_create)
    _logger.info(
        "[vd_crm_lead 9.140] Created %d huyen records (skipped %d)",
        len(to_create), skipped,
    )
    _logger.info("[vd_crm_lead 9.140] DISTRICT MIGRATION COMPLETED")
