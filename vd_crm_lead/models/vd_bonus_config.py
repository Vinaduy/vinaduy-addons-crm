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
    _order = 'team, contract_no, sequence, id'

    name = fields.Char(string='Tên mốc', required=True,
                       help='VD: Hợp đồng thứ nhất')
    # Phòng ban áp dụng: TRỐNG = áp dụng CHUNG cho mọi phòng chưa có cấu hình
    # riêng; có chọn = chế độ thưởng RIÊNG cho phòng đó (vd CTV khác NV thường).
    team = fields.Selection(_VD_TEAM_SELECTION, string='Phòng ban', index=True,
                            help='Trống = áp dụng chung; chọn phòng = chế độ riêng '
                                 'cho phòng đó (đè chế độ chung).')
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
        - personal: mốc thưởng cá nhân của PHÒNG người dùng (nếu phòng có cấu
          hình riêng); nếu không thì lấy mốc CHUNG (team trống).
        - team: chỉ mốc thưởng của PHÒNG người dùng đang xem.
        """
        env = self.env
        user = env['res.users'].sudo().browse(int(user_id)) if user_id else env.user
        team_key = user.vd_team_label or user.vd_team or ''
        Personal = env['vd.bonus.personal'].sudo()
        # Ưu tiên chế độ RIÊNG của phòng; không có thì dùng chế độ CHUNG (team trống).
        own = Personal.search([('team', '=', team_key), ('amount', '>', 0)]) if team_key else Personal.browse()
        recs = own if own else Personal.search([('team', '=', False), ('amount', '>', 0)])
        personal = [{
            'name': r.name or ('Hợp đồng thứ %s' % r.contract_no),
            'contract_no': r.contract_no,
            'amount': r.amount,
        } for r in recs]
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

    # ============ DỮ LIỆU CHO BOARD CẤU HÌNH (admin) ============
    @api.model
    def vd_bonus_config_data(self):
        """Gom toàn bộ mốc thưởng theo PHÒNG BAN cho board thẻ (admin).
        Trả: {teams:[{key,label,personal:[...],team:[...]}], common_personal:[...]}.
        common_personal = mốc cá nhân CHUNG (team trống, áp mọi phòng chưa có riêng).
        """
        env = self.env
        Personal = env['vd.bonus.personal'].sudo()
        Team = self.sudo()

        def _p(r):
            return {'id': r.id, 'name': r.name or '', 'contract_no': r.contract_no,
                    'amount': r.amount, 'active': r.active}

        def _t(r):
            return {'id': r.id, 'name': r.name or '', 'amount': r.amount,
                    'contract_count': r.contract_count,
                    'people_count': r.people_count, 'active': r.active}

        teams = []
        for key, label in _VD_TEAM_SELECTION:
            teams.append({
                'key': key, 'label': label,
                'personal': [_p(r) for r in Personal.search([('team', '=', key)])],
                'team': [_t(r) for r in Team.search([('team', '=', key)])],
            })
        common = [_p(r) for r in Personal.search([('team', '=', False)])]
        return {'teams': teams, 'common_personal': common}

    @api.model
    def vd_bonus_save(self, model, vals, rec_id=None):
        """Tạo/sửa 1 mốc thưởng từ board. model ∈ personal|team. Trả id."""
        target = self.env[
            'vd.bonus.personal' if model == 'personal' else 'vd.bonus.team'].sudo()
        clean = {k: v for k, v in (vals or {}).items() if k in (
            'name', 'team', 'contract_no', 'amount', 'contract_count',
            'people_count', 'active')}
        if rec_id:
            rec = target.browse(int(rec_id))
            rec.write(clean)
            return rec.id
        if model == 'personal' and not clean.get('name'):
            clean['name'] = 'Hợp đồng thứ %s' % (clean.get('contract_no') or 1)
        return target.create(clean).id

    @api.model
    def vd_bonus_delete(self, model, rec_id):
        """Xoá 1 mốc thưởng từ board."""
        target = self.env[
            'vd.bonus.personal' if model == 'personal' else 'vd.bonus.team'].sudo()
        target.browse(int(rec_id)).unlink()
        return True
