# -*- coding: utf-8 -*-
"""Extension res.users — track số KH quá hạn + cờ block nhận lead mới."""
from datetime import date

from odoo import models, fields, api


# Mặc định 3 — có thể đổi qua ir.config_parameter 'vd_crm_lead.overdue_block_threshold'
_DEFAULT_OVERDUE_THRESHOLD = 3


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Số KH có callback_date QUÁ HẠN (đã đến hạn gọi lại mà NV chưa xử lý)
    vd_overdue_lead_count = fields.Integer(
        string='KH quá hạn chăm sóc',
        compute='_compute_vd_overdue_count',
        help='Số lead có callback_date < bây giờ + chưa won/lost.',
    )
    # NV có được phân bổ lead MỚI không (block khi quá hạn > threshold)
    vd_can_receive_new_leads = fields.Boolean(
        string='Được nhận KH mới',
        compute='_compute_vd_overdue_count',
        help='False khi vd_overdue_lead_count > threshold (mặc định 3). '
             'Khi False, hệ thống round-robin sẽ skip NV này.',
    )
    vd_overdue_threshold = fields.Integer(
        string='Ngưỡng quá hạn',
        compute='_compute_vd_overdue_count',
        help='Lấy từ ir.config_parameter vd_crm_lead.overdue_block_threshold (default 3).',
    )
    # ===== TOGGLE NHẬN KH TỪ PANCAKE =====
    # Admin tự bật/tắt cho từng NV — độc lập với cờ quá hạn ở trên.
    vd_can_receive_pancake = fields.Boolean(
        string='Nhận KH từ Pancake',
        default=True,
        help='Admin tắt cờ này khi muốn TẠM DỪNG đẩy KH Pancake cho NV này '
             '(vd: NV nghỉ phép, đang training). Round-robin sẽ skip NV.',
    )

    # ============ THÔNG TIN LÀM VIỆC — số tháng + năng lực ============
    vd_work_start_date = fields.Date(
        string='Ngày bắt đầu làm việc',
        default=fields.Date.context_today,
        help='Ngày NV chính thức bắt đầu làm việc. Mặc định = ngày tạo user, '
             'admin có thể chỉnh sửa lại đúng thực tế.',
    )
    vd_work_months = fields.Integer(
        string='Số tháng làm việc',
        compute='_compute_vd_work_months',
        help='Số tháng tính từ vd_work_start_date đến hôm nay.',
    )
    vd_capacity_level = fields.Selection(
        [
            ('trainee', '🌱 Tập sự'),
            ('junior',  '🌿 Junior'),
            ('mid',     '🌳 Trung cấp'),
            ('senior',  '🏆 Senior'),
            ('expert',  '⭐ Expert'),
        ],
        string='Năng lực',
        default='junior',
        help='Đánh giá năng lực NV — admin set thủ công theo kết quả review định kỳ.',
    )

    @api.depends('vd_work_start_date')
    def _compute_vd_work_months(self):
        today = date.today()
        for u in self:
            if not u.vd_work_start_date:
                u.vd_work_months = 0
                continue
            d = u.vd_work_start_date
            months = (today.year - d.year) * 12 + (today.month - d.month)
            if today.day < d.day:
                months -= 1
            u.vd_work_months = max(0, months)

    # ============ PERFORMANCE / BONUS — cơ cấu chỉ tiêu VINADUY 2026 ============
    vd_contracts_month = fields.Integer(
        string='HĐ chốt tháng này',
        compute='_compute_vd_performance',
        help='Số lead đã ký HĐ (stage WON + vd_contract_signed) trong tháng này.',
    )
    vd_contracts_year = fields.Integer(
        string='HĐ chốt năm này',
        compute='_compute_vd_performance',
    )
    vd_bonus_month = fields.Monetary(
        string='Thưởng tháng (đ)',
        compute='_compute_vd_performance',
        currency_field='company_currency',
        help='Tổng thưởng tháng này theo bậc thang HĐ — file cơ cấu chỉ tiêu 2026.',
    )
    vd_target_month = fields.Integer(
        string='Chỉ tiêu/tháng', default=2,
        help='Chỉ tiêu cá nhân tối thiểu: 2 HĐ/tháng = 20 HĐ/năm.',
    )
    vd_perf_pct = fields.Float(
        string='% Hoàn thành tháng',
        compute='_compute_vd_performance',
        digits=(5, 1),
    )
    company_currency = fields.Many2one(
        'res.currency', compute='_compute_vd_performance',
        string='Currency (compute helper)',
    )

    @api.depends_context('uid')
    def _compute_vd_performance(self):
        """Tính HĐ chốt + bonus theo cơ cấu chỉ tiêu 2026.

        Bonus tiers (đã gồm 500k nóng/HĐ):
          HĐ #1 = 3,500,000đ
          HĐ #2 = 5,500,000đ  (tổng 9M)
          HĐ #3 = 7,500,000đ  (tổng 16.5M — đạt chỉ tiêu 3 HĐ)
          HĐ #4 = 8,500,000đ  (tổng 25M — vượt)
          HĐ #5 = 9,500,000đ  (tổng 34.5M — siêu vượt)
          HĐ #6+ = 9,500,000đ each
        """
        from datetime import date
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        Lead = self.env['crm.lead'].sudo()
        vnd = self.env['res.currency'].sudo().search([('name', '=', 'VND')], limit=1) \
              or self.env.company.currency_id
        for user in self:
            cnt_month = Lead.search_count([
                ('user_id', '=', user.id),
                ('vd_contract_signed', '=', True),
                ('vd_contract_sign_date', '>=', month_start),
            ])
            cnt_year = Lead.search_count([
                ('user_id', '=', user.id),
                ('vd_contract_signed', '=', True),
                ('vd_contract_sign_date', '>=', year_start),
            ])
            user.vd_contracts_month = cnt_month
            user.vd_contracts_year = cnt_year
            user.vd_bonus_month = self._vd_calc_nv_bonus(cnt_month)
            target = user.vd_target_month or 2
            user.vd_perf_pct = (cnt_month / target * 100.0) if target else 0.0
            user.company_currency = vnd

    @api.model
    def _vd_calc_nv_bonus(self, n_contracts):
        """Bậc thang thưởng NV theo file Cơ cấu chỉ tiêu 2026.
        Cumulative — HĐ thứ N có giá trị bonus tier riêng."""
        TIERS = {
            1: 3_500_000,
            2: 5_500_000,
            3: 7_500_000,
            4: 8_500_000,
            5: 9_500_000,
        }
        DEFAULT_HIGH = 9_500_000  # HĐ 6+ giữ mức 9.5M
        total = 0
        for i in range(1, (n_contracts or 0) + 1):
            total += TIERS.get(i, DEFAULT_HIGH)
        return total

    @api.depends_context('uid')
    def _compute_vd_overdue_count(self):
        Lead = self.env['crm.lead'].sudo()
        now = fields.Datetime.now()
        threshold = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'vd_crm_lead.overdue_block_threshold', _DEFAULT_OVERDUE_THRESHOLD,
            ) or _DEFAULT_OVERDUE_THRESHOLD
        )
        for user in self:
            cnt = Lead.search_count([
                ('user_id', '=', user.id),
                ('callback_date', '<', now),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ])
            user.vd_overdue_lead_count = cnt
            user.vd_overdue_threshold = threshold
            user.vd_can_receive_new_leads = cnt <= threshold

    @api.model
    def _vd_pick_next_assignee(self, exclude_user_ids=None, preferred_team_id=None, source=None):
        """Round-robin: chọn NV tiếp theo được nhận lead mới.

        Logic:
        1. Lấy NV thuộc vd_crm_group_employee (active, not share)
        2. LOẠI mọi user có vai trò cao hơn (Trưởng nhóm / Phó GĐ / Admin) —
           lead phải xuống tay NV thuần, không phân cho lãnh đạo
        3. Filter: chỉ giữ NV có vd_can_receive_new_leads = True
        4. Nếu source='pancake' → thêm filter vd_can_receive_pancake = True
        5. Trong số đó, chọn NV có ÍT lead chưa won/lost NHẤT (load-balanced)
        6. Trả về user record, hoặc empty nếu KHÔNG có NV nào eligible

        :param exclude_user_ids: list user IDs để loại trừ (vd: NV vừa được phân lead trước)
        :param preferred_team_id: nếu set, ưu tiên NV thuộc team này.
        :param source: 'pancake' khi lead đến từ Pancake webhook — áp thêm filter
                       vd_can_receive_pancake để admin có thể tắt riêng kênh này
                       cho từng NV mà không ảnh hưởng kênh khác.
        """
        # Pool ban đầu: tất cả sales NV (group_sale_salesman của Odoo gốc — tương
        # ứng với "NV Sale" đã được setup từ trước). Sau đó LOẠI những user có
        # vai trò cao hơn trong VD CRM phân quyền (Trưởng nhóm / Phó GĐ / Admin)
        # — lead Pancake không phân cho lãnh đạo.
        domain = [
            ('share', '=', False),
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ]
        if exclude_user_ids:
            domain.append(('id', 'not in', list(exclude_user_ids)))
        candidates = self.sudo().search(domain)
        # has_group('team_leader') True cho cả Trưởng nhóm / Phó GĐ / Admin
        # (admin implies deputy implies team_leader). → loại 3 vai trò này.
        candidates = candidates.filtered(
            lambda u: not u.has_group('vd_crm_lead.vd_crm_group_team_leader')
        )
        if preferred_team_id:
            team_members = candidates.filtered(
                lambda u: preferred_team_id in u.sale_team_id.ids if u.sale_team_id else False
            )
            if team_members:
                candidates = team_members
        # Lọc NV còn được nhận lead (overdue <= threshold)
        eligible = candidates.filtered('vd_can_receive_new_leads')
        # Lọc thêm theo kênh Pancake nếu source='pancake'
        if source == 'pancake':
            eligible = eligible.filtered('vd_can_receive_pancake')
        if not eligible:
            return self.env['res.users']  # empty
        # Pick NV có ÍT active leads nhất (load-balanced round-robin)
        Lead = self.env['crm.lead'].sudo()
        def active_load(user):
            return Lead.search_count([
                ('user_id', '=', user.id),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ])
        return min(eligible, key=active_load)
