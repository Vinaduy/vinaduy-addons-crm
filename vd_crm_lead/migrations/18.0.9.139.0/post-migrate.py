"""Migrate 63 tinh cu -> 34 tinh moi (sau cai cach 01/07/2025).

post_init_hook chi chay khi INSTALL — KHONG chay khi UPGRADE.
Migration script nay chay khi upgrade module tu version < 9.138.

Logic:
- Rename TP X -> X (Da Nang, Hai Phong, Can Tho), Thua Thien-Hue -> Hue
- Migrate crm_lead.vd_intake_province_id + res.partner.state_id
- Rename tinh cu thanh "X (cu - da sap nhap)"
- Mark 34 tinh moi vd_is_active_2025=True
- Load wards moi (idempotent)
"""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        from odoo.addons.vd_crm_lead.data.vn_admin_2025 import (
            VN_PROVINCES_2025, VN_PROVINCE_MERGE_MAP, VN_WARDS_2025,
        )
    except Exception:
        _logger.exception("[vd_crm_lead 9.138] Cannot import vn_admin_2025")
        return

    State = env['res.country.state'].sudo()
    District = env['vd.district'].sudo()
    Lead = env['crm.lead']
    Partner = env['res.partner']
    vn_country = env.ref('base.vn', raise_if_not_found=False)
    if not vn_country:
        _logger.warning("[vd_crm_lead 9.138] base.vn country not found")
        return

    DB_NAME_ALIASES = {
        'TP. Hồ Chí Minh': 'TP Hồ Chí Minh',
        'Hồ Chí Minh': 'TP Hồ Chí Minh',
        'TP Hải Phòng': 'Hải Phòng',
        'TP Đà Nẵng': 'Đà Nẵng',
        'TP Cần Thơ': 'Cần Thơ',
        'Thừa Thiên - Huế': 'Huế',
        'Thừa Thiên Huế': 'Huế',
        'Bà Rịa-Vũng Tàu': 'Bà Rịa - Vũng Tàu',
    }

    all_states = State.search([('country_id', '=', vn_country.id)])
    by_name = {s.name.strip(): s for s in all_states}
    new_province_names = {p['name'] for p in VN_PROVINCES_2025}

    # ===== Rename DB aliases (TP X → X, Thừa Thiên-Huế → Huế) =====
    rename_count = 0
    for old_db, target in DB_NAME_ALIASES.items():
        if target not in new_province_names:
            continue
        if target in by_name:
            continue  # target đã tồn tại
        if old_db in by_name:
            old_state = by_name[old_db]
            old_state.write({'name': target})
            by_name[target] = old_state
            del by_name[old_db]
            rename_count += 1
    _logger.info("[vd_crm_lead 9.138] Renamed %d DB aliases", rename_count)

    # ===== Tạo các tỉnh mới chưa có trong DB =====
    create_count = 0
    for prov in VN_PROVINCES_2025:
        if prov['name'] not in by_name:
            try:
                new_state = State.create({
                    'name': prov['name'],
                    'country_id': vn_country.id,
                    'code': 'V' + str(create_count + 100)[-2:],
                })
                by_name[prov['name']] = new_state
                create_count += 1
            except Exception as e:
                _logger.warning(
                    "[vd_crm_lead 9.138] Cannot create %s: %s", prov['name'], e
                )
    _logger.info("[vd_crm_lead 9.138] Created %d new provinces", create_count)

    # ===== Migrate FK old → new =====
    migrate_count = 0
    for old_name, new_name in VN_PROVINCE_MERGE_MAP.items():
        if old_name == new_name:
            continue
        old_state = by_name.get(old_name)
        new_state = by_name.get(new_name)
        if not old_state or not new_state or old_state.id == new_state.id:
            continue
        # crm.lead
        try:
            leads = Lead.search([
                ('vd_intake_province_id', '=', old_state.id),
            ])
            if leads:
                leads.with_context(
                    vd_skip_intake_lock=True, mail_notrack=True,
                ).write({'vd_intake_province_id': new_state.id})
                migrate_count += len(leads)
        except Exception as e:
            _logger.warning(
                "[vd_crm_lead 9.138] Lead migrate %s→%s failed: %s",
                old_name, new_name, e,
            )
        # res.partner
        try:
            partners = Partner.search([('state_id', '=', old_state.id)])
            if partners:
                partners.with_context(mail_notrack=True).write(
                    {'state_id': new_state.id}
                )
        except Exception:
            pass
        # Rename old state
        try:
            old_state.write({'name': old_name + ' (cũ - đã sáp nhập)'})
        except Exception:
            pass
    _logger.info("[vd_crm_lead 9.138] Migrated %d lead FKs", migrate_count)

    # ===== Mark 34 active 2025 =====
    mark_count = 0
    for name in new_province_names:
        state = by_name.get(name)
        if state and not state.vd_is_active_2025:
            try:
                state.write({'vd_is_active_2025': True})
                mark_count += 1
            except Exception as e:
                _logger.warning(
                    "[vd_crm_lead 9.138] Cannot mark %s: %s", name, e
                )
    _logger.info("[vd_crm_lead 9.138] Marked %d provinces vd_is_active_2025=True", mark_count)

    # ===== Load wards (idempotent) =====
    ward_count = 0
    to_create = []
    seen = set()
    for province_name, wards in VN_WARDS_2025.items():
        state = by_name.get(province_name)
        if not state:
            continue
        existing = set(District.search([('state_id', '=', state.id)]).mapped('name'))
        for name in wards:
            key = (state.id, name)
            if name in existing or key in seen:
                continue
            seen.add(key)
            to_create.append({'name': name, 'state_id': state.id})
    if to_create:
        District.create(to_create)
        ward_count = len(to_create)
    _logger.info("[vd_crm_lead 9.138] Created %d new wards", ward_count)
    _logger.info("[vd_crm_lead 9.138] MIGRATION COMPLETED")
