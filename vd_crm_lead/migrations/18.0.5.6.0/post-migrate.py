"""Đơn giản hóa pipeline: 7 stages → 4 stages hiện trên dashboard.
- Move leads từ 'potential' / 'callback' → 'new' (gộp vào Khách mới)
- Stages potential/callback vẫn còn trong DB nhưng dashboard JS filter ra.
- Stage 'lost' giữ nguyên (is_lost=True) nhưng cũng không hiện dashboard.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT name, res_id FROM ir_model_data
        WHERE module = 'vd_crm_lead'
          AND model = 'crm.stage'
          AND name IN ('stage_new', 'stage_potential', 'stage_callback')
    """)
    stages = dict(cr.fetchall())
    new_id = stages.get('stage_new')
    potential_id = stages.get('stage_potential')
    callback_id = stages.get('stage_callback')

    if new_id and potential_id:
        cr.execute("UPDATE crm_lead SET stage_id = %s WHERE stage_id = %s",
                   (new_id, potential_id))
    if new_id and callback_id:
        cr.execute("UPDATE crm_lead SET stage_id = %s WHERE stage_id = %s",
                   (new_id, callback_id))
    # Note: crm.stage không có cột 'active' → không archive được. Filter ở
    # dashboard model thay thế (xem dashboard_data trong crm_lead.py).
