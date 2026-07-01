# -*- coding: utf-8 -*-
"""CẤU HÌNH TIỀN THƯỞNG (admin treo thưởng tạo động lực cho NV).

- THƯỞNG CÁ NHÂN (vd.bonus.personal): mốc theo SỐ HỢP ĐỒNG (HĐ thứ 1/2/3...).
  MỌI nhân viên đều thấy trên trang cá nhân.
- THƯỞNG PHÒNG (vd.bonus.team): mốc theo PHÒNG BAN (tiền / số HĐ / số người).
  NV chỉ thấy mốc thưởng của PHÒNG mình. Phòng nào không cấu hình = không có thưởng.

Admin cấu hình trong menu "Cấu hình tiền thưởng"; có thể tạo nhiều mốc + nhiều phòng.
"""
from odoo import api, fields, models

from .res_users import _VD_TEAM_SELECTION


def _vnd(env):
    return (env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1)
            or env.company.currency_id)


class VdBonusPersonal(models.Model):
    _name = 'vd.bonus.personal'
    _description = 'Mốc thưởng cá nhân (theo số hợp đồng)'
    _order = 'contract_no, sequence, id'

    name = fields.Char(string='Tên mốc', required=True,
                       help='VD: Hợp đồng thứ nhất')
    contract_no = fields.Integer(string='Hợp đồng thứ', required=True, default=1,
                                 help='Áp dụng cho hợp đồng thứ mấy trong tháng.')
    amount = fields.Monetary(string='Tiền thưởng', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: _vnd(s.env))
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class VdBonusTeam(models.Model):
    _name = 'vd.bonus.team'
    _description = 'Mốc thưởng phòng (theo phòng ban)'
    _order = 'team, sequence, id'

    name = fields.Char(string='Tên mốc',
                       help='VD: Thưởng đội tháng 7. Bỏ trống cũng được.')
    team = fields.Selection(_VD_TEAM_SELECTION, string='Phòng ban', required=True, index=True)
    amount = fields.Monetary(string='Tiền thưởng', currency_field='currency_id')
    contract_count = fields.Integer(string='Số hợp đồng', default=1)
    people_count = fields.Integer(string='Số người', default=1)
    currency_id = fields.Many2one('res.currency', default=lambda s: _vnd(s.env))
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # ============ DỮ LIỆU CHO TRANG CÁ NHÂN ============
    @api.model
    def vd_bonus_board(self, user_id=None):
        """Trả mốc thưởng để hiện trên trang cá nhân.
        - personal: TẤT CẢ mốc thưởng cá nhân (ai cũng thấy).
        - team: chỉ mốc thưởng của PHÒNG người dùng đang xem.
        """
        env = self.env
        user = env['res.users'].sudo().browse(int(user_id)) if user_id else env.user
        team_key = user.vd_team_label or user.vd_team or ''
        Personal = env['vd.bonus.personal'].sudo()
        personal = [{
            'name': r.name or ('Hợp đồng thứ %s' % r.contract_no),
            'contract_no': r.contract_no,
            'amount': r.amount,
        } for r in Personal.search([('amount', '>', 0)])]
        team_ms = []
        if team_key:
            for r in self.sudo().search([('team', '=', team_key)]):
                team_ms.append({
                    'name': r.name or '',
                    'amount': r.amount,
                    'contract_count': r.contract_count,
                    'people_count': r.people_count,
                })
        return {'personal': personal, 'team': team_ms, 'team_label': team_key}
