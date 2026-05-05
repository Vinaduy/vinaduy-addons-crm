from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class CrmLeadDashboard(models.AbstractModel):
    """Helper compute dashboard data."""
    _name = 'vinaduy.crm.dashboard'
    _description = 'VINADUY CRM Dashboard Data'

    @api.model
    def get_dashboard_data(self):
        Lead = self.env['crm.lead'].sudo()
        Stage = self.env['crm.stage'].sudo()
        Users = self.env['res.users'].sudo()

        # Tháng hiện tại
        today = fields.Date.today()
        month_start = today.replace(day=1)
        domain_month = [('create_date', '>=', month_start.strftime('%Y-%m-%d 00:00:00'))]
        domain_active = [('active', '=', True)]
        domain_all_active = domain_active

        # ============ KPI tháng hiện tại ============
        total_kh = Lead.search_count(domain_month + domain_active)
        won_stage = self.env.ref('vinaduy_crm.stage_won', raise_if_not_found=False)
        urgent_stage = self.env.ref('vinaduy_crm.stage_urgent', raise_if_not_found=False)
        contract_stage = self.env.ref('vinaduy_crm.stage_contract', raise_if_not_found=False)
        negotiation_stage = self.env.ref('vinaduy_crm.stage_negotiation', raise_if_not_found=False)

        won_count = Lead.search_count(domain_month + [('stage_id.is_won', '=', True)])
        gap_count = Lead.search_count(domain_month + domain_active + [('stage_id', '=', urgent_stage.id)]) if urgent_stage else 0
        hopdong_count = Lead.search_count(domain_month + domain_active + [('stage_id', '=', contract_stage.id)]) if contract_stage else 0
        damphan_count = Lead.search_count(domain_month + domain_active + [('stage_id', '=', negotiation_stage.id)]) if negotiation_stage else 0
        conv_pct = round(won_count / total_kh * 100, 2) if total_kh else 0
        overdue_count = Lead.search_count(domain_active + [('sla_overdue', '=', True)])

        # ============ Stages distribution ============
        stages_data = []
        for st in Stage.search([], order='sequence'):
            count = Lead.search_count([('stage_id', '=', st.id), ('active', '=', True)])
            stages_data.append({
                'id': st.id,
                'name': st.name,
                'count': count,
                'is_won': st.is_won,
                'sequence': st.sequence,
            })

        # ============ Per-user (current month) ============
        sale_users = Users.search([
            ('login', '=like', '%@gmail.com'),
            ('login', 'not in', [
                'vinaduyql1@gmail.com', 'vinaduyql2@gmail.com',
                'vinaduyql3@gmail.com', 'vinaduyql5@gmail.com',
                'sale.vinaduy@gmail.com',
            ]),
        ])
        per_user = []
        for user in sale_users:
            user_leads = Lead.search(domain_month + [('user_id', '=', user.id)])
            u_total = len(user_leads)
            u_won = sum(1 for l in user_leads if l.stage_id and l.stage_id.is_won)
            u_dam = sum(1 for l in user_leads if negotiation_stage and l.stage_id == negotiation_stage)
            u_hd = sum(1 for l in user_leads if contract_stage and l.stage_id == contract_stage)
            u_gap = sum(1 for l in user_leads if urgent_stage and l.stage_id == urgent_stage)
            u_overdue = Lead.search_count([('user_id', '=', user.id), ('sla_overdue', '=', True), ('active', '=', True)])
            u_conv = round(u_won / u_total * 100, 2) if u_total else 0
            per_user.append({
                'id': user.id,
                'name': user.partner_id.name or user.name,
                'avatar_url': f'/web/image/res.users/{user.id}/avatar_128',
                'total': u_total,
                'damphan': u_dam,
                'hopdong': u_hd,
                'gap': u_gap,
                'won': u_won,
                'conv': u_conv,
                'overdue': u_overdue,
                'rating': self._compute_rating(u_total, u_won, u_overdue),
            })
        per_user.sort(key=lambda x: -x['total'])

        # ============ Source breakdown ============
        sources_data = []
        Source = self.env['vinaduy.crm.source'].sudo()
        for src in Source.search([]):
            count = Lead.search_count(domain_month + [('vinaduy_source_id', '=', src.id)])
            sources_data.append({
                'name': src.name,
                'count': count,
                'code': src.code or '',
            })

        # ============ Last month comparison ============
        last_month_start = (month_start - relativedelta(months=1))
        last_month_end = month_start
        last_month_domain = [
            ('create_date', '>=', last_month_start.strftime('%Y-%m-%d 00:00:00')),
            ('create_date', '<', last_month_end.strftime('%Y-%m-%d 00:00:00')),
        ]
        last_total = Lead.search_count(last_month_domain + domain_active)
        last_won = Lead.search_count(last_month_domain + [('stage_id.is_won', '=', True)])
        growth_total = round((total_kh - last_total) / last_total * 100, 1) if last_total else 0
        growth_won = round((won_count - last_won) / last_won * 100, 1) if last_won else 0

        # ============ 12-month trend ============
        trend = []
        for i in range(11, -1, -1):
            m_start = month_start - relativedelta(months=i)
            m_end = m_start + relativedelta(months=1)
            m_domain = [
                ('create_date', '>=', m_start.strftime('%Y-%m-%d 00:00:00')),
                ('create_date', '<', m_end.strftime('%Y-%m-%d 00:00:00')),
            ]
            m_total = Lead.search_count(m_domain + domain_active)
            m_won = Lead.search_count(m_domain + [('stage_id.is_won', '=', True)])
            m_conv = round(m_won / m_total * 100, 1) if m_total else 0
            trend.append({
                'label': m_start.strftime('T%m/%y'),
                'total': m_total,
                'won': m_won,
                'conv': m_conv,
            })

        # ============ NV trên/dưới ngưỡng ============
        threshold_above = []  # ≥ 2 chốt
        threshold_below = []  # < 2 chốt VÀ tổng < 3
        for u in per_user:
            if u['won'] >= 2 or u['hopdong'] >= 3:
                threshold_above.append(u)
            elif u['won'] < 2 and u['hopdong'] < 3:
                threshold_below.append(u)

        return {
            'today': today.strftime('%d/%m/%Y'),
            'month': today.strftime('%m/%Y'),
            'kpi': {
                'total_kh': total_kh,
                'damphan': damphan_count,
                'hopdong': hopdong_count,
                'gap': gap_count,
                'won': won_count,
                'conv_pct': conv_pct,
                'overdue': overdue_count,
                'growth_total': growth_total,
                'growth_won': growth_won,
            },
            'stages': stages_data,
            'per_user': per_user,
            'sources': sources_data,
            'sale_user_count': len(sale_users),
            'trend': trend,
            'threshold_above': threshold_above,
            'threshold_below': threshold_below,
        }

    @api.model
    def get_tracker_data(self):
        """Trả về danh sách leads grouped theo urgency cho tracker view của NV."""
        Lead = self.env['crm.lead'].sudo()
        Stage = self.env['crm.stage'].sudo()
        Template = self.env['vinaduy.crm.checklist.template'].sudo()

        # Filter leads của user hiện tại (sales) hoặc tất cả (manager)
        user = self.env.user
        is_manager = user.has_group('sales_team.group_sale_manager')
        domain = [('active', '=', True)]
        if not is_manager:
            domain.append(('user_id', '=', user.id))

        leads = Lead.search(domain, order='sla_overdue desc, sla_deadline asc, create_date desc', limit=500)

        # Tổng số việc cần làm cho mỗi stage (template)
        all_stages = Stage.search([], order='sequence')
        stage_total_tasks = {}
        for st in all_stages:
            stage_total_tasks[st.id] = Template.search_count([('stage_id', '=', st.id), ('active', '=', True)])

        def serialize(lead):
            current_seq = lead.stage_id.sequence if lead.stage_id else 0
            current_stage_id = lead.stage_id.id if lead.stage_id else 0
            # Số việc đã làm ở stage hiện tại
            done_current = len(lead.checklist_item_ids.filtered(
                lambda i: i.stage_id == lead.stage_id and i.done
            ))
            total_current = stage_total_tasks.get(current_stage_id, 0)
            # Build progression: với mỗi stage trong all_stages, xác định trạng thái
            stage_badges = []
            for st in all_stages:
                if st.sequence < current_seq:
                    state = 'done'
                    done = stage_total_tasks.get(st.id, 0)
                    total = stage_total_tasks.get(st.id, 0)
                elif st.sequence == current_seq:
                    state = 'current'
                    done = done_current
                    total = total_current
                else:
                    state = 'pending'
                    done = 0
                    total = stage_total_tasks.get(st.id, 0)
                stage_badges.append({
                    'name': st.name,
                    'short': st.name.replace('Tiềm năng ', '').replace('Khách ', ''),
                    'state': state,
                    'done': done,
                    'total': total,
                    'is_won': st.is_won,
                })
            return {
                'id': lead.id,
                'name': lead.name,
                'phone': lead.phone or '',
                'user_name': lead.user_id.partner_id.name or lead.user_id.name or '',
                'user_id': lead.user_id.id,
                'stage_name': lead.stage_id.name if lead.stage_id else '',
                'stage_id': current_stage_id,
                'stage_progress': f"{done_current}/{total_current}" if total_current else '—',
                'callback': lead.vd_callback_date and lead.vd_callback_date.strftime('%d/%m %H:%M') or '',
                'sla_overdue': lead.sla_overdue,
                'sla_remaining': round(lead.sla_days_remaining, 1) if lead.sla_days_remaining else 0,
                'create_date': lead.create_date.strftime('%d/%m/%Y') if lead.create_date else '',
                'source': lead.vinaduy_source_id.name if lead.vinaduy_source_id else '',
                'project_type': dict(lead._fields['project_type'].selection).get(lead.project_type, ''),
                'overdue_days': abs(int(lead.sla_days_remaining)) if lead.sla_overdue else 0,
                'stage_badges': stage_badges,
            }

        # KPI by stage
        stages_kpi = []
        for st in Stage.search([], order='sequence'):
            count = Lead.search_count(domain + [('stage_id', '=', st.id)])
            stages_kpi.append({'id': st.id, 'name': st.name, 'count': count})

        # Sections
        overdue_leads = [serialize(l) for l in leads.filtered(lambda l: l.sla_overdue)]
        warning_leads = [serialize(l) for l in leads.filtered(
            lambda l: not l.sla_overdue and l.sla_days_remaining and 0 < l.sla_days_remaining <= 2
        )]
        normal_leads = [serialize(l) for l in leads.filtered(
            lambda l: not l.sla_overdue and (not l.sla_days_remaining or l.sla_days_remaining > 2)
        )]

        # ============ Today section: KH cần callback hôm nay ============
        today_dt = fields.Date.today()
        today_start = datetime.combine(today_dt, datetime.min.time())
        today_end = datetime.combine(today_dt, datetime.max.time())
        today_leads = [serialize(l) for l in leads.filtered(
            lambda l: l.vd_callback_date and today_start <= l.vd_callback_date <= today_end
        )]

        return {
            'is_manager': is_manager,
            'user_name': user.partner_id.name or user.name,
            'total': len(leads),
            'stages_kpi': stages_kpi,
            'today': today_leads,
            'overdue': overdue_leads,
            'warning': warning_leads,
            'normal': normal_leads,
        }

    @api.model
    def tracker_advance_stage(self, lead_id):
        """Quick action: chuyển KH sang stage tiếp theo."""
        lead = self.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            return {'success': False, 'message': 'KH không tồn tại'}
        next_stage = self.env['crm.stage'].search([
            ('sequence', '>', lead.stage_id.sequence),
            ('sequence', '<', 99),
        ], order='sequence', limit=1)
        if not next_stage:
            return {'success': False, 'message': 'Đã ở stage cuối'}
        lead.stage_id = next_stage.id
        return {'success': True, 'stage_name': next_stage.name}

    @api.model
    def tracker_postpone_callback(self, lead_id, days=1):
        """Quick action: dời lịch callback lên N ngày."""
        lead = self.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            return {'success': False}
        base = lead.vd_callback_date or fields.Datetime.now()
        lead.vd_callback_date = base + timedelta(days=days)
        return {'success': True, 'new_date': lead.vd_callback_date.strftime('%d/%m %H:%M')}

    # ====================== BONUS ======================
    @api.model
    def get_bonus_data(self, year=None, month=None):
        """Trả về bảng thưởng tháng theo NV và team.

        Quy tắc mặc định (a có thể chỉnh trong Settings → Tham số hệ thống):
        - vinaduy_crm.bonus_min_contracts (mặc định 2):  số HĐ tối thiểu để được thưởng
        - vinaduy_crm.bonus_per_contract (mặc định 1.000.000): thưởng/HĐ khi đạt ngưỡng
        - vinaduy_crm.bonus_extra_per_contract (mặc định 1.000.000): thưởng cho mỗi HĐ vượt
        - vinaduy_crm.bonus_team_threshold (mặc định 10): tổng HĐ team để được thưởng phòng
        - vinaduy_crm.bonus_team_amount (mặc định 5.000.000): thưởng phòng khi đạt
        """
        Lead = self.env['crm.lead'].sudo()
        Users = self.env['res.users'].sudo()
        Team = self.env['crm.team'].sudo()
        Param = self.env['ir.config_parameter'].sudo()

        # Cấu hình thưởng
        min_contracts = int(Param.get_param('vinaduy_crm.bonus_min_contracts', 2))
        per_contract = float(Param.get_param('vinaduy_crm.bonus_per_contract', 1000000))
        extra_per_contract = float(Param.get_param('vinaduy_crm.bonus_extra_per_contract', 1000000))
        team_threshold = int(Param.get_param('vinaduy_crm.bonus_team_threshold', 10))
        team_amount = float(Param.get_param('vinaduy_crm.bonus_team_amount', 5000000))

        # Period
        today = fields.Date.today()
        year = int(year) if year else today.year
        month = int(month) if month else today.month
        period_start = datetime(year, month, 1)
        period_end = period_start + relativedelta(months=1)
        period_domain = [
            ('create_date', '>=', period_start.strftime('%Y-%m-%d 00:00:00')),
            ('create_date', '<', period_end.strftime('%Y-%m-%d 00:00:00')),
        ]

        # Lấy DS NV sale (loại bỏ admin/QL như cũ)
        sale_users = Users.search([
            ('login', '=like', '%@gmail.com'),
            ('login', 'not in', [
                'vinaduyql1@gmail.com', 'vinaduyql2@gmail.com',
                'vinaduyql3@gmail.com', 'vinaduyql5@gmail.com',
                'sale.vinaduy@gmail.com',
            ]),
        ])

        users_data = []
        total_won_all = 0
        for user in sale_users:
            won_count = Lead.search_count(period_domain + [
                ('user_id', '=', user.id),
                ('stage_id.is_won', '=', True),
            ])
            total_won_all += won_count

            # Tính thưởng cá nhân
            if won_count >= min_contracts:
                base_bonus = min_contracts * per_contract
                extra_bonus = (won_count - min_contracts) * extra_per_contract
                personal_bonus = base_bonus + extra_bonus
            else:
                personal_bonus = 0

            users_data.append({
                'id': user.id,
                'name': user.partner_id.name or user.name,
                'avatar_url': f'/web/image/res.users/{user.id}/avatar_128',
                'team_id': user.sale_team_id.id if user.sale_team_id else 0,
                'team_name': user.sale_team_id.name if user.sale_team_id else 'Chưa có team',
                'won': won_count,
                'bonus': personal_bonus,
                'achieved': won_count >= min_contracts,
                'next_milestone': max(0, min_contracts - won_count) if won_count < min_contracts else 0,
            })

        users_data.sort(key=lambda x: -x['won'])

        # Tính thưởng theo team
        teams_data = []
        teams = Team.search([])
        for team in teams:
            team_members = [u for u in users_data if u['team_id'] == team.id]
            if not team_members:
                continue
            team_won = sum(u['won'] for u in team_members)
            team_bonus = team_amount if team_won >= team_threshold else 0
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'won': team_won,
                'member_count': len(team_members),
                'bonus': team_bonus,
                'achieved': team_won >= team_threshold,
                'next_milestone': max(0, team_threshold - team_won),
            })
        teams_data.sort(key=lambda x: -x['won'])

        total_personal_bonus = sum(u['bonus'] for u in users_data)
        total_team_bonus = sum(t['bonus'] for t in teams_data)

        return {
            'year': year,
            'month': month,
            'period_label': period_start.strftime('Tháng %m/%Y'),
            'config': {
                'min_contracts': min_contracts,
                'per_contract': per_contract,
                'extra_per_contract': extra_per_contract,
                'team_threshold': team_threshold,
                'team_amount': team_amount,
            },
            'users': users_data,
            'teams': teams_data,
            'summary': {
                'total_won': total_won_all,
                'total_personal_bonus': total_personal_bonus,
                'total_team_bonus': total_team_bonus,
                'total_bonus': total_personal_bonus + total_team_bonus,
                'achieved_count': sum(1 for u in users_data if u['achieved']),
                'user_count': len(users_data),
            },
        }

    @api.model
    def _compute_rating(self, total, won, overdue):
        """Rate user performance: green/yellow/red."""
        if won >= 2 or total >= 10:
            return {'level': 'good', 'label': '✅ Tốt', 'color': '#198754'}
        if overdue > 0:
            return {'level': 'warning', 'label': '⚠️ Cần cải thiện', 'color': '#fd7e14'}
        if total < 3:
            return {'level': 'low', 'label': '⏬ Ít KH', 'color': '#6c757d'}
        return {'level': 'normal', 'label': '🔵 Bình thường', 'color': '#0d6efd'}
