"""Lead (khách hàng) model.

Probability is a heuristic — not a real prediction. It blends a stage base with
activity modifiers so the dashboard surfaces "warm" leads first. Tune the
constants in `_compute_probability` if the field over- or under-estimates.
"""
from datetime import timedelta

from odoo import api, fields, models


class VdCrmLead(models.Model):
    _name = 'vd.crm.lead'
    _description = 'Khách hàng / Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, callback_date asc, create_date desc'

    name = fields.Char(string='Tên khách hàng', required=True, tracking=True)
    phone = fields.Char(index=True, tracking=True)
    email = fields.Char()
    address = fields.Char()
    notes = fields.Text(string='Ghi chú')

    user_id = fields.Many2one(
        'res.users', string='NV phụ trách',
        default=lambda self: self.env.user, tracking=True, index=True,
    )
    stage_id = fields.Many2one(
        'vd.crm.stage', string='Trạng thái',
        default=lambda self: self._default_stage(), tracking=True, index=True, required=True,
        group_expand='_read_group_stage_ids',
    )
    stage_code = fields.Char(related='stage_id.code', store=True, index=True)
    stage_is_won = fields.Boolean(related='stage_id.is_won', store=True)
    stage_is_lost = fields.Boolean(related='stage_id.is_lost', store=True)

    callback_date = fields.Datetime(string='Hẹn gọi lại lúc', tracking=True)
    expected_close_date = fields.Date(string='Dự kiến chốt')
    expected_revenue = fields.Monetary(string='Doanh thu dự kiến', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )

    priority = fields.Selection([
        ('0', 'Bình thường'),
        ('1', 'Cao'),
        ('2', 'Khẩn'),
    ], default='0', string='Ưu tiên')
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)

    # Activity stats (denormalised from stringee.call for dashboard speed)
    last_call_date = fields.Datetime(string='Lần gọi gần nhất', readonly=True)
    last_answered_date = fields.Datetime(string='Lần nghe máy gần nhất', readonly=True)
    call_count = fields.Integer(string='Số lần gọi', default=0, readonly=True)
    no_answer_streak = fields.Integer(
        string='Số lần không nghe liên tiếp', default=0, readonly=True,
        help='Reset về 0 khi KH nghe máy.',
    )
    call_ids = fields.One2many('stringee.call', 'lead_id', string='Lịch sử gọi')

    # Heuristic close rate — base from stage + activity modifiers
    probability = fields.Float(
        string='Tỉ lệ chốt (%)',
        compute='_compute_probability', store=True,
        help='Stage base ± activity modifiers (recent call +, long silence -, no-answer streak -).',
    )

    is_overdue_callback = fields.Boolean(compute='_compute_flags', search='_search_overdue_callback')
    is_today_callback = fields.Boolean(compute='_compute_flags')
    is_stale = fields.Boolean(
        compute='_compute_flags',
        help='Chưa gọi trong 14 ngày kể từ khi tạo / lần gọi cuối.',
    )

    # ---------- Defaults & group expand ----------

    @api.model
    def _default_stage(self):
        return self.env['vd.crm.stage'].search([('code', '=', 'new')], limit=1) \
               or self.env['vd.crm.stage'].search([], limit=1, order='sequence')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['vd.crm.stage'].search([], order='sequence')

    # ---------- Computes ----------

    @api.depends(
        'stage_id', 'stage_id.default_probability', 'stage_id.is_won', 'stage_id.is_lost',
        'last_call_date', 'last_answered_date', 'no_answer_streak', 'callback_date',
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

            value = base + modifier
            if value < 0:
                value = 0.0
            elif value > 100:
                value = 100.0
            rec.probability = value

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

    def _search_overdue_callback(self, operator, value):
        if operator not in ('=', '!='):
            raise ValueError("Unsupported operator")
        match = (operator == '=' and value) or (operator == '!=' and not value)
        domain = [
            ('callback_date', '<', fields.Datetime.now()),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
        ]
        if match:
            return domain
        return ['!'] + domain

    # ---------- Actions ----------

    def action_call(self):
        """Place an outbound call via vd_stringee, link the call back to this lead."""
        self.ensure_one()
        if not self.phone:
            from odoo.exceptions import UserError
            raise UserError("Khách hàng chưa có số điện thoại.")
        call = self.env['stringee.call'].make_call(
            callee_number=self.phone,
            user_id=self.env.user.id,
        )
        call.write({'lead_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stringee.call',
            'res_id': call.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_dashboard(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_crm_lead.dashboard',
        }

    # ---------- Dashboard data ----------

    @api.model
    def dashboard_data(self, user_id=None):
        """Return everything the dashboard renders in one round-trip."""
        user = self.env['res.users'].browse(user_id) if user_id else self.env.user
        domain_user = [('user_id', '=', user.id)]

        Stage = self.env['vd.crm.stage']
        stages = Stage.search([], order='sequence')
        stage_payload = []
        for st in stages:
            count = self.search_count(domain_user + [('stage_id', '=', st.id)])
            stage_payload.append({
                'id': st.id,
                'code': st.code,
                'name': st.name,
                'count': count,
                'color': st.color,
                'is_won': st.is_won,
                'is_lost': st.is_lost,
                'default_probability': st.default_probability,
            })

        today = fields.Date.context_today(self)
        today_start = fields.Datetime.to_datetime(today)
        today_end = today_start + timedelta(days=1)

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
            'callback_today': self.search_count(domain_user + [
                ('callback_date', '>=', today_start),
                ('callback_date', '<', today_end),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ]),
            'calls_today': Call.search_count(call_today_domain),
            'calls_answered_today': Call.search_count(
                call_today_domain + [('state', 'in', ['answered', 'ended']), ('duration', '>', 0)],
            ),
            'recordings_today': Call.search_count(
                call_today_domain + [('recording_attachment_id', '!=', False)],
            ),
        }

        now = fields.Datetime.now()
        stale_threshold = now - timedelta(days=14)
        active_only = [('stage_is_won', '=', False), ('stage_is_lost', '=', False)]

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
            'phone': l.phone,
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
