"""Extend Odoo's standard crm.lead with our activity tracking + heuristic probability.

Probability formula (overrides standard):
    probability = stage.default_probability ± activity modifiers
        +10  if KH nghe máy ≤ 3 ngày
        +5   if KH nghe máy ≤ 7 ngày
        −15  if KH im ắng ≥ 30 ngày
        +5   if hẹn gọi lại trong 3 ngày tới
        −10  if no_answer_streak == 2
        −20  if no_answer_streak ≥ 3
    Clamp [0, 100]; if stage.is_won → 100; if stage.is_lost → 0.
"""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Custom fields not in standard
    callback_date = fields.Datetime(string='Hẹn gọi lại lúc', tracking=True)
    last_call_date = fields.Datetime(string='Lần gọi gần nhất', readonly=True)
    last_answered_date = fields.Datetime(string='Lần nghe máy gần nhất', readonly=True)
    no_answer_streak = fields.Integer(
        string='Số lần không nghe liên tiếp', default=0, readonly=True,
        help='Reset về 0 khi KH nghe máy.',
    )
    call_count = fields.Integer(string='Số lần gọi', default=0, readonly=True)
    call_ids = fields.One2many('stringee.call', 'lead_id', string='Lịch sử gọi')

    # Live call indicator — computed (not stored), used by form to toggle
    # Gọi/Cúp máy buttons. Cheap query: looks for any non-terminal call.
    vd_active_call_id = fields.Many2one(
        'stringee.call', string='Cuộc gọi đang hoạt động',
        compute='_compute_active_call', search='_search_active_call',
    )
    vd_in_call = fields.Boolean(compute='_compute_active_call')
    vd_active_call_state = fields.Char(compute='_compute_active_call')
    vd_active_call_answer_time = fields.Datetime(compute='_compute_active_call')
    vd_has_intake_data = fields.Boolean(compute='_compute_has_intake_data')

    # Khai thác — tổng hợp nhu cầu khách hàng (xây dựng / nhà ở)
    # `help` = kịch bản gợi ý cho NV khi gọi (hiển thị tooltip).
    vd_intake_province_id = fields.Many2one(
        'res.country.state', string='Tỉnh / Thành',
        domain="[('country_id.code', '=', 'VN')]",
        help='Hỏi: "Anh/chị xây ở tỉnh / thành nào ạ?"',
    )
    vd_intake_district = fields.Char(
        string='Huyện / Quận',
        help='Hỏi: "Khu vực huyện / quận / TP nào?"',
    )
    vd_intake_address = fields.Char(
        string='Số nhà / đường',
        help='Hỏi: "Cho em xin số nhà, tên đường, phường ạ?"',
    )
    vd_intake_timeline = fields.Selection([
        ('chuan_bi', 'Đang chuẩn bị'),
        ('1-3_thang', '1–3 tháng tới'),
        ('3-6_thang', '3–6 tháng tới'),
        ('trong_nam', 'Trong năm nay'),
        ('nam_sau', 'Năm sau'),
        ('chua_xd', 'Chưa xác định'),
    ], string='Thời gian',
        help='Hỏi: "Anh/chị dự kiến khởi công khi nào?"',
    )
    vd_intake_area = fields.Char(
        string='Diện tích',
        help='Hỏi: "Tổng diện tích đất / sàn xây dựng?". VD: 100m² hoặc 5x20m',
    )
    vd_intake_house_type = fields.Selection([
        ('mai_bang', 'Nhà mái bằng'),
        ('mai_thai', 'Nhà mái thái'),
        ('mai_nhat', 'Nhà mái nhật'),
        ('nha_pho', 'Nhà phố'),
        ('biet_thu', 'Biệt thự'),
        ('nha_ong', 'Nhà ống'),
        ('cap_4', 'Nhà cấp 4'),
        ('tum_mansard', 'Tum / Mansard'),
        ('chung_cu', 'Chung cư'),
        ('khac', 'Khác'),
    ], string='Kiểu nhà',
        help='Hỏi: "Anh/chị muốn xây kiểu nhà nào? Mái bằng, mái thái, biệt thự…?"',
    )
    vd_intake_floors = fields.Char(
        string='Số tầng',
        help='Hỏi: "Quy mô bao nhiêu tầng ạ?". VD: "2,5 tầng" hoặc "1 trệt 2 lầu"',
    )
    vd_intake_function = fields.Char(
        string='Công năng',
        help='Hỏi: "Cần bao nhiêu phòng ngủ, có cần thang máy / sân thượng không?"',
    )
    vd_intake_function_notes = fields.Text(
        string='Ghi chú công năng',
        help='Hỏi: "Có yêu cầu đặc biệt gì về phong thủy / ánh sáng / spa / phòng thờ không?"',
    )
    vd_intake_land_type = fields.Selection([
        ('lien_tho', 'Đất liền thổ'),
        ('phan_lo', 'Đất phân lô'),
        ('hon_hop', 'Đất hỗn hợp'),
        ('nong_nghiep', 'Đất nông nghiệp'),
        ('quy_hoach', 'Đất quy hoạch'),
        ('khac', 'Khác'),
    ], string='Loại đất',
        help='Hỏi: "Đất là sổ đỏ thổ cư hay nông nghiệp / phân lô?"',
    )
    vd_intake_position = fields.Selection([
        ('mt_lon', 'Mặt tiền đường lớn'),
        ('mt_nho', 'Mặt tiền đường nhỏ'),
        ('xe_tai', 'Đường xe tải'),
        ('hem_xh', 'Hẻm xe hơi'),
        ('hem_xm', 'Hẻm xe máy'),
        ('cuoi_hem', 'Cuối hẻm'),
        ('khac', 'Khác'),
    ], string='Vị trí',
        help='Hỏi: "Mặt tiền hay trong hẻm? Đường vào có thuận lợi xe vận chuyển không?"',
    )
    vd_intake_budget = fields.Selection([
        ('duoi_1ty', 'Dưới 1 tỷ'),
        ('1-3ty', '1–3 tỷ'),
        ('3-5ty', '3–5 tỷ'),
        ('5-10ty', '5–10 tỷ'),
        ('10-20ty', '10–20 tỷ'),
        ('tren_20ty', 'Trên 20 tỷ'),
        ('chua_xd', 'Chưa xác định'),
    ], string='Ngân sách dự kiến',
        help='Hỏi: "Anh/chị dự kiến đầu tư khoảng bao nhiêu?"',
    )
    vd_intake_dimensions = fields.Selection([
        ('co_so_co_phep', 'Có sổ + có cấp phép'),
        ('co_so_chua_phep', 'Có sổ - chưa cấp phép'),
        ('chua_co_so', 'Chưa có sổ'),
        ('dang_xin_phep', 'Đang xin cấp phép'),
        ('khac', 'Khác'),
    ], string='Sổ đỏ / cấp phép',
        help='Hỏi: "Đất đã có sổ đỏ chưa? Đã có giấy phép xây dựng chưa?"',
    )

    # Convenience related fields for stage flags
    stage_code = fields.Char(related='stage_id.code', store=True, index=True)
    stage_is_won = fields.Boolean(related='stage_id.is_won', store=True)
    stage_is_lost = fields.Boolean(related='stage_id.is_lost', store=True)

    # Override standard probability with our heuristic
    probability = fields.Float(
        compute='_compute_probability', store=True, readonly=False,
        copy=False, aggregator='avg', tracking=True,
    )
    automated_probability = fields.Float(  # Standard PLS field — keep but unused
        compute='_compute_probability_unused', store=False,
    )

    # Computed flags (no store — computed on read)
    is_overdue_callback = fields.Boolean(
        compute='_compute_flags', search='_search_overdue_callback',
    )
    is_today_callback = fields.Boolean(compute='_compute_flags')
    is_stale = fields.Boolean(
        compute='_compute_flags',
        help='Chưa gọi trong 14 ngày kể từ khi tạo / lần gọi cuối.',
    )

    # ---------- Computes ----------

    @api.depends(
        'stage_id', 'stage_id.default_probability', 'stage_id.is_won', 'stage_id.is_lost',
        'last_answered_date', 'no_answer_streak', 'callback_date',
    )
    def _compute_probability(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.stage_is_won:
                rec.probability = 100.0
                continue
            if rec.stage_is_lost:
                rec.probability = 0.0
                continue
            base = rec.stage_id.default_probability or 0.0

            modifier = 0.0
            if rec.last_answered_date:
                days = (now - rec.last_answered_date).days
                if days <= 3:
                    modifier += 10
                elif days <= 7:
                    modifier += 5
                elif days >= 30:
                    modifier -= 15

            if rec.callback_date and rec.callback_date >= now and (rec.callback_date - now).days <= 3:
                modifier += 5

            if rec.no_answer_streak >= 3:
                modifier -= 20
            elif rec.no_answer_streak == 2:
                modifier -= 10

            value = max(0.0, min(100.0, base + modifier))
            rec.probability = value

    def _compute_probability_unused(self):
        # Disable Odoo's PLS — we own probability.
        for rec in self:
            rec.automated_probability = 0.0

    @api.depends('callback_date', 'last_call_date', 'create_date')
    def _compute_flags(self):
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        stale_after = timedelta(days=14)
        for rec in self:
            rec.is_overdue_callback = bool(
                rec.callback_date and rec.callback_date < now
                and not rec.stage_is_won and not rec.stage_is_lost,
            )
            rec.is_today_callback = bool(
                rec.callback_date
                and fields.Datetime.context_timestamp(rec, rec.callback_date).date() == today,
            )
            ref_date = rec.last_call_date or rec.create_date
            rec.is_stale = bool(
                ref_date and (now - ref_date) > stale_after
                and not rec.stage_is_won and not rec.stage_is_lost,
            )

    _intake_data_fields = (
        'vd_intake_province_id', 'vd_intake_district', 'vd_intake_address',
        'vd_intake_position', 'vd_intake_land_type',
        'vd_intake_dimensions', 'vd_intake_area', 'vd_intake_house_type',
        'vd_intake_floors', 'vd_intake_function', 'vd_intake_function_notes',
        'vd_intake_timeline', 'vd_intake_budget',
    )

    @api.depends(*_intake_data_fields)
    def _compute_has_intake_data(self):
        for rec in self:
            rec.vd_has_intake_data = any(rec[f] for f in self._intake_data_fields)

    @api.depends('call_ids', 'call_ids.state', 'call_ids.answer_time')
    def _compute_active_call(self):
        Call = self.env['stringee.call']
        active_states = ('draft', 'initiated', 'ringing', 'answered')
        for rec in self:
            call = Call.search([
                ('lead_id', '=', rec.id),
                ('state', 'in', active_states),
            ], limit=1, order='create_date desc')
            rec.vd_active_call_id = call
            rec.vd_in_call = bool(call)
            rec.vd_active_call_state = call.state if call else False
            rec.vd_active_call_answer_time = call.answer_time if call else False

    def _search_active_call(self, operator, value):
        if operator not in ('=', '!='):
            raise ValueError("Unsupported operator")
        return [('call_ids.state', 'in', ('draft', 'initiated', 'ringing', 'answered'))]

    def _search_overdue_callback(self, operator, value):
        if operator not in ('=', '!='):
            raise ValueError("Unsupported operator")
        match = (operator == '=' and value) or (operator == '!=' and not value)
        domain = [
            ('callback_date', '<', fields.Datetime.now()),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
        ]
        return domain if match else ['!'] + domain

    # ---------- Stage transition: auto-archive on lost ----------

    def write(self, vals):
        result = super().write(vals)
        if 'stage_id' in vals:
            for rec in self:
                if rec.stage_is_lost and rec.active:
                    rec.with_context(skip_lost_archive=True).active = False
        return result

    # ---------- Actions ----------

    def action_call(self):
        """Place an outbound call AND open the intake popup so the agent can
        fill the customer brief during the conversation."""
        self.ensure_one()
        phone = self.phone or self.mobile
        if not phone:
            raise UserError(_('Khách hàng chưa có số điện thoại.'))

        Call = self.env['stringee.call']
        active = Call.search_count([
            ('user_id', '=', self.env.user.id),
            ('state', 'in', ['draft', 'initiated', 'ringing', 'answered']),
            ('create_date', '>', fields.Datetime.now() - timedelta(seconds=30)),
        ])
        if active:
            raise UserError(_(
                'Bạn đang có 1 cuộc gọi chưa kết thúc. '
                'Cúp máy cuộc cũ trước khi gọi tiếp.',
            ))

        call = Call.make_call(callee_number=phone, user_id=self.env.user.id)
        call.write({'lead_id': self.id})

        intake_view = self.env.ref(
            'vd_crm_lead.view_crm_lead_intake_popup', raise_if_not_found=False,
        )
        if not intake_view:
            return True
        return {
            'type': 'ir.actions.act_window',
            'name': _('Khai thác — %s') % (self.name or ''),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'views': [(intake_view.id, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }

    def action_hangup_active(self):
        """End the lead's currently active call. Stays on the same form."""
        self.ensure_one()
        if self.vd_active_call_id:
            self.vd_active_call_id.action_hangup()
        return True

    def action_view_calls(self):
        """Open call history for this lead in a modal dialog."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lịch sử cuộc gọi — %s') % (self.name or ''),
            'res_model': 'stringee.call',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'target': 'new',
            'context': {'default_lead_id': self.id, 'create': False},
        }

    # ---------- Dashboard data ----------

    @api.model
    def _dashboard_is_manager(self):
        # Sales Manager (or technical admin) sees every salesperson's leads.
        return (
            self.env.user.has_group('sales_team.group_sale_manager')
            or self.env.user.has_group('base.group_system')
        )

    @api.model
    def _dashboard_resolve_scope(self, user_id):
        """Return (scope_user, scope_domain_lead, scope_domain_call).

        - Non-manager: always scoped to themselves regardless of `user_id`.
        - Manager + user_id falsy/'all': no user filter (all salespeople).
        - Manager + user_id int: scoped to that user.
        """
        is_manager = self._dashboard_is_manager()
        if not is_manager:
            user = self.env.user
            return user, [('user_id', '=', user.id)], [('user_id', '=', user.id)]
        if not user_id or user_id == 'all':
            return None, [], []
        target = self.env['res.users'].browse(int(user_id))
        return target, [('user_id', '=', target.id)], [('user_id', '=', target.id)]

    @api.model
    def dashboard_users(self):
        """List salespeople for the manager dropdown. Returns [] for non-managers."""
        if not self._dashboard_is_manager():
            return []
        # Distinct users that own at least one lead — keeps dropdown short
        # even when there are many inactive accounts in the system.
        self.env.cr.execute("""
            SELECT DISTINCT u.id, COALESCE(p.name, u.login) AS name
            FROM res_users u
            JOIN res_partner p ON p.id = u.partner_id
            JOIN crm_lead l ON l.user_id = u.id
            WHERE u.active = TRUE
            ORDER BY name
        """)
        return [{'id': r[0], 'name': r[1]} for r in self.env.cr.fetchall()]

    @api.model
    def dashboard_data(self, user_id=None):
        """Single-payload data for the OWL dashboard."""
        scope_user, lead_scope, call_scope = self._dashboard_resolve_scope(user_id)
        is_manager = self._dashboard_is_manager()

        # Manager view crosses record rules (e.g. "Sales: own documents only").
        # `sudo()` is safe here because _dashboard_resolve_scope already gates
        # who can pass `user_id`/`'all'` — non-managers are forced to their own scope.
        Lead = self.sudo() if is_manager else self
        Call = self.env['stringee.call'].sudo() if is_manager else self.env['stringee.call']

        Stage = self.env['crm.stage']
        stages = Stage.search([], order='sequence')
        stage_payload = []
        for st in stages:
            count = Lead.search_count(lead_scope + [('stage_id', '=', st.id)])
            stage_payload.append({
                'id': st.id,
                'code': st.code or '',
                'name': st.name,
                'count': count,
                'is_won': st.is_won,
                'is_lost': st.is_lost,
                'default_probability': st.default_probability,
            })

        today = fields.Date.context_today(self)
        today_start = fields.Datetime.to_datetime(today)
        today_end = today_start + timedelta(days=1)
        now = fields.Datetime.now()
        stale_threshold = now - timedelta(days=14)
        active_only = [('stage_is_won', '=', False), ('stage_is_lost', '=', False)]

        call_today_domain = call_scope + [
            ('create_date', '>=', today_start),
            ('create_date', '<', today_end),
        ]

        kpi = {
            'total': Lead.search_count(lead_scope),
            'new_today': Lead.search_count(lead_scope + [
                ('create_date', '>=', today_start),
                ('create_date', '<', today_end),
            ]),
            'callback_today': Lead.search_count(lead_scope + active_only + [
                ('callback_date', '>=', today_start),
                ('callback_date', '<', today_end),
            ]),
            'calls_today': Call.search_count(call_today_domain),
            'calls_answered_today': Call.search_count(
                call_today_domain + [('state', 'in', ['answered', 'ended']), ('duration', '>', 0)],
            ),
            'recordings_today': Call.search_count(
                call_today_domain + [('recording_attachment_id', '!=', False)],
            ),
        }

        errors = {
            'overdue_callback': Lead.search_count(lead_scope + active_only + [
                ('callback_date', '<', now),
            ]),
            'new_not_called': Lead.search_count(lead_scope + [
                ('stage_id.code', '=', 'new'),
                ('call_count', '=', 0),
            ]),
            'potential_no_quote': Lead.search_count(lead_scope + [
                ('stage_id.code', '=', 'potential'),
            ]),
            'stale': (
                Lead.search_count(lead_scope + active_only + [
                    ('last_call_date', '<', stale_threshold),
                ])
                + Lead.search_count(lead_scope + active_only + [
                    ('last_call_date', '=', False),
                    ('create_date', '<', stale_threshold),
                ])
            ),
        }

        if scope_user:
            user_payload = {'id': scope_user.id, 'name': scope_user.name}
        else:
            user_payload = {'id': 0, 'name': 'Tất cả nhân viên'}

        return {
            'user': user_payload,
            'is_manager': is_manager,
            'selected_user_id': scope_user.id if scope_user else 0,
            'kpi': kpi,
            'errors': errors,
            'stages': stage_payload,
        }

    @api.model
    def dashboard_leads(self, stage_id, user_id=None, limit=80):
        _scope_user, lead_scope, _call_scope = self._dashboard_resolve_scope(user_id)
        Lead = self.sudo() if self._dashboard_is_manager() else self
        leads = Lead.search(
            lead_scope + [('stage_id', '=', stage_id)],
            limit=limit, order='probability desc, callback_date asc, create_date desc',
        )
        return [{
            'id': l.id,
            'name': l.name,
            'phone': l.phone or l.mobile or '',
            'probability': round(l.probability, 1),
            'callback_date': fields.Datetime.to_string(l.callback_date) if l.callback_date else '',
            'last_call_date': fields.Datetime.to_string(l.last_call_date) if l.last_call_date else '',
            'no_answer_streak': l.no_answer_streak,
            'is_overdue_callback': l.is_overdue_callback,
            'is_today_callback': l.is_today_callback,
            'is_stale': l.is_stale,
            'priority': l.priority,
            'expected_revenue': l.expected_revenue,
            'salesperson': l.user_id.name or '',
        } for l in leads]
