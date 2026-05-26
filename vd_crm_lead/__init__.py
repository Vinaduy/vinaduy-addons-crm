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

    # Force recompute vd_intake_complete for all leads — và auto-lock các lead
    # đã đủ thông tin nhưng chưa lock (data tồn tại trước v9.106).
    try:
        Lead = env['crm.lead']
        all_leads = Lead.search([])
        if all_leads:
            all_leads._compute_intake_complete()
            to_lock = all_leads.filtered(lambda l: l.vd_intake_complete and not l.vd_intake_locked)
            if to_lock:
                to_lock.with_context(vd_skip_auto_lock=True).write({
                    'vd_intake_locked': True,
                    'vd_intake_open': False,
                })
    except Exception:
        pass  # không crash post-init nếu có vấn đề


def _populate_vn_districts(env):
    """Tạo các bản ghi vd.district từ data/vn_districts.py.
    Idempotent: bỏ qua nếu (state_id, name) đã tồn tại."""
    from .data.vn_districts import VN_DISTRICTS

    State = env['res.country.state']
    District = env['vd.district'].sudo()
    vn_country = env.ref('base.vn', raise_if_not_found=False)
    if not vn_country:
        return

    states = State.search([('country_id', '=', vn_country.id)])
    by_name = {s.name: s for s in states}

    to_create = []
    seen = set()  # (state_id, name) — chống trùng cả với data sẵn có lẫn nội bộ
    for province_name, districts in VN_DISTRICTS.items():
        state = by_name.get(province_name)
        if not state:
            continue
        existing = set(District.search([('state_id', '=', state.id)]).mapped('name'))
        for name in districts:
            key = (state.id, name)
            if name in existing or key in seen:
                continue
            seen.add(key)
            to_create.append({'name': name, 'state_id': state.id})

    if to_create:
        District.create(to_create)
