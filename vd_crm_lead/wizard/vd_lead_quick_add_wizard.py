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

            lead = Lead.with_context(vd_skip_reassign_check=True).create(vals)
            created |= lead

            # Lưu giá trị các cột tuỳ chọn (extra_1..5) vào vd.lead.custom.value
            extra_vals = [
                line.extra_1, line.extra_2, line.extra_3, line.extra_4, line.extra_5,
            ]
            if any(extra_vals):
                CFs = self.env['vd.intake.custom.field'].sudo().search(
                    [('active', '=', True)], order='sequence, id', limit=5,
                )
                Value = self.env['vd.lead.custom.value'].sudo()
                for idx, val in enumerate(extra_vals):
                    if not val or idx >= len(CFs):
                        continue
                    cf = CFs[idx]
                    existing = Value.search([
                        ('lead_id', '=', lead.id), ('field_id', '=', cf.id),
                    ], limit=1)
                    if existing:
                        existing.value = val
                    else:
                        Value.create({
                            'lead_id': lead.id,
                            'field_id': cf.id,
                            'value': val,
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

    # 5 cột tuỳ chọn — admin tự đặt tên qua "+ Thêm trường" (vd.intake.custom.field).
    # Label hiển thị được override dynamic trong fields_get() dựa trên config.
    extra_1 = fields.Char(string='Tuỳ chọn 1')
    extra_2 = fields.Char(string='Tuỳ chọn 2')
    extra_3 = fields.Char(string='Tuỳ chọn 3')
    extra_4 = fields.Char(string='Tuỳ chọn 4')
    extra_5 = fields.Char(string='Tuỳ chọn 5')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override label các cột extra_N theo cấu hình admin (sequence asc).
        Nếu admin cấu hình 2 trường, cột 1+2 mang tên đó, 3-5 còn label mặc định."""
        res = super().fields_get(allfields, attributes)
        try:
            cfs = self.env['vd.intake.custom.field'].sudo().search(
                [('active', '=', True)], order='sequence, id', limit=5,
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
