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
