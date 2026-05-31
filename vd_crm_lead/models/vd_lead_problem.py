# -*- coding: utf-8 -*-
"""Vấn đề từng KH gặp phải khi đàm phán — tracker dạng row.

Mỗi lead có 1 hoặc nhiều vấn đề. Mỗi vấn đề là 1 row: tên + cách xử lý + tiến độ.
Mục đích: ép NV phải XỬ LÝ TỪNG VẤN ĐỀ cụ thể, không nói chung chung.
2 vấn đề mặc định auto-tạo khi lead vào stage Đàm phán:
- CHÊNH LỆCH CHI PHÍ
- THỜI GIAN KHỞI CÔNG
NV có thể thêm vấn đề khác qua nút "+ Thêm vấn đề".
"""
from odoo import models, fields, api, _


class VdLeadProblem(models.Model):
    _name = 'vd.lead.problem'
    _description = 'Vấn đề KH trong đàm phán'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    lead_id = fields.Many2one(
        'crm.lead', string='KH', required=True, ondelete='cascade', index=True,
    )
    tag_id = fields.Many2one(
        'vd.nego.problem', string='Thẻ vấn đề', ondelete='set null',
        help='Thẻ chọn từ catalog 12 vấn đề mẫu (NV bấm "+ Tạo vấn đề" để pick).',
    )
    tag_code = fields.Char(
        string='Tag code', related='tag_id.code', store=False, readonly=True,
        help='Code của tag (dùng để show/hide section khai thác theo từng loại vấn đề).',
    )
    name = fields.Char(
        string='Tên vấn đề', required=True,
        help='Tự fill từ tag_id khi chọn từ catalog. Có thể custom cho 2 row mặc định.',
    )
    tag_display = fields.Char(
        string='Thẻ vấn đề', compute='_compute_tag_display', store=False,
        help='Hiển thị "icon name" gộp — dùng cho cột hiển thị trong list view.',
    )
    tag_tip_html = fields.Html(
        string='Tips gợi ý',
        related='tag_id.tip_html', sanitize=False, readonly=True,
        help='Mẹo xử lý đàm phán theo tag — đọc từ catalog vd.nego.problem.',
    )
    code = fields.Char(
        string='Mã (built-in)', copy=False,
        help='Mã cho vấn đề mặc định (cost_diff, start_time). Custom row để trống.',
    )
    nv_handling = fields.Text(
        string='Tổng kết / Ghi chú',
        help='NV ghi tổng kết: KH có chuyển biến gì, hành động kế tiếp...',
    )
    status = fields.Selection([
        ('open', '🔴 Chưa xử lý'),
        ('in_progress', '🟡 Đang xử lý'),
        ('resolved', '🟢 Đã giải quyết'),
    ], string='Trạng thái', default='open', required=True, index=True)
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)
    is_default = fields.Boolean(
        string='Mặc định', default=False,
        help='True nếu là 1 trong 2 vấn đề mặc định (không cho xoá).',
    )

    # ============================================================
    # CONTACT TRACKING — dùng chung cho mọi loại vấn đề
    # NV phải tick để xác nhận đã gọi/zalo trao đổi vấn đề này với KH
    # ============================================================
    contact_called = fields.Boolean(
        string='Đã gọi điện trao đổi',
        help='Đã thực hiện cuộc gọi với KH để khai thác/xử lý vấn đề này.',
    )
    contact_zalo = fields.Boolean(
        string='Đã nhắn Zalo trao đổi',
        help='Đã nhắn tin Zalo với KH để khai thác/xử lý vấn đề này.',
    )
    last_contact_date = fields.Datetime(
        string='Lần liên hệ gần nhất',
        help='NV cập nhật mỗi lần liên hệ KH về vấn đề này.',
    )

    # ============================================================
    # THAM KHẢO GIÁ (tag.code = 'reference_price') — khai thác sâu
    # Mục tiêu: tìm đối thủ, tìm nỗi sợ, xây niềm tin (không phải giảm giá)
    # ============================================================
    # A. KHÁCH ĐANG THAM KHẢO ĐỘI NÀO?
    tk_competitor_count = fields.Integer(
        string='Số đơn vị KH đang tham khảo',
        help='Bao nhiêu đơn vị KH đang xem báo giá / tư vấn?',
    )
    tk_competitor_type = fields.Selection([
        ('small_team', '🛠️ Đội thầu nhỏ địa phương — KH ưu tiên GIÁ'),
        ('big_company', '🏢 Công ty lớn — KH ưu tiên AN TOÀN & UY TÍN'),
        ('mixed', '🔀 Hỗn hợp nhiều bên — KH CHƯA CHỐT NIỀM TIN'),
        ('unknown', '❔ Chưa khai thác được'),
    ], string='Loại đối thủ KH đang so sánh')
    tk_competitor_names = fields.Char(
        string='Tên đơn vị đối thủ (nếu biết)',
        help='Ghi tên cụ thể bên KH đang tham khảo, vd: Cty A, đội thầu anh B...',
    )

    # B. THAM KHẢO BAO LÂU?
    tk_duration = fields.Selection([
        ('new', '⏱️ Mới sơ bộ (≤ 1 tuần)'),
        ('weeks', '📆 Vài tuần'),
        ('months', '📅 Trên 1 tháng — đã có báo giá chi tiết'),
        ('long', '🕰️ Trên 3 tháng — KH đang chần chừ'),
    ], string='KH đã tham khảo bao lâu rồi?')

    # C. KẾT QUẢ HIỆN TẠI
    tk_top_competitor = fields.Char(
        string='Bên KH thấy "ổn nhất" hiện tại',
        help='Bên nào đang dẫn đầu trong đầu KH? Ghi tên + lý do ngắn.',
    )
    tk_price_gap = fields.Char(
        string='Báo giá các bên chênh nhau ~',
        help='VD: 100-200tr giữa rẻ nhất và đắt nhất. Để đánh giá KH có đang focus giá ko.',
    )
    tk_concerns = fields.Text(
        string='KH đang phân vân điểm gì nhất?',
        help='Lăn tăn lớn nhất của KH — câu trả lời thường lộ NỖI SỢ chính.',
    )

    # D. KHÁCH THẤY "ỔN" CHƯA?
    tk_signal = fields.Selection([
        ('not_yet', '— Chưa khai thác được'),
        ('on_price', '💵 Ổn về GIÁ'),
        ('on_process', '⚙️ Ổn về CÁCH LÀM VIỆC'),
        ('on_both', '✅ Ổn cả GIÁ + CÁCH LÀM VIỆC'),
        ('still_doubt', '⚠️ Vẫn còn lăn tăn'),
    ], string='Khách thấy "ổn" về gì?')
    tk_close_fear = fields.Text(
        string='Nếu chốt hôm nay, KH sợ điều gì nhất?',
        help='Câu cực quan trọng — câu trả lời lộ nỗi sợ thật.',
    )

    # NỖI SỢ chính của KH (multi-check)
    tk_fear_overrun = fields.Boolean(string='Sợ phát sinh chi phí')
    tk_fear_delay = fields.Boolean(string='Sợ chậm tiến độ')
    tk_fear_material = fields.Boolean(string='Sợ vật tư bị tráo / không đúng')
    tk_fear_quality = fields.Boolean(string='Sợ thi công xấu / kém chất lượng')
    tk_fear_control = fields.Boolean(string='Sợ không kiểm soát được đội thi công')

    # HÀNH ĐỘNG XÂY NIỀM TIN — checkbox đã làm gì
    tk_action_process = fields.Boolean(string='Đã giải thích quy trình thi công')
    tk_action_portfolio = fields.Boolean(string='Đã cho xem công trình thực tế')
    tk_action_checklist = fields.Boolean(string='Đã cho xem checklist vật tư')
    tk_action_progress = fields.Boolean(string='Đã cho xem tiến độ thi công mẫu')
    tk_action_contract = fields.Boolean(string='Đã cho xem hợp đồng mẫu')

    # KẾT QUẢ SAU XỬ LÝ
    tk_outcome = fields.Selection([
        ('explored', '🟢 Đã khai thác xong — KH cởi mở chia sẻ'),
        ('rebuilt_trust', '🟢 KH đã tin tưởng hơn — sẵn sàng nghe tiếp'),
        ('still_compare', '🟡 KH vẫn tiếp tục tham khảo'),
        ('losing', '🔴 KH có dấu hiệu trượt deal'),
        ('signing', '✅ KH sắp chốt — chuẩn bị ký HĐ'),
    ], string='Kết quả sau xử lý')

    # ============================================================
    # KHUYẾN MÃI / GIẢM GIÁ (tag.code = 'promotion') — round 12
    # NV tạo vấn đề → chọn loại (giảm giá / khuyến mãi) + nhập số tiền
    # → Gửi duyệt → trưởng nhóm hoặc admin duyệt → tự động thành dòng
    # trong báo giá chi tiết + PDF.
    # ============================================================
    km_type = fields.Selection([
        ('discount', '💸 Giảm giá (số tiền trực tiếp)'),
        ('promo', '🎁 Khuyến mãi (tên vật tư tặng + số tiền quy đổi)'),
    ], string='Loại')
    km_material_name = fields.Char(
        string='Tên vật tư khuyến mãi',
        help='VD: "Tặng máy nước nóng", "Tặng cửa nhôm", "Nâng cấp sơn ngoài"...',
    )
    km_amount = fields.Monetary(
        string='Số tiền', currency_field='km_currency_id', default=0,
        help='Giảm giá: số tiền trừ trực tiếp. Khuyến mãi: giá trị quy đổi của quà tặng.',
    )
    km_currency_id = fields.Many2one(
        'res.currency', related='lead_id.vd_currency_vnd_id',
        store=False, readonly=True,
    )
    km_state = fields.Selection([
        ('draft', '📝 Nháp — NV soạn'),
        ('pending', '⏳ Chờ duyệt'),
        ('approved', '✓ Đã duyệt — đưa vào báo giá'),
        ('rejected', '✗ Bị từ chối'),
    ], string='Trạng thái duyệt KM', default='draft', tracking=True, copy=False)
    km_submitted_date = fields.Datetime(string='Ngày gửi duyệt', readonly=True, copy=False)
    km_approved_by_id = fields.Many2one(
        'res.users', string='Người duyệt KM', readonly=True, copy=False,
    )
    km_approved_date = fields.Datetime(string='Ngày duyệt', readonly=True, copy=False)
    km_reject_reason = fields.Text(string='Lý do từ chối', copy=False)

    def action_km_submit(self):
        """NV bấm 'Gửi duyệt' → state='pending'."""
        from odoo.exceptions import UserError
        for rec in self:
            if rec.tag_code != 'promotion':
                raise UserError(_('Chỉ vấn đề "Khuyến mãi" mới gửi duyệt được.'))
            if not rec.km_type:
                raise UserError(_('Vui lòng chọn loại (Giảm giá / Khuyến mãi).'))
            if not rec.km_amount or rec.km_amount <= 0:
                raise UserError(_('Số tiền phải > 0.'))
            if rec.km_type == 'promo' and not (rec.km_material_name or '').strip():
                raise UserError(_('Khuyến mãi phải nhập tên vật tư.'))
            rec.write({
                'km_state': 'pending',
                'km_submitted_date': fields.Datetime.now(),
            })
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('🎁 NV %s gửi duyệt KM: <b>%s %s đ</b>') % (
                    self.env.user.name,
                    rec.km_material_name or '(giảm giá)',
                    '{:,.0f}'.format(rec.km_amount).replace(',', '.'),
                ),
            )

    def action_km_approve(self):
        """Trưởng nhóm hoặc admin duyệt → state='approved' →
        tự động render vào báo giá chi tiết + PDF (trigger compute breakdown_html)."""
        from odoo.exceptions import AccessError
        user = self.env.user
        is_admin = user.has_group('vd_crm_lead.vd_crm_group_admin')
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        if not (is_admin or is_leader):
            raise AccessError(_('Chỉ trưởng nhóm hoặc admin được duyệt khuyến mãi.'))
        for rec in self:
            if rec.km_state != 'pending':
                continue
            rec.write({
                'km_state': 'approved',
                'km_approved_by_id': user.id,
                'km_approved_date': fields.Datetime.now(),
            })
            # Trigger recompute breakdown
            rec.lead_id._compute_quote_breakdown_html()
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('✓ <b>%s</b> đã duyệt KM: %s — %s đ') % (
                    user.name,
                    rec.km_material_name or 'Giảm giá',
                    '{:,.0f}'.format(rec.km_amount).replace(',', '.'),
                ),
            )

    def action_km_reject(self):
        """Trưởng nhóm hoặc admin từ chối → state='rejected'."""
        from odoo.exceptions import AccessError
        user = self.env.user
        is_admin = user.has_group('vd_crm_lead.vd_crm_group_admin')
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        if not (is_admin or is_leader):
            raise AccessError(_('Chỉ trưởng nhóm hoặc admin được từ chối khuyến mãi.'))
        for rec in self:
            if rec.km_state not in ('pending', 'approved'):
                continue
            rec.write({
                'km_state': 'rejected',
                'km_approved_by_id': user.id,
                'km_approved_date': fields.Datetime.now(),
            })
            rec.lead_id._compute_quote_breakdown_html()
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('✗ <b>%s</b> từ chối KM: %s') % (
                    user.name,
                    rec.km_reject_reason or rec.km_material_name or '(không rõ lý do)',
                ),
            )

    def action_km_revert_to_draft(self):
        """Đưa về nháp để sửa lại."""
        for rec in self:
            rec.km_state = 'draft'

    # ============================================================
    # PHÁT SINH VẬT TƯ (tag.code = 'extra_material') — round 12.1
    # KH yêu cầu thêm vật tư ngoài báo giá gốc → CỘNG vào tổng (KH trả thêm).
    # Flow giống KM nhưng dấu ngược: NV nhập → gửi duyệt → trưởng nhóm/admin
    # duyệt → tự thành 1 dòng cộng trong báo giá + PDF.
    # ============================================================
    ps_material_name = fields.Char(
        string='Tên vật tư phát sinh',
        help='VD: "Thêm máy lạnh tầng 2", "Nâng cấp gạch lát ngoài", "Thêm 1 WC tầng tum"...',
    )
    ps_amount = fields.Monetary(
        string='Số tiền phát sinh', currency_field='ps_currency_id', default=0,
        help='Số tiền KH phải trả thêm cho vật tư / hạng mục này.',
    )
    ps_currency_id = fields.Many2one(
        'res.currency', related='lead_id.vd_currency_vnd_id',
        store=False, readonly=True,
    )
    ps_state = fields.Selection([
        ('draft', '📝 Nháp — NV soạn'),
        ('pending', '⏳ Chờ duyệt'),
        ('approved', '✓ Đã duyệt — đưa vào báo giá'),
        ('rejected', '✗ Bị từ chối'),
    ], string='Trạng thái duyệt PS', default='draft', tracking=True, copy=False)
    ps_submitted_date = fields.Datetime(string='Ngày gửi duyệt PS', readonly=True, copy=False)
    ps_approved_by_id = fields.Many2one(
        'res.users', string='Người duyệt PS', readonly=True, copy=False,
    )
    ps_approved_date = fields.Datetime(string='Ngày duyệt PS', readonly=True, copy=False)
    ps_reject_reason = fields.Text(string='Lý do từ chối PS', copy=False)

    def action_ps_submit(self):
        """NV gửi duyệt phát sinh vật tư."""
        from odoo.exceptions import UserError
        for rec in self:
            if rec.tag_code != 'extra_material':
                raise UserError(_('Chỉ vấn đề "Phát sinh vật tư" mới gửi duyệt được.'))
            if not (rec.ps_material_name or '').strip():
                raise UserError(_('Vui lòng nhập tên vật tư phát sinh.'))
            if not rec.ps_amount or rec.ps_amount <= 0:
                raise UserError(_('Số tiền phát sinh phải > 0.'))
            rec.write({
                'ps_state': 'pending',
                'ps_submitted_date': fields.Datetime.now(),
            })
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('🧰 NV %s gửi duyệt PS vật tư: <b>%s — %s đ</b>') % (
                    self.env.user.name, rec.ps_material_name,
                    '{:,.0f}'.format(rec.ps_amount).replace(',', '.'),
                ),
            )

    def action_ps_approve(self):
        """Trưởng nhóm hoặc admin duyệt PS → CỘNG vào báo giá."""
        from odoo.exceptions import AccessError
        user = self.env.user
        is_admin = user.has_group('vd_crm_lead.vd_crm_group_admin')
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        if not (is_admin or is_leader):
            raise AccessError(_('Chỉ trưởng nhóm hoặc admin được duyệt phát sinh.'))
        for rec in self:
            if rec.ps_state != 'pending':
                continue
            rec.write({
                'ps_state': 'approved',
                'ps_approved_by_id': user.id,
                'ps_approved_date': fields.Datetime.now(),
            })
            rec.lead_id._compute_quote_breakdown_html()
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('✓ <b>%s</b> duyệt PS vật tư: %s + %s đ') % (
                    user.name, rec.ps_material_name,
                    '{:,.0f}'.format(rec.ps_amount).replace(',', '.'),
                ),
            )

    def action_ps_reject(self):
        from odoo.exceptions import AccessError
        user = self.env.user
        is_admin = user.has_group('vd_crm_lead.vd_crm_group_admin')
        is_leader = user.has_group('vd_crm_lead.vd_crm_group_team_leader')
        if not (is_admin or is_leader):
            raise AccessError(_('Chỉ trưởng nhóm hoặc admin được từ chối phát sinh.'))
        for rec in self:
            if rec.ps_state not in ('pending', 'approved'):
                continue
            rec.write({
                'ps_state': 'rejected',
                'ps_approved_by_id': user.id,
                'ps_approved_date': fields.Datetime.now(),
            })
            rec.lead_id._compute_quote_breakdown_html()
            rec.lead_id.message_post(
                subtype_xmlid='mail.mt_note',
                body=_('✗ <b>%s</b> từ chối PS: %s') % (
                    user.name, rec.ps_reject_reason or rec.ps_material_name or '(không rõ)',
                ),
            )

    def action_ps_revert_to_draft(self):
        for rec in self:
            rec.ps_state = 'draft'

    # ============================================================
    # GIA ĐÌNH KHÔNG ĐỒNG Ý (tag.code = 'family_not_agree') — round 7 phase 3
    # Khai thác: AI không đồng ý, TẠI SAO, HƯỚNG xử lý, CHECKLIST các bước.
    # ============================================================
    fa_who = fields.Selection([
        ('vo', '💑 Vợ'),
        ('chong', '🤵 Chồng'),
        ('bo_me', '👴👵 Bố mẹ'),
        ('ong_ba', '👴👵 Ông bà'),
        ('con_cai', '👨‍👩‍👧 Con cái'),
        ('anh_chi_em', '👨‍👩‍👦 Anh chị em'),
        ('khac', '❓ Khác'),
    ], string='Ai không đồng ý?',
        help='Người đang cản KH chốt — quan trọng vì sau này phải gặp/thuyết phục đúng người đó.')
    fa_who_other = fields.Char(
        string='Chi tiết người khác',
        help='Nếu chọn "Khác" — ghi cụ thể (vd: bố vợ, dì ruột, người tư vấn quen…).',
    )
    fa_why = fields.Text(
        string='Tại sao họ không đồng ý?',
        help='Lý do cụ thể họ phản đối: lo chi phí, lo chất lượng, có ý định khác, '
             'thiên kiến với công ty xây dựng…',
    )
    fa_solution = fields.Text(
        string='Hướng xử lý',
        help='NV dự kiến làm gì để giải quyết: gặp trực tiếp, gửi tài liệu, '
             'đề xuất phương án rẻ hơn, mời đến công trường tham quan…',
    )
    # Checklist 5 bước chuẩn xử lý (theo tip_html của tag)
    fa_step1 = fields.Boolean(string='Đã xác định ĐÚNG người ra quyết định cuối')
    fa_step2 = fields.Boolean(string='Đã gặp / gọi trực tiếp người đó')
    fa_step3 = fields.Boolean(string='Đã gửi tài liệu thuyết phục (báo giá, mẫu nhà, công trình thực)')
    fa_step4 = fields.Boolean(string='Đã đưa phương án thay thế (giảm chi phí / đổi mẫu / chia giai đoạn)')
    fa_step5 = fields.Boolean(string='Đã chốt được sự đồng ý của người đó')

    # ============================================================
    # CÂN ĐỐI NGÂN SÁCH (tag.code = 'budget_balance') — sửa intake
    # Section cho phép NV sửa các trường ảnh hưởng báo giá chi tiết
    # (mẫu nhà / móng / mái / vùng / diện tích từng tầng / lửng / tum).
    # Related fields → write thẳng vào lead.vd_intake_*. Lock bypass qua
    # context vd_skip_intake_lock trong write() override.
    # CHỈ editable khi: tag_code='budget_balance' AND status != 'resolved'.
    # ============================================================
    i_house_type = fields.Selection(
        related='lead_id.vd_intake_house_type', readonly=False, string='Mẫu nhà',
    )
    i_foundation_type = fields.Selection(
        related='lead_id.vd_intake_foundation_type', readonly=False, string='Loại móng',
    )
    i_roof_type = fields.Selection(
        related='lead_id.vd_intake_roof_type', readonly=False, string='Loại mái',
    )
    # Vùng giá derive từ tỉnh — sửa qua i_province_id (m2o → res.country.state)
    i_province_id = fields.Many2one(
        related='lead_id.vd_intake_province_id', readonly=False, string='Tỉnh/Thành',
    )
    i_region = fields.Char(related='lead_id.vd_intake_region', readonly=True, string='Vùng giá')
    i_floor_1_m2 = fields.Float(related='lead_id.vd_intake_floor_1_m2', readonly=False, string='Tầng 1 (m²)')
    i_floor_2_m2 = fields.Float(related='lead_id.vd_intake_floor_2_m2', readonly=False, string='Tầng 2 (m²)')
    i_floor_3_m2 = fields.Float(related='lead_id.vd_intake_floor_3_m2', readonly=False, string='Tầng 3 (m²)')
    i_floor_4_m2 = fields.Float(related='lead_id.vd_intake_floor_4_m2', readonly=False, string='Tầng 4 (m²)')
    i_floor_5_m2 = fields.Float(related='lead_id.vd_intake_floor_5_m2', readonly=False, string='Tầng 5 (m²)')
    i_floor_6_m2 = fields.Float(related='lead_id.vd_intake_floor_6_m2', readonly=False, string='Tầng 6 (m²)')
    i_floor_7_m2 = fields.Float(related='lead_id.vd_intake_floor_7_m2', readonly=False, string='Tầng 7 (m²)')
    i_floor_tum_m2 = fields.Float(related='lead_id.vd_intake_floor_tum_m2', readonly=False, string='Tum (m²)')
    i_floor_lung_m2 = fields.Float(related='lead_id.vd_intake_floor_lung_m2', readonly=False, string='Lửng (m²)')
    i_has_tum = fields.Boolean(related='lead_id.vd_intake_has_tum', readonly=False, string='Có Tum')
    i_has_lung = fields.Boolean(related='lead_id.vd_intake_has_lung', readonly=False, string='Có Lửng')
    i_floors_select = fields.Selection(
        related='lead_id.vd_intake_floors_select', readonly=False, string='Số tầng',
    )
    # Mirror read-only: tổng diện tích sàn + estimate hiện tại để NV thấy ngay
    i_total_m2 = fields.Float(related='lead_id.vd_intake_total_m2', readonly=True, string='Tổng diện tích sàn')
    # vd_intake_estimate là Float (không phải Monetary) → related cùng type
    i_estimate = fields.Float(related='lead_id.vd_intake_estimate', readonly=True, string='Phần mềm tính')

    # ============================================================
    # BÁO GIÁ CŨ (snapshot) — chỉ áp dụng cho tag_code='budget_balance'.
    # User spec 2026-05-31: khi NV TẠO vấn đề "Cân đối ngân sách", chụp lại
    # bảng báo giá chi tiết HIỆN TẠI (= báo giá GỐC, trước khi NV chỉnh để
    # cân đối). Sau khi vấn đề được GIẢI QUYẾT, snapshot này hiện ra ở nút
    # "📋 Báo giá cũ" (hover) trên panel báo giá của lead.
    # ============================================================
    old_quote_html = fields.Html(
        string='Báo giá cũ (chụp lúc tạo vấn đề)', sanitize=False, copy=False,
        readonly=True,
        help='Bảng báo giá chi tiết tại thời điểm tạo vấn đề cân đối ngân sách '
             '— giữ lại để KH/NV so sánh với báo giá đã cân đối.',
    )

    _INTAKE_FIELD_NAMES = (
        'i_house_type', 'i_foundation_type', 'i_roof_type', 'i_province_id',
        'i_floor_1_m2', 'i_floor_2_m2', 'i_floor_3_m2', 'i_floor_4_m2',
        'i_floor_5_m2', 'i_floor_6_m2', 'i_floor_7_m2',
        'i_floor_tum_m2', 'i_floor_lung_m2',
        'i_has_tum', 'i_has_lung', 'i_floors_select',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """User spec 2026-05-27: chỉ cho tạo vấn đề khi lead đã CHỐT
        (vd_intake_locked=True). Chưa CHỐT thì KH vẫn ở "Khách mới",
        không sinh vấn đề.

        Bypass: context vd_skip_intake_lock=True (vd cho _vd_ensure_default_problems
        chạy sau khi action_save_intake_done lock xong).
        """
        from odoo.exceptions import UserError
        if not self.env.context.get('vd_skip_intake_lock'):
            lead_ids = {v.get('lead_id') for v in vals_list if v.get('lead_id')}
            if lead_ids:
                leads = self.env['crm.lead'].browse(list(lead_ids))
                for lead in leads:
                    if not lead.vd_intake_locked:
                        raise UserError(_(
                            'Chưa thể tạo vấn đề cho KH "%s" — vui lòng bấm '
                            '🔒 CHỐT THÔNG TIN trước. KH chưa CHỐT vẫn ở '
                            'giai đoạn "Khách mới".'
                        ) % (lead.name or lead.partner_name or 'lead'))

        # User spec 2026-05-31: vấn đề "Cân đối ngân sách" (tag_code='budget_balance')
        # → chụp bảng báo giá chi tiết GỐC ngay lúc tạo (trước khi NV chỉnh giảm).
        for vals in vals_list:
            if vals.get('old_quote_html') or not vals.get('tag_id') or not vals.get('lead_id'):
                continue
            tag = self.env['vd.nego.problem'].browse(vals['tag_id'])
            if tag.code != 'budget_balance':
                continue
            lead = self.env['crm.lead'].browse(vals['lead_id'])
            vals['old_quote_html'] = lead.vd_quote_breakdown_html or ''
        return super().create(vals_list)

    def write(self, vals):
        """Khi NV sửa intake qua section 'Cân đối ngân sách':
        - Bypass lock check trên lead (qua context vd_skip_intake_lock)
        - CHẶN nếu problem.status='resolved' (user yêu cầu: phải tạo vấn đề mới)
        - CHẶN nếu tag_code != 'budget_balance' (chỉ vấn đề này được sửa)
        """
        from odoo.exceptions import UserError
        intake_keys = set(vals.keys()) & set(self._INTAKE_FIELD_NAMES)
        if intake_keys:
            for rec in self:
                if rec.status == 'resolved':
                    raise UserError(_(
                        'Vấn đề "Cân đối ngân sách" này đã giải quyết — '
                        'tạo vấn đề mới cùng loại để sửa tiếp.'
                    ))
                if rec.tag_code != 'budget_balance':
                    raise UserError(_(
                        'Chỉ sửa thông tin báo giá qua vấn đề "Cân đối ngân sách".'
                    ))
            self = self.with_context(vd_skip_intake_lock=True)
        return super().write(vals)

    _sql_constraints = [
        ('lead_tag_uniq', 'unique(lead_id, tag_id)',
         'Mỗi vấn đề chỉ được thêm 1 lần cho 1 KH.'),
    ]

    @api.depends('tag_id', 'tag_id.icon', 'tag_id.name', 'name')
    def _compute_tag_display(self):
        """Chỉ hiển thị TÊN vấn đề (không description chi tiết).
        - Có tag_id → icon + tag.name
        - Không tag_id → lấy phần trước ':' / '—' / ' - ' của field name."""
        for rec in self:
            if rec.tag_id:
                icon = rec.tag_id.icon or '❓'
                rec.tag_display = f"{icon} {rec.tag_id.name}"
                continue
            text = (rec.name or '').strip()
            for sep in [':', '—', ' – ', ' - ']:
                if sep in text:
                    text = text.split(sep, 1)[0].strip()
                    break
            rec.tag_display = text

    @api.onchange('tag_id')
    def _onchange_tag_id(self):
        """Khi NV pick tag → tự fill name từ tag để hiển thị nhất quán."""
        if self.tag_id:
            self.name = self.tag_id.name

    # ============================================================
    # SCRIPTS XỬ LÝ "Tham khảo giá" — 4 mẫu copy-paste sang Zalo
    # ============================================================
    SCRIPT_SOFT = (
        "Dạ em hiểu ạ — xây nhà là việc lớn, anh/chị tham khảo nhiều bên trước "
        "là hoàn toàn hợp lý.\n"
        "Quan trọng là mình so đúng thứ để tránh sau này phát sinh hoặc thiếu sót thôi ạ. "
        "Em xin phép gửi thêm thông tin để anh/chị có thêm cơ sở so sánh nhé."
    )
    SCRIPT_EXPLORE = (
        "Anh/chị đang thấy phân vân nhất giữa những điểm nào ạ?\n"
        "Em hỗ trợ anh/chị bóc tách chi tiết từng phần luôn để mình dễ so sánh "
        "thực tế hơn — tránh trường hợp nhìn tổng giá thấy khác nhau nhưng "
        "thực ra là khác vật tư / khác kết cấu."
    )
    SCRIPT_PAIN = (
        "Thực ra nhiều khách bên em ban đầu cũng tham khảo giá rất nhiều ạ.\n"
        "Nhưng cuối cùng họ quay về vì sợ 3 điều:\n"
        "1) Phát sinh chi phí ngoài hợp đồng\n"
        "2) Vật tư không đúng cam kết\n"
        "3) Không kiểm soát được tiến độ thi công\n"
        "Bên em có quy trình xử lý cụ thể cho từng điểm này — em gửi anh/chị xem nhé."
    )
    SCRIPT_VALUE = (
        "Nếu chỉ nhìn giá thì luôn có bên rẻ hơn ạ — em không cạnh tranh ở chỗ đó.\n"
        "Điều khách hàng bên em quan tâm cuối cùng vẫn là:\n"
        "“Làm xong có đúng như cam kết không?”\n"
        "Em xin gửi anh/chị: hợp đồng mẫu + checklist vật tư + ảnh tiến độ "
        "công trình thực tế — anh/chị xem rồi mình trao đổi thêm ạ."
    )

    def _copy_action(self, text, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'vd_copy_to_clipboard',
            'params': {
                'text': text,
                'message': message,
                'silent': True,
            },
        }

    def action_copy_script_soft(self):
        self.ensure_one()
        return self._copy_action(self.SCRIPT_SOFT, _('Đã copy MẪU MỀM — dán vào Zalo gửi KH.'))

    def action_copy_script_explore(self):
        self.ensure_one()
        return self._copy_action(self.SCRIPT_EXPLORE, _('Đã copy MẪU KÉO KHAI THÁC — dán vào Zalo gửi KH.'))

    def action_copy_script_pain(self):
        self.ensure_one()
        return self._copy_action(self.SCRIPT_PAIN, _('Đã copy MẪU GÀI NỖI ĐAU — dán vào Zalo gửi KH.'))

    def action_copy_script_value(self):
        self.ensure_one()
        return self._copy_action(self.SCRIPT_VALUE, _('Đã copy MẪU KÉO VỀ GIÁ TRỊ — dán vào Zalo gửi KH.'))

    def action_mark_contacted(self):
        """Bấm 1 lần để cập nhật last_contact_date = now và status → in_progress nếu đang open."""
        self.ensure_one()
        vals = {'last_contact_date': fields.Datetime.now()}
        if self.status == 'open':
            vals['status'] = 'in_progress'
        self.write(vals)
        return True
