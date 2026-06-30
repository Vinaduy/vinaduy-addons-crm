# -*- coding: utf-8 -*-
"""THƯ VIỆN - Mẫu nhà thiết kế.

Kho ảnh mẫu nhà cho NV copy/tải gửi khách qua Zalo. Phân theo:
- Nhóm (category): Nhà cấp 4 / 2 tầng / 3 tầng / 4 tầng.
- Kiểu (style) — tab con khác nhau tùy nhóm:
    cấp 4, 2 tầng : Vuông hiện đại, Mái Nhật, Mái Thái
    3 tầng, 4 tầng: Vuông hiện đại, Mái Pháp, Tân cổ điển
Mỗi (nhóm, kiểu) = 1 album, chứa nhiều ảnh. Admin/quản lý tải ảnh hàng loạt;
NV xem, bấm copy 1 ảnh (dán Zalo) hoặc tải nhiều ảnh đã chọn.
"""
from odoo import api, fields, models
from odoo.exceptions import AccessError

CATEGORIES = [
    ('cap4', 'Nhà cấp 4'),
    ('tang2', 'Nhà 2 tầng'),
    ('tang3', 'Nhà 3 tầng'),
    ('tang4', 'Nhà 4 tầng'),
]
STYLES = [
    ('vuong_hiendai', 'Vuông hiện đại'),
    ('mai_nhat', 'Mái Nhật'),
    ('mai_thai', 'Mái Thái'),
    ('mai_phap', 'Mái Pháp'),
    ('tan_co_dien', 'Tân cổ điển'),
]
# Tab con (kiểu) theo từng nhóm.
CAT_STYLES = {
    'cap4': ['vuong_hiendai', 'mai_nhat', 'mai_thai'],
    'tang2': ['vuong_hiendai', 'mai_nhat', 'mai_thai'],
    'tang3': ['vuong_hiendai', 'mai_phap', 'tan_co_dien'],
    'tang4': ['vuong_hiendai', 'mai_phap', 'tan_co_dien'],
}


class VdHouseDesign(models.Model):
    _name = 'vd.house.design'
    _description = 'Thư viện mẫu nhà thiết kế'
    _order = 'sequence, id desc'

    name = fields.Char(string='Tên mẫu', default='Mẫu nhà')
    category = fields.Selection(CATEGORIES, string='Nhóm', required=True, index=True)
    style = fields.Selection(STYLES, string='Kiểu', required=True, index=True)
    image = fields.Binary(string='Ảnh', attachment=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _vd_can_delete(self):
        """Chỉ ADMIN được xoá ảnh (user spec 2026-06-30)."""
        u = self.env.user
        return bool(u._is_admin() or u.has_group('base.group_system'))

    @api.model
    def vd_house_tabs(self):
        """Cấu trúc tab: nhóm + kiểu (tab con) + số ảnh mỗi album."""
        Sl = dict(STYLES)
        cats = []
        for ck, cl in CATEGORIES:
            styles = []
            for sk in CAT_STYLES.get(ck, []):
                styles.append({
                    'key': sk, 'label': Sl.get(sk, sk),
                    'count': self.sudo().search_count(
                        [('category', '=', ck), ('style', '=', sk)]),
                })
            cats.append({'key': ck, 'label': cl, 'styles': styles})
        # can_delete: chỉ admin. Tải ảnh lên thì MỌI NV đều được.
        return {'can_delete': self._vd_can_delete(), 'categories': cats}

    @api.model
    def vd_house_list(self, category, style):
        """Danh sách ảnh 1 album (chỉ id+tên; ảnh load qua /web/image)."""
        recs = self.sudo().search(
            [('category', '=', category), ('style', '=', style)])
        return [{'id': r.id, 'name': r.name or ''} for r in recs]

    @api.model
    def vd_house_upload(self, category, style, files):
        """Tải ảnh hàng loạt lên 1 album. files=[{name, data(base64)}].
        MỌI nhân viên (internal user) đều được tải lên (user spec 2026-06-30)."""
        if category not in dict(CATEGORIES) or style not in dict(STYLES):
            return 0
        n = 0
        for f in (files or []):
            data = (f or {}).get('data')
            if not data:
                continue
            self.sudo().create({
                'category': category, 'style': style,
                'name': (f.get('name') or 'Mẫu nhà')[:120],
                'image': data,
            })
            n += 1
        return n

    @api.model
    def vd_house_delete(self, ids):
        """Xoá ảnh đã chọn — CHỈ ADMIN (user spec 2026-06-30)."""
        if not self._vd_can_delete():
            raise AccessError('Chỉ admin mới được xoá ảnh.')
        self.sudo().browse([int(i) for i in (ids or [])]).unlink()
        return True
