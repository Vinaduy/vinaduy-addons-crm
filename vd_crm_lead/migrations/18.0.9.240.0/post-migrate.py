# -*- coding: utf-8 -*-
"""User spec 2026-06-19: NV / Trưởng nhóm / Giám đốc đăng nhập xong vào THẲNG
module CRM (set home action = Dashboard CRM). Admin giữ home mặc định.

Việc khoá các app khác (Discuss/Calendar/Contacts/Stringee/Website/Employees/
Apps/Dashboards) về chỉ-admin làm qua data/menu_overrides.xml (groups_id), tự
áp khi upgrade — migration này chỉ lo set action_id cho user CŨ.
"""
import logging

_logger = logging.getLogger(__name__)


# Các app root KHÓA về chỉ-admin (NV/TN/GĐ chỉ còn CRM). Không gồm CRM.
_LOCK_ROOT_MENUS = [
    'mail.menu_root_discuss',
    'calendar.mail_menu_calendar',
    'contacts.menu_contacts',
    'spreadsheet_dashboard.spreadsheet_dashboard_menu_root',
    'vd_stringee.menu_stringee_root',
    'website.menu_website_configuration',
    'hr.menu_hr_root',
    'base.menu_management',
]


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    # ===== Khoá các app root khác về chỉ ADMIN =====
    admin = env.ref('base.group_system', raise_if_not_found=False)
    if admin:
        locked = []
        for xid in _LOCK_ROOT_MENUS:
            m = env.ref(xid, raise_if_not_found=False)
            if m:
                m.sudo().groups_id = [(6, 0, [admin.id])]
                locked.append(xid)
        _logger.info('vd 240: khoa %s app root ve chi-admin: %s', len(locked), locked)

    dash = env.ref('vd_crm_lead.action_vd_crm_dashboard', raise_if_not_found=False)
    admin_grp = env.ref('base.group_system', raise_if_not_found=False)
    internal = env.ref('base.group_user', raise_if_not_found=False)
    if not (dash and internal):
        _logger.warning('vd 240: thiếu dashboard action / group_user, bỏ qua')
        return

    # User nội bộ (internal), KHÔNG phải admin (group_system) → set home = CRM.
    users = env['res.users'].sudo().search([
        ('share', '=', False),
        ('active', '=', True),
        ('groups_id', 'in', internal.id),
    ])
    n = 0
    for u in users:
        if admin_grp and admin_grp in u.groups_id:
            continue  # admin giữ home mặc định
        if u.action_id.id != dash.id:
            u.action_id = dash.id
            n += 1
    _logger.info('vd 240: set home action CRM cho %s user (NV/TN/GĐ)', n)
