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
    vd_has_intake_data = fields.Boolean(compute='_compute_has_intake_data')

    # Khai thác — tổng hợp nhu cầu khách hàng (xây dựng / nhà ở)
    vd_intake_address = fields.Char(string='Địa chỉ')
    vd_intake_timeline = fields.Char(string='Thời gian')
    vd_intake_area = fields.Char(string='Diện tích', help='vd: 100m2 hoặc 5x20m')
    vd_intake_house_type = fields.Selection([
        ('nha_pho', 'Nhà phố'),
        ('biet_thu', 'Biệt thự'),
        ('chung_cu', 'Chung cư'),
        ('cap_4', 'Nhà cấp 4'),
        ('khac', 'Khác'),
    ], string='Kiểu nhà')
    vd_intake_floors = fields.Integer(string='Số tầng')
    vd_intake_function = fields.Char(string='Công năng', help='vd: 3PN + 2WC + bếp + phòng thờ')
    vd_intake_function_notes = fields.Text(string='Ghi chú công năng')
    vd_intake_land_type = fields.Selection([
        ('dat_o', 'Đất ở'),
        ('dat_thuong_mai', 'Đất thương mại / dịch vụ'),
        ('dat_hon_hop', 'Đất hỗn hợp'),
        ('dat_khac', 'Khác'),
    ], string='Loại đất')
    vd_intake_position = fields.Char(string='Vị trí', help='vd: Mặt tiền đường, hẻm xe hơi, …')
    vd_intake_budget = fields.Char(string='Ngân sách dự kiến', help='vd: 5–7 tỷ')
    vd_intake_dimensions = fields.Char(string='Số đo', help='vd: 5m x 20m')

    # Convenience related fields for stage flags
    stage_code = fields.Char(related='stage_id.code', store=True, index=True)
    stage_is_won = fields.Boolean(related='stage_id.is_won', store=True)
    stage_is_lost = fields.Boolean(related='stage_id.is_lost', store=True)

    # Override standard probability with our heuristic
    probability = fields.Float(
        compute='_compute_probability', store=True, readonly=False,
        copy=False, group_operator='avg', tracking=True,
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
        'vd_intake_address', 'vd_intake_position', 'vd_intake_land_type',
        'vd_intake_dimensions', 'vd_intake_area', 'vd_intake_house_type',
        'vd_intake_floors', 'vd_intake_function', 'vd_intake_function_notes',
        'vd_intake_timeline', 'vd_intake_budget',
    )

    @api.depends(*_intake_data_fields)
    def _compute_has_intake_data(self):
        for rec in self:
            rec.vd_has_intake_data = any(rec[f] for f in self._intake_data_fields)

    @api.depends('call_ids', 'call_ids.state')
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
        """Place an outbound call. Stays on the same form (no modal/notification)."""
        self.ensure_one()
        phone = self.phone or self.mobile
        if not phone:
            raise UserError(_('Khách hàng chưa có số điện thoại.'))

        Call = self.env['stringee.call']
        # Block accidental double-clicks: refuse if same user has a still-live
        # call started in the last 30 seconds.
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
        # Reload current form so vd_in_call flips to True and the UI swaps
        # the Gọi button for the Cúp máy button.
        return True

    def action_hangup_active(self):
        """End the lead's currently active call. Stays on the same form."""
        self.ensure_one()
        if self.vd_active_call_id:
            self.vd_active_call_id.action_hangup()
        return True

    # ---------- Dashboard data ----------

    @api.model
    def dashboard_data(self, user_id=None):
        """Single-payload data for the OWL dashboard."""
        user = self.env['res.users'].browse(user_id) if user_id else self.env.user
        domain_user = [('user_id', '=', user.id)]

        Stage = self.env['crm.stage']
        stages = Stage.search([], order='sequence')
        stage_payload = []
        for st in stages:
            count = self.search_count(domain_user + [('stage_id', '=', st.id)])
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

        Call = self.env['stringee.call']
        call_today_domain = [
            ('user_id', '=', user.id),
            ('create_date', '>=', today_start),
            ('create_date', '<', today_end),
        ]

        kpi = {
            'total': self.search_count(domain_user),
            'new_today': self.search_count(domain_user + [
                ('create_date', '>=', today_start),
                ('create_date', '<', today_end),
            ]),
            'callback_today': self.search_count(domain_user + active_only + [
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
            'overdue_callback': self.search_count(domain_user + active_only + [
                ('callback_date', '<', now),
            ]),
            'new_not_called': self.search_count(domain_user + [
                ('stage_id.code', '=', 'new'),
                ('call_count', '=', 0),
            ]),
            'potential_no_quote': self.search_count(domain_user + [
                ('stage_id.code', '=', 'potential'),
            ]),
            'stale': (
                self.search_count(domain_user + active_only + [
                    ('last_call_date', '<', stale_threshold),
                ])
                + self.search_count(domain_user + active_only + [
                    ('last_call_date', '=', False),
                    ('create_date', '<', stale_threshold),
                ])
            ),
        }

        return {
            'user': {'id': user.id, 'name': user.name},
            'kpi': kpi,
            'errors': errors,
            'stages': stage_payload,
        }

    @api.model
    def dashboard_leads(self, stage_id, user_id=None, limit=80):
        user = self.env['res.users'].browse(user_id) if user_id else self.env.user
        leads = self.search([
            ('user_id', '=', user.id),
            ('stage_id', '=', stage_id),
        ], limit=limit, order='probability desc, callback_date asc, create_date desc')
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
        } for l in leads]
