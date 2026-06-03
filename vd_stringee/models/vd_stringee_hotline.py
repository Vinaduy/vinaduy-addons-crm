"""Pool số tổng đài Stringee — admin quản lý, assign cho từng NV.

Mỗi NV chỉ dùng 1 hotline (res.users.stringee_from_number_id).
Khi NV gọi ra:
- Ưu tiên dùng số hotline assign cho NV
- Fallback global config 'vd_stringee.from_number' nếu NV chưa assign

Đặt model trong vd_stringee để không phụ thuộc vd_crm_lead.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

# Thứ tự + label cột nhà mạng hiển thị trên bảng kéo-thả.
_CARRIER_ORDER = [
    ('viettel', 'Viettel'),
    ('mobi', 'MobiFone'),
    ('vina', 'Vinaphone'),
    ('vietnamobile', 'Vietnamobile'),
    ('itelecom', 'iTel'),
    ('gmobile', 'Gmobile'),
    ('other', 'Khác'),
]


def _digits_only(s):
    return ''.join(c for c in (s or '') if c.isdigit())


# Map đầu số (prefix 2 chữ số national, đã bỏ 0/84) → nhà mạng.
# Nguồn: quy hoạch số di động VN sau chuyển đổi 11→10 số.
_CARRIER_PREFIX = {
    'viettel': {'96', '97', '98', '86', '32', '33', '34', '35', '36', '37', '38', '39'},
    'vina':    {'91', '94', '88', '81', '82', '83', '84', '85'},
    'mobi':    {'90', '93', '89', '70', '76', '77', '78', '79'},
    'vietnamobile': {'92', '52', '56', '58'},
    'gmobile': {'99', '59'},
    'itelecom': {'87'},
}


def vd_carrier_from_number(number):
    """Suy nhà mạng từ số điện thoại theo đầu số. Trả carrier code hoặc 'other'.
    Chuẩn hoá: bỏ ký tự lạ, bỏ '84'/'0' đầu để lấy prefix national 2 chữ số."""
    d = _digits_only(number)
    if not d:
        return 'other'
    if d.startswith('84'):
        nat = d[2:]
    elif d.startswith('0'):
        nat = d[1:]
    else:
        nat = d
    pref = nat[:2]
    for carrier, prefixes in _CARRIER_PREFIX.items():
        if pref in prefixes:
            return carrier
    return 'other'


class VdStringeeHotline(models.Model):
    _name = 'vd.stringee.hotline'
    _description = 'Số tổng đài Stringee'
    _order = 'team_label, carrier, name'

    name = fields.Char(
        string='Tên gọi', required=True,
        help='Label nội bộ. Vd: "HCM1 - Viettel hotline".',
    )
    number = fields.Char(
        string='Số tổng đài', required=True,
        help='Số phone đã mua trên Stringee (format E.164, vd: 84917690625).',
    )
    carrier = fields.Selection([
        ('viettel', 'Viettel'),
        ('mobi', 'MobiFone'),
        ('vina', 'Vinaphone'),
        ('vietnamobile', 'Vietnamobile'),
        ('gmobile', 'Gmobile'),
        ('itelecom', 'iTel'),
        ('other', 'Khác'),
    ], required=True, default='viettel', string='Nhà mạng')
    team_label = fields.Char(
        string='Team',
        help='HCM1/HCM2/HN/QN... — chỉ để admin filter, không ràng buộc logic.',
    )
    note = fields.Text(string='Ghi chú nội bộ')
    active = fields.Boolean(default=True)

    # Legacy: số đơn cũ (1 NV = 1 số). Giữ để tương thích + migration.
    user_ids = fields.One2many(
        'res.users', 'stringee_from_number_id', string='NV (số đơn cũ)',
    )
    # Gán theo mạng (mới): 1 NV có nhiều số (mỗi mạng 1), 1 số dùng chung nhiều NV.
    assigned_user_ids = fields.Many2many(
        'res.users', 'vd_stringee_hotline_user_rel', 'hotline_id', 'user_id',
        string='NV được gán',
    )
    user_count = fields.Integer(
        string='Số NV dùng', compute='_compute_user_count',
    )
    assigned_user_names = fields.Char(
        string='NV đã gán', compute='_compute_assigned_user_names',
        help='Danh sách NV đang dùng số này (1 số có thể gán cho nhiều NV).',
    )

    @api.depends('assigned_user_ids', 'assigned_user_ids.name')
    def _compute_assigned_user_names(self):
        for rec in self:
            rec.assigned_user_names = ', '.join(
                rec.assigned_user_ids.sorted('name').mapped('name')
            ) or '—'

    _sql_constraints = [
        ('number_unique', 'unique(number)',
         'Số tổng đài này đã được tạo trước đó — kiểm tra lại danh sách.'),
    ]

    @api.depends('assigned_user_ids')
    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.assigned_user_ids)

    @api.constrains('number')
    def _check_number_e164(self):
        for rec in self:
            digits = _digits_only(rec.number)
            if len(digits) < 9:
                raise ValidationError(_(
                    'Số tổng đài "%s" không hợp lệ — cần ít nhất 9 chữ số.'
                ) % rec.number)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number'):
                # Normalize: chỉ giữ chữ số
                vals['number'] = _digits_only(vals['number'])
                # Auto phân loại nhà mạng theo đầu số (user spec 2026-06-01):
                # admin không cần tự chọn — đầu số là nguồn chuẩn.
                vals['carrier'] = vd_carrier_from_number(vals['number'])
        return super().create(vals_list)

    def write(self, vals):
        if 'number' in vals and vals['number']:
            vals['number'] = _digits_only(vals['number'])
            # Số đổi → tự cập nhật lại nhà mạng theo đầu số mới.
            vals['carrier'] = vd_carrier_from_number(vals['number'])
        return super().write(vals)

    # ===================== BẢNG KÉO-THẢ (OWL client action) =====================
    def _check_board_access(self):
        """Chỉ admin / quản lý sale được thao tác bảng phân số."""
        if not (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('sales_team.group_sale_manager')):
            raise AccessError(_('Bạn không có quyền phân bổ số tổng đài.'))

    @api.model
    def _board_call_stats(self, numbers):
        """Thống kê gọi theo (số tổng đài, NV): tổng giây + số cuộc + lần gọi ĐẦU.
        Dùng cho popover hover. Bọc try/except để lỗi thống kê không làm sập bảng."""
        stats = {}
        if not numbers:
            return stats
        try:
            groups = self.env['stringee.call'].read_group(
                [('caller_number', 'in', list(numbers)), ('user_id', '!=', False)],
                ['duration:sum', 'create_date:min'],
                ['caller_number', 'user_id'],
                lazy=False,
            )
            for g in groups:
                uid = g['user_id'][0] if g.get('user_id') else False
                stats[(g['caller_number'], uid)] = {
                    'seconds': g.get('duration') or 0,
                    'count': g.get('__count') or 0,
                    'first': g.get('create_date'),
                }
        except Exception:
            return {}
        return stats

    @api.model
    def get_assignment_board(self):
        """Dữ liệu cho bảng kéo-thả: kho số gom theo mạng + danh sách NV kèm số đã gán.
        Mỗi số kèm 'detail' = NV nào / dùng từ bao giờ / tổng phút gọi / số cuộc."""
        self._check_board_access()
        hotlines = self.search([('active', '=', True)])
        all_numbers = hotlines.mapped('number')
        stats = self._board_call_stats(all_numbers)
        num_stats = self.env['stringee.call']._vd_numbers_stats(all_numbers)
        today = fields.Date.context_today(self)

        def _detail(h):
            rows = []
            for u in h.assigned_user_ids.sorted('name'):
                st = stats.get((h.number, u.id)) or {}
                secs = st.get('seconds') or 0
                first = st.get('first')
                first_date = None
                if first:
                    first_date = (first.date() if hasattr(first, 'date')
                                  else fields.Datetime.to_datetime(first).date())
                rows.append({
                    'user': u.name,
                    'minutes': int(round(secs / 60.0)),
                    'count': st.get('count') or 0,
                    'first': first_date.strftime('%d/%m/%Y') if first_date else '',
                    'days': (today - first_date).days if first_date else None,
                })
            return rows

        def _fmt_hm(secs):
            secs = int(secs or 0)
            h = secs // 3600
            m = (secs % 3600) // 60
            if h:
                return f'{h}h{m:02d}'
            return f'{m} phút'

        by_carrier = {}
        for h in hotlines:
            ns = num_stats.get(h.number) or {}
            by_carrier.setdefault(h.carrier, []).append({
                'id': h.id,
                'number': h.number,
                'name': h.name or '',
                'user_count': len(h.assigned_user_ids),
                'detail': _detail(h),
                # --- Thống kê + sức khoẻ số (cho chip màu + bảng hover) ---
                'health': ns.get('health') or 'unused',
                'total_calls': ns.get('total') or 0,
                'reached': ns.get('reached') or 0,
                'talk_hm': _fmt_hm(ns.get('secs')),
                'first': ns.get('first') or '',
                'last': ns.get('last') or '',
                'active_days': ns.get('active_days') or 0,
                'per_day': ns.get('per_day') or 0,
            })
        carriers = []
        for code, label in _CARRIER_ORDER:
            nums = by_carrier.get(code)
            if nums:
                carriers.append({
                    'code': code,
                    'label': label,
                    'numbers': sorted(nums, key=lambda x: x['number']),
                })

        users = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)], order='name')
        user_list = []
        for u in users:
            assigned = [
                {'id': h.id, 'number': h.number, 'carrier': h.carrier,
                 'health': (num_stats.get(h.number) or {}).get('health') or 'unused'}
                for h in u.stringee_hotline_ids if h.active
            ]
            assigned.sort(key=lambda x: x['carrier'])
            user_list.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'hotlines': assigned,
                'no_share': bool(u.vd_no_number_share),
            })
        return {'carriers': carriers, 'users': user_list}

    @api.model
    def toggle_user_no_share(self, user_id, value):
        """Bật/tắt cờ 'không tham gia chia số' cho 1 NV (từ bảng kho số)."""
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        if user.exists():
            user.vd_no_number_share = bool(value)
        return True

    @api.model
    def distribute_numbers_to_users(self, number_ids, user_ids):
        """Chia ĐỀU các số ĐÃ CHỌN cho các NV ĐÃ CHỌN (popup chia số).

        Gom số theo nhà mạng → round-robin từng mạng cho danh sách NV: mỗi NV
        nhận 1 số/mạng, thay số CÙNG MẠNG đang có. (1 mạng 1 số / NV.)
        """
        self._check_board_access()
        numbers = self.browse(number_ids or []).filtered(lambda h: h.active)
        users = self.env['res.users'].browse(user_ids or []).filtered('active')
        if not numbers:
            return {'ok': False, 'message': 'Chưa chọn số nào để chia.'}
        if not users:
            return {'ok': False, 'message': 'Chưa chọn nhân viên nào.'}
        by_carrier = {}
        for h in numbers.sorted('number'):
            by_carrier.setdefault(h.carrier, []).append(h)
        users_sorted = users.sorted('name')
        for carrier, hs in by_carrier.items():
            n = len(hs)
            for idx, u in enumerate(users_sorted):
                target = hs[idx % n]
                same = u.stringee_hotline_ids.filtered(
                    lambda h: h.active and h.carrier == carrier and h.id != target.id
                )
                cmds = [(3, h.id) for h in same]
                cmds.append((4, target.id))
                u.sudo().stringee_hotline_ids = cmds
        labels = ', '.join(
            dict(_CARRIER_ORDER).get(c, c) for c in by_carrier
        )
        return {'ok': True, 'message':
                'Đã chia %d số (%s) cho %d NV.'
                % (len(numbers), labels, len(users))}

    @api.model
    def distribute_carrier_evenly(self, carrier='viettel'):
        """Chia ĐỀU các số CÒN SỐNG của 1 nhà mạng cho NV đủ điều kiện.

        - NV đủ điều kiện: active, không phải share-user, KHÔNG tick
          vd_no_number_share (admin/quản lý/Thành đã tick sẵn).
        - Số tham gia: hotline active của mạng đó VÀ đang 'alive' (đổ chuông
          gần đây — theo _vd_numbers_stats). Tránh gán số chết.
        - Round-robin: xoá số cũ CÙNG MẠNG của NV đủ điều kiện rồi gán lại đều.
        Trả {'ok', 'message'} để client toast.
        """
        self._check_board_access()
        hotlines = self.search([('active', '=', True), ('carrier', '=', carrier)])
        if not hotlines:
            return {'ok': False, 'message': 'Không có số %s nào trong kho.' % carrier}
        stats = self.env['stringee.call']._vd_numbers_stats(hotlines.mapped('number'))
        alive = hotlines.filtered(
            lambda h: (stats.get(h.number) or {}).get('health') == 'alive'
        )
        if not alive:
            return {'ok': False, 'message':
                    'Không có số %s nào CÒN SỐNG (đổ chuông gần đây) để chia. '
                    'Kiểm tra/mở outbound trên Stringee trước.' % carrier}
        users = self.env['res.users'].search([
            ('share', '=', False), ('active', '=', True),
            ('vd_no_number_share', '=', False),
        ], order='name')
        if not users:
            return {'ok': False, 'message': 'Không có NV đủ điều kiện để chia số.'}

        alive_sorted = alive.sorted('number')
        n_alive = len(alive_sorted)
        for idx, u in enumerate(users):
            target = alive_sorted[idx % n_alive]
            # bỏ mọi số cùng mạng đang gán, gán đúng 1 số target
            same = u.stringee_hotline_ids.filtered(
                lambda h: h.active and h.carrier == carrier and h.id != target.id
            )
            cmds = [(3, h.id) for h in same]
            cmds.append((4, target.id))
            u.sudo().stringee_hotline_ids = cmds
        _lbl = dict(_CARRIER_ORDER).get(carrier, carrier)
        return {'ok': True, 'message':
                'Đã chia đều %d số %s (còn sống) cho %d NV.'
                % (n_alive, _lbl, len(users))}

    @api.model
    def assign_user_hotline(self, user_id, hotline_id):
        """Gán số cho NV. 1 mạng 1 số → bỏ số cùng mạng cũ trước khi gán số mới."""
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        hotline = self.browse(hotline_id)
        if not user.exists() or not hotline.exists() or not hotline.active:
            return False
        same_carrier = user.stringee_hotline_ids.filtered(
            lambda h: h.active and h.carrier == hotline.carrier and h.id != hotline.id
        )
        cmds = [(3, h.id) for h in same_carrier]
        cmds.append((4, hotline.id))
        user.stringee_hotline_ids = cmds
        return True

    @api.model
    def unassign_user_hotline(self, user_id, hotline_id):
        """Gỡ 1 số khỏi NV."""
        self._check_board_access()
        user = self.env['res.users'].browse(user_id).sudo()
        if not user.exists():
            return False
        user.stringee_hotline_ids = [(3, hotline_id)]
        return True

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gán NV cho %s') % (self.name or self.number or ''),
            'res_model': 'vd.stringee.hotline.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hotline_id': self.id,
                'active_id': self.id,
                'active_model': 'vd.stringee.hotline',
            },
        }
