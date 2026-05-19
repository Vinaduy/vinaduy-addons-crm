"""Resurrect 2 client action ids đã bị xoá ở 9.12.0/9.12.1.

Context: gộp 2 menu KH/NV thành 1 menu → xoá action_vd_crm_dashboard_customers
(id 585) + action_vd_crm_dashboard_employees (id 586). User có tabs/bookmarks
trỏ /odoo/action-585 hoặc /odoo/action-586 sẽ thấy "Tác vụ X không tồn tại"
khi reload. Migration này tạo lại 2 row trỏ tag 'vd_crm_lead.dashboard',
rồi UPDATE id về 585/586 chính xác để URL cũ vẫn mở được dashboard mới.

Dùng ORM để Odoo tự fill các NOT NULL columns (binding_type, etc.) thay vì
raw SQL INSERT (đã từng fail vì binding_type NOT NULL).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

TARGET_IDS = (585, 586)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Action = env['ir.actions.client']

    for target_id in TARGET_IDS:
        cr.execute("SAVEPOINT resurrect_%s" % target_id)
        try:
            # Check id đã tồn tại chưa
            cr.execute("SELECT id FROM ir_actions WHERE id = %s", (target_id,))
            if cr.fetchone():
                _logger.info(
                    "[vd_crm_lead] Action id=%s đã tồn tại, skip", target_id
                )
                cr.execute("RELEASE SAVEPOINT resurrect_%s" % target_id)
                continue

            # Tạo action mới qua ORM (auto-fill binding_type, các NOT NULL cols)
            new_action = Action.create({
                'name': 'Dashboard NV (legacy)',
                'tag': 'vd_crm_lead.dashboard',
            })
            new_id = new_action.id

            # UPDATE id về target để URL cũ /odoo/action-585/586 hoạt động
            # ir_actions là parent table (qua _inherits), ir_act_client là child
            cr.execute(
                "UPDATE ir_actions SET id = %s WHERE id = %s",
                (target_id, new_id),
            )
            cr.execute(
                "UPDATE ir_act_client SET id = %s WHERE id = %s",
                (target_id, new_id),
            )
            cr.execute("RELEASE SAVEPOINT resurrect_%s" % target_id)
            _logger.info(
                "[vd_crm_lead] Resurrected action id=%s (was %s) → dashboard",
                target_id, new_id,
            )
        except Exception as e:
            cr.execute("ROLLBACK TO SAVEPOINT resurrect_%s" % target_id)
            _logger.warning(
                "[vd_crm_lead] Không resurrect được action %s: %s",
                target_id, e,
            )

    # Bump sequence để auto-increment tiếp theo không trùng id đã insert thủ công
    try:
        cr.execute("""
            SELECT setval('ir_actions_id_seq', GREATEST(
                COALESCE((SELECT last_value FROM ir_actions_id_seq), 1),
                (SELECT COALESCE(MAX(id), 1) FROM ir_actions)
            ))
        """)
    except Exception as e:
        _logger.warning("[vd_crm_lead] Bump ir_actions_id_seq fail: %s", e)
