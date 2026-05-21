# -*- coding: utf-8 -*-
"""Quick-add lead wizard — bảng tính nhập nhiều KH cùng lúc.

Mỗi dòng = 1 KH: tên, SĐT, nguồn, ngày, trạng thái.
Trạng thái rỗng → mặc định 'Khách mới'. Có chọn → lead được đẩy thẳng vào stage đó.
Auto-assign theo round-robin (leader/admin) hoặc gán cho chính mình (NV).
"""
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

# Map trạng thái dashboard (3 cột) → stage code trong crm.stage
STATUS_SELECTION = [
    ('new', '🆕 Khách mới'),
    ('progress', '⏳ Đang xử lý vấn đề'),
    ('won', '🏆 Khách chốt'),
]
STATUS_TO_STAGE_CODE = {
    'new': 'new',
    'progress': 'quote',  # mid-funnel representative
    'won': 'won',
}


class VdLeadQuickAddWizard(models.TransientModel):
    _name = 'vd.lead.quick.add.wizard'
    _description = 'Thêm KH nhanh (bảng tính nhiều dòng)'

    line_ids = fields.One2many(
        'vd.lead.quick.add.wizard.line', 'wizard_id',
        string='Danh sách KH',
    )
    # Quick-create field: admin gõ tên → tạo vd.intake.custom.field → cột
    # tương ứng xuất hiện trong bảng (qua fields_get override trên line model).
    quick_add_field_id = fields.Many2one(
        'vd.intake.custom.field',
        string='+ Thêm cột',
        store=False,
        help='Gõ tên cột mới + Enter để tạo. Đóng và mở lại wizard để thấy cột mới.',
    )

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
                'i_floors_select': 'vd_intake_floors_select',
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
                if val:
                    intake_vals[lead_fld] = val.id if hasattr(val, 'id') else val
            # Nếu có Tum thì set vd_intake_has_tum=True
            if intake_vals.get('vd_intake_floor_tum_m2'):
                intake_vals['vd_intake_has_tum'] = True
            vals.update(intake_vals)

            lead = Lead.with_context(vd_skip_reassign_check=True).create(vals)
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

    wizard_id = fields.Many2one(
        'vd.lead.quick.add.wizard', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='STT', default=10)
    name = fields.Char(string='Tên KH', required=False)
    phone = fields.Char(string='SĐT', required=False)
    source = fields.Selection(
        SOURCE_SELECTION,
        string='Nguồn',
        default='manual',
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
    i_house_type = fields.Selection([
        ('mai_bang', 'Nhà mái bằng'),
        ('mai_thai', 'Nhà mái thái'),
        ('mai_nhat', 'Nhà mái nhật'),
        ('nha_ong', 'Nhà ống'),
    ], string='Kiểu nhà')
    i_foundation_type = fields.Selection([
        ('don', 'Móng đơn'),
        ('bang', 'Móng băng'),
        ('coc', 'Móng cọc'),
    ], string='Loại móng')
    i_floors_select = fields.Selection([
        ('1', '1 tầng'), ('2', '2 tầng'), ('3', '3 tầng'),
        ('4', '4 tầng'), ('5', '5 tầng'), ('6', '6 tầng'), ('7', '7 tầng'),
    ], string='Số tầng')
    i_area_m2 = fields.Float(string='Tổng DT đất (m²)', digits=(10, 1))
    i_floor_1_m2 = fields.Float(string='Tầng 1 (m²)', digits=(10, 1))
    i_floor_2_m2 = fields.Float(string='Tầng 2 (m²)', digits=(10, 1))
    i_floor_3_m2 = fields.Float(string='Tầng 3 (m²)', digits=(10, 1))
    i_floor_4_m2 = fields.Float(string='Tầng 4 (m²)', digits=(10, 1))
    i_floor_5_m2 = fields.Float(string='Tầng 5 (m²)', digits=(10, 1))
    i_floor_6_m2 = fields.Float(string='Tầng 6 (m²)', digits=(10, 1))
    i_floor_7_m2 = fields.Float(string='Tầng 7 (m²)', digits=(10, 1))
    i_floor_tum_m2 = fields.Float(string='Tum (m²)', digits=(10, 1))
    i_province_id = fields.Many2one('res.country.state', string='Tỉnh/Thành',
                                    domain="[('country_id.code', '=', 'VN')]")
    i_district = fields.Many2one('vd.district', string='Huyện/Quận')
    i_dimensions = fields.Selection([
        ('co_so_co_phep', 'Có sổ + có phép'),
        ('co_so_chua_phep', 'Có sổ - chưa cấp phép'),
        ('chua_so', 'Chưa có sổ'),
    ], string='Sổ đỏ / cấp phép')
    i_land_type = fields.Selection([
        ('lien_tho', 'Đất liền thổ'),
        ('phan_lo', 'Đất phân lô'),
        ('nong_nghiep', 'Nông nghiệp'),
    ], string='Loại đất')
    i_car_access_select = fields.Selection([
        ('co', 'Có'),
        ('khong', 'Không'),
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
        Slot dư giữ label mặc định 'Tuỳ chọn N'; view ẩn bằng optional='hide'."""
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
