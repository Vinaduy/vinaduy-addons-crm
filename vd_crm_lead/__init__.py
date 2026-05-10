from . import models
from . import wizard


def _post_init_hook(env):
    """Khởi tạo sau cài / nâng cấp module:
    - Archive 4 stage CRM mặc định để pipeline chỉ còn 7 stage của VINADUY.
    - Populate huyện/quận/thị xã VN vào model vd.district.
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
