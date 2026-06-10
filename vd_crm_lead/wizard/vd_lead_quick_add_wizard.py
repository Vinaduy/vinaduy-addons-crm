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
    # User spec 2026-06-03: bỏ "chia đều" cũ. Flow mới: nhập KH trước → bấm
    # CHỌN NHÂN VIÊN (show_distribute=True) → chọn 1 trong 4 cách chia → cột NV
    # tự điền → bấm CHIA SỐ (action_create_leads) để tạo.
    show_distribute = fields.Boolean(default=False)
    # User spec 2026-06-05: nút CHIA SỐ chỉ hiện khi TẤT CẢ khách (Tên+SĐT) đã
    # có nhân viên. NV thường (không phải leader) tự gán mình -> luôn cho CHIA.
    can_chia_so = fields.Boolean(compute='_compute_can_chia_so')

    @api.depends('line_ids.user_id', 'line_ids.name', 'line_ids.phone')
    def _compute_can_chia_so(self):
        is_leader = self.env.user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        for w in self:
            valid = w.line_ids.filtered(lambda l: l.name and l.phone)
            if not valid:
                w.can_chia_so = False
            elif is_leader:
                w.can_chia_so = all(l.user_id for l in valid)
            else:
                w.can_chia_so = True

    distribute_mode = fields.Selection(
        [
            ('even_all', '⚖️ Chia đều cho TẤT CẢ nhân viên'),
            ('least', '📉 Dồn cho nhân viên ÍT SỐ nhất'),
            ('per_line', '✍️ Chọn nhân viên theo từng khách'),
            ('group', '👥 Chia đều theo NHÓM nhân viên đã chọn'),
        ],
        string='Cách chia số',
    )
    group_user_ids = fields.Many2many(
        'res.users', string='Nhóm NV nhận',
        domain="[('share', '=', False)]",
        help='Chọn 2+ nhân viên — khách sẽ được chia đều trong nhóm này.',
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

    def _vd_check_leader(self):
        if not self.env.user.has_group('vd_crm_lead.vd_crm_group_team_leader'):
            raise UserError(_(
                'Chỉ Trưởng nhóm / Admin mới được chia KH cho nhân viên.'
            ))

    def _vd_eligible_users(self):
        """POOL NV nhận KH: salesman, không phải lãnh đạo, đang nhận KH mới."""
        ResUsers = self.env['res.users'].sudo()
        candidates = ResUsers.search([
            ('share', '=', False),
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ])
        return candidates.filtered(
            lambda u: not u.has_group('vd_crm_lead.vd_crm_group_team_leader')
                      and u.vd_can_receive_new_leads
        )

    def _vd_user_new_total(self, uid):
        """Tổng KH MỚI hiện tại của 1 NV (bucket KHÁCH MỚI)."""
        Lead = self.env['crm.lead'].sudo()
        return Lead.search_count(
            Lead._dashboard_new_bucket_domain([('user_id', '=', uid)]))

    @api.model
    def _vd_phone_is_valid(self, phone):
        """SĐT hợp lệ = số di động VN: 10 số (0 + 9 số), đầu số 03/05/07/08/09.
        Chặn nhập linh tinh ('2', '3434'...)."""
        s = self.env['crm.lead']._vd_normalize_phones_set(phone)
        if not s:
            return False
        nat = next(iter(s))   # đã strip 0/84
        return len(nat) == 9 and nat[0] in '35789'

    @api.model
    def _vd_name_is_valid(self, name):
        """Tên hợp lệ = có ≥2 CHỮ CÁI (chặn 'A2', '22', ký tự linh tinh)."""
        import re
        return len(re.findall(r'[^\W\d_]', name or '', re.UNICODE)) >= 2

    def _vd_validate_quick_lines(self, lines):
        """Chặn dòng nhập linh tinh (tên/SĐT không hợp lệ) — user spec 2026-06-10."""
        bad = []
        for l in lines:
            errs = []
            if not self._vd_name_is_valid(l.name):
                errs.append('TÊN không hợp lệ')
            if not self._vd_phone_is_valid(l.phone):
                errs.append('SĐT không hợp lệ')
            if errs:
                bad.append('• %s — %s: %s' % (
                    l.name or '(trống)', l.phone or '(trống)', ', '.join(errs)))
        if bad:
            raise UserError(_(
                'Có %d dòng nhập SAI — sửa lại trước khi chia số:\n%s\n\n'
                'Quy tắc: TÊN phải có ≥2 chữ cái · SĐT phải là số di động VN '
                '(10 số, đầu 03/05/07/08/09).'
            ) % (len(bad), '\n'.join(bad)))

    def action_show_distribute(self):
        """Bấm CHỌN NHÂN VIÊN → hiện bộ chọn cách chia (sau khi đã nhập KH)."""
        self.ensure_one()
        self._vd_check_leader()
        valid_lines = self.line_ids.filtered(lambda l: l.name and l.phone)
        if not valid_lines:
            raise UserError(_('Hãy nhập ít nhất 1 khách (Tên + SĐT) trước khi chia số.'))
        # CHẶN NHẬP LINH TINH (tên/SĐT sai) trước khi sang bước chia.
        self._vd_validate_quick_lines(valid_lines)
        # CHẶN TRÙNG NGAY (user 2026-06-05): nhập 2 số giống nhau (kể cả số chưa
        # chuẩn) hoặc đã có trong hệ thống -> không cho sang bước chia.
        dups = self.line_ids.filtered(lambda l: l.name and l.phone and l.phone_is_dup)
        if dups:
            raise UserError(_(
                'Có %d số bị TRÙNG (nhập 2 lần hoặc đã có trong hệ thống) — '
                'sửa/xoá trước khi chia số:\n%s'
            ) % (len(dups), '\n'.join(
                '• %s — %s' % (l.name or '(chưa tên)', l.phone or '') for l in dups)))
        # BẮT BUỘC chọn NGUỒN (user 2026-06-05).
        no_src = self.line_ids.filtered(lambda l: l.name and l.phone and not l.source)
        if no_src:
            raise UserError(_(
                'Vui lòng chọn NGUỒN cho các khách:\n%s'
            ) % '\n'.join('• %s — %s' % (l.name or '(chưa tên)', l.phone or '') for l in no_src))
        self.show_distribute = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, dialog_size='fullscreen'),
        }

    @api.onchange('distribute_mode', 'group_user_ids')
    def _onchange_distribute_mode(self):
        """Chọn cách chia → tự ĐIỀN cột Nhân viên cho từng dòng."""
        if not self.show_distribute or not self.distribute_mode:
            return
        self._vd_apply_distribution()

    def _vd_apply_distribution(self):
        """Điền user_id cho từng dòng KH theo distribute_mode."""
        lines = self.line_ids.filtered(lambda l: l.name and l.phone)
        if not lines:
            return
        mode = self.distribute_mode
        if mode == 'per_line':
            # NV chọn tay → không tự điền (giữ nguyên / xoá để chọn lại)
            return
        if mode == 'group':
            pool = list(self.group_user_ids)
            if not pool:
                return
        else:
            pool = list(self._vd_eligible_users())
        if not pool:
            raise UserError(_(
                'Không có NV nào đủ điều kiện nhận KH mới (kiểm tra quá hạn chăm sóc).'
            ))
        # Tải hiện tại (tổng KH mới) — dùng cho 'least' và để chia đều cân bằng.
        load = {u.id: self._vd_user_new_total(u.id) for u in pool}
        if mode == 'least':
            # Greedy: mỗi KH → NV đang ít số nhất (tính cả KH vừa gán trong đợt).
            assigned = dict(load)
            for line in lines:
                uid = min(assigned, key=lambda k: assigned[k])
                line.user_id = uid
                assigned[uid] += 1
        else:
            # even_all / group: round-robin theo thứ tự NV ít số → nhiều số.
            order = sorted(pool, key=lambda u: load.get(u.id, 0))
            n = len(order)
            for i, line in enumerate(lines):
                line.user_id = order[i % n].id

    def action_redistribute(self):
        """Nút 'Chia lại' — áp dụng lại distribution với cấu hình hiện tại."""
        self.ensure_one()
        self._vd_apply_distribution()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, dialog_size='fullscreen'),
        }

    def action_create_leads(self):
        """Tạo N lead từ self.line_ids — mỗi dòng 1 lead."""
        self.ensure_one()
        Lead = self.env['crm.lead']
        ResUsers = self.env['res.users']

        lines = self.line_ids.filtered(lambda l: l.name and l.phone)
        if not lines:
            raise UserError(_('Phải có ít nhất 1 dòng có Tên + SĐT.'))

        # CHẶN NHẬP LINH TINH (tên/SĐT sai) — user spec 2026-06-10.
        self._vd_validate_quick_lines(lines)

        # CHẶN TRÙNG SỐ — không cho tạo nếu có số đã có trong hệ thống / nhập 2 lần.
        dups = lines.filtered(lambda l: l.phone_is_dup)
        if dups:
            raise UserError(_(
                'Có %d số bị TRÙNG (đã có trong hệ thống hoặc nhập 2 lần) — '
                'vui lòng sửa/xoá trước khi chia số:\n%s'
            ) % (len(dups), '\n'.join(
                '• %s — %s' % (l.name or '(chưa tên)', l.phone or '') for l in dups)))
        # BẮT BUỘC chọn NGUỒN (user 2026-06-05).
        no_src = lines.filtered(lambda l: not l.source)
        if no_src:
            raise UserError(_(
                'Vui lòng chọn NGUỒN cho các khách:\n%s'
            ) % '\n'.join('• %s — %s' % (l.name or '(chưa tên)', l.phone or '') for l in no_src))

        user = self.env.user
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        Stage = self.env['crm.stage'].sudo()

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

    # ===== Chỉ số tải NV — hiện CẠNH tên NV sau khi chia số =====
    assignee_new_total = fields.Integer(
        string='Tổng KH mới', compute='_compute_assignee_stats')
    assignee_not_called = fields.Integer(
        string='Chưa gọi', compute='_compute_assignee_stats')
    assignee_overloaded = fields.Boolean(compute='_compute_assignee_stats')
    assignee_stat_label = fields.Char(
        string='Tải NV (KH mới)', compute='_compute_assignee_stats')

    @api.depends('user_id', 'wizard_id.line_ids.user_id')
    def _compute_assignee_stats(self):
        Lead = self.env['crm.lead'].sudo()
        stat = {}

        def _stat(uid):
            if uid not in stat:
                base = Lead._dashboard_new_bucket_domain([('user_id', '=', uid)])
                stat[uid] = (Lead.search_count(base),
                             Lead.search_count(base + [('call_count', '=', 0)]))
            return stat[uid]

        # Tải hiệu dụng theo từng wizard (tổng KH mới + KH vừa gán trong đợt)
        wiz_loads = {}
        for wiz in self.mapped('wizard_id'):
            assigned = {}
            for l in wiz.line_ids:
                if l.user_id and l.name:
                    assigned[l.user_id.id] = assigned.get(l.user_id.id, 0) + 1
            loads = {uid: _stat(uid)[0] + cnt for uid, cnt in assigned.items()}
            avg = (sum(loads.values()) / len(loads)) if loads else 0
            wiz_loads[wiz.id] = (loads, avg)
        for rec in self:
            if not rec.user_id:
                rec.assignee_new_total = 0
                rec.assignee_not_called = 0
                rec.assignee_overloaded = False
                rec.assignee_stat_label = ''
                continue
            total, nc = _stat(rec.user_id.id)
            rec.assignee_new_total = total
            rec.assignee_not_called = nc
            loads, avg = wiz_loads.get(rec.wizard_id.id, ({}, 0))
            eff = loads.get(rec.user_id.id, total)
            over = bool(avg and len(loads) >= 2 and eff > avg * 1.5 and eff >= 10)
            rec.assignee_overloaded = over
            rec.assignee_stat_label = (
                '📋 %d mới · 📵 %d chưa gọi%s'
                % (total, nc, ' ⚠️ QUÁ TẢI' if over else '')
            )

    def action_copy_user_down(self):
        """User spec 2026-06-10: sao chép NHÂN VIÊN của dòng này XUỐNG tất cả các
        dòng dưới (có tên KH). Tiện chia 1 NV cho cả loạt khách bên dưới."""
        self.ensure_one()
        if not self.user_id:
            raise UserError(_('Hãy chọn nhân viên cho dòng này trước khi sao chép xuống.'))
        below = self.wizard_id.line_ids.filtered(
            lambda l: l.id != self.id
            and (l.sequence, l.id) > (self.sequence, self.id)
            and l.name)
        if below:
            below.write({'user_id': self.user_id.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vd.lead.quick.add.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, dialog_size='fullscreen'),
        }

    # ===== CHẶN TRÙNG SỐ — đã có trong hệ thống / nhập 2 lần trong danh sách =====
    phone_is_dup = fields.Boolean(compute='_compute_phone_dup')
    phone_dup_label = fields.Char(string='Cảnh báo', compute='_compute_phone_dup')

    @api.depends('phone', 'wizard_id.line_ids.phone')
    def _compute_phone_dup(self):
        Lead = self.env['crm.lead'].sudo()

        def norm(p):
            s = Lead._vd_normalize_phones_set(p)
            if s:
                return next(iter(s))
            # Fallback: số CHƯA chuẩn (vd '33') vẫn so THÔ để bắt trùng trong bảng.
            return (p or '').strip()

        # Đếm trùng TRONG wizard (cùng số nhập nhiều dòng)
        wiz_count = {}
        for wiz in self.mapped('wizard_id'):
            cnt = {}
            for l in wiz.line_ids:
                c = norm(l.phone)
                if c:
                    cnt[c] = cnt.get(c, 0) + 1
            wiz_count[wiz.id] = cnt
        # Số đã có TRONG HỆ THỐNG (mọi lead, kể cả đã archive)
        cores = {norm(l.phone) for l in self if l.phone}
        cores.discard('')
        sys_cores = set()
        if cores:
            variants = []
            for c in cores:
                variants += [c, '0' + c, '84' + c, '+84' + c]
            rows = Lead.with_context(active_test=False).search_read(
                [('phone', 'in', variants)], ['phone'])
            for r in rows:
                cc = norm(r.get('phone'))
                if cc:
                    sys_cores.add(cc)
        for rec in self:
            c = norm(rec.phone)
            if not c:
                rec.phone_is_dup = False
                rec.phone_dup_label = ''
                continue
            in_sys = c in sys_cores
            in_wiz = wiz_count.get(rec.wizard_id.id, {}).get(c, 0) > 1
            rec.phone_is_dup = bool(in_sys or in_wiz)
            if in_sys:
                rec.phone_dup_label = '⛔ TRÙNG — số đã có trong hệ thống'
            elif in_wiz:
                rec.phone_dup_label = '⛔ TRÙNG — nhập 2 lần trong danh sách'
            else:
                rec.phone_dup_label = ''

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
    i_district = fields.Many2one('vd.district', string='Phường/Xã')
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
