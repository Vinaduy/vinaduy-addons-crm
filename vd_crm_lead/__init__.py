from . import models
from . import wizard
from . import controllers


def _post_init_hook(env):
    """Khởi tạo sau cài / nâng cấp module:
    - Archive 4 stage CRM mặc định để pipeline chỉ còn 7 stage của VINADUY.
    - Populate huyện/quận/thị xã VN vào model vd.district.
    - Force recompute vd_intake_complete cho các lead hiện có (stored compute
      cần trigger để badge + auto-lock work).
    """
    Stage = env['crm.stage']
    standard_xml_ids = ['crm.stage_lead1', 'crm.stage_lead2', 'crm.stage_lead3', 'crm.stage_lead4']
    to_archive = Stage.browse()
    for xmlid in standard_xml_ids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            to_archive |= rec
    if to_archive:
        to_archive.write({'active': False})

    _populate_vn_districts(env)

    # Force recompute vd_intake_complete + lock các lead đã đủ thông tin.
    # User spec 2026-05-27: KHÔNG revert lead về 'new' nữa — data persist
    # mãi mãi; thay vào đó tự lock + đẩy về stage 'quote' để dashboard hiển
    # thị KH ở đúng bảng (THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ).
    try:
        Lead = env['crm.lead']
        Stage = env['crm.stage']
        quote_stage = Stage.search([('code', '=', 'quote')], limit=1)
        all_leads = Lead.search([])
        if all_leads:
            all_leads._compute_intake_complete()
            # Auto-lock + đẩy về 'quote' các lead đủ thông tin (chưa locked
            # hoặc đã bị revert về 'new' do post_init cũ).
            complete_leads = all_leads.filtered(lambda l: l.vd_intake_complete)
            for lead in complete_leads:
                vals = {}
                if not lead.vd_intake_locked:
                    vals['vd_intake_locked'] = True
                    vals['vd_intake_open'] = False
                if (quote_stage
                        and lead.stage_id.code in ('new', 'lead')
                        and lead.active):
                    vals['stage_id'] = quote_stage.id
                if vals:
                    lead.with_context(
                        vd_skip_auto_lock=True,
                        vd_skip_intake_lock=True,
                        mail_notrack=True,
                    ).write(vals)
    except Exception:
        pass  # không crash post-init nếu có vấn đề

    # Backfill vd_lost_user_id / vd_lost_is_auto cho KH đã huỷ trước v9.133
    # Heuristic:
    #   - reason starts với "Tự động:" → cron auto-trash → is_auto=True, user_id=False
    #   - else → manual → user_id = write_uid (suy luận)
    try:
        env.cr.execute("""
            UPDATE crm_lead
               SET vd_lost_is_auto = TRUE
             WHERE vd_lost_reason LIKE 'Tự động:%%'
               AND vd_lost_is_auto = FALSE
        """)
        env.cr.execute("""
            UPDATE crm_lead
               SET vd_lost_user_id = write_uid
             WHERE vd_lost_reason IS NOT NULL
               AND vd_lost_reason NOT LIKE 'Tự động:%%'
               AND vd_lost_user_id IS NULL
        """)
    except Exception:
        pass


def _populate_vn_districts(env):
    """Migrate VN administrative divisions to 2025 post-reform structure:
    - 34 cấp tỉnh (6 TP + 28 tỉnh) thay cho 63 cũ
    - Xã/Phường (~3.321) thay cho huyện cũ (~705)

    Source: data/vn_admin_2025.py
    Idempotent: chạy lại không tạo trùng + không re-migrate đã merge.
    """
    from .data.vn_admin_2025 import (
        VN_PROVINCES_2025, VN_PROVINCE_MERGE_MAP, VN_WARDS_2025,
    )
    State = env['res.country.state']
    District = env['vd.district'].sudo()
    vn_country = env.ref('base.vn', raise_if_not_found=False)
    if not vn_country:
        return

    # ============== STEP 0: Name aliases — chuẩn hoá tên cũ trong DB ==============
    # DB Odoo seed dùng "TP X", "Thừa Thiên - Huế" → chuẩn hoá theo tên mới.
    DB_NAME_ALIASES = {
        'TP Hồ Chí Minh': 'TP Hồ Chí Minh',
        'TP. Hồ Chí Minh': 'TP Hồ Chí Minh',
        'Hồ Chí Minh': 'TP Hồ Chí Minh',
        'TP Hải Phòng': 'Hải Phòng',
        'TP Đà Nẵng': 'Đà Nẵng',
        'TP Cần Thơ': 'Cần Thơ',
        'Thừa Thiên - Huế': 'Huế',
        'Thừa Thiên Huế': 'Huế',
        'Bà Rịa-Vũng Tàu': 'Bà Rịa - Vũng Tàu',
    }

    # ============== STEP 1: ENSURE 34 new provinces exist ==============
    all_states = State.search([('country_id', '=', vn_country.id)])
    by_name = {s.name.strip(): s for s in all_states}
    new_province_names = {p['name'] for p in VN_PROVINCES_2025}

    # Tạo các tỉnh mới chưa có trong DB (dùng alias để tránh tạo duplicate)
    for prov in VN_PROVINCES_2025:
        new_name = prov['name']
        if new_name in by_name:
            continue
        # Kiểm tra alias: vd "Đà Nẵng" mới → có "TP Đà Nẵng" cũ → đổi tên
        renamed = False
        for old_db_name, target in DB_NAME_ALIASES.items():
            if target == new_name and old_db_name in by_name:
                # Rename tỉnh cũ thành tên mới
                old_state = by_name[old_db_name]
                old_state.sudo().write({'name': new_name})
                by_name[new_name] = old_state
                del by_name[old_db_name]
                renamed = True
                break
        if not renamed:
            try:
                new_state = State.sudo().create({
                    'name': new_name,
                    'country_id': vn_country.id,
                    'code': 'V' + str(len(by_name) + 100)[-2:],
                })
                by_name[new_name] = new_state
            except Exception:
                pass

    # ============== STEP 2: Migrate lead FK old → new ==============
    Lead = env['crm.lead']
    Partner = env['res.partner']
    for old_name, new_name in VN_PROVINCE_MERGE_MAP.items():
        if old_name == new_name:
            continue  # giữ nguyên
        old_state = by_name.get(old_name)
        new_state = by_name.get(new_name)
        if not old_state or not new_state:
            continue
        if old_state.id == new_state.id:
            continue
        # Migrate crm.lead
        leads_to_migrate = Lead.search([
            ('vd_intake_province_id', '=', old_state.id),
        ])
        if leads_to_migrate:
            try:
                leads_to_migrate.with_context(
                    vd_skip_intake_lock=True, mail_notrack=True,
                ).write({'vd_intake_province_id': new_state.id})
            except Exception:
                pass
        # Migrate res.partner.state_id (nếu có)
        try:
            partners = Partner.search([('state_id', '=', old_state.id)])
            if partners:
                partners.sudo().with_context(mail_notrack=True).write(
                    {'state_id': new_state.id}
                )
        except Exception:
            pass
        # Rename old state để NV biết là tỉnh cũ (không xoá để giữ FK history khác)
        try:
            old_state.sudo().write({'name': old_name + ' (cũ - đã sáp nhập)'})
        except Exception:
            pass

    # ============== STEP 2b: Mark 34 new provinces vd_is_active_2025=True ==============
    # Picker domain filter: chỉ show các state có flag này → NV chỉ thấy 34 mới.
    for name in new_province_names:
        state = by_name.get(name)
        if state and not state.vd_is_active_2025:
            try:
                state.sudo().write({'vd_is_active_2025': True})
            except Exception:
                pass

    # ============== STEP 3: Reload ward data ==============
    # Strategy: chỉ create wards mới chưa có, KHÔNG xoá cái cũ (tránh
    # vỡ FK của lead đang dùng). Sau này admin có thể xoá thủ công.
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
