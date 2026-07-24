# -*- coding: utf-8 -*-
"""Extension res.users — track số KH quá hạn + cờ block nhận lead mới."""
from datetime import date

from odoo import models, fields, api


# Mặc định 3 — có thể đổi qua ir.config_parameter 'vd_crm_lead.overdue_block_threshold'
_DEFAULT_OVERDUE_THRESHOLD = 15

# Danh sách phòng ban chọn được trên thẻ (user spec 2026-06-13).
_VD_TEAM_SELECTION = [
    ('HCM1', 'HCM1'), ('HCM2', 'HCM2'), ('HN', 'HN'),
    ('CTV', 'CTV'), ('VINADUY', 'VINADUY'),
]

# 5 vai trò CRM — XML id nhóm, xếp từ CAO xuống THẤP (admin → CTV).
_VD_ROLE_GROUPS = [
    ('admin', 'vd_crm_lead.vd_crm_group_admin'),
    ('director', 'vd_crm_lead.vd_crm_group_deputy_director'),
    ('team_leader', 'vd_crm_lead.vd_crm_group_team_leader'),
    ('employee', 'vd_crm_lead.vd_crm_group_employee'),
    ('collaborator', 'vd_crm_lead.vd_crm_group_collaborator'),
]


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
    # Phòng ban CHỌN ĐƯỢC (thẻ) — admin đổi thẻ = chuyển NV sang phòng ban khác.
    # Bỏ trống → tự suy từ tiền tố TÊN (tương thích NV cũ).
    vd_team = fields.Selection(
        _VD_TEAM_SELECTION, string='Phòng ban',
        help='Phòng ban của nhân viên. Đổi thẻ để chuyển NV sang phòng ban khác '
             '(KH + dashboard nhóm theo trường này). Bỏ trống = tự suy từ tiền tố TÊN.')
    vd_team_label = fields.Char(
        string='Team', compute='_compute_vd_team_label',
        help='Phòng ban hiệu lực: ưu tiên thẻ "Phòng ban", nếu trống thì suy từ '
             'tiền tố TÊN ("HCM1 - Tên" → HCM1).')

    def _vd_autoset_team(self):
        """Gán vd_team từ tiền tố TÊN nếu CHƯA set (để record rule theo phòng ban
        luôn đúng cho NV mới / đổi tên). KHÔNG đè khi admin đã chọn thẻ thủ công."""
        import re
        valid = dict(_VD_TEAM_SELECTION)
        for u in self:
            if u.vd_team:
                continue
            m = re.match(r'^([A-ZĐ]+\d*)\s*[-–—]\s*', u.name or '')
            prefix = m.group(1) if m else ''
            if prefix in valid:
                u.sudo().vd_team = prefix

    def write(self, vals):
        res = super().write(vals)
        # Đổi TÊN mà chưa set thẻ phòng ban → tự suy lại từ tiền tố.
        if 'name' in vals and 'vd_team' not in vals:
            self._vd_autoset_team()
        return res

    @api.depends('name', 'vd_team', 'sale_team_id')
    def _compute_vd_team_label(self):
        import re
        for u in self:
            if u.vd_team:
                u.vd_team_label = u.vd_team
                continue
            m = re.match(r'^([A-ZĐ]+\d*)\s*[-–—]\s*', u.name or '')
            u.vd_team_label = (m.group(1) if m
                               else (u.sale_team_id.name if u.sale_team_id else 'KHÁC'))

    # ===== PHÂN QUYỀN CRM — chọn nhanh 1 trong 5 vai trò (đồng bộ nhóm) =====
    vd_crm_role = fields.Selection(
        [('collaborator', '1. Cộng tác viên'), ('employee', '2. Nhân viên'),
         ('team_leader', '3. Trưởng nhóm'), ('director', '4. Giám đốc'),
         ('admin', '5. Admin')],
        string='Phân quyền', compute='_compute_vd_crm_role',
        inverse='_inverse_vd_crm_role',
        help='Vai trò trong hệ thống CRM của VINADUY. Đổi để cấp/thu quyền — '
             'hệ thống tự đồng bộ nhóm bảo mật tương ứng.')

    @api.depends('groups_id')
    def _compute_vd_crm_role(self):
        refs = {code: self.env.ref(xid, raise_if_not_found=False)
                for code, xid in _VD_ROLE_GROUPS}
        for u in self:
            role = False
            for code, _xid in _VD_ROLE_GROUPS:  # CAO → THẤP, lấy vai trò cao nhất
                g = refs.get(code)
                if g and g in u.groups_id:
                    role = code
                    break
            u.vd_crm_role = role

    def _inverse_vd_crm_role(self):
        all_groups = self.env['res.groups']
        refs = {}
        for code, xid in _VD_ROLE_GROUPS:
            g = self.env.ref(xid, raise_if_not_found=False)
            refs[code] = g
            if g:
                all_groups |= g
        # Home action = Dashboard CRM cho mọi vai trò TRỪ Admin → đăng nhập vào
        # thẳng module CRM (user spec 2026-06-19). Admin giữ home mặc định (toàn
        # quyền, tự chọn app). Menu các app khác đã bị khoá về admin trong
        # menu_overrides.xml → NV/TN/GĐ chỉ còn CRM.
        dash = self.env.ref('vd_crm_lead.action_vd_crm_dashboard',
                            raise_if_not_found=False)
        for u in self:
            if not u.vd_crm_role:
                continue
            target = refs.get(u.vd_crm_role)
            cmds = [(3, g.id) for g in all_groups]  # gỡ cả 5 vai trò trước
            if target:
                cmds.append((4, target.id))  # gán vai trò mới (tự kéo theo cấp dưới)
            vals = {'groups_id': cmds}
            if dash:
                vals['action_id'] = False if u.vd_crm_role == 'admin' else dash.id
            u.sudo().write(vals)

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
            # User spec 2026-06-14: KHÔNG cấp 'group_sale_salesman_all_leads' nữa
            # (vốn cho NV xem mọi lead). NV mới chỉ thấy KH của mình.
            nv_gids = []
            for x in ('base.group_user', 'sales_team.group_sale_salesman',
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
        # Tự gán thẻ phòng ban từ tiền tố tên (record rule theo nhóm cần vd_team).
        users._vd_autoset_team()
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
    def vd_recent_recordings(self, user_id, limit=100, min_seconds=180, offset=0):
        """Hover thẻ "Cuộc gọi tháng này" → trả (user spec 2026-06-22):
          - stats: thống kê cuộc gọi THÁNG (tổng, % nghe máy, % >3', % >5').
          - recordings: ghi âm >= 3 phút (mỗi trang 100), kèm TÊN KH + TRẠNG THÁI.
          - total / page_size / offset: phục vụ phân trang (>100 thì trang 2,3...).
        """
        Call = self.env['stringee.call'].sudo()
        uid = int(user_id)
        rec_dom = [
            ('user_id', '=', uid),
            ('duration', '>=', int(min_seconds)),
            ('recording_attachment_id', '!=', False),
        ]
        total_rec = Call.search_count(rec_dom)
        calls = Call.search(rec_dom, order='create_date desc',
                            limit=int(limit), offset=int(offset))
        today_local = fields.Date.context_today(self)
        res = []
        for c in calls:
            att = c.recording_attachment_id
            if not att:
                continue
            local_dt = fields.Datetime.context_timestamp(c, c.create_date) if c.create_date else None
            rec_day = local_dt.date() if local_dt else None
            days_ago = (today_local - rec_day).days if rec_day else 0
            lead = c.lead_id
            if lead:
                st = lead._vd_status_label_short()
                lead_name = lead.partner_name or lead.name or (c.callee_number or '—')
            else:
                st = {'label': '—', 'cls': 'none'}
                lead_name = c.callee_number or c.caller_number or '—'
            res.append({
                'id': c.id,
                'lead_id': lead.id if lead else False,
                'lead_name': lead_name,
                'status': st['label'],
                'status_cls': st['cls'],
                'duration': c.duration or 0,
                'date': local_dt.strftime('%d/%m %H:%M') if local_dt else '',
                # Nhóm theo NGÀY + số ngày trước (user spec 2026-07-08).
                'time': local_dt.strftime('%H:%M') if local_dt else '',
                'day_key': rec_day.isoformat() if rec_day else '',
                'day_dm': rec_day.strftime('%d/%m') if rec_day else '',
                'days_ago': days_ago,
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
        return {'stats': stats, 'recordings': res, 'total': total_rec,
                'page_size': int(limit), 'offset': int(offset)}

    # ===== TOGGLE NHẬN KH TỪ PANCAKE =====
    # Admin tự bật/tắt cho từng NV — độc lập với cờ quá hạn ở trên.
    vd_can_receive_pancake = fields.Boolean(
        string='Nhận số (tự động + thủ công)',
        default=True,
        help='Công tắc nhận số DUY NHẤT của NV. Tắt = DỪNG cả chia tự động '
             '(Pancake/TikTok/Facebook) LẪN chia thủ công (đẩy file/dán/round-robin). '
             'Đồng bộ giữa báo cáo dashboard và bảng Thêm KH mới.',
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
        """Bậc thang thưởng NV — ĐỌC TỪ CẤU HÌNH 'Thưởng cá nhân' (vd.bonus.personal).
        Cumulative: cộng dồn mốc của từng HĐ. HĐ vượt quá mốc cấu hình cao nhất →
        dùng mức của mốc cao nhất. Chưa cấu hình → fallback mốc cũ."""
        n = n_contracts or 0
        if n <= 0:
            return 0
        recs = self.env['vd.bonus.personal'].sudo().search([], order='contract_no')
        if recs:
            tiers = {r.contract_no: r.amount for r in recs}
            max_no = max(tiers)
            top = tiers[max_no]
            return sum(tiers.get(i, top) for i in range(1, n + 1))
        # Fallback khi CHƯA cấu hình mốc nào.
        TIERS = {1: 3_500_000, 2: 5_500_000, 3: 7_500_000, 4: 8_500_000, 5: 9_500_000}
        DEFAULT_HIGH = 9_500_000
        return sum(TIERS.get(i, DEFAULT_HIGH) for i in range(1, n + 1))

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
        5. CHIA ĐỀU TRONG NGÀY (user spec 2026-06-20): chọn NV được chia ÍT KHÁCH
           NHẤT HÔM NAY (giờ VN). Hoà → NV tải active ít hơn, rồi id nhỏ hơn.
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
        if source == 'pancake':
            # Pancake (user spec 2026-06-30): Trưởng nhóm / Giám đốc CŨNG nhận số
            # nếu đang BẬT — chỉ loại admin kỹ thuật. Union thêm họ (có thể không
            # nằm trong group_sale_salesman) rồi loại admin/system.
            bosses = self.sudo().search([
                ('share', '=', False), ('active', '=', True),
            ]).filtered(lambda u: u.vd_crm_role in ('team_leader', 'director'))
            if exclude_user_ids:
                _ex = set(exclude_user_ids)
                bosses = bosses.filtered(lambda u: u.id not in _ex)
            candidates = (candidates | bosses).filtered(
                lambda u: not (u._is_admin() or u.has_group('base.group_system')))
        else:
            # Kênh KHÁC: lead không phân cho lãnh đạo → loại Trưởng nhóm/Phó GĐ/Admin.
            candidates = candidates.filtered(
                lambda u: not u.has_group('vd_crm_lead.vd_crm_group_team_leader')
            )
        if preferred_team_id:
            team_members = candidates.filtered(
                lambda u: preferred_team_id in u.sale_team_id.ids if u.sale_team_id else False
            )
            if team_members:
                candidates = team_members
        Lead = self.env['crm.lead'].sudo()
        if source == 'pancake':
            # CHIA ĐỀU TUYỆT ĐỐI cho KH TikTok/Facebook (user spec 2026-06-23):
            # kênh Pancake CHỈ phụ thuộc nút BẬT/TẮT thủ công vd_can_receive_pancake
            # (admin tự tắt NV quá tải/nghỉ ngay trong báo cáo chia số). KHÔNG áp
            # cổng quá hạn / chặn tồn → để MỌI NV đang BẬT đều nhận đều như nhau.
            eligible = candidates.filtered('vd_can_receive_pancake')
            if not eligible:
                return self.env['res.users']  # empty
            # Cân bằng theo SỐ KH PANCAKE đã chia HÔM NAY (giờ VN) → cuối ngày mọi
            # NV bật nhận ~ bằng nhau. Hoà → tải active ít hơn, rồi id nhỏ hơn.
            today_map = Lead._vd_today_assigned_count_map(eligible.ids, pancake_only=True)
        else:
            # Kênh KHÁC (nhập tay / auto nội bộ): giữ cổng quá hạn + chặn tồn.
            # ĐỒNG BỘ (user spec 2026-07-24): công tắc vd_can_receive_pancake giờ
            # là công tắc nhận số DUY NHẤT — tắt NV = tắt cả tự động LẪN thủ công.
            eligible = candidates.filtered(
                lambda u: u.vd_can_receive_new_leads and u.vd_can_receive_pancake)
            if not eligible:
                return self.env['res.users']  # empty
            # CHẶN CHIA SỐ (user spec 2026-06-12): loại NV đang tồn >= ngưỡng KH
            # mới CHƯA gọi. Nếu TẤT CẢ đều đầy → fallback chọn NV ÍT tồn nhất
            # (auto KHÔNG được rớt lead).
            threshold = Lead._vd_distribute_block_threshold()
            if threshold > 0:
                uncalled = Lead._vd_uncalled_new_count_map(eligible.ids)
                with_cap = eligible.filtered(
                    lambda u: uncalled.get(u.id, 0) < threshold)
                if with_cap:
                    eligible = with_cap
                else:
                    return min(eligible, key=lambda u: uncalled.get(u.id, 0))
            # CHIA ĐỀU TRONG NGÀY (user spec 2026-06-20): NV ít số nhất hôm nay.
            today_map = Lead._vd_today_assigned_count_map(eligible.ids)

        def active_load(user):
            return Lead.search_count([
                ('user_id', '=', user.id),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ])
        return min(eligible, key=lambda u: (today_map.get(u.id, 0), active_load(u), u.id))

    # ============================================================
    # BẢNG QUẢN LÝ NHÂN VIÊN — 2 cột kéo thả (đang hoạt động / nghỉ-tạm dừng)
    # ============================================================
    _VD_TEAM_COLOR = {
        'HCM1': '#228be6', 'HCM2': '#15aabf', 'HCM3': '#0ca678',
        'HN': '#fa5252', 'QN': '#f59f00', 'CTV': '#12b886',
        'VINADUY': '#7048e8', 'KHÁC': '#868e96',
    }
    _VD_ROLE_LABEL = {
        'admin': 'Admin', 'director': 'Phó GĐ', 'team_leader': 'Trưởng nhóm',
        'employee': 'Nhân viên', 'collaborator': 'CTV',
    }

    def _vd_board_card(self, lead_count=0):
        """Dict 1 thẻ NV cho bảng quản lý. lead_count = số KH đang quản lý."""
        self.ensure_one()
        import re as _re
        full = self.name or self.login or ''
        # Bỏ tiền tố team "HCM2 - " để lấy tên thuần.
        m = _re.match(r'^\s*[A-Za-zÀ-ỹ0-9]+\s*-\s*(.+)$', full)
        pure = (m.group(1) if m else full).strip()
        # Mã icon = chữ cái đầu của 2-3 từ cuối (vd "Mai Thị Thao" → "MTT").
        words = [w for w in _re.split(r'\s+', pure) if w]
        code = ''.join(w[0] for w in words[-3:]).upper() if words else (self.login or '?')[:3].upper()
        team = self.vd_team_label or 'KHÁC'
        role = self.vd_crm_role or 'employee'
        return {
            'id': self.id,
            'name': pure or full,
            'code': code or '?',
            'team': team,
            'team_color': self._VD_TEAM_COLOR.get(team, '#868e96'),
            'role': role,
            'role_label': self._VD_ROLE_LABEL.get(role, 'Nhân viên'),
            'is_leader': role in ('team_leader', 'director'),
            'login': self.login or '',
            'active': bool(self.active),
            'lead_count': lead_count,
        }

    @api.model
    def vd_user_board_data(self):
        """Dữ liệu 2 bảng: NV đang hoạt động vs nghỉ việc/tạm dừng (archived).
        Chỉ NV nội bộ (share=False). Sắp theo team rồi tên."""
        users = self.sudo().with_context(active_test=False).search([
            ('share', '=', False),
        ])
        # Số KH mỗi NV đang quản lý (lead đang mở, gộp 1 query read_group).
        counts = {}
        groups = self.env['crm.lead'].sudo().read_group(
            [('user_id', 'in', users.ids)], ['user_id'], ['user_id'],
        )
        for g in groups:
            if g.get('user_id'):
                counts[g['user_id'][0]] = g['user_id_count']
        working, off = [], []
        for u in users:
            (working if u.active else off).append(
                u._vd_board_card(lead_count=counts.get(u.id, 0)))
        keyf = lambda c: (c['team'], c['name'].lower())
        return {
            'working': sorted(working, key=keyf),
            'off': sorted(off, key=keyf),
        }

    @api.model
    def vd_set_user_active(self, user_id, working):
        """Kéo thẻ giữa 2 bảng → archive/unarchive NV. Chỉ admin/quản lý.
        KHÔNG cho tự archive chính mình hoặc tài khoản admin gốc."""
        caller = self.env.user
        allowed = (
            caller._is_admin()
            or caller.has_group('sales_team.group_sale_manager')
            or caller.has_group('vd_crm_lead.vd_crm_group_team_leader')
        )
        if not allowed:
            from odoo.exceptions import AccessError
            raise AccessError('Chỉ admin / quản lý mới được đổi trạng thái nhân viên.')
        target = self.sudo().with_context(active_test=False).browse(int(user_id))
        if not target.exists():
            return False
        want = bool(working)
        if not want:
            # Chặn archive admin gốc + chính mình → tránh tự khoá.
            from odoo import SUPERUSER_ID
            if target.id in (SUPERUSER_ID, caller.id):
                from odoo.exceptions import UserError
                raise UserError('Không thể tạm dừng tài khoản admin gốc hoặc chính bạn.')
            # Chặn nghỉ việc khi NV còn khách trong tài khoản.
            n = self.env['crm.lead'].sudo().search_count([('user_id', '=', target.id)])
            if n:
                from odoo.exceptions import UserError
                raise UserError(
                    'Không thể cho nghỉ việc: %s còn %d khách trong tài khoản. '
                    'Hãy chuyển hết khách sang NV khác trước.' % (target.name, n))
        target.write({'active': want})
        return want

    @api.model
    def vd_toggle_pancake_receive(self, user_id):
        """BẬT/TẮT nhận KH Pancake cho 1 NV (gọi từ nút trên báo cáo chia số).
        Chỉ admin / quản lý CRM được phép. Trả về trạng thái mới (bool)."""
        caller = self.env.user
        allowed = (
            caller._is_admin()
            or caller.has_group('sales_team.group_sale_manager')
            or caller.has_group('vd_crm_lead.vd_crm_group_team_leader')
        )
        if not allowed:
            from odoo.exceptions import AccessError
            raise AccessError('Chỉ admin / quản lý mới được bật/tắt nhận số Pancake.')
        target = self.sudo().browse(int(user_id))
        if not target.exists():
            return False
        new_val = not bool(target.vd_can_receive_pancake)
        target.write({'vd_can_receive_pancake': new_val})
        return new_val
