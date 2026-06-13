# -*- coding: utf-8 -*-
"""Extension res.users — track số KH quá hạn + cờ block nhận lead mới."""
from datetime import date

from odoo import models, fields, api


# Mặc định 3 — có thể đổi qua ir.config_parameter 'vd_crm_lead.overdue_block_threshold'
_DEFAULT_OVERDUE_THRESHOLD = 15


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
        help='False khi vd_overdue_lead_count > threshold (mặc định 15). '
             'Khi False, hệ thống round-robin sẽ skip NV này.',
    )
    vd_overdue_threshold = fields.Integer(
        string='Ngưỡng quá hạn',
        compute='_compute_vd_overdue_count',
        help='Lấy từ ir.config_parameter vd_crm_lead.overdue_block_threshold (default 3).',
    )

    # ===== TEAM/PHÒNG BAN suy từ TÊN (user spec 2026-06-13) =====
    # Hệ thống lấy team theo TIỀN TỐ TÊN ("HCM1 - Tên" → HCM1), KHÔNG dùng
    # crm.team. Field này hiện rõ team để admin biết NV thuộc HN/HCM1/HCM2...
    vd_team_label = fields.Char(
        string='Team (theo tên)', compute='_compute_vd_team_label',
        help='Phòng ban suy từ TIỀN TỐ TÊN: "HCM1 - Tên" → HCM1. Muốn đổi team '
             'thì sửa tiền tố trong TÊN nhân viên.')

    @api.depends('name')
    def _compute_vd_team_label(self):
        import re
        for u in self:
            m = re.match(r'^([A-ZĐ]+\d*)\s*[-–—]\s*', u.name or '')
            u.vd_team_label = (m.group(1) if m
                               else (u.sale_team_id.name if u.sale_team_id else 'KHÁC'))

    @api.model_create_multi
    def create(self, vals_list):
        """User spec 2026-06-13: NV tạo MỚI thường bị 'trần' (0 nhóm) → thành user
        portal (share=True) → KHÔNG đăng nhập backend được. Tự gán 5 nhóm NV chuẩn
        cho user mới KHÔNG có nhóm loại (internal/portal/public) → mặc định = NV
        nội bộ, đăng nhập được ngay. User portal/public CÓ CHỦ ĐÍCH (đã set nhóm)
        thì giữ nguyên."""
        users = super().create(vals_list)
        try:
            internal = self.env.ref('base.group_user', raise_if_not_found=False)
            portal = self.env.ref('base.group_portal', raise_if_not_found=False)
            public = self.env.ref('base.group_public', raise_if_not_found=False)
            nv_gids = []
            for x in ('base.group_user', 'sales_team.group_sale_salesman',
                      'sales_team.group_sale_salesman_all_leads',
                      'vd_crm_lead.vd_crm_group_collaborator',
                      'vd_crm_lead.vd_crm_group_employee'):
                g = self.env.ref(x, raise_if_not_found=False)
                if g:
                    nv_gids.append(g.id)
            for u in users:
                has_type = ((internal and internal in u.groups_id)
                            or (portal and portal in u.groups_id)
                            or (public and public in u.groups_id))
                if not has_type and nv_gids:
                    u.sudo().write({'groups_id': [(4, gid) for gid in nv_gids]})
        except Exception:
            pass
        return users

    # ===== KHOÁ DO CHƯA TÌM VẤN ĐỀ (user spec 2026-06-01) =====
    # Khi > ngưỡng % KH (trong bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ) chưa có vấn đề
    # liên tục quá số ngày gia hạn → cron bật vd_problem_lock=True. Dashboard
    # chặn mở thẻ KHÁCH MỚI cho tới khi NV xử lý xong (cả 2 bảng <= ngưỡng).
    vd_problem_lock = fields.Boolean(
        string='Khoá do chưa tìm vấn đề', default=False, copy=False,
        help='True khi NV quá hạn xử lý "tìm vấn đề". Khi True dashboard chặn '
             'bấm mở KHÁCH MỚI. Tự gỡ khi NV xử lý xong (cả 2 bảng <= ngưỡng).',
    )
    vd_problem_find_since = fields.Datetime(
        string='Vi phạm tìm vấn đề từ', copy=False,
        help='Mốc NV bắt đầu vượt ngưỡng % KH chưa có vấn đề. Cron đếm từ đây '
             'để áp khoá sau số ngày gia hạn. Reset khi NV xử lý xong.',
    )
    # KHOÁ THEO TỪNG BẢNG (user spec 2026-06-05): "bảng nào vi phạm khoá bảng đó".
    # Quá hạn gia hạn mà bảng còn vượt ngưỡng -> khoá đúng bảng đó. CHỈ ADMIN GỠ
    # (NV không tự gỡ vì bảng bị khoá không bấm được). vd_problem_lock cũ giữ làm
    # cờ tổng (= urgent OR xlvd) cho tương thích chỗ khác.
    vd_pf_lock_urgent = fields.Boolean(
        string='Khoá bảng THI CÔNG GẤP', default=False, copy=False,
        help='True khi bảng THI CÔNG GẤP quá hạn tìm vấn đề. Chặn bấm cả bảng. '
             'Chỉ admin gỡ.',
    )
    vd_pf_lock_xlvd = fields.Boolean(
        string='Khoá bảng XỬ LÝ VẤN ĐỀ', default=False, copy=False,
        help='True khi bảng XỬ LÝ VẤN ĐỀ quá hạn tìm vấn đề. Chặn bấm cả bảng. '
             'Chỉ admin gỡ.',
    )
    # Mốc gia hạn RIÊNG từng bảng (đếm ngày để áp khoá). Admin gỡ khoá -> đặt
    # mốc sao cho CÒN ĐÚNG 1 NGÀY (user spec 2026-06-05: mở 1 ngày, không xử lý
    # thì tự khoá lại). Tách riêng để gỡ bảng này không ảnh hưởng bảng kia.
    vd_pf_since_urgent = fields.Datetime(string='Vi phạm THI CÔNG GẤP từ', copy=False)
    vd_pf_since_xlvd = fields.Datetime(string='Vi phạm XỬ LÝ VẤN ĐỀ từ', copy=False)

    # ===== NHẮC NHỞ NHÂN VIÊN — admin tick Lần 1..5 (user spec 2026-06-01) =====
    # Mỗi lần admin nhắc 1 NV thì tick lên 1 mức. Hiển thị ✓ cho mức 1..N + câu
    # nhắc tương ứng (admin chụp màn hình gửi NV). 0 = chưa nhắc lần nào.
    vd_reminder_level = fields.Integer(
        string='Mức nhắc nhở (0-5)', default=0, copy=False,
        help='Số lần admin đã nhắc NV xử lý KH tồn đọng (0..5). Set qua popover '
             'NHẮC NHỞ trên dashboard.',
    )

    # ===== HƯỚNG DẪN NÚT SOS — coachmark tự hiện cho NV (user spec 2026-06-03) =====
    # Bảng nhỏ hướng dẫn cách dùng nút SOS, neo vào 1 nút SOS. NV bấm "Đã đọc"
    # = 1 lần (chỉ tính 1 lần/ngày). Đủ 3 lần trên 3 NGÀY KHÁC NHAU → ẩn vĩnh
    # viễn. Default 0 → mọi NV (kể cả NV tạo mới) đều thấy lúc đầu.
    vd_sos_guide_ack_count = fields.Integer(
        string='Số ngày đã đọc hướng dẫn SOS', default=0, copy=False,
        help='Số NGÀY KHÁC NHAU NV đã bấm "Đã đọc" bảng hướng dẫn SOS. '
             '>= 3 thì ẩn hướng dẫn vĩnh viễn.',
    )
    vd_sos_guide_last_ack = fields.Date(
        string='Ngày đọc hướng dẫn SOS gần nhất', copy=False,
        help='Chỉ tính 1 lần/ngày — bấm "Đã đọc" lại trong cùng ngày không cộng thêm.',
    )

    @api.model
    def vd_sos_guide_should_show(self, user=None):
        """True nếu user còn phải xem hướng dẫn SOS: chưa đủ 3 ngày VÀ hôm nay
        chưa bấm 'Đã đọc'."""
        user = user or self.env.user
        today = fields.Date.context_today(self)
        return (user.vd_sos_guide_ack_count or 0) < 3 and user.vd_sos_guide_last_ack != today

    @api.model
    def vd_sos_guide_ack(self):
        """NV bấm 'Đã đọc'. Chỉ cộng 1 lần/ngày → cần 3 ngày khác nhau mới đủ.
        Trả {show, count}."""
        user = self.env.user
        today = fields.Date.context_today(self)
        if user.vd_sos_guide_last_ack != today:
            user.sudo().write({
                'vd_sos_guide_ack_count': (user.vd_sos_guide_ack_count or 0) + 1,
                'vd_sos_guide_last_ack': today,
            })
        return {
            'show': self.vd_sos_guide_should_show(user),
            'count': user.vd_sos_guide_ack_count or 0,
        }

    @api.model
    def vd_set_reminder_level(self, user_id, level):
        """Admin set mức nhắc nhở cho 1 NV (0..5). Trả mức mới."""
        try:
            level = max(0, min(5, int(level)))
        except (TypeError, ValueError):
            level = 0
        user = self.browse(int(user_id))
        if user.exists():
            user.sudo().vd_reminder_level = level
        return level

    @api.model
    def vd_recent_recordings(self, user_id, limit=20, min_seconds=180):
        """Hover thẻ "Cuộc gọi tháng này" → trả 2 phần (user spec 2026-06-05):
          - stats: thống kê cuộc gọi THÁNG (tổng, % nghe máy, % >3', % >5').
          - recordings: 20 ghi âm gần nhất >= 3 phút (nghe/tải ngay).
        """
        Call = self.env['stringee.call'].sudo()
        uid = int(user_id)
        calls = Call.search([
            ('user_id', '=', uid),
            ('duration', '>=', int(min_seconds)),
            ('recording_attachment_id', '!=', False),
        ], order='create_date desc', limit=int(limit))
        res = []
        for c in calls:
            att = c.recording_attachment_id
            if not att:
                continue
            local_dt = fields.Datetime.context_timestamp(c, c.create_date) if c.create_date else None
            res.append({
                'id': c.id,
                'callee': c.callee_number or c.caller_number or '',
                'duration': c.duration or 0,
                'date': local_dt.strftime('%d/%m %H:%M') if local_dt else '',
                'play_url': '/web/content/%s?download=false' % att.id,
                'download_url': '/web/content/%s?download=true' % att.id,
            })
        # ===== Thống kê cuộc gọi THÁNG hiện tại =====
        month_start = fields.Datetime.to_datetime(date.today().replace(day=1))
        base = [
            ('user_id', '=', uid),
            ('create_date', '>=', month_start),
            ('lead_id', '!=', False),
        ]
        answered_dom = ['|', ('state', '=', 'answered'),
                        '&', ('state', '=', 'ended'), ('duration', '>', 0)]
        total = Call.search_count(base)
        answered = Call.search_count(base + answered_dom)
        over3 = Call.search_count(base + [('duration', '>=', 180)])
        over5 = Call.search_count(base + [('duration', '>=', 300)])

        def _pct(x):
            return round(x / total * 100) if total else 0

        stats = {
            'total': total,
            'answered': answered, 'answered_pct': _pct(answered),
            'over3': over3, 'over3_pct': _pct(over3),
            'over5': over5, 'over5_pct': _pct(over5),
        }
        return {'stats': stats, 'recordings': res}

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
        Lead = self.env['crm.lead'].sudo()
        # CHẶN CHIA SỐ (user spec 2026-06-12): loại NV đang tồn >= ngưỡng KH mới
        # CHƯA gọi. Nếu TẤT CẢ đều đầy → fallback chọn NV ÍT tồn nhất (Pancake /
        # auto KHÔNG được rớt lead).
        threshold = Lead._vd_distribute_block_threshold()
        if threshold > 0:
            uncalled = Lead._vd_uncalled_new_count_map(eligible.ids)
            with_cap = eligible.filtered(
                lambda u: uncalled.get(u.id, 0) < threshold)
            if with_cap:
                eligible = with_cap
            else:
                return min(eligible, key=lambda u: uncalled.get(u.id, 0))
        # Pick NV có ÍT active leads nhất (load-balanced round-robin)
        def active_load(user):
            return Lead.search_count([
                ('user_id', '=', user.id),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ])
        return min(eligible, key=active_load)
