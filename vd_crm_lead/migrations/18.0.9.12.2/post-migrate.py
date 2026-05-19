"""Resurrect 2 client action ids đã bị xoá ở 9.12.0/9.12.1.

Context: gộp 2 menu KH/NV thành 1 menu → xoá action_vd_crm_dashboard_customers
(id 585) + action_vd_crm_dashboard_employees (id 586). User có tabs/bookmarks
trỏ /odoo/action-585 hoặc /odoo/action-586 sẽ thấy "Tác vụ X không tồn tại"
khi reload. Migration này tạo lại 2 row với CHÍNH XÁC id 585+586, trỏ tới
tag 'vd_crm_lead.dashboard' → URL cũ vẫn mở được dashboard mới.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    for action_id in (585, 586):
        cr.execute("SELECT id FROM ir_actions WHERE id = %s", (action_id,))
        if cr.fetchone():
            _logger.info("[vd_crm_lead] Action id=%s đã tồn tại, skip resurrect", action_id)
            continue
        try:
            cr.execute("""
                INSERT INTO ir_actions
                    (id, type, name, create_uid, create_date, write_uid, write_date)
                VALUES
                    (%s, 'ir.actions.client', 'Dashboard NV (legacy)', 1, NOW(), 1, NOW())
            """, (action_id,))
            cr.execute("""
                INSERT INTO ir_act_client (id, tag)
                VALUES (%s, 'vd_crm_lead.dashboard')
            """, (action_id,))
            _logger.info("[vd_crm_lead] Resurrected ir.actions.client id=%s → dashboard", action_id)
        except Exception as e:
            _logger.warning("[vd_crm_lead] Không resurrect được action %s: %s", action_id, e)

    # Bump sequence để auto-increment tiếp theo không trùng 585/586
    try:
        cr.execute("""
            SELECT setval('ir_actions_id_seq', GREATEST(
                COALESCE((SELECT last_value FROM ir_actions_id_seq), 1),
                (SELECT COALESCE(MAX(id), 1) FROM ir_actions)
            ))
        """)
    except Exception as e:
        _logger.warning("[vd_crm_lead] Bump ir_actions_id_seq fail: %s", e)
