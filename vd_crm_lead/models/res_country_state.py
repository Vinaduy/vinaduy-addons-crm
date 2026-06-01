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
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """Override để sort priority cho VN states khi domain match.
        Tăng limit để hiển thị tất cả 34 tỉnh inline (không 'Tìm kiếm thêm').
        """
        # Detect VN picker: qua context vd_province_picker (cách mới — field
        # KHÔNG còn đặt domain để tránh client tự xoá giá trị) HOẶC qua domain
        # clause vd_is_active_2025 (backward compat các view khác).
        is_vd_picker = bool(self.env.context.get('vd_province_picker'))
        if not is_vd_picker and domain:
            for clause in domain:
                if isinstance(clause, (list, tuple)) and len(clause) >= 1:
                    if clause[0] == 'vd_is_active_2025':
                        is_vd_picker = True
                        break
        if not is_vd_picker:
            return super()._name_search(name, domain=domain, operator=operator,
                                         limit=limit, order=order)
        # Đảm bảo lọc đúng 34 tỉnh sau cải cách (kể cả khi field không truyền domain).
        picker_domain = list(domain or [])
        existing = {c[0] for c in picker_domain
                    if isinstance(c, (list, tuple)) and len(c) >= 1}
        if 'vd_is_active_2025' not in existing:
            picker_domain.append(('vd_is_active_2025', '=', True))
        if 'country_id' not in existing:
            vn = self.env.ref('base.vn', raise_if_not_found=False)
            if vn:
                picker_domain.append(('country_id', '=', vn.id))
        # Bump limit để return tất cả 34
        all_ids = super()._name_search(
            name, domain=picker_domain, operator=operator,
            limit=100, order=order,
        )
        if not all_ids:
            return all_ids
        # Sort theo priority list rồi đến alphabetical
        states = self.browse(all_ids)
        priority_map = {n: i for i, n in enumerate(self._VD_PROVINCE_PRIORITY)}
        sorted_states = states.sorted(
            key=lambda s: (
                priority_map.get(s.name, len(self._VD_PROVINCE_PRIORITY)),
                s.name or '',
            )
        )
        return sorted_states.ids
