import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

VINADUY_TEAM_NAMES = ['HCM1', 'HCM2', 'HCM3', 'HN']
PARAM_AUTO_ASSIGN = 'vinaduy_crm.auto_assign_enabled'
PARAM_LAST_USER = 'vinaduy_crm.last_assigned_user_id'


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _order = 'create_date desc, id desc'

    vinaduy_source_id = fields.Many2one(
        'vinaduy.crm.source',
        string='Nguồn data',
        tracking=True,
    )
    vinaduy_source_code = fields.Char(
        related='vinaduy_source_id.code',
        readonly=True,
    )
    vd_source_other = fields.Char(
        string='Mô tả nguồn data khác',
        help='Nhập tên nguồn khi chọn "Khác"',
    )

    project_type = fields.Selection(
        selection=[
            ('nha_pho', 'Nhà phố'),
            ('biet_thu', 'Biệt thự'),
            ('van_phong', 'Văn phòng'),
            ('nha_xuong', 'Nhà xưởng'),
            ('khac', 'Khác'),
        ],
        string='Loại công trình',
        tracking=True,
    )

    # ============ TỔNG HỢP NHU CẦU KHÁCH HÀNG (11 fields) ============
    vd_address = fields.Char(string='Địa chỉ', tracking=True)
    vd_timeframe = fields.Selection(
        selection=[
            ('under_3m', 'Dưới 3 tháng'),
            ('3_to_6m', '3 - 6 tháng'),
            ('6_to_12m', '6 - 12 tháng'),
            ('this_year', 'Trong năm nay'),
            ('next_year', 'Năm sau'),
            ('undecided', 'Chưa xác định'),
        ],
        string='Thời gian dự kiến xây',
        tracking=True,
    )
    vd_area = fields.Char(
        string='Diện tích',
        help='Vd: 5x10, 6x15, 100m²',
        tracking=True,
    )
    vd_house_type = fields.Selection(
        selection=[
            ('mai_bang', 'Nhà mái bằng'),
            ('mai_thai', 'Nhà mái thái'),
            ('biet_thu', 'Biệt thự'),
            ('nha_pho', 'Nhà phố'),
            ('nha_cap_4', 'Nhà cấp 4'),
            ('khac', 'Khác'),
        ],
        string='Kiểu nhà',
        tracking=True,
    )
    vd_floors = fields.Float(
        string='Số tầng',
        digits=(3, 1),
        help='Vd: 2 (cho 2 tầng), 3.5 (cho 3,5 tầng)',
        tracking=True,
    )
    vd_functions = fields.Text(
        string='Công năng',
        help='Vd: 1 Khách - 1 Bếp - 3 Phòng Ngủ - 2 WC - 1 Phòng thờ',
    )
    vd_function_notes = fields.Text(string='Ghi chú công năng')
    vd_land_type = fields.Selection(
        selection=[
            ('lien_tho', 'Đất liền thổ'),
            ('nong_nghiep', 'Đất nông nghiệp'),
            ('thanh_pho', 'Đất thành phố'),
            ('khac', 'Khác'),
        ],
        string='Loại đất',
        tracking=True,
    )
    vd_position = fields.Char(
        string='Vị trí',
        help='Vd: ĐƯỜNG XE TẢI - Có chỗ tập kết vật tư',
    )
    vd_budget = fields.Monetary(
        string='Ngân sách dự kiến',
        currency_field='company_currency',
        help='Số tiền VND. Vd: 1000000000 = 1 tỷ',
        tracking=True,
    )
    vd_land_cert = fields.Selection(
        selection=[
            ('co_so_co_phep', 'CÓ SỔ - Có làm cấp phép'),
            ('co_so_chua_phep', 'CÓ SỔ - Chưa làm cấp phép'),
            ('khong_so', 'KHÔNG CÓ SỔ'),
            ('dang_lam', 'Đang làm sổ'),
        ],
        string='Sổ đỏ',
        tracking=True,
    )

    vd_callback_date = fields.Datetime(
        string='Ngày gọi lại',
        tracking=True,
        help='Lịch hẹn gọi lại khách hàng',
    )

    vd_close_reason = fields.Char(
        string='Lý do đóng lead',
        tracking=True,
        help='Bắt buộc nhập khi đóng lead (Khách không có nhu cầu / Khách hủy)',
    )

    vd_stage_history_ids = fields.One2many(
        'mail.tracking.value',
        compute='_compute_vd_stage_history',
        string='Hành trình chuyển trạng thái',
    )

    checklist_pending_ids = fields.One2many(
        'vinaduy.crm.checklist.item',
        compute='_compute_checklist_pending',
        string='Việc cần làm (chưa xong)',
    )

    vd_stage_badge_html = fields.Html(
        compute='_compute_vd_stage_badge_html',
        sanitize=False,
        string='Trạng thái hiện tại',
    )

    @api.depends('stage_id', 'active', 'lost_reason_id')
    def _compute_vd_stage_badge_html(self):
        STAGE_COLORS = {
            'Khách chưa gán': '#6c757d',       # xám
            'Khách mới': '#0dcaf0',            # xanh lam nhạt
            'Có tiềm năng': '#0d6efd',         # xanh dương
            'Báo giá': '#fd7e14',              # cam
            'Tiềm năng đàm phán': '#6f42c1',   # tím
            'Tiềm năng hợp đồng': '#0a58ca',   # xanh đậm
            'Tiềm năng gấp': '#dc3545',        # ĐỎ
            'Chốt': '#198754',                 # XANH LÁ
        }
        for lead in self:
            if not lead.active:
                # Lead đã đóng — show theo lost_reason
                no_need = self.env.ref('vinaduy_crm.lost_reason_not_potential', raise_if_not_found=False)
                cancelled = self.env.ref('vinaduy_crm.lost_reason_cancelled', raise_if_not_found=False)
                if no_need and lead.lost_reason_id == no_need:
                    color, label = '#fd7e14', 'KHÁCH KHÔNG CÓ NHU CẦU'  # cam
                elif cancelled and lead.lost_reason_id == cancelled:
                    color, label = '#212529', 'ĐÃ HỦY'  # đen
                else:
                    color, label = '#6c757d', 'ĐÃ ĐÓNG'
            elif lead.stage_id:
                stage_name = lead.stage_id.name
                color = STAGE_COLORS.get(stage_name, '#6c757d')
                label = stage_name.upper()
            else:
                lead.vd_stage_badge_html = ''
                continue
            lead.vd_stage_badge_html = (
                f'<div style="background-color:{color};color:white;'
                f'padding:10px 20px;border-radius:8px;font-weight:bold;'
                f'display:inline-block;font-size:16px;letter-spacing:1px;'
                f'box-shadow:0 2px 4px rgba(0,0,0,0.15);margin-bottom:8px;">'
                f'📍 {label}</div>'
            )

    @api.depends('message_ids')
    def _compute_vd_stage_history(self):
        # sudo() để sale user không cần quyền ir.model.fields / mail.tracking.value
        Tracking = self.env['mail.tracking.value'].sudo()
        for lead in self:
            tracking = Tracking.search([
                ('mail_message_id.model', '=', 'crm.lead'),
                ('mail_message_id.res_id', '=', lead.id),
                ('field_id.name', '=', 'stage_id'),
            ], order='id desc')
            lead.vd_stage_history_ids = tracking

    @api.depends('stage_id', 'checklist_item_ids', 'checklist_item_ids.done',
                 'checklist_item_ids.stage_id')
    def _compute_checklist_pending(self):
        for lead in self:
            lead.checklist_pending_ids = lead.checklist_item_ids.filtered(
                lambda i: i.stage_id == lead.stage_id and not i.done
            )

    # Sub-stage for "Khách mới"
    vd_new_substage = fields.Selection(
        selection=[
            ('no_need', 'Khách không có nhu cầu'),
            ('potential', 'Khách có tiềm năng'),
        ],
        string='Phân loại khách mới',
        tracking=True,
        copy=False,
    )

    omicall_call_count = fields.Integer(
        string='Số cuộc gọi OMICall',
        default=0,
        readonly=True,
    )

    last_omicall_date = fields.Datetime(
        string='Cuộc gọi OMICall gần nhất',
        readonly=True,
    )

    stage_entry_date = fields.Datetime(
        string='Ngày vào stage hiện tại',
        readonly=True,
        copy=False,
        index=True,
    )
    sla_deadline = fields.Datetime(
        string='Deadline SLA',
        compute='_compute_sla', store=True,
    )
    sla_overdue = fields.Boolean(
        string='Quá hạn SLA',
        compute='_compute_sla', store=True,
        help='True khi lead đã ở stage hiện tại quá số ngày SLA cho phép',
    )
    sla_days_remaining = fields.Float(
        string='Còn (ngày)',
        compute='_compute_sla',
        help='Số ngày còn lại trước khi quá hạn SLA (âm = đã quá)',
    )

    checklist_item_ids = fields.One2many(
        'vinaduy.crm.checklist.item', 'lead_id', string='Checklist',
    )
    checklist_progress = fields.Char(
        compute='_compute_checklist_progress', string='Tiến độ checklist',
    )
    checklist_required_done = fields.Boolean(
        compute='_compute_checklist_progress', string='Checklist bắt buộc đã xong',
        store=True,
    )

    @api.constrains('phone')
    def _check_vd_phone(self):
        for lead in self:
            if not lead.phone:
                continue
            digits = re.sub(r'\D', '', lead.phone)
            if not re.match(r'^(0\d{9}|84\d{9,10})$', digits):
                raise ValidationError(_(
                    'Số điện thoại "%s" không hợp lệ.\n\n'
                    'SĐT phải là:\n'
                    '  • 10 chữ số bắt đầu bằng 0 (vd: 0901234567)\n'
                    '  • Hoặc 11-12 chữ số bắt đầu 84 (vd: 84901234567)',
                    lead.phone
                ))

    @api.onchange('phone')
    def _onchange_vd_phone_format(self):
        """Tự format SĐT với khoảng trắng dễ đọc: 0901 234 567"""
        if not self.phone:
            return
        digits = re.sub(r'\D', '', self.phone)
        if len(digits) == 10 and digits.startswith('0'):
            self.phone = f"{digits[:4]} {digits[4:7]} {digits[7:]}"
        elif digits.startswith('84') and len(digits) in (11, 12):
            self.phone = f"+84 {digits[2:5]} {digits[5:8]} {digits[8:]}"

    @api.depends('stage_entry_date', 'stage_id', 'stage_id.sla_days')
    def _compute_sla(self):
        now = fields.Datetime.now()
        for lead in self:
            if (
                not lead.stage_id
                or not lead.stage_id.sla_days
                or not lead.stage_entry_date
                or lead.stage_id.is_won
                or not lead.active
            ):
                lead.sla_deadline = False
                lead.sla_overdue = False
                lead.sla_days_remaining = 0.0
                continue
            deadline = lead.stage_entry_date + timedelta(days=lead.stage_id.sla_days)
            lead.sla_deadline = deadline
            lead.sla_overdue = now > deadline
            lead.sla_days_remaining = (deadline - now).total_seconds() / 86400.0

    @api.depends(
        'stage_id',
        'checklist_item_ids.done',
        'checklist_item_ids.required',
        'checklist_item_ids.stage_id',
    )
    def _compute_checklist_progress(self):
        for lead in self:
            items = lead.checklist_item_ids.filtered(
                lambda i: i.stage_id == lead.stage_id
            )
            total = len(items)
            done = len(items.filtered('done'))
            if total:
                lead.checklist_progress = f'{done}/{total}'
            else:
                lead.checklist_progress = '—'
            required_items = items.filtered('required')
            lead.checklist_required_done = (
                all(i.done for i in required_items) if required_items else True
            )

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        # Default stage cho lead mới khi không có stage_id (vd: từ StringeeX webhook)
        default_stage = self.env.ref('vinaduy_crm.stage_new', raise_if_not_found=False)
        for vals in vals_list:
            if not vals.get('stage_id') and default_stage:
                vals['stage_id'] = default_stage.id
            if not vals.get('user_id'):
                next_user = self._vinaduy_pick_next_round_robin_user()
                if next_user:
                    vals['user_id'] = next_user.id
            if vals.get('stage_id') and not vals.get('stage_entry_date'):
                vals['stage_entry_date'] = now
        leads = super().create(vals_list)
        for lead in leads:
            lead._vinaduy_sync_checklist_items()
            lead._vinaduy_auto_tick_checklist(None)
        return leads

    def _vinaduy_auto_tick_checklist(self, vals=None):
        """Auto-tick checklist item khi field tương ứng đã có giá trị."""
        self.ensure_one()
        items = self.checklist_item_ids.filtered(
            lambda i: not i.done and i.template_id.field_name
        )
        for item in items:
            fname = item.template_id.field_name
            if hasattr(self, fname) and self[fname]:
                item.write({'done': True})

    def write(self, vals):
        # Validate stage transition before saving (skip for system admin)
        is_admin = self.env.user.has_group('base.group_system')
        backward_messages = []
        if 'stage_id' in vals and not is_admin and not self.env.context.get('vinaduy_skip_stage_check'):
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            for lead in self:
                msg = lead._vinaduy_validate_stage_transition(new_stage)
                if msg:
                    backward_messages.append((lead.id, msg))
        if 'stage_id' in vals and 'stage_entry_date' not in vals:
            vals['stage_entry_date'] = fields.Datetime.now()
        res = super().write(vals)
        if 'stage_id' in vals:
            for lead in self:
                lead._vinaduy_sync_checklist_items()
        # Auto-tick checklist items khi field tương ứng có giá trị
        for lead in self:
            lead._vinaduy_auto_tick_checklist(vals)
        for lead_id, msg in backward_messages:
            self.browse(lead_id).message_post(
                body=msg,
                subtype_xmlid='mail.mt_note',
            )
        return res

    def _vinaduy_validate_stage_transition(self, new_stage):
        """Validate khi chuyển stage. Trả về message để post chatter (nếu lùi stage), hoặc raise UserError."""
        self.ensure_one()
        old_stage = self.stage_id
        if not old_stage or not new_stage or old_stage == new_stage:
            return None

        # "Khách không có nhu cầu" / "Chốt" có thể chuyển từ bất kỳ stage nào
        no_need = self.env.ref('vinaduy_crm.stage_no_need', raise_if_not_found=False)
        if no_need and new_stage == no_need:
            return None

        all_stages = self.env['crm.stage'].search([], order='sequence')
        idx = {s.id: i for i, s in enumerate(all_stages)}
        old_idx = idx.get(old_stage.id, -1)
        new_idx = idx.get(new_stage.id, -1)
        if old_idx < 0 or new_idx < 0:
            return None

        # Lùi stage → CẤM (phải gửi yêu cầu lùi cho admin)
        if new_idx < old_idx:
            raise UserError(_(
                'KHÔNG được tự ý lùi trạng thái.\n\n'
                'Lead đang ở "%(old)s", không thể lùi về "%(new)s".\n\n'
                'Nếu cần lùi → Vào lead → bấm nút "🔄 Yêu cầu lùi trạng thái" '
                'để gửi yêu cầu cho admin duyệt (có lý do).',
                old=old_stage.display_name,
                new=new_stage.display_name,
            ))

        # Nhảy >1 stage forward → block
        if new_idx > old_idx + 1:
            raise UserError(_(
                'Không được nhảy quá 1 stage. Lead đang ở "%(old)s", '
                'phải chuyển sang "%(next)s" trước (không thể nhảy thẳng tới "%(new)s").',
                old=old_stage.display_name,
                next=all_stages[old_idx + 1].display_name,
                new=new_stage.display_name,
            ))

        # Tiến 1 stage → kiểm tra checklist required của stage CŨ phải xong
        items = self.checklist_item_ids.filtered(
            lambda i: i.stage_id == old_stage and i.required
        )
        incomplete = items.filtered(lambda i: not i.done)
        if incomplete:
            names = '\n'.join(f'  • {i.name}' for i in incomplete)
            raise UserError(_(
                'Chưa thể chuyển sang "%(new)s".\n\n'
                'Cần hoàn thành các việc bắt buộc ở stage "%(old)s":\n%(items)s',
                new=new_stage.display_name,
                old=old_stage.display_name,
                items=names,
            ))
        return None

    # ============ ACTION: Sub-stage cho "Khách mới" ============
    def action_vinaduy_mark_no_need(self):
        """Khách không có nhu cầu → chuyển sang stage 'Khách không có nhu cầu'"""
        self.ensure_one()
        if not self.vd_close_reason:
            raise UserError(_(
                'Vui lòng nhập "Lý do đóng lead" trước khi đánh dấu không có nhu cầu.'
            ))
        stage = self.env.ref('vinaduy_crm.stage_no_need', raise_if_not_found=False)
        if not stage:
            raise UserError(_('Không tìm thấy stage "Khách không có nhu cầu".'))
        self.with_context(vinaduy_skip_stage_check=True).write({
            'vd_new_substage': 'no_need',
            'stage_id': stage.id,
        })
        self.message_post(
            body='❌ <b>Khách không có nhu cầu</b> — Lý do: <i>%s</i>' % self.vd_close_reason,
            subtype_xmlid='mail.mt_note',
        )
        return {
            'effect': {
                'fadeout': 'medium',
                'message': '❌ Đã đóng — Khách không có nhu cầu',
                'type': 'rainbow_man',
                'img_url': '/vinaduy_crm/static/img/sad.svg',
            }
        }

    def action_vinaduy_mark_cancelled(self):
        """Đánh dấu lead bị hủy (thường ở stage 'Tiềm năng gấp')."""
        self.ensure_one()
        if not self.vd_close_reason:
            raise UserError(_(
                'Vui lòng nhập "Lý do đóng lead" trước khi đánh dấu khách hủy.'
            ))
        reason = self.env.ref('vinaduy_crm.lost_reason_cancelled', raise_if_not_found=False)
        vals = {'active': False, 'probability': 0}
        if reason:
            vals['lost_reason_id'] = reason.id
        self.write(vals)
        self.message_post(
            body='🚫 <b>Khách hủy</b> — Lý do: <i>%s</i>' % self.vd_close_reason,
            subtype_xmlid='mail.mt_note',
        )
        return {
            'effect': {
                'fadeout': 'medium',
                'message': '🚫 Đã hủy lead',
                'type': 'rainbow_man',
                'img_url': '/vinaduy_crm/static/img/sad.svg',
            }
        }

    def action_vinaduy_save_and_advance(self):
        """Generic: lưu form + chuyển sang stage tiếp theo (sau khi validate checklist)."""
        self.ensure_one()
        # Force reload checklist từ DB (form vừa save)
        self.invalidate_recordset(['checklist_item_ids'])
        self.checklist_item_ids.invalidate_recordset(['done'])

        all_stages = self.env['crm.stage'].search([], order='sequence')
        if not self.stage_id or self.stage_id not in all_stages:
            raise UserError(_('Lead chưa có stage hoặc stage không hợp lệ.'))
        idx = list(all_stages.ids).index(self.stage_id.id)
        if idx >= len(all_stages) - 1:
            raise UserError(_('Đã ở stage cuối "%s", không thể chuyển tiếp.', self.stage_id.name))
        next_stage = all_stages[idx + 1]

        # Validate checklist của stage hiện tại
        items = self.checklist_item_ids.filtered(
            lambda i: i.stage_id == self.stage_id and i.required
        )
        incomplete = items.filtered(lambda i: not i.done)
        if incomplete:
            names = '\n'.join(f'  • {i.name}' for i in incomplete)
            raise UserError(_(
                'Chưa thể chuyển sang "%(next)s".\n\n'
                'Cần hoàn thành các việc bắt buộc:\n%(items)s',
                next=next_stage.name, items=names,
            ))

        # Skip validation trong write (đã validate ở trên)
        self.with_context(vinaduy_skip_stage_check=True).write({'stage_id': next_stage.id})

        # Nếu chuyển sang stage WON (Chốt) → fire rainbowman 🌈
        if next_stage.is_won:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': '🎉 Chốt thành công!',
                    'type': 'rainbow_man',
                }
            }
        return True

    def action_vinaduy_mark_potential(self):
        """Khách có tiềm năng → chuyển sang stage 'Có tiềm năng'"""
        self.ensure_one()
        next_stage = self.env.ref('vinaduy_crm.stage_potential', raise_if_not_found=False)
        if not next_stage:
            raise UserError(_('Không tìm thấy stage "Có tiềm năng".'))

        # Force reload checklist từ DB (form vừa save xong)
        self.invalidate_recordset(['checklist_item_ids'])
        self.checklist_item_ids.invalidate_recordset(['done'])

        items = self.checklist_item_ids.filtered(
            lambda i: i.stage_id == self.stage_id and i.required
        )
        incomplete = items.filtered(lambda i: not i.done)
        if incomplete:
            names = '\n'.join(f'  • {i.name}' for i in incomplete)
            raise UserError(_(
                'Chưa thể chuyển sang "Có tiềm năng".\n\n'
                'Cần hoàn thành các việc bắt buộc:\n%s', names
            ))

        # Bypass write() validation (đã validate ở trên)
        self.with_context(vinaduy_skip_stage_check=True).write({
            'vd_new_substage': 'potential',
            'stage_id': next_stage.id,
        })
        return True

    @api.model
    def action_vinaduy_resync_all_checklists(self):
        """Public action: re-sync checklist items cho tất cả lead theo template hiện tại."""
        leads = self.search([])
        for lead in leads:
            lead._vinaduy_sync_checklist_items()
        return len(leads)

    def _vinaduy_sync_checklist_items(self):
        """Tạo checklist items cho stage hiện tại + xoá items của stage cũ."""
        self.ensure_one()
        if not self.stage_id:
            return
        # XÓA items của stage khác (giữ slate sạch cho stage hiện tại)
        old_items = self.checklist_item_ids.filtered(
            lambda i: i.stage_id != self.stage_id
        )
        if old_items:
            old_items.unlink()
        # THÊM items mới cho stage hiện tại
        existing_template_ids = self.checklist_item_ids.mapped('template_id').ids
        new_templates = self.env['vinaduy.crm.checklist.template'].search([
            ('stage_id', '=', self.stage_id.id),
            ('active', '=', True),
            ('id', 'not in', existing_template_ids),
        ])
        for tpl in new_templates:
            self.env['vinaduy.crm.checklist.item'].create({
                'lead_id': self.id,
                'template_id': tpl.id,
            })

    @api.model
    def _vinaduy_cron_check_sla(self):
        """Cron daily: tìm leads quá hạn SLA → tạo activity cảnh báo + post chatter."""
        overdue = self.search([
            ('sla_overdue', '=', True),
            ('active', '=', True),
            ('user_id', '!=', False),
            ('stage_id.is_won', '=', False),
        ])
        if not overdue:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        Activity = self.env['mail.activity'].sudo()
        model_id = self.env.ref('crm.model_crm_lead').id
        today = fields.Date.context_today(self)
        for lead in overdue:
            existing = Activity.search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('user_id', '=', lead.user_id.id),
                ('summary', '=like', '[SLA]%'),
                ('date_deadline', '=', today),
            ], limit=1)
            if existing:
                continue
            overdue_days = abs(int(lead.sla_days_remaining))
            Activity.create({
                'res_model_id': model_id,
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'user_id': lead.user_id.id,
                'summary': f'[SLA] Quá hạn {overdue_days} ngày ở "{lead.stage_id.display_name}"',
                'note': (
                    f'Lead <b>{lead.name}</b> đã ở stage <b>{lead.stage_id.display_name}</b> '
                    f'quá {overdue_days} ngày so với SLA ({lead.stage_id.sla_days} ngày).'
                ),
                'date_deadline': today,
                'activity_type_id': activity_type.id if activity_type else False,
            })
            lead.message_post(
                body=_(
                    '⚠️ <b>SLA QUÁ HẠN</b>: lead đã ở stage "%(stage)s" quá %(d)s ngày '
                    '(SLA cho phép %(sla)s ngày).',
                    stage=lead.stage_id.display_name,
                    d=overdue_days,
                    sla=lead.stage_id.sla_days,
                ),
                subtype_xmlid='mail.mt_note',
            )

    @api.model
    def _vinaduy_get_round_robin_users(self):
        members = self.env['crm.team.member'].search([
            ('crm_team_id.name', 'in', VINADUY_TEAM_NAMES),
            ('user_id.active', '=', True),
        ])
        return members.mapped('user_id').sorted(key=lambda u: u.id)

    @api.model
    def _vinaduy_pick_next_round_robin_user(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(PARAM_AUTO_ASSIGN, 'True') != 'True':
            return False
        users = self._vinaduy_get_round_robin_users()
        if not users:
            return False
        last_id = int(ICP.get_param(PARAM_LAST_USER, '0'))
        user_ids = users.ids
        try:
            idx = (user_ids.index(last_id) + 1) % len(user_ids)
        except ValueError:
            idx = 0
        next_user = users[idx]
        ICP.set_param(PARAM_LAST_USER, str(next_user.id))
        return next_user
