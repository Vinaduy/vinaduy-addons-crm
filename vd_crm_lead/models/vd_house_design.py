# -*- coding: utf-8 -*-
"""THƯ VIỆN - Mẫu nhà thiết kế.

Kho ảnh mẫu nhà cho NV copy/tải gửi khách qua Zalo. Tổ chức 2 cấp ALBUM ĐỘNG:
- category = NHÓM (vd: Mẫu 1 Tầng, Mẫu 2 Tầng, Biệt Thự, Trần gỗ...).
- style    = KIỂU / album con (vd: 1 TMB, 1 T Mái Thái, 2,5 TMB...).
Tab tự sinh từ chính dữ liệu (distinct category/style) nên thêm nhóm/kiểu mới
chỉ cần upload ảnh với category/style tương ứng, KHÔNG phải sửa code.

Phân quyền: MỌI nhân viên tải ảnh lên được; CHỈ ADMIN được xoá.
"""
from odoo import api, fields, models
from odoo.exceptions import AccessError

# Thứ tự ưu tiên hiển thị NHÓM (cái nào không có ở đây thì xếp sau, theo tên).
_CAT_ORDER = [
    'Mẫu 1 Tầng', 'Mẫu 2 Tầng', 'Mẫu 3 Tầng', 'Mẫu 4 Tầng',
    'Biệt Thự', 'Trần gỗ', 'Khác',
]


class VdHouseDesign(models.Model):
    _name = 'vd.house.design'
    _description = 'Thư viện mẫu nhà thiết kế'
    _order = 'sequence, id desc'

    name = fields.Char(string='Tên mẫu', default='Mẫu nhà')
    category = fields.Char(string='Nhóm', required=True, index=True)
    style = fields.Char(string='Kiểu', required=True, index=True)
    image = fields.Binary(string='Ảnh', attachment=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    def _vd_can_delete(self):
        """Chỉ ADMIN được xoá ảnh (user spec 2026-06-30)."""
        u = self.env.user
        return bool(u._is_admin() or u.has_group('base.group_system'))

    @api.model
    def vd_house_tabs(self):
        """Tab động: gom distinct (category, style) + đếm ảnh mỗi album."""
        self.env.cr.execute(
            "SELECT category, style, count(*) FROM vd_house_design "
            "WHERE category IS NOT NULL AND style IS NOT NULL "
            "GROUP BY category, style")
        bucket = {}
        for cat, sty, cnt in self.env.cr.fetchall():
            bucket.setdefault(cat, {})[sty] = cnt

        def cat_key(c):
            return (_CAT_ORDER.index(c) if c in _CAT_ORDER else len(_CAT_ORDER), c)

        cats = []
        for cat in sorted(bucket.keys(), key=cat_key):
            styles = [{'key': sk, 'label': sk, 'count': bucket[cat][sk]}
                      for sk in sorted(bucket[cat].keys())]
            cats.append({'key': cat, 'label': cat, 'styles': styles})
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
        category = (category or '').strip()
        style = (style or '').strip()
        if not category or not style:
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
