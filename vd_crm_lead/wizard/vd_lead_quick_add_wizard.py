# -*- coding: utf-8 -*-
"""Quick-add lead wizard — bảng tính nhập nhiều KH cùng lúc.

Mỗi dòng = 1 KH: tên, SĐT, nguồn, ngày, trạng thái.
Trạng thái rỗng → mặc định 'Khách mới'. Có chọn → lead được đẩy thẳng vào stage đó.
Auto-assign theo round-robin (leader/admin) hoặc gán cho chính mình (NV).
"""
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError


SOURCE_SELECTION = [
    ('manual', '📝 Thủ công'),
    ('facebook', '📘 Facebook'),
    ('tiktok', '🎵 TikTok'),
    ('instagram', '📸 Instagram'),
    ('zalo', '💬 Zalo'),
    ('hotline', '☎ Hotline'),
    ('referral', '🤝 Giới thiệu'),
]

SOURCE_PREFIX = {
    'facebook': '[FB] ',
    'tiktok': '[TT] ',
    'instagram': '[IG] ',
    'zalo': '[Zalo] ',
    'hotline': '[Hotline] ',
    'referral': '[GT] ',
    'manual': '',
}

# Map trạng thái dashboard → stage code trong crm.stage
STATUS_SELECTION = [
    ('new', '🆕 Khách mới'),
    ('progress', '⏳ Khách đang xử lý vấn đề'),
    ('won', '🏆 Khách chốt'),
    ('lost', '❌ Khách hủy'),
]
STATUS_TO_STAGE_CODE = {
    'new': 'new',
    'progress': 'quote',  # mid-funnel representative
    'won': 'won',
    'lost': 'lost',
}


class VdLeadQuickAddWizard(models.TransientModel):
    _name = 'vd.lead.quick.add.wizard'
    _description = 'Thêm KH nhanh (bảng tính nhiều dòng)'

    line_ids = fields.One2many(
        'vd.lead.quick.add.wizard.line', 'wizard_id',
        string='Danh sách KH',
    )
    # User spec 2026-05-29: mutually exclusive — manual per-line user_id
    # vs auto round-robin distribute on save. Ẩn cột NV khi chọn 'even'.
    assign_mode = fields.Selection(
        [
            ('manual', '👤 Tự chọn NV cho từng KH'),
            ('even', '🎯 Chia đều cho tất cả NV'),
        ],
        string='Phân bổ NV',
        default='manual',
        required=True,
    )
    # Quick-create field: admin gõ tên → tạo vd.intake.custom.field → cột
    # tương ứng xuất hiện trong bảng (qua fields_get override trên line model).
    quick_add_field_id = fields.Many2one(
        'vd.intake.custom.field',
        string='+ Thêm cột',
        store=False,
        help='Gõ tên cột mới + Enter để tạo. Đóng và mở lại wizard để thấy cột mới.',
    )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """Xoá các <field name="extra_N"/> dư khỏi arch khi N > số custom field đang active.
        Tránh hiện 'Tuỳ chọn N' vô nghĩa trong dropdown ⋮ optional columns."""
        arch, view = super()._get_view(view_id, view_type, **options)
        try:
            n = self.env['vd.intake.custom.field'].sudo().search_count(
                [('active', '=', True)],
            )
            for idx in range(n + 1, 11):
                for node in arch.xpath(f'//field[@name="extra_{idx}"]'):
                    node.getparent().remove(node)
        except Exception:
            pass
        return arch, view

    @api.onchange('quick_add_field_id')
    def _onchange_quick_add_field_id(self):
        if self.quick_add_field_id:
            field = self.quick_add_field_id
            self.quick_add_field_id = False
            return {
                'warning': {
                    'title': '✅ Đã tạo cột mới',
                    'message': f'Cột "{field.name}" đã được tạo. Đóng wizard và '
                               f'mở lại để cột xuất hiện trong bảng.',
                },
            }

    def action_distribute_evenly(self):
        """User spec 2026-05-29: chia đều các dòng cho tất cả NV eligible.
        Round-robin theo thứ tự dòng trong wizard. Override user_id hiện tại.

        Only Leader/Admin được dùng (NV thường không được phân lead cho NV khác).
        """
        self.ensure_one()
        user = self.env.user
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        if not is_leader:
            raise UserError(_(
                'Chỉ Trưởng nhóm / Admin mới được chia KH cho tất cả NV.'
            ))

        ResUsers = self.env['res.users'].sudo()
        # Lấy POOL NV sales eligible (loại lãnh đạo, chỉ NV có vd_can_receive_new_leads)
        domain = [
            ('share', '=', False),
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ]
        candidates = ResUsers.search(domain)
        eligible = candidates.filtered(
            lambda u: not u.has_group('vd_crm_lead.vd_crm_group_team_leader')
                      and u.vd_can_receive_new_leads
        )
        if not eligible:
            raise UserError(_('Không có NV nào đủ điều kiện nhận KH mới (kiểm tra quá hạn chăm sóc).'))

        # Sort theo số lead active asc → NV ít lead nhận trước
        users_sorted = sorted(
            eligible,
            key=lambda u: self.env['crm.lead'].sudo().search_count([
                ('user_id', '=', u.id),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ]),
        )
        # Round-robin gán
        lines = self.line_ids.filtered(lambda l: l.name and l.phone)
        n = len(users_sorted)
        for i, line in enumerate(lines):
            line.user_id = users_sorted[i % n].id

        # Notification: bao nhiêu lines / bao nhiêu NV
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã chia đều'),
                'message': _('Đã chia %d KH cho %d NV (round-robin theo NV ít lead nhất).') % (len(lines), n),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_create_leads(self):
        """Tạo N lead từ self.line_ids — mỗi dòng 1 lead."""
        self.ensure_one()
        Lead = self.env['crm.lead']
        ResUsers = self.env['res.users']

        lines = self.line_ids.filtered(lambda l: l.name and l.phone)
        if not lines:
            raise UserError(_('Phải có ít nhất 1 dòng có Tên + SĐT.'))

        user = self.env.user
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        Stage = self.env['crm.stage'].sudo()

        # User spec 2026-05-29: mode='even' → distribute round-robin trước khi tạo
        if self.assign_mode == 'even':
            if not is_leader:
                raise UserError(_(
                    'Chỉ Trưởng nhóm / Admin mới được chọn "Chia đều cho NV".'
                ))
            self.action_distribute_evenly()

        # Cache stage lookups for 3 status options
        stage_cache = {}
        for status_key, stage_code in STATUS_TO_STAGE_CODE.items():
            s = Stage.search([('code', '=', stage_code)], limit=1)
            if s:
                stage_cache[status_key] = s.id

        created = self.env['crm.lead']
        for line in lines:
            # Assignee: ưu tiên user chọn explicit, fallback round-robin/self
            if line.user_id:
                assignee = line.user_id
            elif is_leader:
                picked = ResUsers.sudo()._vd_pick_next_assignee()
                assignee = picked or user
            else:
                assignee = user

            prefix = SOURCE_PREFIX.get(line.source or 'manual', '')
            vals = {
                'name': f'{prefix}{line.name}'.strip(),
                'partner_name': line.name,
                'phone': line.phone,
                'user_id': assignee.id,
                'type': 'lead',
            }
            stage_id = stage_cache.get(line.status)
            if stage_id:
                vals['stage_id'] = stage_id
            if line.date:
                vals['date_open'] = fields.Datetime.to_datetime(line.date)

            # Map intake mirror fields (i_*) → vd_intake_* trên crm.lead
            intake_vals = {}
            mirror_map = {
                'i_house_type': 'vd_intake_house_type',
                'i_foundation_type': 'vd_intake_foundation_type',
                # i_floors_select xử lý riêng phía dưới (vì có biến thể "Nt" = N tầng + tum)
                'i_area_m2': 'vd_intake_area_m2',
                'i_floor_1_m2': 'vd_intake_floor_1_m2',
                'i_floor_2_m2': 'vd_intake_floor_2_m2',
                'i_floor_3_m2': 'vd_intake_floor_3_m2',
                'i_floor_4_m2': 'vd_intake_floor_4_m2',
                'i_floor_5_m2': 'vd_intake_floor_5_m2',
                'i_floor_6_m2': 'vd_intake_floor_6_m2',
                'i_floor_7_m2': 'vd_intake_floor_7_m2',
                'i_floor_tum_m2': 'vd_intake_floor_tum_m2',
                'i_province_id': 'vd_intake_province_id',
                'i_district': 'vd_intake_district',
                'i_dimensions': 'vd_intake_dimensions',
                'i_land_type': 'vd_intake_land_type',
                'i_car_access_select': 'vd_intake_car_access_select',
                'i_budget_amount': 'vd_intake_budget_amount',
            }
            for line_fld, lead_fld in mirror_map.items():
                val = line[line_fld]
                if not val:
                    continue
                # Defensive: nếu lead field là Selection, chỉ gán khi key có
                # trong selection — tránh ValueError nếu wizard/lead lệch keys.
                # selection có thể là callable (extensible) → dùng helper.
                lead_field = Lead._fields.get(lead_fld)
                if lead_field and lead_field.type == 'selection':
                    sel = lead_field.selection
                    if callable(sel):
                        sel = sel(Lead)
                    valid_keys = {k for k, _lbl in (sel or [])}
                    if val not in valid_keys:
                        continue
                intake_vals[lead_fld] = val.id if hasattr(val, 'id') else val
            # Tách "Nt" → vd_intake_floors_select=N + vd_intake_has_tum=True
            if line.i_floors_select:
                raw = line.i_floors_select
                if raw.endswith('t'):
                    intake_vals['vd_intake_floors_select'] = raw[:-1]
                    intake_vals['vd_intake_has_tum'] = True
                else:
                    intake_vals['vd_intake_floors_select'] = raw
            # Nếu có diện tích Tum thì cũng set vd_intake_has_tum=True
            if intake_vals.get('vd_intake_floor_tum_m2'):
                intake_vals['vd_intake_has_tum'] = True
            vals.update(intake_vals)

            # vd_skip_assignment_balance: khách nhập TAY qua wizard là lựa chọn
            # explicit của NV/leader → KHÔNG reroute dù NV đang quá hạn (>threshold).
            # Chặn quá-hạn chỉ áp cho lead tự động (Pancake / chia đều), không áp
            # cho self-add. User spec 2026-05-30: "tự thêm thì luôn giữ".
            lead = Lead.with_context(
                vd_skip_reassign_check=True,
                vd_skip_assignment_balance=True,
            ).create(vals)
            created |= lead

            # Nếu line có preset phát sinh + qty → tạo vd.lead.surcharge
            if line.surcharge_preset_id and line.surcharge_qty:
                preset = line.surcharge_preset_id
                self.env['vd.lead.surcharge'].sudo().create({
                    'lead_id': lead.id,
                    'name': preset.name,
                    'quantity': line.surcharge_qty,
                    'quantity_label': (
                        f'Số lượng {int(line.surcharge_qty)} {preset.unit_label}'
                        if preset.unit_label else f'Số lượng {int(line.surcharge_qty)}'
                    ),
                    'unit_price': preset.unit_price,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã tạo %s KH') % len(created),
                'message': _('Đã phân bổ cho NV phụ trách.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }


class VdLeadQuickAddWizardLine(models.TransientModel):
    _name = 'vd.lead.quick.add.wizard.line'
    _description = 'Dòng KH trong wizard thêm nhanh'
    _order = 'sequence, id'

    # Base selection cho các field "extensible" — selection callable sẽ merge
    # với records từ vd.field.option để user có thể "+ Thêm mới" trên UI.
    _VD_EXT_SELECTIONS = {
        'source': SOURCE_SELECTION,
        'i_house_type': [
            ('mai_bang', 'Nhà mái bằng'),
            ('mai_thai', 'Nhà mái thái'),
            ('mai_nhat', 'Nhà mái nhật'),
        ],
        'i_foundation_type': [
            ('don', 'Móng đơn'),
            ('bang', 'Móng băng'),
            ('coc', 'Móng cọc'),
        ],
        'i_dimensions': [
            ('co_so_can_phep', 'CÓ SỔ - Phải làm cấp phép'),
            ('co_so_khong_phep', 'CÓ SỔ - Không cần cấp phép'),
            ('khong_so_khong_phep', 'KHÔNG SỔ - Không cần cấp phép'),
        ],
        'i_land_type': [
            ('dat_cung', 'ĐẤT CỨNG - Liền thổ'),
            ('dat_yeu', 'ĐẤT YẾU - Ao ruộng san lấp'),
        ],
    }

    @api.model
    def _vd_ext_selection(self, fname):
        """Merge base selection + user-added records từ vd.field.option."""
        base = list(self._VD_EXT_SELECTIONS.get(fname, []))
        try:
            extras = self.env['vd.field.option'].sudo().get_options(
                self._name, fname,
            )
        except Exception:
            extras = []
        keys = {k for k, _ in base}
        return base + [(k, l) for k, l in extras if k not in keys]

    wizard_id = fields.Many2one(
        'vd.lead.quick.add.wizard', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='STT', default=10)
    name = fields.Char(string='Tên KH', required=False)
    phone = fields.Char(string='SĐT', required=False)

    @api.onchange('name')
    def _onchange_name_normalize(self):
        """User spec 2026-05-29: normalize tên KH theo quy tắc title-case
        (preserves ASCII team code, capitalize từng từ Vietnamese)."""
        if self.name:
            normalized = self.env['crm.lead']._vd_normalize_kh_name(self.name)
            if normalized != self.name:
                self.name = normalized
    source = fields.Selection(
        selection=lambda self: self._vd_ext_selection('source'),
        string='Nguồn',
        # User spec 2026-05-29: KHÔNG default → bắt NV chọn explicit
    )
    date = fields.Date(
        string='Ngày',
        default=fields.Date.context_today,
    )
    status = fields.Selection(
        STATUS_SELECTION,
        string='Trạng thái',
        default='new',
        help='Khách mới → stage "Khách mới". Đang xử lý → stage "Khách báo giá". '
             'Khách chốt → stage "Khách chốt".',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Nhân viên',
        domain="[('share', '=', False)]",
        help='Chọn NV phụ trách. Để trống = round-robin (leader) hoặc gán cho chính mình (NV).',
    )

    # ===== MIRROR các trường intake từ crm.lead — admin bật tắt qua ⋮ menu =====
    # Khi NV nhập giá trị → action_create_leads sẽ ghi xuống crm.lead tương ứng.
    i_house_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('i_house_type'),
        string='Kiểu nhà',
    )
    i_foundation_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('i_foundation_type'),
        string='Loại móng',
    )
    i_floors_select = fields.Selection([
        ('1', '1 tầng'), ('1t', '1 tầng + tum'),
        ('2', '2 tầng'), ('2t', '2 tầng + tum'),
        ('3', '3 tầng'), ('3t', '3 tầng + tum'),
        ('4', '4 tầng'), ('4t', '4 tầng + tum'),
        ('5', '5 tầng'), ('5t', '5 tầng + tum'),
        ('6', '6 tầng'), ('6t', '6 tầng + tum'),
        ('7', '7 tầng'), ('7t', '7 tầng + tum'),
    ], string='Số tầng')
    i_area_m2 = fields.Float(string='Tổng DT đất (m²)', digits=(10, 1))
    # Integer (m² số nguyên) — đồng bộ với crm.lead, tránh '0,0' + parse lỗi.
    i_floor_1_m2 = fields.Integer(string='Tầng 1 (m²)')
    i_floor_2_m2 = fields.Integer(string='Tầng 2 (m²)')
    i_floor_3_m2 = fields.Integer(string='Tầng 3 (m²)')
    i_floor_4_m2 = fields.Integer(string='Tầng 4 (m²)')
    i_floor_5_m2 = fields.Integer(string='Tầng 5 (m²)')
    i_floor_6_m2 = fields.Integer(string='Tầng 6 (m²)')
    i_floor_7_m2 = fields.Integer(string='Tầng 7 (m²)')
    i_floor_tum_m2 = fields.Integer(string='Tum (m²)')
    i_province_id = fields.Many2one('res.country.state', string='Tỉnh/Thành',
                                    domain="[('country_id.code', '=', 'VN')]")
    i_district = fields.Many2one('vd.district', string='Huyện/Quận')
    # Base keys PHẢI khớp 1-1 với crm.lead.vd_intake_dimensions để mirror_map
    # copy thẳng được mà không cần convert key.
    i_dimensions = fields.Selection(
        selection=lambda self: self._vd_ext_selection('i_dimensions'),
        string='Sổ đỏ / cấp phép',
    )
    i_land_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('i_land_type'),
        string='Loại đất',
    )
    i_car_access_select = fields.Selection([
        ('xe_tai_lon', 'ĐƯỜNG - Xe tải lớn'),
        ('xe_tai_nho', 'ĐƯỜNG - Xe tải nhỏ'),
        ('xe_3_banh', 'ĐƯỜNG - Xe 3 bánh'),
    ], string='Ô tô vào')
    i_budget_amount = fields.Float(string='Ngân sách (VNĐ)')

    # 10 cột tuỳ chọn — admin tự đặt tên qua "+ Thêm cột" (vd.intake.custom.field).
    # Label hiển thị được override dynamic trong fields_get() dựa trên config.
    extra_1 = fields.Char(string='Tuỳ chọn 1')
    extra_2 = fields.Char(string='Tuỳ chọn 2')
    extra_3 = fields.Char(string='Tuỳ chọn 3')
    extra_4 = fields.Char(string='Tuỳ chọn 4')
    extra_5 = fields.Char(string='Tuỳ chọn 5')
    extra_6 = fields.Char(string='Tuỳ chọn 6')
    extra_7 = fields.Char(string='Tuỳ chọn 7')
    extra_8 = fields.Char(string='Tuỳ chọn 8')
    extra_9 = fields.Char(string='Tuỳ chọn 9')
    extra_10 = fields.Char(string='Tuỳ chọn 10')

    # ===== Phát sinh preset (cũ — vẫn giữ phòng khi cần) =====
    surcharge_preset_id = fields.Many2one(
        'vd.lead.surcharge.preset',
        string='+ Tùy biến',
        domain="[('active', '=', True)]",
    )
    surcharge_qty = fields.Float(string='Số lượng PS', digits=(10, 2))

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Map vd.intake.custom.field config → extra_N column labels.
        Field luôn tồn tại để view không crash; slot dư bị xoá khỏi arch trong _get_view."""
        res = super().fields_get(allfields, attributes)
        try:
            cfs = self.env['vd.intake.custom.field'].sudo().search(
                [('active', '=', True)], order='sequence, id', limit=10,
            )
            for idx, cf in enumerate(cfs, start=1):
                key = f'extra_{idx}'
                if key in res:
                    res[key]['string'] = cf.name
                    if cf.help_text:
                        res[key]['help'] = cf.help_text
        except Exception:
            pass
        return res
