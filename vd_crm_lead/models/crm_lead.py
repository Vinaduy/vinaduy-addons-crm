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
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# NV tồn >= ngưỡng này KH "chờ duyệt hủy" → phần mềm CHẶN không cho hủy thêm,
# ép trưởng phòng duyệt/từ chối bớt xuống DƯỚI ngưỡng (user spec 2026-06-21).
_VD_PENDING_CANCEL_BLOCK = 20


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ============ EXTENSIBLE SELECTION INFRA ============
    # Mỗi field liệt kê ở đây dùng `selection=callable` để merge base list
    # với records của vd.field.option (NV/admin thêm option qua UI "+ Thêm mới").
    _VD_EXT_SELECTIONS = {
        'vd_intake_house_type': [
            ('mai_bang', 'Nhà mái bằng'),
            ('mai_thai', 'Nhà mái thái'),
            ('mai_nhat', 'Nhà mái nhật'),
            ('mai_ton', 'Nhà mái tôn'),
        ],
        'vd_intake_foundation_type': [
            ('don', 'Móng đơn'),
            ('bang', 'Móng băng'),
            ('coc', 'Móng cọc'),
        ],
        'vd_intake_roof_type': [
            ('mai_bang', 'Mái bằng (20%)'),
            ('mai_nhat_kdt', 'Mái nhật — Không đổ trần (42%)'),
            ('mai_nhat_cdt', 'Mái nhật — Có đổ trần (48%)'),
            ('mai_thai_kdt', 'Mái thái — Không đổ trần (45%)'),
            ('mai_thai_cdt', 'Mái thái — Có đổ trần (55%)'),
            ('mai_ton', 'Mái tôn (13%)'),
            ('thong_tang', 'Thông tầng (40%)'),
            ('mai_trang_tri', 'Mái trang trí (50%)'),
            ('mai_trang_tri_dt', 'Mái trang trí — Đổ trần (100%)'),
            ('mai_ton_1m', 'Mái tôn 1 mặt (13%)'),
            ('mai_ton_2m', 'Mái tôn 2 mặt (16%)'),
            ('mai_ton_3m', 'Mái tôn 3 mặt (20%)'),
        ],
        'vd_intake_dimensions': [
            ('co_so_khong_phep', 'CÓ SỔ - Có cấp phép'),
            ('co_so_can_phep', 'Đang làm sổ đỏ'),
            ('khong_so_khong_phep', 'Không có sổ đỏ'),
        ],
        'vd_intake_land_type': [
            ('dat_cung', 'ĐẤT CỨNG - Liền thổ'),
            ('dat_yeu', 'ĐẤT YẾU - Ao ruộng san lấp'),
        ],
        'vd_intake_position': [
            ('mt_lon', 'Mặt tiền đường lớn'),
            ('mt_nho', 'Mặt tiền đường nhỏ'),
            ('xe_tai', 'Đường xe tải'),
            ('hem_xh', 'Hẻm xe hơi'),
            ('hem_xm', 'Hẻm xe máy'),
            ('cuoi_hem', 'Cuối hẻm'),
            ('khac', 'Khác'),
        ],
        'vd_intake_budget': [
            ('duoi_1ty', 'Dưới 1 tỷ'),
            ('1-3ty', '1–3 tỷ'),
            ('3-5ty', '3–5 tỷ'),
            ('5-10ty', '5–10 tỷ'),
            ('10-20ty', '10–20 tỷ'),
            ('tren_20ty', 'Trên 20 tỷ'),
            ('chua_xd', 'Chưa xác định'),
        ],
    }

    @api.model
    def _vd_ext_selection(self, fname):
        """Merge base selection + records từ vd.field.option."""
        base = list(self._VD_EXT_SELECTIONS.get(fname, []))
        try:
            extras = self.env['vd.field.option'].sudo().get_options(
                self._name, fname,
            )
        except Exception:
            extras = []
        keys = {k for k, _ in base}
        return base + [(k, l) for k, l in extras if k not in keys]

    def _vd_selection_dict(self, fname):
        """Resolve Selection field → dict {key: label}, hỗ trợ cả callable selection."""
        field = self._fields.get(fname)
        if not field:
            return {}
        sel = field.selection
        if callable(sel):
            sel = sel(self)
        return dict(sel or [])

    # Custom fields not in standard
    callback_date = fields.Datetime(string='Hẹn gọi lại lúc', tracking=True)

    # ============ PANCAKE INTEGRATION ============
    # 3 field này dùng để dedup + truy ngược về conversation Pancake.
    vd_pancake_page_id = fields.Many2one(
        'vd.pancake.page', string='Pancake Page', index=True, ondelete='set null',
        help='Page Pancake mà KH này đến từ.',
    )
    vd_pancake_conversation_id = fields.Char(
        string='Pancake Conversation ID', index=True, copy=False,
        help='ID conversation Pancake — dùng để dedup webhook tránh tạo lead 2 lần.',
    )
    vd_pancake_customer_id = fields.Char(
        string='Pancake Customer ID', index=True, copy=False,
        help='page_customer_id (UUID) của Pancake.',
    )

    # ============ DUPLICATE PHONE DETECTION + MERGE ============
    vd_duplicate_lead_ids = fields.One2many(
        'crm.lead', compute='_compute_vd_duplicates',
        string='Lead trùng SĐT',
        help='Các lead khác có cùng SĐT (chuẩn hóa) — chưa won/lost.',
    )
    vd_duplicate_count = fields.Integer(
        compute='_compute_vd_duplicates',
        string='Số lead trùng SĐT',
    )

    @api.depends('phone', 'mobile')
    def _compute_vd_duplicates(self):
        """Tìm lead khác có CÙNG SĐT (normalize digits-only). Skip won/lost."""
        for rec in self:
            phones = self._vd_normalize_phones_set(rec.phone, rec.mobile)
            if not phones:
                rec.vd_duplicate_count = 0
                rec.vd_duplicate_lead_ids = False
                continue
            # Search bằng OR multiple normalized variants
            all_leads = self.sudo().search([
                ('id', '!=', rec.id or 0),
                ('active', '=', True),
                '|', ('phone', '!=', False), ('mobile', '!=', False),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ])
            dupes = all_leads.filtered(
                lambda l: self._vd_normalize_phones_set(l.phone, l.mobile) & phones
            )
            rec.vd_duplicate_count = len(dupes)
            rec.vd_duplicate_lead_ids = dupes

    @api.model
    def _vd_normalize_phones_set(self, *phones):
        """Trả về set các phone đã normalize (digits only, strip leading 0/+84)."""
        import re
        result = set()
        for p in phones:
            if not p:
                continue
            digits = re.sub(r'\D', '', str(p))
            if not digits:
                continue
            # Strip country code + leading 0
            if digits.startswith('84') and len(digits) > 9:
                digits = digits[2:]
            elif digits.startswith('0'):
                digits = digits[1:]
            if len(digits) >= 6:    # phone hợp lệ tối thiểu 6 digits
                result.add(digits)
        return result

    def action_vd_merge_duplicates(self):
        """🔀 Gộp lead hiện tại với các lead trùng SĐT.
        Logic: giữ lead này làm KEEPER, archive (active=False) các lead khác,
        copy call history + chatter notes vào keeper.
        """
        self.ensure_one()
        if not self.vd_duplicate_lead_ids:
            raise UserError(_('Không có lead nào trùng SĐT.'))

        self._vd_absorb_dupes(self.vd_duplicate_lead_ids)
        # Reload form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _vd_absorb_dupes(self, dupes):
        """Gộp các lead `dupes` vào KEEPER (self): dồn lịch sử cuộc gọi + ghi chú,
        rồi archive dupes. Dùng chung cho nút gộp tay + cron tự động."""
        self.ensure_one()
        dupes = dupes.filtered(lambda d: d.id != self.id and d.active)
        if not dupes:
            return False
        merged_names = []
        for dup in dupes:
            if dup.call_ids:
                dup.call_ids.write({'lead_id': self.id})
            notes = dup.message_ids.filtered(
                lambda m: m.message_type in ('comment', 'notification') and m.body
            )[:5]
            owner_old = dup.user_id.name or '(chưa gán)'
            if notes:
                summary = '<br/>'.join(
                    f'<i>[{m.create_date.strftime("%d/%m/%Y")}]</i> {m.body}'
                    for m in notes
                )
            else:
                summary = '<i>(không có ghi chú)</i>'
            self.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('🔀 <b>Gộp từ lead "%s"</b> (ID %d, NV cũ: %s):<br/>%s')
                % (dup.name or 'KH', dup.id, owner_old, summary),
            )
            merged_names.append(f'#{dup.id} "{dup.name or "KH"}"')
            dup.with_context(skip_lost_archive=True).write({'active': False})
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_('✅ Đã gộp %d lead trùng SĐT vào lead này (NV quản lý: %s): %s')
            % (len(dupes), self.user_id.name or '(chưa gán)', ', '.join(merged_names)),
        )
        return True

    @api.model
    def _vd_cron_merge_dup_phones(self):
        """CRON: tự động gộp các lead TRÙNG SĐT (active, chưa won/lost) -> 1 KH 1 NV.
        Keeper = lead có NHIỀU cuộc gọi nhất (NV thực sự đang chăm); hoà thì lấy
        lead tạo SỚM NHẤT (first-touch). Các lead còn lại dồn cuộc gọi vào keeper
        rồi archive. An toàn: chạy sau khi cuộc gọi đã link xong."""
        leads = self.sudo().search([
            ('active', '=', True),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
            '|', ('phone', '!=', False), ('mobile', '!=', False),
        ])
        groups = {}
        for l in leads:
            for ph in self._vd_normalize_phones_set(l.phone, l.mobile):
                groups.setdefault(ph, self.browse())
                groups[ph] |= l
        merged_total = 0
        for ph, grp in groups.items():
            grp = grp.filtered(lambda x: x.active)
            if len(grp) < 2:
                continue
            keeper = grp.sorted(
                key=lambda c: (len(c.call_ids),
                               -(c.create_date.timestamp() if c.create_date else 0)),
                reverse=True,
            )[0]
            keeper._vd_absorb_dupes(grp - keeper)
            merged_total += len(grp) - 1
        return merged_total

    def action_vd_view_duplicates(self):
        """Mở list view các lead trùng SĐT để xem chi tiết trước khi gộp."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead trùng SĐT của "%s"') % (self.name or ''),
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.vd_duplicate_lead_ids.ids)],
            'target': 'new',
            'context': {'create': False, 'dialog_size': 'large'},
        }
    last_call_date = fields.Datetime(string='Lần gọi gần nhất', readonly=True)
    last_answered_date = fields.Datetime(string='Lần nghe máy gần nhất', readonly=True)
    no_answer_streak = fields.Integer(
        string='Số lần không nghe liên tiếp', default=0, readonly=True,
        help='Reset về 0 khi KH nghe máy.',
    )
    call_count = fields.Integer(
        string='Số lần gọi', default=0, readonly=True,
        compute='_compute_call_count', store=True,
        help='Auto-sync từ len(call_ids). User spec 2026-05-28: fix bug stale '
             '(trước đó dùng `lead.call_count + 1` trong _sync_lead_activity '
             'không bao giờ chạy vì _origin.id luôn truthy sau create).',
    )
    call_ids = fields.One2many('stringee.call', 'lead_id', string='Lịch sử gọi')

    # Track đổi NV quản lý KH (user spec 2026-06-22): mỗi lần đổi user_id ghi vào
    # chatter (mail.tracking.value) -> render bảng "Lịch sử chuyển NV" ở panel cuộc gọi.
    user_id = fields.Many2one('res.users', tracking=True)

    @api.depends('call_ids')
    def _compute_call_count(self):
        for rec in self:
            rec.call_count = len(rec.call_ids)

    # ===== Thống kê cuộc gọi + đánh giá KH tiềm năng =====
    vd_call_answered_count = fields.Integer(
        string='Số lần nghe máy', compute='_compute_call_stats', store=False,
    )
    vd_call_not_answered_count = fields.Integer(
        string='Số lần không nghe', compute='_compute_call_stats', store=False,
    )
    vd_lead_call_rating = fields.Selection([
        ('high', 'Nghe máy cao'),
        ('low', 'Nghe máy thấp'),
        ('none', 'Không nghe máy'),
        ('unreachable', 'Thuê bao'),
    ], string='Đánh giá KH tiềm năng', compute='_compute_call_stats', store=False)

    @api.depends('call_ids', 'call_ids.state', 'call_ids.duration',
                 'call_ids.recording_url', 'call_ids.recording_attachment_id',
                 'call_ids.answer_time', 'call_count')
    def _compute_call_stats(self):
        """Đánh giá 'nghe máy / không nghe' theo MỌI tín hiệu KH thực sự bắt máy:
        1. state == 'answered'                     → chắc chắn nghe
        2. answer_time có giá trị                  → Stringee ghi nhận pickup
        3. duration > 0                            → có thời gian đàm thoại
        4. recording_url / recording_attachment_id → có file ghi âm
                                                     (Stringee chỉ record sau khi
                                                      KH bắt máy, file = bằng chứng)
        → chỉ cần 1 trong 4 đúng = COUNT NGHE MÁY.

        State 'busy' / 'failed' / 'no_answer' / 'declined' / 'cancelled' không
        có 1 trong 4 trên = KHÔNG NGHE.
        """
        for rec in self:
            answered = 0
            not_answered = 0
            unreachable = 0
            for c in rec.call_ids:
                has_recording = bool(c.recording_url or c.recording_attachment_id)
                has_duration = (c.duration or 0) > 0
                has_answer_time = bool(c.answer_time)
                is_answered_state = c.state == 'answered'
                if is_answered_state or has_answer_time or has_duration or has_recording:
                    answered += 1
                elif c.state in ('busy', 'failed'):
                    unreachable += 1
                else:
                    not_answered += 1
            rec.vd_call_answered_count = answered
            rec.vd_call_not_answered_count = not_answered + unreachable

            total = answered + not_answered + unreachable
            if total == 0:
                rec.vd_lead_call_rating = False
            elif answered == 0 and unreachable >= max(1, total // 2):
                rec.vd_lead_call_rating = 'unreachable'
            elif answered == 0:
                rec.vd_lead_call_rating = 'none'
            else:
                rec.vd_lead_call_rating = 'high' if (answered / total) >= 0.5 else 'low'

    # ===== Báo cáo nhanh + lịch sử cuộc gọi SAU BÁO GIÁ (panel VẤN ĐỀ) =====
    vd_post_quote_call_report = fields.Html(
        string='Lịch sử cuộc gọi sau báo giá',
        compute='_compute_post_quote_call_report',
        store=False, sanitize=False,
    )

    # ===== KIỂM SOÁT CHĂM SÓC ZALO (Phase 1) — panel VẤN ĐỀ, chỉ sau báo giá =====
    vd_zalo_group_url = fields.Char(string='Link nhóm Zalo')
    vd_zalo_step_group = fields.Datetime(string='Zalo: đã tạo nhóm')
    vd_zalo_step_quote = fields.Datetime(string='Zalo: đã gửi báo giá')
    vd_zalo_step_model = fields.Datetime(string='Zalo: đã gửi mẫu nhà')
    vd_zalo_step_problem = fields.Datetime(string='Zalo: đã nhắn khai thác vấn đề')
    vd_zalo_problem_overdue = fields.Boolean(
        string='Zalo: quá hạn nhắn khai thác',
        compute='_compute_zalo_problem_overdue',
    )
    vd_zalo_problem_overdue_days = fields.Integer(
        string='Zalo: số ngày chưa nhắn khai thác',
        compute='_compute_zalo_problem_overdue',
    )

    @api.depends('vd_zalo_step_problem', 'vd_quote_created_date')
    def _compute_zalo_problem_overdue(self):
        """Đèn đỏ bước ④: sau báo giá mà NV chưa 'nhắn khai thác vấn đề' qua
        Zalo quá ngưỡng (default 2 ngày, chỉnh qua ir.config_parameter
        'vd_crm_lead.zalo_problem_overdue_days')."""
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'vd_crm_lead.zalo_problem_overdue_days', 2) or 2)
        now = fields.Datetime.now()
        for rec in self:
            days = 0
            overdue = False
            if rec.vd_quote_created_date and not rec.vd_zalo_step_problem:
                days = (now - rec.vd_quote_created_date).days
                overdue = days >= threshold
            rec.vd_zalo_problem_overdue_days = days
            rec.vd_zalo_problem_overdue = overdue

    # ----- CHĂM SÓC các ngày tiếp theo (cái cần kiểm soát chính) -----
    vd_zalo_last_care = fields.Datetime(string='Zalo: lần chăm sóc cuối')
    vd_zalo_care_count = fields.Integer(string='Zalo: tổng số lần chăm', default=0)
    # User spec 2026-06-07: NV bấm "TƯ VẤN QUA ZALO" → đánh dấu đã chuyển kênh
    # Zalo. KH đã tư vấn Zalo VÀ có báo giá chi tiết (vd_intake_complete) → MIỄN
    # yêu cầu gọi điện (call-watch). Chưa có báo giá thì vẫn phải gọi đủ.
    vd_zalo_consulted_date = fields.Datetime(
        string='Zalo: bắt đầu tư vấn', copy=False, readonly=True,
        help='Set khi xác nhận NGÀY 1. Miễn khoá "chưa gọi" khi KH đã có báo giá '
             'chi tiết.',
    )
    # User spec 2026-06-10: NV bấm "KHÔNG TÌM THẤY ZALO" khi SĐT khách không có
    # Zalo / không tìm được → khỏi ép nhắn Zalo nữa; thẻ hiện icon Zalo XÁM.
    vd_zalo_not_found = fields.Boolean(
        string='Không tìm thấy Zalo', default=False, copy=False,
        help='Khách không có Zalo / không tìm thấy → bỏ khỏi diện ép nhắn Zalo.')
    # User spec 2026-06-10: NV (chủ KH) đã nhắn ĐỦ hạn mức Zalo hôm nay (mặc định
    # 15) → nút "NHẮN ZALO" chuyển VÀNG báo "mai nhắn tiếp" thay vì lỗi im lặng.
    vd_zalo_msg_cap_reached = fields.Boolean(
        string='Đã đủ hạn mức nhắn Zalo hôm nay',
        compute='_compute_vd_zalo_msg_cap_reached', store=False)

    def _compute_vd_zalo_msg_cap_reached(self):
        cap, _w = self._vd_zalo_friend_cap()
        for rec in self:
            user = rec.user_id or rec.env.user
            rec.vd_zalo_msg_cap_reached = bool(
                user and rec._vd_zalo_friend_today(user) >= cap)
    # Đã phát sinh ≥1 CUỘC GỌI THẬT (đã đổ chuông/nghe máy) — user spec 2026-06-07.
    # Điều kiện hiện nút Zalo + bảng hướng dẫn. Loại cuộc 'failed'/'cancelled'.
    vd_has_real_call = fields.Boolean(
        string='Đã có cuộc gọi thật', compute='_compute_vd_has_real_call',
        store=False)

    @api.depends('call_ids', 'call_ids.state', 'call_ids.answer_time',
                 'call_ids.duration', 'call_ids.recording_url',
                 'call_ids.recording_attachment_id', 'call_ids.direction')
    def _compute_vd_has_real_call(self):
        # User spec 2026-06-07: cuộc gọi THẬT = đã gọi đi tới nhà mạng, KỂ CẢ
        # bận/thuê bao/sai số/đổ chuông không nghe/từ chối. CHỈ loại 'cancelled'
        # (bấm gọi rồi tắt luôn, chưa đi đâu) — trừ khi nó đã đổ chuông (duration).
        real_states = ('answered', 'ended', 'no_answer', 'busy', 'declined', 'failed')
        for rec in self:
            rec.vd_has_real_call = any(
                c.direction == 'outbound' and (
                    c.state in real_states
                    or c.answer_time or (c.duration or 0) > 0
                    or c.recording_url or c.recording_attachment_id
                )
                for c in rec.call_ids
            )
    # Quy trình chăm Zalo 3 NGÀY (user spec 2026-06-07) — mỗi bước xác nhận ở 1
    # NGÀY khác nhau, trong hạn 7 ngày (tạo → chuyển bảng "không gọi được").
    vd_zalo_day1_date = fields.Datetime(
        string='Zalo Ngày 1: Kết bạn + chào', copy=False, readonly=True)
    vd_zalo_day2_date = fields.Datetime(
        string='Zalo Ngày 2: Gọi + nhắn', copy=False, readonly=True)
    vd_zalo_day3_date = fields.Datetime(
        string='Zalo Ngày 3: Gọi + nhắn', copy=False, readonly=True)
    vd_zalo_care_deadline = fields.Datetime(
        string='Hạn chăm Zalo (7 ngày)', compute='_compute_vd_zalo_care', store=False)
    vd_zalo_care_html = fields.Html(
        string='Lịch sử chăm Zalo', compute='_compute_vd_zalo_care',
        sanitize=False, store=False)
    # Cờ "đã sang ngày mới để hiện bước kế" (user spec 2026-06-07): Ngày 2 chỉ
    # hiện khi đã SANG NGÀY sau Ngày 1; Ngày 3 chỉ hiện khi đã sang ngày sau Ngày 2.
    vd_zalo_day2_available = fields.Boolean(
        compute='_compute_vd_zalo_care', store=False)
    vd_zalo_day3_available = fields.Boolean(
        compute='_compute_vd_zalo_care', store=False)

    _ZALO_DAY_LABELS = {
        1: 'Nhắn tin Zalo chào khách (kết bạn khi khách trả lời)',
        2: 'Gọi điện và nhắn tin qua Zalo',
        3: 'Gọi điện và nhắn tin qua Zalo',
    }

    @api.depends('vd_zalo_day1_date', 'vd_zalo_day2_date', 'vd_zalo_day3_date',
                 'create_date')
    def _compute_vd_zalo_care(self):
        for rec in self:
            deadline = (rec.create_date + timedelta(days=7)) if rec.create_date else False
            rec.vd_zalo_care_deadline = deadline
            # Cờ hiện bước kế: đã xác nhận bước trước VÀ hôm nay đã SANG NGÀY KHÁC.
            today = fields.Date.context_today(rec)
            d1 = fields.Datetime.context_timestamp(rec, rec.vd_zalo_day1_date).date() if rec.vd_zalo_day1_date else None
            d2 = fields.Datetime.context_timestamp(rec, rec.vd_zalo_day2_date).date() if rec.vd_zalo_day2_date else None
            rec.vd_zalo_day2_available = bool(rec.vd_zalo_day2_date) or bool(d1 and today > d1)
            rec.vd_zalo_day3_available = bool(rec.vd_zalo_day3_date) or bool(d2 and today > d2)
            rows = []
            for n, dt in ((1, rec.vd_zalo_day1_date), (2, rec.vd_zalo_day2_date),
                          (3, rec.vd_zalo_day3_date)):
                label = rec._ZALO_DAY_LABELS[n]
                if dt:
                    ts = fields.Datetime.context_timestamp(rec, dt).strftime('%H:%M · %d/%m/%Y')
                    rows.append(
                        '<div class="o_vd_zcare_row o_vd_zcare_done">'
                        '<span class="o_vd_zcare_ico">✅</span>'
                        '<span class="o_vd_zcare_lbl"><b>NGÀY %d:</b> %s</span>'
                        '<span class="o_vd_zcare_meta">%s</span></div>' % (n, label, ts))
                else:
                    rows.append(
                        '<div class="o_vd_zcare_row o_vd_zcare_todo">'
                        '<span class="o_vd_zcare_ico">⬜</span>'
                        '<span class="o_vd_zcare_lbl"><b>NGÀY %d:</b> %s</span>'
                        '<span class="o_vd_zcare_meta">chưa xác nhận</span></div>' % (n, label))
            dl_html = ''
            if deadline:
                dl_local = fields.Datetime.context_timestamp(rec, deadline)
                days_left = (dl_local.date() - fields.Date.context_today(rec)).days
                cls = 'o_vd_zcare_dl_over' if days_left < 0 else 'o_vd_zcare_dl'
                txt = ('QUÁ HẠN %d ngày' % (-days_left)) if days_left < 0 else ('còn %d ngày' % days_left)
                dl_html = ('<div class="%s">⏳ Hạn chăm Zalo: <b>%s</b> (%s)</div>'
                           % (cls, dl_local.strftime('%d/%m/%Y'), txt))
            html = (
                '<div class="o_vd_zcare_title">💬 ĐANG TƯ VẤN QUA ZALO ĐỂ LẤY THÔNG TIN</div>'
                '<div class="o_vd_zcare">' + ''.join(rows) + dl_html + '</div>')
            # Sau khi có BÁO GIÁ → thêm phần KHAI THÁC VẤN ĐỀ (user spec 2026-06-07).
            if rec.vd_intake_complete:
                open_n = rec.vd_lead_problem_open_count or 0
                note = ('Tiếp tục khai thác &amp; xử lý <b>%d vấn đề</b> của khách qua Zalo.'
                        % open_n) if open_n else 'Tiếp tục khai thác vấn đề của khách qua Zalo.'
                html += (
                    '<div class="o_vd_zcare_title o_vd_zcare_title2">🔍 ĐANG KHAI THÁC VẤN ĐỀ</div>'
                    '<div class="o_vd_zcare2">' + note + '</div>')
            rec.vd_zalo_care_html = html
    vd_zalo_care_overdue = fields.Boolean(
        string='Zalo: quá hạn chăm sóc', compute='_compute_zalo_care_overdue',
    )
    vd_zalo_care_overdue_days = fields.Integer(
        string='Zalo: số ngày chưa chăm', compute='_compute_zalo_care_overdue',
    )

    @api.depends('vd_zalo_last_care', 'vd_quote_created_date')
    def _compute_zalo_care_overdue(self):
        """Đèn đỏ chăm sóc: số ngày kể từ LẦN CHĂM CUỐI (nếu chưa chăm lần nào
        thì tính từ ngày báo giá). Quá ngưỡng (default 2 ngày, config
        'vd_crm_lead.zalo_care_overdue_days') → đỏ."""
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'vd_crm_lead.zalo_care_overdue_days', 2) or 2)
        now = fields.Datetime.now()
        for rec in self:
            anchor = rec.vd_zalo_last_care or rec.vd_quote_created_date
            days = 0
            overdue = False
            if rec.vd_quote_created_date and anchor:
                days = (now - anchor).days
                overdue = days >= threshold
            rec.vd_zalo_care_overdue_days = days
            rec.vd_zalo_care_overdue = overdue

    def action_zalo_log_care(self):
        """Ghi nhận 'đã chăm khách hôm nay' → cập nhật lần cuối + tăng đếm."""
        self.ensure_one()
        self.vd_zalo_last_care = fields.Datetime.now()
        self.vd_zalo_care_count = (self.vd_zalo_care_count or 0) + 1

    def action_open_zalo_chat(self):
        """Mở Zalo của KH theo SĐT (zalo.me/<sđt>) → vào profile KH, bấm Nhắn tin.
        Zalo KHÔNG hỗ trợ deep-link thẳng vào hộp thoại — đây là cách gần nhất."""
        self.ensure_one()
        phone = ''.join(ch for ch in (self.phone or self.mobile or '') if ch.isdigit())
        if not phone:
            raise UserError(_('KH chưa có số điện thoại để mở Zalo.'))
        return {'type': 'ir.actions.act_url', 'url': f'https://zalo.me/{phone}', 'target': 'new'}

    def action_vd_zalo_confirm_day(self, day):
        """Xác nhận 1 bước chăm Zalo (user spec 2026-06-07).
        - NGÀY 1: Kết bạn + gửi tin chào.  NGÀY 2/3: Gọi + nhắn qua Zalo.
        - NGÀY N chỉ xác nhận được khi NGÀY N-1 đã xác nhận VÀ vào NGÀY KHÁC.
        - NGÀY 1 set vd_zalo_consulted_date → miễn khoá "chưa gọi" khi có báo giá."""
        self.ensure_one()
        from odoo.exceptions import UserError
        day = int(day)
        field_by_day = {1: 'vd_zalo_day1_date', 2: 'vd_zalo_day2_date', 3: 'vd_zalo_day3_date'}
        if day not in field_by_day:
            return False
        fname = field_by_day[day]
        if self[fname]:
            return True  # đã xác nhận rồi
        if day > 1 and not self[field_by_day[day - 1]]:
            raise UserError(_('Phải xác nhận NGÀY %d trước.') % (day - 1))
        if day > 1:
            prev_d = fields.Datetime.context_timestamp(self, self[field_by_day[day - 1]]).date()
            today = fields.Date.context_today(self)
            if today <= prev_d:
                raise UserError(_(
                    'NGÀY %d phải xác nhận vào NGÀY KHÁC (sau NGÀY %d) — mỗi ngày '
                    'chỉ xác nhận 1 bước.') % (day, day - 1))
        # HẠN MỨC KẾT BẠN ZALO/NGÀY (user spec 2026-06-09): NGÀY 1 = kết bạn mới.
        # Chặn khi NV đã đạt hạn mức để Zalo KHÔNG khoá tài khoản cá nhân của NV.
        if day == 1:
            self._vd_check_zalo_friend_daily_cap()
        now = fields.Datetime.now()
        self[fname] = now
        if not self.vd_zalo_consulted_date:
            self.vd_zalo_consulted_date = now
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_('💬 Zalo NGÀY %d: %s') % (day, self._ZALO_DAY_LABELS[day]))
        return True

    def action_vd_zalo_not_found(self):
        """User spec 2026-06-10: SĐT khách KHÔNG có Zalo / không tìm thấy → đánh
        dấu vd_zalo_not_found (bỏ khỏi diện ép nhắn Zalo, thẻ hiện icon Zalo xám)."""
        self.ensure_one()
        if not self.vd_zalo_not_found:
            self.vd_zalo_not_found = True
            self.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('🚫 Đã đánh dấu <b>KHÔNG TÌM THẤY ZALO</b> của khách này.'))
        return True

    def _vd_zalo_friend_today(self, user=None):
        """Số KH mà NV (user) đã KẾT BẠN Zalo (vd_zalo_day1_date) trong HÔM NAY."""
        user = user or self.user_id or self.env.user
        today = fields.Date.context_today(self)
        start = fields.Datetime.to_datetime(today)
        return self.env['crm.lead'].sudo().search_count([
            ('user_id', '=', user.id),
            ('vd_zalo_day1_date', '>=', start),
            ('vd_zalo_day1_date', '<', start + timedelta(days=1)),
        ])

    def _vd_zalo_friend_cap(self):
        """(cap, warn) hạn mức kết bạn Zalo/ngày — chỉnh qua System Parameter
        vd_crm_lead.zalo_friend_daily_cap / _warn. Mặc định 15 / 10."""
        ICP = self.env['ir.config_parameter'].sudo()
        cap = int(ICP.get_param('vd_crm_lead.zalo_friend_daily_cap', 15) or 15)
        warn = int(ICP.get_param('vd_crm_lead.zalo_friend_daily_warn', 10) or 10)
        return cap, warn

    def _vd_check_zalo_friend_daily_cap(self):
        """Chặn kết bạn Zalo khi NV đã đạt hạn mức/ngày (user spec 2026-06-09).
        Kết bạn quá nhiều/ngày → Zalo khoá tính năng kết bạn / khoá tài khoản NV."""
        self.ensure_one()
        from odoo.exceptions import UserError
        user = self.user_id or self.env.user
        cap, _warn = self._vd_zalo_friend_cap()
        done = self._vd_zalo_friend_today(user)
        if done >= cap:
            raise UserError(_(
                '🔒 Hôm nay bạn đã NHẮN ZALO %d khách — ĐẠT HẠN MỨC AN TOÀN '
                '(%d/ngày).\n\nNhắn người lạ quá nhiều trong ngày khiến Zalo HẠN '
                'CHẾ/KHOÁ tài khoản. Hãy chăm tiếp các khách đã nhắn hôm nay '
                '(kết bạn khi khách trả lời); mai nhắn thêm khách mới.'
            ) % (done, cap))

    def vd_dashboard_zalo_friend(self):
        """Dashboard: kết bạn Zalo (NGÀY 1) + trả tiến độ hạn mức để toast cảnh
        báo. action_vd_zalo_confirm_day đã tự kiểm tra/chặn hạn mức."""
        self.ensure_one()
        self.action_vd_zalo_confirm_day(1)
        cap, warn = self._vd_zalo_friend_cap()
        done = self._vd_zalo_friend_today()
        return {'done': done, 'cap': cap, 'warn': warn}

    # ===== LÀM HỢP ĐỒNG - HẸN GẶP — nút Xem/Tải HĐ + Phụ lục.
    # Auto-gen từ mẫu (.docx) trộn dữ liệu KH + bảng giá + đợt ứng: xử lý sau. =====
    def action_view_contract_file(self):
        return self._vd_contract_pending('HỢP ĐỒNG')

    def action_download_contract_file(self):
        return self._vd_contract_pending('HỢP ĐỒNG')

    def action_view_appendix_file(self):
        return self._vd_contract_pending('PHỤ LỤC')

    def action_download_appendix_file(self):
        return self._vd_contract_pending('PHỤ LỤC')

    def _vd_contract_pending(self, doc):
        self.ensure_one()
        raise UserError(_(
            'Chưa cấu hình MẪU %s. Gửi file mẫu (.docx) cho admin để thiết lập '
            'tự động trộn: tên KH, địa chỉ, thông tin công trình, bảng giá chi '
            'tiết và các đợt thanh toán.'
        ) % doc)

    # Panel "Làm hợp đồng - Hẹn gặp" chỉ bung khi NV bấm nút (không tự hiện).
    vd_contract_open = fields.Boolean(string='Mở panel làm hợp đồng', default=False, copy=False)

    def action_toggle_contract_panel(self):
        self.ensure_one()
        self.vd_contract_open = not self.vd_contract_open
        return True

    # ===== CẦN CẤP TRÊN HỖ TRỢ — NV bấm 🆘 cuối dòng KH ở dashboard.
    # User spec 2026-05-31: ĐÃ BẤM thì KHÔNG huỷ được; 2 chế độ: trong ngày /
    # nhiều ngày (đến khi chốt); mỗi NV tối đa 3 KH active cùng lúc. =====
    vd_need_help = fields.Boolean(string='Cần cấp trên hỗ trợ', default=False)
    vd_need_help_at = fields.Datetime(string='Thời điểm yêu cầu hỗ trợ')
    vd_need_help_scope = fields.Selection([
        ('today', 'Trong ngày'),
        ('multi', 'Nhiều ngày — đến khi chốt'),
    ], string='Phạm vi hỗ trợ', default='today')
    vd_help_status = fields.Selection([
        ('waiting', 'Chờ hỗ trợ'),     # đỏ nhấp nháy — NV đã gửi, chưa ai tới
        ('helping', 'Đang hỗ trợ'),    # xanh — cấp trên đang hỗ trợ
    ], string='Trạng thái hỗ trợ')

    def _vd_need_help_active(self, today_d):
        """Cờ hỗ trợ còn hiệu lực? multi = đến khi chốt; today = chỉ hôm nay.
        KH đã won/lost → hết hiệu lực."""
        self.ensure_one()
        if not self.vd_need_help or not self.vd_need_help_at:
            return False
        if self.stage_is_won or self.stage_is_lost:
            return False
        if self.vd_need_help_scope == 'multi':
            return True
        return fields.Datetime.context_timestamp(self, self.vd_need_help_at).date() == today_d

    def vd_request_help(self):
        """NV gửi yêu cầu hỗ trợ. Scope qua context {'help_scope': 'today'|'multi'}.
        KHÔNG có chức năng tắt — đã gửi là cấp trên xử lý. Chỉ cho NÂNG today → multi."""
        self.ensure_one()
        scope = self.env.context.get('help_scope', 'today')
        if scope not in ('today', 'multi'):
            scope = 'today'
        today_d = fields.Date.context_today(self)
        if self._vd_need_help_active(today_d):
            # Đã bật — chỉ cho nâng cấp today → multi (không hạ, không tắt).
            if scope == 'multi' and self.vd_need_help_scope != 'multi':
                self.write({'vd_need_help_scope': 'multi'})
            return True
        # Chưa active → check giới hạn 3 KH active của NV phụ trách
        candidates = self.search([
            ('user_id', '=', self.user_id.id),
            ('vd_need_help', '=', True),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
            ('id', '!=', self.id),
        ])
        active_n = sum(1 for c in candidates if c._vd_need_help_active(today_d))
        if active_n >= 3:
            raise UserError(_(
                'NV %s đang cần hỗ trợ tối đa 3 KH. Chờ cấp trên xử lý xong bớt '
                'rồi mới gửi thêm.'
            ) % (self.user_id.name or ''))
        self.write({
            'vd_need_help': True,
            'vd_need_help_at': fields.Datetime.now(),
            'vd_need_help_scope': scope,
            'vd_help_status': 'waiting',
        })
        return True

    def vd_ack_help(self):
        """Cấp trên bấm 'Đang hỗ trợ' → chuyển đỏ (chờ) sang xanh (đang hỗ trợ)."""
        self.ensure_one()
        if self.vd_need_help and self.vd_help_status == 'waiting':
            self.write({'vd_help_status': 'helping'})
        return True

    def vd_done_help(self):
        """Cấp trên bấm 'Hoàn tất' → kết thúc yêu cầu hỗ trợ (xoá cờ)."""
        self.ensure_one()
        self.write({'vd_need_help': False, 'vd_help_status': False})
        return True

    @api.depends('call_ids', 'call_ids.state', 'call_ids.duration',
                 'call_ids.start_time', 'call_ids.recording_url',
                 'vd_quote_created_date')
    def _compute_post_quote_call_report(self):
        """Báo cáo nhanh + lịch sử cuộc gọi KỂ TỪ ngày báo giá thành công
        (vd_quote_created_date). Phân loại: ✅ nghe máy (state ended/answered +
        duration>0) / 🔕 cố tình không nghe (no_answer/busy/declined) /
        📵 thuê bao (failed). Hiển thị trong panel VẤN ĐỀ trên form KH."""
        for rec in self:
            # Fallback create_date nếu chưa có latch vd_quote_created_date → báo cáo
            # LUÔN hiện khi panel VẤN ĐỀ hiện (user spec 2026-05-31).
            since = rec.vd_quote_created_date or rec.create_date
            if not since:
                rec.vd_post_quote_call_report = ''
                continue
            calls = rec.call_ids.filtered(
                lambda c: c.start_time and c.start_time >= since
            ).sorted(key=lambda c: c.start_time, reverse=True)
            ans = refuse = sub = 0
            days = set()
            for c in calls:
                dur = c.duration or 0
                days.add(c.start_time.date())
                if c.state in ('answered', 'ended') and dur > 0:
                    ans += 1
                elif c.state == 'failed':
                    sub += 1
                else:
                    refuse += 1
            total = ans + refuse + sub

            noans = refuse + sub  # "không nghe" = cố tình không nghe + thuê bao
            # Đánh giá (giống vd_lead_call_rating) → render thẻ badge như Hình 2.
            if total == 0:
                rclass, rtext = '', ''
            elif ans == 0 and sub >= max(1, total // 2):
                rclass, rtext = 'unreachable', '📵 Thuê bao'
            elif ans == 0:
                rclass, rtext = 'none', '🚫 Không nghe máy'
            elif (ans / total) >= 0.5:
                rclass, rtext = 'high', '🔥 Nghe máy cao'
            else:
                rclass, rtext = 'low', '⚖️ Nghe máy thấp'
            rating_html = (
                f'<span class="o_vd_cs_sep">|</span>'
                f'<span class="o_vd_cs_part o_vd_cs_rating">'
                f'<span class="o_vd_cr_badge o_vd_cr_{rclass}">{rtext}</span></span>'
            ) if rclass else ''
            # User spec 2026-05-31 (cập nhật #3): BỎ pill "⏳ X ngày từ báo giá"
            # theo yêu cầu user — chỉ còn ✓ Nghe máy | ✗ Không nghe | thẻ đánh giá.
            rec.vd_post_quote_call_report = (
                f'<span style="display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap;">'
                f'<span class="o_vd_call_stats_chip">'
                f'<span class="o_vd_cs_part o_vd_cs_yes"><i class="fa fa-check-circle"></i>'
                f'<span class="o_vd_cs_lbl">Nghe máy:</span> <span class="o_vd_cs_val">{ans}</span></span>'
                f'<span class="o_vd_cs_sep">|</span>'
                f'<span class="o_vd_cs_part o_vd_cs_no"><i class="fa fa-times-circle"></i>'
                f'<span class="o_vd_cs_lbl">Không nghe:</span> <span class="o_vd_cs_val">{noans}</span></span>'
                f'{rating_html}'
                f'</span>'
                f'</span>'
            )

    # ===== LỊCH SỬ CUỘC GỌI TÁCH 2 BẢNG (sau / trước báo giá) — HOVER panel =====
    # User spec 2026-05-31: hover (không click) trên 2 nút "Lịch sử cuộc gọi"
    # (Thông tin tư vấn + Vấn đề) → bung CÙNG panel chứa 2 bảng xếp chồng:
    #   • TRÊN  = cuộc gọi SAU báo giá (start_time >= vd_quote_created_date)
    #   • DƯỚI  = cuộc gọi TRƯỚC báo giá (tạo KH → ngày báo giá)
    # Chưa có vd_quote_created_date → tất cả vào bảng TRƯỚC, bảng SAU rỗng.
    vd_call_history_split = fields.Html(
        string='Lịch sử cuộc gọi (tách trước/sau báo giá)',
        compute='_compute_call_history_split',
        store=False, sanitize=False,
    )

    # Nhãn trạng thái cuộc gọi (đồng bộ selection ở vd_stringee/stringee_call).
    _VD_CALL_STATE_LABELS = {
        'draft': 'Chưa khởi tạo', 'initiated': 'Đã khởi tạo', 'ringing': 'Đang đổ chuông',
        'answered': 'Đã trả lời', 'ended': 'Đã kết thúc', 'no_answer': 'Không nghe máy',
        'busy': 'Máy bận', 'declined': 'Từ chối', 'cancelled': 'Đã huỷ', 'failed': 'Lỗi',
    }

    def _vd_render_call_rows(self, calls):
        """Render các <tr> cho 1 bảng lịch sử cuộc gọi (đã sort sẵn)."""
        self.ensure_one()
        labels = self._VD_CALL_STATE_LABELS
        rows = []
        for c in calls:
            when = (
                fields.Datetime.context_timestamp(self, c.start_time).strftime('%d/%m/%Y %H:%M:%S')
                if c.start_time else '—'
            )
            dur = c.duration or 0
            dur_s = '%02d:%02d' % (dur // 60, dur % 60)
            is_ans = c.state in ('answered', 'ended') and dur > 0
            if is_ans:
                bg, fg = '#e6f7ed', '#0b7a3b'
            elif c.state == 'failed':
                bg, fg = '#f1f3f5', '#868e96'
            else:
                bg, fg = '#fff0f0', '#c92a2a'
            st = labels.get(c.state, c.state or '—')
            if c.recording_attachment_id:
                aid = c.recording_attachment_id.id
                rec_html = (
                    f'<audio controls preload="none" class="o_vd_chs_audio" '
                    f'src="/web/content/{aid}?download=false"></audio>'
                    f'<a href="/web/content/{aid}?download=true" class="o_vd_chs_dl" '
                    f'title="Tải ghi âm" download="">⬇</a>'
                )
            elif c.recording_url:
                rec_html = (
                    f'<a href="{c.recording_url}" target="_blank" '
                    f'class="o_vd_chs_dl">Nghe</a>'
                )
            else:
                rec_html = '<span style="color:#adb5bd;">—</span>'
            caller_nv = (c.user_id.name or '—') if c.user_id else '—'
            rows.append(
                f'<tr><td>{when}</td>'
                f'<td>{c.caller_number or "—"}</td>'
                f'<td>{c.callee_number or "—"}</td>'
                f'<td style="white-space:nowrap;font-weight:600;">{caller_nv}</td>'
                f'<td style="text-align:right;white-space:nowrap;">{dur_s}</td>'
                f'<td><span style="background:{bg};color:{fg};border-radius:6px;'
                f'padding:1px 7px;font-weight:700;white-space:nowrap;">{st}</span></td>'
                f'<td class="o_vd_chs_rec">{rec_html}</td></tr>'
            )
        return ''.join(rows)

    def _vd_render_call_table(self, title, subtitle, calls, accent):
        """Render 1 block bảng (header + table)."""
        self.ensure_one()
        head = (
            '<tr><th>Thời điểm</th><th>Từ số</th><th>Đến số</th>'
            '<th>Người gọi</th>'
            '<th style="text-align:right;">Thời lượng</th><th>Trạng thái</th>'
            '<th>Ghi âm</th></tr>'
        )
        if calls:
            body = self._vd_render_call_rows(calls)
        else:
            body = (
                '<tr><td colspan="7" style="text-align:center;color:#adb5bd;'
                'padding:14px;font-style:italic;">Chưa có cuộc gọi</td></tr>'
            )
        return (
            f'<div class="o_vd_chs_block">'
            f'<div class="o_vd_chs_head" style="border-left:4px solid {accent};">'
            f'<span class="o_vd_chs_title">{title}</span>'
            f'<span class="o_vd_chs_sub">{subtitle}</span>'
            f'<span class="o_vd_chs_count">{len(calls)}</span></div>'
            f'<table class="o_vd_chs_table"><thead>{head}</thead>'
            f'<tbody>{body}</tbody></table></div>'
        )

    def _vd_render_owner_log(self):
        """Bảng LỊCH SỬ CHUYỂN NV QUẢN LÝ — đọc từ mail.tracking.value (field user_id)."""
        self.ensure_one()
        entries = []
        # sudo: field mail.message.tracking_value_ids chi cho nhom Admin/Settings
        # -> NV thuong doc se bi Access Error. Doc qua sudo (chi de render bang lich su).
        msgs = self.sudo().message_ids.sorted(
            key=lambda x: x.date or fields.Datetime.now(), reverse=True)
        for m in msgs:
            for tv in m.tracking_value_ids:
                fname = tv.field_id.name if tv.field_id else ''
                if fname != 'user_id':
                    continue
                when = (fields.Datetime.context_timestamp(self, m.date).strftime('%d/%m/%Y %H:%M')
                        if m.date else '—')
                old = tv.old_value_char or '— (chưa gán)'
                new = tv.new_value_char or '— (bỏ gán)'
                by = (m.author_id.name if m.author_id else '') or 'Hệ thống'
                entries.append((when, old, new, by))
        head = ('<tr><th>Thời điểm</th><th>NV cũ</th><th>NV mới</th>'
                '<th>Người chuyển</th></tr>')
        if entries:
            body = ''.join(
                f'<tr><td>{w}</td><td>{o}</td>'
                f'<td style="font-weight:700;color:#0b7a3b;">{n}</td><td>{b}</td></tr>'
                for (w, o, n, b) in entries
            )
        else:
            body = ('<tr><td colspan="4" style="text-align:center;color:#adb5bd;'
                    'padding:14px;font-style:italic;">Chưa có lịch sử chuyển nhân viên</td></tr>')
        return (
            '<div class="o_vd_chs_block">'
            '<div class="o_vd_chs_head" style="border-left:4px solid #7048e8;">'
            '<span class="o_vd_chs_title">🔄 Lịch sử chuyển NV quản lý</span>'
            f'<span class="o_vd_chs_count">{len(entries)}</span></div>'
            f'<table class="o_vd_chs_table"><thead>{head}</thead>'
            f'<tbody>{body}</tbody></table></div>'
        )

    @api.depends('call_ids', 'call_ids.state', 'call_ids.duration', 'call_ids.start_time',
                 'call_ids.caller_number', 'call_ids.callee_number', 'call_ids.user_id',
                 'call_ids.recording_url', 'call_ids.recording_attachment_id',
                 'vd_quote_created_date', 'message_ids')
    def _compute_call_history_split(self):
        for rec in self:
            all_calls = rec.call_ids.sorted(
                key=lambda c: (c.start_time or fields.Datetime.to_datetime('1970-01-01')),
                reverse=True,
            )
            since = rec.vd_quote_created_date
            if since:
                after = all_calls.filtered(lambda c: c.start_time and c.start_time >= since)
                before = all_calls.filtered(lambda c: not c.start_time or c.start_time < since)
                since_str = fields.Datetime.context_timestamp(rec, since).strftime('%d/%m/%Y')
                sub_after = f'kể từ {since_str}'
                sub_before = f'tạo KH → {since_str}'
            else:
                after = rec.call_ids.browse()
                before = all_calls
                sub_after = 'chưa có báo giá'
                sub_before = 'từ tạo KH đến nay'
            tbl_after = rec._vd_render_call_table(
                '📞 Sau báo giá', sub_after, after, '#e8590c')
            tbl_before = rec._vd_render_call_table(
                '☎️ Trước báo giá', sub_before, before, '#1971c2')
            owner_log = rec._vd_render_owner_log()
            rec.vd_call_history_split = (
                f'<div class="o_vd_chs_wrap">{tbl_after}{tbl_before}{owner_log}</div>'
            )

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
    # Cuộc gọi gần nhất ĐÃ KẾT THÚC (terminal state, end_time < 5 phút) — dùng
    # để hiện note "Cuộc gọi đã kết thúc" trong popup. Tự ẩn sau 5 phút.
    vd_last_call_end_msg = fields.Char(compute='_compute_last_call_end_msg')

    # Toggle "phiếu khai thác" — False = chế độ tóm tắt (compact card),
    # True = chế độ mở rộng (form fields hiện đầy đủ + sheet wider + sidebar
    # bong bóng kịch bản). Mặc định False; bật khi NV bấm Gọi hoặc nút "Mở
    # khai thác". Tắt khi NV bấm "Lưu & Hoàn tất".
    vd_intake_open = fields.Boolean(
        string='Thông tin tư vấn', default=False, copy=False,
    )
    # Khoá phiếu khai thác sau khi NV bấm "Lưu & Chuyển sang BÁO GIÁ".
    # NV không sửa được khi locked. Admin/Leader có nút "Mở khoá" để bypass.
    # ============ AUTO-LOCK INFRA ============
    # Required fields cho 'intake complete' — TẤT CẢ phải có giá trị trừ:
    #   - Xã/Phường (vd_intake_district)
    #   - Diện tích đất (vd_intake_length_m / vd_intake_width_m)
    #   - Ghi chú (vd_intake_function_notes)
    vd_intake_complete = fields.Boolean(
        string='Khai thác đủ thông tin',
        compute='_compute_intake_complete', store=True,
        help='True khi đã điền đủ 11 trường bắt buộc của THÔNG TIN TƯ VẤN. '
             'Trigger: auto-lock + auto hiện panel BÁO GIÁ CHI TIẾT.',
    )

    @api.depends(
        'vd_intake_province_id',                              # 1. Địa chỉ (Tỉnh)
        'vd_intake_timeline',                                 # 2. Thời gian
        'vd_intake_total_m2',                                 # 3. Diện tích nhà (computed)
        'vd_intake_house_type', 'vd_intake_foundation_type',  # 4. Mẫu nhà + Móng
        'vd_intake_floor_1_m2',                               # 5. Số tầng (ít nhất T1)
        'vd_intake_floor_1_function_ids',                     # 6. Công năng (ít nhất T1 có tag)
        'vd_intake_land_type',                                # 7. Loại đất
        'vd_intake_soil_dump',                                # 8. Chỗ để đất móng
        'vd_intake_car_access_select',                        # 9. Ô tô vào
        'vd_intake_budget_range',                             # 10. Tầm tài chính
        # User spec 2026-06-07: BỎ 'vd_intake_dimensions' (Sổ đỏ/cấp phép) khỏi
        # điều kiện → báo giá chi tiết hiện chỉ cần 11 trường. Trường Sổ đỏ vẫn
        # BẮT BUỘC khi bấm CHỐT BÁO GIÁ (validate trong action_save_intake_done).
    )
    def _compute_intake_complete(self):
        for rec in self:
            rec.vd_intake_complete = bool(
                rec.vd_intake_province_id
                and rec.vd_intake_timeline
                and (rec.vd_intake_total_m2 or 0) > 0
                and rec.vd_intake_house_type
                and rec.vd_intake_foundation_type
                and (rec.vd_intake_floor_1_m2 or 0) > 0
                and rec.vd_intake_floor_1_function_ids
                and rec.vd_intake_land_type
                and rec.vd_intake_soil_dump
                and rec.vd_intake_car_access_select
                and rec.vd_intake_budget_range
            )

    vd_intake_locked = fields.Boolean(
        string='Đã khoá thông tin tư vấn', default=False, copy=False,
        help='True sau khi NV bấm Lưu & Chuyển sang Báo giá. Admin/Leader có thể mở khoá.',
    )
    vd_quote_cancelled = fields.Boolean(
        string='Tạm huỷ báo giá', default=False, copy=False,
        help='NV bấm HUỶ BÁO GIÁ khi thông tin tư vấn chưa chính xác → tạm ẩn '
             'BÁO GIÁ CHI TIẾT, KH coi như CHƯA làm báo giá (pill mất màu xanh). '
             'Data tư vấn giữ nguyên; bấm LÀM BÁO GIÁ để khôi phục.',
    )
    vd_quote_created_date = fields.Datetime(
        string='Ngày tạo báo giá chi tiết', copy=False, readonly=True,
        help='Latch lần đầu intake đủ → khoá → báo giá chi tiết hiện ra. '
             'Dùng để đếm số ngày KH đã ở giai đoạn báo giá/đàm phán.',
    )
    # Timestamp lần cuối NV chỉnh sửa intake (chưa CHỐT). Cron wipe sau 15 phút
    # im lặng → ép NV phải CHỐT trong 1 lượt khai thác. Bump trong write() khi
    # locked field đổi + lead chưa locked.
    vd_intake_last_edit = fields.Datetime(
        string='Lần cuối chỉnh sửa khai thác', copy=False, readonly=True,
        help='Cron _cron_vd_wipe_unsaved_intake wipe data nếu vd_intake_last_edit '
             'cách hiện tại > 15 phút và chưa CHỐT.',
    )

    # Khai thác — tổng hợp nhu cầu khách hàng (xây dựng / nhà ở)
    # `help` = kịch bản gợi ý cho NV khi gọi (hiển thị tooltip).
    vd_intake_province_id = fields.Many2one(
        'res.country.state', string='Tỉnh / Thành',
        domain="[('country_id.code', '=', 'VN')]",
        help='Hỏi: "Anh/chị xây ở tỉnh / thành nào ạ?"',
    )
    vd_intake_district = fields.Many2one(
        'vd.district', string='Phường / Xã',
        help='Hỏi: "Khu vực phường / xã nào?" (sau sáp nhập 01/07/2025 — bỏ cấp huyện)',
    )

    @api.onchange('vd_intake_province_id')
    def _onchange_intake_province_reset_district(self):
        """Đổi Tỉnh → reset Huyện nếu Huyện hiện tại không thuộc Tỉnh mới.
        Tránh lưu cặp Tỉnh/Huyện lệch nhau (vd: Tỉnh Bắc Ninh + Huyện của Hà Nội).
        """
        for rec in self:
            _logger.info(
                "VD_DEBUG province_onchange: province=%r district=%r district.state=%r",
                rec.vd_intake_province_id.display_name if rec.vd_intake_province_id else None,
                rec.vd_intake_district.display_name if rec.vd_intake_district else None,
                rec.vd_intake_district.state_id.display_name if rec.vd_intake_district else None,
            )
            # CHỈ reset Huyện khi Tỉnh CÓ giá trị và khác tỉnh của huyện.
            # KHÔNG reset khi Tỉnh tạm None (tránh xoá lây Huyện khi client
            # chớp tắt giá trị Tỉnh).
            if (rec.vd_intake_province_id
                    and rec.vd_intake_district
                    and rec.vd_intake_district.state_id != rec.vd_intake_province_id):
                rec.vd_intake_district = False
                _logger.info("VD_DEBUG province_onchange -> RESET district")

    @api.onchange('vd_intake_district')
    def _onchange_intake_district_sync_province(self):
        """Chọn Huyện → LUÔN set lại Tỉnh = huyện.state_id.

        Fix bug: khi chọn Huyện thì Tỉnh bị mất trắng trên UI (Odoo client-side).
        Vì state_id của huyện CHÍNH LÀ tỉnh nên ta tự điền lại — onchange trả về
        province trong kết quả → client hiển thị lại đúng + lưu đúng, bất kể UI
        có tạm xoá. (user spec 2026-06-01)
        """
        for rec in self:
            _logger.info(
                "VD_DEBUG district_onchange BEFORE: district=%r district.state=%r province=%r",
                rec.vd_intake_district.display_name if rec.vd_intake_district else None,
                rec.vd_intake_district.state_id.display_name if rec.vd_intake_district else None,
                rec.vd_intake_province_id.display_name if rec.vd_intake_province_id else None,
            )
            if rec.vd_intake_district and rec.vd_intake_district.state_id:
                rec.vd_intake_province_id = rec.vd_intake_district.state_id
            _logger.info(
                "VD_DEBUG district_onchange AFTER: province=%r",
                rec.vd_intake_province_id.display_name if rec.vd_intake_province_id else None,
            )
    vd_intake_timeline = fields.Char(
        string='Thời gian dự kiến',
        help='Tháng dự kiến khởi công (vd: Tháng 6/2026). NV gõ → autocomplete '
             'tự gợi ý 24 tháng tới.',
    )
    vd_intake_timeline_status = fields.Selection([
        ('ok', 'Đủ thời gian'),
        ('warn', 'Hơi gấp'),
        ('critical', 'Quá gấp — cảnh báo!'),
        ('unknown', 'Chưa rõ'),
    ], compute='_compute_timeline_status', store=False)
    vd_intake_timeline_alert = fields.Html(
        compute='_compute_timeline_status', store=False,
    )

    @api.depends('vd_intake_timeline')
    def _compute_timeline_status(self):
        """Phân tích chuỗi 'Tháng X/YYYY' → tính khoảng cách đến hiện tại.
        - >= 6 tháng → OK
        - 3-6 tháng → cảnh báo nhẹ
        - < 3 tháng → CRITICAL + kịch bản tư vấn lùi thời gian
        - Chuỗi khác (vd "Càng sớm càng tốt") → unknown
        """
        import re
        from datetime import date
        today = date.today()
        pattern = re.compile(r'Tháng\s+(\d{1,2})\s*/\s*(\d{4})', re.IGNORECASE)

        for rec in self:
            rec.vd_intake_timeline_status = 'unknown'
            rec.vd_intake_timeline_alert = ''
            if not rec.vd_intake_timeline:
                continue
            m = pattern.search(rec.vd_intake_timeline.strip())
            if not m:
                # Chuỗi free-text như "Càng sớm càng tốt" / "Năm sau" → cảnh báo nhẹ
                low = rec.vd_intake_timeline.lower()
                if 'càng sớm' in low or 'asap' in low:
                    rec.vd_intake_timeline_status = 'critical'
                    rec.vd_intake_timeline_alert = (
                        '<b>⏰ KH muốn khởi công NGAY — cần lưu ý</b><br/>'
                        '<u>NV cần biết:</u> 1 công trình tốt cần tối thiểu '
                        '<b>2-3 tháng chuẩn bị</b> (thiết kế, giấy phép, vật liệu). '
                        'Khởi công gấp dễ ảnh hưởng chất lượng + giá vật liệu '
                        'không tối ưu.<br/>'
                        '<u>💬 Gợi ý hỏi thêm KH:</u><br/>'
                        '<i>"Dạ anh/chị muốn khởi công sớm thế này là có việc gì '
                        'gấp không ạ? Ví dụ kịp trước Tết / kịp đám cưới / chuyển '
                        'từ chỗ thuê...? Em hỏi để bên em biết mình ưu tiên gì để '
                        'tư vấn phương án phù hợp nhất ạ. Thông thường để có 1 '
                        'công trình đẹp + chất lượng, bên em cần <b>2-3 tháng '
                        'chuẩn bị</b>. Anh/chị có thể linh hoạt thời gian khởi '
                        'công không ạ?"</i>'
                    )
                continue
            month = int(m.group(1))
            year = int(m.group(2))
            try:
                target = date(year, min(max(month, 1), 12), 1)
            except ValueError:
                continue
            # Khoảng cách theo tháng
            months_diff = (target.year - today.year) * 12 + (target.month - today.month)
            if months_diff < 0:
                rec.vd_intake_timeline_status = 'critical'
                rec.vd_intake_timeline_alert = (
                    f'<b>⏰ Thời gian ĐÃ QUA</b> — tháng {month}/{year} đã trôi qua<br/>'
                    f'<u>Hành động:</u> hỏi lại KH thời gian khởi công mới + '
                    f'cập nhật trường "Thời gian".<br/>'
                    f'<u>💬 Hỏi lại KH:</u><br/>'
                    f'<i>"Dạ anh/chị ơi, em xem lại thấy mốc khởi công ghi '
                    f'tháng {month}/{year} đã qua rồi ạ. Hiện tại anh/chị dự '
                    f'kiến xây vào tháng nào để bên em <b>tư vấn phù hợp</b> '
                    f'với tiến độ của mình ạ?"</i>'
                )
            elif months_diff < 3:
                rec.vd_intake_timeline_status = 'critical'
                rec.vd_intake_timeline_alert = (
                    f'<b>⏰ Khá gấp — còn {months_diff} tháng tới khởi công</b><br/>'
                    f'<u>NV cần biết:</u> 1 công trình tốt cần ≥ <b>3-4 tháng</b> '
                    f'chuẩn bị. Khởi công trong {months_diff} tháng có thể '
                    f'ảnh hưởng <b>chất lượng + giá vật liệu</b>.<br/>'
                    f'<u>💬 Gợi ý hỏi thêm KH:</u><br/>'
                    f'<i>"Dạ thời gian anh/chị mong muốn khá sát ạ. Em xin phép '
                    f'hỏi: anh/chị có lý do gì cần khởi công trong '
                    f'{months_diff} tháng tới không ạ? Ví dụ kịp dịp gì đặc '
                    f'biệt? Em hỏi để hiểu ưu tiên của mình. Thông thường để '
                    f'<b>chất lượng tốt nhất + giá vật liệu tối ưu</b>, bên em '
                    f'cần khoảng 3-4 tháng chuẩn bị. Anh/chị có thể linh hoạt '
                    f'thời gian khởi công không ạ?"</i>'
                )
            elif months_diff < 6:
                rec.vd_intake_timeline_status = 'warn'
                rec.vd_intake_timeline_alert = (
                    f'<b>⏰ Hơi gấp — còn {months_diff} tháng tới khởi công</b><br/>'
                    f'<u>NV cần biết:</u> {months_diff} tháng là khoảng <b>vừa '
                    f'đủ</b>. Cần phối hợp nhanh sau khi KH chốt báo giá để '
                    f'kịp tiến độ.<br/>'
                    f'<u>💬 Nói với KH:</u><br/>'
                    f'<i>"Dạ thời gian {months_diff} tháng là vừa đủ để bên em '
                    f'chuẩn bị tốt cho công trình của anh/chị ạ. Nếu được, em '
                    f'mong anh/chị có thể <b>phản hồi nhanh khi em gửi báo giá</b> '
                    f'để mình kịp tiến độ. Anh/chị cứ trao đổi thoải mái với em, '
                    f'còn vướng mắc gì em sẽ giải đáp ngay nhé ạ."</i>'
                )
            else:
                rec.vd_intake_timeline_status = 'ok'
    vd_intake_area = fields.Char(
        string='Diện tích',
        help='Hỏi: "Tổng diện tích đất / sàn xây dựng?". VD: 100m² hoặc 5x20m',
    )
    vd_intake_house_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_house_type'),
        string='Kiểu nhà', tracking=True,
        help='Hỏi: "Anh/chị muốn xây kiểu nhà nào? Mái bằng, mái thái, mái nhật, nhà ống?"',
    )
    vd_intake_house_type_other = fields.Char(
        string='Mô tả kiểu nhà khác',
        help='Chỉ điền khi Kiểu nhà = "Khác". NV nhập tự do mô tả kiểu nhà KH muốn.',
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
    vd_intake_land_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_land_type'),
        string='Loại đất',
        help='Hỏi: "Đất là sổ đỏ thổ cư hay nông nghiệp / phân lô?"',
    )
    vd_intake_position = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_position'),
        string='Vị trí',
        help='Hỏi: "Mặt tiền hay trong hẻm? Đường vào có thuận lợi xe vận chuyển không?"',
    )
    vd_intake_budget = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_budget'),
        string='Ngân sách dự kiến',
        help='Hỏi: "Anh/chị dự kiến đầu tư khoảng bao nhiêu?"',
    )
    vd_intake_dimensions = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_dimensions'),
        string='Sổ đỏ / cấp phép',
        help='Hỏi: "Đất đã có sổ đỏ chưa? Đã có giấy phép xây dựng chưa?"',
    )

    # ============ FIELDS KỸ THUẬT cho TÍNH ĐƠN GIÁ ============
    vd_intake_length_m = fields.Float(
        string='Chiều dài (m)', digits=(8, 2),
        help='Chiều dài 1 sàn (mét). Vd: 20',
    )
    vd_intake_width_m = fields.Float(
        string='Chiều rộng (m)', digits=(8, 2),
        help='Chiều rộng 1 sàn (mét). Vd: 5',
    )
    vd_intake_area_m2 = fields.Float(
        string='Diện tích 1 sàn (m²)', digits=(10, 1),
        compute='_compute_area_from_dims', store=True, readonly=False,
        help='Auto = Dài × Rộng. NV vẫn có thể nhập tay nếu hình dạng đặc biệt.',
    )
    vd_intake_show_land_area = fields.Boolean(
        string='Hiện diện tích đất',
        default=False,
        help='Default OFF (user request 2026-05-27). NV bật khi cần ghi nhận '
             'diện tích đất riêng. Mutually exclusive với vd_intake_land_unlimited.',
    )
    vd_intake_show_house_area = fields.Boolean(
        string='Hiện diện tích nhà',
        default=True,
        help='Tắt khi chưa rõ kích thước cụ thể của nhà (vd: chỉ ước tính từ số tầng).',
    )
    vd_intake_land_unlimited = fields.Boolean(
        string='Đất rộng (không kích thước cụ thể)',
        default=False,
        help='Bật khi đất vườn rộng, không có kích thước cụ thể → ẩn ô nhập diện tích đất. '
             'Mutually exclusive với vd_intake_show_land_area.',
    )

    @api.onchange('vd_intake_show_land_area')
    def _onchange_show_land_area(self):
        """Toggle Diện tích đất ON → tự tắt Đất rộng."""
        for rec in self:
            if rec.vd_intake_show_land_area:
                rec.vd_intake_land_unlimited = False

    @api.onchange('vd_intake_land_unlimited')
    def _onchange_land_unlimited(self):
        """Toggle Đất rộng ON → tự tắt Diện tích đất (ẩn các ô nhập kích thước)."""
        for rec in self:
            if rec.vd_intake_land_unlimited:
                rec.vd_intake_show_land_area = False

    @api.depends('vd_intake_length_m', 'vd_intake_width_m')
    def _compute_area_from_dims(self):
        for rec in self:
            if rec.vd_intake_length_m and rec.vd_intake_width_m:
                rec.vd_intake_area_m2 = rec.vd_intake_length_m * rec.vd_intake_width_m
            elif not rec.vd_intake_area_m2:
                rec.vd_intake_area_m2 = 0.0
            # Nếu user đã nhập area_m2 thủ công và 1 trong 2 dim trống → giữ nguyên

    # ===== Kích thước nhà (footprint) — optional, NV nhập riêng nếu khác đất =====
    vd_intake_house_length_m = fields.Float(
        string='Chiều dài nhà (m)', digits=(8, 2),
        help='Chiều dài footprint nhà — có thể khác đất nếu chừa sân vườn.',
    )
    vd_intake_house_width_m = fields.Float(
        string='Chiều rộng nhà (m)', digits=(8, 2),
        help='Chiều rộng footprint nhà.',
    )
    vd_intake_floors_num = fields.Float(
        string='Số tầng', digits=(10, 1), default=1.0,
        help='Vd: 2.5 tầng (2 tầng + tum). Auto sync từ vd_intake_floors_select.',
    )

    # ===== Chip selector cho Số tầng (1-7) — tum giờ là toggle riêng =====
    vd_intake_floors_select = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
    ], string='Số tầng', default='1', tracking=True,
        help='Chọn số tầng dạng thẻ (1-7). Default = 1. Tự sync sang vd_intake_floors_num + mở các ô nhập diện tích từng tầng. Tum là toggle riêng (vd_intake_has_tum).')

    # Tum optional toggle — chỉ chọn khi đã chọn số tầng. Tum là tầng trên cùng.
    vd_intake_has_tum = fields.Boolean(
        string='Có tầng tum', tracking=True,
        help='Tum là tầng trên cùng (≈ 15-30m²). Bắt buộc đã chọn số tầng (1-7) trước.',
    )

    # Diện tích từng tầng — Integer (m² số nguyên). Float + digits(10,1) trước đây
    # render '0,0' (locale VN dấu phẩy) + parse lỗi khi gõ → giá trị bị 'tự xoá'.
    vd_intake_floor_1_m2 = fields.Integer(string='Tầng 1 (m²)', tracking=True)
    vd_intake_floor_2_m2 = fields.Integer(string='Tầng 2 (m²)', tracking=True)
    vd_intake_floor_3_m2 = fields.Integer(string='Tầng 3 (m²)', tracking=True)
    vd_intake_floor_4_m2 = fields.Integer(string='Tầng 4 (m²)', tracking=True)
    vd_intake_floor_5_m2 = fields.Integer(string='Tầng 5 (m²)', tracking=True)
    vd_intake_floor_6_m2 = fields.Integer(string='Tầng 6 (m²)', tracking=True)
    vd_intake_floor_7_m2 = fields.Integer(string='Tầng 7 (m²)', tracking=True)
    vd_intake_floor_tum_m2 = fields.Integer(string='Tum (m²)', tracking=True)
    # ===== Lửng (mezzanine) — NV bấm '+ Lửng' để mở 2 ô: Lửng + Thông tầng =====
    vd_intake_has_lung = fields.Boolean(string='Có Lửng', default=False, tracking=True)
    vd_intake_floor_lung_m2 = fields.Integer(string='Lửng (m²)', tracking=True)
    # Thông tầng — TỰ TÍNH = DT sàn Tầng 1 − DT Lửng (user spec 2026-06-05),
    # nhưng NV SỬA lại được (compute store readonly=False). Reset 0 khi tắt Lửng.
    vd_intake_floor_thongtang_m2 = fields.Integer(
        string='Thông tầng (m²)', tracking=True,
        compute='_compute_intake_thongtang_m2', store=True, readonly=False,
        help='Mặc định = DT sàn Tầng 1 − DT Lửng. NV có thể sửa lại.',
    )

    @api.depends('vd_intake_has_lung', 'vd_intake_floor_1_m2', 'vd_intake_floor_lung_m2')
    def _compute_intake_thongtang_m2(self):
        for rec in self:
            if rec.vd_intake_has_lung:
                rec.vd_intake_floor_thongtang_m2 = max(
                    0, (rec.vd_intake_floor_1_m2 or 0) - (rec.vd_intake_floor_lung_m2 or 0))
            else:
                rec.vd_intake_floor_thongtang_m2 = 0
    # ===== Counter cho UI '+ Tầng' button — sync 2 chiều với floors_select =====
    vd_intake_floors_count = fields.Integer(
        string='Số tầng đã thêm', default=1,
        help='Đếm số lần bấm + Tầng. Default = 1 (mặc định có Tầng 1). Sync với vd_intake_floors_select.',
    )

    # ===== Công năng từng tầng — Many2many dropdown per floor =====
    # NV chọn nhanh từ dropdown chip-pill cho mỗi tầng.
    vd_intake_floor_1_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_1_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 1')
    vd_intake_floor_2_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_2_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 2')
    vd_intake_floor_3_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_3_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 3')
    vd_intake_floor_4_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_4_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 4')
    vd_intake_floor_5_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_5_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 5')
    vd_intake_floor_6_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_6_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 6')
    vd_intake_floor_7_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_7_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng 7')
    vd_intake_floor_tum_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_tum_func_rel',
        'lead_id', 'tag_id', string='Công năng tum')
    vd_intake_floor_lung_function_ids = fields.Many2many(
        'vd.floor.function.tag', 'vd_lead_floor_lung_func_rel',
        'lead_id', 'tag_id', string='Công năng tầng lửng')

    # ===== Computed HTML hiển thị công năng từng tầng trong card thông tin KH =====
    vd_intake_floor_functions_html = fields.Html(
        string='Công năng các tầng (display)',
        compute='_compute_floor_functions_html',
        sanitize=False, store=False,
    )

    @api.depends(
        'vd_intake_floors_select', 'vd_intake_has_tum',
        'vd_intake_floor_1_function_ids', 'vd_intake_floor_2_function_ids',
        'vd_intake_floor_3_function_ids', 'vd_intake_floor_4_function_ids',
        'vd_intake_floor_5_function_ids', 'vd_intake_floor_6_function_ids',
        'vd_intake_floor_7_function_ids', 'vd_intake_floor_tum_function_ids',
    )
    def _compute_floor_functions_html(self):
        """Display HTML TABLE 2 cột — 2 tầng / 1 hàng. Table layout đảm bảo
        bố cục không bị Odoo's html widget hoặc parent CSS làm vỡ.
        NBSP giữa các từ trong tag name → emoji + chữ không tách dòng.
        """
        NBSP = ' '
        TD_STYLE = ('padding:4px 12px 4px 0;vertical-align:top;'
                    'font-size:13px;line-height:1.5;color:#1f2a44;'
                    'width:50%;word-wrap:break-word;')

        def _floor_cell(label, color, tags):
            tag_text = ', '.join(
                t.name.replace(' ', NBSP) for t in tags
            )
            return (
                f'<td style="{TD_STYLE}">'
                f'<b style="color:{color};">{label}:</b> {tag_text}'
                f'</td>'
            )

        for rec in self:
            n = int(rec.vd_intake_floors_select) if rec.vd_intake_floors_select else 0
            floors = []
            for i in range(1, n + 1):
                tags = rec[f'vd_intake_floor_{i}_function_ids']
                if tags:
                    floors.append((f'Tầng {i}', '#1864ab', tags))
            if rec.vd_intake_has_tum and rec.vd_intake_floor_tum_function_ids:
                floors.append(('Tum', '#2b8a3e', rec.vd_intake_floor_tum_function_ids))

            if not floors:
                rec.vd_intake_floor_functions_html = False
                continue

            # 2 floors / row
            tr_parts = []
            for j in range(0, len(floors), 2):
                left = _floor_cell(*floors[j])
                right = (_floor_cell(*floors[j + 1])
                         if j + 1 < len(floors)
                         else f'<td style="{TD_STYLE}"></td>')
                tr_parts.append(f'<tr>{left}{right}</tr>')

            rec.vd_intake_floor_functions_html = (
                '<table style="width:100%;border-collapse:collapse;'
                'table-layout:fixed;margin:4px 0;">'
                f'{"".join(tr_parts)}'
                '</table>'
            )

    @api.onchange('vd_intake_floors_select', 'vd_intake_has_tum', 'vd_intake_area_m2')
    def _onchange_floors_select(self):
        mapping = {'1': 1.0, '2': 2.0, '3': 3.0, '4': 4.0, '5': 5.0, '6': 6.0, '7': 7.0}
        base = mapping.get(self.vd_intake_floors_select, 0.0) if self.vd_intake_floors_select else 0.0
        if self.vd_intake_floors_select or self.vd_intake_has_tum:
            self.vd_intake_floors_num = base + (0.5 if self.vd_intake_has_tum else 0.0)

        n = int(self.vd_intake_floors_select) if self.vd_intake_floors_select else 0
        # CLEAR diện tích các tầng vượt số tầng đã chọn (tránh count tầng ẩn vào tổng)
        for i in range(n + 1, 8):
            fname = f'vd_intake_floor_{i}_m2'
            if self[fname]:
                self[fname] = 0
        if not self.vd_intake_has_tum and self.vd_intake_floor_tum_m2:
            self.vd_intake_floor_tum_m2 = 0

        # Auto-fill diện tích từng tầng từ L×R (chỉ điền nếu trường tầng đang trống)
        # area_m2 là Float (footprint) → làm tròn về số nguyên cho ô tầng (Integer)
        area = int(round(self.vd_intake_area_m2 or 0.0))
        if area > 0:
            for i in range(1, n + 1):
                fname = f'vd_intake_floor_{i}_m2'
                if not self[fname]:
                    self[fname] = area
            if self.vd_intake_has_tum and not self.vd_intake_floor_tum_m2:
                self.vd_intake_floor_tum_m2 = area

    def _vd_auto_foundation(self):
        """Tự động chọn loại móng (user spec 2026-06-22):
        - Đất yếu  -> Móng cọc (ưu tiên cao nhất).
        - >= 2 tầng -> Móng băng.
        - còn lại (1 tầng, đất cứng) -> Móng đơn.
        NV vẫn đổi tay được sau đó; chỉ tự set khi số tầng / loại đất thay đổi."""
        for rec in self:
            sel = rec.vd_intake_floors_select or ''
            floors = int(sel) if sel.isdigit() else (rec.vd_intake_floors_count or 1)
            if rec.vd_intake_land_type == 'dat_yeu':
                rec.vd_intake_foundation_type = 'coc'
            elif floors >= 2:
                rec.vd_intake_foundation_type = 'bang'
            else:
                rec.vd_intake_foundation_type = 'don'

    @api.onchange('vd_intake_land_type', 'vd_intake_floors_select')
    def _onchange_vd_auto_foundation(self):
        self._vd_auto_foundation()

    def action_toggle_tum(self):
        """Toggle tầng tum on/off (chip button). Khi tắt → clear data."""
        self.ensure_one()
        self.vd_intake_has_tum = not self.vd_intake_has_tum
        # Sync lại floors_num
        mapping = {'1': 1.0, '2': 2.0, '3': 3.0, '4': 4.0, '5': 5.0, '6': 6.0, '7': 7.0}
        base = mapping.get(self.vd_intake_floors_select, 0.0)
        self.vd_intake_floors_num = base + (0.5 if self.vd_intake_has_tum else 0.0)
        if self.vd_intake_has_tum:
            # Auto-fill tum area từ area_m2 nếu vừa bật (làm tròn về số nguyên)
            if self.vd_intake_area_m2 and not self.vd_intake_floor_tum_m2:
                self.vd_intake_floor_tum_m2 = int(round(self.vd_intake_area_m2))
        else:
            # Tắt → clear m² + function_ids
            self.vd_intake_floor_tum_m2 = 0
            self.vd_intake_floor_tum_function_ids = [(5, 0, 0)]
        return True

    def action_add_floor(self):
        """Bấm '+ Tầng' → tăng counter (max 7) + sync floors_select."""
        self.ensure_one()
        if self.vd_intake_floors_count < 7:
            new_count = self.vd_intake_floors_count + 1
            self.vd_intake_floors_count = new_count
            self.vd_intake_floors_select = str(new_count)
            self._vd_auto_foundation()   # >=2 tầng -> móng băng (trừ đất yếu -> cọc)
        return True

    def action_remove_floor(self):
        """Bấm '- Tầng' → giảm counter (min 0) + clear m² của tầng vừa xoá.
        (LEGACY — button đã ẩn khỏi view sau 2026-05-27.)"""
        self.ensure_one()
        if self.vd_intake_floors_count > 0:
            last = self.vd_intake_floors_count
            setattr(self, f'vd_intake_floor_{last}_m2', 0)
            new_count = last - 1
            self.vd_intake_floors_count = new_count
            self.vd_intake_floors_select = str(new_count) if new_count > 0 else False
        return True

    def action_vd_remove_floor_n(self):
        """Xoá tầng N (lấy từ context vd_floor_n). User spec 2026-05-27:
        button X trên từng row công năng — xoá cả m² + function_ids của Tn,
        đồng thời shift các tầng cao hơn xuống (T(N+1) → Tn, T(N+2) → T(N+1)...)
        và decrement floors_count.

        Riêng Tum/Lửng: dùng action_toggle_tum/lung (đã clear data sẵn).
        """
        self.ensure_one()
        n = int(self.env.context.get('vd_floor_n', 0))
        if n < 1 or n > 7:
            return True
        # Đọc data 7 tầng vào list
        floor_data = []
        for i in range(1, 8):
            m2 = self[f'vd_intake_floor_{i}_m2'] or 0.0
            fids = self[f'vd_intake_floor_{i}_function_ids'].ids
            floor_data.append((m2, fids))
        # Bỏ index n-1, append empty cuối
        floor_data.pop(n - 1)
        floor_data.append((0.0, []))
        # Build vals shift xuống
        vals = {}
        for i in range(1, 8):
            m2, fids = floor_data[i - 1]
            vals[f'vd_intake_floor_{i}_m2'] = m2
            vals[f'vd_intake_floor_{i}_function_ids'] = [(6, 0, fids)]
        # Decrement floors_count (min 1 — Tầng 1 luôn có)
        current = self.vd_intake_floors_count or int(self.vd_intake_floors_select or '1')
        new_count = max(1, current - 1)
        vals['vd_intake_floors_count'] = new_count
        vals['vd_intake_floors_select'] = str(new_count)
        self.write(vals)
        self._vd_auto_foundation()   # cập nhật móng theo số tầng mới
        return True

    def action_toggle_lung(self):
        """Toggle Lửng on/off — bật → mở 2 ô Lửng + Thông tầng. Tắt → clear data."""
        self.ensure_one()
        self.vd_intake_has_lung = not self.vd_intake_has_lung
        if not self.vd_intake_has_lung:
            self.vd_intake_floor_lung_m2 = 0
            self.vd_intake_floor_thongtang_m2 = 0
            self.vd_intake_floor_lung_function_ids = [(5, 0, 0)]
        return True

    # ===== Tổng diện tích các tầng (sum per-floor inputs) =====
    vd_intake_total_m2 = fields.Integer(
        string='Diện tích nhà',
        compute='_compute_total_m2', store=True, readonly=False,
        help='Auto = sum diện tích các tầng. NV có thể gõ tay để override.',
    )

    @api.depends(
        'vd_intake_floors_select',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_has_tum', 'vd_intake_floor_tum_m2',
        'vd_intake_house_length_m', 'vd_intake_house_width_m',
    )
    def _compute_total_m2(self):
        """Tính Diện tích nhà với độ ưu tiên:
        1. Sum per-tầng (chính xác nhất nếu NV đã nhập từng tầng)
        2. House L × W (footprint) khi NV chỉ nhập L+R
        3. Giữ giá trị NV gõ tay (override) nếu cả 2 trên = 0
        """
        for rec in self:
            # Sum per-tầng
            n = int(rec.vd_intake_floors_select) if rec.vd_intake_floors_select else 0
            total = 0.0
            for i in range(1, n + 1):
                total += rec[f'vd_intake_floor_{i}_m2'] or 0
            if rec.vd_intake_has_tum:
                total += rec.vd_intake_floor_tum_m2 or 0
            # Fallback L × W nhà nếu không có per-tầng
            if total <= 0 and rec.vd_intake_house_length_m and rec.vd_intake_house_width_m:
                total = rec.vd_intake_house_length_m * rec.vd_intake_house_width_m
            if total > 0:
                rec.vd_intake_total_m2 = int(round(total))
    vd_intake_foundation_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_foundation_type'),
        string='Loại móng', tracking=True,
    )
    # ===== Loại mái — directly selectable, FILTER theo Kiểu nhà =====
    vd_intake_roof_type = fields.Selection(
        selection=lambda self: self._vd_ext_selection('vd_intake_roof_type'),
        string='Loại mái', tracking=True,
    )

    @api.onchange('vd_intake_house_type')
    def _onchange_house_type_reset_roof(self):
        """Đổi Kiểu nhà → reset Loại mái nếu không còn valid theo mapping."""
        valid_roofs = {
            'mai_bang': ['mai_bang'],
            'mai_thai': ['mai_thai_kdt', 'mai_thai_cdt'],
            'mai_nhat': ['mai_nhat_kdt', 'mai_nhat_cdt'],
            'mai_ton': ['mai_ton'],
            # Nhà phố / biệt thự / ống / cấp 4 / tum / chung cư / khác → tất cả
        }
        for rec in self:
            ok = valid_roofs.get(rec.vd_intake_house_type)
            if ok and rec.vd_intake_roof_type not in ok:
                rec.vd_intake_roof_type = False
    vd_intake_car_access = fields.Boolean(string='Ô tô vào được', default=True)
    # Selection mirror cho UI dropdown (sync 2 chiều với Boolean ở trên):
    #  - xe_tai_lon / xe_tai_nho → vào được (True)
    #  - xe_3_banh → không vào được ô tô (False, chỉ xe 3 bánh)
    vd_intake_car_access_select = fields.Selection([
        ('xe_tai_lon', 'ĐƯỜNG - Xe tải lớn'),
        ('xe_tai_nho', 'ĐƯỜNG - Xe tải nhỏ'),
        ('xe_3_banh', 'ĐƯỜNG - Xe 3 bánh'),
    ], string='Ô tô vào',
        compute='_compute_car_access_select',
        inverse='_inverse_car_access_select',
        store=True)

    @api.depends('vd_intake_car_access')
    def _compute_car_access_select(self):
        for rec in self:
            # Chỉ set giá trị mặc định khi chưa có (tránh ghi đè lựa chọn cụ thể)
            if not rec.vd_intake_car_access_select:
                rec.vd_intake_car_access_select = 'xe_tai_nho' if rec.vd_intake_car_access else 'xe_3_banh'

    def _inverse_car_access_select(self):
        for rec in self:
            rec.vd_intake_car_access = rec.vd_intake_car_access_select in ('xe_tai_lon', 'xe_tai_nho')

    # Chỗ để đất móng — KH có chỗ chứa/đổ đất móng đào lên không?
    # Ảnh hưởng đến chi phí thi công (phải thuê xe vận chuyển hay không).
    vd_intake_soil_dump = fields.Selection([
        ('co_dat_rong', 'CÓ - Đất rộng'),
        ('co_quanh_mong', 'CÓ - Để quanh móng, vỉa hè'),
        ('khong', 'KHÔNG - Không có chỗ'),
    ], string='Chỗ để đất móng',
        help='KH có chỗ chứa đất móng đào lên không? '
             'KHÔNG → phải thuê xe vận chuyển đi (đội chi phí).')

    vd_intake_budget_amount = fields.Monetary(
        string='Tầm tài chính (VNĐ)', currency_field='vd_currency_vnd_id',
        help='Số tiền cụ thể KH dự kiến. Được auto-set khi user pick '
             'vd_intake_budget_range (qua onchange + write hook).',
    )
    # ============ TẦM TÀI CHÍNH — Selection dropdown ============
    # Mapping key → VND amount để sync 2 chiều với vd_intake_budget_amount.
    # Tăng dần: 0 (chưa xđ) → 700tr → ... → 3 tỷ.
    _VD_BUDGET_RANGE_AMOUNT = {
        'chua_xd':  0,
        '700tr':    700_000_000,
        '800tr':    800_000_000,
        '900tr':    900_000_000,
        '1ty':    1_000_000_000,
        '1_1ty':  1_100_000_000,
        '1_2ty':  1_200_000_000,
        '1_3ty':  1_300_000_000,
        '1_4ty':  1_400_000_000,
        '1_5ty':  1_500_000_000,
        '1_6ty':  1_600_000_000,
        '1_7ty':  1_700_000_000,
        '2ty':    2_000_000_000,
        '2_2ty':  2_200_000_000,
        '2_5ty':  2_500_000_000,
        '2_8ty':  2_800_000_000,
        '3ty':    3_000_000_000,
    }
    vd_intake_budget_range = fields.Selection([
        ('chua_xd', 'Chưa xác định'),
        ('700tr',   '700 Triệu'),
        ('800tr',   '800 Triệu'),
        ('900tr',   '900 Triệu'),
        ('1ty',     '1 Tỷ'),
        ('1_1ty',   '1,1 Tỷ'),
        ('1_2ty',   '1,2 Tỷ'),
        ('1_3ty',   '1,3 Tỷ'),
        ('1_4ty',   '1,4 Tỷ'),
        ('1_5ty',   '1,5 Tỷ'),
        ('1_6ty',   '1,6 Tỷ'),
        ('1_7ty',   '1,7 Tỷ'),
        ('2ty',     '2 Tỷ'),
        ('2_2ty',   '2,2 Tỷ'),
        ('2_5ty',   '2,5 Tỷ'),
        ('2_8ty',   '2,8 Tỷ'),
        ('3ty',     '3 Tỷ'),
    ], string='Tầm tài chính',
        help='KH chọn từ dropdown. Auto cập nhật vd_intake_budget_amount '
             'để compute chênh lệch với estimate.')

    @api.onchange('vd_intake_budget_range')
    def _onchange_budget_range(self):
        """UI: user pick range → set amount tương ứng."""
        if self.vd_intake_budget_range:
            self.vd_intake_budget_amount = self._VD_BUDGET_RANGE_AMOUNT.get(
                self.vd_intake_budget_range, 0,
            )

    @classmethod
    def _sync_budget_range_to_amount(cls, vals):
        """Helper: nếu vals có budget_range mà chưa có budget_amount → tự fill amount.
        Gọi từ create()/write() override bên dưới."""
        if 'vd_intake_budget_range' in vals and 'vd_intake_budget_amount' not in vals:
            amount = cls._VD_BUDGET_RANGE_AMOUNT.get(vals['vd_intake_budget_range'])
            if amount is not None:
                vals['vd_intake_budget_amount'] = amount
    vd_currency_vnd_id = fields.Many2one(
        'res.currency', compute='_compute_vnd_currency', store=False,
        help='Currency cố định = VND để monetary widget format đúng.',
    )

    def _compute_vnd_currency(self):
        # KHÔNG dùng @api.model — sẽ làm compute không chạy per-record.
        # KHÔNG cần @api.depends — không phụ thuộc field nào trên record.
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        for rec in self:
            rec.vd_currency_vnd_id = vnd

    # ============ LÝ DO KHÁCH HỦY (khi NV bấm "Khách không có nhu cầu") ============
    vd_lost_reason = fields.Text(
        string='Lý do khách hủy / không có nhu cầu',
        help='NV ghi rõ vì sao KH không có nhu cầu. Bắt buộc khi chuyển sang stage Khách hủy.',
    )
    vd_lost_date = fields.Datetime(
        string='Thời điểm đánh dấu hủy', readonly=True, copy=False,
    )
    vd_lost_user_id = fields.Many2one(
        'res.users', string='Người huỷ', readonly=True, copy=False,
        help='User ấn nút Hủy. False = cron auto-trash (4+ ngày không nghe máy).',
    )
    vd_lost_is_auto = fields.Boolean(
        string='Tự động huỷ', readonly=True, copy=False, default=False,
        help='True = cron auto-trash. False = NV bấm Hủy thủ công.',
    )

    # ============ CHƯA BÁO GIÁ — round 11 (chuyển sang THAM KHẢO) ============
    # NV bấm CHƯA BÁO GIÁ → wizard → set state='pending' → KH tự xuất hiện
    # trong THAM KHẢO bucket thay vì KHÁCH MỚI. Có callback_date để dashboard
    # hiện nút "GỌI LẠI" khi đến ngày.
    vd_no_quote_state = fields.Selection([
        ('pending', '⏸️ Chưa báo giá — đang theo dõi'),
    ], string='Trạng thái CHƯA BÁO GIÁ', tracking=True, copy=False)
    vd_no_quote_category = fields.Selection([
        ('financial', '💰 Tài chính'),
        ('land', '🌍 Đất đai'),
        ('legal', '📜 Pháp lý giấy tờ'),
        ('timing', '⏰ Thời gian xây'),
    ], string='Lý do CHƯA BÁO GIÁ', copy=False, tracking=True)
    vd_no_quote_reason = fields.Text(
        string='Chi tiết CHƯA BÁO GIÁ', copy=False,
        help='Khai thác cụ thể: tài chính bao nhiêu, đất ở đâu, pháp lý gì, '
             'thời gian khi nào… do wizard sinh ra.',
    )
    # JSON các trường wizard THAM KHẢO đã nhập — để mở lại wizard hiện đúng dữ
    # liệu đã chọn trước đó (user spec 2026-06-05).
    vd_no_quote_data = fields.Char(string='Dữ liệu wizard THAM KHẢO (JSON)', copy=False)
    vd_no_quote_callback_date = fields.Date(
        string='Ngày gọi lại (THAM KHẢO)', copy=False, tracking=True,
        help='Ngày NV phải gọi lại để follow up. Dashboard THAM KHẢO hiển '
             'thị nút GỌI LẠI khi today >= ngày này.',
    )
    vd_no_quote_date = fields.Datetime(
        string='Thời điểm CHƯA BÁO GIÁ', readonly=True, copy=False,
    )
    vd_no_quote_user_id = fields.Many2one(
        'res.users', string='NV đánh dấu CHƯA BÁO GIÁ',
        readonly=True, copy=False,
    )

    def action_open_no_quote_wizard(self):
        """Mở wizard CHƯA BÁO GIÁ — KHÁCH THAM KHẢO."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vd.lead.no_quote.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            },
        }

    # ============ ĐỀ XUẤT HỦY — Approval gate (user spec round 7 phase 2) ============
    # NV submit wizard → vd_cancel_state='proposed'. Admin xem trong thùng rác,
    # bấm Duyệt → state='approved' + archive (active=False).
    vd_cancel_state = fields.Selection([
        ('proposed', '⏳ Đề xuất hủy — chờ duyệt'),
        ('approved', '✓ Đã duyệt hủy'),
    ], string='Trạng thái duyệt hủy', tracking=True, copy=False,
        help='proposed = NV đã đề xuất, chờ admin duyệt. '
             'approved = admin đã duyệt → KH thực sự hủy + archive.')
    vd_cancel_category = fields.Selection([
        ('no_budget', '💸 Không đủ ngân sách'),
        ('competitor', '🏗️ Đã chọn bên khác'),
        ('cancel_plan', '🚫 Hủy kế hoạch xây'),
        ('wrong_number', '❌ Nhầm số'),
    ], string='Chủ đề hủy', copy=False)
    vd_cancel_approved_by_id = fields.Many2one(
        'res.users', string='Người duyệt hủy', readonly=True, copy=False,
    )
    vd_cancel_approved_date = fields.Datetime(
        string='Ngày duyệt hủy', readonly=True, copy=False,
    )

    def action_approve_cancel(self):
        """Admin duyệt đề xuất hủy → archive lead (active=False) + record audit.
        Lead vẫn ở stage=lost (đã được wizard set) → vẫn xuất hiện trong thùng
        rác với active_test=False. NV không thấy ở pipeline chính (active=False
        + stage_is_lost=True → đã exclude từ mọi domain pipeline chuẩn).

        Round 7 phase 2.1: cho phép duyệt CẢ legacy leads (vd_cancel_state=None)
        — KH lost trước Phase 2 vẫn cần audit trail admin duyệt.

        User spec 2026-06-21: TRƯỞNG PHÒNG + Giám đốc + Admin được duyệt hủy
        (NV/CTV chỉ ĐỀ XUẤT). has_group('team_leader') True cho cả 3 vai trò trên
        (admin implies director implies team_leader). Record rule vẫn giới hạn
        trưởng phòng chỉ duyệt được KH trong phòng ban mình (write theo rule)."""
        can_approve = (
            self.env.user._is_superuser()
            or self.env.user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        )
        if not can_approve:
            raise UserError(_(
                'Chỉ Trưởng phòng / Giám đốc / Admin mới được DUYỆT hủy khách. '
                'Nhân viên chỉ được ĐỀ XUẤT hủy.'
            ))
        for rec in self:
            if rec.vd_cancel_state == 'approved':
                continue  # đã duyệt rồi, skip
            rec.with_context(mail_notrack=True, tracking_disable=True).write({
                'vd_cancel_state': 'approved',
                'vd_cancel_approved_by_id': self.env.user.id,
                'vd_cancel_approved_date': fields.Datetime.now(),
                'active': False,
                # User spec 2026-06-21: GỠ NV khỏi KH khi duyệt hủy → KH vào thùng
                # rác công ty KHÔNG còn thuộc NV nào (NV không thấy lại trong mọi
                # bảng theo user_id; chỉ Admin/Giám đốc xem ở thùng rác công ty).
                'user_id': False,
            })
            rec.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('✓ <b>Đã duyệt hủy</b> bởi %s — KH chính thức archive.') % self.env.user.name,
            )
        return True

    # ============ BÁO GIÁ — fields working trong panel báo giá ============
    # Helper Many2many: tự filter template theo intake KH (vùng / tầng / móng / mái)
    # Dropdown vd_quote_template_id dùng domain id IN suggested_ids để chỉ show
    # template phù hợp 4 chiều phân loại trên category.
    vd_quote_template_suggested_ids = fields.Many2many(
        'vd.quote.template', string='Template gợi ý theo intake',
        compute='_compute_quote_template_suggested', store=False,
        help='Auto-filter từ category: region + floor_range + foundation + roof_simple match intake KH.',
    )
    vd_quote_template_id = fields.Many2one(
        'vd.quote.template', string='Template báo giá',
        domain="[('id', 'in', vd_quote_template_suggested_ids)]",
        compute='_compute_quote_template_id_auto', store=True, readonly=False,
        help='AUTO-pick template đầu tiên trong suggested list khi field còn rỗng. '
             'Admin có thể override bằng cách set manual (compute respect non-empty).',
    )

    @api.depends('vd_quote_template_suggested_ids')
    def _compute_quote_template_id_auto(self):
        """Tự pick template đầu tiên match intake nếu chưa có template nào.
        Giữ nguyên nếu đã có (kể cả khi suggested thay đổi) để không ghi đè
        manual selection."""
        for rec in self:
            if not rec.vd_quote_template_id and rec.vd_quote_template_suggested_ids:
                rec.vd_quote_template_id = rec.vd_quote_template_suggested_ids[0]

    @api.depends(
        'vd_intake_region', 'vd_intake_foundation_type',
        'vd_intake_roof_type', 'vd_intake_floors_num',
    )
    def _compute_quote_template_suggested(self):
        """Compute danh sách template gợi ý dựa trên 4 chiều intake KH.

        Map intake → category dimensions:
        - region: vd_intake_region (bac/trung/nam) — trực tiếp
        - foundation: vd_intake_foundation_type (don/bang/coc) — trực tiếp
        - roof_simple: 'bang' nếu mai_bang, 'ngoi' nếu các loại còn lại
        - floor_range: '1' / '2_4' / '5_plus' theo vd_intake_floors_num

        Strategy: match all dimensions ĐÃ set của lead. Dimension chưa set
        thì không filter (cho phép category bất kỳ value match). Template
        chưa có category cũng luôn hiện (backward compat).
        """
        Tpl = self.env['vd.quote.template']
        for rec in self:
            # Map intake values → category codes
            roof_raw = rec.vd_intake_roof_type or ''
            if roof_raw == 'mai_bang':
                roof_simple = 'bang'
            elif roof_raw:
                roof_simple = 'ngoi'
            else:
                roof_simple = False

            floors = int(rec.vd_intake_floors_num or 0)
            if floors == 1:
                floor_range = '1'
            elif 2 <= floors <= 4:
                floor_range = '2_4'
                # Float 2.5 (2 tầng + tum) → vẫn coi là 2_4
            elif floors >= 5:
                floor_range = '5_plus'
            else:
                floor_range = False

            # Build domain: filter trực tiếp trên template (sau refactor 4
            # chiều move từ category → template). Template chưa tag dimension
            # luôn hiện (cho phép template legacy / chung không bị ẩn).
            domain = [('active', '=', True)]
            tag_clauses = []
            if rec.vd_intake_region:
                tag_clauses.extend([
                    '|', ('region_ids', '=', False),
                    ('region_ids.code', '=', rec.vd_intake_region),
                ])
            if rec.vd_intake_foundation_type:
                tag_clauses.extend([
                    '|', ('foundation', '=', False),
                    ('foundation', '=', rec.vd_intake_foundation_type),
                ])
            if roof_simple:
                tag_clauses.extend([
                    '|', ('roof_simple', '=', False),
                    ('roof_simple', '=', roof_simple),
                ])
            if floor_range:
                tag_clauses.extend([
                    '|', ('floor_range', '=', False),
                    ('floor_range', '=', floor_range),
                ])

            rec.vd_quote_template_suggested_ids = Tpl.search(domain + tag_clauses)
    vd_quote_price = fields.Monetary(
        string='Giá báo cho KH', currency_field='vd_currency_vnd_id',
        compute='_compute_quote_price_default', store=True, readonly=False, copy=False,
        help='Tự động đồng bộ với GIÁ ƯỚC TÍNH từ khai thác (intake_estimate). '
             'Mỗi lần ước tính thay đổi → giá báo tự cập nhật theo.',
    )
    vd_quote_date = fields.Date(string='Ngày báo giá', default=fields.Date.context_today)
    vd_quote_valid_until = fields.Date(
        string='Hiệu lực đến',
        compute='_compute_quote_valid_until', store=True, readonly=False, copy=False,
        help='Tự động = ngày báo + 30 ngày. NV có thể sửa.',
    )

    # ============ KHUYẾN MÃI / GIẢM GIÁ — Round 10 spec ============
    # NV nhập 1 số tiền giảm trực tiếp + label (vd "Khuyến mãi Tết 2026").
    # Hiển thị thành 1 dòng riêng trong bảng báo giá chi tiết và PDF, TRỪ
    # khỏi tổng tiền. Mặc định = 0 (không hiện dòng nào).
    vd_quote_discount_amount = fields.Monetary(
        string='Khuyến mãi / Giảm giá (VNĐ)',
        currency_field='vd_currency_vnd_id', default=0, copy=False,
        help='Số tiền giảm trực tiếp cho KH. Sẽ hiện thành 1 dòng riêng "(-)" '
             'trong báo giá và trừ khỏi tổng tiền.',
    )
    vd_quote_discount_label = fields.Char(
        string='Lý do khuyến mãi',
        default='Khuyến mãi', copy=False,
        help='Nhãn cho dòng giảm giá (VD: "Khuyến mãi Tết 2026", "VIP discount", "Tri ân KH cũ"...).',
    )

    # Upload file template trực tiếp từ máy (sẽ tự tạo vd.quote.template record)
    vd_quote_template_upload = fields.Binary(
        string='Upload file template từ máy', attachment=True, copy=False,
        help='Upload file mẫu báo giá (.docx/.xlsx/.pdf/.png/...). Sẽ tự tạo '
             'template mới và gán cho lead này.',
    )
    vd_quote_template_upload_name = fields.Char(string='Tên file upload', copy=False)

    # PREVIEW HTML inline (legacy — fallback nếu chưa upload template PDF)
    vd_quote_preview_html = fields.Html(
        string='Preview báo giá (HTML)', compute='_compute_quote_preview_html',
        store=False, sanitize=False,
    )

    # BẢNG BREAKDOWN — chỉ pricing table (Móng / Tầng trệt / Mái), nhúng trong quote panel
    vd_quote_breakdown_html = fields.Html(
        string='Bảng báo giá chi tiết (breakdown)',
        compute='_compute_quote_breakdown_html',
        store=False, sanitize=False,
    )

    # ===== COPY GỬI ZALO — text format gửi nhóm xác nhận thông tin KH =====
    vd_zalo_copy_text = fields.Text(
        string='Text gửi Zalo',
        compute='_compute_vd_zalo_copy_text',
        store=False,
        help='Format text đầy đủ thông tin KH, click nút Copy để paste vào Zalo.',
    )

    @api.depends(
        'vd_intake_province_id', 'vd_intake_district',
        'vd_intake_total_m2', 'vd_intake_floors_select', 'vd_intake_has_tum',
        'vd_intake_has_lung', 'vd_intake_house_type', 'vd_intake_foundation_type',
        'vd_intake_house_length_m', 'vd_intake_house_width_m',
        'vd_intake_length_m', 'vd_intake_width_m',
        'vd_intake_budget_range', 'vd_intake_budget_amount',
        'vd_intake_timeline', 'vd_intake_land_type', 'vd_intake_dimensions',
        'vd_intake_car_access_select', 'vd_intake_soil_dump',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2', 'vd_intake_floor_lung_m2',
        'vd_intake_floor_1_function_ids', 'vd_intake_floor_2_function_ids',
        'vd_intake_floor_3_function_ids', 'vd_intake_floor_4_function_ids',
        'vd_intake_floor_5_function_ids', 'vd_intake_floor_6_function_ids',
        'vd_intake_floor_7_function_ids', 'vd_intake_floor_tum_function_ids',
        'vd_intake_floor_lung_function_ids', 'vd_intake_function_notes',
    )
    def _compute_vd_zalo_copy_text(self):
        """User spec 2026-05-29: copy ĐẦY ĐỦ 11 trường intake + công năng từng tầng."""
        import re
        # Strip emoji/non-word prefix khỏi tên công năng. User spec round 5:
        # "công năng đã bỏ các icon trong nội dung". DB name dạng
        # "🛋️🍳 1 Khách 1 Bếp" → output "1 Khách 1 Bếp". Regex match leading
        # ký tự không phải [a-zA-Z0-9_à-ỹÀ-Ỹ] (\w trong UNICODE) → strip.
        _emoji_prefix_re = re.compile(r'^[^\w]+', re.UNICODE)

        def _strip_emoji(name):
            return _emoji_prefix_re.sub('', name or '').strip()

        def _sel_label(rec, fname):
            val = rec[fname]
            if not val:
                return ''
            return rec._vd_selection_dict(fname).get(val, val)

        def _fn_names(funcs):
            if not funcs:
                return ''
            return ', '.join(_strip_emoji(n) for n in funcs.mapped('name'))

        for rec in self:
            # User spec 2026-05-29 round 5: LABEL viết HOA + value giữ NGUYÊN
            # case từ DB. Bỏ trường không có data (chỉ append khi có giá trị).
            lines = ['📋 THÔNG TIN TƯ VẤN', '────────────────────']

            # 📍 ĐỊA CHỈ — chỉ append nếu có ít nhất 1 phần
            addr = ''
            if rec.vd_intake_district:
                addr = rec.vd_intake_district.name
            if rec.vd_intake_province_id:
                addr = (addr + ', ' if addr else '') + rec.vd_intake_province_id.name
            if addr:
                lines.append('📍 ĐỊA CHỈ: %s' % addr)

            # ⏰ THỜI GIAN — chỉ append nếu có
            if rec.vd_intake_timeline:
                lines.append('⏰ THỜI GIAN: %s' % rec.vd_intake_timeline)

            # 📐 DIỆN TÍCH
            dt_parts = []
            if rec.vd_intake_house_width_m and rec.vd_intake_house_length_m:
                dt_parts.append('Nhà %sx%sm' % (rec.vd_intake_house_width_m, rec.vd_intake_house_length_m))
            if rec.vd_intake_width_m and rec.vd_intake_length_m:
                dt_parts.append('Đất %sx%sm' % (rec.vd_intake_width_m, rec.vd_intake_length_m))
            if rec.vd_intake_total_m2:
                dt_parts.append('Tổng %sm²' % rec.vd_intake_total_m2)
            if dt_parts:
                lines.append('📐 DIỆN TÍCH: %s' % ' | '.join(dt_parts))

            # 🏠 MẪU NHÀ
            if rec.vd_intake_house_type:
                lines.append('🏠 MẪU NHÀ: %s' % _sel_label(rec, 'vd_intake_house_type'))

            # 🌱 LOẠI ĐẤT
            if rec.vd_intake_land_type:
                lines.append('🌱 LOẠI ĐẤT: %s' % _sel_label(rec, 'vd_intake_land_type'))

            # 🔨 MÓNG
            if rec.vd_intake_foundation_type:
                lines.append('🔨 MÓNG: %s' % _sel_label(rec, 'vd_intake_foundation_type'))

            # 🏗️ SỐ TẦNG + DT từng tầng
            floor_parts = []
            n = int(rec.vd_intake_floors_select or '0')
            for i in range(1, n + 1):
                m2 = rec['vd_intake_floor_%s_m2' % i] or 0
                if m2:
                    floor_parts.append('T%s: %sm²' % (i, m2))
            if rec.vd_intake_has_tum and rec.vd_intake_floor_tum_m2:
                floor_parts.append('Tum: %sm²' % rec.vd_intake_floor_tum_m2)
            if rec.vd_intake_has_lung and rec.vd_intake_floor_lung_m2:
                floor_parts.append('Lửng: %sm²' % rec.vd_intake_floor_lung_m2)
            if floor_parts:
                lines.append('🏗️ SỐ TẦNG: %s' % ' | '.join(floor_parts))

            # 🛋️ CÔNG NĂNG (không icon trong nội dung công năng)
            cn_lines = []
            for i in range(1, n + 1):
                fns = _fn_names(rec['vd_intake_floor_%s_function_ids' % i])
                if fns:
                    cn_lines.append('   • T%s: %s' % (i, fns))
            if rec.vd_intake_has_lung:
                fns = _fn_names(rec.vd_intake_floor_lung_function_ids)
                if fns:
                    cn_lines.append('   • Lửng: %s' % fns)
            if rec.vd_intake_has_tum:
                fns = _fn_names(rec.vd_intake_floor_tum_function_ids)
                if fns:
                    cn_lines.append('   • Tum: %s' % fns)
            if cn_lines:
                lines.append('🛋️ CÔNG NĂNG:')
                lines.extend(cn_lines)
            if rec.vd_intake_function_notes:
                lines.append('   Ghi chú: %s' % rec.vd_intake_function_notes)

            # 🚧 CHỖ ĐỂ ĐẤT MÓNG
            if rec.vd_intake_soil_dump:
                lines.append('🚧 CHỖ ĐỂ ĐẤT MÓNG: %s' % _sel_label(rec, 'vd_intake_soil_dump'))

            # 🚗 Ô TÔ VÀO
            if rec.vd_intake_car_access_select:
                lines.append('🚗 Ô TÔ VÀO: %s' % _sel_label(rec, 'vd_intake_car_access_select'))

            # 💰 TẦM TÀI CHÍNH
            if rec.vd_intake_budget_range:
                budget = _sel_label(rec, 'vd_intake_budget_range') or rec.vd_intake_budget_range
                lines.append('💰 TẦM TÀI CHÍNH: %s' % budget)
            elif rec.vd_intake_budget_amount:
                lines.append('💰 TẦM TÀI CHÍNH: %s đ' % '{:,.0f}'.format(rec.vd_intake_budget_amount))

            # 📜 SỔ ĐỎ / CẤP PHÉP
            if rec.vd_intake_dimensions:
                lines.append('📜 SỔ ĐỎ: %s' % _sel_label(rec, 'vd_intake_dimensions'))

            lines.append('────────────────────')
            rec.vd_zalo_copy_text = '\n'.join(lines)

    def action_copy_zalo(self):
        """User spec 2026-05-29: mở popup preview với nút Copy. Click button trong
        popup = fresh user gesture → navigator.clipboard.writeText() always works.
        (silent=True bị browser block do action chain mất user-gesture context.)"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_copy_to_clipboard',
            'params': {
                'text': self.vd_zalo_copy_text or '',
                'message': _('Đã copy thông tin KH vào clipboard. Dán vào Zalo!'),
                'silent': False,
            },
        }

    def action_copy_name(self):
        """Copy tên KH vào clipboard (dùng từ chip tên trong header form)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_copy_to_clipboard',
            'params': {
                'text': self.name or '',
                'message': _('Đã copy tên khách hàng vào clipboard.'),
            },
        }

    def action_copy_phone(self):
        """Copy số điện thoại KH vào clipboard (click vào chip phone trong header)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_copy_to_clipboard',
            'params': {
                'text': self.phone or '',
                'message': _('Đã copy số điện thoại vào clipboard.'),
            },
        }

    @api.depends(
        'vd_intake_total_m2', 'vd_intake_floors_num', 'vd_intake_foundation_type',
        'vd_intake_house_type', 'vd_intake_roof_type', 'vd_intake_region',
        'vd_intake_car_access', 'vd_intake_estimate', 'vd_quote_price',
        'vd_intake_floors_select', 'vd_intake_has_tum',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2',
        'vd_intake_floor_1_function_ids', 'vd_intake_floor_2_function_ids',
        'vd_intake_floor_3_function_ids', 'vd_intake_floor_4_function_ids',
        'vd_intake_floor_5_function_ids', 'vd_intake_floor_6_function_ids',
        'vd_intake_floor_7_function_ids', 'vd_intake_floor_tum_function_ids',
        # Round 10: Lửng + Khuyến mãi
        'vd_intake_has_lung', 'vd_intake_floor_lung_m2',
        'vd_intake_floor_lung_function_ids',
        # Round 12: KM từ problems
        'vd_lead_problem_ids.km_state', 'vd_lead_problem_ids.km_amount',
        'vd_lead_problem_ids.km_type', 'vd_lead_problem_ids.km_material_name',
        'vd_lead_problem_ids.km_price_old', 'vd_lead_problem_ids.km_price_new',
        # Round 12.1: PS (phát sinh vật tư) từ problems
        'vd_lead_problem_ids.ps_state', 'vd_lead_problem_ids.ps_amount',
        'vd_lead_problem_ids.ps_material_name',
    )
    def _vd_km_row_label(self, p):
        """Nhãn dòng KM trong báo giá chi tiết — theo 3 loại KM."""
        if p.km_type == 'discount_price':
            def _f(n):
                return '{:,.0f}'.format(n or 0).replace(',', '.')
            return '🏷️ Giảm đơn giá: %s→%s' % (_f(p.km_price_old), _f(p.km_price_new))
        if p.km_type == 'promo_material' and p.km_material_name:
            return f'🎁 KM: {p.km_material_name}'
        return '💸 Khuyến mãi tiền'

    def _compute_quote_breakdown_html(self):
        Pricing = self.env['vd.pricing.region']
        for rec in self:
            total_m2 = rec.vd_intake_total_m2 or 0.0
            floors = rec.vd_intake_floors_num or 1.0
            if not total_m2:
                rec.vd_quote_breakdown_html = (
                    '<div style="padding:0.7rem;text-align:center;color:#868e96;'
                    'background:#f8f9fa;border:1px dashed #ced4da;border-radius:6px;">'
                    '<i>Chưa có dữ liệu — cần Tổng diện tích sàn, Số tầng, Loại móng để tính breakdown.</i></div>'
                )
                continue
            pricing = Pricing.search([('code', '=', rec.vd_intake_region)], limit=1) if rec.vd_intake_region else None
            if not pricing:
                rec.vd_quote_breakdown_html = (
                    '<div style="padding:0.7rem;text-align:center;color:#92400e;'
                    'background:#fffbeb;border:1px dashed #fbbf24;border-radius:6px;">'
                    '<i>Chưa cấu hình pricing region — bảng breakdown chưa hiển thị.</i></div>'
                )
                continue

            # MÓNG: diện tích Tầng 1; MÁI: diện tích tầng trên cùng;
            # SÀN: tổng diện tích các tầng (giữ nguyên).
            found_area, roof_area = rec._vd_get_found_roof_areas()
            # Đơn giá sàn theo DT 1 SÀN (footprint), KHÔNG theo tổng sàn (fix 2026-06-12)
            san_unit = rec._vd_san_unit_for(pricing)
            # Threshold % móng theo DT MÓNG (Tầng 1), KHÔNG phải tổng sàn (fix 2026-05-28)
            found_pct = rec._get_foundation_pct(pricing, rec.vd_intake_foundation_type, found_area >= 70)
            roof_pct = rec._get_roof_pct(pricing, rec._vd_resolve_roof_type())
            found_cost = found_area * (found_pct / 100.0) * san_unit
            roof_cost = roof_area * (roof_pct / 100.0) * san_unit

            # ===== Build per-floor rows từ diện tích mỗi tầng đã nhập =====
            # Round 10 fix: bổ sung Lửng vào breakdown (trước đó bị thiếu).
            n_floors = int(rec.vd_intake_floors_select) if rec.vd_intake_floors_select else 0
            per_floor_data = []  # list of (label, area_m2)  — bỏ công năng
            sum_per_floor_area = 0.0
            for i in range(1, n_floors + 1):
                fa = rec[f'vd_intake_floor_{i}_m2'] or 0.0
                if fa > 0:
                    per_floor_data.append((f'Tầng {i}', fa))
                    sum_per_floor_area += fa
            if rec.vd_intake_has_lung:
                lung_a = rec.vd_intake_floor_lung_m2 or 0.0
                if lung_a > 0:
                    per_floor_data.append(('Lửng', lung_a))
                    sum_per_floor_area += lung_a
            if rec.vd_intake_has_tum:
                tum_a = rec.vd_intake_floor_tum_m2 or 0.0
                if tum_a > 0:
                    per_floor_data.append(('Tum', tum_a))
                    sum_per_floor_area += tum_a

            if per_floor_data and sum_per_floor_area > 0:
                # Tính cost per floor từ diện tích thực, không dùng area × floors.
                floor_cost = sum_per_floor_area * san_unit
                floor_rows_html = ''
                for label, fa in per_floor_data:
                    cost = fa * san_unit
                    floor_rows_html += f'''
        <tr>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;font-weight:600;font-size:0.85rem;">{label}</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:center;font-size:0.85rem;">{fa:.0f} M2</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(san_unit)} VNĐ</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(cost)} VNĐ</td>
        </tr>'''
            else:
                # Fallback: 1 dòng "Tổng sàn" — dùng total_m2, không phụ thuộc diện tích đất.
                floor_cost = total_m2 * san_unit
                floor_rows_html = f'''
        <tr>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;font-weight:600;font-size:0.85rem;">Tổng sàn ({floors:g} tầng)</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:center;font-size:0.85rem;">{total_m2:.0f} M2</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(san_unit)} VNĐ</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(floor_cost)} VNĐ</td>
        </tr>'''

            # THÔNG TẦNG (user spec 2026-06-05): có Lửng → tự thêm 1 dòng thông
            # tầng = DT thông tầng (Tầng1 − Lửng, NV sửa được) × 40% × đơn giá sàn.
            thongtang_cost = 0.0
            thongtang_extra_rows = 0
            if rec.vd_intake_has_lung:
                tt_base = rec.vd_intake_floor_thongtang_m2 or 0.0
                if tt_base > 0:
                    tt_pct = rec._get_roof_pct(pricing, 'thong_tang') or 0.0
                    thongtang_cost = tt_base * (tt_pct / 100.0) * san_unit
                    thongtang_extra_rows = 1
                    floor_rows_html += f'''
        <tr>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;font-weight:600;font-size:0.85rem;">Thông tầng</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:center;font-size:0.85rem;">{tt_base:.0f} M2 x {tt_pct:.0f}%</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(san_unit)} VNĐ</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(thongtang_cost)} VNĐ</td>
        </tr>'''

            # Round 12: TRỪ KM (khuyến mãi) — approved problems tag_code='promotion'
            km_problems = rec.vd_lead_problem_ids.filtered(
                lambda p: p.tag_code == 'promotion' and p.km_state == 'approved' and (p.km_amount or 0) > 0
            )
            km_total = sum(p.km_amount or 0 for p in km_problems)
            # Round 12.1: CỘNG PS (phát sinh vật tư) — approved tag_code='extra_material'
            ps_problems = rec.vd_lead_problem_ids.filtered(
                lambda p: p.tag_code == 'extra_material' and p.ps_state == 'approved' and (p.ps_amount or 0) > 0
            )
            ps_total = sum(p.ps_amount or 0 for p in ps_problems)
            total = found_cost + floor_cost + roof_cost + thongtang_cost + ps_total - km_total
            # rowspan = móng + N tầng + (thông tầng) + mái + N dòng PS + N dòng KM
            num_rows = (2 + max(len(per_floor_data), 1) + thongtang_extra_rows
                        + len(ps_problems) + len(km_problems))

            # Build PS rows HTML (xanh — cộng tiền)
            ps_rows_html = ''
            for ps in ps_problems:
                ps_label = f'🧰 PS: {ps.ps_material_name}' if ps.ps_material_name else '🧰 Phát sinh vật tư'
                ps_rows_html += (
                    '<tr style="background:#e6fcf5;">'
                    f'<td style="padding:0.5rem 0.55rem;border:1px solid #63e6be;background:#e6fcf5;font-weight:700;color:#0b7285;font-size:0.85rem;">{ps_label}</td>'
                    '<td style="padding:0.5rem 0.55rem;border:1px solid #63e6be;background:#e6fcf5;text-align:center;color:#0b7285;font-size:0.85rem;">—</td>'
                    '<td style="padding:0.5rem 0.55rem;border:1px solid #63e6be;background:#e6fcf5;text-align:right;color:#0b7285;font-size:0.85rem;">—</td>'
                    f'<td style="padding:0.5rem 0.55rem;border:1px solid #63e6be;background:#e6fcf5;text-align:right;font-weight:700;color:#0b7285;font-size:0.85rem;">+ {self._fmt_vnd(ps.ps_amount)} VNĐ</td>'
                    '</tr>'
                )
            # Build KM rows HTML (vàng — trừ tiền)
            km_rows_html = ''
            for km in km_problems:
                km_label = self._vd_km_row_label(km)
                km_rows_html += (
                    '<tr style="background:#fff8e1;">'
                    f'<td style="padding:0.5rem 0.55rem;border:1px solid #ffd43b;background:#fff8e1;font-weight:700;color:#d9480f;font-size:0.85rem;">{km_label}</td>'
                    '<td style="padding:0.5rem 0.55rem;border:1px solid #ffd43b;background:#fff8e1;text-align:center;color:#d9480f;font-size:0.85rem;">—</td>'
                    '<td style="padding:0.5rem 0.55rem;border:1px solid #ffd43b;background:#fff8e1;text-align:right;color:#d9480f;font-size:0.85rem;">—</td>'
                    f'<td style="padding:0.5rem 0.55rem;border:1px solid #ffd43b;background:#fff8e1;text-align:right;font-weight:700;color:#d9480f;font-size:0.85rem;">− {self._fmt_vnd(km.km_amount)} VNĐ</td>'
                    '</tr>'
                )
            # PS rows trước (cộng) → KM rows sau (trừ) — render trước dòng mái close cuối
            discount_row_html = ps_rows_html + km_rows_html

            found_lbl = self._vd_selection_dict('vd_intake_foundation_type').get(
                rec.vd_intake_foundation_type, 'Móng đơn'
            ) or 'Móng'
            # Roof label: ưu tiên roof_type cụ thể (vd "Mái thái — Có đổ trần").
            # Fallback: lấy từ house_type (vd "Nhà mái thái" → "Mái thái").
            # Cuối cùng: hiện "Chưa chọn mái" để NV biết cần cập nhật.
            roof_lbl = ''
            if rec.vd_intake_roof_type:
                roof_lbl = self._vd_selection_dict('vd_intake_roof_type').get(
                    rec.vd_intake_roof_type, ''
                )
                # Bỏ phần % trong ngoặc "(20%)" để gọn
                if '(' in roof_lbl:
                    roof_lbl = roof_lbl.split('(')[0].strip()
            if not roof_lbl and rec.vd_intake_house_type:
                house_lbl = self._vd_selection_dict('vd_intake_house_type').get(
                    rec.vd_intake_house_type, ''
                )
                # "Nhà mái thái" → "Mái thái"
                roof_lbl = house_lbl.replace('Nhà ', '').capitalize() if house_lbl else ''
            if not roof_lbl:
                roof_lbl = '⚠️ Chưa chọn mái'

            rec.vd_quote_breakdown_html = f'''
<table class="o_vd_quote_breakdown_tbl" style="width:100%;border-collapse:collapse;font-size:0.82rem;margin:0.4rem 0;">
    <thead>
        <tr style="background:#5c8fb8;color:#fff;">
            <th style="padding:0.5rem;border:1px solid #1864ab;text-align:left;font-weight:700;font-size:0.85rem;">Nội dung</th>
            <th style="padding:0.5rem;border:1px solid #1864ab;text-align:center;font-weight:700;font-size:0.85rem;">Diện tích</th>
            <th style="padding:0.5rem;border:1px solid #1864ab;text-align:right;font-weight:700;font-size:0.85rem;">Đơn giá</th>
            <th style="padding:0.5rem;border:1px solid #1864ab;text-align:right;font-weight:700;font-size:0.85rem;">Thành Tiền</th>
            <th style="padding:0.5rem;border:1px solid #1864ab;text-align:center;font-weight:700;font-size:0.85rem;background:#4a7aa0;">Tổng Tiền</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;font-weight:600;font-size:0.85rem;">{found_lbl}</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:center;font-size:0.85rem;">{found_area:.0f} M2 x {found_pct:.0f}%</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(san_unit)} VNĐ</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(found_cost)} VNĐ</td>
            <td rowspan="{num_rows}" style="padding:0.5rem 0.55rem;border:1px solid #1864ab;background:#dbeafe;text-align:center;font-weight:700;font-size:1rem;color:#1864ab;vertical-align:middle;">{self._fmt_vnd(total)} VNĐ</td>
        </tr>{floor_rows_html}
        <tr>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;font-weight:600;font-size:0.85rem;">{roof_lbl}</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:center;font-size:0.85rem;">{roof_area:.0f} M2 x {roof_pct:.0f}%</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(san_unit)} VNĐ</td>
            <td style="padding:0.5rem 0.55rem;border:1px solid #93c5fd;background:#fff;text-align:right;font-size:0.85rem;">{self._fmt_vnd(roof_cost)} VNĐ</td>
        </tr>{discount_row_html}
    </tbody>
</table>
'''.strip()

    @api.model
    def _fmt_vnd(self, n):
        return f'{n:,.0f}'.replace(',', '.')

    @api.model
    def _fmt_vnd_short(self, n):
        """Rút gọn số tiền VNĐ cho cột hẹp: ≥1 tỷ → 'X,X tỷ', ≥1 triệu → 'X tr'."""
        n = abs(n or 0)
        if n >= 1_000_000_000:
            s = f'{n / 1_000_000_000:.1f}'.rstrip('0').rstrip('.')
            return f'{s} tỷ'
        if n >= 1_000_000:
            return f'{n / 1_000_000:.0f} tr'
        if n >= 1_000:
            return f'{n / 1_000:.0f}k'
        return f'{n:.0f}'

    # PREVIEW PDF — Binary field + widget="pdf_viewer" hiển thị inline
    # NV bấm "🔄 Cập nhật preview" → generate file → embed PDF reader
    vd_quote_preview_pdf = fields.Binary(
        string='Preview PDF', attachment=True, copy=False,
    )
    vd_quote_preview_pdf_name = fields.Char(default='preview_baogia.pdf', copy=False)

    # Toggle preview inline: NV bấm 👁️ Xem PDF preview để hiện/ẩn cột preview.
    # Default False = preview ẩn, panel báo giá chỉ chiếm 1 cột (form gọn hơn).
    vd_quote_show_preview = fields.Boolean(
        string='Hiển thị preview PDF',
        default=False, copy=False,
    )

    def action_toggle_quote_preview(self):
        """Toggle preview inline. Lần đầu bật + chưa có PDF → auto generate."""
        self.ensure_one()
        if not self.vd_quote_show_preview and not self.vd_quote_preview_pdf:
            self.action_refresh_quote_preview()
        self.vd_quote_show_preview = not self.vd_quote_show_preview
        return True

    def action_refresh_quote_preview(self):
        """🔄 Generate file PDF merged + lưu vào field Binary để widget
        pdf_viewer embed inline. Ưu tiên render từ template upload."""
        self.ensure_one()
        import base64

        # Generate file mới: ưu tiên template upload (giữ nguyên trang)
        att = self._render_uploaded_template()
        pdf_bytes = None
        if att:
            pdf_bytes = base64.b64decode(att.datas)
        else:
            # Fallback: QWeb 4 trang
            try:
                new_v = self._generate_quote_pdf_now()
                if new_v.pdf_attachment_id:
                    pdf_bytes = base64.b64decode(new_v.pdf_attachment_id.datas)
            except Exception:
                pass

        if pdf_bytes:
            kh = self.partner_name or self.contact_name or self.name or 'KH'
            kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
            self.vd_quote_preview_pdf = base64.b64encode(pdf_bytes)
            self.vd_quote_preview_pdf_name = f'BaoGia_{kh_safe}.pdf'
        return True

    @api.depends(
        'name', 'phone', 'vd_intake_province_id', 'vd_intake_district',
        'vd_intake_house_type', 'vd_intake_foundation_type', 'vd_intake_roof_type',
        'vd_intake_total_m2', 'vd_intake_floors_num', 'vd_intake_estimate',
        'vd_intake_floors_select', 'vd_intake_has_tum',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2',
        'vd_intake_region', 'vd_intake_car_access', 'vd_quote_price',
    )
    def _compute_quote_preview_html(self):
        """Render báo giá HTML inline preview — same logic with QWeb PDF report."""
        from datetime import date
        Pricing = self.env['vd.pricing.region']
        for rec in self:
            total_m2 = rec.vd_intake_total_m2 or 0.0
            floors = rec.vd_intake_floors_num or 1.0
            if total_m2 <= 0 or not rec.vd_intake_region:
                rec.vd_quote_preview_html = (
                    '<div style="padding:1rem;text-align:center;color:#868e96;'
                    'font-style:italic;background:#f8f9fa;border:1px dashed #dee2e6;'
                    'border-radius:8px;">'
                    '<i class="fa fa-file-pdf-o" style="font-size:2rem;display:block;'
                    'margin-bottom:0.5rem;"></i>'
                    'Chưa đủ thông tin khai thác để preview báo giá.<br/>'
                    '<small>Cần: tỉnh/thành, tổng diện tích sàn, số tầng, móng, mái.</small>'
                    '</div>'
                )
                continue

            pricing = Pricing.search([('code', '=', rec.vd_intake_region)], limit=1)
            if not pricing:
                rec.vd_quote_preview_html = '<i>Chưa có pricing region.</i>'
                continue

            # Tất cả formula dùng TỔNG DIỆN TÍCH SÀN
            sum_floor_areas = 0.0
            n_floors_select = int(rec.vd_intake_floors_select) if rec.vd_intake_floors_select else 0
            for i in range(1, n_floors_select + 1):
                sum_floor_areas += rec['vd_intake_floor_%s_m2' % i] or 0.0
            if rec.vd_intake_has_tum and rec.vd_intake_floor_tum_m2:
                sum_floor_areas += rec.vd_intake_floor_tum_m2
            if sum_floor_areas <= 0:
                sum_floor_areas = total_m2  # fallback total_m2 (NV nhập tay)

            san_unit = rec._vd_san_unit_for(pricing)  # bậc giá theo DT 1 sàn (fix 2026-06-12)
            # Threshold % móng theo DT MÓNG (Tầng 1) — fix 2026-05-28
            _found_area_th, _ = rec._vd_get_found_roof_areas()
            found_pct = rec._get_foundation_pct(
                pricing, rec.vd_intake_foundation_type, _found_area_th >= 70,
            )
            roof_pct = rec._get_roof_pct(pricing, rec._vd_resolve_roof_type())
            found_cost = total_m2 * (found_pct / 100.0) * san_unit
            floor_cost = sum_floor_areas * san_unit
            roof_cost = total_m2 * (roof_pct / 100.0) * san_unit

            # Labels
            house_lbl = self._vd_selection_dict('vd_intake_house_type').get(
                rec.vd_intake_house_type, 'NHÀ DÂN DỤNG'
            ) or 'NHÀ DÂN DỤNG'
            found_lbl = self._vd_selection_dict('vd_intake_foundation_type').get(
                rec.vd_intake_foundation_type, 'MÓNG ĐƠN'
            ) or 'MÓNG ĐƠN'
            roof_lbl = self._vd_selection_dict('vd_intake_roof_type').get(
                rec._vd_resolve_roof_type(), 'MÁI BẰNG'
            ) or 'MÁI BẰNG'

            kh_name = rec.partner_name or rec.contact_name or rec.name or ''
            kh_address = ', '.join(filter(None, [
                rec.vd_intake_district.name if rec.vd_intake_district else '',
                rec.vd_intake_province_id.name if rec.vd_intake_province_id else '',
            ]))
            today_str = date.today().strftime('%d/%m/%Y')
            total_price = rec.vd_quote_price or rec.vd_intake_estimate or 0

            def fmt(n):
                return f'{n:,.0f}'.replace(',', '.')

            # ========== 1 TRANG DUY NHẤT — replica file mẫu Lệ Chi ==========
            kh_phone = rec.phone or rec.mobile or ''
            rec.vd_quote_preview_html = f'''
<div style="background:#fff;border:1px solid #ccc;padding:1.2rem 1rem;font-family:'Times New Roman',serif;font-size:11px;color:#1a1a1a;position:relative;">
    <!-- Decorative triangles góc phải -->
    <div style="position:absolute;top:0;right:0;width:90px;height:75px;overflow:hidden;pointer-events:none;">
        <div style="position:absolute;top:-20px;right:-20px;width:110px;height:110px;background:linear-gradient(135deg,#fb923c 0%,#fed7aa 100%);transform:rotate(45deg);opacity:0.85;"></div>
        <div style="position:absolute;top:30px;right:-15px;width:55px;height:80px;background:linear-gradient(180deg,#1864ab 0%,#4dabf7 100%);transform:rotate(20deg);opacity:0.8;"></div>
    </div>
    <!-- HEADER: Logo + Tiêu đề -->
    <table style="width:100%;border:none;margin-bottom:0.6rem;">
        <tr>
            <td style="width:22%;vertical-align:middle;padding-right:0.4rem;">
                <div style="background:#fff;border:2px solid #1864ab;border-radius:6px;padding:0.35rem 0.6rem;display:inline-block;text-align:center;">
                    <span style="font-weight:900;font-size:14pt;color:#fa5252;font-style:italic;">V</span><span style="font-weight:900;font-size:14pt;color:#1864ab;letter-spacing:0.5px;">INADUY</span>
                </div>
            </td>
            <td style="vertical-align:middle;text-align:center;background:linear-gradient(180deg,#5c8fb8 0%,#1864ab 100%);border-radius:5px;padding:0.7rem 0.4rem;">
                <span style="color:#fff;font-size:13pt;font-weight:700;letter-spacing:1.5px;">BẢNG BÁO GIÁ CHI TIẾT</span>
            </td>
        </tr>
    </table>
    <!-- INTRO BULLETS -->
    <ul style="padding-left:1.3rem;margin:0.7rem 0 0.9rem;line-height:1.6;font-size:10.5pt;">
        <li><b>VINADUY</b> xin gửi tới quý Khách hàng bảng báo giá chi tiết xây nhà trọn gói nhà ở dân dụng</li>
        <li>Bảng báo giá được áp dụng với mẫu nhà <b style="color:#c92a2a;text-transform:uppercase;">{house_lbl}</b></li>
        <li>Kết cấu móng được sử dụng là hệ <b style="color:#c92a2a;text-transform:uppercase;">{found_lbl}</b></li>
    </ul>
    <!-- KH INFO TABLE -->
    <table style="width:60%;border-collapse:collapse;margin-bottom:0.8rem;font-size:10.5pt;">
        <tr><td style="padding:0.4rem 0.7rem;background:#dbeafe;font-weight:700;border:1px solid #93c5fd;width:40%;">Khách Hàng</td><td style="padding:0.4rem 0.7rem;background:#fff;border:1px solid #93c5fd;">{kh_name or '—'}</td></tr>
        <tr><td style="padding:0.4rem 0.7rem;background:#dbeafe;font-weight:700;border:1px solid #93c5fd;">Ngày tạo</td><td style="padding:0.4rem 0.7rem;background:#fff;border:1px solid #93c5fd;">{today_str}</td></tr>
        <tr><td style="padding:0.4rem 0.7rem;background:#dbeafe;font-weight:700;border:1px solid #93c5fd;">Địa Chỉ</td><td style="padding:0.4rem 0.7rem;background:#fff;border:1px solid #93c5fd;">{kh_address or '—'}</td></tr>
    </table>
    <!-- PRICING TABLE -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:0.6rem;font-size:10.5pt;">
        <thead>
            <tr style="background:#5c8fb8;color:#fff;">
                <th style="padding:0.5rem;border:1px solid #1864ab;text-align:left;font-weight:700;">Nội dung</th>
                <th style="padding:0.5rem;border:1px solid #1864ab;text-align:center;font-weight:700;">Diện tích</th>
                <th style="padding:0.5rem;border:1px solid #1864ab;text-align:right;font-weight:700;">Đơn giá</th>
                <th style="padding:0.5rem;border:1px solid #1864ab;text-align:right;font-weight:700;">Thành Tiền</th>
                <th style="padding:0.5rem;border:1px solid #1864ab;text-align:center;font-weight:700;background:#4a7aa0;">Tổng Tiền</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;">{found_lbl}</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{total_m2:.0f} M2 x {found_pct:.0f}%</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(found_cost)} VNĐ</td>
                <td rowspan="3" style="padding:0.45rem 0.6rem;border:1px solid #1864ab;background:#fff;text-align:center;font-weight:700;font-size:13pt;color:#1a1a1a;vertical-align:middle;">{fmt(total_price)} VNĐ</td>
            </tr>
            <tr>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;">Tầng trệt</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{sum_floor_areas:.0f}</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(floor_cost)} VNĐ</td>
            </tr>
            <tr>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;">{roof_lbl}</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{total_m2:.0f} M2 x {roof_pct:.0f}%</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.38rem 0.5rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(roof_cost)} VNĐ</td>
            </tr>
        </tbody>
    </table>
    <!-- STAMP góc phải dưới -->
    <div style="text-align:right;margin-top:3rem;">
        <div style="display:inline-block;border:2px solid #c92a2a;border-radius:50%;padding:0.7rem 0.85rem;color:#c92a2a;font-weight:700;line-height:1.2;text-align:center;">
            <div style="font-size:7pt;">M.S.D.N: 0109446258 - C.T.C.P</div>
            <div style="font-size:9pt;margin:0.2rem 0;">CÔNG TY<br/>CỔ PHẦN<br/>VINADUY</div>
            <div style="font-size:7pt;">★ THÀNH PHỐ HÀ NỘI ★</div>
        </div>
    </div>
    <!-- HOTLINE FOOTER -->
    <div style="margin-top:0.6rem;padding-top:0.4rem;border-top:1px solid #1864ab;font-size:9pt;color:#1864ab;">
        ☎ <b>1900 9999 46 — 024 99999 868</b>
    </div>
</div>
'''.strip()

    @api.depends('vd_intake_estimate')
    def _compute_quote_price_default(self):
        """LUÔN sync với ước tính từ khai thác — KH muốn giá báo đúng = ước tính."""
        for rec in self:
            if rec.vd_intake_estimate:
                rec.vd_quote_price = rec.vd_intake_estimate
            elif not rec.vd_quote_price:
                rec.vd_quote_price = 0.0

    @api.depends('vd_quote_date')
    def _compute_quote_valid_until(self):
        """Auto = ngày báo + 30 ngày."""
        from datetime import timedelta
        for rec in self:
            if rec.vd_quote_date and not rec.vd_quote_valid_until:
                rec.vd_quote_valid_until = rec.vd_quote_date + timedelta(days=30)

    @api.onchange('vd_quote_template_upload')
    def _onchange_template_upload(self):
        """Khi NV upload file mới → tự tạo vd.quote.template + gán cho lead.
        Mỗi upload mới sinh 1 template record (không clear upload field
        trong onchange để tránh recursion — upload field sẽ tự reset sau save)."""
        if not self.vd_quote_template_upload:
            return
        tpl_name = self.vd_quote_template_upload_name or 'Template upload'
        display = tpl_name.rsplit('.', 1)[0][:80] or 'Template upload'
        tpl = self.env['vd.quote.template'].create({
            'name': f'{display} (NV upload)',
            'file_attachment': self.vd_quote_template_upload,
            'file_name': tpl_name,
            'description': f'Tự upload bởi {self.env.user.name} cho lead "{self.name or ""}"',
        })
        self.vd_quote_template_id = tpl.id
    vd_quote_material = fields.Char(
        string='Vật liệu chính',
        help='Vd: Xi măng Hà Tiên, gạch Đồng Tâm, sơn Dulux...',
    )
    vd_quote_payment_schedule = fields.Text(
        string='Tiến độ thanh toán', default='Đợt 1: 30% khi ký HĐ\nĐợt 2: 30% xong móng\nĐợt 3: 30% xong phần thô\nĐợt 4: 10% bàn giao',
    )
    vd_quote_notes = fields.Text(string='Ghi chú báo giá')

    # Versions + lock state
    vd_quote_version_ids = fields.One2many('vd.quote.version', 'lead_id', string='Lịch sử báo giá')
    vd_quote_version_count = fields.Integer(compute='_compute_quote_version_count', store=False)
    vd_quote_locked = fields.Boolean(string='Đã chốt báo giá', readonly=True, copy=False)
    vd_quote_locked_version_id = fields.Many2one(
        'vd.quote.version', string='Bản chốt cuối', readonly=True, copy=False,
    )

    @api.depends('vd_quote_version_ids')
    def _compute_quote_version_count(self):
        for rec in self:
            rec.vd_quote_version_count = len(rec.vd_quote_version_ids)

    # Danh sách báo giá cũ (hover nút "Báo giá cũ") — mới nhất trên cùng, ghi rõ
    # bản V mấy + ngày + giá. User spec 2026-05-31.
    vd_quote_versions_html = fields.Html(
        string='Danh sách báo giá cũ',
        compute='_compute_quote_versions_html', store=False, sanitize=False,
    )

    @api.depends('vd_quote_version_ids', 'vd_quote_version_count')
    def _compute_quote_versions_html(self):
        for rec in self:
            versions = rec.vd_quote_version_ids.sorted(
                key=lambda v: (v.version_no or 0), reverse=True
            )
            if not versions:
                rec.vd_quote_versions_html = ''
                continue
            rows = ''
            for v in versions:
                d = (fields.Datetime.context_timestamp(rec, v.create_date).strftime('%d/%m/%Y %H:%M')
                     if v.create_date else '—')
                price = self._fmt_vnd(v.quote_price) if v.quote_price else '—'
                locked = ' · 🔒 chốt' if v.state == 'locked' else ''
                rows += (
                    f'<tr style="border-bottom:1px solid #f1f3f5;">'
                    f'<td style="padding:5px 9px;font-weight:800;color:#1864ab;white-space:nowrap;">Bản V{v.version_no}</td>'
                    f'<td style="padding:5px 9px;color:#495057;white-space:nowrap;">{d}{locked}</td>'
                    f'<td style="padding:5px 9px;text-align:right;font-weight:700;color:#1f2a44;white-space:nowrap;">{price} VNĐ</td>'
                    f'</tr>'
                )
            rec.vd_quote_versions_html = (
                f'<div style="font-weight:800;color:#fff;background:linear-gradient(135deg,#5c8fb8,#4a7aa0);'
                f'padding:6px 10px;font-size:0.82rem;border-radius:8px 8px 0 0;">📋 Báo giá cũ (mới nhất trên cùng)</div>'
                f'<table style="width:100%;border-collapse:collapse;font-size:0.8rem;background:#fff;">{rows}</table>'
            )

    # ============================================================
    # BÁO GIÁ CŨ — nút "📋 Báo giá cũ" CHỈ hiện khi đã TẠO + GIẢI QUYẾT
    # vấn đề "Cân đối ngân sách". Hover → popup bảng báo giá chi tiết GỐC
    # (snapshot lúc tạo vấn đề, trước khi cân đối). User spec 2026-05-31.
    # ============================================================
    vd_has_old_quote = fields.Boolean(
        string='Có báo giá cũ', compute='_compute_vd_old_quote', store=False,
    )
    vd_oldquote_breakdown_html = fields.Html(
        string='Báo giá cũ (bảng chi tiết)',
        compute='_compute_vd_old_quote', store=False, sanitize=False,
    )

    @api.depends(
        'vd_lead_problem_ids.tag_code', 'vd_lead_problem_ids.status',
        'vd_lead_problem_ids.old_quote_html',
    )
    def _compute_vd_old_quote(self):
        for rec in self:
            # Vấn đề cân đối ngân sách ĐÃ giải quyết + có snapshot báo giá gốc.
            probs = rec.vd_lead_problem_ids.filtered(
                lambda p: p.tag_code == 'budget_balance'
                and p.status == 'resolved'
                and p.old_quote_html
            ).sorted(key=lambda p: (p.write_date or p.create_date or fields.Datetime.now()), reverse=True)
            if not probs:
                rec.vd_has_old_quote = False
                rec.vd_oldquote_breakdown_html = ''
                continue
            rec.vd_has_old_quote = True
            blocks = ''
            for p in probs:
                d = (fields.Datetime.context_timestamp(rec, p.create_date).strftime('%d/%m/%Y %H:%M')
                     if p.create_date else '—')
                blocks += (
                    f'<div style="font-weight:800;color:#fff;background:linear-gradient(135deg,#5c8fb8,#4a7aa0);'
                    f'padding:6px 10px;font-size:0.82rem;border-radius:8px 8px 0 0;">'
                    f'📋 Báo giá cũ — trước khi cân đối ngân sách ({d})</div>'
                    f'<div style="padding:6px 8px;background:#fff;border-radius:0 0 8px 8px;">{p.old_quote_html}</div>'
                )
            rec.vd_oldquote_breakdown_html = blocks

    # ============ ĐÀM PHÁN + HỢP ĐỒNG ============
    vd_negotiate_deadline = fields.Date(
        string='Deadline đàm phán', copy=False,
        help='Auto = ngày chốt báo + 7 ngày. Quá deadline → cảnh báo manager.',
    )
    vd_negotiate_status = fields.Selection([
        ('ok', 'Trong hạn'),
        ('warn', 'Sắp quá hạn (≤ 2 ngày)'),
        ('overdue', 'QUÁ HẠN — cần escalate!'),
    ], compute='_compute_negotiate_status', store=False)

    # ===== Negotiation notes + checklist tiến độ =====
    vd_negotiate_notes = fields.Text(
        string='Ghi chú đàm phán',
        help='NV note các ý KH cần, lý do delay, điều khoản chốt v.v.',
        copy=False,
    )
    vd_nego_chk_quote_sent = fields.Boolean(
        string='Đã gửi báo giá qua Zalo/Email', copy=False)
    vd_nego_chk_explained = fields.Boolean(
        string='Đã giải thích chi phí từng hạng mục', copy=False)
    vd_nego_chk_timeline = fields.Boolean(
        string='Đã chốt thời gian khởi công', copy=False)
    vd_nego_chk_payment = fields.Boolean(
        string='Đã thống nhất điều khoản thanh toán', copy=False)
    vd_nego_chk_commit = fields.Boolean(
        string='KH cam kết miệng / sẵn sàng cọc', copy=False)

    # ===== PHÁT HIỆN VẤN ĐỀ KH (đàm phán) =====
    # Many2many — NV tick các vấn đề KH đang gặp. Một số được auto-suggest
    # dựa trên intake data (xem _compute_vd_nego_suggested_problem_ids).
    vd_nego_problem_ids = fields.Many2many(
        'vd.nego.problem', 'vd_lead_nego_problem_rel', 'lead_id', 'problem_id',
        string='Vấn đề KH gặp phải',
        copy=False,
        help='Các vấn đề KH đang vướng — giúp NV chọn giải pháp đàm phán phù hợp.',
    )
    vd_nego_suggested_problem_ids = fields.Many2many(
        'vd.nego.problem', 'vd_lead_nego_problem_sugg_rel', 'lead_id', 'problem_id',
        string='Vấn đề gợi ý (auto-detect)',
        compute='_compute_vd_nego_suggested_problem_ids',
        help='Hệ thống suy ra từ intake data — NV xem rồi tick thêm vào Vấn đề.',
    )
    vd_nego_problem_tips_html = fields.Html(
        string='Gợi ý xử lý các vấn đề đã chọn',
        compute='_compute_vd_nego_problem_tips_html',
        sanitize=False,
    )
    # ===== ROW-BASED PROBLEM TRACKER (mỗi vấn đề = 1 dòng) =====
    vd_lead_problem_ids = fields.One2many(
        'vd.lead.problem', 'lead_id',
        string='Vấn đề KH',
        copy=False,
        help='Tracker từng vấn đề KH gặp + cách NV xử lý + tiến độ.',
    )
    vd_custom_value_ids = fields.One2many(
        'vd.lead.custom.value', 'lead_id',
        string='Trường khai thác tuỳ chọn',
        copy=False,
    )
    vd_surcharge_ids = fields.One2many(
        'vd.lead.surcharge', 'lead_id',
        string='Phát sinh báo giá',
        copy=True,
        help='Items phát sinh thêm vào báo giá (Thêm WC, cầu thang phụ...).',
    )

    def _ensure_custom_value_records(self):
        """Tạo value record rỗng cho mọi custom field active mà lead chưa có.
        Gọi khi mở form lead → admin add new field thì tất cả lead cũ auto thấy."""
        Field = self.env['vd.intake.custom.field'].sudo()
        Value = self.env['vd.lead.custom.value'].sudo()
        active_fields = Field.search([('active', '=', True)])
        if not active_fields:
            return
        for lead in self:
            existing_field_ids = set(lead.vd_custom_value_ids.mapped('field_id.id'))
            missing = active_fields.filtered(lambda f: f.id not in existing_field_ids)
            for f in missing:
                Value.create({'lead_id': lead.id, 'field_id': f.id})

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._ensure_custom_value_records()
        return leads

    def read(self, fields=None, load='_classic_read'):
        # Lazy-fill khi UI load form (chỉ fill 1 lần / lead / session vì có sql constraint)
        if fields and 'vd_custom_value_ids' in fields and self.ids:
            try:
                self._ensure_custom_value_records()
            except Exception:
                pass
        return super().read(fields, load)
    vd_lead_problem_open_count = fields.Integer(
        string='Số vấn đề chưa giải quyết',
        compute='_compute_vd_lead_problem_open_count',
    )
    vd_problem_tag_picker = fields.Many2one(
        'vd.nego.problem', string='+ Tạo vấn đề',
        help='Pick 1 thẻ từ catalog để tạo vấn đề mới — chọn xong picker tự reset.',
    )

    @api.depends('vd_lead_problem_ids.status')
    def _compute_vd_lead_problem_open_count(self):
        for rec in self:
            rec.vd_lead_problem_open_count = len(
                rec.vd_lead_problem_ids.filtered(lambda p: p.status != 'resolved')
            )

    # Code các vấn đề ĐANG MỞ (chuẩn hoá), bọc dấu ',' → dùng cho invisible
    # ẩn nút trùng trong picker "Thêm vấn đề" (vd ',budget_balance,').
    vd_problem_used_codes = fields.Char(
        compute='_compute_problem_used_codes',
        help='Danh sách code vấn đề đang mở (đã chuẩn hoá) — ẩn nút tạo trùng.',
    )

    @api.model
    def _vd_norm_problem_code(self, code):
        """Chuẩn hoá code vấn đề: auto 'cost_diff' ≡ thủ công 'budget_balance'
        (cùng là 'Cân đối ngân sách') → tránh tạo trùng 2 thẻ cùng nội dung."""
        return 'budget_balance' if code == 'cost_diff' else (code or '')

    @api.depends('vd_lead_problem_ids', 'vd_lead_problem_ids.status',
                 'vd_lead_problem_ids.tag_id', 'vd_lead_problem_ids.code')
    def _compute_problem_used_codes(self):
        for rec in self:
            codes = set()
            for p in rec.vd_lead_problem_ids:
                if p.status == 'resolved':
                    continue
                raw = (p.tag_id.code if p.tag_id else False) or p.code or ''
                norm = rec._vd_norm_problem_code(raw)
                if norm:
                    codes.add(norm)
            rec.vd_problem_used_codes = (
                ',' + ','.join(sorted(codes)) + ',') if codes else ','

    @api.onchange('vd_problem_tag_picker')
    def _onchange_vd_problem_tag_picker(self):
        """NV chọn 1 thẻ từ dropdown → auto-tạo row vấn đề mới + reset picker.
        Không cần ép NV bấm 'Add a line' rồi gõ tay."""
        if self.vd_problem_tag_picker:
            tag = self.vd_problem_tag_picker
            self.vd_lead_problem_ids = [(0, 0, {
                'tag_id': tag.id,
                'name': tag.name,
                'status': 'open',
                'sequence': 50,
                'is_default': False,
            })]
            self.vd_problem_tag_picker = False

    def action_add_problem_tag(self):
        """Click 1 item trong dropdown 'Thêm vấn đề' → tạo row mới.
        Chặn trùng: nếu lead đã có vấn đề với tag này → notification cảnh báo, không tạo."""
        self.ensure_one()
        tag_xmlid = self.env.context.get('tag_xmlid')
        if not tag_xmlid:
            return
        tag = self.env.ref(tag_xmlid, raise_if_not_found=False)
        if not tag:
            return
        # Chặn TRÙNG: nếu lead đã có vấn đề ĐANG MỞ cùng loại (chuẩn hoá code —
        # auto 'cost_diff' ≡ thủ công 'budget_balance') → không tạo thêm.
        new_norm = self._vd_norm_problem_code(tag.code)
        dup = self.vd_lead_problem_ids.filtered(
            lambda p: p.status != 'resolved'
            and self._vd_norm_problem_code(
                (p.tag_id.code if p.tag_id else False) or p.code or '') == new_norm
        )
        if dup:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': 'Vấn đề đã tồn tại',
                    'message': f'"{tag.icon or "❓"} {tag.name}" đã có trong danh sách rồi.',
                    'sticky': False,
                },
            }
        self.env['vd.lead.problem'].create({
            'lead_id': self.id,
            'tag_id': tag.id,
            'name': tag.name,
            'status': 'open',
            'sequence': 50,
            'is_default': False,
        })
        return True

    def _vd_auto_budget_problem(self):
        """Tự sinh/cập nhật vấn đề 'Cân đối ngân sách' (code='cost_diff').
        User spec 2026-05-31: TẠO khi tầm tài chính KH THẤP HƠN GIÁ BÁO > 15%.
        Gọi ngay khi tạo báo giá hoặc khi NS KH / giá báo thay đổi.

        User spec 2026-06-01: KH CHƯA xác định tài chính (NS = 0) thì KHÔNG
        sinh vấn đề 'Cân đối ngân sách' — chưa biết NS thì không có gì để cân
        đối. Chỉ tạo khi biết CẢ NS KH lẫn giá báo VÀ chênh > 15%."""
        Problem = self.env['vd.lead.problem']
        THRESHOLD = 0.15  # > 15% so với GIÁ BÁO
        for rec in self:
            if rec.stage_is_won or rec.stage_is_lost:
                continue
            kh_budget = rec.vd_intake_budget_amount or 0
            quote = rec.vd_quote_price or 0
            existing = rec.vd_lead_problem_ids.filtered(lambda p: p.code == 'cost_diff')[:1]
            # Tránh TRÙNG: nếu NV đã tạo THỦ CÔNG vấn đề "Cân đối ngân sách"
            # (tag budget_balance) đang mở → coi như đã có, KHÔNG auto-sinh
            # cost_diff. (Không động vào vấn đề thủ công của NV.)
            if not existing:
                manual_budget = rec.vd_lead_problem_ids.filtered(
                    lambda p: p.status != 'resolved' and p.tag_id
                    and p.tag_id.code == 'budget_balance')
                if manual_budget:
                    continue
            name = None
            status = None
            if quote and kh_budget:
                diff = quote - kh_budget
                diff_pct = (diff / quote) if quote else 0  # base = GIÁ BÁO
                if diff > 0 and diff_pct > THRESHOLD:
                    name = (
                        '💰 CÂN ĐỐI NGÂN SÁCH: KH dự kiến %s đ — Giá báo %s đ — '
                        'Thiếu %s đ (chênh %.0f%% so với giá báo)'
                    ) % (
                        '{:,.0f}'.format(kh_budget), '{:,.0f}'.format(quote),
                        '{:,.0f}'.format(diff), diff_pct * 100,
                    )
                    status = 'open'
                elif diff > 0:
                    name = None  # chênh ≤ 15% → bỏ qua
                else:
                    name = '✅ CÂN ĐỐI NGÂN SÁCH: KH đủ NS (%s đ ≥ giá báo %s đ)' % (
                        '{:,.0f}'.format(kh_budget), '{:,.0f}'.format(quote),
                    )
                    status = 'resolved'
            # User spec 2026-06-01: BỎ nhánh "elif quote" (có giá báo nhưng
            # chưa biết NS) — không sinh vấn đề khi KH chưa xác định tài chính.
            # name=None → resolve vấn đề cost_diff cũ (nếu có) ở khối dưới.
            # Áp dụng
            if name is None:
                if existing and existing.status != 'resolved':
                    existing.with_context(mail_notrack=True).write({'status': 'resolved'})
            elif existing:
                existing.with_context(mail_notrack=True).write({'name': name, 'status': status})
            else:
                # User spec 2026-06-06: HỢP NHẤT bản tự động với bản thủ công —
                # gán tag 'budget_balance' để vấn đề tự sinh CŨNG hiện đầy đủ
                # section SỬA THÔNG TIN BÁO GIÁ (diện tích/móng/tầng) như bản NV
                # tự tạo. Bỏ qua nếu lead đã có thẻ tag này (tránh phạm unique).
                budget_tag = self.env.ref(
                    'vd_crm_lead.nego_problem_budget_balance',
                    raise_if_not_found=False)
                tag_id = budget_tag.id if budget_tag else False
                if tag_id and rec.vd_lead_problem_ids.filtered(
                        lambda p: p.tag_id.id == tag_id):
                    tag_id = False
                Problem.create({
                    'lead_id': rec.id, 'code': 'cost_diff', 'name': name,
                    'status': status, 'sequence': 10, 'is_default': True,
                    'tag_id': tag_id,
                })

    def _vd_ensure_default_problems(self):
        """Auto-tạo vấn đề mặc định khi lead vào stage Đàm phán."""
        self.ensure_one()
        # ===== 1. CHÊNH LỆCH CHI PHÍ — dùng chung _vd_auto_budget_problem (15%) =====
        self._vd_auto_budget_problem()

        # ===== 2. THỜI GIAN KHỞI CÔNG — round 14: BỎ auto-sinh =====
        # User spec round 14: "thi công gấp" đã có hệ thống tự sinh (badge
        # urgent_construction trong dashboard) → vấn đề "Thời gian khởi công"
        # KHÔNG cần auto-tạo nữa. Bỏ hoàn toàn.
        # (Code cũ vẫn còn các lead legacy đã được tạo — xử lý qua migration
        #  hoặc cron dọn dẹp nếu cần.)

    @api.depends('vd_nego_problem_ids', 'vd_nego_problem_ids.tip_html')
    def _compute_vd_nego_problem_tips_html(self):
        for rec in self:
            if not rec.vd_nego_problem_ids:
                rec.vd_nego_problem_tips_html = ''
                continue
            parts = []
            for p in rec.vd_nego_problem_ids:
                parts.append(
                    '<div style="margin-bottom:0.85rem; padding:0.7rem 0.9rem; '
                    'background:#fffaf0; border-left:4px solid #fd7e14; border-radius:6px;">'
                    '<div style="font-weight:700; color:#c92a2a; margin-bottom:0.3rem;">'
                    '%s %s'
                    '</div>'
                    '%s'
                    '</div>'
                    % (p.icon or '❓', p.name, p.tip_html or '')
                )
            rec.vd_nego_problem_tips_html = ''.join(parts)

    @api.depends(
        'vd_intake_dimensions', 'vd_intake_land_type', 'vd_intake_budget',
        'vd_intake_budget_amount', 'vd_quote_price',
        'vd_intake_house_type',
    )
    def _compute_vd_nego_suggested_problem_ids(self):
        """Suy ra các vấn đề KH có thể đang vướng từ intake data."""
        Problem = self.env['vd.nego.problem'].sudo()
        # Cache problem records by code 1 lần
        all_problems = {p.code: p for p in Problem.search([])}
        for rec in self:
            suggested = Problem.browse()
            # KHÔNG SỔ → no_red_book; CÓ SỔ - phải làm cấp phép → cũng cảnh báo
            if rec.vd_intake_dimensions in ('khong_so_khong_phep', 'co_so_can_phep'):
                p = all_problems.get('no_red_book')
                if p:
                    suggested |= p
            # Budget thấp → low_budget hoặc very_low_budget
            if rec.vd_quote_price and rec.vd_intake_budget_amount:
                ratio = rec.vd_intake_budget_amount / rec.vd_quote_price
                if ratio < 0.7:
                    p = all_problems.get('very_low_budget')
                elif ratio < 0.95:
                    p = all_problems.get('low_budget')
                else:
                    p = None
                if p:
                    suggested |= p
            # Chưa chọn được nhà → no_design (intake chưa điền house_type)
            if not rec.vd_intake_house_type:
                p = all_problems.get('no_design')
                if p:
                    suggested |= p
            rec.vd_nego_suggested_problem_ids = suggested

    # ===== LỊCH HẸN ĐI KÝ HĐ (KH đã đồng ý, đặt lịch) =====
    vd_planned_sign_date = fields.Datetime(
        string='Lịch hẹn ký HĐ', copy=False,
        tracking=True,
        help='Datetime hẹn NV+KH gặp nhau ký HĐ. Set khi KH đồng ý qua wizard.',
    )
    vd_planned_sign_location = fields.Char(
        string='Địa điểm ký', copy=False,
        help='Nhà KH / VP VINADUY / quán cafe...',
    )
    vd_planned_sign_note = fields.Text(string='Ghi chú lịch hẹn ký', copy=False)

    # ===== LỊCH GẶP (user spec 2026-06-12) — card văn bản để NV chụp gửi KH =====
    vd_meet_created = fields.Boolean(string='Đã tạo lịch gặp', copy=False, default=False)
    vd_meet_address = fields.Char(string='Địa chỉ gặp', copy=False)
    vd_meet_maps_link = fields.Char(string='Link Maps lịch gặp', copy=False)
    vd_meet_datetime = fields.Datetime(string='Ngày giờ gặp', copy=False)
    vd_meet_content = fields.Text(string='Nội dung lịch gặp', copy=False)
    vd_planned_sign_countdown = fields.Char(
        string='Đếm ngược ký HĐ',
        compute='_compute_vd_planned_sign_countdown',
        help='Hiển thị "Còn N ngày/giờ" tới lịch hẹn ký.',
    )
    vd_planned_sign_urgency = fields.Selection(
        [('past', 'Quá hạn'), ('today', 'Hôm nay'), ('soon', 'Sắp đến'), ('far', 'Còn xa')],
        compute='_compute_vd_planned_sign_countdown',
        help='Mức độ cảnh báo lịch hẹn: past/today/soon/far.',
    )

    @api.depends('vd_planned_sign_date')
    def _compute_vd_planned_sign_countdown(self):
        from datetime import timedelta as _td
        now = fields.Datetime.now()
        for rec in self:
            if not rec.vd_planned_sign_date:
                rec.vd_planned_sign_countdown = ''
                rec.vd_planned_sign_urgency = False
                continue
            delta = rec.vd_planned_sign_date - now
            secs = delta.total_seconds()
            if secs < -3600:
                rec.vd_planned_sign_countdown = '⚠️ QUÁ HẠN %d giờ' % int(abs(secs) // 3600)
                rec.vd_planned_sign_urgency = 'past'
            elif secs < 0:
                rec.vd_planned_sign_countdown = '⚠️ QUÁ HẠN vài phút'
                rec.vd_planned_sign_urgency = 'past'
            elif secs < 3600:
                rec.vd_planned_sign_countdown = '🔥 CÒN %d phút' % int(secs // 60)
                rec.vd_planned_sign_urgency = 'today'
            elif secs < 86400:
                rec.vd_planned_sign_countdown = '⏰ CÒN %d giờ' % int(secs // 3600)
                rec.vd_planned_sign_urgency = 'today'
            elif secs < 86400 * 3:
                rec.vd_planned_sign_countdown = '📅 Còn %d ngày' % int(secs // 86400)
                rec.vd_planned_sign_urgency = 'soon'
            else:
                rec.vd_planned_sign_countdown = '🗓️ Còn %d ngày' % int(secs // 86400)
                rec.vd_planned_sign_urgency = 'far'

    vd_contract_signed = fields.Boolean(string='Đã ký HĐ', readonly=True, copy=False)
    vd_contract_sign_date = fields.Date(string='Ngày ký HĐ', readonly=True, copy=False)
    vd_contract_deposit = fields.Monetary(
        string='Tiền cọc đã nhận', currency_field='vd_currency_vnd_id',
        readonly=True, copy=False,
    )

    # Hằng số cọc tối thiểu (theo yêu cầu user)
    VD_MIN_DEPOSIT = 50_000_000

    @api.depends('vd_negotiate_deadline')
    def _compute_negotiate_status(self):
        from datetime import date
        today = date.today()
        for rec in self:
            if not rec.vd_negotiate_deadline:
                rec.vd_negotiate_status = False
                continue
            days = (rec.vd_negotiate_deadline - today).days
            if days < 0:
                rec.vd_negotiate_status = 'overdue'
            elif days <= 2:
                rec.vd_negotiate_status = 'warn'
            else:
                rec.vd_negotiate_status = 'ok'

    # ============ COMPUTED — ƯỚC TÍNH + CHÊNH LỆCH + KỊCH BẢN ============
    vd_intake_region = fields.Char(
        string='Vùng', compute='_compute_intake_region', store=False,
    )
    vd_intake_estimate = fields.Float(
        string='Đơn giá ước tính (đ)', digits=(16, 0),
        compute='_compute_intake_estimate', store=False,
    )
    vd_intake_gap = fields.Float(
        string='Chênh lệch (đ)', digits=(16, 0),
        compute='_compute_intake_estimate', store=False,
        help='Estimate − Ngân sách KH. Dương = cần thêm tiền.',
    )
    vd_intake_consult_script = fields.Html(
        string='Kịch bản tư vấn', compute='_compute_intake_estimate', store=False,
    )
    vd_intake_budget_status = fields.Selection([
        ('none', 'Chưa rõ'),
        ('fit', 'Phù hợp'),
        ('warn', 'Chênh nhẹ'),
        ('over', 'Chênh lớn'),
    ], compute='_compute_intake_estimate', store=False,
        help='Trạng thái ngân sách so với ước tính.')

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
        'vd_intake_province_id', 'vd_intake_district',
        'vd_intake_position', 'vd_intake_land_type',
        'vd_intake_dimensions', 'vd_intake_area_m2', 'vd_intake_house_type',
        'vd_intake_house_type_other',
        'vd_intake_floors_num', 'vd_intake_function', 'vd_intake_function_notes',
        'vd_intake_timeline', 'vd_intake_budget', 'vd_intake_budget_amount',
        'vd_intake_length_m', 'vd_intake_width_m',
        'vd_intake_foundation_type', 'vd_intake_roof_type',
    )

    @api.depends(*_intake_data_fields)
    def _compute_has_intake_data(self):
        for rec in self:
            rec.vd_has_intake_data = any(rec[f] for f in self._intake_data_fields)

    # ========== PRICING / ESTIMATE LOGIC ==========
    # Bản đồ tỉnh → vùng (Bắc/Trung/Nam) theo địa lý hành chính VN.
    _BAC_PROVINCES = frozenset({
        'Hà Nội', 'Hải Phòng', 'Bắc Ninh', 'Hà Nam', 'Hải Dương', 'Hưng Yên',
        'Nam Định', 'Ninh Bình', 'Thái Bình', 'Vĩnh Phúc',
        'Hà Giang', 'Cao Bằng', 'Bắc Kạn', 'Tuyên Quang', 'Lào Cai', 'Điện Biên',
        'Lai Châu', 'Sơn La', 'Yên Bái', 'Hòa Bình', 'Thái Nguyên', 'Lạng Sơn',
        'Quảng Ninh', 'Bắc Giang', 'Phú Thọ',
    })
    _TRUNG_PROVINCES = frozenset({
        'Thanh Hóa', 'Nghệ An', 'Hà Tĩnh', 'Quảng Bình', 'Quảng Trị', 'Thừa Thiên Huế',
        'Huế',   # tên mới sau sáp nhập 01/07/2025 (trước là Thừa Thiên Huế)
        'Đà Nẵng', 'Quảng Nam', 'Quảng Ngãi', 'Bình Định', 'Phú Yên', 'Khánh Hòa',
        'Ninh Thuận', 'Bình Thuận',
        'Kon Tum', 'Gia Lai', 'Đắk Lắk', 'Đắk Nông', 'Lâm Đồng',
    })
    # Mọi tỉnh khác (Đông Nam Bộ + Tây Nam Bộ) coi là Nam.
    # Phụ phí +300k/m² cho vùng cao (toàn tỉnh):
    _SURCHARGE_PROVINCES = frozenset({
        'Lai Châu', 'Sơn La', 'Điện Biên', 'Cao Bằng', 'Bắc Kạn',
    })
    # Phụ phí +300k/m² cho HUYỆN của tỉnh (TP/thị xã của tỉnh đó miễn phụ phí):
    _SURCHARGE_DISTRICT_PROVINCES = frozenset({'Hà Giang', 'Lạng Sơn'})

    @api.model
    def _vd_norm_province(self, name):
        """Chuẩn hoá tên tỉnh để map vùng — bỏ hậu tố sau sáp nhập 01/07/2025
        ('... (cũ - đã sáp nhập)') để tỉnh cũ vẫn khớp tên gốc."""
        if not name:
            return name
        for sfx in (' (cũ - đã sáp nhập)', ' (cũ)', '(cũ - đã sáp nhập)'):
            if name.endswith(sfx):
                name = name[:-len(sfx)]
        return name.strip()

    @api.depends('vd_intake_province_id')
    def _compute_intake_region(self):
        for rec in self:
            province = self._vd_norm_province(
                rec.vd_intake_province_id.name) if rec.vd_intake_province_id else None
            if province in self._BAC_PROVINCES:
                rec.vd_intake_region = 'bac'
            elif province in self._TRUNG_PROVINCES:
                rec.vd_intake_region = 'trung'
            elif province:
                rec.vd_intake_region = 'nam'
            else:
                rec.vd_intake_region = False

    def _get_san_unit_price(self, pricing, area_per_floor, has_car):
        """Đơn giá sàn (đ/m²) tùy DT 1 sàn & ô tô vào được không.

        LƯU Ý: bậc giá tính theo DIỆN TÍCH 1 SÀN (footprint = Tầng 1),
        KHÔNG phải tổng diện tích sàn. Nhà to nhiều tầng nhưng mặt sàn nhỏ
        vẫn phải dùng đơn giá cao. Dùng _vd_san_unit_for() để khỏi truyền nhầm.
        """
        suffix = 'oto' if has_car else 'kxe'
        if area_per_floor >= 75:
            return getattr(pricing, f'san_75_{suffix}')
        if area_per_floor >= 65:
            return getattr(pricing, f'san_65_{suffix}')
        if area_per_floor >= 50:
            return getattr(pricing, f'san_50_{suffix}')
        if area_per_floor >= 40:
            return getattr(pricing, f'san_40_{suffix}')
        return getattr(pricing, f'san_lt40_{suffix}')

    def _vd_san_unit_for(self, pricing):
        """Đơn giá sàn cho lead này — bậc giá theo DT 1 SÀN (Tầng 1 footprint).
        Fix 2026-06-12: trước đây mọi call site truyền TỔNG diện tích sàn →
        nhà tổng ≥75m² luôn rơi bậc rẻ nhất (6.4tr) dù mặt sàn chỉ 40-65m²."""
        if not pricing:
            return 0.0
        found_area, _ = self._vd_get_found_roof_areas()
        return self._get_san_unit_price(pricing, found_area, self.vd_intake_car_access)

    def _get_foundation_pct(self, pricing, ftype, is_lon):
        if ftype == 'don':
            return pricing.mong_don_lon if is_lon else pricing.mong_don_nho
        if ftype == 'bang':
            return pricing.mong_bang_lon if is_lon else pricing.mong_bang_nho
        if ftype == 'coc':
            return pricing.mong_coc_lon if is_lon else pricing.mong_coc_nho
        return 0.0

    def _vd_resolve_roof_type(self):
        """Trả về effective roof_type. Ưu tiên vd_intake_roof_type (NV chọn explicit).
        Fallback derive từ vd_intake_house_type (Kiểu nhà) — UI chỉ cho chọn Mẫu nhà:
        - Nhà mái bằng → mai_bang (20%)
        - Nhà mái thái → mai_thai_cdt (55%)   (fix 2026-06-12: trước là kdt 45%)
        - Nhà mái nhật → mai_nhat_cdt (48%)   (fix 2026-06-12: trước là kdt 42%)
        - Nhà mái tôn  → mai_ton (13%)        (mới 2026-06-12)
        """
        if self.vd_intake_roof_type:
            return self.vd_intake_roof_type
        return {
            'mai_bang': 'mai_bang',
            'mai_thai': 'mai_thai_cdt',
            'mai_nhat': 'mai_nhat_cdt',
            'mai_ton': 'mai_ton',
        }.get(self.vd_intake_house_type, False)

    def _vd_get_found_roof_areas(self):
        """Trả về (found_area, roof_area) cho công thức báo giá:
        - Móng: diện tích Tầng 1 (sàn dưới cùng đỡ móng)
        - Mái : diện tích tầng trên cùng (Tum nếu có, không thì tầng N cao nhất
                có diện tích > 0)
        Fallback nếu chưa nhập per-floor: dùng total_m2 / floors (bình quân)."""
        self.ensure_one()
        floor_1 = self.vd_intake_floor_1_m2 or 0.0

        # Top floor — ưu tiên Tum, không thì floor cao nhất có area > 0
        top = 0.0
        if self.vd_intake_has_tum and self.vd_intake_floor_tum_m2:
            top = self.vd_intake_floor_tum_m2
        else:
            n_select = int(self.vd_intake_floors_select) if self.vd_intake_floors_select else 0
            for i in range(n_select, 0, -1):
                fa = self['vd_intake_floor_%s_m2' % i] or 0.0
                if fa > 0:
                    top = fa
                    break

        # Fallback bình quân nếu user chưa nhập per-floor
        total = self.vd_intake_total_m2 or 0.0
        floors = self.vd_intake_floors_num or 1.0
        avg = (total / floors) if floors > 0 else 0.0
        if floor_1 <= 0:
            floor_1 = avg
        if top <= 0:
            top = avg
        return floor_1, top

    def _get_roof_pct(self, pricing, rtype):
        return {
            'mai_bang': pricing.mai_bang,
            'mai_nhat_kdt': pricing.mai_nhat_kdt,
            'mai_nhat_cdt': pricing.mai_nhat_cdt,
            'mai_thai_kdt': pricing.mai_thai_kdt,
            'mai_thai_cdt': pricing.mai_thai_cdt,
            'thong_tang': pricing.thong_tang,
            'mai_trang_tri': pricing.mai_trang_tri,
            'mai_trang_tri_dt': pricing.mai_trang_tri_dt,
            'mai_ton': pricing.mai_ton,
            'mai_ton_1m': pricing.mai_ton_1m,
            'mai_ton_2m': pricing.mai_ton_2m,
            'mai_ton_3m': pricing.mai_ton_3m,
        }.get(rtype, 0.0)

    def _budget_to_amount(self):
        """Map vd_intake_budget Selection → số tiền giữa khoảng (đ).
        Ưu tiên vd_intake_budget_amount nếu có."""
        if self.vd_intake_budget_amount:
            return self.vd_intake_budget_amount
        return {
            'duoi_1ty': 800_000_000,
            '1-3ty': 2_000_000_000,
            '3-5ty': 4_000_000_000,
            '5-10ty': 7_500_000_000,
            '10-20ty': 15_000_000_000,
            'tren_20ty': 25_000_000_000,
        }.get(self.vd_intake_budget, 0.0)

    @api.depends(
        'vd_intake_province_id', 'vd_intake_district',
        'vd_intake_total_m2', 'vd_intake_floors_num',
        'vd_intake_floors_select', 'vd_intake_has_tum',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2',
        'vd_intake_foundation_type', 'vd_intake_roof_type',
        'vd_intake_car_access', 'vd_intake_budget', 'vd_intake_budget_amount',
    )
    def _compute_intake_estimate(self):
        """Luôn dùng công thức CHI TIẾT (móng + sàn + mái) — không còn binary
        'xây thô / trọn gói'. Sản phẩm duy nhất = "Xây nhà trọn gói chưa nội thất"."""
        Pricing = self.env['vd.pricing.region']
        for rec in self:
            rec.vd_intake_estimate = 0.0
            rec.vd_intake_gap = 0.0
            rec.vd_intake_consult_script = ''
            rec.vd_intake_budget_status = 'none'

            floors = rec.vd_intake_floors_num or 1.0
            # Công thức (2026-05-21 final): TẤT CẢ rows dùng TỔNG DIỆN TÍCH SÀN
            # (vd_intake_total_m2 = sum per-tầng). KHÔNG dùng diện tích đất.
            sum_floor_areas = 0.0
            n_floors_select = int(rec.vd_intake_floors_select) if rec.vd_intake_floors_select else 0
            for i in range(1, n_floors_select + 1):
                sum_floor_areas += rec['vd_intake_floor_%s_m2' % i] or 0.0
            if rec.vd_intake_has_tum and rec.vd_intake_floor_tum_m2:
                sum_floor_areas += rec.vd_intake_floor_tum_m2
            total_floor_area = sum_floor_areas or rec.vd_intake_total_m2 or 0.0

            if total_floor_area <= 0 or not rec.vd_intake_region:
                continue

            pricing = Pricing.search([('code', '=', rec.vd_intake_region)], limit=1)
            if not pricing:
                continue

            # ===== Tính chi tiết: Móng + Sàn + Mái =====
            # MÓNG: dùng diện tích Tầng 1 (sàn dưới cùng đỡ móng)
            # MÁI : dùng diện tích tầng trên cùng (Tum hoặc tầng N cao nhất)
            # SÀN : dùng TỔNG diện tích các tầng (giữ nguyên)
            found_area, roof_area = rec._vd_get_found_roof_areas()
            san_unit = rec._vd_san_unit_for(pricing)  # bậc giá theo DT 1 sàn (fix 2026-06-12)
            # Threshold % móng theo DT MÓNG (Tầng 1) — fix 2026-05-28
            found_pct = rec._get_foundation_pct(
                pricing, rec.vd_intake_foundation_type, found_area >= 70,
            ) / 100.0
            found_cost = found_area * found_pct * san_unit
            floor_cost = total_floor_area * san_unit
            roof_pct = rec._get_roof_pct(pricing, rec._vd_resolve_roof_type()) / 100.0
            roof_cost = roof_area * roof_pct * san_unit

            total = found_cost + floor_cost + roof_cost
            # Phụ phí móng đơn 10% / móng băng-cọc 15% đã BỎ (2026-05-21 spec).

            # Phụ phí tỉnh vùng cao (+300k/m² × total_floor_area)
            province_name = self._vd_norm_province(
                rec.vd_intake_province_id.name) if rec.vd_intake_province_id else None
            if province_name in self._SURCHARGE_PROVINCES:
                total += 300_000 * total_floor_area
            elif province_name in self._SURCHARGE_DISTRICT_PROVINCES:
                # Apply nếu huyện được chọn (loại trừ TP của tỉnh đó)
                district_name = rec.vd_intake_district.name if rec.vd_intake_district else ''
                if district_name and not district_name.startswith(province_name):
                    total += 300_000 * total_floor_area

            rec.vd_intake_estimate = total

            # ===== Tính chênh lệch & kịch bản =====
            kh_budget = rec._budget_to_amount()
            if kh_budget <= 0:
                rec.vd_intake_consult_script = (
                    '<i>Chưa có ngân sách KH để so sánh.</i>'
                )
                continue
            gap = total - kh_budget
            rec.vd_intake_gap = gap

            est_str = f"{total:,.0f}đ".replace(',', '.')
            kh_str = f"{kh_budget:,.0f}đ".replace(',', '.')
            gap_abs = abs(gap)
            gap_str = f"{gap_abs:,.0f}đ".replace(',', '.')

            if gap <= 100_000_000:
                rec.vd_intake_budget_status = 'fit'
                rec.vd_intake_consult_script = (
                    f'<b style="color:#2b8a3e;">✅ NGÂN SÁCH PHÙ HỢP</b><br/>'
                    f'Ước tính sơ bộ <b>{est_str}</b> ≈ ngân sách <b>{kh_str}</b> '
                    f'(chênh dưới 100tr).<br/>'
                    f'<u>Bước tiếp theo:</u><br/>'
                    f'• Hoàn tất khai thác → chuyển sang <b>Báo giá</b><br/>'
                    f'• Lập file báo giá chi tiết, gửi KH qua <b>Zalo/Email</b> '
                    f'trong 1-2 ngày<br/>'
                    f'<u>💬 Nói với KH:</u><br/>'
                    f'<i>"Dạ ngân sách anh/chị rất phù hợp với quy mô công '
                    f'trình ạ. Em xin phép <b>chuẩn bị báo giá chi tiết</b> '
                    f'(từng hạng mục: móng, sàn, mái, nhân công...) và <b>gửi '
                    f'qua Zalo trong 1-2 ngày tới</b> để anh/chị xem trước. '
                    f'Nếu anh/chị thấy ổn, mình hẹn ngày bên em xuống <b>ký '
                    f'HĐ + nhận cọc</b> để bắt đầu công trình ạ."</i>'
                )
            elif gap < 300_000_000:
                rec.vd_intake_budget_status = 'warn'
                rec.vd_intake_consult_script = (
                    f'<b style="color:#1864ab;">⚖️ CHÊNH NHẸ {gap_str}</b> (dưới 300tr)<br/>'
                    f'Ước tính <b>{est_str}</b> vượt ngân sách <b>{kh_str}</b>.<br/>'
                    f'<u>3 hướng tối ưu chi phí (giữ chất lượng):</u><br/>'
                    f'• Đổi sang <b>móng đơn giản hơn</b> (đơn/băng thay vì cọc) — '
                    f'tiết kiệm ~50-100tr nếu nền đất tốt<br/>'
                    f'• Chọn <b>mái bằng / mái tôn</b> thay mái thái đổ trần — '
                    f'tiết kiệm ~80-150tr<br/>'
                    f'• Gộp/tối ưu công năng (ví dụ phòng thờ kết hợp đa năng) — '
                    f'tiết kiệm ~50-80tr/phòng<br/>'
                    f'<u>💬 Nói với KH:</u><br/>'
                    f'<i>"Dạ ước tính sơ bộ đang chênh khoảng <b>{gap_str}</b> '
                    f'so với ngân sách của anh/chị. Em hoàn toàn có thể tối ưu '
                    f'để <b>vừa khít ngân sách + giữ chất lượng</b>. Em xin phép '
                    f'<b>chuẩn bị 2 phương án báo giá</b>: <b>(A)</b> giữ thiết '
                    f'kế đầy đủ + bổ sung thêm ~{gap_str}, hoặc <b>(B)</b> tối '
                    f'ưu một vài hạng mục để vừa ngân sách. Em <b>gửi qua Zalo</b> '
                    f'trong 1-2 ngày, anh/chị xem rồi mình trao đổi nhé ạ."</i>'
                )
            else:
                rec.vd_intake_budget_status = 'over'
                rec.vd_intake_consult_script = (
                    f'<b style="color:#c92a2a;">⚠️ CHÊNH LỚN {gap_str}</b> (≥ 300tr)<br/>'
                    f'Ước tính <b>{est_str}</b> vượt ngân sách <b>{kh_str}</b>.<br/>'
                    f'<u>3 phương án để KH cân nhắc:</u><br/>'
                    f'<b>1️⃣ Tăng ngân sách (vay/xoay vốn)</b> — KH chủ động: vay '
                    f'NH lãi xây nhà ~8-10%/năm, hoặc xoay vốn người thân.<br/>'
                    f'<b>2️⃣ Chia 2 giai đoạn</b> — bên mình xây thô trước '
                    f'(~60-70% tổng), KH hoàn thiện sau khi có thêm vốn (giảm '
                    f'áp lực tài chính ~30-40%).<br/>'
                    f'<b>3️⃣ Tối ưu thiết kế</b> — bên mình giảm tầng / đổi loại '
                    f'mái / móng đơn giản để vừa ngân sách (chất lượng có thể '
                    f'giảm nhẹ).<br/>'
                    f'<u>💬 Nói với KH:</u><br/>'
                    f'<i>"Dạ em hiểu lo lắng của anh/chị về ngân sách. Với quy '
                    f'mô anh/chị mong muốn, ước tính sơ bộ đang vượt khoảng '
                    f'<b>{gap_str}</b>. Em đề xuất <b>3 hướng</b> để anh/chị '
                    f'cân nhắc: <b>(1)</b> nếu anh/chị có thể tăng ngân sách '
                    f'(vay NH ~8-10%/năm hoặc xoay vốn người thân) thì giữ '
                    f'nguyên thiết kế đầy đủ, <b>(2)</b> bên em <b>chia 2 giai '
                    f'đoạn</b> — xây thô trước hoàn thiện sau, <b>(3)</b> bên em '
                    f'tối ưu lại thiết kế (giảm tầng/đổi mái) để vừa ngân sách. '
                    f'Anh/chị xem hướng nào phù hợp, em sẽ <b>chuẩn bị báo giá '
                    f'gửi qua Zalo</b> theo hướng đó ạ."</i>'
                )

    @api.depends('call_ids', 'call_ids.state', 'call_ids.end_time')
    def _compute_last_call_end_msg(self):
        """Trả message Vietnamese cho call kết thúc gần nhất (< 5 phút).
        Hết 5 phút thì ẩn để banner không kẹt mãi."""
        TERMINAL = ('ended', 'no_answer', 'busy', 'declined', 'cancelled', 'failed')
        MSG = {
            'ended':     '✅ Cuộc gọi đã kết thúc',
            'no_answer': '⏰ Khách hàng không bắt máy',
            'busy':      '📵 Máy bận',
            'declined':  '🚫 Khách hàng từ chối',
            'cancelled': '⊘ Cuộc gọi bị huỷ',
            'failed':    '⚠️ Cuộc gọi thất bại',
        }
        cutoff = fields.Datetime.now() - timedelta(minutes=5)
        for rec in self:
            recent = rec.call_ids.filtered(
                lambda c: c.state in TERMINAL and c.end_time and c.end_time > cutoff
            ).sorted('end_time', reverse=True)
            rec.vd_last_call_end_msg = MSG.get(recent[0].state, '') if recent else False

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

    @staticmethod
    def _vd_normalize_kh_name(value):
        """User spec 2026-05-28: title-case tên KH per-word với logic:
        - Word có chữ thường → .capitalize() (vd "anh"→"Anh", "đặng"→"Đặng")
        - Word ALL UPPER + có dấu Tiếng Việt (Đ,Ơ,Ư...) → .capitalize() (vd "ĐOÀN"→"Đoàn")
        - Word ALL UPPER ASCII len≥2 → keep (vd "VINADUY", "TNI", "HN", "TP.HCM")
        - Word 1 letter (vd "T" trong "T5/26") → capitalize
        Skip prefix "(Fanpage)" / "(Tiktok)" / "(Pancake)".
        """
        if not value or not isinstance(value, str):
            return value
        s = value.strip()
        if not s:
            return s
        if s.startswith('(Fanpage)') or s.startswith('(Tiktok)') or s.startswith('(Pancake)'):
            return s

        def _capitalize_first(s):
            """Title-case: upper first alpha char, lower rest. Robust với
            Vietnamese chars (.capitalize() built-in có thể không lower rest đúng)."""
            result = []
            found_first = False
            for c in s:
                if c.isalpha():
                    if not found_first:
                        result.append(c.upper())
                        found_first = True
                    else:
                        result.append(c.lower())
                else:
                    result.append(c)
            return ''.join(result)

        def _norm_word(w):
            if not w:
                return w
            alpha = [c for c in w if c.isalpha()]
            if not alpha:
                return w  # all digits/punctuation
            alpha_str = ''.join(alpha)
            is_ascii = all(ord(c) < 128 for c in alpha)
            is_all_upper = all(c.isupper() for c in alpha)
            if is_all_upper and is_ascii and len(alpha) >= 2:
                # ASCII all-upper team code/brand → keep
                return w  # "VINADUY", "TNI", "HN", "TP.HCM"
            # Else: title case (upper first, lower rest)
            return _capitalize_first(w)

        out_parts = []
        for part in s.split(' - '):
            p = part.strip()
            if not p:
                out_parts.append(p)
                continue
            out_parts.append(' '.join(_norm_word(w) for w in p.split()))
        return ' - '.join(out_parts)

    def _vd_normalize_kh_names_in_vals(self, vals):
        """Apply normalize cho 3 field tên KH trong vals dict."""
        for f in ('name', 'partner_name', 'contact_name'):
            if f in vals and isinstance(vals[f], str):
                vals[f] = self._vd_normalize_kh_name(vals[f])

    @staticmethod
    def _vd_phone_to_local(num):
        """Chuẩn hoá SĐT KH về ĐẦU SỐ 0 (nội địa VN) — bỏ hết mã nước 84.
        '+84xxxxxxxxx' / '84xxxxxxxxx' / '0084..' / '8484..' (nhân đôi) → '0xxxxxxxxx'.
        Số đã '0...' giữ nguyên. KHÔNG dùng cho số tổng đài (hotline cần 84).

        Guard len>9 để KHÔNG cắt nhầm số Vinaphone national bắt đầu '84x'
        (vd '0848446886' giữ nguyên; '84848446886' → '0848446886')."""
        if not num or not isinstance(num, str):
            return num
        import re
        digits = re.sub(r'\D', '', num)
        if not digits:
            return num  # không có chữ số → giữ nguyên (có thể là text)
        if digits.startswith('00'):
            digits = digits[2:]
        # bỏ các tiền tố '84' lặp ở đầu, dừng khi còn ~9 số national
        while digits.startswith('84') and len(digits) > 9:
            digits = digits[2:]
        if digits.startswith('0'):
            return digits
        return '0' + digits

    def _vd_normalize_phones_in_vals(self, vals):
        """Đưa phone/mobile trong vals về đầu số 0 (nhập 84 → tự về 0)."""
        for f in ('phone', 'mobile'):
            if f in vals and isinstance(vals[f], str) and vals[f].strip():
                vals[f] = self._vd_phone_to_local(vals[f])

    @api.model
    def vd_fix_phones_to_local(self):
        """LỆNH: ép TOÀN BỘ KH còn SĐT đầu 84 → về đầu số 0. Chạy 1 lần / khi cần.
        Trả số KH đã sửa. Gọi qua Server Action 'Chuẩn hoá SĐT về đầu số 0'."""
        leads = self.with_context(active_test=False).search(
            ['|', ('phone', 'like', '84'), ('mobile', 'like', '84')])
        fixed = 0
        for lead in leads:
            vals = {}
            for f in ('phone', 'mobile'):
                cur = lead[f]
                if cur:
                    new = self._vd_phone_to_local(cur)
                    if new != cur:
                        vals[f] = new
            if vals:
                lead.with_context(mail_notrack=True, tracking_disable=True).write(vals)
                fixed += 1
        return fixed

    @api.model_create_multi
    def create(self, vals_list):
        """Override create — auto round-robin nếu NV được assign đã block
        (quá hạn chăm sóc > 3 KH). Pancake / Zalo / Manual đều áp.
        Plus normalize tên KH viết HOA TOÀN BỘ → Title Case."""
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for vals in vals_list:
            self._vd_normalize_kh_names_in_vals(vals)
            self._vd_normalize_phones_in_vals(vals)   # SĐT → đầu số 0
        Users = self.env['res.users']
        used_users = []  # tránh phân tất cả vào 1 NV trong cùng batch
        for vals in vals_list:
            # Skip nếu là internal action (bypass via context)
            if self.env.context.get('vd_skip_assignment_balance'):
                continue
            assigned_uid = vals.get('user_id')
            should_reroute = False
            # User spec 2026-05-30: NV TỰ THÊM khách cho CHÍNH MÌNH thì LUÔN giữ —
            # không reroute dù đang quá hạn (>threshold). Chặn quá-hạn chỉ áp cho
            # lead TỰ ĐỘNG (Pancake đã tự pick eligible NV trước khi create nên
            # không vướng nhánh này). assigned_uid == uid = self-add qua form/kanban.
            if assigned_uid and assigned_uid == self.env.uid:
                continue
            if assigned_uid:
                # Có NV được chỉ định → check họ có bị block không
                u = Users.sudo().browse(assigned_uid)
                if u.exists() and not u.vd_can_receive_new_leads:
                    should_reroute = True
            elif vals.get('team_id') or self.env.context.get('default_team_id'):
                # Không có user_id nhưng có team → auto pick eligible NV trong team
                should_reroute = True
            if should_reroute:
                team_id = vals.get('team_id') or self.env.context.get('default_team_id')
                next_user = Users._vd_pick_next_assignee(
                    exclude_user_ids=used_users,
                    preferred_team_id=team_id,
                )
                if next_user:
                    vals['user_id'] = next_user.id
                    used_users.append(next_user.id)
                    _logger.info(
                        "VD CRM round-robin: rerouted lead to user %s (was %s, original blocked)",
                        next_user.name, assigned_uid,
                    )
        # Auto-set callback_date = today + 2 ngày cho lead mới (nếu chưa set)
        from datetime import timedelta
        default_callback = fields.Datetime.now() + timedelta(days=2)
        for vals in vals_list:
            if not vals.get('callback_date'):
                vals['callback_date'] = default_callback
            # Chuẩn hoá tên KH MỚI: strip pattern 'VINADUY - X - <code>' nếu
            # user/wizard lỡ nhập sẵn. Pattern này CHỈ được auto-apply sau khi
            # báo giá (qua _vd_apply_quote_name_pattern).
            if vals.get('name'):
                vals['name'] = self._vd_clean_input_name(vals['name']) or vals['name']
            if vals.get('contact_name'):
                vals['contact_name'] = self._vd_clean_input_name(vals['contact_name']) or vals['contact_name']
            if vals.get('partner_name'):
                vals['partner_name'] = self._vd_clean_input_name(vals['partner_name']) or vals['partner_name']
            # Tầm tài chính: range → amount auto
            self._sync_budget_range_to_amount(vals)
        return super().create(vals_list)

    # Các field intake bị khoá sau khi NV bấm "Lưu & Chuyển sang Báo giá".
    # NV không write được nữa; admin/leader bypass bằng action_unlock_intake.
    _INTAKE_LOCKED_FIELDS = frozenset({
        'vd_intake_province_id', 'vd_intake_district',
        'vd_intake_position', 'vd_intake_land_type', 'vd_intake_dimensions',
        'vd_intake_area_m2', 'vd_intake_length_m', 'vd_intake_width_m',
        'vd_intake_house_length_m', 'vd_intake_house_width_m', 'vd_intake_total_m2',
        'vd_intake_house_type', 'vd_intake_house_type_other',
        'vd_intake_foundation_type', 'vd_intake_roof_type',
        'vd_intake_floors_select', 'vd_intake_floors_num', 'vd_intake_has_tum',
        'vd_intake_floor_1_m2', 'vd_intake_floor_2_m2', 'vd_intake_floor_3_m2',
        'vd_intake_floor_4_m2', 'vd_intake_floor_5_m2', 'vd_intake_floor_6_m2',
        'vd_intake_floor_7_m2', 'vd_intake_floor_tum_m2',
        'vd_intake_function', 'vd_intake_function_notes',
        'vd_intake_floor_1_function_ids', 'vd_intake_floor_2_function_ids',
        'vd_intake_floor_3_function_ids', 'vd_intake_floor_4_function_ids',
        'vd_intake_floor_5_function_ids', 'vd_intake_floor_6_function_ids',
        'vd_intake_floor_7_function_ids', 'vd_intake_floor_tum_function_ids',
        'vd_intake_timeline', 'vd_intake_budget', 'vd_intake_budget_amount',
        'vd_intake_budget_range',
        'vd_intake_car_access', 'vd_intake_car_access_select',
        'vd_intake_soil_dump',
    })

    def write(self, vals):
        # ============ Tầm tài chính: range → amount auto ============
        self._sync_budget_range_to_amount(vals)
        # ============ Normalize tên KH viết HOA → Title Case ============
        self._vd_normalize_kh_names_in_vals(vals)
        # ============ SĐT KH → đầu số 0 (nhập 84 → tự về 0) ============
        self._vd_normalize_phones_in_vals(vals)

        # ============ Chặn NV/Leader sửa intake khi đã khoá — chỉ admin bypass ============
        # ALSO bypass khi write đến từ section 'Cân đối ngân sách' trong popup
        # vấn đề (context vd_skip_intake_lock=True từ vd.lead.problem.write).
        locked_keys = self._INTAKE_LOCKED_FIELDS & vals.keys()
        if locked_keys and not self.env.context.get('vd_skip_intake_lock'):
            current_user = self.env.user
            is_admin = (
                current_user._is_superuser()
                or current_user.has_group('vd_crm_lead.vd_crm_group_admin')
            )
            if not is_admin:
                for rec in self:
                    if rec.vd_intake_locked:
                        raise UserError(_(
                            'Thông tin tư vấn đã được chốt. Liên hệ Admin '
                            'để mở khoá nếu cần chỉnh sửa, hoặc tạo vấn đề '
                            '"Cân đối ngân sách" mới để sửa qua popup vấn đề.'
                        ))

        # ============ Phân quyền: chặn user không được phép chuyển KH ============
        # Nếu vals['user_id'] khác user_id hiện tại → user đang cố CHUYỂN KH cho
        # NV khác. Chỉ user thuộc group có can_reassign_lead=True mới được làm.
        if 'user_id' in vals:
            new_uid = vals.get('user_id')
            current_user = self.env.user
            # Skip check khi superuser hoặc context bypass (vd auto-assign)
            if not (current_user._is_superuser() or self.env.context.get('vd_skip_reassign_check')):
                role_model = self.env['vd.crm.role.config'].sudo()
                can_reassign = role_model.can_user_reassign(current_user)
                if not can_reassign:
                    for rec in self:
                        if rec.user_id.id != new_uid:
                            from odoo.exceptions import AccessError
                            raise AccessError(_(
                                'Bạn không có quyền chuyển KH "%s" cho NV khác. '
                                'Liên hệ Trưởng nhóm hoặc Admin.'
                            ) % (rec.name or rec.partner_name or 'KH'))

        # MỌI thay đổi stage_id (kể cả qua badge widget / auto-save / external API)
        # đều cần disable auto-tracking — server chưa config email sender, sẽ
        # raise "Invalid Operation: Unable to send message, please configure
        # the sender's email address" nếu để Odoo CRM tự gửi email tracking.
        if 'stage_id' in vals:
            self = self.with_context(mail_notrack=True, tracking_disable=True)
            # Snapshot stage_code TRƯỚC super() để detect transition vào 'quote'
            old_codes = {rec.id: rec.stage_code for rec in self}

            # ===== GATE: chặn chuyển stage sang Báo giá/Đàm phán nếu chưa CHỐT =====
            # User spec 2026-05-27: NV phải bấm "🔒 CHỐT THÔNG TIN" trước. Drag
            # kanban từ "Khách mới" sang "Báo giá" sẽ raise UserError.
            # Bypass: context vd_skip_intake_lock=True (vd action_save_intake_done
            # tự set locked=True trong cùng write_vals → check pass).
            if not self.env.context.get('vd_skip_intake_lock'):
                new_stage_rec = self.env['crm.stage'].browse(vals['stage_id']) \
                    if vals.get('stage_id') else self.env['crm.stage']
                if new_stage_rec and new_stage_rec.code in ('quote', 'negotiate'):
                    will_lock = vals.get('vd_intake_locked', None)
                    for rec in self:
                        locked_after = (
                            will_lock if will_lock is not None else rec.vd_intake_locked
                        )
                        if not locked_after:
                            raise UserError(_(
                                'KH "%s" chưa CHỐT THÔNG TIN. Vui lòng bấm '
                                '🔒 CHỐT THÔNG TIN trước khi chuyển sang giai '
                                'đoạn "%s".'
                            ) % (
                                rec.name or rec.partner_name or 'lead',
                                new_stage_rec.name,
                            ))
        result = super().write(vals)
        if 'stage_id' in vals:
            from datetime import timedelta
            now = fields.Datetime.now()
            default_callback = now + timedelta(days=2)
            for rec in self:
                if rec.stage_is_lost and rec.active:
                    rec.with_context(skip_lost_archive=True).active = False
                # Auto-set callback_date = today + 2 ngày khi chuyển stage active
                # (new/lead/quote/negotiate). KHÔNG set cho won/lost (đã đóng).
                # Override callback cũ nếu chưa có hoặc đã quá hạn.
                if rec.stage_code in ('new', 'lead', 'quote', 'negotiate'):
                    if not rec.callback_date or rec.callback_date < now:
                        rec.with_context(
                            skip_callback_auto=True, mail_notrack=True,
                        ).callback_date = default_callback
                # ===== AUTO-RENAME khi chuyển sang "Khách báo giá" =====
                # Format: "VINADUY - <Tên KH> <TỈNH> - MM/YY"
                # Vd: "VINADUY - Lê Văn Duẩn TH - 12/26"
                # Chỉ rename khi TRANSITION (old != quote) → tránh rename lặp.
                if (rec.stage_code == 'quote'
                        and old_codes.get(rec.id) != 'quote'
                        and not (rec.name or '').startswith('VINADUY -')):
                    new_name = rec._vd_build_quote_name()
                    if new_name:
                        rec.with_context(mail_notrack=True).name = new_name
                # ===== AUTO-tạo 2 vấn đề mặc định khi vào Đàm phán =====
                # CHỈ tạo nếu intake_complete=True (đã đủ thông tin + có báo giá).
                # KH chưa đủ thông tin coi như khách mới → không sinh vấn đề.
                if (rec.stage_code == 'negotiate'
                        and old_codes.get(rec.id) != 'negotiate'
                        and rec.vd_intake_complete):
                    rec._vd_ensure_default_problems()
        # ===== KHÔNG auto-lock theo intake_complete nữa =====
        # User spec (2026-05): NV phải bấm nút "🔒 CHỐT THÔNG TIN" (action_save_intake_done)
        # mới khoá + chuyển stage 'quote'. Tránh khoá ngoài ý muốn khi NV
        # vô tình điền đủ 11 trường nhưng chưa muốn chốt.
        # Data persist mãi mãi — KHÔNG wipe. NV chưa CHỐT thì KH vẫn ở
        # bảng "Khách mới"; chỉ khi CHỐT mới chuyển sang Báo giá + tạo vấn đề.

        # Tự sinh/cập nhật "Cân đối ngân sách" khi NS KH hoặc giá báo thay đổi
        # (chỉ KH đã ở giai đoạn báo giá/đàm phán/chốt).
        if {'vd_intake_budget_amount', 'vd_intake_budget_range', 'vd_quote_price'} & set(vals.keys()):
            self.filtered(
                lambda r: r.stage_code in ('quote', 'negotiate', 'won')
            )._vd_auto_budget_problem()
        return result

    # ============================================================
    # AUTO-RENAME KHI CHUYỂN SANG "KHÁCH BÁO GIÁ"
    # ============================================================
    _VD_PROVINCE_SKIP_WORDS = {'tỉnh', 'thành', 'phố', 'tp', 'tp.'}

    @api.model
    def _vd_province_code(self, province_name):
        """Sinh code viết tắt từ tên tỉnh/thành.
        Vd: 'Thanh Hóa' → 'TH', 'Hà Nội' → 'HN',
            'Thành phố Hồ Chí Minh' → 'HCM', 'Bà Rịa - Vũng Tàu' → 'BRVT'.
        Quy tắc: bỏ tiền tố 'Tỉnh/Thành phố/TP', lấy chữ cái đầu mỗi từ còn lại.
        """
        if not province_name:
            return ''
        import re
        words = re.findall(r'\w+', province_name, re.UNICODE)
        letters = []
        for w in words:
            if w.lower().rstrip('.') in self._VD_PROVINCE_SKIP_WORDS:
                continue
            if w:
                letters.append(w[0].upper())
        return ''.join(letters)

    def _vd_extract_customer_name(self):
        """Tên KH thực để build tên báo giá.
        Ưu tiên partner_name → contact_name → strip prefix '(Fanpage)/(Tiktok)/...'
        khỏi name → cuối cùng dùng name nguyên."""
        self.ensure_one()
        # Priority 1: NV đã điền partner_name
        if self.partner_name and self.partner_name.strip():
            return self.partner_name.strip()
        if self.contact_name and self.contact_name.strip():
            return self.contact_name.strip()
        # Priority 3: strip Pancake prefix khỏi name
        import re
        nm = (self.name or '').strip()
        nm = re.sub(r'^\((Fanpage|Tiktok|Instagram|Pancake)\)\s*', '', nm, flags=re.IGNORECASE)
        return nm.strip() or 'KH'

    def _vd_build_quote_name(self):
        """Build "VINADUY - <Tên KH> - <MÃ TỈNH> - T<tháng>/<năm>".
        Trả '' nếu thiếu data buộc — caller giữ tên cũ.

        Vd: "VINADUY - Lê Văn Duẩn - TH - T5/2026"
        - MÃ TỈNH: viết tắt tỉnh (Thanh Hóa→TH). Thiếu tỉnh → bỏ đoạn này.
        - T<tháng>/<năm>: THỜI ĐIỂM TẠO BÁO GIÁ (vd_quote_created_date, giờ VN);
          chưa có thì lấy hiện tại. (user spec 2026-06-08)
        """
        self.ensure_one()
        kh_name = self._vd_extract_customer_name()
        if not kh_name or kh_name == 'KH':
            return ''  # Không có tên rõ ràng → skip rename
        province_code = self._vd_province_code(
            self.vd_intake_province_id.name if self.vd_intake_province_id else ''
        )
        qdt = self.vd_quote_created_date or fields.Datetime.now()
        local = fields.Datetime.context_timestamp(self, qdt)
        my_str = 'T%d/%d' % (local.month, local.year)
        parts = ['VINADUY', kh_name]
        if province_code:
            parts.append(province_code)
        parts.append(my_str)
        return ' - '.join(parts)

    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """Fallback email_from khi user không config email → tránh
        'Unable to send message' UserError trong message_post(mt_note).
        Áp dụng cho mọi message_post trên crm.lead trong module này."""
        try:
            return super()._message_compute_author(
                author_id=author_id, email_from=email_from, raise_on_email=raise_on_email,
            )
        except Exception:
            # Author không có email → dùng fallback (chỉ để qua validation,
            # KHÔNG thực sự gửi email vì mt_note là internal note).
            company = self.env.company
            domain = (company.email or 'noreply@vinaduy.local').split('@')[-1]
            user_email = self.env.user.login if '@' in (self.env.user.login or '') else None
            fallback = email_from or user_email or f'noreply@{domain}'
            return super()._message_compute_author(
                author_id=author_id, email_from=fallback, raise_on_email=False,
            )

    # ---------- Actions ----------

    def action_call(self):
        """Place an outbound call AND open intake popup if intake hasn't been
        done yet. NV vừa nói chuyện vừa điền popup.

        2 PATH dial:
        - Web SDK (NV có stringee_user_id): trả client action `vd_stringee_call`
          → browser khởi StringeeCall2 với mic của NV → audio bridge 2 chiều
          qua headset. ƯU TIÊN — đây là path có audio thật.
        - REST callout (NV không có stringee_user_id): fallback — dial KH qua
          PSTN, hotline làm Caller ID. KH bắt máy nhưng KHÔNG có ai nói chuyện
          (không bridge được) → Stringee tự ngắt sau vài giây. Cảnh báo NV.

        Chỉ guard 1 case: đang có call ACTIVE → block.
        Window dedup 3s ở make_call() đã đủ chặn accidental double-click.
        """
        self.ensure_one()
        phone = self.phone or self.mobile
        _logger.info("[VD-CALL] action_call: lead=%s phone=%s user=%s sui=%s",
                     self.id, phone, self.env.user.login,
                     self.env.user.stringee_user_id or '(none)')
        if not phone:
            _logger.warning("[VD-CALL] action_call REJECT: no phone on lead %s", self.id)
            raise UserError(_('Khách hàng chưa có số điện thoại.'))

        Call = self.env['stringee.call']
        user = self.env.user
        now = fields.Datetime.now()

        # === SELF-HEAL: auto-finalize stale placeholders trước khi check ===
        # Lý do: nếu Stringee reject CALL_NOT_ALLOWED hoặc JS crash giữa chừng,
        # placeholder kẹt state=initiated mãi → mọi call mới của user bị block
        # đến khi cron 60s chạy. Self-heal: bất kỳ placeholder >45s mà chưa
        # answered → coi như stale → mark ended (silent, không broadcast lỗi).
        # 45s đủ rộng để Stringee event đến (typical 1-3s) trước khi heal,
        # tránh kill stub trước khi matcher kịp claim call_id.
        stale_cutoff = now - timedelta(seconds=45)
        stale_records = Call.sudo().search([
            ('user_id', '=', user.id),
            ('state', 'in', ['draft', 'initiated', 'ringing']),
            ('create_date', '<', stale_cutoff),
        ])
        if stale_records:
            _logger.info(
                "[VD-CALL] action_call self-heal %d stale placeholders for user %s",
                len(stale_records), user.login,
            )
            stale_records.write({
                'state': 'no_answer',
                'end_time': now,
                'hangup_cause': 'SELF_HEAL_ON_NEW_CALL',
            })
            self.env.cr.commit()

        # Guard: chỉ block khi THỰC SỰ có call ACTIVE trong 20s gần đây
        # (đủ chặn double-click thật, không bị bug stale placeholder).
        active = Call.search_count([
            ('user_id', '=', user.id),
            ('state', 'in', ['draft', 'initiated', 'ringing', 'answered']),
            ('create_date', '>', stale_cutoff),
        ])
        if active:
            _logger.warning("[VD-CALL] action_call REJECT: %s active calls for user %s",
                            active, user.login)
            raise UserError(_(
                'Bạn đang có 1 cuộc gọi chưa kết thúc. '
                'Cúp máy cuộc cũ trước khi gọi tiếp.',
            ))

        # Mở popup khai thác khi lead còn ở giai đoạn khai thác
        if self.stage_code not in ('quote', 'negotiate', 'won', 'lost'):
            self.vd_intake_open = True

        # === STRINGEE FLOW 2 (App-to-Phone) ===
        # Browser StringeeCall2(client, hotline, customer) → Stringee fetches
        # answer_url → controller returns SCCO connect from=internal:hotline,
        # to=external:customer → audio bridge browser ↔ KH PSTN.
        # Doc: https://developer.stringee.com/docs/call-api-overview Flow 2
        if user.stringee_user_id:
            _logger.info("[VD-CALL] action_call → return client action vd_stringee_call (sui=%s, phone=%s)",
                         user.stringee_user_id, phone)
            # Pre-create call record → FAB switch sang "Đang đổ chuông" + nút hangup.
            # /stringee/answer controller sẽ match record này bằng callee_number
            # fallback rồi stamp call_id sau.
            placeholder = Call.create({
                'callee_number': phone,
                'user_id': user.id,
                'lead_id': self.id,
                'direction': 'outbound',
                'state': 'initiated',
            })
            self.env.cr.commit()  # ensure record visible cho answer_url + UI ngay
            return {
                'type': 'ir.actions.client',
                'tag': 'vd_stringee_call',
                'params': {
                    'phone': phone,
                    'lead_id': self.id,
                    'lead_name': self.name or self.partner_name or '',
                    'call_record_id': placeholder.id,
                },
            }

        _logger.info("[VD-CALL] action_call → REST callout fallback (user %s has NO sui)", user.login)
        # CHỈ GỌI NỘI MẠNG: resolve số tổng đài CÙNG MẠNG với khách trước.
        # Không có số cùng mạng (thiếu/khác mạng) → chặn + báo rõ cho NV.
        resolved = user._vd_resolve_outbound(phone)
        if resolved.get('error'):
            raise UserError(resolved['error'])
        # Fallback REST callout cho NV không có stringee_user_id (no Web SDK)
        call = Call.make_call(callee_number=phone, user_id=user.id,
                              from_number=resolved.get('from_number'))
        call.write({'lead_id': self.id})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã dial KH (REST fallback)'),
                'message': _('Bạn chưa cấu hình Stringee Web SDK → KH bắt máy '
                             'nhưng KHÔNG nghe được bạn nói.'),
                'type': 'warning',
            },
        }

    def action_open_intake_inline(self):
        """Toggle MỞ phiếu khai thác (chế độ mở rộng) mà không cần gọi điện."""
        self.ensure_one()
        self.vd_intake_open = True
        return True

    def action_close_intake_inline(self):
        """Đóng phiếu khai thác → quay về chế độ tóm tắt."""
        self.ensure_one()
        self.vd_intake_open = False
        return True

    def action_unlock_intake(self):
        """🔓 Mở khoá thông tin tư vấn — CHỈ admin. NV + Trưởng nhóm đều bị reject.

        User spec 2026-05-28: Mở khoá phải đồng thời revert stage về 'new'
        (vì filter "Xử lý vấn đề"/"Thi công gấp" yêu cầu locked=True). Không
        revert → KH biến mất khỏi mọi bucket.
        """
        self.ensure_one()
        is_admin = (
            self.env.user._is_superuser()
            or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin')
        )
        if not is_admin:
            raise UserError(_(
                'Chỉ Admin mới được mở khoá thông tin tư vấn đã chốt. '
                'Liên hệ Admin nếu cần chỉnh sửa.'
            ))
        write_vals = {
            'vd_intake_locked': False,
            'vd_intake_open': True,
        }
        # Revert stage về 'new' để KH quay lại bucket "Khách mới"
        if self.stage_code in ('quote', 'negotiate'):
            new_stage = self.env.ref(
                'vd_crm_lead.stage_new', raise_if_not_found=False,
            ) or self.env['crm.stage'].search([('code', '=', 'new')], limit=1)
            if new_stage:
                write_vals['stage_id'] = new_stage.id
        # vd_skip_auto_lock + vd_skip_intake_lock: bypass gate v9.131
        self.with_context(
            vd_skip_auto_lock=True, vd_skip_intake_lock=True, mail_notrack=True,
        ).write(write_vals)
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_('🔓 <b>%s</b> đã mở khoá thông tin tư vấn để chỉnh sửa.') % self.env.user.name,
        )
        return True

    def action_cancel_quote(self):
        """🗑️ HUỶ BÁO GIÁ (tạm thời) — KH coi như CHƯA làm báo giá: ẩn BÁO GIÁ
        CHI TIẾT + pill mất màu xanh. Data tư vấn GIỮ NGUYÊN để LÀM BÁO GIÁ
        lại sau khi sửa thông tin. Chỉ khi chưa CHỐT (locked=False)."""
        self.ensure_one()
        if self.vd_intake_locked:
            raise UserError(_(
                'Báo giá đã CHỐT — không thể huỷ. Liên hệ Admin để Mở khoá trước.'
            ))
        self.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_quote_cancelled': True,
        })
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_('🗑️ <b>%s</b> đã HUỶ BÁO GIÁ tạm thời (sửa lại thông tin tư vấn).')
            % self.env.user.name,
        )
        return True

    def action_redo_quote(self):
        """📝 LÀM BÁO GIÁ — khôi phục báo giá đã tạm huỷ (sau khi đã sửa thông tin)."""
        self.ensure_one()
        self.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_quote_cancelled': False,
        })
        return True

    def action_open_intake_popup(self):
        """LEGACY: redirect về chính lead form (popup đã bị xóa).
        Giữ lại stub để tương thích nếu có button cũ còn gọi."""
        self.ensure_one()
        self.vd_intake_open = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_save_intake_done(self):
        """🔒 CHỐT THÔNG TIN — khoá phiếu khai thác + chuyển stage sang Báo giá.

        Validate ĐỦ 12 trường bắt buộc — GỒM cả Sổ đỏ/cấp phép. Lưu ý (user spec
        2026-06-07): báo giá chi tiết chỉ cần 11 trường để HIỆN (vd_intake_complete),
        nhưng để CHỐT thì BẮT BUỘC đủ 12 (phải chọn Sổ đỏ/cấp phép, kể cả 'Chưa
        xác định'). Áp dụng cho TẤT CẢ user (kể cả admin/leader).
        """
        self.ensure_one()

        # ===== Validate ĐỦ 11 trường bắt buộc (giống vd_intake_complete) =====
        missing = []
        if not self.vd_intake_province_id:
            missing.append('1. Địa chỉ (Tỉnh / Thành)')
        if not self.vd_intake_timeline:
            missing.append('2. Thời gian khởi công')
        if not (self.vd_intake_total_m2 or 0) > 0:
            missing.append('3. Diện tích nhà (Ngang × Dài)')
        if not self.vd_intake_house_type:
            missing.append('4a. Mẫu nhà')
        if not self.vd_intake_foundation_type:
            missing.append('4b. Loại móng')
        if not (self.vd_intake_floor_1_m2 or 0) > 0:
            missing.append('5. Số tầng (ít nhất Tầng 1)')
        if not self.vd_intake_floor_1_function_ids:
            missing.append('6. Công năng Tầng 1')
        if not self.vd_intake_land_type:
            missing.append('7. Loại đất')
        if not self.vd_intake_soil_dump:
            missing.append('8. Chỗ để đất móng')
        if not self.vd_intake_car_access_select:
            missing.append('9. Ô tô vào')
        if not self.vd_intake_budget_range:
            missing.append('10. Tầm tài chính')
        if not self.vd_intake_dimensions:
            missing.append('11. Sổ đỏ / cấp phép')
        if missing:
            raise UserError(_(
                '❗ Chưa đủ thông tin để CHỐT. Vui lòng điền:\n• %s'
            ) % '\n• '.join(missing))

        filled = sum(1 for f in self._intake_data_fields if self[f])
        total = len(self._intake_data_fields)
        pct = round(filled * 100 / total) if total else 0
        kh = self.partner_name or self.contact_name or self.name or 'khách hàng'

        # Đóng phiếu khai thác + khoá để NV không sửa được nữa
        write_vals = {
            'vd_intake_open': False, 'vd_intake_locked': True,
            'vd_intake_last_edit': False,  # clear → cron không nhầm
        }
        if not self.vd_quote_created_date:
            write_vals['vd_quote_created_date'] = fields.Datetime.now()

        # AUTO chuyển stage sang "Báo giá" — bao gồm cả callback (Hẹn gọi lại).
        # User bấm SAVE = họ muốn chuyển. Chỉ skip nếu đã ở quote/negotiate/won/lost.
        auto_quoted = False
        if filled > 0 and self.stage_code not in ('quote', 'negotiate', 'won', 'lost'):
            quote_stage = self.env.ref('vd_crm_lead.stage_quote', raise_if_not_found=False) \
                          or self.env['crm.stage'].search([('code', '=', 'quote')], limit=1)
            if quote_stage:
                old_stage_name = self.stage_id.name or ''
                write_vals['stage_id'] = quote_stage.id
                auto_quoted = (old_stage_name, quote_stage.name)

        # write override sẽ tự apply mail_notrack/tracking_disable cho stage_id
        self.write(write_vals)

        # Vừa tạo báo giá → tự sinh "Cân đối ngân sách" nếu NS KH < giá báo > 15%.
        self._vd_auto_budget_problem()

        if auto_quoted:
            old_stage_name, new_stage_name = auto_quoted
            self.message_post(
                subtype_xmlid='mail.mt_note',
                body=_(
                    "✅ <b>Lưu khai thác + chuyển sang báo giá</b> — "
                    "từ <i>%s</i> sang <b>%s</b>."
                ) % (old_stage_name, new_stage_name),
            )

        # KHÔNG return act_window + rainbow effect nữa (user request).
        # Khoá fields đã set qua write_vals['vd_intake_locked']=True ở trên.
        # Odoo tự re-fetch + re-render form sau khi button method xong →
        # locked badge + button MỞ KHOÁ hiện ra, inputs readonly.
        # Stage_code mới (quote) cũng tự apply → panel BÁO GIÁ visible.
        # `filled`, `pct`, `kh` giữ lại trong audit log via message_post nếu cần.
        return True

    # ============ PHASE A — WORKFLOW BUTTONS ============
    @api.model
    def _vd_pending_cancel_count(self, user_id):
        """Số KH NV đang ĐỀ XUẤT HỦY mà CHƯA được duyệt (chờ duyệt) — khớp số
        hiện ở thùng rác của NV đó."""
        if not user_id:
            return 0
        return self.with_context(active_test=False).search_count([
            ('user_id', '=', user_id),
            ('stage_is_lost', '=', True),
            ('vd_cancel_state', '!=', 'approved'),
        ])

    def _vd_check_cancel_block(self):
        """Chặn NV hủy thêm khi đã tồn >= ngưỡng KH chờ duyệt hủy. Người DUYỆT
        được (trưởng phòng/GĐ/admin) KHÔNG bị chặn (họ tự xử lý được)."""
        user = self.env.user
        if (user._is_superuser()
                or user.has_group('vd_crm_lead.vd_crm_group_team_leader')):
            return
        pending = self.env['crm.lead']._vd_pending_cancel_count(user.id)
        if pending >= _VD_PENDING_CANCEL_BLOCK:
            raise UserError(_(
                '🚫 TẠM KHÓA HỦY KHÁCH\n\n'
                'Bạn đang tồn %d khách CHỜ DUYỆT HỦY (từ %d trở lên là bị khóa).\n'
                'Phần mềm tạm khóa để tránh hủy dồn quá nhiều chưa xử lý.\n\n'
                '➡ Nhờ TRƯỞNG PHÒNG vào duyệt hoặc từ chối bớt, đưa số khách '
                'chờ duyệt xuống DƯỚI %d, rồi bạn mới hủy tiếp được.'
            ) % (pending, _VD_PENDING_CANCEL_BLOCK, _VD_PENDING_CANCEL_BLOCK))

    def action_reject_cancel(self):
        """TỪ CHỐI đề xuất hủy → trả KH về 'Khách mới' cho NV chăm tiếp (KHÔNG
        archive, GIỮ NV phụ trách). Trưởng phòng/Giám đốc/Admin được làm."""
        can = (self.env.user._is_superuser()
               or self.env.user.has_group('vd_crm_lead.vd_crm_group_team_leader'))
        if not can:
            raise UserError(_(
                'Chỉ Trưởng phòng / Giám đốc / Admin được TỪ CHỐI hủy.'))
        new_stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False) \
            or self.env['crm.stage'].search([('code', '=', 'new')], limit=1)
        for rec in self:
            if rec.vd_cancel_state == 'approved':
                continue  # đã duyệt rồi → không từ chối nữa
            rec.with_context(mail_notrack=True, tracking_disable=True,
                             vd_skip_intake_lock=True).write({
                'active': True,
                'stage_id': new_stage.id if new_stage else rec.stage_id.id,
                'vd_cancel_state': False,
                'vd_cancel_category': False,
                'vd_lost_reason': False,
                'vd_lost_date': False,
                'vd_lost_is_auto': False,
            })
            rec.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('↩️ <b>Từ chối hủy</b> bởi %s — KH trả về <b>Khách mới</b> '
                       'để NV chăm tiếp.') % self.env.user.name,
            )
        return True

    def action_mark_no_demand(self):
        """KH KHÔNG có nhu cầu → mở wizard nhập lý do → set stage = lost."""
        self.ensure_one()
        self._vd_check_cancel_block()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Khách hàng không có nhu cầu'),
            'res_model': 'vd.lead.lost.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'dialog_size': 'medium',
            },
        }

    def action_vd_restore_cancelled_lead(self):
        """🔄 Hoàn tác huỷ — đưa KH từ stage 'Khách huỷ' trở về 'Khách mới'.
        CHỈ admin (vd_crm_group_admin) hoặc superuser được gọi.

        Clear toàn bộ field huỷ (reason/date/user/is_auto) + active=True.
        Post message vào chatter để audit ai khôi phục lúc nào.
        """
        self.ensure_one()
        is_admin = (
            self.env.user._is_superuser()
            or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin')
        )
        if not is_admin:
            raise UserError(_(
                'Chỉ Admin mới được hoàn tác huỷ KH. '
                'Liên hệ Admin nếu cần khôi phục KH này.'
            ))
        if not self.stage_is_lost:
            raise UserError(_('KH này không ở trạng thái Huỷ — không cần hoàn tác.'))

        new_stage = self.env['crm.stage'].search([('code', '=', 'new')], limit=1)
        if not new_stage:
            raise UserError(_('Không tìm thấy stage "Khách mới" (code="new").'))

        old_reason = self.vd_lost_reason or ''
        old_actor = self.vd_lost_user_id.name if self.vd_lost_user_id else (
            '🤖 cron auto' if self.vd_lost_is_auto else 'không rõ'
        )
        old_date_str = (
            self.vd_lost_date.strftime('%d/%m/%Y %H:%M:%S')
            if self.vd_lost_date else '—'
        )

        self.with_context(
            vd_skip_intake_lock=True, mail_notrack=True,
        ).write({
            'stage_id': new_stage.id,
            'active': True,
            'vd_lost_reason': False,
            'vd_lost_date': False,
            'vd_lost_user_id': False,
            'vd_lost_is_auto': False,
        })
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "🔄 <b>Hoàn tác huỷ KH</b> — <b>%s</b> đã khôi phục KH về "
                "<b>Khách mới</b>.<br/>"
                "<i>Huỷ trước đó:</i> %s lúc %s<br/>"
                "<i>Lý do huỷ cũ:</i> %s"
            ) % (self.env.user.name, old_actor, old_date_str, old_reason),
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_show_cancel_history(self):
        """🚫 ĐÃ HUỶ → mở popup hiển thị lịch sử huỷ: ai huỷ, khi nào, lý do,
        manual hay auto cron. Đọc từ field vd_lost_user_id + vd_lost_is_auto.
        Fallback (data cũ chưa backfill): dùng write_uid."""
        self.ensure_one()
        wiz = self.env['vd.lead.cancel.history.wizard'].create({
            'lead_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('🚫 Lịch sử huỷ KH'),
            'res_model': 'vd.lead.cancel.history.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }

    def action_open_callback_wizard(self):
        """Mở wizard hẹn ngày gọi lại — preset nhanh + custom datetime + note."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('📅 Hẹn ngày gọi lại'),
            'res_model': 'vd.lead.callback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'dialog_size': 'medium',
            },
        }

    def action_finish_intake_to_quote(self):
        """Hoàn tất khai thác → chuyển stage sang 'Khách báo giá'."""
        self.ensure_one()
        quote_stage = self.env.ref('vd_crm_lead.stage_quote', raise_if_not_found=False)
        if not quote_stage:
            quote_stage = self.env['crm.stage'].search([('code', '=', 'quote')], limit=1)
        if not quote_stage:
            raise UserError(_('Không tìm thấy stage "Khách báo giá".'))

        old_stage_name = self.stage_id.name or ''
        # mail_notrack=True → bỏ qua auto-tracking email (cần email_from config).
        # tracking_disable=True → disable mọi tracking message tự động.
        self.with_context(mail_notrack=True, tracking_disable=True).write(
            {'stage_id': quote_stage.id}
        )
        # Vẫn ghi note vào chatter (mt_note = internal, không gửi email)
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "✅ <b>Hoàn tất khai thác</b> — chuyển từ <i>%s</i> sang "
                "<b>%s</b>. NV bắt đầu lập báo giá."
            ) % (old_stage_name, quote_stage.name),
        )
        # Reload form để stage_code mới render → panel BÁO GIÁ tự hiện
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'effect': {
                'fadeout': 'slow',
                'message': f'✅ Đã chuyển sang Báo giá — "{self.name or ""}" sẵn sàng để báo giá.',
                'type': 'rainbow_man',
                'img_url': '/vd_crm_lead/static/src/img/celebration.svg',
            },
        }

    # ============ PHASE B — BÁO GIÁ ============
    def _build_quote_snapshot_vals(self):
        """Thu thập tất cả field cần snapshot vào vd.quote.version."""
        self.ensure_one()
        Pricing = self.env['vd.pricing.region']
        pricing = Pricing.search([('code', '=', self.vd_intake_region or '')], limit=1)
        # Tính breakdown chi tiết (móng / sàn / mái / phụ phí) — dùng TỔNG SÀN
        total_m2 = self.vd_intake_total_m2 or 0.0
        floors = self.vd_intake_floors_num or 1.0
        if pricing and total_m2:
            san_unit = self._vd_san_unit_for(pricing)  # bậc giá theo DT 1 sàn (fix 2026-06-12)
            # Threshold % móng theo DT MÓNG (Tầng 1) — fix 2026-05-28
            _found_area_th, _ = self._vd_get_found_roof_areas()
            found_pct = self._get_foundation_pct(
                pricing, self.vd_intake_foundation_type, _found_area_th >= 70,
            )
            roof_pct = self._get_roof_pct(pricing, self.vd_intake_roof_type)
        else:
            san_unit = 0; found_pct = 0; roof_pct = 0

        area = total_m2
        found_cost = total_m2 * (found_pct / 100.0) * san_unit
        floor_cost = total_m2 * san_unit
        roof_cost = total_m2 * (roof_pct / 100.0) * san_unit
        surcharge = self.vd_intake_estimate - (found_cost + floor_cost + roof_cost) if self.vd_intake_estimate else 0

        # Labels (text-readable cho snapshot)
        house_lbl = self._vd_selection_dict('vd_intake_house_type').get(
            self.vd_intake_house_type, ''
        )
        if self.vd_intake_house_type == 'khac' and self.vd_intake_house_type_other:
            house_lbl += f' ({self.vd_intake_house_type_other})'
        found_lbl = self._vd_selection_dict('vd_intake_foundation_type').get(
            self.vd_intake_foundation_type, ''
        )
        roof_lbl = self._vd_selection_dict('vd_intake_roof_type').get(
            self.vd_intake_roof_type, ''
        )
        region_lbl = {'bac': 'Miền Bắc', 'trung': 'Miền Trung', 'nam': 'Miền Nam'}.get(
            self.vd_intake_region, ''
        )

        return {
            'lead_id': self.id,
            'template_id': self.vd_quote_template_id.id if self.vd_quote_template_id else False,
            'kh_name': self.partner_name or self.contact_name or self.name or '',
            'kh_phone': self.phone or self.mobile or '',
            'kh_address': ', '.join(filter(None, [
                self.vd_intake_district.name if self.vd_intake_district else '',
                self.vd_intake_province_id.name if self.vd_intake_province_id else '',
            ])),
            'region_label': region_lbl,
            'length_m': self.vd_intake_length_m or 0,
            'width_m': self.vd_intake_width_m or 0,
            'area_m2': area,
            'floors': floors,
            'house_type_label': house_lbl,
            'foundation_label': found_lbl,
            'roof_label': roof_lbl,
            'san_unit_price': san_unit,
            'found_pct': found_pct,
            'roof_pct': roof_pct,
            'found_cost': found_cost,
            'floor_cost': floor_cost,
            'roof_cost': roof_cost,
            'surcharge': max(surcharge, 0),
            'estimate_total': self.vd_intake_estimate or 0,
            'quote_price': self.vd_quote_price or self.vd_intake_estimate or 0,
            'material': self.vd_quote_material or '',
            'payment_schedule': self.vd_quote_payment_schedule or '',
            'notes': self.vd_quote_notes or '',
        }

    def action_save_quote_version(self):
        """💾 Lưu báo giá hiện tại → tạo version mới (snapshot + diff)."""
        self.ensure_one()
        if self.vd_quote_locked:
            raise UserError(_('Báo giá đã CHỐT, không thể tạo version mới. '
                              'Mở khoá hoặc tạo lead mới.'))
        if not self.vd_quote_price and not self.vd_intake_estimate:
            raise UserError(_('Vui lòng nhập "Giá báo cho KH" hoặc điền '
                              'thông tin khai thác để tự tính ước tính trước.'))

        prev = self.vd_quote_version_ids[:1]  # Latest version (sorted desc)
        vals = self._build_quote_snapshot_vals()
        new_v = self.env['vd.quote.version'].create(vals)
        new_v.changes_log = new_v._build_diff_log(prev)

        # Generate PDF luôn
        new_v._generate_pdf()

        # Auto-rename lead khi có báo giá đầu tiên — format: "VINADUY - <KH> - <team>"
        self._vd_apply_quote_name_pattern()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'💾 Đã lưu V{new_v.version_no}',
                'message': new_v.changes_log or 'Bản nháp báo giá đã được snapshot.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_quote_history(self):
        """📜 Mở popup xem lịch sử báo giá (list view của vd.quote.version
        filter theo lead). target='new' → hiện trong dialog, không rời form lead."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('📜 Lịch sử báo giá — %s') % (self.name or ''),
            'res_model': 'vd.quote.version',
            'view_mode': 'list,form',
            'target': 'new',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
                'create': False,
                'edit': False,
                'dialog_size': 'fullscreen',
            },
        }

    @api.model
    def _vd_static_image_data_uri(self, relpath, mime='image/png'):
        """Đọc file ảnh trong static folder → trả về data URI base64.
        Dùng cho QWeb report vì wkhtmltopdf không luôn fetch được /module/static/."""
        import base64, os
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full = os.path.join(module_path, relpath)
            with open(full, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            return f'data:{mime};base64,{b64}'
        except Exception:
            return ''

    def _build_quote_context(self):
        """Build dict context để truyền vào docx template (Jinja placeholders).
        Tất cả intake data → key flat đơn giản cho NV viết template dễ."""
        self.ensure_one()
        from datetime import date
        Pricing = self.env['vd.pricing.region']
        pricing = Pricing.search([('code', '=', self.vd_intake_region or '')], limit=1)

        floors = self.vd_intake_floors_num or 1.0
        # Công thức (2026-05-21 final): TẤT CẢ rows dùng TỔNG DIỆN TÍCH SÀN.
        sum_floor_areas = 0.0
        n_floors = int(self.vd_intake_floors_select) if self.vd_intake_floors_select else 0
        for i in range(1, n_floors + 1):
            sum_floor_areas += self['vd_intake_floor_%s_m2' % i] or 0.0
        if self.vd_intake_has_tum and self.vd_intake_floor_tum_m2:
            sum_floor_areas += self.vd_intake_floor_tum_m2
        total_floor_area = sum_floor_areas or self.vd_intake_total_m2 or 0.0

        san_unit = self._vd_san_unit_for(pricing) if pricing and total_floor_area else 0  # bậc giá theo DT 1 sàn (fix 2026-06-12)
        # Móng dùng DT TẦNG 1; Mái dùng DT tầng trên cùng (fix 2026-05-29: trước
        # đây dùng total_floor_area → PDF lệch với UI breakdown panel).
        found_area, roof_area = self._vd_get_found_roof_areas() if pricing else (0.0, 0.0)
        found_pct = self._get_foundation_pct(pricing, self.vd_intake_foundation_type, found_area >= 70) if pricing else 0
        roof_pct = self._get_roof_pct(pricing, self._vd_resolve_roof_type()) if pricing else 0
        found_cost = found_area * (found_pct / 100.0) * san_unit
        floor_cost = total_floor_area * san_unit
        roof_cost = roof_area * (roof_pct / 100.0) * san_unit

        # Per-floor breakdown rows (Tầng 1/2/.../Lửng/Tum) — đồng nhất với UI panel.
        # Round 10 fix: bổ sung Lửng (trước đó bị thiếu cả PDF + UI HTML).
        floor_breakdown = []
        for i in range(1, n_floors + 1):
            fa = self['vd_intake_floor_%s_m2' % i] or 0.0
            if fa > 0:
                floor_breakdown.append({
                    'label': f'Tầng {i}',
                    'area': f'{fa:.0f}',
                    'cost': f'{fa * san_unit:,.0f}'.replace(',', '.'),
                })
        # Lửng — tầng phụ giữa 2 tầng (50-70 m² thường)
        if self.vd_intake_has_lung and self.vd_intake_floor_lung_m2:
            la = self.vd_intake_floor_lung_m2
            floor_breakdown.append({
                'label': 'Lửng',
                'area': f'{la:.0f}',
                'cost': f'{la * san_unit:,.0f}'.replace(',', '.'),
            })
        # Thông tầng — có Lửng → DT thông tầng (Tầng1−Lửng) × 40% × đơn giá
        thongtang_cost = 0.0
        if self.vd_intake_has_lung and pricing:
            tt_base = self.vd_intake_floor_thongtang_m2 or 0.0
            if tt_base > 0:
                tt_pct = self._get_roof_pct(pricing, 'thong_tang') or 0.0
                thongtang_cost = tt_base * (tt_pct / 100.0) * san_unit
                floor_breakdown.append({
                    'label': 'Thông tầng',
                    'area': f'{tt_base:.0f}',
                    'pct': f'{tt_pct:.0f}',
                    'cost': f'{thongtang_cost:,.0f}'.replace(',', '.'),
                })
        # Tum — tầng trên cùng
        if self.vd_intake_has_tum and self.vd_intake_floor_tum_m2:
            ta = self.vd_intake_floor_tum_m2
            floor_breakdown.append({
                'label': 'Tum',
                'area': f'{ta:.0f}',
                'cost': f'{ta * san_unit:,.0f}'.replace(',', '.'),
            })

        # TỔNG TIỀN báo giá = sum chính xác các dòng PDF (đồng bộ với UI
        # breakdown panel). User spec round 9: KHI NV update intake sau khi
        # lock báo giá → quote_price stored bị lệch với các dòng đang hiển thị
        # → PDF tổng = 1.228B nhưng các dòng cộng lại 937M (mismatch).
        # Fix: LUÔN ưu tiên components_total để toán PDF chính xác.
        components_total = found_cost + floor_cost + roof_cost + thongtang_cost
        # Cộng các item phát sinh (Thêm WC, cầu thang...) vào tổng
        surcharges_total = sum(self.vd_surcharge_ids.mapped('total'))
        components_total += surcharges_total
        # Round 12: TRỪ KM (khuyến mãi) — approved problems tag_code='promotion'
        km_problems = self.vd_lead_problem_ids.filtered(
            lambda p: p.tag_code == 'promotion' and p.km_state == 'approved' and (p.km_amount or 0) > 0
        )
        km_total = sum(p.km_amount or 0 for p in km_problems)
        # Round 12.1: CỘNG PS (phát sinh vật tư) — tag_code='extra_material'
        ps_problems = self.vd_lead_problem_ids.filtered(
            lambda p: p.tag_code == 'extra_material' and p.ps_state == 'approved' and (p.ps_amount or 0) > 0
        )
        ps_total = sum(p.ps_amount or 0 for p in ps_problems)
        components_total = components_total + ps_total - km_total
        total = components_total or self.vd_quote_price or self.vd_intake_estimate or 0

        house_lbl = self._vd_selection_dict('vd_intake_house_type').get(
            self.vd_intake_house_type, 'NHÀ DÂN DỤNG'
        ) or 'NHÀ DÂN DỤNG'
        found_lbl = self._vd_selection_dict('vd_intake_foundation_type').get(
            self.vd_intake_foundation_type, 'MÓNG ĐƠN'
        ) or 'MÓNG ĐƠN'
        eff_roof = self._vd_resolve_roof_type()
        roof_lbl = self._vd_selection_dict('vd_intake_roof_type').get(
            eff_roof, 'MÁI BẰNG'
        ) or 'MÁI BẰNG'

        def fmt(n):
            return f'{n:,.0f}'.replace(',', '.') if n else '0'

        return {
            'kh_name': self.partner_name or self.contact_name or self.name or '',
            'kh_phone': self.phone or self.mobile or '',
            'kh_address': ', '.join(filter(None, [
                self.vd_intake_district.name if self.vd_intake_district else '',
                self.vd_intake_province_id.name if self.vd_intake_province_id else '',
            ])),
            'today': date.today().strftime('%d/%m/%Y'),
            'house_type': house_lbl,
            'foundation': found_lbl,
            'roof': roof_lbl,
            # Diện tích MÓNG = Tầng 1, MÁI = tầng trên cùng (KHÔNG dùng total)
            'found_area': f'{found_area:.0f}',
            'roof_area': f'{roof_area:.0f}',
            # 'area' giữ legacy = tổng diện tích sàn (template khác dùng)
            'area': f'{total_floor_area:.0f}',
            'floors': f'{floors:.1f}'.rstrip('0').rstrip('.'),
            'total_floor_area': f'{total_floor_area:.0f}',
            'floor_breakdown': floor_breakdown,
            'unit_price': fmt(san_unit),
            'unit_price_raw': san_unit,  # raw float để template tính cost per tầng
            'found_pct': f'{found_pct:.0f}',
            'roof_pct': f'{roof_pct:.0f}',
            'found_cost': fmt(found_cost),
            'floor_cost': fmt(floor_cost),
            'roof_cost': fmt(roof_cost),
            # Round 12: list KM approved (mỗi item 1 row trong PDF — TRỪ)
            'km_items': [{
                'label': self._vd_km_row_label(p),
                'amount': fmt(p.km_amount),
                'amount_raw': p.km_amount,
            } for p in km_problems],
            # Round 12.1: list PS approved (mỗi item 1 row trong PDF — CỘNG)
            'ps_items': [{
                'label': (
                    f'🧰 PS: {p.ps_material_name}' if p.ps_material_name
                    else '🧰 Phát sinh vật tư'
                ),
                'amount': fmt(p.ps_amount),
                'amount_raw': p.ps_amount,
            } for p in ps_problems],
            # Legacy keys giữ để fallback (không dùng nếu km_items hoạt động)
            'discount_amount_raw': km_total,
            'discount_amount': fmt(km_total) if km_total else '',
            'discount_label': '',
            'total_price': fmt(total),
            'total_price_int': int(total),
            # Tiến độ thanh toán (4 đợt)
            'tt1': fmt(total * 0.30),
            'tt2': fmt(total * 0.30),
            'tt3': fmt(total * 0.30),
            'tt4': fmt(total * 0.10),
            # Logo + dấu mộc inline (base64) — bypass wkhtmltopdf static URL fetch
            'logo_data_uri': self._vd_static_image_data_uri('static/src/img/vinaduy_logo.png'),
            'stamp_data_uri': self._vd_static_image_data_uri('static/src/img/vinaduy_stamp.png'),
            # Items phát sinh (Thêm WC, cầu thang...) — render thêm rows sau Mái
            'surcharges': [{
                'name': s.name,
                'qty_label': s.quantity_label or (f'Số lượng {int(s.quantity)}' if s.quantity else '1'),
                'unit_price': fmt(s.unit_price),
                'total': fmt(s.total),
            } for s in self.vd_surcharge_ids.sorted(lambda x: (x.sequence, x.id))],
        }

    def _render_template_pdf_overlay_text(self):
        """🎯 GIỮ NGUYÊN 100% template PDF gốc (logo, ảnh, font, dấu mộc,
        decoration). Chỉ OVERLAY text values trên page báo giá bằng PyMuPDF.

        Cách hoạt động:
        1. Đọc template PDF gốc (16 trang) bằng PyMuPDF
        2. Trên page báo giá: search & replace text values cụ thể
           (Chị Lệ Chi → KH name, 16/04/2025 → today, Cần Thơ → address, etc.)
        3. Các trang khác giữ nguyên 100%
        4. Output: PDF cùng số trang với template, fonts/images giữ nguyên.

        Để dùng được: template phải có placeholder text giống Lệ Chi sample
        (Chị Lệ Chi, 16/04/2025, Cần Thơ, 120 M2 x 30%, 6.300.000 VNĐ, etc.)
        — hoặc user CHỈNH placeholder thành {{KH_NAME}}, {{TODAY}}, etc.
        trước khi upload.
        """
        self.ensure_one()
        tpl = self.vd_quote_template_id
        if not tpl or not tpl.file_attachment:
            return False
        fname = (tpl.file_name or '').lower()
        if not fname.endswith('.pdf'):
            return False

        try:
            import fitz  # PyMuPDF
        except ImportError:
            return False

        import base64, io
        ctx = self._build_quote_context()
        page_idx = (tpl.quote_page_index or 3) - 1  # 1-based to 0-based

        # Open template PDF
        tpl_bytes = base64.b64decode(tpl.file_attachment)
        doc = fitz.open(stream=tpl_bytes, filetype='pdf')
        if page_idx < 0 or page_idx >= len(doc):
            doc.close()
            return False

        # Build replacement mapping — cả placeholder {{...}} lẫn data Lệ Chi sample
        # (cover trường hợp user upload nguyên file Lệ Chi mà không sửa placeholder)
        replacements = {
            # Placeholders style
            '{{KH_NAME}}': ctx['kh_name'] or '—',
            '{{kh_name}}': ctx['kh_name'] or '—',
            '{{TODAY}}': ctx['today'],
            '{{today}}': ctx['today'],
            '{{ADDRESS}}': ctx['kh_address'] or '—',
            '{{kh_address}}': ctx['kh_address'] or '—',
            '{{HOUSE_TYPE}}': ctx['house_type'],
            '{{house_type}}': ctx['house_type'],
            '{{FOUNDATION}}': ctx['foundation'],
            '{{foundation}}': ctx['foundation'],
            '{{ROOF}}': ctx['roof'],
            '{{roof}}': ctx['roof'],
            '{{AREA}}': ctx['area'],
            '{{area}}': ctx['area'],
            '{{TOTAL_FLOOR_AREA}}': ctx['total_floor_area'],
            '{{total_floor_area}}': ctx['total_floor_area'],
            '{{UNIT_PRICE}}': ctx['unit_price'],
            '{{unit_price}}': ctx['unit_price'],
            '{{FOUND_PCT}}': ctx['found_pct'],
            '{{found_pct}}': ctx['found_pct'],
            '{{FOUND_COST}}': ctx['found_cost'],
            '{{found_cost}}': ctx['found_cost'],
            '{{FLOOR_COST}}': ctx['floor_cost'],
            '{{floor_cost}}': ctx['floor_cost'],
            '{{ROOF_PCT}}': ctx['roof_pct'],
            '{{roof_pct}}': ctx['roof_pct'],
            '{{ROOF_COST}}': ctx['roof_cost'],
            '{{roof_cost}}': ctx['roof_cost'],
            '{{TOTAL_PRICE}}': ctx['total_price'],
            '{{total_price}}': ctx['total_price'],
            # Fallback: data Lệ Chi sample (nếu user upload nguyên template chưa sửa)
            'Chị Lệ Chi': ctx['kh_name'] or 'Chị Lệ Chi',
            '16/04/2025': ctx['today'],
            'Cần Thơ': ctx['kh_address'] or 'Cần Thơ',
            '120 M2 x 30%': f"{ctx['area']} M2 x {ctx['found_pct']}%",
            '120 M2 x 53%': f"{ctx['area']} M2 x {ctx['roof_pct']}%",
            '120 ': f"{ctx['total_floor_area']} ",  # Diện tích sàn (đứng riêng)
            '6.300.000 VNĐ': f"{ctx['unit_price']} VNĐ",
            '226.800.000 VNĐ': f"{ctx['found_cost']} VNĐ",
            '756.000.000 VNĐ': f"{ctx['floor_cost']} VNĐ",
            '400.680.000 VNĐ': f"{ctx['roof_cost']} VNĐ",
            '1.383.480.000 VNĐ': f"{ctx['total_price']} VNĐ",
            'MÁI NGÓI': (ctx['roof'] or '').upper(),
            'MÓNG ĐƠN': (ctx['foundation'] or '').upper(),
            'NHÀ DÂN DỤNG': (ctx['house_type'] or '').upper(),
        }

        # 2-STEP overlay với DejaVu Sans + FALLBACK get_text("dict") cho Vietnamese:
        # PDF từ PowerPoint thường lưu Vietnamese theo glyph riêng → search_for fail.
        # Fallback: extract all text spans → substring match → dùng span bbox.
        import unicodedata
        page = doc[page_idx]
        FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

        # Pre-extract spans VÀ full-lines (cho fallback substring match đa-span)
        # Lưu thêm font/size/color của span để replacement match được style gốc.
        all_spans = []
        all_lines = []  # mỗi line = concat các span trên cùng dòng (cho phrase đa-span)
        try:
            page_dict = page.get_text("dict")
            for block in page_dict.get('blocks', []):
                for line in block.get('lines', []):
                    line_text = ''
                    line_bbox = None
                    line_size = None
                    line_color = None
                    for span in line.get('spans', []):
                        sb = fitz.Rect(span.get('bbox', [0, 0, 0, 0]))
                        ssize = float(span.get('size', 11) or 11)
                        scolor = int(span.get('color', 0) or 0)
                        all_spans.append({
                            'text': span.get('text', ''),
                            'bbox': sb, 'size': ssize, 'color': scolor,
                        })
                        line_text += span.get('text', '')
                        line_bbox = fitz.Rect(sb) if line_bbox is None else (line_bbox | sb)
                        if line_size is None:
                            line_size = ssize
                            line_color = scolor
                    if line_text.strip() and line_bbox is not None:
                        all_lines.append({
                            'text': line_text, 'bbox': line_bbox,
                            'size': line_size or 11, 'color': line_color or 0,
                        })
        except Exception:
            pass

        def int_to_rgb(c):
            """Convert PyMuPDF int color (0xRRGGBB) → tuple(0-1)."""
            return ((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0

        def search_robust(text):
            """Search NFC/NFD; fallback substring match qua spans → lines.
            Trả về list dict {bbox, size, color} (size/color = None khi từ search_for)."""
            text = str(text)
            for variant in [text, unicodedata.normalize('NFC', text),
                            unicodedata.normalize('NFD', text)]:
                try:
                    found = page.search_for(variant)
                    if found:
                        # search_for không cho font info → match span gần nhất để lấy size/color
                        out = []
                        for r in found:
                            best = None
                            for sp in all_spans:
                                if sp['bbox'].intersects(r) or r.contains(sp['bbox'].tl):
                                    best = sp
                                    break
                            out.append({
                                'bbox': r,
                                'size': best['size'] if best else 11,
                                'color': best['color'] if best else 0,
                            })
                        return out
                except Exception:
                    continue
            text_norm = unicodedata.normalize('NFC', text).strip()
            if not text_norm:
                return []
            # FALLBACK 1: span-level substring
            results = []
            for span in all_spans:
                span_text = unicodedata.normalize('NFC', span['text']).strip()
                if span_text and (text_norm == span_text or text_norm in span_text):
                    results.append({'bbox': span['bbox'], 'size': span['size'],
                                     'color': span['color']})
            if results:
                return results
            # FALLBACK 2: line-level substring (cho phrase chia ra nhiều span)
            for line in all_lines:
                line_text = unicodedata.normalize('NFC', line['text']).strip()
                if line_text and text_norm in line_text:
                    results.append({'bbox': line['bbox'], 'size': line['size'],
                                     'color': line['color']})
            return results

        def sample_bg_color(rect):
            """Sample 8 điểm BÊN NGOÀI rect (trên/dưới ở 3 vị trí ngang + 2 bên),
            lấy MEDIAN từng kênh để tránh outliers (border, stripe, text bleed).
            Cách xa rect 6px để né edge effects."""
            samples = []
            offsets = [
                # trên (3 điểm)
                (rect.width * 0.25, -6), (rect.width * 0.5, -6), (rect.width * 0.75, -6),
                # dưới (3 điểm)
                (rect.width * 0.25, rect.height + 6),
                (rect.width * 0.5, rect.height + 6),
                (rect.width * 0.75, rect.height + 6),
                # 2 bên
                (-6, rect.height / 2), (rect.width + 6, rect.height / 2),
            ]
            for dx, dy in offsets:
                sx = rect.x0 + dx
                sy = rect.y0 + dy
                if sx < 0 or sy < 0 or sx >= page.rect.x1 or sy >= page.rect.y1:
                    continue
                try:
                    clip = fitz.Rect(sx, sy, sx + 1, sy + 1)
                    pix = page.get_pixmap(clip=clip, alpha=False)
                    if pix.samples and len(pix.samples) >= 3:
                        samples.append((pix.samples[0], pix.samples[1], pix.samples[2]))
                except Exception:
                    continue
            if not samples:
                return (1, 1, 1)
            # Filter saturated samples (likely là pixel của chữ màu — đỏ "VINADUY",
            # xanh header, etc.). Chỉ giữ pixel gần gray/white (chênh lệch RGB < 35).
            near_gray = [s for s in samples if max(s) - min(s) < 35]
            if near_gray:
                samples = near_gray
            # median per channel → loại outlier (border/text bleed)
            samples_r = sorted(s[0] for s in samples)
            samples_g = sorted(s[1] for s in samples)
            samples_b = sorted(s[2] for s in samples)
            mid = len(samples) // 2
            r, g, b = samples_r[mid], samples_g[mid], samples_b[mid]
            # Sanity check: nếu vẫn quá tối (mean < 100) → fallback trắng,
            # vì cell báo giá hầu như luôn nền trắng/xám-nhạt.
            if (r + g + b) / 3 < 100:
                return (1, 1, 1)
            return (r / 255.0, g / 255.0, b / 255.0)

        # Phase 1: collect rect + new text + whiteout (rect mở rộng để clean)
        # QUAN TRỌNG: sample bg color TRƯỚC khi add redact (vì redact chưa apply
        # nên page vẫn còn nguyên — get_pixmap đọc được màu cell gốc).
        to_insert = []
        seen_bbox = set()  # tránh redact 2 lần cùng vùng
        for old_text, new_text in replacements.items():
            new_text = str(new_text or '').strip()
            old_text = str(old_text)
            # Skip nếu giá trị mới trống hoặc giống cũ
            if not new_text or old_text.strip() == new_text:
                continue
            for hit in search_robust(old_text):
                rect = hit['bbox']
                key = (round(rect.x0, 1), round(rect.y0, 1),
                        round(rect.x1, 1), round(rect.y1, 1))
                if key in seen_bbox:
                    continue
                seen_bbox.add(key)
                # Mở rộng rect 1.5px mỗi phía → whiteout clean, không lòi text cũ
                expanded = fitz.Rect(rect.x0 - 1.5, rect.y0 - 1,
                                      rect.x1 + 1.5, rect.y1 + 1)
                bg = sample_bg_color(rect)
                to_insert.append((expanded, new_text, bg, hit['size'], hit['color']))
                page.add_redact_annot(expanded, fill=bg)

        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Phase 2: insert text — size = MIN(span_size, rect_fits) để KHÔNG bị
        # insert_textbox return âm (text quá lớn không fit → silent fail).
        # Font face vẫn dùng DejaVu Sans để hỗ trợ tiếng Việt unicode đầy đủ.
        for rect, new_text, bg, src_size, src_color in to_insert:
            # Cap fsize: phải fit trong rect height (textbox cần ~1.2 line-height)
            max_fits = rect.height / 1.2
            src_size = float(src_size) if src_size else 11.0
            fsize = min(src_size, max_fits)
            fsize = max(6.0, fsize)  # tối thiểu 6pt để vẫn đọc được

            # Color gốc của span (đen mặc định nếu 0)
            text_color = int_to_rgb(src_color) if src_color else (0, 0, 0)
            # Contrast fallback: nếu màu chữ và bg quá giống → đảo đen/trắng
            lum_bg = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
            lum_tx = 0.299 * text_color[0] + 0.587 * text_color[1] + 0.114 * text_color[2]
            if abs(lum_bg - lum_tx) < 0.25:
                text_color = (1, 1, 1) if lum_bg < 0.5 else (0, 0, 0)

            # insert_textbox RETURN NEGATIVE khi text không fit (không raise!).
            # Check return value → fallback insert_text (anchor-based, no box).
            rv = None
            try:
                rv = page.insert_textbox(
                    rect, new_text,
                    fontfile=FONT_FILE, fontname='vd_dejavu',
                    fontsize=fsize, color=text_color,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            except Exception:
                rv = None
            if rv is None or (isinstance(rv, (int, float)) and rv < 0):
                # Fallback: insert_text anchored — không có box constraint
                try:
                    page.insert_text(
                        (rect.x0 + 1, rect.y0 + fsize * 0.9), new_text,
                        fontfile=FONT_FILE, fontname='vd_dejavu_fb',
                        fontsize=fsize, color=text_color,
                    )
                except Exception:
                    pass

        # Save merged PDF
        out = io.BytesIO()
        doc.save(out, garbage=4, deflate=True)
        doc.close()
        out.seek(0)
        merged = out.read()

        kh = self.partner_name or self.contact_name or self.name or 'KH'
        kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
        return self.env['ir.attachment'].create({
            'name': f'BaoGia_{kh_safe}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(merged),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

    def _render_template_pdf_replace_page(self):
        """ƯU TIÊN cao nhất khi template là .pdf: GIỮ NGUYÊN 100% các trang
        khác, CHỈ THAY trang BẢNG BÁO GIÁ CHI TIẾT bằng data của KH cụ thể.
        - Trang giữ nguyên: lấy từ template (logo, ảnh, format, mọi thứ)
        - Trang thay thế: generate từ QWeb single-page với data intake
        - Số thứ tự trang báo giá: vd_quote_template_id.quote_page_index (default 3)"""
        self.ensure_one()
        tpl = self.vd_quote_template_id
        # FALLBACK: nếu lead chưa gán template, auto-pick template active mới nhất
        # (đảm bảo NV nhận template chuẩn ngay cả khi quên upload riêng).
        if not tpl:
            tpl = self.env['vd.quote.template'].sudo().search(
                [('active', '=', True)],
                order='create_date desc', limit=1,
            )
            if tpl:
                _logger.info("[Quote] Lead %s thiếu template, auto-pick %s",
                             self.id, tpl.name)
                self.with_context(mail_notrack=True).vd_quote_template_id = tpl.id
        if not tpl or not tpl.file_attachment:
            _logger.warning(
                "[Quote] Lead %s: no template (vd_quote_template_id=%s, file_attachment=%s)",
                self.id, tpl.id if tpl else None, bool(tpl.file_attachment) if tpl else None,
            )
            return False
        fname = (tpl.file_name or '').lower()
        if not fname.endswith('.pdf'):
            _logger.warning("[Quote] Lead %s: template file_name=%r KHÔNG kết thúc .pdf",
                            self.id, tpl.file_name)
            return False

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            raise UserError(_('Thiếu thư viện pypdf. Yêu cầu admin: pip install pypdf'))

        import base64, io

        # 1. Đọc template PDF
        tpl_bytes = base64.b64decode(tpl.file_attachment)
        tpl_reader = PdfReader(io.BytesIO(tpl_bytes))
        total_pages = len(tpl_reader.pages)

        # 2. Generate báo giá single-page PDF
        report = self.env.ref('vd_crm_lead.action_vd_quote_single_page_report',
                              raise_if_not_found=False)
        if not report:
            raise UserError(_('Không tìm thấy report single-page báo giá.'))
        baogia_bytes, _ct = report._render_qweb_pdf(report.report_name, [self.id])
        baogia_reader = PdfReader(io.BytesIO(baogia_bytes))

        # 3. Splice: giữ trang khác, thay 1 trang báo giá
        target_idx = (tpl.quote_page_index or 3) - 1  # 1-based → 0-based
        if target_idx < 0 or target_idx >= total_pages:
            target_idx = min(2, total_pages - 1)  # fallback page 3 hoặc cuối

        # Scale báo giá page khớp KÍCH THƯỚC trang template đang thay (để mọi
        # trang trong file PDF cuối cùng có cùng size, KHÔNG xoay gì hết).
        try:
            from pypdf import Transformation
        except ImportError:
            Transformation = None

        target_tpl_page = tpl_reader.pages[target_idx]
        target_w = float(target_tpl_page.mediabox.width)
        target_h = float(target_tpl_page.mediabox.height)

        def _scale_to_target(p):
            if Transformation is None:
                return
            try:
                src_w = float(p.mediabox.width)
                src_h = float(p.mediabox.height)
                if src_w <= 0 or src_h <= 0:
                    return
                sx = target_w / src_w
                sy = target_h / src_h
                p.add_transformation(Transformation().scale(sx, sy))
                p.mediabox.upper_right = (target_w, target_h)
                p.cropbox.upper_right = (target_w, target_h)
            except Exception:
                pass

        writer = PdfWriter()
        for i, page in enumerate(tpl_reader.pages):
            if i == target_idx:
                for new_p in baogia_reader.pages:
                    _scale_to_target(new_p)
                    writer.add_page(new_p)
            else:
                writer.add_page(page)

        # 4. Save merged PDF
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        merged = out.read()

        kh = self.partner_name or self.contact_name or self.name or 'KH'
        kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
        att = self.env['ir.attachment'].create({
            'name': f'BaoGia_{kh_safe}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(merged),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return att

    def _render_template_pdf(self):
        """Fill AcroForm fields trong template .pdf (giữ NGUYÊN 100% trang/ảnh).
        Yêu cầu: PDF phải có form fields tên trùng với keys của _build_quote_context
        (kh_name, kh_phone, kh_address, today, total_price, area, ...)."""
        self.ensure_one()
        tpl = self.vd_quote_template_id
        if not tpl or not tpl.file_attachment:
            return False
        fname = (tpl.file_name or '').lower()
        if not fname.endswith('.pdf'):
            return False

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            raise UserError(_('Thiếu thư viện pypdf. Yêu cầu admin: pip install pypdf'))

        import base64, io
        tpl_bytes = base64.b64decode(tpl.file_attachment)
        reader = PdfReader(io.BytesIO(tpl_bytes))

        fields = reader.get_fields()
        if not fields:
            raise UserError(_(
                'File PDF template KHÔNG có form fields → không thể auto-fill data.\n\n'
                'CÁCH 1 (đơn giản): Convert PDF → .docx tại ilovepdf.com → '
                'mở Word, gõ {{kh_name}}, {{total_price}}... vào trang báo giá → '
                'upload file .docx (16 trang giữ nguyên).\n\n'
                'CÁCH 2: Mở PDF trong Adobe Acrobat Pro → Tools → Prepare Form → '
                'Add Text Field tại các vị trí cần điền + đặt TÊN field theo:\n'
                'kh_name, kh_phone, kh_address, today, house_type, foundation, '
                'roof, area, floors, found_pct, found_cost, floor_cost, roof_pct, '
                'roof_cost, unit_price, total_price → Save + upload lại.'
            ))

        ctx = self._build_quote_context()
        fill_data = {k: str(v) for k, v in ctx.items() if k in fields}

        writer = PdfWriter(clone_from=reader)
        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, fill_data)
            except Exception:
                pass

        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        merged_bytes = out.read()

        kh = self.partner_name or self.contact_name or self.name or 'KH'
        kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
        att = self.env['ir.attachment'].create({
            'name': f'BaoGia_{kh_safe}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(merged_bytes),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return att

    def _render_template_docx(self):
        """Merge data vào file template .docx (giữ nguyên ảnh/format/branding).
        Yêu cầu: vd_quote_template_id phải là .docx có Jinja placeholders."""
        self.ensure_one()
        tpl = self.vd_quote_template_id
        if not tpl or not tpl.file_attachment:
            return False
        fname = (tpl.file_name or '').lower()
        if not fname.endswith('.docx'):
            return False  # chỉ support .docx merge

        try:
            from docxtpl import DocxTemplate
        except ImportError:
            raise UserError(_(
                'Thiếu thư viện docxtpl. Yêu cầu admin cài: pip install docxtpl'
            ))

        import base64, io
        # Decode template binary
        tpl_bytes = base64.b64decode(tpl.file_attachment)
        doc = DocxTemplate(io.BytesIO(tpl_bytes))

        ctx = self._build_quote_context()
        doc.render(ctx)

        out = io.BytesIO()
        doc.save(out)
        out.seek(0)
        merged_bytes = out.read()

        # Lưu file merged vào ir.attachment
        kh = self.partner_name or self.contact_name or self.name or 'KH'
        kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
        att = self.env['ir.attachment'].create({
            'name': f'BaoGia_{kh_safe}.docx',
            'type': 'binary',
            'datas': base64.b64encode(merged_bytes),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        })
        return att

    def _generate_single_page_quote_pdf(self):
        """Generate 1 TRANG báo giá chi tiết (QWeb DejaVu Sans, hỗ trợ Vietnamese).
        Output: 1 trang duy nhất với layout VINADUY (logo, header xanh, KH info,
        pricing table, dấu mộc đỏ). Data từ intake KH."""
        self.ensure_one()
        if not self.vd_intake_estimate and not self.vd_quote_price:
            raise UserError(_(
                'Chưa có dữ liệu để tạo báo giá. Cần: diện tích, số tầng, móng, mái.'
            ))
        report = self.env.ref('vd_crm_lead.action_vd_quote_single_page_report',
                              raise_if_not_found=False)
        if not report:
            raise UserError(_('Không tìm thấy report single-page báo giá.'))
        pdf_bytes, _ct = report._render_qweb_pdf(report.report_name, [self.id])
        import base64
        kh = self.partner_name or self.contact_name or self.name or 'KH'
        kh_safe = ''.join(c if c.isalnum() else '_' for c in kh)[:40]
        return self.env['ir.attachment'].create({
            'name': f'BaoGia_{kh_safe}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_bytes),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

    def _generate_quote_pdf_now(self):
        """Helper: tạo snapshot + generate PDF từ data hiện tại. Trả về vd.quote.version."""
        self.ensure_one()
        if not self.vd_intake_estimate and not self.vd_quote_price:
            raise UserError(_(
                'Chưa có dữ liệu để tạo báo giá. Vui lòng nhập:\n'
                '• Diện tích, số tầng, móng, mái\n'
                '• Hoặc Giá báo cho KH (manual)'
            ))
        prev = self.vd_quote_version_ids[:1]
        vals = self._build_quote_snapshot_vals()
        new_v = self.env['vd.quote.version'].create(vals)
        new_v.changes_log = new_v._build_diff_log(prev)
        new_v._generate_pdf()
        if not new_v.pdf_attachment_id:
            raise UserError(_('Không tạo được file PDF. Liên hệ admin kiểm tra wkhtmltopdf.'))
        return new_v

    def _render_uploaded_template(self):
        """ƯU TIÊN: thay nguyên page báo giá bằng QWeb single-page → DATA chính xác
        100%, font/màu đồng nhất; các page khác (logo, dấu mộc, terms) giữ NGUYÊN.
        Overlay text bị xuống cuối vì PowerPoint-export PDF lưu Vietnamese theo
        custom CID → search/replace KHÔNG đáng tin (sai tên KH, lệch font, ô đỏ).
        1. .pdf splice page (BEST: page báo giá clean, page khác nguyên gốc)
        2. .pdf AcroForm fill (template có form fields)
        3. .docx Jinja merge (template Word giữ 100% format)
        4. .pdf overlay text (last resort cho PDF không splice được)
        5. Default 1 trang QWeb (cuối cùng)"""
        # LOGGING: trước đây except: pass nuốt mọi exception → không biết
        # tại sao splice fail. Giờ log để debug.
        try:
            att = self._render_template_pdf_replace_page()
            if att:
                return att
            _logger.warning("[Quote] _render_template_pdf_replace_page returned empty")
        except Exception as e:
            _logger.warning("[Quote] _render_template_pdf_replace_page failed: %s",
                            e, exc_info=True)
        try:
            att = self._render_template_pdf()
            if att:
                return att
        except Exception as e:
            _logger.warning("[Quote] _render_template_pdf (AcroForm) failed: %s", e)
        try:
            att = self._render_template_docx()
            if att:
                return att
        except Exception as e:
            _logger.warning("[Quote] _render_template_docx failed: %s", e)
        try:
            att = self._render_template_pdf_overlay_text()
            if att:
                return att
        except Exception as e:
            _logger.warning("[Quote] _render_template_pdf_overlay_text failed: %s",
                            e, exc_info=True)
        try:
            _logger.warning("[Quote] FALLBACK to QWeb single-page (uploaded template paths failed)")
            return self._generate_single_page_quote_pdf()
        except Exception as e:
            _logger.error("[Quote] All quote PDF paths failed: %s", e)
            return None

    def action_download_quote_now(self):
        """📥 DOWNLOAD báo giá:
        - Template .pdf có AcroForm → fill fields, giữ NGUYÊN 16 trang gốc
        - Template .docx có Jinja placeholders → merge giữ NGUYÊN tất cả trang
        - Không có template / format khác → fallback QWeb 4 trang tự sinh
        """
        self.ensure_one()
        if self.vd_quote_locked and self.vd_quote_locked_version_id:
            return self.vd_quote_locked_version_id.action_view_pdf()

        att = self._render_uploaded_template()
        if att:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{att.id}?download=true',
                'target': 'self',
            }

        new_v = self._generate_quote_pdf_now()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{new_v.pdf_attachment_id.id}?download=true',
            'target': 'self',
        }

    def action_preview_quote_now(self):
        """👁️ XEM TRƯỚC: mở POPUP TO ĐÙNG (fullscreen modal) hiển thị PDF
        inline qua widget pdf_viewer của Odoo. Scroll xem từng trang ngay
        trong dialog, không cần mở tab mới."""
        self.ensure_one()
        import base64

        # Tìm/generate PDF
        pdf_bytes = None
        pdf_name = 'preview_baogia.pdf'

        if self.vd_quote_locked and self.vd_quote_locked_version_id:
            att = self.vd_quote_locked_version_id.pdf_attachment_id
            if att:
                pdf_bytes = base64.b64decode(att.datas)
                pdf_name = att.name or pdf_name
        if not pdf_bytes:
            att = self._render_uploaded_template()
            if att:
                pdf_bytes = base64.b64decode(att.datas)
                pdf_name = att.name or pdf_name
        if not pdf_bytes:
            new_v = self._generate_quote_pdf_now()
            if new_v.pdf_attachment_id:
                pdf_bytes = base64.b64decode(new_v.pdf_attachment_id.datas)
                pdf_name = new_v.pdf_attachment_id.name or pdf_name

        if not pdf_bytes:
            raise UserError(_('Không tạo được file PDF preview.'))

        # Tạo wizard chứa file PDF + mở dialog FULLSCREEN
        wizard = self.env['vd.quote.preview.wizard'].create({
            'lead_id': self.id,
            'pdf_data': base64.b64encode(pdf_bytes),
            'pdf_name': pdf_name,
        })
        kh = self.partner_name or self.contact_name or self.name or ''
        return {
            'type': 'ir.actions.act_window',
            'name': f'📄 Xem trước báo giá — {kh}',
            'res_model': 'vd.quote.preview.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'fullscreen'},
        }

    def action_lock_quote_to_negotiate(self):
        """🔒 Chốt báo giá CUỐI CÙNG → set state='locked' + chuyển sang Đàm phán.
        Yêu cầu: phải có ít nhất 1 version + có quote_price."""
        self.ensure_one()
        if self.vd_quote_locked:
            raise UserError(_('Báo giá đã chốt rồi.'))
        if not self.vd_quote_price:
            raise UserError(_('Vui lòng nhập "Giá báo cho KH" trước khi chốt.'))

        # Lưu version cuối + lock luôn
        prev = self.vd_quote_version_ids[:1]
        vals = self._build_quote_snapshot_vals()
        vals['state'] = 'locked'
        new_v = self.env['vd.quote.version'].create(vals)
        new_v.changes_log = (new_v._build_diff_log(prev) + '\n🔒 BẢN CHỐT CUỐI CÙNG').strip()
        new_v._generate_pdf()

        from datetime import date, timedelta
        deadline = date.today() + timedelta(days=7)

        # Move stage to negotiate
        nego = self.env.ref('vd_crm_lead.stage_negotiate', raise_if_not_found=False) or \
               self.env['crm.stage'].search([('code', '=', 'negotiate')], limit=1)
        if not nego:
            raise UserError(_('Không tìm thấy stage "Khách đàm phán".'))

        old_stage = self.stage_id.name or ''
        self.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_quote_locked': True,
            'vd_quote_locked_version_id': new_v.id,
            'stage_id': nego.id,
            'vd_negotiate_deadline': deadline,
        })
        # Auto-rename theo format VINADUY (nếu chưa)
        self._vd_apply_quote_name_pattern()
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "🔒 <b>Đã CHỐT báo giá V%d</b> với giá <b>%s đ</b>.<br/>"
                "Chuyển từ <i>%s</i> → <b>%s</b>.<br/>"
                "Deadline đàm phán: <b>%s</b> (7 ngày)."
            ) % (
                new_v.version_no,
                f'{new_v.quote_price:,.0f}'.replace(',', '.'),
                old_stage, nego.name, deadline.strftime('%d/%m/%Y'),
            ),
        )
        # Reload form để stage_id mới hiển thị + panel Đàm phán visible
        # mà không cần F5. Effect = rainbow_man celebration.
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'effect': {
                'fadeout': 'slow',
                'message': (f'🔒 Đã CHỐT báo giá → Đàm phán\n'
                            f'Deadline: {deadline.strftime("%d/%m/%Y")} (7 ngày)'),
                'type': 'rainbow_man',
            },
        }

    # ============ PHASE C — ĐÀM PHÁN ============
    def action_create_negotiate_activity(self, days_offset=1):
        """Tạo activity nhắc NV gọi KH sau X ngày để chốt cọc."""
        self.ensure_one()
        from datetime import date, timedelta
        due = date.today() + timedelta(days=days_offset)
        self.activity_schedule(
            'mail.mail_activity_data_call',
            date_deadline=due,
            summary=_('📞 Gọi KH chốt cọc 50tr (sau %d ngày)') % days_offset,
            note=_(
                'Báo giá đã chốt. Cần gọi để KH cọc tối thiểu 50.000.000đ.<br/>'
                '<b>Kịch bản gợi ý:</b><br/>'
                '"Anh/chị ơi, để bên em giữ giá vật liệu + lịch khởi công + huy động '
                'tổ thợ thì cần KH cọc tối thiểu 50tr trong vòng 7 ngày. Anh/chị '
                'tiện hôm nào ghé văn phòng ký HĐ + chuyển khoản cọc ạ?"'
            ),
            user_id=self.user_id.id or self.env.uid,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '📞 Đã tạo nhắc gọi',
                'message': f'Activity gọi sau {days_offset} ngày — deadline {due.strftime("%d/%m/%Y")}',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_unlock_quote_for_edit(self):
        """🔓 Mở khóa báo giá đã chốt → cho phép NV sửa lại theo yêu cầu KH
        trong quá trình đàm phán. Stage giữ nguyên = negotiate. Sau khi sửa
        + Lưu version, NV bấm Chốt báo giá lại để lock.
        """
        self.ensure_one()
        if not self.vd_quote_locked:
            raise UserError(_('Báo giá chưa khóa, không cần unlock.'))
        if self.vd_contract_signed:
            raise UserError(_('Đã ký HĐ rồi, không sửa được báo giá nữa.'))
        old_v = self.vd_quote_locked_version_id
        self.write({
            'vd_quote_locked': False,
            'vd_quote_locked_version_id': False,
        })
        self.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                '🔓 <b>MỞ KHÓA báo giá</b> để sửa theo yêu cầu KH trong đàm phán.<br/>'
                'Bản chốt cũ: <b>V%s</b>. NV cần Lưu version mới + bấm Chốt lại '
                'để khóa giá mới.'
            ) % (old_v.version_no if old_v else '?'),
        )
        # Reload form để panel báo giá hiện lại (có thể edit)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_sign_contract(self):
        """📅 Mở wizard đặt lịch đi ký HĐ — KH đã đồng ý."""
        self.ensure_one()
        if not self.vd_quote_locked:
            raise UserError(_('Phải chốt báo giá trước khi đặt lịch ký HĐ.'))
        if self.vd_contract_signed:
            raise UserError(_('Hợp đồng đã được ký rồi.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Đặt lịch ký hợp đồng'),
            'res_model': 'vd.contract.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'dialog_size': 'medium',
            },
        }

    def action_open_meeting_wizard(self):
        """📅 Mở popup TẠO LỊCH GẶP — nhập info, lưu xong ra card văn bản chụp gửi KH."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Thông tin lịch gặp'),
            'res_model': 'vd.meeting.schedule.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_lead_id': self.id, 'dialog_size': 'medium'},
        }

    def action_mark_contract_signed(self):
        """🏆 Đánh dấu đã ký HĐ thực sự (sau khi NV gặp KH ký xong + nhận cọc)."""
        self.ensure_one()
        if self.vd_contract_signed:
            raise UserError(_('Hợp đồng đã được đánh dấu ký rồi.'))
        self.with_context(mail_notrack=True).write({
            'vd_contract_signed': True,
            'vd_contract_sign_date': fields.Date.context_today(self),
        })
        self.message_post(subtype_xmlid='mail.mt_note', body=_(
            '🏆 <b>ĐÃ KÝ HỢP ĐỒNG</b> chính thức ngày <b>%s</b>!'
        ) % fields.Date.context_today(self).strftime('%d/%m/%Y'))
        return {
            'type': 'ir.actions.client', 'tag': 'reload',
            'effect': {
                'fadeout': 'slow',
                'message': '🏆 Đã ghi nhận ký HĐ thành công!',
                'type': 'rainbow_man',
            },
        }

    def action_hangup_active(self):
        """End the lead's currently active call. Stays on the same form.
        Cleanup BROWSER-side trước (Web SDK) qua client action, rồi server REST.
        """
        self.ensure_one()
        if self.vd_active_call_id:
            self.vd_active_call_id.action_hangup()
        # Trigger browser hangup để đóng WebRTC peer (per Stringee doc step 6)
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_stringee_hangup',
        }

    def action_view_calls(self):
        """Open call history for this lead in a modal dialog.

        Per-lead context: rows đều thuộc 1 lead + chủ yếu 1 NV phụ trách →
        flag `vd_hide_lead_col` + `vd_hide_user_col` để list view ẩn 2 cột này
        cho khỏi redundant + đỡ chật. Action menu company-wide không set flag
        nên vẫn giữ cột user_id/lead_id.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lịch sử cuộc gọi — %s') % (self.name or ''),
            'res_model': 'stringee.call',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'create': False,
                'dialog_size': 'fullscreen',
                'vd_hide_lead_col': True,
                'vd_hide_user_col': True,
                'vd_call_history_popup': True,  # cho CSS target popup này
            },
        }

    def action_zalo_mark_step(self):
        """Toggle 1 bước checklist Zalo (chưa → set giờ hiện tại; đã → bỏ).
        Bước truyền qua context {'zalo_step': 'group'|'quote'|'model'|'problem'}."""
        self.ensure_one()
        fmap = {
            'group': 'vd_zalo_step_group',
            'quote': 'vd_zalo_step_quote',
            'model': 'vd_zalo_step_model',
            'problem': 'vd_zalo_step_problem',
        }
        fname = fmap.get(self.env.context.get('zalo_step'))
        if fname:
            self[fname] = False if self[fname] else fields.Datetime.now()

    def action_open_zalo_group(self):
        """Mở nhóm Zalo trong tab mới (act_url) — NV/leader bấm vào nhóm nhanh."""
        self.ensure_one()
        url = (self.vd_zalo_group_url or '').strip()
        if not url:
            raise UserError(_('Chưa có link nhóm Zalo. Dán link vào ô bên cạnh trước.'))
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def action_view_calls_post_quote(self):
        """Popup lịch sử cuộc gọi CHỈ tính từ ngày làm báo giá thành công
        (vd_quote_created_date). Dùng chung view stringee.call (có widget
        vd_audio_player để nghe ghi âm) y như action_view_calls."""
        self.ensure_one()
        domain = [('lead_id', '=', self.id)]
        if self.vd_quote_created_date:
            domain.append(('start_time', '>=', self.vd_quote_created_date))
        since_str = (
            fields.Datetime.context_timestamp(self, self.vd_quote_created_date).strftime('%d/%m/%Y')
            if self.vd_quote_created_date else ''
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cuộc gọi sau báo giá (từ %s) — %s') % (since_str, self.name or ''),
            'res_model': 'stringee.call',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'create': False,
                'dialog_size': 'fullscreen',
                'vd_hide_lead_col': True,
                'vd_hide_user_col': True,
                'vd_call_history_popup': True,
            },
        }

    # ---------- Dashboard data ----------

    def _dashboard_is_manager(self):
        """Admin / Sales Manager / Settings → xem được data của TẤT CẢ NV."""
        u = self.env.user
        return (
            u.has_group('sales_team.group_sale_manager')
            or u.has_group('base.group_system')
            or u._is_admin()
        )

    def _dashboard_is_team_leader(self):
        """Trưởng nhóm (KHÔNG phải manager) → xem data NV TRONG NHÓM (cùng phòng
        ban). Manager (Giám đốc/Admin) trả False ở đây vì họ đã xem toàn bộ."""
        return (
            self.env.user.has_group('vd_crm_lead.vd_crm_group_team_leader')
            and not self._dashboard_is_manager()
        )

    def _dashboard_team_member_ids(self):
        """IDs các NV cùng PHÒNG BAN với user hiện tại (gồm chính họ).
        Phòng ban = _vd_team_label_for (ưu tiên thẻ vd_team, fallback tiền tố tên)."""
        me = self.env.user
        label = self._vd_team_label_for(me)
        users = self.env['res.users'].sudo().search([
            ('share', '=', False), ('active', '=', True)])
        ids = [u.id for u in users if self._vd_team_label_for(u) == label]
        if me.id not in ids:
            ids.append(me.id)
        return ids

    def _can_see_company_trash(self):
        """CHỈ Admin + Giám đốc được xem THÙNG RÁC CÔNG TY (KH đã duyệt hủy).
        Khác _dashboard_is_manager (rộng hơn, gồm sale_manager thường)."""
        u = self.env.user
        return (
            u.has_group('base.group_system')
            or u.has_group('vd_crm_lead.vd_crm_group_deputy_director')
        )

    def _dashboard_resolve_scope(self, user_id):
        """Trả về (user_record_or_None, scope_label, lead_user_domain, call_user_domain).
        - user_id = 'all' hoặc 0 → toàn bộ NV (manager) / CHÍNH MÌNH (trưởng nhóm)
        - user_id = int → 1 NV cụ thể (manager: mọi NV; trưởng nhóm: NV trong nhóm;
          NV thường: chỉ chính họ)
        - user_id = None → mặc định: manager → 'all'; trưởng nhóm + NV → chính họ

        Trưởng nhóm: dashboard MẶC ĐỊNH là CỦA CHÍNH HỌ (như 1 NV) — chọn xem NV
        trong nhóm qua bảng "nhân viên dưới quyền" (không có chế độ gộp nhóm).
        """
        is_manager = self._dashboard_is_manager()
        is_team_leader = self._dashboard_is_team_leader()
        team_ids = self._dashboard_team_member_ids() if is_team_leader else []

        # Chuẩn hoá input: manager → 'all'; trưởng nhóm/NV → chính mình.
        if user_id in ('all', 0, '0') or user_id is None:
            user_id = 'all' if is_manager else self.env.user.id

        if user_id == 'all':
            # Manager: toàn bộ NV (lead đã giao).
            return (
                None, 'Tất cả nhân viên',
                [('user_id', '!=', False)],
                [('user_id', '!=', False)],
            )

        # 1 NV cụ thể.
        target = self.env['res.users'].browse(int(user_id))
        # NV thường không xem NV khác; trưởng nhóm chỉ xem NV TRONG NHÓM.
        if not is_manager:
            if is_team_leader:
                if target.id not in team_ids:
                    target = self.env.user
            elif target.id != self.env.user.id:
                target = self.env.user
        return (
            target, target.name,
            [('user_id', '=', target.id)],
            [('user_id', '=', target.id)],
        )

    @api.model
    def vd_dashboard_active_calls(self):
        """User spec 2026-05-29: trả về trạng thái cuộc gọi LIVE của từng NV.
        Frontend poll mỗi 5s → update badge "Đang gọi" / "Không gọi" mỗi row.

        Returns: dict {user_id: {'is_calling': bool, 'since_min': int, 'state': str}}
        User spec round 8: "cứ bấm gọi = đang gọi" — KHÔNG cần đợi ringing/answered.
        Bao gồm CẢ draft, initiated (vừa tạo call record) → ringing → answered.
        Filter qua end_time IS NULL + start ≤ 30 phút để loại record cũ stuck.
        """
        from datetime import timedelta as _td
        Call = self.env['stringee.call'].sudo()
        now = fields.Datetime.now()
        threshold = now - _td(minutes=30)
        active = Call.search([
            ('state', 'in', ['draft', 'initiated', 'ringing', 'answered']),
            ('end_time', '=', False),
            ('start_time', '>=', threshold),
            ('user_id', '!=', False),
        ])
        result = {}
        for c in active:
            uid = c.user_id.id
            since_min = int((now - c.start_time).total_seconds() // 60) if c.start_time else 0
            existing = result.get(uid)
            # Nếu NV có nhiều call đồng thời (rare), lấy cái latest
            if not existing or since_min < existing['since_min']:
                result[uid] = {
                    'is_calling': True,
                    'since_min': since_min,
                    'state': c.state,
                }
        return result

    @api.model
    def vd_dashboard_help_live(self):
        """User spec 2026-06-01: trạng thái 🆘 CẦN HỖ TRỢ LIVE của từng NV để
        admin poll mỗi 5s — NV bấm SOS là hiện ngay, KHÔNG cần F5.

        Returns: {user_id: {'count', 'waiting', 'leads': [{lead_id,name,phone,
                  scope,status,problems}]}}  (≤3 KH/NV, waiting lên trước).
        """
        if not self._dashboard_is_manager():
            return {}
        today = fields.Date.context_today(self)
        from collections import defaultdict as _dd
        leads = self.search([
            ('vd_need_help', '=', True),
            ('active', '=', True),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
        ], order='vd_need_help_at asc')
        result = {}
        for l in leads:
            if not l._vd_need_help_active(today):
                continue
            uid = l.user_id.id
            if not uid:
                continue
            e = result.setdefault(uid, {'count': 0, 'waiting': 0, 'leads': []})
            e['count'] += 1
            status = l.vd_help_status or 'waiting'
            if status == 'waiting':
                e['waiting'] += 1
            if len(e['leads']) < 3:
                open_probs = l.vd_lead_problem_ids.filtered(
                    lambda p: p.status in ('open', 'in_progress')
                )
                e['leads'].append({
                    'lead_id': l.id,
                    'name': l.name or l.partner_name or 'KH',
                    'phone': l.phone or '',
                    'scope': l.vd_need_help_scope or 'today',
                    'status': status,
                    'problems': [{
                        'name': (p.tag_id.name if p.tag_id else p.name) or 'Vấn đề',
                        'icon': p.tag_id.icon if p.tag_id else '🔸',
                        'status': p.status,
                    } for p in open_probs[:3]],
                })
        for e in result.values():
            e['leads'].sort(key=lambda x: x['status'] == 'helping')
        return result

    @api.model
    def dashboard_users(self, team_scope=False):
        """Danh sách NV để manager chọn xem dashboard theo từng NV.

        team_scope=True (Giám đốc ở chế độ "CÁ NHÂN"): bó về NV cùng PHÒNG BAN
        với người xem (giống trưởng nhóm) thay vì toàn công ty.

        Mỗi NV kèm 2 số liệu cho dropdown CHUYỂN KH:
          - new_not_called: KH mới CHƯA gọi cuộc nào (call_count = 0).
          - new_total: tổng KH trong bảng KHÁCH MỚI = bucket KHÁCH MỚI TRỪ
            nhóm 'CHƯA GỌI ĐƯỢC' (unreachable, call_count >= 3) → khớp đúng
            con số hiển thị ở bảng KHÁCH MỚI trên UI (leadsNoProblems).
        """
        is_manager = self._dashboard_is_manager()
        is_team_leader = self._dashboard_is_team_leader()
        if not is_manager and not is_team_leader:
            u = self.env.user
            return [{'id': u.id, 'name': u.name}]
        from collections import defaultdict
        # Giám đốc chế độ CÁ NHÂN cũng bó về phòng ban mình (như trưởng nhóm).
        scope_team = is_team_leader or (is_manager and team_scope)
        user_domain = [('share', '=', False), ('active', '=', True)]
        if scope_team:
            # Trưởng nhóm / Giám đốc-CÁ NHÂN: chỉ NV TRONG NHÓM (cùng phòng ban).
            user_domain.append(('id', 'in', self._dashboard_team_member_ids()))
        users = self.env['res.users'].search(user_domain, order='name')
        Lead = self.env['crm.lead'].sudo()
        # NV có ít nhất 1 lead + TỔNG KH/NV (1 query read_group).
        groups = Lead.read_group([('user_id', '!=', False)], ['user_id'], ['user_id'])
        user_ids_with_lead = {g['user_id'][0] for g in groups if g['user_id']}
        total_by_user = {
            g['user_id'][0]: (g.get('user_id_count') or g.get('__count') or 0)
            for g in groups if g['user_id']
        }
        # Manager: chỉ NV có lead. Trưởng nhóm / GĐ-CÁ NHÂN: LIỆT KÊ ĐỦ NV trong
        # nhóm (kể cả 0 KH).
        listing = users if scope_team else users.filtered(
            lambda u: u.id in user_ids_with_lead)
        # Toàn bộ bucket KHÁCH MỚI của mọi NV — 1 query.
        all_new = Lead.search(
            self._dashboard_new_bucket_domain([('user_id', '!=', False)]))
        new_by_user = defaultdict(list)
        for l in all_new:
            new_by_user[l.user_id.id].append(l)
        # 'CHƯA GỌI ĐƯỢC' ∩ bucket mới = unreachable trên lead call_count >= 3.
        unreach_cand = all_new.filtered(lambda l: (l.call_count or 0) >= 3)
        unreachable_ids = set(self._dashboard_unreachable_ids(unreach_cand, limit=100000))
        result = []
        for u in listing:
            leads = new_by_user.get(u.id, [])
            not_called = sum(1 for l in leads if (l.call_count or 0) == 0)
            in_table = sum(1 for l in leads if l.id not in unreachable_ids)
            result.append({
                'id': u.id, 'name': u.name, 'login': u.login,
                'total': total_by_user.get(u.id, 0),
                'new_not_called': not_called,
                'new_total': in_table,
            })
        return result

    @api.model
    def dashboard_bulk_reassign(self, lead_ids, target_user_id):
        """Chuyển HÀNG LOẠT KH (lead_ids) sang NV target_user_id.

        Quyền: chỉ admin + role có can_reassign_lead=True (người chia số /
        giám đốc). Dùng can_user_reassign (KHÔNG chỉ is_manager) để khớp đúng
        yêu cầu: admin + người chia số hàng ngày + giám đốc.

        Trả về số KH thực sự đã chuyển (bỏ qua KH vốn đã thuộc target).
        """
        from odoo.exceptions import AccessError
        role_model = self.env['vd.crm.role.config'].sudo()
        if not (self.env.user._is_superuser() or role_model.can_user_reassign(self.env.user)):
            raise AccessError(_(
                'Bạn không có quyền chuyển KH cho NV khác. '
                'Chỉ Admin, người chia số hoặc giám đốc mới được làm.'
            ))
        try:
            target_id = int(target_user_id)
        except (TypeError, ValueError):
            target_id = 0
        ids = [int(i) for i in (lead_ids or [])]
        if not ids or not target_id:
            return 0
        target = self.env['res.users'].sudo().browse(target_id)
        if not target.exists():
            raise UserError(_('Nhân viên nhận không tồn tại.'))
        leads = self.sudo().browse(ids).exists()
        # Bỏ qua KH đã thuộc về target (tránh write thừa)
        leads = leads.filtered(lambda l: l.user_id.id != target_id)
        if leads:
            # vd_skip_reassign_check: đã tự kiểm tra quyền ở trên → bỏ qua
            # check lặp trong write(). mail_notrack tránh lỗi gửi email tracking.
            leads.with_context(
                vd_skip_reassign_check=True,
                mail_notrack=True,
                tracking_disable=True,
            ).write({'user_id': target_id})
        return len(leads)

    @api.model
    def dashboard_bulk_distribute(self, assignments):
        """CHIA SỐ: mỗi KH chuyển sang 1 NV KHÁC NHAU (user spec 2026-06-08).

        assignments = [[lead_id, user_id], ...] — chỉ ĐỔI user_id từng KH, GIỮ
        NGUYÊN mọi data bên trong (lịch sử gọi, vấn đề, báo giá...). Cùng quyền
        + cùng cách write như dashboard_bulk_reassign.

        Trả về số KH thực sự đã chuyển.
        """
        from collections import defaultdict
        from odoo.exceptions import AccessError
        role_model = self.env['vd.crm.role.config'].sudo()
        if not (self.env.user._is_superuser() or role_model.can_user_reassign(self.env.user)):
            raise AccessError(_(
                'Bạn không có quyền chia số cho NV khác. '
                'Chỉ Admin, người chia số hoặc giám đốc mới được làm.'
            ))
        by_user = defaultdict(list)
        for pair in (assignments or []):
            try:
                lid = int(pair[0])
                uid = int(pair[1])
            except (TypeError, ValueError, IndexError):
                continue
            if lid and uid:
                by_user[uid].append(lid)
        if not by_user:
            return 0
        # Gom theo NV để write 1 lần/NV (đổi đúng user_id, KHÔNG đụng field khác).
        valid_uids = set(self.env['res.users'].sudo().browse(list(by_user)).exists().ids)
        # CHẶN CHIA SỐ (user spec 2026-06-12): TỔNG dự kiến KH mới CHƯA gọi của 1
        # NV không được vượt ngưỡng (đang tồn + số chưa gọi sắp chia vào). Vi phạm
        # → chặn cả cụm cho NV đó (buộc chọn NV khác). Frontend đã chặn, đây là rào.
        threshold = self._vd_distribute_block_threshold()
        if threshold > 0:
            current = self._vd_uncalled_new_count_map(list(valid_uids))
            Users = self.env['res.users'].sudo()
            over = []
            for uid, lids in by_user.items():
                if uid not in valid_uids:
                    continue
                incoming = self.sudo().browse(lids).exists().filtered(
                    lambda l: l.user_id.id != uid and (l.call_count or 0) == 0)
                projected = current.get(uid, 0) + len(incoming)
                if projected > threshold:
                    cap = max(0, threshold - current.get(uid, 0))
                    over.append('• %s — đang tồn %d KH mới chưa gọi, chỉ nhận thêm '
                                '%d (ngưỡng %d)' % (
                                    Users.browse(uid).name, current.get(uid, 0),
                                    cap, threshold))
            if over:
                raise UserError(_(
                    'KHÔNG chia được — các NV sau sẽ VƯỢT ngưỡng khách mới chưa '
                    'gọi:\n%s\n\nChọn NV khác cho các số dư (gọi bớt khách cũ để '
                    'mở thêm chỗ).'
                ) % '\n'.join(over))
        moved = 0
        for uid, lids in by_user.items():
            if uid not in valid_uids:
                continue
            leads = self.sudo().browse(lids).exists().filtered(
                lambda l: l.user_id.id != uid)
            if leads:
                leads.with_context(
                    vd_skip_reassign_check=True,
                    mail_notrack=True,
                    tracking_disable=True,
                ).write({'user_id': uid})
                moved += len(leads)
        return moved

    # ========================================================================
    # YÊU CẦU TÌM VẤN ĐỀ — cảnh báo + auto-khoá (user spec 2026-06-01)
    # ========================================================================
    @api.model
    def _vd_problem_find_config(self):
        """(enabled, pct_threshold, grace_days) đọc từ ir.config_parameter.
        Cấu hình ở trang Cài đặt (res.config.settings)."""
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('vd_crm_lead.problem_find_enabled', '1') in ('1', 'True', 'true')
        try:
            pct = int(ICP.get_param('vd_crm_lead.problem_find_pct', 20) or 20)
        except (TypeError, ValueError):
            pct = 20
        try:
            grace = int(ICP.get_param('vd_crm_lead.problem_find_grace_days', 3) or 3)
        except (TypeError, ValueError):
            grace = 3
        return enabled, pct, grace

    def _vd_pf_table_cfg(self, key):
        """(pct, grace) RIÊNG cho 'urgent' / 'xlvd' (user spec 2026-06-05).
        Fallback: tham số per-bảng -> tham số chung cũ -> default."""
        ICP = self.env['ir.config_parameter'].sudo()
        _en, base_pct, base_grace = self._vd_problem_find_config()

        def _i(k, d):
            try:
                return int(ICP.get_param(k, d) or d)
            except (TypeError, ValueError):
                return d

        pct = _i('vd_crm_lead.problem_find_%s_pct' % key, base_pct)
        grace = _i('vd_crm_lead.problem_find_%s_grace' % key, base_grace)
        return pct, grace

    def _vd_urgent_tag_id(self):
        tag = self.env.ref('vd_crm_lead.nego_problem_urgent_construction',
                           raise_if_not_found=False)
        return tag.id if tag else 0

    def _vd_lead_has_real_problem(self, urgent_tag_id):
        """KH 'đã có vấn đề' = có >=1 vấn đề open/in_progress NGOÀI tag 'Thi công
        gấp' (khớp đúng badge ⚠️ TÌM VẤN ĐỀ ở dashboard = problems_non_urgent)."""
        self.ensure_one()
        return bool(self.vd_lead_problem_ids.filtered(
            lambda p: p.status in ('open', 'in_progress')
            and not (p.tag_id and p.tag_id.id == urgent_tag_id)
        ))

    def _vd_status_label_short(self):
        """Nhãn trạng thái KH ngắn cho bảng ghi âm (hover tên NV):
        Huỷ / Thi công gấp / Xử lý vấn đề / Đang tham khảo / Khách mới."""
        self.ensure_one()
        if self.vd_cancel_state == 'approved' or not self.active or self.stage_is_lost:
            return {'label': 'Huỷ', 'cls': 'huy'}
        urgent_tag_id = self._vd_urgent_tag_id()
        has_urgent = bool(self.vd_lead_problem_ids.filtered(
            lambda p: p.status in ('open', 'in_progress')
            and p.tag_id and p.tag_id.id == urgent_tag_id))
        if has_urgent:
            return {'label': 'Thi công gấp', 'cls': 'urgent'}
        if self._vd_lead_has_real_problem(urgent_tag_id):
            return {'label': 'Xử lý vấn đề', 'cls': 'xlvd'}
        if self.stage_code in ('quote', 'negotiate', 'won'):
            return {'label': 'Đang tham khảo', 'cls': 'ref'}
        return {'label': 'Khách mới', 'cls': 'new'}

    @api.model
    def _vd_problem_find_stats(self, domain_user):
        """Đếm % KH 'chưa có vấn đề' RIÊNG cho từng bảng THI CÔNG GẤP + XỬ LÝ
        VẤN ĐỀ (dùng đúng tập lead như 2 hàm dashboard_leads_* tương ứng).
        Trả: {enabled, threshold_pct, urgent:{...}, xlvd:{...}, violating}."""
        enabled, pct, _grace = self._vd_problem_find_config()
        urgent_tag_id = self._vd_urgent_tag_id()

        # THI CÔNG GẤP = _dashboard_urgent_construction_ids
        urgent_leads = self.browse(self._dashboard_urgent_construction_ids(domain_user))
        # XỬ LÝ VẤN ĐỀ = mirror dashboard_leads_with_problems
        mid_stage_ids = self.env['crm.stage'].search([('code', 'in', ['quote', 'negotiate'])]).ids
        xlvd_leads = self.browse()
        if mid_stage_ids:
            xlvd_leads = self.search(domain_user + [
                ('stage_id', 'in', mid_stage_ids),
                ('active', '=', True),
                ('vd_intake_complete', '=', True),
                ('vd_intake_locked', '=', True),
                ('id', 'not in', urgent_leads.ids),
            ])

        def _tbl(leads, tbl_pct):
            total = len(leads)
            no_problem = sum(
                1 for l in leads if not l._vd_lead_has_real_problem(urgent_tag_id)
            )
            ratio = (no_problem / total * 100.0) if total else 0.0
            return {
                'total': total,
                'no_problem': no_problem,
                'pct': round(ratio),
                'threshold_pct': tbl_pct,
                'over': bool(enabled and total > 0 and ratio > tbl_pct),
            }

        u_pct, _ug = self._vd_pf_table_cfg('urgent')
        x_pct, _xg = self._vd_pf_table_cfg('xlvd')
        urgent = _tbl(urgent_leads, u_pct)
        xlvd = _tbl(xlvd_leads, x_pct)
        return {
            'enabled': enabled,
            'threshold_pct': pct,
            'urgent': urgent,
            'xlvd': xlvd,
            'violating': urgent['over'] or xlvd['over'],
        }

    @api.model
    def _vd_apply_problem_lock(self, user, grace=None, now=None, stats=None):
        """Đánh giá + áp/gỡ khoá 2 bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ cho 1 NV
        (user spec 2026-06-05: "bảng nào vi phạm thì khoá bảng đó"), mốc gia hạn
        RIÊNG từng bảng.

        - Vượt ngưỡng % chưa-có-vấn-đề + quá hạn gia hạn → khoá ĐÚNG bảng đó.
        - Hết vượt ngưỡng ở bảng nào → gỡ + reset mốc bảng đó.
        - CHỈ ADMIN gỡ thủ công (cron không tự gỡ khi NV vẫn vượt ngưỡng — vì
          bảng bị khoá NV không bấm vào tạo vấn đề được). Admin gỡ -> còn 1 ngày
          (xem vd_admin_clear_problem_lock) rồi tự khoá lại nếu vẫn vi phạm.
        Dùng chung cho CRON (mọi NV) và LIVE (1 NV khi mở dashboard)."""
        enabled, _pct, g = self._vd_problem_find_config()
        grace = g if grace is None else grace
        now = now or fields.Datetime.now()
        if enabled:
            stats = stats or self._vd_problem_find_stats([('user_id', '=', user.id)])
        vals = {}
        any_lock = False
        for key in ('urgent', 'xlvd'):
            lock_f = 'vd_pf_lock_' + key
            since_f = 'vd_pf_since_' + key
            over = bool(enabled and stats and stats[key]['over'])
            if not over:
                # hết vượt ngưỡng (hoặc tắt tính năng) -> gỡ + reset mốc bảng đó
                if user[lock_f]:
                    vals[lock_f] = False
                if user[since_f]:
                    vals[since_f] = False
                continue
            _pct_k, grace_k = self._vd_pf_table_cfg(key)   # grace RIÊNG từng bảng
            since = user[since_f]
            if not since:
                since = now
                vals[since_f] = now
            overdue = (now - since).total_seconds() >= grace_k * 86400
            if overdue != user[lock_f]:
                vals[lock_f] = overdue
            any_lock = any_lock or overdue
        # cờ tổng (tương thích chỗ khác) + mốc tổng cho hiển thị days_left
        if bool(any_lock) != bool(user.vd_problem_lock):
            vals['vd_problem_lock'] = bool(any_lock)
        if vals:
            user.sudo().write(vals)   # LIVE: NV không có quyền ghi res.users

    @api.model
    def _vd_pf_days_left(self, since, grace, now=None):
        """Số ngày còn lại trước khi khoá, tính từ mốc `since` (None -> grace)."""
        if not since:
            return grace
        now = now or fields.Datetime.now()
        elapsed = (now - since).total_seconds() / 86400.0
        return max(0, int(round(grace - elapsed + 0.4999)))

    @api.model
    def _vd_cron_notify_overdue_problems(self):
        """CRON hằng ngày: báo TRƯỞNG PHÒNG các vấn đề KH ĐÃ QUÁ HẠN xử lý mà
        chưa giải quyết (user spec 2026-06-06). Mỗi vấn đề chỉ báo 1 lần
        (overdue_notified) — gia hạn/sửa hạn sẽ reset cờ để báo lại nếu lại quá."""
        Problem = self.env['vd.lead.problem'].sudo()
        now = fields.Datetime.now()
        overdue = Problem.search([
            ('deadline', '!=', False),
            ('deadline', '<', now),
            ('status', '!=', 'resolved'),
            ('overdue_notified', '=', False),
        ])
        for p in overdue:
            days = (now - p.deadline).days
            p._vd_notify_leaders(_(
                '⏰ QUÁ HẠN xử lý: vấn đề "%s" của KH %s (NV %s) đã quá hạn %d '
                'ngày mà chưa giải quyết.'
            ) % (p.name, p.lead_id.name or '', p.lead_id.user_id.name or '?', days))
            p.overdue_notified = True

    @api.model
    def _vd_cron_eval_problem_find_lock(self):
        """CRON hằng ngày: đánh giá khoá per-bảng cho mọi NV sales."""
        enabled, _pct, grace = self._vd_problem_find_config()
        Users = self.env['res.users'].sudo()
        sales_users = Users.search([
            ('share', '=', False),
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ])
        now = fields.Datetime.now()
        for u in sales_users:
            self._vd_apply_problem_lock(u, grace=grace, now=now)
        return True

    @api.model
    def vd_admin_clear_problem_lock(self, user_id, which='all'):
        """ADMIN gỡ khoá bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ cho 1 NV (2026-06-05).
        which: 'urgent' | 'xlvd' | 'all'.

        Gỡ = mở NHƯNG chỉ 1 NGÀY: đặt mốc gia hạn của bảng đó = now-(grace-1)d
        nên nếu NV vẫn không xử lý thì sau 1 ngày cron/live TỰ KHOÁ LẠI."""
        from datetime import timedelta
        # User spec 2026-06-15: TRƯỞNG NHÓM cũng được gỡ khoá (giống admin) — nhưng
        # CHỈ cho NV TRONG NHÓM mình.
        if not self._dashboard_is_manager():
            if not (self._dashboard_is_team_leader()
                    and int(user_id) in self._dashboard_team_member_ids()):
                raise AccessError(_('Chỉ quản lý/admin hoặc trưởng nhóm (NV trong nhóm) được gỡ khoá.'))
        u = self.env['res.users'].sudo().browse(int(user_id))
        if not u.exists():
            return False
        _enabled, _pct, grace = self._vd_problem_find_config()
        # Mốc lùi về quá khứ (grace-1) ngày -> còn đúng 1 ngày là tới hạn.
        reprieve = fields.Datetime.now() - timedelta(days=max(0, grace - 1))
        vals = {}
        if which in ('urgent', 'all'):
            vals['vd_pf_lock_urgent'] = False
            vals['vd_pf_since_urgent'] = reprieve
        if which in ('xlvd', 'all'):
            vals['vd_pf_lock_xlvd'] = False
            vals['vd_pf_since_xlvd'] = reprieve
        # cờ tổng = còn khoá bảng nào không
        still_u = (which == 'xlvd') and u.vd_pf_lock_urgent
        still_x = (which == 'urgent') and u.vd_pf_lock_xlvd
        vals['vd_problem_lock'] = bool(still_u or still_x)
        u.write(vals)
        return True

    @api.model
    def _vd_distribution_report(self, pancake=True):
        """Báo cáo CHIA SỐ (user spec 2026-06-05). pancake=True → KH Pancake tự
        động; False → KH nhập TAY.

        Cửa sổ "hôm nay" theo MỐC 15h: tính từ 15h ngày D đến 24h ngày D, hiển
        thị (kèm cảnh báo) tới 15h ngày D+1 thì reset. Trước 15h hôm nay → đang
        xem lô NGÀY HÔM QUA (label 'Hôm qua'); từ 15h → 'Hôm nay'.

        Mỗi section: total, eligible, uneven, rows[{name,count,eval}] — eval ∈
        few/ok/many; rows sắp NV ÍT số nhất lên đầu."""
        import pytz
        from datetime import datetime as _dt, time as _time, timedelta as _tdd
        Users = self.env['res.users'].sudo()
        salesman_gid = self.env.ref('sales_team.group_sale_salesman').id
        sales = Users.search([
            ('share', '=', False), ('active', '=', True),
            ('groups_id', 'in', salesman_gid),
        ])
        # CHỈ tính NV THẬT: loại admin / quản lý / trưởng phòng (user 2026-06-05).
        leader_gid = self.env.ref('vd_crm_lead.vd_crm_group_team_leader', raise_if_not_found=False)
        mgr_gid = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)

        def _is_real_nv(u):
            # NV THẬT = không phải admin/quản lý/trưởng nhóm. KHÔNG lọc theo cờ
            # vd_can_receive_pancake ở đây nữa (user spec 2026-06-23): NV bị TẮT
            # vẫn phải HIỆN trong báo cáo (xám + nút BẬT lại), chỉ là không nhận số.
            if u._is_admin() or u.has_group('base.group_system'):
                return False
            if mgr_gid and u.has_group('sales_team.group_sale_manager'):
                return False
            if leader_gid and u.has_group('vd_crm_lead.vd_crm_group_team_leader'):
                return False
            return True

        # TẤT CẢ NV thật (kể cả đang TẮT nhận) → hiển thị + có nút bật/tắt.
        all_nv = sales.filtered(_is_real_nv)
        # NV đang BẬT nhận = "đang trong vòng chia" → dùng để tính cân bằng/eligible.
        eligible = all_nv.filtered('vd_can_receive_pancake')
        can_recv = {u.id: bool(u.vd_can_receive_pancake) for u in all_nv}
        name_by = {u.id: (u.name or '') for u in sales}
        src_dom = [('vd_pancake_page_id', '!=', False)] if pancake \
            else [('vd_pancake_page_id', '=', False)]
        # Map page_id -> platform để tách cột TikTok / Facebook (user spec 2026-06-23).
        plat_by_page = {}
        if pancake:
            for pg in self.env['vd.pancake.page'].sudo().search([]):
                plat_by_page[pg.id] = pg.platform or 'other'

        # HIỂN THỊ tách bạch HÔM NAY và HÔM QUA (cả ngày 0h→24h theo giờ VN) để
        # GĐ/TP xem được NGAY hôm nay có bao nhiêu số + chia cho ai, không phải
        # chờ tới mốc 15h mới thấy (user spec 2026-06-24). Đếm theo create_date.
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        now_vn = pytz.utc.localize(fields.Datetime.now()).astimezone(vn)
        today_d = now_vn.date()
        yest_d = today_d - _tdd(days=1)

        def _utc(d, t):
            return vn.localize(_dt.combine(d, t)).astimezone(pytz.utc).replace(tzinfo=None)

        today_since = _utc(today_d, _time(0, 0))                    # 0h hôm nay
        today_until = _utc(today_d + _tdd(days=1), _time(0, 0))     # 24h hôm nay
        yest_since = _utc(yest_d, _time(0, 0))                      # 0h hôm qua
        yest_until = today_since                                    # = 0h hôm nay
        month_since = _utc(now_vn.date().replace(day=1), _time(0, 0))
        month_until = fields.Datetime.now() + _tdd(days=1)

        n = len(eligible)
        # MỐC ĐỦ KHÁCH/NGÀY (user spec 2026-06-20): mặc định 5 khách FB/TikTok/NV/ngày.
        daily_target = int(self.env['ir.config_parameter'].sudo().get_param(
            'vd_crm_lead.daily_pancake_target', 5) or 5)

        Conv = self.env['vd.pancake.conversation'].sudo()

        def _build(since, until, eval_even, label):
            leads = self.sudo().search(src_dom + [
                ('create_date', '>=', since),
                ('create_date', '<', until),
                ('user_id', '!=', False),
            ])
            per = {}        # tổng theo NV
            per_tt = {}     # TikTok theo NV
            per_fb = {}     # Facebook theo NV
            for l in leads:
                uid = l.user_id.id
                per[uid] = per.get(uid, 0) + 1
                plat = plat_by_page.get(l.vd_pancake_page_id.id) if l.vd_pancake_page_id else None
                if plat == 'tiktok':
                    per_tt[uid] = per_tt.get(uid, 0) + 1
                elif plat == 'facebook':
                    per_fb[uid] = per_fb.get(uid, 0) + 1
            total = sum(per.values())
            # TỔNG lead TẠO trong khoảng (kể cả đã GỘP trùng SĐT / chưa gán NV) —
            # để giải thích vì sao "số" (lead active còn lại) ÍT hơn "lượt cho số"
            # ở ô tỷ lệ phía trên: chênh lệch = SĐT trùng đã gộp + lead chưa gán.
            created_all = self.sudo().with_context(active_test=False).search_count(
                src_dom + [('create_date', '>=', since), ('create_date', '<', until)])
            merged = max(0, created_all - total)
            # Cân bằng chỉ tính trên NV ĐANG BẬT nhận (eligible) — NV tắt cố ý = 0.
            fair_low = total // n if n else 0
            fair_high = -(-total // n) if n else 0   # ceil
            rows = []
            under_count = 0
            for u in all_nv:
                c = per.get(u.id, 0)
                # Kênh THỦ CÔNG không phụ thuộc cờ Pancake → coi như luôn "bật".
                on = can_recv.get(u.id, True) if pancake else True
                ev = 'few' if c < fair_low else ('many' if c > fair_high else 'ok')
                # NV đang TẮT → không tính "chưa đủ" (cố ý không nhận).
                under = on and (c < daily_target)
                if under:
                    under_count += 1
                rows.append({'uid': u.id,
                             'name': name_by.get(u.id) or 'NV #%s' % u.id,
                             'count': c,
                             'tiktok': per_tt.get(u.id, 0),
                             'facebook': per_fb.get(u.id, 0),
                             'eval': ev, 'under_target': under,
                             'can_receive': on})
            # NV TẮT xuống cuối; trong cùng nhóm thì ÍT số nhất lên đầu.
            rows.sort(key=lambda r: (not r['can_receive'], r['count'], r['name']))
            uneven = False
            if eval_even and total > 0 and n:
                counts = [per.get(u.id, 0) for u in eligible]
                uneven = (max(counts) - min(counts)) > 1
            block = {'total': total, 'nv_count': len(per), 'eligible': n,
                     'created_all': created_all, 'merged': merged,
                     'rows': rows, 'uneven': uneven, 'label': label,
                     'target': daily_target, 'under_count': under_count}
            # TỶ LỆ XIN SỐ (chỉ kênh Pancake): hội thoại có SĐT / tổng hội thoại.
            if pancake:
                block['rate'] = Conv._vd_rate_block(
                    fields.Datetime.to_string(since),
                    fields.Datetime.to_string(until))
            return block

        result = {
            'today': _build(today_since, today_until, True, 'Hôm nay'),
            'yesterday': _build(yest_since, yest_until, True, 'Hôm qua'),
            'month': _build(month_since, month_until, False, 'Tháng này'),
        }
        # TỶ LỆ XIN SỐ 7 NGÀY GẦN NHẤT (chỉ kênh Pancake) — ô trên cùng báo cáo.
        if pancake:
            wd = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']  # weekday() 0..6
            rate7 = []
            for i in range(6, -1, -1):           # 6 ngày trước → hôm nay
                d = now_vn.date() - _tdd(days=i)
                since = _utc(d, _time(0, 0))
                until = _utc(d + _tdd(days=1), _time(0, 0))
                blk = Conv._vd_rate_block(
                    fields.Datetime.to_string(since),
                    fields.Datetime.to_string(until))
                rate7.append({
                    'label': wd[d.weekday()],
                    'day': '%d/%d' % (d.day, d.month),
                    'is_today': (i == 0),
                    'pct': blk['all']['pct'],
                    'with_phone': blk['all']['with_phone'],
                    'total': blk['all']['total'],
                    'tiktok': blk['tiktok'],
                    'facebook': blk['facebook'],
                })
            result['rate7'] = rate7
        return result

    @api.model
    def vd_pancake_dist_reports(self):
        """Wrapper PUBLIC cho JS: trả lại 2 báo cáo chia số sau khi bật/tắt NV."""
        return {
            'pancake_report': self._vd_distribution_report(pancake=True),
            'manual_report': self._vd_distribution_report(pancake=False),
        }

    def _vd_inbound_today_chips(self, call_user_domain, limit=400):
        """KHÁCH GỌI ĐẾN của NV đang xem — gộp theo SĐT (1 KH = 1 chip).
        Hiện TẤT CẢ cuộc gọi đến (kể cả quá khứ, user spec 2026-06-24), KHÔNG chỉ
        hôm nay → gọi nhỡ cũ vẫn nhắc gọi lại. answered=True nếu từng nghe máy
        (answer_time / state='answered'); ngược lại = gọi nhỡ (đỏ).
        call_user_domain đã scope theo NV (KHÔNG kèm điều kiện ngày)."""
        import re as _re
        try:
            Call = self.env['stringee.call'].sudo()
            calls = Call.search(
                call_user_domain + [('direction', '=', 'inbound')],
                order='create_date desc', limit=limit)
        except Exception:
            return []
        by_phone = {}
        for c in calls:
            phone = (c.caller_number or (c.lead_id.phone if c.lead_id else '') or '').strip()
            digits = _re.sub(r'\D', '', phone)
            key = digits[-9:] if len(digits) >= 9 else (digits or 'id%s' % c.id)
            answered = bool(c.answer_time) or c.state == 'answered'
            ts = c.create_date and c.create_date.timestamp() or 0
            rec = by_phone.get(key)
            if rec:
                if answered:
                    rec['answered'] = True
                rec['ts'] = max(rec['ts'], ts)
                continue
            nm = ''
            if c.lead_id:
                nm = c.lead_id.partner_name or c.lead_id.name or ''
            by_phone[key] = {
                'name': nm or ('KH ' + phone if phone else 'Khách lạ'),
                'phone': phone,
                'lead_id': c.lead_id.id if c.lead_id else False,
                'answered': answered,
                'ts': ts,
            }
        chips = list(by_phone.values())
        # Gọi nhỡ (đỏ) LÊN ĐẦU để NV ưu tiên gọi lại; trong nhóm thì gần đây trước.
        chips.sort(key=lambda r: (r['answered'], -r['ts']))
        for r in chips:
            r.pop('ts', None)
        return chips

    @api.model
    def vd_my_course_stats(self):
        """Báo cáo khóa học của NV ĐANG đăng nhập: tổng / đã học / chưa học.
        Dùng cho nút HỌC CÙNG VINADUY trên dashboard. An toàn nếu module
        vd_elearning chưa cài (trả về 0, không vỡ dashboard)."""
        try:
            Channel = self.env['slide.channel'].sudo()
            user = self.env.user
            # Khu khóa học theo vai trò: trưởng nhóm/lãnh đạo học khu 'leader'.
            zone = 'leader' if user.has_group(
                'vd_crm_lead.vd_crm_group_team_leader') else 'sales'
            courses = Channel.search([('vd_role_zone', '=', zone)])
            courses = courses.filtered(lambda c: Channel._vd_course_has_content(c))
            cids = set(courses.ids)
            total = len(cids)
            done = set()
            ER = self.env['vd.exam.result'].sudo()
            for r in ER.search([('user_id', '=', user.id),
                                ('channel_id', 'in', list(cids)),
                                ('passed', '=', True)]):
                done.add(r.channel_id.id)
            SCP = self.env['slide.channel.partner'].sudo()
            for p in SCP.search([('partner_id', '=', user.partner_id.id),
                                 ('channel_id', 'in', list(cids)),
                                 ('member_status', '=', 'completed')]):
                done.add(p.channel_id.id)
            d = len(done & cids)
            return {'total': total, 'done': d, 'todo': max(0, total - d)}
        except Exception:
            return {'total': 0, 'done': 0, 'todo': 0}

    @api.model
    def _vd_call_report(self, user_ids, today=None):
        """NGUỒN DUY NHẤT cho báo cáo cuộc gọi HÔM NAY + THÁNG NÀY của từng NV.

        Dùng chung cho trang cá nhân NV (dashboard_data) lẫn trang danh sách NV
        (nv_unified_flat) → số liệu 2 nơi LUÔN khớp.

        Đếm theo SỐ CUỘC GỌI thực tế (user spec 2026-06-08), KHÔNG phải số KH.
        'Nghe máy' (success) = answer_time IS NOT NULL HOẶC raw_events ILIKE
        '%answered%' — KHÔNG dùng state/duration (state không bao giờ lưu
        'answered', duration hay = 0; cùng tín hiệu với _vd_number_health/reached
        trong vd_stringee). Toàn bộ bằng search_count cho nhẹ (không load raw_events).

        Trả: {uid: {calls_today_total, calls_today_success,
                    calls_month_total, calls_month_success}}.
        """
        today = today or fields.Date.context_today(self)
        today_start = fields.Datetime.to_datetime(today)
        today_end = today_start + timedelta(days=1)
        month_start = fields.Datetime.to_datetime(today.replace(day=1))
        Call = self.env['stringee.call'].sudo()
        ANSWERED = ['|', ('answer_time', '!=', False),
                    ('raw_events', 'ilike', 'answered')]
        out = {}
        for uid in user_ids:
            base_today = [
                ('user_id', '=', uid), ('lead_id', '!=', False),
                ('create_date', '>=', today_start), ('create_date', '<', today_end),
            ]
            base_month = [
                ('user_id', '=', uid), ('lead_id', '!=', False),
                ('create_date', '>=', month_start), ('create_date', '<', today_end),
            ]
            out[uid] = {
                'calls_today_total': Call.search_count(base_today),
                'calls_today_success': Call.search_count(base_today + ANSWERED),
                'calls_month_total': Call.search_count(base_month),
                'calls_month_success': Call.search_count(base_month + ANSWERED),
            }
        return out

    # Tên 3 NV mẫu cho bảng GHI ÂM THAM KHẢO (user spec 2026-06-17). Đặt riêng
    # để dễ chỉnh; khớp MỀM bằng ilike (tên user có thể có tiền tố phòng ban).
    _VD_REF_REC_NAMES = ['Hồ A Du', 'Lâm Văn Hậu', 'Lê Xuân Hưng']

    @api.model
    def vd_reference_recordings(self, min_seconds=300, limit=50):
        """GHI ÂM THAM KHẢO — file ghi âm trên 5 phút của 3 NV mẫu (Hồ A Du,
        Lâm Văn Hậu, Lê Xuân Hưng) cho TOÀN công ty tham khảo cách tư vấn.

        Mỗi người 1 bảng: tên KH (KHÔNG kèm số ĐT), ngày gọi, thời lượng,
        link nghe inline (không cho tải) + thống kê số cuộc gọi trên 5 phút.
        @api.model + sudo nội bộ → ai trong công ty cũng gọi/xem được.
        """
        Users = self.env['res.users'].sudo()
        Call = self.env['stringee.call'].sudo()
        min_s = int(min_seconds)
        people = []
        for nm in self._VD_REF_REC_NAMES:
            user = Users.search([('name', 'ilike', nm)], limit=1)
            if not user:
                # khớp theo phần tên cuối (vd "Du" / "Hậu" / "Hưng")
                user = Users.search([('name', 'ilike', nm.split()[-1])], limit=1)
            if not user:
                people.append({'name': nm, 'found': False, 'count': 0,
                               'total_seconds': 0, 'recordings': []})
                continue
            rec_domain = [
                ('user_id', '=', user.id),
                ('duration', '>=', min_s),
                ('recording_attachment_id', '!=', False),
            ]
            count = Call.search_count(rec_domain)
            calls = Call.search(rec_domain, order='create_date desc', limit=int(limit))
            recs = []
            total_seconds = 0
            for c in calls:
                att = c.recording_attachment_id
                if not att:
                    continue
                total_seconds += c.duration or 0
                local_dt = (fields.Datetime.context_timestamp(c, c.create_date)
                            if c.create_date else None)
                lead = c.lead_id
                cust = ((lead.partner_name or lead.contact_name or lead.name)
                        if lead else None) or 'Khách hàng'
                recs.append({
                    'id': c.id,
                    'customer': cust,
                    'date': local_dt.strftime('%d/%m/%Y') if local_dt else '',
                    'duration': c.duration or 0,
                    'play_url': '/web/content/%s?download=false' % att.id,
                })
            people.append({
                'name': user.name,
                'found': True,
                'count': count,
                'total_seconds': total_seconds,
                'recordings': recs,
            })
        return {'people': people, 'min_minutes': min_s // 60}

    @api.model
    def dashboard_bootstrap(self):
        """Payload SIÊU NHẸ (chỉ group-check + uid) gọi TRƯỚC dashboard_data để
        client biết role và chọn đúng phạm vi ngay từ đầu → KHÔNG load 'all' thừa
        rồi mới load 'self' (tiết kiệm ~750ms cho Giám đốc). User spec 2026-06-20 r3.
        """
        u = self.env.user
        return {
            'current_user_id': u.id,
            'is_manager': self._dashboard_is_manager(),
            'is_director': bool(
                u.has_group('vd_crm_lead.vd_crm_group_deputy_director')
                and not u.has_group('base.group_system')
                and not u.has_group('vd_crm_lead.vd_crm_group_admin')),
        }

    @api.model
    def dashboard_data(self, user_id=None, team_scope=False):
        """Single-payload data for the OWL dashboard.

        team_scope=True (Giám đốc ở chế độ "CÁ NHÂN"): payload is_team_leader=True
        để client hiện bảng NV phòng mình (kể cả khi GĐ drill vào 1 NV trong phòng).
        """
        scope_user, scope_label, domain_user, call_user_domain = self._dashboard_resolve_scope(user_id)
        is_manager = self._dashboard_is_manager()
        # Auto-trash KH 4+ ngày không nghe máy — chạy trước khi tính counts
        try:
            self._vd_auto_trash_no_answer_leads(domain_user)
        except Exception:
            pass

        Stage = self.env['crm.stage']
        # Chỉ 4 stage chính: Khách mới / Báo giá / Đàm phán / Chốt
        # (bỏ Tiềm năng/Hẹn gọi lại đã archive + Hủy ẩn khỏi dashboard)
        stages = Stage.search([
            ('code', 'in', ['new', 'quote', 'negotiate', 'won']),
        ], order='sequence')
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
        call_today_domain = call_user_domain + [
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
            'recordings_today': Call.search_count(
                call_today_domain + [('recording_attachment_id', '!=', False)],
            ),
        }
        # Báo cáo cuộc gọi HÔM NAY + THÁNG NÀY cho card sidebar trang cá nhân NV.
        # Lấy từ NGUỒN CHUNG _vd_call_report (cùng số với badge trang danh sách NV).
        # Chỉ tính khi xem 1 NV cụ thể; màn "Tất cả NV" không hiện card này.
        # (Thay ô "Nghe" cũ tính bằng duration>0 — sai vì duration hay = 0.)
        if scope_user:
            kpi.update(self._vd_call_report([scope_user.id], today=today)[scope_user.id])

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

        # Block status — NV này có đang bị tạm dừng nhận lead mới không
        block_status = {'is_blocked': False, 'overdue_count': 0, 'threshold': 15}
        if scope_user:
            block_status = {
                'is_blocked': not scope_user.vd_can_receive_new_leads,
                'overdue_count': scope_user.vd_overdue_lead_count,
                'threshold': scope_user.vd_overdue_threshold,
            }

        # ===== YÊU CẦU TÌM VẤN ĐỀ — số liệu 2 banner + trạng thái khoá =====
        # Banner riêng cho từng bảng (THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ). days_left =
        # số ngày còn lại trước khi cron áp khoá (đếm từ vd_problem_find_since).
        _pf_enabled, _pf_pct, _pf_grace = self._vd_problem_find_config()
        # PERF (2026-06-01): CHỈ tính cho 1 NV cụ thể. Màn "Tất cả NV"
        # (scope_user=None) quét toàn bộ lead + regex urgent → ~25s/lần ->
        # với workers=0 gây nghẽn process -> 502. Banner chỉ hiện ở màn NV nên
        # bỏ tính ở view tổng cho nhẹ.
        if scope_user:
            problem_find = self._vd_problem_find_stats(domain_user)
            # LIVE (2026-06-05): áp/gỡ khoá NGAY khi mở dashboard — không chờ
            # cron hằng ngày (trước đây khoá trễ tới ~1 ngày). "bảng nào vi
            # phạm khoá bảng đó". Truyền lại stats để khỏi tính 2 lần.
            self._vd_apply_problem_lock(scope_user, now=now, stats=problem_find)
        else:
            _z = {'total': 0, 'no_problem': 0, 'pct': 0, 'over': False}
            problem_find = {
                'enabled': _pf_enabled, 'threshold_pct': _pf_pct,
                'urgent': dict(_z), 'xlvd': dict(_z), 'violating': False,
            }
        problem_find['grace_days'] = _pf_grace
        # Cờ khoá + đếm ngày RIÊNG TỪNG BẢNG (grace per-bảng từ Cài đặt khoá).
        _u_pct, _u_grace = self._vd_pf_table_cfg('urgent')
        _x_pct, _x_grace = self._vd_pf_table_cfg('xlvd')
        problem_find['urgent']['locked'] = bool(scope_user and scope_user.vd_pf_lock_urgent)
        problem_find['xlvd']['locked'] = bool(scope_user and scope_user.vd_pf_lock_xlvd)
        problem_find['urgent']['grace_days'] = _u_grace
        problem_find['xlvd']['grace_days'] = _x_grace
        problem_find['urgent']['days_left'] = (
            self._vd_pf_days_left(scope_user.vd_pf_since_urgent, _u_grace, now)
            if scope_user else _u_grace)
        problem_find['xlvd']['days_left'] = (
            self._vd_pf_days_left(scope_user.vd_pf_since_xlvd, _x_grace, now)
            if scope_user else _x_grace)
        problem_find['locked'] = bool(scope_user and scope_user.vd_problem_lock)
        # days_left tổng = nhỏ nhất của 2 bảng đang vi phạm (cho chỗ cũ tham chiếu)
        problem_find['days_left'] = min(
            problem_find['urgent']['days_left'], problem_find['xlvd']['days_left'])

        # ===== PERFORMANCE — leaderboard + bonus calculation =====
        # Tính số HĐ chốt tháng + năm + bonus theo cơ cấu chỉ tiêu 2026.
        from datetime import date
        month_start = date.today().replace(day=1)
        year_start = date.today().replace(month=1, day=1)
        won_month_count = self.search_count(domain_user + [
            ('vd_contract_signed', '=', True),
            ('vd_contract_sign_date', '>=', month_start),
        ])
        won_year_count = self.search_count(domain_user + [
            ('vd_contract_signed', '=', True),
            ('vd_contract_sign_date', '>=', year_start),
        ])
        ResUsers = self.env['res.users']
        my_bonus = ResUsers._vd_calc_nv_bonus(won_month_count) if scope_user else 0
        total_revenue_month = sum(self.search(domain_user + [
            ('vd_contract_signed', '=', True),
            ('vd_contract_sign_date', '>=', month_start),
        ]).mapped('vd_quote_price') or [0])

        # Danh sách HĐ đã chốt trong tháng (tooltip khi hover Thưởng)
        closed_contracts = []
        if scope_user:
            won_leads = self.search(domain_user + [
                ('vd_contract_signed', '=', True),
                ('vd_contract_sign_date', '>=', month_start),
            ], order='vd_contract_sign_date desc, id desc', limit=20)
            for ld in won_leads:
                closed_contracts.append({
                    'id': ld.id,
                    'name': ld.name or ld.partner_name or 'KH',
                    'date': ld.vd_contract_sign_date.strftime('%d/%m/%Y') if ld.vd_contract_sign_date else '',
                    'price': ld.vd_quote_price or 0,
                    'deposit': ld.vd_contract_deposit or 0,
                })

        # Leaderboard tất cả NV (chỉ manager mới thấy full list).
        # Admin view: KHÔNG skip NV 0 HĐ — admin cần thấy CẢ NV chưa chốt
        # để biết ai đang cần thúc.
        leaderboard = []
        if is_manager:
            sales_users = ResUsers.search([
                ('share', '=', False),
                ('active', '=', True),
                ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
            ])
            for u in sales_users:
                u_month_count = self.search_count([
                    ('user_id', '=', u.id),
                    ('vd_contract_signed', '=', True),
                    ('vd_contract_sign_date', '>=', month_start),
                ])
                u_year_count = self.search_count([
                    ('user_id', '=', u.id),
                    ('vd_contract_signed', '=', True),
                    ('vd_contract_sign_date', '>=', year_start),
                ])
                u_active_count = self.search_count([
                    ('user_id', '=', u.id),
                    ('stage_is_won', '=', False),
                    ('stage_is_lost', '=', False),
                ])
                bonus = ResUsers._vd_calc_nv_bonus(u_month_count)
                leaderboard.append({
                    'user_id': u.id,
                    'name': u.name,
                    'contracts_month': u_month_count,
                    'contracts_year': u_year_count,
                    'active_leads': u_active_count,
                    'bonus_month': bonus,
                    'target_month': 2,
                    'perf_pct': (u_month_count / 2.0 * 100) if u_month_count else 0,
                })
            leaderboard.sort(key=lambda x: (-x['contracts_month'], -x['bonus_month'], -x['active_leads']))

        performance = {
            'contracts_month': won_month_count,
            'contracts_year': won_year_count,
            'target_month': 2,
            'target_year': 20,
            'perf_pct_month': (won_month_count / 2.0 * 100) if won_month_count else 0,
            'perf_pct_year': (won_year_count / 20.0 * 100) if won_year_count else 0,
            'bonus_month': my_bonus,
            'next_tier_at': won_month_count + 1,
            'next_tier_bonus': ResUsers._vd_calc_nv_bonus(won_month_count + 1) - my_bonus,
            'revenue_month': total_revenue_month,
            'leaderboard': leaderboard,
            'closed_contracts': closed_contracts,
        }

        return {
            'user': {
                'id': scope_user.id if scope_user else 0,
                'name': scope_label,
                'is_all': scope_user is None,
            },
            'is_manager': is_manager,
            # Dòng KHÁCH GỌI ĐẾN HÔM NAY (user spec 2026-06-24): gọi đến nghe máy +
            # gọi nhỡ của NV đang xem, hiện trên cùng bảng KHÁCH MỚI.
            'inbound_today': self._vd_inbound_today_chips(call_user_domain),
            # Trưởng nhóm: mở "giao diện quản lý NHÓM" (chọn/xem NV cùng phòng ban),
            # KHÔNG có quyền toàn công ty / thùng rác công ty (giữ cho Giám đốc+).
            # User spec 2026-06-20: Giám đốc (manager) ở chế độ "CÁ NHÂN"
            # (team_scope=True) thì cũng hiện bảng NV phòng mình GIỐNG trưởng nhóm —
            # giữ cả khi GĐ drill vào 1 NV trong phòng (để còn nút "Về dashboard").
            'is_team_leader': self._dashboard_is_team_leader() or bool(
                is_manager and team_scope),
            'team_label': self._vd_team_label_for(self.env.user),
            # CHỈ ADMIN được DUYỆT hủy KH (user spec 2026-06-10) — ẩn nút Duyệt
            # khỏi NV (backend action_approve_cancel cũng chặn).
            'is_admin': bool(self.env.user._is_superuser()
                             or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin')),
            # GIÁM ĐỐC (không phải admin): client dùng để mặc định mở chế độ CÁ
            # NHÂN. Admin giữ mặc định "Tất cả NV" như cũ.
            'is_director': bool(
                self.env.user.has_group('vd_crm_lead.vd_crm_group_deputy_director')
                and not self.env.user.has_group('base.group_system')
                and not self.env.user.has_group('vd_crm_lead.vd_crm_group_admin')),
            # Quyền chuyển KH hàng loạt (admin + role có can_reassign_lead =
            # người chia số / giám đốc). Client dùng để hiện nút "Chọn KH".
            'can_reassign': self.env['vd.crm.role.config'].sudo().can_user_reassign(self.env.user),
            'current_user_id': self.env.user.id,
            'selected_user_id': scope_user.id if scope_user else 0,
            # Hướng dẫn nút SOS (coachmark) — theo user ĐANG đăng nhập.
            'sos_guide': {
                'show': self.env['res.users'].vd_sos_guide_should_show(self.env.user),
                'count': self.env.user.vd_sos_guide_ack_count or 0,
            },
            # Thùng rác CÔNG TY — tổng KH huỷ toàn công ty (mọi NV). Chỉ manager.
            # Khác thùng rác KH HỦY của TỪNG NV ở bảng KHÁCH MỚI (đã scope theo NV).
            'company_trash_count': (
                self.with_context(active_test=False).search_count(
                    [('stage_is_lost', '=', True),
                     ('vd_cancel_state', '=', 'approved')])
                if self._can_see_company_trash() else 0
            ),
            'can_see_company_trash': self._can_see_company_trash(),
            'kpi': kpi,
            'errors': errors,
            'stages': stage_payload,
            'block_status': block_status,
            'problem_find': problem_find,
            # CALL-WATCH (2026-06-04): banner "chưa gọi" + khoá bảng Khách mới.
            'call_watch': self._vd_callwatch_payload(scope_user),
            # KHOÁ TOÀN BỘ khi tồn quá nhiều KH mới chưa gọi (user spec 2026-06-12)
            'uncalled_new_lock': self._vd_uncalled_new_lock_payload(scope_user),
            # Ngưỡng CHẶN CHIA SỐ (KH mới chưa gọi) — frontend dùng tính sức chứa NV
            'distribute_block_threshold': self._vd_distribute_block_threshold(),
            # Công tắc khoá cứng "chưa nhắn Zalo" (>10) — mặc định TẮT (user spec
            # 2026-06-10: khoá cứng phản tác dụng). Bật: System Parameter
            # vd_crm_lead.zalo_lock_enabled = 1.
            'zalo_lock_enabled': (self.env['ir.config_parameter'].sudo()
                                  .get_param('vd_crm_lead.zalo_lock_enabled', '0') == '1'),
            # CHIA SỐ (2026-06-05): báo cáo chia số tự động (Pancake) + thủ công
            # (nhập tay) hôm nay/tháng + cảnh báo chia không đều. Chỉ ở màn quản lý.
            'pancake_report': self._vd_distribution_report(pancake=True) if is_manager else {},
            'manual_report': self._vd_distribution_report(pancake=False) if is_manager else {},
            'performance': performance,
            # BẢO MẬT (user spec 2026-06-18): buộc NV đổi mật khẩu khi hết chu kỳ
            # 30 ngày — frontend chặn dashboard tới khi đổi xong.
            'must_change_password': bool(self.env.user.vd_pwd_must_change),
        }

    def _dashboard_new_bucket_domain(self, user_domain):
        """Domain bucket KHÁCH MỚI — dùng CHUNG cho màn NV (dashboard_leads) và
        grid admin (newcust_by_user) để 2 chỗ luôn khớp số.

        Gồm:
          - KH stage 'new', VÀ
          - KH stage Báo giá/Đàm phán NHƯNG chưa CHỐT thông tin
            (vd_intake_locked=False HOẶC vd_intake_complete=False).

        Lý do (user spec 2026-06-01 — "khách mất tích"): THI CÔNG GẤP và XỬ LÝ
        VẤN ĐỀ đều yêu cầu locked=True AND complete=True. KH đã sang Báo giá
        nhưng NV chưa CHỐT thông tin không lọt vào 2 bảng đó, cũng không phải
        stage 'new' → biến mất khỏi mọi bảng dù vẫn đếm trong Tổng KH. Gom
        chúng về KHÁCH MỚI (frontend hiện pill xanh lá + 💰, tier -1) đúng ý
        "chưa CHỐT = vẫn là khách mới".

        LOẠI vd_no_quote_state='pending' (→ bucket THAM KHẢO riêng).
        """
        Stage = self.env['crm.stage']
        new_ids = Stage.search([('code', '=', 'new')]).ids
        mid_ids = Stage.search([('code', 'in', ['quote', 'negotiate'])]).ids
        if mid_ids:
            stage_clause = [
                '|',
                    ('stage_id', 'in', new_ids),
                    '&', ('stage_id', 'in', mid_ids),
                         '|', ('vd_intake_locked', '=', False),
                              ('vd_intake_complete', '=', False),
            ]
        else:
            stage_clause = [('stage_id', 'in', new_ids)]
        return user_domain + [
            ('active', '=', True),
            ('vd_no_quote_state', '!=', 'pending'),
        ] + stage_clause

    def _vd_uncalled_new_lock_payload(self, scope_user):
        """KHOÁ TOÀN BỘ bảng khi NV tồn quá nhiều KH mới CHƯA GỌI (user spec
        2026-06-12). Đếm KH bucket KHÁCH MỚI có 0 cuộc gọi (call_stats.total==0
        → khớp ĐÚNG 'vùng CHƯA GỌI' frontend, cùng cách lọc số chết). Chỉ áp khi
        xem 1 NV cụ thể; >ngưỡng → khoá; gọi cho ≤ngưỡng → tự mở. Ngưỡng 0 = tắt."""
        ICP = self.env['ir.config_parameter'].sudo()
        threshold = int(ICP.get_param(
            'vd_crm_lead.uncalled_new_lock_threshold', 15) or 15)
        base = {'enabled': threshold > 0, 'threshold': threshold,
                'count': 0, 'locked': False}
        if threshold <= 0 or not scope_user:
            return base
        new_leads = self.search(
            self._dashboard_new_bucket_domain([('user_id', '=', scope_user.id)]))
        if not new_leads:
            return base
        stats = self._dashboard_compute_call_stats(new_leads)
        base['count'] = sum(
            1 for l in new_leads if (stats.get(l.id, {}).get('total') or 0) == 0)
        base['locked'] = base['count'] > threshold
        return base

    @api.model
    def _vd_distribute_block_threshold(self):
        """Ngưỡng CHẶN CHIA SỐ theo KH mới chưa gọi. 0 = tắt (user spec 2026-06-12)."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'vd_crm_lead.distribute_block_uncalled', 20) or 20)

    @api.model
    def _vd_today_assigned_count_map(self, user_ids, pancake_only=False):
        """Map {user_id: số KH được CHIA HÔM NAY (theo giờ VN, UTC+7)}.
        Dùng cho CHIA ĐỀU TRONG NGÀY (user spec 2026-06-20): cuối ngày mọi NV
        nhận ~ bằng nhau. Đếm theo create_date (mọi nguồn) để tổng ngày cân bằng.

        pancake_only=True (user spec 2026-06-23): CHỈ đếm KH đến từ Pancake
        (vd_pancake_page_id != False) → chia đều RIÊNG kênh TikTok/Facebook."""
        from collections import defaultdict
        from datetime import timedelta
        uids = [int(u) for u in (user_ids or []) if u]
        if not uids:
            return {}
        # VN cố định UTC+7 (không DST). Mốc 00:00 VN hôm nay → quy về UTC.
        now_vn = fields.Datetime.now() + timedelta(hours=7)
        start_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_vn - timedelta(hours=7)
        domain = [
            ('user_id', 'in', uids),
            ('create_date', '>=', fields.Datetime.to_string(start_utc)),
        ]
        if pancake_only:
            domain.append(('vd_pancake_page_id', '!=', False))
        leads = self.sudo().search(domain)
        cnt = defaultdict(int)
        for l in leads:
            if l.user_id:
                cnt[l.user_id.id] += 1
        return dict(cnt)

    @api.model
    def _vd_uncalled_new_count_map(self, user_ids):
        """Map {user_id: số KH MỚI CHƯA gọi cuộc nào (call_count=0) trong bucket
        KHÁCH MỚI}. Dùng CHẶN CHIA SỐ (user spec 2026-06-12) — khớp 'new_not_called'
        ở dashboard_users."""
        from collections import defaultdict
        uids = [int(u) for u in (user_ids or []) if u]
        if not uids:
            return {}
        leads = self.sudo().search(
            self._dashboard_new_bucket_domain([('user_id', 'in', uids)])
            + [('call_count', '=', 0)])
        cnt = defaultdict(int)
        for l in leads:
            if l.user_id:
                cnt[l.user_id.id] += 1
        return dict(cnt)

    @api.model
    def dashboard_leads(self, stage_id, user_id=None, limit=500):
        # User spec 2026-06-01: cap 80 cũ cắt cụt danh sách (NV >80 KH mới hiện
        # thiếu → lệch số với bảng admin). Nâng 500 để hiện đủ + khớp số đếm.
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        stage = self.env['crm.stage'].browse(stage_id)
        # KHÁCH MỚI = stage 'new' + KH Báo giá/Đàm phán chưa CHỐT (xem
        # _dashboard_new_bucket_domain). Round 11: loại "CHƯA BÁO GIÁ"
        # (vd_no_quote_state='pending') → THAM KHẢO bucket riêng.
        if stage.code == 'new':
            domain = self._dashboard_new_bucket_domain(domain_user)
        else:
            domain = domain_user + [('stage_id', '=', stage_id)]
        leads = self.search(
            domain, limit=limit,
            order='last_call_date desc, create_date desc',
        )
        # User spec 2026-06-08: sắp theo LẦN GỌI gần nhất cho ỔN ĐỊNH, dễ tìm —
        # KH chưa gọi / lâu chưa gọi lên ĐẦU, KH vừa gọi xong xuống CUỐI. Tránh
        # nhảy lung tung do probability/callback_date đổi sau mỗi cuộc gọi.
        # (KH chưa gọi: last_call_date rỗng -> coi như cũ nhất -> lên đầu.)
        from datetime import datetime as _dt
        leads = leads.sorted(
            key=lambda l: (l.last_call_date or _dt.min, l.create_date or _dt.min)
        )
        return self._dashboard_serialize_leads(leads)

    @api.model
    def dashboard_leads_by_alert(self, kind, user_id=None, limit=80):
        """Trả lead theo loại cảnh báo (overdue_callback / new_not_called /
        potential_no_quote / stale). Domain match _compute_errors trong
        dashboard_data để consistent số đếm vs danh sách."""
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        now = fields.Datetime.now()
        stale_threshold = now - timedelta(days=14)
        active_only = [('stage_is_won', '=', False), ('stage_is_lost', '=', False)]

        DOMAINS = {
            'overdue_callback': domain_user + active_only + [
                ('callback_date', '<', now),
            ],
            'new_not_called': domain_user + [
                ('stage_id.code', '=', 'new'),
                ('call_count', '=', 0),
            ],
            'potential_no_quote': domain_user + [
                ('stage_id.code', '=', 'potential'),
            ],
            'stale': domain_user + active_only + [
                '|',
                ('last_call_date', '<', stale_threshold),
                '&', ('last_call_date', '=', False), ('create_date', '<', stale_threshold),
            ],
        }
        domain = DOMAINS.get(kind)
        if not domain:
            return []
        leads = self.search(
            domain, limit=limit,
            order='callback_date asc, create_date desc',
        )
        return self._dashboard_serialize_leads(leads)

    @api.model
    def _dashboard_urgent_construction_ids(self, domain_user):
        """Helper: IDs của lead có thời gian thi công gấp.
        Tiêu chí: vd_intake_timeline chứa 'càng sớm' / 'asap' / 'gấp' HOẶC
        có 'Tháng N/YYYY' trong khoảng <= 3 tháng tới (kể cả tháng đã qua).

        REQUIRE: vd_intake_complete=True — KH chưa đủ thông tin (chưa sinh
        báo giá) coi như khách mới, KHÔNG hiện ở THI CÔNG GẤP.

        SIDE EFFECT: Auto-tạo problem "Thi công gấp" cho mọi lead match
        điều kiện (idempotent — bỏ qua nếu đã có).
        """
        import re
        from datetime import date
        # User spec 2026-05-28 (round 2 — revert): KH chưa CHỐT (locked=False)
        # phải ở KH MỚI bucket. Chỉ KH đã CHỐT mới vào THI CÔNG GẤP.
        candidates = self.search(
            domain_user + [
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
                ('active', '=', True),
                ('vd_intake_complete', '=', True),
                ('vd_intake_locked', '=', True),
                ('vd_intake_timeline', '!=', False),
            ],
        )
        today = date.today()
        urgent_ids = []
        pat = re.compile(r'Tháng\s+(\d{1,2})\s*/\s*(\d{4})', re.IGNORECASE)
        for lead in candidates:
            tl = (lead.vd_intake_timeline or '').strip()
            if not tl:
                continue
            low = tl.lower()
            if 'càng sớm' in low or 'asap' in low or 'gấp' in low:
                urgent_ids.append(lead.id)
                continue
            m = pat.search(tl)
            if m:
                try:
                    month = min(max(int(m.group(1)), 1), 12)
                    year = int(m.group(2))
                    target = date(year, month, 1)
                    months_diff = (target.year - today.year) * 12 + (target.month - today.month)
                    if months_diff <= 3:
                        urgent_ids.append(lead.id)
                except ValueError:
                    continue
        if urgent_ids:
            self.browse(urgent_ids)._vd_ensure_urgent_construction_problem()
        return urgent_ids

    def _vd_ensure_urgent_construction_problem(self):
        """Idempotent: tạo 'Thi công gấp' problem nếu chưa có cho leads này."""
        tag = self.env.ref(
            'vd_crm_lead.nego_problem_urgent_construction',
            raise_if_not_found=False,
        )
        if not tag:
            return
        # Bypass gate vd_skip_intake_lock — system tự tạo problem cho KH urgent,
        # KHÔNG yêu cầu CHỐT THÔNG TIN trước (chỉ áp cho NV bấm + Thêm vấn đề).
        # try/except defense: nếu 1 lead fail không break cả batch.
        Problem = self.env['vd.lead.problem'].sudo().with_context(
            vd_skip_intake_lock=True
        )
        for lead in self:
            if lead.vd_lead_problem_ids.filtered(lambda p: p.tag_id.id == tag.id):
                continue
            try:
                Problem.create({
                    'lead_id': lead.id,
                    'tag_id': tag.id,
                    'name': tag.name,
                    'status': 'open',
                    'sequence': 1,
                    'is_default': True,
                })
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "[vd_crm_lead] Skip create urgent problem for lead %d (%s)",
                    lead.id, lead.name,
                )

    @api.model
    def dashboard_leads_urgent_construction(self, user_id=None, limit=200):
        """Trả KH có thời gian thi công GẤP (≤ 3 tháng tới hoặc 'càng sớm càng tốt').
        Round 17 sort: ưu tiên KH có quote_created_date CŨ NHẤT (= quote_days
        cao nhất = ít ngày còn lại nhất / đã quá hạn). Fallback create_date asc."""
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        urgent_ids = self._dashboard_urgent_construction_ids(domain_user)
        if not urgent_ids:
            return []
        leads = self.search(
            [('id', 'in', urgent_ids)],
            limit=limit,
            order='vd_quote_created_date desc nulls last, create_date desc',
        )
        data = self._dashboard_serialize_leads(leads)
        return self._dashboard_attach_quote_info(leads, data)

    @api.model
    def dashboard_leads_with_problems(self, user_id=None, limit=200):
        """Trả TẤT CẢ KH ở stage quote/negotiate (sau báo giá, trước khi chốt).
        EXCLUDE KH đã hiển thị ở section 'THI CÔNG GẤP' (tránh trùng lặp).

        REQUIRE: vd_intake_complete=True — KH chưa đủ thông tin (chưa sinh
        báo giá) coi như khách mới, KHÔNG hiện ở XỬ LÝ VẤN ĐỀ.
        """
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        Stage = self.env['crm.stage']
        mid_stage_ids = Stage.search([
            ('code', 'in', ['quote', 'negotiate']),
        ]).ids
        if not mid_stage_ids:
            return []
        urgent_ids = self._dashboard_urgent_construction_ids(domain_user)
        # User spec 2026-05-28 (round 2 — revert): chỉ KH đã CHỐT mới ở XLVD.
        # Chưa CHỐT (locked=False) → ở KH MỚI bucket với pill xanh lá + 💰.
        leads = self.search(
            domain_user + [
                ('stage_id', 'in', mid_stage_ids),
                ('active', '=', True),
                ('vd_intake_complete', '=', True),
                ('vd_intake_locked', '=', True),
                ('id', 'not in', urgent_ids),
            ],
            limit=limit,
            # Round 17 sort: ưu tiên KH cũ nhất (= ít ngày còn lại / quá hạn).
            order='vd_quote_created_date desc nulls last, create_date desc',
        )
        data = self._dashboard_serialize_leads(leads)
        return self._dashboard_attach_quote_info(leads, data)

    @api.model
    def _dashboard_attach_quote_info(self, leads, data):
        """Gắn THÔNG TIN KHÁCH HÀNG (tầm tài chính + bảng báo giá chi tiết HTML)
        vào serialized data — CHỈ cho 2 bảng THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ để render
        panel hover trên tên KH. KHÔNG dùng cho list chính vì vd_quote_breakdown_html
        là field compute (store=False) — tính hàng loạt sẽ nặng.
        """
        by_id = {l.id: l for l in leads}
        budget_sel = dict(self._fields['vd_intake_budget_range'].selection)
        # User spec 2026-05-30: chỉ số cuộc gọi ở 2 bảng này CHỈ tính từ ngày báo
        # giá thành công (vd_quote_created_date). Recompute + overwrite call_stats.
        since_map = {
            l.id: l.vd_quote_created_date for l in leads if l.vd_quote_created_date
        }
        quote_call_stats = self._dashboard_compute_call_stats(leads, since_by_lead=since_map)
        for d in data:
            if d['id'] in quote_call_stats:
                d['call_stats'] = quote_call_stats[d['id']]
        for d in data:
            rec = by_id.get(d['id'])
            if not rec:
                continue
            budget_amt = rec.vd_intake_budget_amount or 0
            quote_amt = rec.vd_quote_price or 0
            d['budget_label'] = (
                budget_sel.get(rec.vd_intake_budget_range, '')
                if rec.vd_intake_budget_range else ''
            )
            d['budget_amount_fmt'] = self._fmt_vnd(budget_amt) if budget_amt else ''
            d['quote_price_fmt'] = self._fmt_vnd(quote_amt) if quote_amt else ''
            d['quote_breakdown_html'] = rec.vd_quote_breakdown_html or ''
            # Chênh lệch: BÁO GIÁ − TÀI CHÍNH DỰ KIẾN. > 0 = vượt ngân sách (đỏ),
            # < 0 = còn dư (xanh). Chỉ tính khi có cả 2 số.
            # budget_fit: 'fit' (giá ≤ tài chính = KHỚP), 'over' (vượt), '' (thiếu data).
            # budget_fit_diff_short: số chênh rút gọn (vd '300 tr', '1,8 tỷ') cho cột hẹp.
            if budget_amt and quote_amt:
                diff = quote_amt - budget_amt
                d['quote_over_budget'] = diff > 0
                d['quote_vs_budget_diff_fmt'] = self._fmt_vnd(abs(diff))
                d['budget_fit'] = 'over' if diff > 0 else 'fit'
                d['budget_fit_diff_short'] = self._fmt_vnd_short(abs(diff)) if diff else ''
            else:
                d['quote_over_budget'] = False
                d['quote_vs_budget_diff_fmt'] = ''
                d['budget_fit'] = ''
                d['budget_fit_diff_short'] = ''
        # User spec 2026-05-31: KH KHỚP TÀI CHÍNH lên ĐẦU, rồi vượt ngân sách,
        # cuối là chưa đủ dữ liệu. sort ỔN ĐỊNH → giữ thứ tự urgency cũ trong nhóm.
        _fit_rank = {'fit': 0, 'over': 1}
        data.sort(key=lambda d: _fit_rank.get(d.get('budget_fit'), 2))
        return data

    @api.model
    def vd_dashboard_search_leads(self, query, user_id=None, limit=30):
        """User spec 2026-05-29 + 2026-06-06: search KH theo SĐT hoặc TÊN không dấu.

        Nâng cấp 2026-06-06:
        - TÌM CẢ lead LƯU TRỮ + THÙNG RÁC công ty (active_test=False), không chỉ active.
        - SĐT chuẩn hoá về dạng NỘI ĐỊA (bỏ 0 / 84 / +84) → gõ '09...' ra cả '084.../84...'.
        - Trả về NV quản lý + TRẠNG THÁI (đang xử lý / lưu trữ / thùng rác).
        Scope theo quyền: user_id chỉ định → leads của NV đó; None → theo quyền user
        hiện tại (ir.rules vẫn áp — NV thường không thấy KH người khác).
        """
        import unicodedata
        import re
        q = (query or '').strip()
        if not q:
            return []

        def _norm(s):
            """Lowercase + strip diacritics. 'Hà Nội' → 'ha noi'."""
            if not s:
                return ''
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            s = s.replace('đ', 'd').replace('Đ', 'd')
            return s.lower().strip()

        def _nat(s):
            """SĐT về dạng nội địa: bỏ ký tự không phải số, bỏ tiền tố 84/+84/0.
            '0977261290' / '84977261290' / '+84977261290' → '977261290'."""
            d = re.sub(r'\D', '', s or '')
            while d.startswith('84') and len(d) > 9:
                d = d[2:]
            if d.startswith('0'):
                d = d[1:]
            return d

        q_norm = _norm(q)
        q_nat = _nat(q)  # national-form digits của query
        is_phone_q = len(q_nat) >= 4

        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)

        # active_test=False → bao gồm lead LƯU TRỮ + THÙNG RÁC (active=False).
        Lead = self.with_context(active_test=False)
        if is_phone_q:
            # Phone: prefilter domain bằng national digits → tìm cả 0xxx/84xxx,
            # không bị giới hạn fetch khi có nhiều lead lưu trữ.
            cand = Lead.search(
                domain_user + ['|', ('phone', 'ilike', q_nat), ('mobile', 'ilike', q_nat)],
                limit=300, order='write_date desc',
            )
        else:
            cand = Lead.search(domain_user, limit=400, order='write_date desc')

        # GỘP TRÙNG SĐT (user spec 2026-06-22): 1 số KH = 1 dòng. Gom theo số nội
        # địa; mỗi nhóm chỉ hiện 1 lead ƯU TIÊN (active/đang xử lý > mới nhất). Lead
        # không có số (search theo tên) giữ riêng từng dòng.
        groups = {}      # key -> list[lead] (theo thứ tự write_date desc của cand)
        order = []       # giữ thứ tự xuất hiện của key
        for l in cand:
            hit = False
            if is_phone_q and (q_nat in _nat(l.phone) or q_nat in _nat(l.mobile)):
                hit = True
            if not hit and q_norm and (q_norm in _norm(l.name) or q_norm in _norm(l.partner_name)):
                hit = True
            if not hit:
                continue
            key = _nat(l.phone) or _nat(l.mobile) or ('id%d' % l.id)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(l)

        matches = []
        for key in order:
            leads = groups[key]
            # Ưu tiên lead ĐANG xử lý (active + chưa vào thùng rác); không có thì
            # lấy lead mới nhất (đầu list vì cand sort write_date desc).
            live = [x for x in leads if x.active and x.vd_cancel_state != 'approved']
            l = live[0] if live else leads[0]
            archived_others = len(leads) - 1
            if l.vd_cancel_state == 'approved':
                state_label = '🗑️ Thùng rác công ty'
            elif not l.active:
                state_label = '🗄️ Lưu trữ'
            else:
                state_label = l.stage_id.name or ''
            if archived_others > 0:
                state_label = '%s · +%d bản trùng đã gộp' % (state_label, archived_others)
            matches.append({
                'id': l.id,
                'name': l.partner_name or l.name or '(không tên)',
                'phone': l.phone or l.mobile or '',
                'stage_name': l.stage_id.name or '',
                'state_label': state_label,
                'archived': not l.active,
                'user_name': l.user_id.name or '',
            })
            if len(matches) >= limit:
                break
        return matches

    @api.model
    def dashboard_leads_not_called(self, user_id=None, limit=200):
        """KH "CHƯA GỌI ĐƯỢC" (user spec 2026-06-13) — số ĐÚNG, đã ĐỔ CHUÔNG nhưng
        KH KHÔNG NGHE máy, trên ≥3 NGÀY khác nhau (chưa từng nghe máy lần nào).

        KH thuê bao/sai số THUẦN (chưa từng đổ chuông) KHÔNG ở đây — bị HỦY tự
        động (xem _vd_auto_trash_no_answer_leads). KH đã nghe máy cũng loại.
        """
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        candidates = self.search(
            domain_user + [
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
                ('call_count', '>=', 3),
            ],
            order='create_date desc',
        )
        matched_ids = self._dashboard_unreachable_ids(candidates, limit)
        if not matched_ids:
            return []
        return self._dashboard_serialize_leads(self.browse(matched_ids))

    @api.model
    def _dashboard_unreachable_ids(self, candidates, limit=200):
        """Lọc trong `candidates` ra các lead "không liên lạc được": NV đã cố
        gọi nhưng KH chưa bao giờ bắt máy (cond A/B/C). Trả về list lead id.

        Dùng chung cho 'CHƯA GỌI ĐƯỢC' (mọi stage) và 'BÁO GIÁ XONG MẤT TÍCH'
        (chỉ stage Báo giá/Đàm phán) để logic không bị lệch nhau.
        """
        from datetime import date as _date, timedelta
        today = _date.today()
        if not candidates:
            return []
        Call = self.env['stringee.call']
        # User spec 2026-06-09: bỏ qua cuộc gọi từ SỐ CHẾT (không đổ chuông) →
        # khách chỉ-bị-gọi-bằng-số-chết KHÔNG bị coi là "chưa gọi được" (oan).
        dead_numbers = self._vd_dead_caller_numbers()
        calls = Call.search_read(
            [('lead_id', 'in', candidates.ids)],
            ['lead_id', 'state', 'duration', 'answer_time', 'start_time',
             'caller_number'],
        )
        from collections import defaultdict
        by_lead = defaultdict(list)
        for c in calls:
            lid = c['lead_id'][0] if c['lead_id'] else False
            if lid:
                by_lead[lid].append(c)

        matched_ids = []
        now_dt = fields.Datetime.now()
        for lead in candidates:
            lcalls = by_lead.get(lead.id) or []
            # Loại cuộc VÔ GIÁ TRỊ từ số chết (không answer_time, không nghe máy).
            if dead_numbers and lcalls:
                lcalls = [
                    c for c in lcalls
                    if not (
                        c.get('caller_number') in dead_numbers
                        and not c.get('answer_time')
                        and not ((c.get('state') in ('answered', 'ended'))
                                 and (c.get('duration') or 0) > 0)
                    )
                ]
            if not lcalls:
                continue
            # User spec 2026-05-28 (round 2): answered = state ∈ {answered, ended}
            # AND dur > 0 (declined dur=1s không count là answered).
            had_success = any(
                (c.get('state') in ('answered', 'ended'))
                and (c.get('duration') or 0) > 0
                for c in lcalls
            )
            if had_success:
                continue
            # User spec 2026-06-13: CHƯA GỌI ĐƯỢC = KH đã ĐỔ CHUÔNG (số ĐÚNG, máy
            # reo) nhưng KHÔNG NGHE máy, trên ≥3 NGÀY khác nhau. Thuê bao/sai số
            # THUẦN (chưa từng reo) → HỦY tự động (_vd_auto_trash_no_answer_leads),
            # KHÔNG nằm ở đây. (Đảo lại logic 2026-06-09.)
            all_days = set()
            rang = 0          # cuộc ĐỔ CHUÔNG: no_answer / busy / declined
            for c in lcalls:
                s = c.get('start_time')
                day = s.date() if s and hasattr(s, 'date') else None
                if day:
                    all_days.add(day)
                if c.get('state') in ('no_answer', 'busy', 'declined'):
                    rang += 1
            if rang >= 1 and len(all_days) >= 3:
                matched_ids.append(lead.id)
                if len(matched_ids) >= limit:
                    break
        return matched_ids

    @api.model
    def dashboard_leads_quoted_lost(self, user_id=None, limit=200):
        """KH "BÁO GIÁ XONG MẤT TÍCH" — đã sang stage Báo giá/Đàm phán RỒI nhưng
        dính tiêu chí không liên lạc được (NV gọi ≥3 lần, KH không bao giờ bắt máy).

        = giao của (đã báo giá) ∩ (không liên lạc được). Hiển thị ở box cuối 2
        bảng THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ (user spec 2026-05-30).
        """
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        quoted_stages = self.env['crm.stage'].search([('code', 'in', ['quote', 'negotiate'])])
        if not quoted_stages:
            return []
        candidates = self.search(
            domain_user + [
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
                ('stage_id', 'in', quoted_stages.ids),
                ('call_count', '>=', 3),
            ],
            order='create_date desc',
        )
        matched_ids = self._dashboard_unreachable_ids(candidates, limit)
        if not matched_ids:
            return []
        return self._dashboard_serialize_leads(self.browse(matched_ids))

    @api.model
    def dashboard_leads_planned_sign(self, user_id=None, limit=200):
        """KH "ĐÃ LÀM HỢP ĐỒNG" — NV đã bấm nút "Làm hợp đồng" mở panel làm HĐ /
        hẹn gặp ký (vd_contract_open=True). Dùng cho bucket "KHÁCH GỬI HỢP ĐỒNG"
        + board "KHÁCH ĐÃ LÀM HỢP ĐỒNG" trên cùng (user spec 2026-06-12).
        (Trước dùng vd_planned_sign_date — SAI vì KH bấm 'Làm hợp đồng' chưa chắc
        đã đặt lịch ký.)"""
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        leads = self.search(
            domain_user + [
                ('vd_contract_open', '=', True),
                ('stage_is_lost', '=', False),
                ('active', '=', True),
            ],
            order='vd_planned_sign_date asc, id desc',
            limit=limit,
        )
        if not leads:
            return []
        return self._dashboard_serialize_leads(leads)

    @api.model
    def dashboard_leads_reference(self, user_id=None, limit=200):
        """KH "tham khảo" — round 16 (user spec 2026-05-30):
        CHỈ KH explicit NV bấm "CHƯA BÁO GIÁ" (vd_no_quote_state='pending').
        BỎ legacy heuristic (answered ≥ 1 + no quote) — vì KH chưa đủ thông
        tin vẫn phải ở KHÁCH MỚI, không tự động chuyển sang THAM KHẢO chỉ
        vì đã bắt máy.
        """
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        explicit = self.search(
            domain_user + [
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
                ('vd_no_quote_state', '=', 'pending'),
            ],
            limit=limit,
            order='vd_no_quote_callback_date asc, create_date desc',
        )
        if not explicit:
            return []
        return self._dashboard_serialize_leads(explicit)

    @api.model
    def dashboard_leads_lost(self, user_id=None, limit=200):
        """Trả KH đã hủy (stage_is_lost=True). Dùng cho ô 'Khách hủy' ở
        bảng KHÁCH MỚI (split 2 nửa) của dashboard.

        ⚠️ write() tự động archive (active=False) khi chuyển stage sang lost
        (xem crm_lead.py:2311) → phải dùng with_context(active_test=False) để
        search cả archived records, nếu không sẽ không tìm thấy KH nào.
        """
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        # CHỜ DUYỆT thôi: KH đã DUYỆT hủy biến mất khỏi bảng KH HỦY (đã chuyển
        # sang thùng rác công ty). approved → ẩn; proposed/legacy(None) → hiện.
        leads = self.with_context(active_test=False).search(
            domain_user + [('stage_is_lost', '=', True),
                           ('vd_cancel_state', '!=', 'approved')],
            limit=limit,
            order='write_date desc, create_date desc',
        )
        data = self._dashboard_serialize_leads(leads)
        # Gắn GHI ÂM gần nhất cho từng KH (dùng chung bảng KH hủy với màn trưởng
        # phòng → cột "Ghi âm gần nhất"). 1 query cho tất cả lead.
        if leads:
            rec_by_lead = {}
            _rec_calls = self.env['stringee.call'].sudo().search([
                ('lead_id', 'in', leads.ids),
                ('recording_attachment_id', '!=', False),
            ], order='create_date desc')
            for c in _rec_calls:
                lid = c.lead_id.id
                if lid in rec_by_lead:
                    continue
                _ldt = (fields.Datetime.context_timestamp(c, c.create_date)
                        if c.create_date else None)
                rec_by_lead[lid] = {
                    'rec_url': '/web/content/%s?download=false' % c.recording_attachment_id.id,
                    'rec_time': _ldt.strftime('%d/%m %H:%M') if _ldt else '',
                    'rec_dur': c.duration or 0,
                }
            for d in data:
                d.update(rec_by_lead.get(d.get('id'), {'rec_url': '', 'rec_time': '', 'rec_dur': 0}))
        # Bỏ tiền tố "[Chủ đề] • " trong tóm tắt (đã có pill Chủ đề) → gộp 1 cột.
        import re as _re
        for d in data:
            d['cancel_reason_short'] = _re.sub(
                r'^\[[^\]]*\]\s*[•·]\s*', '', d.get('cancel_reason_short') or '')
        return data

    @api.model
    def dashboard_cancel_report(self, user_id=None):
        """Báo cáo KH mới vs Hủy cho PHẠM VI hiện tại (NV: chính mình; trưởng nhóm:
        phòng mình; manager: NV được chọn / toàn bộ). Trả LIST 6 kỳ — DÙNG CHUNG
        bảng thống kê với popover thùng rác màn trưởng phòng (đồng bộ)."""
        scope_user, _label, _du, _cu = self._dashboard_resolve_scope(user_id)
        if scope_user:
            uids = scope_user.ids
        elif self._dashboard_is_team_leader():
            uids = self._dashboard_team_member_ids()
        else:
            sg = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
            uids = self.env['res.users'].search([
                ('share', '=', False), ('active', '=', True),
            ] + ([('groups_id', 'in', sg.id)] if sg else [])).ids
        if not uids:
            return []
        by_user = self._vd_newcancel_report_by_user(uids)
        agg = None
        for uid in uids:
            for i, r in enumerate(by_user.get(uid) or []):
                if agg is None or i >= len(agg):
                    if agg is None:
                        agg = []
                    agg.append({'label': r['label'], 'created': 0, 'cancelled': 0, 'pct': 0.0})
                agg[i]['created'] += r['created']
                agg[i]['cancelled'] += r['cancelled']
        if not agg:
            return []
        for p in agg:
            p['pct'] = round(p['cancelled'] * 100.0 / p['created'], 1) if p['created'] else 0.0
        return agg

    @api.model
    def dashboard_company_trash(self, limit=1000):
        """Thùng rác CÔNG TY — KH đã được admin DUYỆT hủy (vd_cancel_state=
        'approved') của MỌI NV. CHỈ Admin + Giám đốc xem.

        Dùng active_test=False vì KH huỷ bị archive (active=False).
        """
        if not self._can_see_company_trash():
            return []
        leads = self.with_context(active_test=False).search(
            [('stage_is_lost', '=', True), ('vd_cancel_state', '=', 'approved')],
            limit=limit,
            order='vd_cancel_approved_date desc, write_date desc',
        )
        return self._dashboard_serialize_leads(leads)

    @api.model
    def dashboard_trash_restore(self, lead_ids):
        """Khôi phục KH khỏi thùng rác → trả về pipeline (stage 'new', bỏ
        archive, xoá trạng thái hủy). CHỈ Admin + Giám đốc."""
        if not self._can_see_company_trash():
            return {'ok': False, 'message': 'Bạn không có quyền.'}
        leads = self.with_context(active_test=False).browse(lead_ids or [])
        leads = leads.exists()
        if not leads:
            return {'ok': False, 'message': 'Không tìm thấy KH.'}
        new_stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False) \
            or self.env['crm.stage'].search([('code', '=', 'new')], limit=1)
        vals = {
            'active': True,
            'vd_cancel_state': False,
            'vd_cancel_approved_by_id': False,
            'vd_cancel_approved_date': False,
        }
        if new_stage:
            vals['stage_id'] = new_stage.id
        leads.with_context(mail_notrack=True, tracking_disable=True).write(vals)
        for rec in leads:
            rec.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('♻️ <b>Khôi phục từ thùng rác</b> bởi %s — KH trở lại pipeline.')
                % self.env.user.name,
            )
        return {'ok': True, 'message': 'Đã khôi phục %d KH về pipeline.' % len(leads)}

    @api.model
    def dashboard_trash_delete(self, lead_ids):
        """Xoá VĨNH VIỄN KH khỏi DB. CHỈ Admin + Giám đốc. Không khôi phục được."""
        if not self._can_see_company_trash():
            return {'ok': False, 'message': 'Bạn không có quyền.'}
        leads = self.with_context(active_test=False).browse(lead_ids or [])
        leads = leads.exists()
        if not leads:
            return {'ok': False, 'message': 'Không tìm thấy KH.'}
        n = len(leads)
        leads.sudo().unlink()
        return {'ok': True, 'message': 'Đã xoá vĩnh viễn %d KH.' % n}

    def _today_call_category(self, lead, urgent_ids):
        """Nhãn nhóm KH cho bảng cuộc gọi hôm nay."""
        if lead.stage_is_lost:
            return 'KH huỷ'
        if lead.stage_is_won:
            return 'Đã chốt'
        if lead.id in urgent_ids:
            return 'Thi công gấp'
        code = lead.stage_id.code
        if code in ('quote', 'negotiate') and lead.vd_intake_locked:
            return 'Xử lý vấn đề'
        if code == 'new' or code in ('quote', 'negotiate'):
            return 'Khách mới'
        return lead.stage_id.name or '—'

    def _today_call_result(self, call):
        """(nhãn, class) kết quả 1 cuộc gọi."""
        if call.state == 'answered' or (call.state == 'ended' and (call.duration or 0) > 0):
            return ('Nghe máy', 'ok')
        return {
            'no_answer': ('Không nghe máy', 'noans'),
            'busy': ('Máy bận', 'busy'),
            'declined': ('Từ chối', 'busy'),
            'failed': ('Thuê bao', 'sub'),
            'cancelled': ('Đã huỷ', 'cancel'),
            'ringing': ('Đang đổ chuông', 'ring'),
            'initiated': ('Đang gọi', 'ring'),
            'ended': ('Không kết nối', 'cancel'),
        }.get(call.state, (call.state or '—', 'cancel'))

    @api.model
    def dashboard_nv_today_calls(self, user_id):
        """Danh sách KH mà NV (user_id) đã GỌI hôm nay + báo cáo tổng hợp.

        Mỗi KH: tên, SĐT, nhóm (Khách mới / Thi công gấp / Xử lý vấn đề / ...),
        danh sách cuộc gọi (giờ, thời lượng, kết quả, link ghi âm) + tổng hợp.
        Chỉ manager (hoặc chính NV) xem.
        """
        uid = int(user_id)
        if not self._dashboard_is_manager() and uid != self.env.user.id:
            return {'summary': {}, 'customers': []}
        today = fields.Date.context_today(self)
        today_start = fields.Datetime.to_datetime(today)
        today_end = today_start + timedelta(days=1)
        Call = self.env['stringee.call'].sudo()
        calls = Call.search([
            ('user_id', '=', uid),
            ('create_date', '>=', today_start),
            ('create_date', '<', today_end),
            ('lead_id', '!=', False),
        ], order='create_date desc')
        empty_summary = {
            'total_calls': 0, 'customers': 0, 'answered_customers': 0,
            'talk_seconds': 0, 'answered': 0, 'no_answer': 0, 'busy': 0,
            'subscriber': 0,
        }
        if not calls:
            return {'summary': empty_summary, 'customers': []}

        def is_success(c):
            return c.state == 'answered' or (c.state == 'ended' and (c.duration or 0) > 0)

        from collections import OrderedDict
        by_lead = OrderedDict()
        n_ans = n_noans = n_busy = n_sub = 0
        talk_seconds = 0
        answered_lead_ids = set()
        for c in calls:
            lid = c.lead_id.id
            if is_success(c):
                n_ans += 1
                talk_seconds += (c.duration or 0)
                answered_lead_ids.add(lid)
            elif c.state == 'no_answer':
                n_noans += 1
            elif c.state in ('busy', 'declined'):
                n_busy += 1
            elif c.state == 'failed':
                n_sub += 1
            local_dt = (fields.Datetime.context_timestamp(c, c.start_time or c.create_date)
                        if (c.start_time or c.create_date) else None)
            att = c.recording_attachment_id
            result, rcls = self._today_call_result(c)
            by_lead.setdefault(lid, []).append({
                'time': local_dt.strftime('%H:%M') if local_dt else '',
                'duration': c.duration or 0,
                'result': result,
                'result_class': rcls,
                'recording_url': ('/web/content/%s?download=false' % att.id) if att else '',
            })

        lead_id_list = list(by_lead.keys())
        # 'Thi công gấp' = lead có problem urgent đang mở — TRA CỨU read-only
        # (KHÔNG gọi _dashboard_urgent_construction_ids vì hàm đó auto-tạo problem).
        urgent_ids = set()
        urgent_tag = self.env.ref(
            'vd_crm_lead.nego_problem_urgent_construction', raise_if_not_found=False)
        if urgent_tag:
            urgent_ids = set(self.env['vd.lead.problem'].sudo().search([
                ('lead_id', 'in', lead_id_list),
                ('tag_id', '=', urgent_tag.id),
                ('status', 'in', ['open', 'in_progress']),
            ]).mapped('lead_id').ids)
        leads = self.with_context(active_test=False).browse(lead_id_list)
        cat_by_lead = {l.id: self._today_call_category(l, urgent_ids) for l in leads}
        name_by_lead = {l.id: (l.name or l.partner_name or 'KH') for l in leads}
        phone_by_lead = {l.id: (l.phone or '') for l in leads}
        cat_class_map = {
            'Khách mới': 'new', 'Thi công gấp': 'urgent', 'Xử lý vấn đề': 'xlvd',
            'Đã chốt': 'won', 'KH huỷ': 'lost',
        }

        customers = []
        for lid, cl in by_lead.items():
            cat = cat_by_lead.get(lid, '')
            customers.append({
                'lead_id': lid,
                'name': name_by_lead.get(lid, 'KH'),
                'phone': phone_by_lead.get(lid, ''),
                'category': cat,
                'cat_class': cat_class_map.get(cat, 'other'),
                'call_count': len(cl),
                'total_duration': sum(x['duration'] for x in cl),
                'has_success': lid in answered_lead_ids,
                'calls': cl,
            })
        summary = {
            'total_calls': len(calls),
            'customers': len(by_lead),
            'answered_customers': len(answered_lead_ids),
            'talk_seconds': talk_seconds,
            'answered': n_ans,
            'no_answer': n_noans,
            'busy': n_busy,
            'subscriber': n_sub,
        }
        return {'summary': summary, 'customers': customers}

    @api.model
    def dashboard_nv_active_leads(self, user_id, limit=30):
        """Danh sách KH đang active của 1 NV — dùng cho NV detail panel
        khi admin click vào NV trong tab Thành tích."""
        if not self._dashboard_is_manager():
            return []
        leads = self.search([
            ('user_id', '=', user_id),
            ('stage_is_won', '=', False),
            ('stage_is_lost', '=', False),
        ], order='probability desc, callback_date asc', limit=limit)
        return self._dashboard_serialize_leads(leads)

    @api.model
    def _dashboard_serialize_leads(self, leads):
        # Tổng hợp thống kê cuộc gọi cho tất cả leads trong batch — 1 query duy nhất
        call_stats_by_lead = self._dashboard_compute_call_stats(leads)
        _today_d = fields.Date.context_today(self)  # cho cờ 'cần hỗ trợ' (active = hôm nay)

        import re as _re
        _urgent_tag = self.env.ref(
            'vd_crm_lead.nego_problem_urgent_construction',
            raise_if_not_found=False,
        )
        _urgent_tag_id = _urgent_tag.id if _urgent_tag else 0

        def _fmt_urgent_label(timeline_str):
            """'Càng sớm càng tốt,Tháng 10/2026' → 'THÁNG 10 - CÀNG SỚM CÀNG TỐT'."""
            if not timeline_str:
                return 'THI CÔNG GẤP'
            parts = [s.strip() for s in timeline_str.split(',') if s.strip()]
            months, others = [], []
            pat = _re.compile(r'Tháng\s+(\d{1,2})\s*/\s*(\d{4})', _re.IGNORECASE)
            for p in parts:
                m = pat.search(p)
                if m:
                    months.append('THÁNG %d' % int(m.group(1)))
                else:
                    others.append(p.upper())
            ordered = months + others
            return ' - '.join(ordered) if ordered else 'THI CÔNG GẤP'

        def _calls_since(lead_id, since_dt):
            if not since_dt:
                return 0
            return self.env['stringee.call'].search_count([
                ('lead_id', '=', lead_id),
                ('start_time', '>=', since_dt),
            ])

        def _lead_problems(l, exclude_urgent=False):
            open_probs = l.vd_lead_problem_ids.filtered(
                lambda p: p.status in ('open', 'in_progress')
            ).sorted(key=lambda p: (p.sequence, p.id))
            out = []
            for p in open_probs[:8]:
                if p.tag_id and p.tag_id.id == _urgent_tag_id:
                    if exclude_urgent:
                        continue  # cũ: TCG tách urgent ra cột riêng
                    # User spec 2026-05-28 round 5: badge dùng tag.name
                    # ("Thi công gấp") thay vì format "THÁNG X · 📞 N"
                    # (timeline + call count đã ở urgent_label cột riêng).
                    nm = p.tag_id.name
                    ic = p.tag_id.icon or '⚡'
                elif p.tag_id:
                    nm = p.tag_id.name
                    ic = p.tag_id.icon or '🔸'
                else:
                    text = (p.name or '').strip()
                    nm = text
                    for sep in (':', '—', ' – ', ' - '):
                        if sep in text:
                            nm = text.split(sep, 1)[0].strip()
                            break
                    ic = '🔸'
                out.append({
                    'name': nm, 'icon': ic, 'status': p.status,
                    # Đếm ngược hạn xử lý (user spec 2026-06-06) — chỉ theo NGÀY.
                    'deadline_state': p.deadline_state,
                    'days_left': p.days_left,
                    'deadline_label': p.deadline_label or '',
                })
            return out

        def _lead_urgent_label(l):
            """Trả label urgent timeline (vd 'THÁNG 5/2026 · 📞 0').
            Empty nếu lead không match urgent problem."""
            urgent_p = l.vd_lead_problem_ids.filtered(
                lambda p: p.status in ('open', 'in_progress')
                and p.tag_id.id == _urgent_tag_id
            )[:1]
            if not urgent_p:
                return ''
            p = urgent_p
            label = _fmt_urgent_label(l.vd_intake_timeline)
            calls_n = _calls_since(l.id, p.create_date)
            icon = p.tag_id.icon or '⚡'
            return '%s %s · 📞 %d' % (icon, label, calls_n)

        return [{
            'id': l.id,
            'name': l.name,
            'phone': l.phone or l.mobile or '',
            'user_name': l.user_id.name or '',
            'probability': round(l.probability, 1),
            'callback_date': fields.Datetime.to_string(l.callback_date) if l.callback_date else '',
            'last_call_date': fields.Datetime.to_string(l.last_call_date) if l.last_call_date else '',
            'no_answer_streak': l.no_answer_streak,
            'is_overdue_callback': l.is_overdue_callback,
            'is_today_callback': l.is_today_callback,
            'is_stale': l.is_stale,
            'priority': l.priority,
            'expected_revenue': l.expected_revenue,
            # Lịch hẹn ký HĐ (cho card view ở stage Khách chốt)
            'planned_sign_date': fields.Datetime.to_string(l.vd_planned_sign_date) if l.vd_planned_sign_date else '',
            'planned_sign_location': l.vd_planned_sign_location or '',
            'planned_sign_note': l.vd_planned_sign_note or '',
            'planned_sign_countdown': l.vd_planned_sign_countdown or '',
            'planned_sign_urgency': l.vd_planned_sign_urgency or '',
            'contract_signed': l.vd_contract_signed,
            'province_name': l.vd_intake_province_id.name or '' if l.vd_intake_province_id else '',
            'intake_timeline': l.vd_intake_timeline or '',
            'quote_price': l.vd_quote_price or 0,
            'has_quote': bool(l.vd_quote_price and l.vd_quote_price > 0),
            # has_intake_complete = báo giá đã hiện (đủ 11 trường). User spec
            # 2026-05-27: pill xanh lá đậm + icon báo giá khi complete nhưng
            # chưa CHỐT (locked=False).
            'intake_complete': bool(l.vd_intake_complete),
            'intake_locked': bool(l.vd_intake_locked),
            # Đã bấm "TƯ VẤN QUA ZALO" chưa (hiện ✓ trên header popup).
            'zalo_consulted': bool(l.vd_zalo_consulted_date),
            'zalo_not_found': bool(l.vd_zalo_not_found),
            # Số ngày từ lúc tạo KH (cho cảnh báo "có thể tư vấn Zalo" — ≥2 ngày).
            'create_days': (fields.Datetime.now() - l.create_date).days if l.create_date else 0,
            # Tạm huỷ báo giá → pill mất xanh, coi như chưa làm báo giá.
            'quote_cancelled': bool(l.vd_quote_cancelled),
            # Nguồn KH: facebook/tiktok/instagram/other/manual — quyết định màu pill
            'pancake_platform': (
                l.vd_pancake_page_id.platform if l.vd_pancake_page_id else 'manual'
            ),
            'stage_code': l.stage_code or '',
            # Team/Công ty: extract prefix từ tên NV (vd: "HCM1 - Mai" → "HCM1")
            'team_label': self._vd_team_label_for(l.user_id),
            # Số vấn đề đang mở (chưa resolved). >0 → tách ra bảng riêng.
            'problem_open_count': l.vd_lead_problem_open_count,
            # Cờ 'cần cấp trên hỗ trợ' — active theo scope (today=hôm nay / multi=đến khi chốt).
            'need_help': l._vd_need_help_active(_today_d),
            'need_help_scope': l.vd_need_help_scope or 'today',
            'help_status': l.vd_help_status or '',
            # Danh sách vấn đề (max 8) để render badge inline trên dashboard rows.
            'problems': _lead_problems(l),
            # User spec 2026-05-28: TCG tách urgent ra cột riêng + show vấn đề khác
            'urgent_label': _lead_urgent_label(l),
            'problems_non_urgent': _lead_problems(l, exclude_urgent=True),
            # Số ngày từ lúc báo giá chi tiết xuất hiện. Fallback create_date
            # cho lead cũ chưa có latch (chưa migrate field này).
            'quote_days': (
                (fields.Datetime.now() - (l.vd_quote_created_date or l.create_date)).days
                if (l.vd_quote_created_date or (l.vd_intake_locked and l.create_date))
                else None
            ),
            # Thống kê cuộc gọi → frontend quyết định màu pill (xanh/lá/đỏ)
            'call_stats': call_stats_by_lead.get(l.id, {
                'total': 0, 'answered': 0, 'answered_long': 0,
                'no_answer': 0, 'busy_like': 0, 'subscriber': 0,
                'distinct_days': 0, 'distinct_days_subscriber': 0,
                'days_no_answer': 0, 'has_call_today': False,
                'recent_calls': [],
                'unreachable': 0, 'distinct_days_unreachable': 0,
            }),
            # ÉP ZALO (user spec 2026-06-09): KH 'new' đã ≥2 lần đổ chuông không
            # nghe (số khỏe) mà chưa kết bạn Zalo/chưa báo giá → cảnh báo mạnh.
            'must_zalo': self._vd_lead_must_zalo(
                l, call_stats_by_lead.get(l.id, {})),
            # Cảnh báo "cần gọi hôm nay" — chỉ stage 'new':
            #   Day 1 (ngày tạo): skip
            #   Day 2: cumulative distinct_days >= 1
            #   Day 3: cumulative distinct_days >= 2
            #   Day 4: cumulative distinct_days >= 3
            # Border xanh nếu: behind schedule + chưa gọi hôm nay.
            'needs_call_today': self._vd_pill_needs_call_today(
                l, call_stats_by_lead.get(l.id, {}),
            ),
            # ===== CHƯA BÁO GIÁ info (round 11) — cho THAM KHẢO popover =====
            'no_quote_state': l.vd_no_quote_state or '',
            'no_quote_category': l.vd_no_quote_category or '',
            'no_quote_category_label': dict(
                l._fields['vd_no_quote_category'].selection
            ).get(l.vd_no_quote_category, '') if l.vd_no_quote_category else '',
            'no_quote_callback_date': fields.Date.to_string(l.vd_no_quote_callback_date) if l.vd_no_quote_callback_date else '',
            'no_quote_callback_due': bool(
                l.vd_no_quote_callback_date and l.vd_no_quote_callback_date <= fields.Date.today()
            ),
            # Số ngày ĐẾM NGƯỢC tới ngày gọi lại (âm/0 = tới hạn). None = legacy.
            'no_quote_callback_days': (
                (l.vd_no_quote_callback_date - fields.Date.today()).days
                if l.vd_no_quote_callback_date else None),
            'no_quote_reason_short': (l.vd_no_quote_reason or '').strip()[:160],
            # ===== Đề xuất hủy info (cho thùng rác) =====
            'cancel_state': l.vd_cancel_state or '',
            'cancel_category': l.vd_cancel_category or '',
            'cancel_category_label': dict(
                l._fields['vd_cancel_category'].selection
            ).get(l.vd_cancel_category, '') if l.vd_cancel_category else '',
            'cancel_reason_short': (l.vd_lost_reason or '').strip()[:160],
            'cancel_proposed_date': fields.Datetime.to_string(l.vd_lost_date) if l.vd_lost_date else '',
            'cancel_proposed_by_name': l.vd_lost_user_id.name if l.vd_lost_user_id else '',
            'cancel_approved_by_name': l.vd_cancel_approved_by_id.name if l.vd_cancel_approved_by_id else '',
        } for l in leads]

    @api.model
    def _vd_pill_needs_call_today(self, lead, stats):
        """True khi blue border cần hiện (NV cần gọi hôm nay).

        Conditions ALL true:
        - stage = 'new'
        - days_since_create in [1, 4]
        - total > 0 (KHÔNG áp dụng cho thẻ trắng = chưa gọi cuộc nào)
        - distinct_days < 3 (đủ 3 ngày → off border, lead đã đủ pace)
        - distinct_days < days_since (behind schedule)
        - has_call_today = False (chưa gọi hôm nay)
        """
        if lead.stage_code != 'new':
            return False
        if not lead.create_date:
            return False
        # Bỏ qua thẻ trắng (chưa có cuộc gọi nào) — user spec 2026-05-27
        if (stats.get('total') or 0) == 0:
            return False
        # Đủ 3 ngày khác nhau → không cần báo nữa
        if (stats.get('distinct_days') or 0) >= 3:
            return False
        if stats.get('has_call_today'):
            return False
        from datetime import date as _date
        today = _date.today()
        days_since = (today - lead.create_date.date()).days
        if days_since < 1 or days_since > 4:
            return False
        required = days_since
        actual = stats.get('distinct_days', 0)
        return actual < required

    @api.model
    def _vd_auto_trash_no_answer_leads(self, domain_user):
        """Auto-HỦY KH stage 'new' bị THUÊ BAO / SAI SỐ (state 'failed') trên ≥4
        NGÀY khác nhau mà CHƯA TỪNG đổ chuông (số hỏng/sai) → chuyển stage 'lost'
        (user spec 2026-06-21).

        ĐIỀU KIỆN DUY NHẤT cho tự động hủy (mọi case khác NV phải tự bấm xác nhận):
        - answered == 0          : KH chưa từng bắt máy
        - reached_no_answer == 0 : KH CHƯA TỪNG ĐỔ CHUÔNG (no_answer/busy/declined).
                                   → có chuông dù chỉ 1 lần = số ĐÚNG, KHÔNG auto-hủy.
        - distinct_days_subscriber >= 4 : toàn thuê bao/sai số trên ≥4 ngày khác nhau.
        KH đổ chuông không nghe = thuộc 'CHƯA GỌI ĐƯỢC' (NV gọi lại / Zalo), KHÔNG
        bao giờ tự vào thùng rác."""
        candidates = self.search(
            domain_user + [
                ('stage_id.code', '=', 'new'),
                ('active', '=', True),
                ('call_count', '>=', 4),
            ],
        )
        if not candidates:
            return
        stats = self._dashboard_compute_call_stats(candidates)
        to_archive_ids = [
            lid for lid, s in stats.items()
            if s.get('answered', 0) == 0
            and s.get('reached_no_answer', 0) == 0      # chưa từng đổ chuông
            and s.get('distinct_days_subscriber', 0) >= 4   # thuê bao ≥4 ngày
        ]
        if not to_archive_ids:
            return
        lost_stage = self.env['crm.stage'].search([('is_lost', '=', True)], limit=1)
        if not lost_stage:
            return
        reason = 'Tự động: thuê bao/sai số 4+ ngày khác nhau (số hỏng, chưa từng đổ chuông)'
        self.browse(to_archive_ids).with_context(mail_notrack=True).write({
            'stage_id': lost_stage.id,
            'vd_lost_reason': reason,
            'vd_lost_date': fields.Datetime.now(),
            'vd_lost_user_id': False,    # cron — không có user
            'vd_lost_is_auto': True,
        })

    @api.model
    def _vd_newcancel_report_by_user(self, user_ids):
        """Báo cáo KHÁCH MỚI vs HỦY THEO TỪNG NV, 6 kỳ: hôm nay, hôm qua, 2 ngày
        trước, 3 ngày trước, tuần này, tháng này. Mỗi kỳ: tạo mới, hủy, % hủy.
        Tính theo MÚI GIỜ VN. Trả {uid: [{label,created,cancelled,pct}, ...]}.
        read_group → 12 query cho TOÀN BỘ NV (không lặp theo user)."""
        if not user_ids:
            return {}
        import pytz
        from datetime import datetime as _dt, time as _time, timedelta as _td2
        tzname = self.env.context.get('tz') or self.env.user.tz or 'Asia/Ho_Chi_Minh'
        tz = pytz.timezone(tzname)
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()

        def _utc_midnight(d):
            local = tz.localize(_dt.combine(d, _time.min))
            return local.astimezone(pytz.utc).replace(tzinfo=None)

        d0 = _utc_midnight(today)
        d1 = _utc_midnight(today - _td2(days=1))
        d2 = _utc_midnight(today - _td2(days=2))
        d3 = _utc_midnight(today - _td2(days=3))
        wk = _utc_midnight(today - _td2(days=today.weekday()))
        mo = _utc_midnight(today.replace(day=1))
        # (label, start, end) — kỳ NGÀY ĐƠN có end = đầu ngày kế; kỳ tích lũy end=now
        periods = [
            ('Hôm nay', d0, now),
            ('Hôm qua', d1, d0),
            ((today - _td2(days=2)).strftime('%d/%m'), d2, d1),
            ((today - _td2(days=3)).strftime('%d/%m'), d3, d2),
            ('Tuần này', wk, now),
            ('Tháng này', mo, now),
        ]
        # init: mỗi user 1 list rỗng theo thứ tự periods
        result = {uid: [{'label': p[0], 'created': 0, 'cancelled': 0, 'pct': 0.0}
                        for p in periods] for uid in user_ids}
        for idx, (_label, start, end) in enumerate(periods):
            for g in self.read_group(
                [('user_id', 'in', user_ids),
                 ('create_date', '>=', start), ('create_date', '<', end)],
                ['user_id'], ['user_id'],
            ):
                if g.get('user_id'):
                    result[g['user_id'][0]][idx]['created'] = g['user_id_count']
            for g in self.with_context(active_test=False).read_group(
                [('vd_lost_user_id', 'in', user_ids),
                 ('stage_is_lost', '=', True),
                 ('vd_lost_date', '>=', start), ('vd_lost_date', '<', end)],
                ['vd_lost_user_id'], ['vd_lost_user_id'],
            ):
                if g.get('vd_lost_user_id'):
                    result[g['vd_lost_user_id'][0]][idx]['cancelled'] = g['vd_lost_user_id_count']
        for uid in user_ids:
            for cell in result[uid]:
                c, x = cell['created'], cell['cancelled']
                cell['pct'] = round(x * 100.0 / c, 1) if c else 0.0
        return result

    @api.model
    @api.model
    def _vd_dead_caller_numbers(self):
        """Set số tổng đài đang CHẾT (vd.stringee.hotline.vd_health='dead', không
        ép xanh). Cuộc gọi từ các số này KHÔNG đổ chuông tới khách → bỏ qua khi
        phân loại 'đã gọi / chưa gọi được' (user spec 2026-06-09). Guard nếu
        module vd_stringee chưa cài."""
        Hotline = self.env.get('vd.stringee.hotline')
        if Hotline is None:
            return set()
        deads = Hotline.sudo().with_context(active_test=False).search([
            ('vd_health', '=', 'dead'),
            ('vd_force_alive', '=', False),
        ])
        return set(n for n in deads.mapped('number') if n)

    def _vd_lead_must_zalo(self, lead, stats):
        """User spec 2026-06-09: KH ở stage 'new' đã ≥2 lần ĐỔ CHUÔNG KHÔNG NGHE
        (từ số khỏe — reached_no_answer) mà CHƯA kết bạn Zalo và CHƯA báo giá
        → BẮT BUỘC chuyển hướng Zalo (cảnh báo mạnh, KHÔNG chặn gọi).
        Đã từng nghe máy (answered>0) → thôi (đã liên lạc được)."""
        if (lead.stage_code or '') != 'new':
            return False
        # Đã nhắn Zalo / đã báo giá / KHÔNG TÌM THẤY Zalo → thôi ép (2026-06-10).
        if (lead.vd_zalo_consulted_date or lead.vd_intake_complete
                or lead.vd_zalo_not_found):
            return False
        s = stats or {}
        if s.get('answered', 0) > 0:
            return False
        return s.get('reached_no_answer', 0) >= 2

    def _dashboard_compute_call_stats(self, leads, since_by_lead=None):
        """Trả dict {lead_id: {total, answered, no_answer, busy_like,
        subscriber, distinct_days, distinct_days_subscriber}} cho batch leads.

        Phân loại trạng thái cuộc gọi:
        - answered: nói chuyện được (duration>0 / state='answered' / 'ended' có answer_time)
        - no_answer: chuông kêu nhưng không bắt (state='no_answer')
        - busy_like: máy bận / từ chối (state in 'busy','declined')
        - subscriber: thuê bao (state='failed' — không kết nối được tới máy KH)
        - cancelled: NV tự huỷ trước khi bắt → bỏ qua, không tính vào nhóm nào.
        """
        from collections import defaultdict
        from datetime import date as _date
        today_date = _date.today()
        result = {}
        if not leads:
            return result
        # User spec 2026-06-09: BỎ QUA cuộc gọi từ SỐ TỔNG ĐÀI CHẾT mà không đổ
        # chuông (cuộc "ma" do số công ty hỏng, không phải khách sai số) → khách
        # chỉ-bị-gọi-bằng-số-chết tự quay về "chưa gọi".
        dead_numbers = self._vd_dead_caller_numbers()
        calls = self.env['stringee.call'].search_read(
            [('lead_id', 'in', leads.ids)],
            ['lead_id', 'state', 'duration', 'answer_time', 'start_time',
             'recording_url', 'caller_number'],
        )
        by_lead = defaultdict(list)
        for c in calls:
            lid = c['lead_id'][0] if c['lead_id'] else False
            if lid:
                by_lead[lid].append(c)
        for lead_id, lcalls in by_lead.items():
            # User spec 2026-05-30: chỉ tính cuộc gọi KỂ TỪ khi báo giá thành công
            # (nếu since_by_lead có mốc ngày cho lead này).
            since = (since_by_lead or {}).get(lead_id)
            if since:
                lcalls = [
                    c for c in lcalls
                    if c.get('start_time') and c['start_time'] >= since
                ]
            # Loại cuộc VÔ GIÁ TRỊ: từ số chết + chưa từng nghe máy (không
            # answer_time, không duration>0). Cuộc nghe máy thật vẫn giữ.
            if dead_numbers:
                lcalls = [
                    c for c in lcalls
                    if not (
                        c.get('caller_number') in dead_numbers
                        and not c.get('answer_time')
                        and not ((c.get('state') in ('answered', 'ended'))
                                 and (c.get('duration') or 0) > 0)
                    )
                ]
            total = len(lcalls)
            # Sort desc by start_time để recent_calls hiển thị mới nhất trước
            lcalls_sorted = sorted(
                lcalls,
                key=lambda c: c.get('start_time') or '',
                reverse=True,
            )
            answered = 0
            answered_long = 0  # answered + duration >= 120s
            no_answer = 0
            busy_like = 0
            subscriber = 0
            all_days = set()
            subscriber_days = set()
            days_answered = set()  # ngày có ≥1 cuộc liên lạc được
            has_call_today = False
            for c in lcalls:
                st = c.get('state')
                dur = c.get('duration') or 0
                # User spec 2026-05-28 (round 2): answered = state ∈ {answered, ended}
                # AND duration > 0. State='declined' với dur=1s (system ghi vài
                # giây ring trước khi reject) → KHÔNG phải answered.
                is_answered = (st in ('answered', 'ended')) and dur > 0
                start = c.get('start_time')
                day = start.date() if start and hasattr(start, 'date') else None
                if day:
                    all_days.add(day)
                    if day == today_date:
                        has_call_today = True
                if is_answered:
                    answered += 1
                    if dur >= 120:
                        answered_long += 1
                    if day:
                        days_answered.add(day)
                elif st == 'no_answer':
                    no_answer += 1
                elif st in ('busy', 'declined'):
                    busy_like += 1
                elif st == 'failed':
                    subscriber += 1
                    if day:
                        subscriber_days.add(day)
                # cancelled → bỏ qua
            # Số ngày không có cuộc nghe máy nào (mọi ngày có call mà KH không bắt)
            days_no_answer = len(all_days - days_answered)
            # Round 16: recent_calls — top 10 mới nhất với recording_url
            # cho popover hover badge (NV xem nhanh file ghi âm).
            recent_calls = []
            for c in lcalls_sorted[:10]:
                st = c.get('state') or ''
                dur = c.get('duration') or 0
                start = c.get('start_time')
                start_str = start.strftime('%d/%m %H:%M') if start and hasattr(start, 'strftime') else ''
                is_answered = (st in ('answered', 'ended')) and dur > 0
                recent_calls.append({
                    'time': start_str,
                    'state': st,
                    'duration': dur,
                    'is_answered': is_answered,
                    'recording_url': c.get('recording_url') or '',
                })
            result[lead_id] = {
                'total': total,
                'answered': answered,
                'answered_long': answered_long,
                'no_answer': no_answer,
                'busy_like': busy_like,
                'subscriber': subscriber,
                'distinct_days': len(all_days),
                'distinct_days_subscriber': len(subscriber_days),
                'days_no_answer': days_no_answer,
                # Cuộc ĐỔ CHUÔNG nhưng KHÔNG NGHE (từ số khỏe): no_answer + máy bận/
                # từ chối. Dùng cho "ép Zalo" (≥2 → must_zalo). subscriber=failed
                # = số khách sai → KHÔNG tính là đổ chuông.
                'reached_no_answer': no_answer + busy_like,
                'has_call_today': has_call_today,
                'recent_calls': recent_calls,
                # giữ field cũ để backward compatible nếu nơi nào còn ref
                'unreachable': busy_like + subscriber,
                'distinct_days_unreachable': len(subscriber_days),
            }
        return result

    @api.model
    def _vd_apply_quote_name_pattern(self):
        """Đổi tên lead khi TẠO BÁO GIÁ sang format:
        VINADUY - <Tên KH> - <MÃ TỈNH> - T<tháng>/<năm tạo báo giá>.
        (user spec 2026-06-08 — dùng MÃ TỈNH + tháng/năm thay cho Team.)
        Idempotent: name đã có prefix 'VINADUY - ' → bỏ qua."""
        self.ensure_one()
        if (self.name or '').startswith('VINADUY - '):
            return
        new_name = self._vd_build_quote_name()
        if new_name and new_name != self.name:
            self.with_context(mail_notrack=True).write({'name': new_name})

    @api.model
    def _vd_clean_input_name(self, name):
        """Chuẩn hoá tên KH MỚI: ép về dạng 'Anh Hải'/'Chị Minh'/tên đầy đủ.
        Strip aggressively:
          - Prefix nguồn: (Fanpage), [FB], [Pancake]...
          - Pattern 'VINADUY - X - <code>'
          - Prefix số-gạch: "21-Nguyễn..." → "Nguyễn..."
          - Suffix date pair dính liền: "Phúc12/5" → "Phúc"
          - Suffix gạch + code: " - HCM2", " - T5/26"
          - Token cuối toàn caps (HT, LĐ, ĐNA, AG, HCM, HCM2, BN, ...)
          - Token cuối cặp số: "19/3", "30-12", "1-11", "8/5"
        Pattern 'VINADUY - X - <team>' CHỈ được auto-apply sau khi báo giá
        (qua _vd_apply_quote_name_pattern).
        """
        if not name:
            return name
        import re
        s = name.strip()
        # 1. Prefix nguồn
        s = re.sub(r'^\((Fanpage|Tiktok|Instagram|Pancake)\)\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^\[(Pancake|FB|TT|IG|Zalo|Hotline|GT)\]\s*', '', s, flags=re.IGNORECASE)
        # 2. Pattern VINADUY → giữ phần giữa
        m = re.match(r'^VINADUY\s*[-–—]\s*(.+?)\s*[-–—]\s*[^-–—]+\s*$', s, re.IGNORECASE)
        if m:
            s = m.group(1).strip()
        # 3. Prefix số-gạch
        s = re.sub(r'^\d+\s*[-–—]\s*', '', s)
        # 4. Date pair dính liền cuối
        s = re.sub(r'(\D)\d+[-/]\d+\s*$', r'\1', s)
        # 5. Gạch + code cuối
        s = re.sub(r'\s*[-–—]\s*[A-ZĐ][A-ZĐ\d]{0,4}\s*$', '', s)
        # 6. Lặp strip token cuối nếu là caps-code hoặc cặp số
        upper_pat = re.compile(r'^[A-ZĐ][A-ZĐ\d]{1,4}$')
        num_pat = re.compile(r'^T?\d{1,2}[-/]\d{1,4}$')
        parts = s.split()
        while len(parts) > 1:
            last = parts[-1]
            if upper_pat.match(last) or num_pat.match(last):
                parts.pop()
            else:
                break
        return ' '.join(parts).strip() or name

    def _vd_team_label_for(self, user):
        """Lấy 'team label' từ tên NV (HCM1/HCM2/HCM3/HN/QN/...).
        Fallback dùng sale_team_id.name nếu không match prefix."""
        if not user:
            return 'KHÁC'
        # Ưu tiên thẻ Phòng ban admin gán (user spec 2026-06-13).
        if user.vd_team:
            return user.vd_team
        import re
        name = user.name or ''
        # Match prefix dạng "HCM1 - ", "HN - ", "QN - "...
        m = re.match(r'^([A-ZĐ]+\d*)\s*[-–—]\s*', name)
        if m:
            return m.group(1)
        # Fallback theo sale_team_id
        if user.sale_team_id and user.sale_team_id.name:
            return user.sale_team_id.name.upper()[:6]
        return 'KHÁC'

    # ============================================================
    # 🧠 SALES INSIGHTS DASHBOARD — admin tab "Tổng quan"
    # Trả ra insight thực sự để quản lý phòng KD ra quyết định:
    #   1. 🚨 Cần hành động ngay
    #   2. 📊 Sức khoẻ pipeline
    #   3. 🏆 Hiệu suất NV
    #   4. 🎯 Insight KH
    #   5. 💡 Gợi ý hành động (system-suggested)
    # ============================================================
    @api.model
    def dashboard_analytics(self, date_from=None, date_to=None, scope=None):
        """Insight payload cho admin dashboard — thay charts bằng list/table actionable.
        Chỉ manager được gọi.

        scope='team' (Giám đốc ở chế độ "CÁ NHÂN"): bó về NV cùng PHÒNG BAN với
        người xem (giống trưởng nhóm) thay vì toàn công ty.
        """
        # Manager (toàn cty) HOẶC trưởng nhóm (scope NV trong nhóm) — trưởng nhóm
        # dùng CHUNG bảng team của admin (user spec 2026-06-14).
        _is_mgr = self._dashboard_is_manager()
        _is_tl = self._dashboard_is_team_leader()
        # NV thường: KHÔNG raise nữa — cho xem CHÍNH MÌNH (1 dòng) để trang cá nhân
        # hiện thanh tổng quan DÙNG CHUNG template với bảng danh sách NV (tự đồng bộ).
        _self_only = not _is_mgr and not _is_tl
        # Trưởng nhóm: chỉ NV cùng phòng ban (gồm chính họ). Giám đốc chế độ CÁ
        # NHÂN (scope='team') cũng bó về phòng ban mình.
        _tl_member_ids = self._dashboard_team_member_ids() if (
            (_is_tl and not _is_mgr) or (_is_mgr and scope == 'team')) else None

        from datetime import timedelta as _td
        from collections import defaultdict, Counter
        import re

        # === Parse date range — fallback 90 ngày gần nhất ===
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        if date_to:
            d_to = fields.Date.from_string(date_to) if isinstance(date_to, str) else date_to
        else:
            d_to = today
        if date_from:
            d_from = fields.Date.from_string(date_from) if isinstance(date_from, str) else date_from
        else:
            d_from = d_to - _td(days=90)

        dt_from = fields.Datetime.to_datetime(d_from)
        dt_to = fields.Datetime.to_datetime(d_to) + _td(days=1)
        date_domain = [
            ('create_date', '>=', dt_from),
            ('create_date', '<', dt_to),
        ]

        ResUsers = self.env['res.users']
        # User spec 2026-06-09: ADMIN + QUẢN LÝ KHÔNG phải nhân viên → loại khỏi
        # danh sách NV (chỉ giữ salesman thuần). groups_id đã materialize cả group
        # implied nên manager/admin vẫn có group_salesman → phải loại tường minh.
        _sale_dom = [
            ('share', '=', False),
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ]
        _mgr_g = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
        _sys_g = self.env.ref('base.group_system', raise_if_not_found=False)
        if _mgr_g:
            _sale_dom.append(('groups_id', 'not in', _mgr_g.id))
        if _sys_g:
            _sale_dom.append(('groups_id', 'not in', _sys_g.id))
        if _tl_member_ids is not None:
            _sale_dom.append(('id', 'in', _tl_member_ids))
        # NV thường: bó về CHÍNH MÌNH (1 dòng cho thanh tổng quan cá nhân).
        sales_users = self.env.user if _self_only else ResUsers.search(_sale_dom)

        # User spec 2026-06-21: GIÁM ĐỐC KIÊM TRƯỞNG PHÒNG vẫn phải hiện 1 dòng
        # trong bảng phòng ban của họ (vd: Hồ A Du = Giám đốc + Trưởng phòng HN).
        # Giám đốc (deputy_director) implies group_sale_manager nên bị domain trên
        # loại ra → thêm lại tường minh (vẫn loại Admin/system). Họ giữ cờ
        # is_team_leader=True nên lên ĐẦU bảng phòng ban tương ứng (theo vd_team).
        _dir_g = self.env.ref('vd_crm_lead.vd_crm_group_deputy_director',
                              raise_if_not_found=False)
        if _dir_g and not _self_only:
            _dir_dom = [
                ('share', '=', False),
                ('active', '=', True),
                ('groups_id', 'in', _dir_g.id),
            ]
            if _sys_g:
                _dir_dom.append(('groups_id', 'not in', _sys_g.id))
            if _tl_member_ids is not None:
                _dir_dom.append(('id', 'in', _tl_member_ids))
            sales_users |= ResUsers.search(_dir_dom)

        sales_user_ids = sales_users.ids

        # User spec 2026-06-14: ĐỒNG BỘ số liệu giữa trưởng nhóm và admin. Mọi tính
        # toán bên dưới chạy SUDO → số KHÔNG phụ thuộc record-rule người xem (admin
        # full quyền vs trưởng nhóm). An toàn vì phạm vi đã giới hạn ở sales_user_ids
        # (admin = toàn cty; trưởng nhóm = NV trong nhóm).
        self = self.sudo()
        # NV có phân quyền TRƯỞNG NHÓM (để thẻ tên hiển thị kiểu cao cấp + lên đầu).
        _tl_group = self.env.ref('vd_crm_lead.vd_crm_group_team_leader', raise_if_not_found=False)
        _tl_user_ids = set(_tl_group.sudo().users.ids) if _tl_group else set()

        def _short_name(name):
            return re.sub(r'^[A-ZĐ]+\d*\s*[-–—]\s*', '', name or '') or (name or 'NV')

        def _team_pretty(label):
            colors = {'HN': '#dc2626', 'HCM1': '#16a34a', 'HCM2': '#9333ea', 'HCM3': '#d97706'}
            return {'name': label, 'color': colors.get(label, '#6c757d')}

        # ============ KPI TOP (5) ============
        total_deals = self.search_count(date_domain)
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT NULLIF(TRIM(phone), ''))
            FROM crm_lead
            WHERE create_date >= %s AND create_date < %s AND active = TRUE
        """, (dt_from, dt_to))
        unique_customers = self.env.cr.fetchone()[0] or 0
        closed_contracts = self.search_count(date_domain + [('vd_contract_signed', '=', True)])
        active_negotiations = self.search_count([
            ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
        ])

        # NV "ngồi không": chưa gọi cuộc nào >2 ngày, nhưng đang có KH active
        two_days_ago = now - _td(days=2)
        idle_nv_list = []
        for u in sales_users:
            active_count = self.search_count([
                ('user_id', '=', u.id),
                ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            ])
            if not active_count:
                continue
            recent_calls = self.env['stringee.call'].search_count([
                ('user_id', '=', u.id),
                ('create_date', '>=', two_days_ago),
            ])
            if recent_calls == 0:
                last_call = self.env['stringee.call'].search([
                    ('user_id', '=', u.id),
                ], order='create_date desc', limit=1)
                days_idle = ((now - last_call.create_date).days
                              if last_call else 99)
                idle_nv_list.append({
                    'user_id': u.id,
                    'name': _short_name(u.name),
                    'full_name': u.name,
                    'team': self._vd_team_label_for(u),
                    'days_idle': days_idle,
                    'active_leads': active_count,
                    'last_call_date': last_call.create_date.isoformat() if last_call else None,
                })
        idle_nv_list.sort(key=lambda x: (-x['days_idle'], -x['active_leads']))

        kpi = {
            'total_deals': total_deals,
            'unique_customers': unique_customers,
            'closed_contracts': closed_contracts,
            'active_negotiations': active_negotiations,
            'idle_nv_count': len(idle_nv_list),
            'conversion_pct': round((closed_contracts / total_deals * 100), 1) if total_deals else 0,
        }

        # ============ 🚨 SECTION 1: CẦN HÀNH ĐỘNG NGAY ============
        # 1a. Overdue callbacks (top 10)
        overdue_recs = self.search([
            ('callback_date', '<', now),
            ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            ('active', '=', True),
        ], order='callback_date asc', limit=10)
        overdue_callbacks = [{
            'lead_id': r.id,
            'name': r.name or r.partner_name or 'KH',
            'phone': r.phone or '',
            'user_name': _short_name(r.user_id.name) if r.user_id else '—',
            'team': self._vd_team_label_for(r.user_id) if r.user_id else 'KHÁC',
            'hours_overdue': int((now - r.callback_date).total_seconds() // 3600) if r.callback_date else 0,
            'callback_date': r.callback_date.isoformat() if r.callback_date else None,
        } for r in overdue_recs]

        # 1b. HĐ sắp ký / quá hạn (top 10)
        pending_signs = self.search([
            ('vd_planned_sign_date', '!=', False),
            ('vd_contract_signed', '=', False),
            ('stage_is_won', '=', True),
            ('active', '=', True),
        ], order='vd_planned_sign_date asc', limit=10)
        pending_signatures = []
        for r in pending_signs:
            if not r.vd_planned_sign_date:
                continue
            delta = r.vd_planned_sign_date - now
            days_until = delta.days
            urgency = (
                'past' if days_until < 0 else
                'today' if days_until == 0 else
                'soon' if days_until <= 2 else
                'far'
            )
            pending_signatures.append({
                'lead_id': r.id,
                'name': r.name or r.partner_name or 'KH',
                'phone': r.phone or '',
                'user_name': _short_name(r.user_id.name) if r.user_id else '—',
                'team': self._vd_team_label_for(r.user_id) if r.user_id else 'KHÁC',
                'planned_sign_date': r.vd_planned_sign_date.isoformat(),
                'days_until': days_until,
                'urgency': urgency,
                'location': r.vd_planned_sign_location or '',
            })

        # 1c. KH mới chưa gọi cuộc nào
        Stage = self.env['crm.stage']
        new_stage = Stage.search([('code', '=', 'new')], limit=1)
        uncalled_new = []
        if new_stage:
            uc_recs = self.search([
                ('stage_id', '=', new_stage.id),
                ('call_count', '=', 0),
                ('create_date', '<', now - _td(hours=6)),  # >6h chưa gọi
                ('active', '=', True),
            ], order='create_date asc', limit=10)
            for r in uc_recs:
                hours = int((now - r.create_date).total_seconds() // 3600) if r.create_date else 0
                uncalled_new.append({
                    'lead_id': r.id,
                    'name': r.name or r.partner_name or 'KH',
                    'phone': r.phone or '',
                    'user_name': _short_name(r.user_id.name) if r.user_id else 'CHƯA PHÂN',
                    'team': self._vd_team_label_for(r.user_id) if r.user_id else 'KHÁC',
                    'hours_since_created': hours,
                })

        urgent_section = {
            'overdue_callbacks': overdue_callbacks,
            'overdue_count': self.search_count([
                ('callback_date', '<', now),
                ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            ]),
            'idle_nvs': idle_nv_list[:8],
            'pending_signatures': pending_signatures,
            'uncalled_new': uncalled_new,
            'uncalled_count': self.search_count([
                ('stage_id', '=', new_stage.id if new_stage else False),
                ('call_count', '=', 0),
                ('create_date', '<', now - _td(hours=6)),
            ]) if new_stage else 0,
        }

        # ============ 📊 SECTION 2: SỨC KHOẺ PIPELINE ============
        # Funnel: stages new → quote → negotiate → won. Count active leads tại mỗi stage.
        # Conversion %: cumulative — KH tạo trong period đã reach stage X chưa.
        funnel_stages = Stage.search([
            ('code', 'in', ['new', 'quote', 'negotiate', 'won'])
        ], order='sequence')
        stage_code_seq = ['new', 'quote', 'negotiate', 'won']
        stage_seq_map = {s.code: i for i, s in enumerate(funnel_stages) if s.code in stage_code_seq}

        # Count active leads currently at each stage
        funnel_payload = []
        funnel_color = {
            'new': '#2563eb', 'quote': '#d97706',
            'negotiate': '#9333ea', 'won': '#16a34a',
        }
        for st in funnel_stages:
            c = self.search_count([('stage_id', '=', st.id), ('active', '=', True)])
            # Average age (days since create_date) of leads at this stage
            self.env.cr.execute("""
                SELECT EXTRACT(EPOCH FROM AVG(NOW() - create_date)) / 86400
                FROM crm_lead WHERE stage_id = %s AND active = TRUE
            """, (st.id,))
            avg_days_row = self.env.cr.fetchone()
            avg_days = round(avg_days_row[0], 1) if avg_days_row and avg_days_row[0] else 0
            funnel_payload.append({
                'code': st.code,
                'name': st.name,
                'count': c,
                'avg_days': avg_days,
                'color': funnel_color.get(st.code or '', '#6c757d'),
            })

        # Conversion: leads tạo trong period → bao nhiêu đã reach stage tiếp theo
        # Đếm leads tạo trong period có stage_id sequence >= sequence của stage target
        conversions = []
        try:
            new_seq = funnel_stages.filtered(lambda s: s.code == 'new').sequence or 1
            quote_seq = funnel_stages.filtered(lambda s: s.code == 'quote').sequence or 2
            nego_seq = funnel_stages.filtered(lambda s: s.code == 'negotiate').sequence or 3
            won_seq = funnel_stages.filtered(lambda s: s.code == 'won').sequence or 4
            def _count_reached(min_seq):
                return self.search_count(date_domain + [('stage_id.sequence', '>=', min_seq)])
            n_new = _count_reached(new_seq) or total_deals or 0
            n_quote = _count_reached(quote_seq)
            n_nego = _count_reached(nego_seq)
            n_won = closed_contracts
            steps = [
                ('Mới → Báo giá', n_new, n_quote, 'new', 'quote'),
                ('Báo giá → Đàm phán', n_quote, n_nego, 'quote', 'negotiate'),
                ('Đàm phán → Chốt', n_nego, n_won, 'negotiate', 'won'),
            ]
            for label, frm, to_val, frm_code, to_code in steps:
                pct = round((to_val / frm * 100), 1) if frm else 0
                conversions.append({
                    'label': label,
                    'from_count': frm, 'to_count': to_val,
                    'pct': pct,
                    'from_code': frm_code, 'to_code': to_code,
                })
        except Exception:
            pass

        # Bottleneck: conversion step thấp nhất (ignore 100% = chốt)
        bottleneck = None
        if conversions:
            non_perfect = [c for c in conversions if c['from_count'] > 0]
            if non_perfect:
                worst = min(non_perfect, key=lambda x: x['pct'])
                bottleneck = {
                    'label': worst['label'],
                    'pct': worst['pct'],
                    'hint': (
                        'Tỉ lệ chuyển thấp — review process / training'
                        if worst['pct'] < 50 else
                        'Có thể tối ưu thêm'
                    ),
                }

        # Stale leads — >14 ngày không gọi
        stale_threshold = now - _td(days=14)
        stale_recs = self.search([
            ('active', '=', True),
            ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            '|',
            ('last_call_date', '<', stale_threshold),
            '&', ('last_call_date', '=', False), ('create_date', '<', stale_threshold),
        ], order='last_call_date asc, create_date asc', limit=10)
        stale_count = self.search_count([
            ('active', '=', True),
            ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            '|',
            ('last_call_date', '<', stale_threshold),
            '&', ('last_call_date', '=', False), ('create_date', '<', stale_threshold),
        ])
        stale_top = []
        for r in stale_recs:
            anchor = r.last_call_date or r.create_date
            days_stale = ((now - anchor).days if anchor else 99)
            stale_top.append({
                'lead_id': r.id,
                'name': r.name or r.partner_name or 'KH',
                'days_stale': days_stale,
                'user_name': _short_name(r.user_id.name) if r.user_id else '—',
                'team': self._vd_team_label_for(r.user_id) if r.user_id else 'KHÁC',
            })

        # Negotiation problems status (vd.lead.problem)
        Problem = self.env['vd.lead.problem']
        prob_total = Problem.search_count([('lead_id.create_date', '>=', dt_from)])
        prob_open = Problem.search_count([
            ('lead_id.create_date', '>=', dt_from),
            ('status', '=', 'open'),
        ])
        prob_in_progress = Problem.search_count([
            ('lead_id.create_date', '>=', dt_from),
            ('status', '=', 'in_progress'),
        ])
        prob_resolved = Problem.search_count([
            ('lead_id.create_date', '>=', dt_from),
            ('status', '=', 'resolved'),
        ])
        problems = {
            'total': prob_total,
            'open': prob_open,
            'in_progress': prob_in_progress,
            'resolved': prob_resolved,
            'open_pct': round((prob_open + prob_in_progress) / prob_total * 100, 1) if prob_total else 0,
            'resolved_pct': round(prob_resolved / prob_total * 100, 1) if prob_total else 0,
        }

        pipeline_section = {
            'funnel': funnel_payload,
            'conversions': conversions,
            'bottleneck': bottleneck,
            'stale_count': stale_count,
            'stale_top': stale_top,
            'problems': problems,
        }

        # ============ 🏆 SECTION 3: HIỆU SUẤT NV ============
        # Cho mỗi NV active: tính contracts, leads, calls, answered, conversion
        nv_perf_rows = []
        Call = self.env['stringee.call']
        for u in sales_users:
            uid = u.id
            u_leads_total = self.search_count([
                ('user_id', '=', uid), ('create_date', '>=', dt_from), ('create_date', '<', dt_to),
            ])
            if u_leads_total == 0:
                continue
            u_closed = self.search_count([
                ('user_id', '=', uid),
                ('vd_contract_signed', '=', True),
                ('vd_contract_sign_date', '>=', d_from),
                ('vd_contract_sign_date', '<', d_to + _td(days=1)),
            ])
            u_active = self.search_count([
                ('user_id', '=', uid),
                ('stage_is_won', '=', False), ('stage_is_lost', '=', False),
            ])
            u_calls = Call.search_count([
                ('user_id', '=', uid),
                ('create_date', '>=', dt_from), ('create_date', '<', dt_to),
            ])
            u_answered = Call.search_count([
                ('user_id', '=', uid),
                ('create_date', '>=', dt_from), ('create_date', '<', dt_to),
                ('state', 'in', ['answered', 'ended']),
                ('duration', '>', 0),
            ])
            conv_pct = round((u_closed / u_leads_total * 100), 1) if u_leads_total else 0
            answer_pct = round((u_answered / u_calls * 100), 1) if u_calls else 0
            nv_perf_rows.append({
                'user_id': uid,
                'name': _short_name(u.name),
                'full_name': u.name,
                'team': self._vd_team_label_for(u),
                'leads_total': u_leads_total,
                'closed': u_closed,
                'active': u_active,
                'calls': u_calls,
                'answered': u_answered,
                'conversion_pct': conv_pct,
                'answer_pct': answer_pct,
            })

        # Top closers (>= 1 HĐ chốt, sort by closed desc)
        top_closers = sorted(
            [r for r in nv_perf_rows if r['closed'] > 0],
            key=lambda x: (-x['closed'], -x['conversion_pct']),
        )[:5]

        # Need training: leads_total >= 5 nhưng closed = 0
        need_training = sorted(
            [r for r in nv_perf_rows if r['leads_total'] >= 5 and r['closed'] == 0],
            key=lambda x: -x['leads_total'],
        )[:5]

        # Gọi nhiều chốt ít: calls >= 30 và conversion < 5% và leads_total >= 5
        high_call_low_close = sorted(
            [r for r in nv_perf_rows if r['calls'] >= 30 and r['conversion_pct'] < 5 and r['leads_total'] >= 5],
            key=lambda x: -x['calls'],
        )[:5]

        # Tỉ lệ bắt máy thấp: calls >= 10 và answer_pct < 40
        low_answer = sorted(
            [r for r in nv_perf_rows if r['calls'] >= 10 and r['answer_pct'] < 40],
            key=lambda x: x['answer_pct'],
        )[:5]

        nv_section = {
            'top_closers': top_closers,
            'need_training': need_training,
            'high_call_low_close': high_call_low_close,
            'low_answer': low_answer,
            'total_nv': len(nv_perf_rows),
        }

        # ============ 🎯 SECTION 4: INSIGHT KHÁCH HÀNG ============
        # 4a. Top negotiation problem tags
        self.env.cr.execute("""
            SELECT p.tag_id, COUNT(*)
            FROM vd_lead_problem p
            JOIN crm_lead l ON l.id = p.lead_id
            WHERE l.create_date >= %s AND l.create_date < %s
              AND p.tag_id IS NOT NULL
            GROUP BY p.tag_id
            ORDER BY COUNT(*) DESC
            LIMIT 8
        """, (dt_from, dt_to))
        prob_rows = self.env.cr.fetchall()
        NegoProblem = self.env['vd.nego.problem']
        top_problems = []
        prob_total_with_tag = sum(c for _, c in prob_rows) or 1
        for tag_id, cnt in prob_rows:
            tag = NegoProblem.browse(tag_id)
            top_problems.append({
                'tag_id': tag_id,
                'name': tag.name or 'Vấn đề',
                'icon': tag.icon or '🔸',
                'count': cnt,
                'pct': round(cnt / prob_total_with_tag * 100, 1),
            })

        # 4b. Top lost reasons
        self.env.cr.execute("""
            SELECT COALESCE(NULLIF(TRIM(vd_lost_reason), ''), '— không ghi —') AS reason,
                   COUNT(*)
            FROM crm_lead
            WHERE create_date >= %s AND create_date < %s
              AND stage_id IN (SELECT id FROM crm_stage WHERE is_lost = TRUE)
            GROUP BY reason
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """, (dt_from, dt_to))
        top_lost = [
            {'reason': (r[0] or '—')[:200], 'count': r[1]}
            for r in self.env.cr.fetchall()
        ]
        total_lost = sum(r['count'] for r in top_lost) or 1
        for r in top_lost:
            r['pct'] = round(r['count'] / total_lost * 100, 1)

        # 4c. Source quality — platform lấy từ vd_pancake_page_id.platform
        # (lead trỏ tới vd.pancake.page, page có cột platform = facebook/tiktok/ig).
        # Lead không có pancake_page_id → coi là 'manual' (NV nhập tay).
        SOURCE_LABELS = {
            'facebook': ('📘 Facebook', '#1877f2'),
            'tiktok':   ('🎵 TikTok', '#000000'),
            'instagram': ('📷 Instagram', '#e4405f'),
            'manual':   ('👤 Thủ công', '#6c757d'),
        }
        self.env.cr.execute("""
            SELECT COALESCE(p.platform, 'manual') AS src,
                   COUNT(*) AS total,
                   SUM(CASE WHEN l.vd_contract_signed THEN 1 ELSE 0 END) AS closed
            FROM crm_lead l
            LEFT JOIN vd_pancake_page p ON p.id = l.vd_pancake_page_id
            WHERE l.create_date >= %s AND l.create_date < %s AND l.active = TRUE
            GROUP BY COALESCE(p.platform, 'manual')
            ORDER BY total DESC
        """, (dt_from, dt_to))
        source_quality = []
        for src, total, closed_cnt in self.env.cr.fetchall():
            lbl, color = SOURCE_LABELS.get(src) or (f'📌 {src or "—"}', '#6c757d')
            source_quality.append({
                'source': src or 'manual',
                'label': lbl,
                'color': color,
                'total': total or 0,
                'closed': closed_cnt or 0,
                'pct': round((closed_cnt or 0) / total * 100, 1) if total else 0,
            })

        # 4d. Region performance (HN/HCM1/HCM2/HCM3)
        team_user_ids = defaultdict(list)
        for u in sales_users:
            team_user_ids[self._vd_team_label_for(u)].append(u.id)
        region_perf = []
        for team in ['HN', 'HCM1', 'HCM2', 'HCM3']:
            uids = team_user_ids.get(team, [])
            if not uids:
                region_perf.append({
                    **_team_pretty(team), 'total': 0, 'closed': 0, 'pct': 0,
                })
                continue
            self.env.cr.execute("""
                SELECT COUNT(*), SUM(CASE WHEN vd_contract_signed THEN 1 ELSE 0 END)
                FROM crm_lead
                WHERE user_id = ANY(%s)
                  AND create_date >= %s AND create_date < %s AND active = TRUE
            """, (uids, dt_from, dt_to))
            row = self.env.cr.fetchone()
            tot = row[0] or 0
            cl = row[1] or 0
            region_perf.append({
                **_team_pretty(team),
                'total': tot, 'closed': cl,
                'pct': round(cl / tot * 100, 1) if tot else 0,
            })

        customer_section = {
            'top_problems': top_problems,
            'top_lost_reasons': top_lost,
            'source_quality': source_quality,
            'region_performance': region_perf,
        }

        # ============ 💡 SECTION 5: GỢI Ý HÀNH ĐỘNG ============
        recommendations = []
        # High priority
        if urgent_section['overdue_count'] >= 5:
            recommendations.append({
                'priority': 'high', 'icon': '🚨',
                'title': f"{urgent_section['overdue_count']} KH quá hạn callback",
                'detail': 'Cần phân lại NV khác hoặc thúc NV gọi gấp — KH đợi lâu sẽ trượt deal.',
            })
        if kpi['idle_nv_count'] >= 1:
            recommendations.append({
                'priority': 'high', 'icon': '😴',
                'title': f"{kpi['idle_nv_count']} NV không gọi cuộc nào trong 2 ngày",
                'detail': 'Họp 1-on-1 hoặc kiểm tra workload — NV đang ngồi không nhưng KH active còn nhiều.',
            })
        if pending_signatures:
            past_due = [p for p in pending_signatures if p['urgency'] == 'past']
            if past_due:
                recommendations.append({
                    'priority': 'high', 'icon': '⏰',
                    'title': f"{len(past_due)} lịch ký HĐ đã quá hạn",
                    'detail': 'Liên hệ KH gấp để xác nhận có ký không — tránh KH lật kèo.',
                })

        # Medium priority
        if bottleneck and bottleneck['pct'] < 30:
            recommendations.append({
                'priority': 'medium', 'icon': '🔍',
                'title': f"Bottleneck: {bottleneck['label']} chỉ {bottleneck['pct']}%",
                'detail': 'Review process tại bước này — đa số KH dừng ở đây, cần training kỹ năng cụ thể.',
            })
        if top_problems and len(top_problems) > 0 and top_problems[0]['pct'] >= 30:
            tp = top_problems[0]
            recommendations.append({
                'priority': 'medium', 'icon': tp['icon'],
                'title': f"Vấn đề '{tp['name']}' xuất hiện {tp['count']} lần ({tp['pct']}%)",
                'detail': 'Tag này dominant — cân nhắc cải thiện sản phẩm/giá/process để xử lý gốc rễ.',
            })
        if stale_count >= 10:
            recommendations.append({
                'priority': 'medium', 'icon': '💤',
                'title': f"{stale_count} KH bị bỏ rơi >14 ngày",
                'detail': 'Phân lại NV hoặc đóng (lost) — KH không liên hệ sẽ tự lạnh đi.',
            })

        # ============ 🆕 KH overview — grouped by TEAM, mỗi NV 3 metric ============
        # Cấu trúc per-team: {team, color, nvs: [{user_id, name, resolved_*, in_progress_*, new_*}]}
        # 3 metric per NV:
        # - resolved: stage='won' + tất cả problems status='resolved' (đã giải quyết xong vấn đề
        #             → đang ở gửi HĐ / chốt)
        # - in_progress: có ít nhất 1 problem status open/in_progress (đang giải quyết vấn đề)
        # - new: stage='new' (chưa báo giá chưa tư vấn)
        TEAM_ORDER = ['HN', 'HCM1', 'HCM2', 'HCM3']
        TEAM_COLOR = {
            'HN': '#dc2626', 'HCM1': '#16a34a',
            'HCM2': '#9333ea', 'HCM3': '#d97706',
        }

        def _group_by_team(nv_list):
            """nv_list = [{user_id, name, full_name, team, count, leads}]
            → return [{team, color, total, nvs: [sorted by count desc]}]"""
            from collections import defaultdict as _dd
            buckets = _dd(list)
            for item in nv_list:
                buckets[item['team']].append(item)
            # Preserve TEAM_ORDER first, rest alphabetical, KHÁC cuối
            teams_seen = set(buckets.keys())
            order = [t for t in TEAM_ORDER if t in teams_seen]
            others = sorted(t for t in teams_seen if t not in TEAM_ORDER and t != 'KHÁC')
            order += others
            if 'KHÁC' in teams_seen:
                order.append('KHÁC')
            def _item_total(item):
                # Support cả 2 schema: legacy single 'count' và new 3 metrics
                if 'count' in item:
                    return item['count']
                return (
                    item.get('resolved_count', 0)
                    + item.get('in_progress_count', 0)
                    + item.get('new_count', 0)
                )
            result = []
            for team in order:
                # Trưởng nhóm LÊN ĐẦU (user spec 2026-06-14), còn lại theo tổng giảm dần.
                nvs = sorted(buckets[team],
                             key=lambda x: (0 if x.get('is_team_leader') else 1, -_item_total(x)))
                result.append({
                    'team': team,
                    'color': TEAM_COLOR.get(team, '#6c757d'),
                    'total': sum(_item_total(n) for n in nvs),
                    'nvs': nvs,
                })
            return result

        # ============ NEW: 1 NV → 3 metric (new / in_progress mid-stages / won) ============
        won_stage = Stage.search([('code', '=', 'won')], limit=1)
        # ĐANG XỬ LÝ = lead đã khai thác thông tin, đang báo giá, đàm phán, phát hiện
        # vấn đề... mọi stage giữa 'new' và 'won' đều count vào đây.
        mid_stage_ids = Stage.search([
            ('code', 'in', ['potential', 'callback', 'quote', 'negotiate']),
        ]).ids

        # ===== THI CÔNG GẤP + XỬ LÝ VẤN ĐỀ (user spec 2026-05-31 r3) =====
        # Tính 1 LẦN cho TẤT CẢ NV rồi nhóm theo user (tránh query lặp 14 lần).
        # Định nghĩa GIỐNG HỆT 2 bảng ở màn NV: dashboard_leads_urgent_construction
        # + dashboard_leads_with_problems.
        all_urgent_ids = self._dashboard_urgent_construction_ids(
            [('user_id', 'in', sales_user_ids)]
        ) if sales_user_ids else []
        urgent_by_user = defaultdict(list)
        for l in self.browse(all_urgent_ids):
            urgent_by_user[l.user_id.id].append(l)
        # Tag 'Thi công gấp' để tách "đã có vấn đề thật" vs "chưa tìm vấn đề"
        # (khớp badge ⚠️ TÌM VẤN ĐỀ = problems_non_urgent) cho popover NHẮC NHỞ.
        _rem_urgent_tag_id = self._vd_urgent_tag_id()
        # Ngưỡng % cho popover NHẮC NHỞ — dùng CHUNG ngưỡng "tìm vấn đề" (mặc định
        # 20%): chỉ nhắc nhóm nào vượt ngưỡng (user spec 2026-06-01).
        _rem_enabled, _rem_pct, _rem_grace = self._vd_problem_find_config()

        xlvd_stage_ids = Stage.search([('code', 'in', ['quote', 'negotiate'])]).ids
        xlvd_by_user = defaultdict(list)
        if xlvd_stage_ids and sales_user_ids:
            xlvd_leads_all = self.search([
                ('user_id', 'in', sales_user_ids),
                ('stage_id', 'in', xlvd_stage_ids),
                ('active', '=', True),
                ('vd_intake_complete', '=', True),
                ('vd_intake_locked', '=', True),
                ('id', 'not in', all_urgent_ids),
            ], order='vd_quote_created_date desc nulls last, create_date desc')
            for l in xlvd_leads_all:
                xlvd_by_user[l.user_id.id].append(l)

        # ===== KHÁCH MỚI (user spec 2026-06-01: KHỚP số với màn NV) =====
        # Bảng "Khách mới" màn NV = leadsNoProblems = dashboard_leads('new')
        # → dùng CHUNG _dashboard_new_bucket_domain (stage 'new' + KH Báo giá/
        # Đàm phán chưa CHỐT, KHÔNG vd_no_quote_state='pending') TRỪ KH "chưa
        # gọi được" (unreachable). KHÔNG lọc theo ngày, KHÔNG cap 80 như trước
        # → admin đếm đúng bằng bên trong NV. Tính 1 lần cho toàn bộ NV.
        newcust_by_user = defaultdict(list)
        if new_stage and sales_user_ids:
            new_base_all = self.search(
                self._dashboard_new_bucket_domain([('user_id', 'in', sales_user_ids)]),
                order='create_date desc',
            )
            unreach_cand = new_base_all.filtered(lambda l: (l.call_count or 0) >= 3)
            unreachable_ids = set(
                self._dashboard_unreachable_ids(unreach_cand, limit=100000)
            )
            for l in new_base_all:
                if l.id not in unreachable_ids:
                    newcust_by_user[l.user_id.id].append(l)

        # ===== 🗑️ KH HỦY — CHỜ DUYỆT (user spec 2026-06-21) =====
        # Mỗi NV thêm 1 "thùng rác" ở bảng trưởng phòng/giám đốc: danh sách KH NV
        # đề xuất hủy nhưng CHƯA được admin duyệt (stage lost + cancel_state !=
        # approved). GIỐNG HỆT bảng "KH HỦY" ở màn NV (dashboard_leads_lost) →
        # dùng chung sub-template bảng ở frontend. active_test=False vì lead lost
        # bị archive.
        _cancel_cat_sel = dict(self.env['crm.lead']._fields['vd_cancel_category'].selection)
        # Báo cáo KH mới vs Hủy THEO TỪNG NV (hôm nay/tuần/tháng) — hiện trong
        # popover thùng rác của từng NV.
        newcancel_by_user = self._vd_newcancel_report_by_user(sales_user_ids)
        cancel_by_user = defaultdict(list)
        if sales_user_ids:
            cancel_leads_all = self.with_context(active_test=False).search([
                ('user_id', 'in', sales_user_ids),
                ('stage_is_lost', '=', True),
                ('vd_cancel_state', '!=', 'approved'),
            ], order='write_date desc, create_date desc')
            for l in cancel_leads_all:
                cancel_by_user[l.user_id.id].append(l)

        # GHI ÂM gần nhất cho từng KH chờ hủy (1 query cho TẤT CẢ lead → map
        # lead_id -> cuộc gọi mới nhất CÓ ghi âm). Để nghe ngay trong bảng hủy.
        rec_by_lead = {}
        _all_cancel_ids = [l.id for ll in cancel_by_user.values() for l in ll]
        if _all_cancel_ids:
            _rec_calls = self.env['stringee.call'].sudo().search([
                ('lead_id', 'in', _all_cancel_ids),
                ('recording_attachment_id', '!=', False),
            ], order='create_date desc')
            for c in _rec_calls:
                lid = c.lead_id.id
                if lid in rec_by_lead:
                    continue  # search desc → cái đầu tiên là mới nhất
                _ldt = (fields.Datetime.context_timestamp(c, c.create_date)
                        if c.create_date else None)
                rec_by_lead[lid] = {
                    'url': '/web/content/%s?download=false' % c.recording_attachment_id.id,
                    'time': _ldt.strftime('%d/%m %H:%M') if _ldt else '',
                    'dur': c.duration or 0,
                }

        def _ld_cancel(l):
            # Khớp ĐÚNG các trường bảng "KH HỦY" màn NV (o_vd_cancel_table) dùng.
            _rec = rec_by_lead.get(l.id)
            # Bỏ tiền tố "[Chủ đề] • " trong lý do (đã có pill Chủ đề riêng) →
            # gộp 1 cột, không lặp lại "Nhầm số" 2 lần.
            _reason = re.sub(r'^\[[^\]]*\]\s*[•·]\s*', '', (l.vd_lost_reason or '').strip())
            return {
                'id': l.id,
                'name': l.name or l.partner_name or 'KH',
                # Bỏ tiền tố phòng ("HCM2 - ") cho gọn, KHÔNG bị cắt/xuống dòng.
                'user_name': _short_name(l.user_id.name) if l.user_id else '',
                'cancel_state': l.vd_cancel_state or '',
                'cancel_category_label': _cancel_cat_sel.get(l.vd_cancel_category, '') if l.vd_cancel_category else '',
                'cancel_reason_short': _reason[:160],
                # 🎙️ Ghi âm gần nhất (nghe ngay trong bảng)
                'rec_url': _rec['url'] if _rec else '',
                'rec_time': _rec['time'] if _rec else '',
                'rec_dur': _rec['dur'] if _rec else 0,
            }

        def _ld_basic(l):
            return {
                'lead_id': l.id,
                'name': l.name or l.partner_name or 'KH',
                'phone': l.phone or '',
                'hours_ago': int((now - l.create_date).total_seconds() // 3600) if l.create_date else 0,
                'call_count': l.call_count or 0,
            }

        def _short_prob_name(p):
            if p.tag_id:
                return p.tag_id.name
            text = (p.name or '').strip()
            for sep in (':', '—', ' – ', ' - '):
                if sep in text:
                    return text.split(sep, 1)[0].strip()
            return text or 'Vấn đề'

        def _ld_with_problems(l):
            open_probs = l.vd_lead_problem_ids.filtered(
                lambda p: p.status in ('open', 'in_progress')
            )
            return {
                **_ld_basic(l),
                'problem_count': len(open_probs),
                'problems': [{
                    'name': _short_prob_name(p),
                    'icon': p.tag_id.icon if p.tag_id else '🔸',
                    'status': p.status,
                } for p in open_probs[:5]],
            }

        def _ld_help(l):
            # KH mà NV đã bấm 🆘 — kèm phạm vi/trạng thái + vấn đề đang mở để
            # admin nắm ngay tình huống khi rê chuột vào cột "Cần hỗ trợ".
            open_probs = l.vd_lead_problem_ids.filtered(
                lambda p: p.status in ('open', 'in_progress')
            )
            return {
                **_ld_basic(l),
                'scope': l.vd_need_help_scope or 'today',
                'status': l.vd_help_status or 'waiting',
                'stage_name': l.stage_id.name or '',
                'problems': [{
                    'name': _short_prob_name(p),
                    'icon': p.tag_id.icon if p.tag_id else '🔸',
                    'status': p.status,
                } for p in open_probs[:3]],
            }

        # Build NV stats — iterate sales_users for completeness
        cap_labels = dict(
            self.env['res.users']._fields['vd_capacity_level'].selection
        )
        nv_unified_flat = []
        # Báo cáo cuộc gọi HÔM NAY + THÁNG NÀY — NGUỒN CHUNG với trang cá nhân NV
        # (_vd_call_report). Tính 1 lần cho toàn bộ NV trước vòng lặp → số ở badge
        # danh sách NV KHỚP 100% với card sidebar trang cá nhân. Đếm theo SỐ CUỘC GỌI.
        call_report_map = self._vd_call_report(sales_users.ids, today=today)
        _empty_cr = {'calls_today_total': 0, 'calls_today_success': 0,
                     'calls_month_total': 0, 'calls_month_success': 0}
        for u in sales_users:
            # Metric 1: ĐANG CHỐT = lead ở stage 'won' (đang trong giai đoạn ký HĐ /
            # chốt — bao gồm cả đã ký lẫn chưa ký). Không yêu cầu vấn đề đã giải quyết.
            resolved_leads = []
            if won_stage:
                won_leads_qs = self.search([
                    ('user_id', '=', u.id),
                    ('stage_id', '=', won_stage.id),
                    ('active', '=', True),
                    ('create_date', '>=', dt_from),
                    ('create_date', '<', dt_to),
                ], order='create_date desc', limit=100)
                resolved_leads = list(won_leads_qs)

            # Metric 2: ĐANG XỬ LÝ = lead ở stage potential/callback/quote/negotiate
            # (đã khai thác info, đang báo giá, đang đàm phán, có vấn đề...)
            # Tách thành 2 sub-bucket:
            #   - in_progress: lead có vấn đề đang mở (open/in_progress)
            #   - no_problem:  lead ở mid-stage NHƯNG chưa có vấn đề nào
            #                  (mới làm báo giá, chưa khai thác/tạo vấn đề)
            mid_qs = self.env['crm.lead'].browse()
            if mid_stage_ids:
                mid_qs = self.search([
                    ('user_id', '=', u.id),
                    ('stage_id', 'in', mid_stage_ids),
                    ('active', '=', True),
                    ('create_date', '>=', dt_from),
                    ('create_date', '<', dt_to),
                ], order='create_date desc', limit=200)

            in_progress_qs = mid_qs.browse()
            no_problem_qs = mid_qs.browse()
            for l in mid_qs:
                if l.vd_lead_problem_ids.filtered(
                    lambda p: p.status in ('open', 'in_progress')
                ):
                    in_progress_qs |= l
                else:
                    no_problem_qs |= l

            # Metric 3: KH MỚI = stage 'new'
            new_leads_qs = self.env['crm.lead'].browse()
            if new_stage:
                new_leads_qs = self.search([
                    ('user_id', '=', u.id),
                    ('stage_id', '=', new_stage.id),
                    ('active', '=', True),
                    ('create_date', '>=', dt_from),
                    ('create_date', '<', dt_to),
                ], order='create_date desc', limit=100)

            # KH MỚI HÔM NAY (user spec 2026-06-05): KH được TẠO MỚI hôm nay của
            # NV — KHÔNG phụ thuộc stage hiện tại hay khoảng lọc ngày dashboard.
            today_start = fields.Datetime.to_datetime(today)
            today_end = today_start + _td(days=1)
            new_today_qs = self.search([
                ('user_id', '=', u.id),
                ('create_date', '>=', today_start),
                ('create_date', '<', today_end),
                ('active', '=', True),
            ], order='create_date desc', limit=100)
            # User spec round 13: số KH đã GỌI hôm nay + số KH gọi THÀNH CÔNG.
            # Số cuộc gọi HÔM NAY + THÁNG NÀY lấy từ map nguồn chung (đã tính ở trên).
            _cr = call_report_map.get(u.id, _empty_cr)

            # 🆘 CẦN HỖ TRỢ — KH mà NV này đã bấm yêu cầu cấp trên hỗ trợ và còn
            # hiệu lực (today/multi, chưa won/lost). Độc lập với khoảng lọc ngày
            # (vấn đề cần xử lý NGAY bất kể KH tạo lúc nào). Tối đa 3/NV.
            help_qs = self.search([
                ('user_id', '=', u.id),
                ('vd_need_help', '=', True),
                ('active', '=', True),
                ('stage_is_won', '=', False),
                ('stage_is_lost', '=', False),
            ], order='vd_need_help_at asc', limit=20)
            help_active = [l for l in help_qs if l._vd_need_help_active(today)]
            # Sort: 🔴 chờ (waiting) lên trước 🟢 đang hỗ trợ (helping), rồi theo thời gian.
            help_active.sort(key=lambda l: (l.vd_help_status == 'helping',
                                            l.vd_need_help_at or now))
            n_help_waiting = sum(
                1 for l in help_active if (l.vd_help_status or 'waiting') == 'waiting'
            )

            n_resolved = len(resolved_leads)
            n_in_prog = len(in_progress_qs)
            n_no_problem = len(no_problem_qs)
            # KH MỚI = bucket khớp màn NV (đã trừ pending + unreachable, không cap)
            nv_new = newcust_by_user.get(u.id, [])
            n_new = len(nv_new)
            # Tổng KH NV quản lý: tất cả lead active gán cho NV (không filter
            # theo date — total real, không phụ thuộc khoảng lọc)
            total_managed = self.search_count([
                ('user_id', '=', u.id),
                ('active', '=', True),
            ])
            # User spec 2026-06-09: NV cứ có tài khoản (salesman, active) là PHẢI
            # hiện trên danh sách, kể cả 0 khách / 0 số → bỏ skip NV rỗng (trước
            # đây ẩn NV total_managed==0 nên NV mới giao tài khoản không thấy).

            # ===== NHẮC NHỞ NHÂN VIÊN — số liệu tồn đọng cần xử lý =====
            _nv_urgent = urgent_by_user.get(u.id, [])
            _nv_xlvd = xlvd_by_user.get(u.id, [])
            rem_new_not_called = sum(1 for l in nv_new if (l.call_count or 0) == 0)
            rem_urgent_no_problem = sum(
                1 for l in _nv_urgent if not l._vd_lead_has_real_problem(_rem_urgent_tag_id)
            )
            rem_xlvd_no_problem = sum(
                1 for l in _nv_xlvd if not l._vd_lead_has_real_problem(_rem_urgent_tag_id)
            )
            rem_xlvd_open_problem = len(_nv_xlvd) - rem_xlvd_no_problem
            _n_urgent = len(_nv_urgent)
            _n_xlvd = len(_nv_xlvd)

            # ===== NHẮC NHỞ dạng tỷ lệ "X/Y khách (Z%)" — chỉ nhóm > ngưỡng =====
            # Mỗi item: count/total + pct; over=True khi vượt ngưỡng (mặc định 20%).
            # Frontend chỉ hiện item over → ẩn hết nhóm =0 hoặc dưới ngưỡng.
            def _rem_item(icon, count, total, label):
                pct = round(count / total * 100) if total else 0
                return {
                    'icon': icon, 'count': count, 'total': total, 'pct': pct,
                    'label': label,
                    'over': bool(_rem_enabled and total > 0 and count > 0 and pct > _rem_pct),
                }
            # 3 nhóm gọn (user spec 2026-06-01): chưa gọi / chưa tìm vấn đề /
            # chưa xử lý vấn đề. "Chưa tìm vấn đề" gộp cả thi công gấp + sau báo giá.
            _chua_tim = rem_urgent_no_problem + rem_xlvd_no_problem
            _chua_tim_total = _n_urgent + _n_xlvd
            reminder_items = [
                _rem_item('📞', rem_new_not_called, n_new, '(Mới) - CHƯA GỌI'),
                _rem_item('❓', _chua_tim, _chua_tim_total, '- CHƯA Tìm vấn đề'),
                _rem_item('🛠️', rem_xlvd_open_problem, _n_xlvd, '- CHƯA Xử lý vấn đề'),
            ]

            nv_unified_flat.append({
                'user_id': u.id,
                'name': _short_name(u.name),
                'full_name': u.name,
                'is_team_leader': u.id in _tl_user_ids,
                'team': self._vd_team_label_for(u),
                'work_months': u.vd_work_months or 0,
                'capacity_level': u.vd_capacity_level or 'junior',
                'capacity_label': cap_labels.get(u.vd_capacity_level or 'junior', ''),
                'total_leads': total_managed,
                'resolved_count': n_resolved,
                'resolved_leads': [_ld_basic(l) for l in resolved_leads[:50]],
                'in_progress_count': n_in_prog,
                'in_progress_leads': [_ld_with_problems(l) for l in in_progress_qs[:50]],
                'no_problem_count': n_no_problem,
                'no_problem_leads': [_ld_basic(l) for l in no_problem_qs[:50]],
                'new_count': n_new,
                'new_leads': [_ld_basic(l) for l in nv_new[:50]],
                # User spec 2026-05-29: KH mới HÔM NAY
                'new_today_count': len(new_today_qs),
                'new_today_leads': [_ld_basic(l) for l in new_today_qs[:50]],
                # Số cuộc gọi HÔM NAY + THÁNG NÀY (nguồn chung _vd_call_report,
                # đếm theo SỐ CUỘC GỌI — khớp card sidebar trang cá nhân NV).
                'calls_today_total': _cr['calls_today_total'],
                'calls_today_success': _cr['calls_today_success'],
                'calls_month_total': _cr['calls_month_total'],
                'calls_month_success': _cr['calls_month_success'],
                # 🆘 Cần hỗ trợ (user spec 2026-05-31): count + danh sách ≤3 KH
                'help_count': len(help_active),
                'help_waiting': n_help_waiting,
                'help_leads': [_ld_help(l) for l in help_active[:3]],
                # ⚡ Thi công gấp + 🛠 Xử lý vấn đề (mirror 2 bảng màn NV)
                'urgent_count': len(urgent_by_user.get(u.id, [])),
                'urgent_leads': [_ld_basic(l) for l in urgent_by_user.get(u.id, [])[:50]],
                'xlvd_count': len(xlvd_by_user.get(u.id, [])),
                'xlvd_leads': [_ld_with_problems(l) for l in xlvd_by_user.get(u.id, [])[:50]],
                # 🗑️ KH hủy chờ duyệt (thùng rác mỗi dòng NV)
                'cancel_count': len(cancel_by_user.get(u.id, [])),
                'cancel_leads': [_ld_cancel(l) for l in cancel_by_user.get(u.id, [])[:100]],
                # 📊 Báo cáo KH mới vs Hủy của RIÊNG NV này (cho popover thùng rác)
                'newcancel_report': newcancel_by_user.get(u.id) or [],
                # 🔒 Trạng thái KHOÁ từng bảng (user spec 2026-06-05) — thẻ overview
                # khoá theo + admin gỡ ngay. Dùng cờ đã lưu (cron/live set).
                'lock_new': bool(u.vd_call_lock),
                'lock_urgent': bool(u.vd_pf_lock_urgent),
                'lock_xlvd': bool(u.vd_pf_lock_xlvd),
                # 🔔 NHẮC NHỞ NHÂN VIÊN (user spec 2026-06-01)
                'reminder_level': u.vd_reminder_level or 0,
                'rem_new_not_called': rem_new_not_called,
                'rem_callback': u.vd_overdue_lead_count or 0,
                'rem_urgent': len(_nv_urgent),
                'rem_urgent_no_problem': rem_urgent_no_problem,
                'rem_xlvd_no_problem': rem_xlvd_no_problem,
                'rem_xlvd_open_problem': rem_xlvd_open_problem,
                'reminder_items': reminder_items,
                'reminder_threshold_pct': _rem_pct,
            })
        kh_by_team = _group_by_team(nv_unified_flat)

        # Backward compat: giữ 2 list cũ (frontend cũ chưa update có thể đọc)
        kh_moi_by_team = []
        kh_van_de_by_team = []

        # Low priority insights
        if source_quality:
            best_src = max(source_quality, key=lambda x: x['pct'])
            worst_src = min([s for s in source_quality if s['total'] >= 5], key=lambda x: x['pct'], default=None)
            if best_src['total'] >= 5 and best_src['pct'] > 0:
                recommendations.append({
                    'priority': 'low', 'icon': '✨',
                    'title': f"Nguồn {best_src['label']} hiệu quả nhất ({best_src['pct']}%)",
                    'detail': 'Đầu tư thêm ngân sách marketing cho kênh này.',
                })
            if worst_src and worst_src['pct'] < 2 and worst_src['total'] >= 10:
                recommendations.append({
                    'priority': 'low', 'icon': '⚠️',
                    'title': f"Nguồn {worst_src['label']} chốt thấp ({worst_src['pct']}%)",
                    'detail': 'Review chất lượng SĐT / ad creative — đang đốt tiền không ra deal.',
                })

        # Ngưỡng KH mới CHƯA gọi (user spec 2026-06-14): NV vượt ngưỡng -> hiện thẻ
        # cảnh báo ở dòng NV để trưởng nhóm đôn đốc. Dùng chung config với KHOÁ.
        uncalled_new_threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'vd_crm_lead.uncalled_new_lock_threshold', 15) or 15)

        return {
            'date_from': d_from.isoformat(),
            'date_to': d_to.isoformat(),
            'generated_at': now.isoformat(),
            'kpi': kpi,
            'uncalled_new_threshold': uncalled_new_threshold,
            'kh_moi_by_team': kh_moi_by_team,
            'kh_van_de_by_team': kh_van_de_by_team,
            'kh_by_team': kh_by_team,
            'urgent': urgent_section,
            'pipeline': pipeline_section,
            'nv_performance': nv_section,
            'customer_insights': customer_section,
            'recommendations': recommendations,
        }
