from odoo import api, fields, models


class ResCountryState(models.Model):
    """Mở rộng res.country.state để đánh dấu 34 tỉnh mới sau cải cách
    01/07/2025. Picker chỉ hiển thị các state có vd_is_active_2025=True
    → NV không chọn nhầm tỉnh cũ đã sáp nhập.

    name_search override: sort ưu tiên 6 TP trực thuộc TW + tỉnh lớn lên đầu,
    return tất cả 34 (limit cao) → không cần "Tìm kiếm thêm".
    """
    _inherit = 'res.country.state'

    vd_is_active_2025 = fields.Boolean(
        string='Tỉnh sau cải cách 2025',
        default=False, index=True,
        help='True = 1 trong 34 tỉnh/TP sau cải cách 01/07/2025. '
             'Set bởi _populate_vn_districts() trong post_init.',
    )

    # Priority list: 6 TP trực thuộc TW + tỉnh lớn lên top (user spec 2026-05-27)
    _VD_PROVINCE_PRIORITY = [
        # 6 TP trực thuộc TW
        'Hà Nội', 'TP Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ', 'Huế',
        # Tỉnh lớn / công nghiệp mạnh
        'Quảng Ninh', 'Bắc Ninh', 'Hưng Yên', 'Ninh Bình', 'Đồng Nai',
        'Khánh Hòa', 'Lâm Đồng', 'Phú Thọ', 'Thanh Hóa', 'Nghệ An',
    ]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Lọc danh sách Tỉnh cho picker khai thác QUA name_search (Odoo 18).

        QUAN TRỌNG: KHÔNG lọc bằng `domain` trên field nữa — domain tham chiếu
        vd_is_active_2025 (field của bản ghi liên kết) khiến Odoo 18 client TỰ
        XOÁ giá trị Tỉnh khi onchange (đã xác nhận qua log). Thay vào đó, view
        truyền context {'vd_province_picker': 1}; ở đây ta chèn domain lọc 34
        tỉnh server-side → dropdown vẫn đúng, field không có domain nên client
        không xoá. (fix mất tỉnh 2026-06-01)
        """
        if self.env.context.get('vd_province_picker'):
            args = list(args or [])
            keys = {a[0] for a in args
                    if isinstance(a, (list, tuple)) and len(a) >= 1}
            if 'vd_is_active_2025' not in keys:
                args.append(('vd_is_active_2025', '=', True))
            if 'country_id' not in keys:
                vn = self.env.ref('base.vn', raise_if_not_found=False)
                if vn:
                    args.append(('country_id', '=', vn.id))
            limit = max(limit or 0, 100)  # trả hết 34 tỉnh, không "Tìm thêm"
            res = super().name_search(name, args, operator=operator, limit=limit)
            # Sort ưu tiên: 6 TP trực thuộc TW + tỉnh lớn lên đầu
            prio = self._VD_PROVINCE_PRIORITY

            def _key(t):
                dn = t[1] or ''
                for i, p in enumerate(prio):
                    if dn.startswith(p):
                        return (i, dn)
                return (len(prio), dn)
            return sorted(res, key=_key)
        return super().name_search(name, args, operator=operator, limit=limit)
