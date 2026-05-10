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

    # Toggle "phiếu khai thác" — False = chế độ tóm tắt (compact card),
    # True = chế độ mở rộng (form fields hiện đầy đủ + sheet wider + sidebar
    # bong bóng kịch bản). Mặc định False; bật khi NV bấm Gọi hoặc nút "Mở
    # khai thác". Tắt khi NV bấm "Lưu & Hoàn tất".
    vd_intake_open = fields.Boolean(
        string='Mở phiếu khai thác', default=False, copy=False,
    )

    # Khai thác — tổng hợp nhu cầu khách hàng (xây dựng / nhà ở)
    # `help` = kịch bản gợi ý cho NV khi gọi (hiển thị tooltip).
    vd_intake_province_id = fields.Many2one(
        'res.country.state', string='Tỉnh / Thành',
        domain="[('country_id.code', '=', 'VN')]",
        help='Hỏi: "Anh/chị xây ở tỉnh / thành nào ạ?"',
    )
    vd_intake_district = fields.Many2one(
        'vd.district', string='Huyện / Quận',
        help='Hỏi: "Khu vực huyện / quận nào?"',
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
        ('khac', 'Khác (mô tả thêm)'),
    ], string='Kiểu nhà',
        help='Hỏi: "Anh/chị muốn xây kiểu nhà nào? Mái bằng, mái thái, biệt thự…?"',
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

    @api.depends('vd_intake_length_m', 'vd_intake_width_m')
    def _compute_area_from_dims(self):
        for rec in self:
            if rec.vd_intake_length_m and rec.vd_intake_width_m:
                rec.vd_intake_area_m2 = rec.vd_intake_length_m * rec.vd_intake_width_m
            elif not rec.vd_intake_area_m2:
                rec.vd_intake_area_m2 = 0.0
            # Nếu user đã nhập area_m2 thủ công và 1 trong 2 dim trống → giữ nguyên
    vd_intake_floors_num = fields.Float(
        string='Số tầng', digits=(10, 1), default=1.0,
        help='Vd: 2.5 tầng (2 tầng + tum).',
    )
    vd_intake_foundation_type = fields.Selection([
        ('don', 'Móng đơn'),
        ('bang', 'Móng băng'),
        ('coc', 'Móng cọc'),
    ], string='Loại móng')
    # ===== Loại mái — directly selectable, FILTER theo Kiểu nhà =====
    vd_intake_roof_type = fields.Selection([
        ('mai_bang', 'Mái bằng (20%)'),
        ('mai_nhat_kdt', 'Mái nhật — Không đổ trần (42%)'),
        ('mai_nhat_cdt', 'Mái nhật — Có đổ trần (48%)'),
        ('mai_thai_kdt', 'Mái thái — Không đổ trần (45%)'),
        ('mai_thai_cdt', 'Mái thái — Có đổ trần (55%)'),
        ('thong_tang', 'Thông tầng (40%)'),
        ('mai_trang_tri', 'Mái trang trí (50%)'),
        ('mai_trang_tri_dt', 'Mái trang trí — Đổ trần (100%)'),
        ('mai_ton_1m', 'Mái tôn 1 mặt (13%)'),
        ('mai_ton_2m', 'Mái tôn 2 mặt (16%)'),
        ('mai_ton_3m', 'Mái tôn 3 mặt (20%)'),
    ], string='Loại mái')

    @api.onchange('vd_intake_house_type')
    def _onchange_house_type_reset_roof(self):
        """Đổi Kiểu nhà → reset Loại mái nếu không còn valid theo mapping."""
        valid_roofs = {
            'mai_bang': ['mai_bang'],
            'mai_thai': ['mai_thai_kdt', 'mai_thai_cdt'],
            'mai_nhat': ['mai_nhat_kdt', 'mai_nhat_cdt'],
            # Nhà phố / biệt thự / ống / cấp 4 / tum / chung cư / khác → tất cả
        }
        for rec in self:
            ok = valid_roofs.get(rec.vd_intake_house_type)
            if ok and rec.vd_intake_roof_type not in ok:
                rec.vd_intake_roof_type = False
    vd_intake_car_access = fields.Boolean(string='Ô tô vào được', default=True)
    vd_intake_budget_amount = fields.Monetary(
        string='Ngân sách KH (VNĐ)', currency_field='vd_currency_vnd_id',
        help='NV gõ số tiền cụ thể KH dự kiến (VD: 2_000_000_000). '
             'Nếu để trống, dùng vd_intake_budget Selection.',
    )
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

    # ============ BÁO GIÁ — fields working trong panel báo giá ============
    vd_quote_template_id = fields.Many2one(
        'vd.quote.template', string='Template báo giá',
        domain="[('active', '=', True)]",
        help='Admin upload template tham khảo. NV chọn template áp dụng cho KH này.',
    )
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
        'vd_intake_area_m2', 'vd_intake_floors_num', 'vd_intake_estimate',
        'vd_intake_region', 'vd_intake_car_access', 'vd_quote_price',
    )
    def _compute_quote_preview_html(self):
        """Render báo giá HTML inline preview — same logic with QWeb PDF report."""
        from datetime import date
        Pricing = self.env['vd.pricing.region']
        for rec in self:
            area = rec.vd_intake_area_m2 or 0
            floors = rec.vd_intake_floors_num or 1.0
            if area <= 0 or not rec.vd_intake_region:
                rec.vd_quote_preview_html = (
                    '<div style="padding:1rem;text-align:center;color:#868e96;'
                    'font-style:italic;background:#f8f9fa;border:1px dashed #dee2e6;'
                    'border-radius:8px;">'
                    '<i class="fa fa-file-pdf-o" style="font-size:2rem;display:block;'
                    'margin-bottom:0.5rem;"></i>'
                    'Chưa đủ thông tin khai thác để preview báo giá.<br/>'
                    '<small>Cần: tỉnh/thành, diện tích, số tầng, móng, mái.</small>'
                    '</div>'
                )
                continue

            pricing = Pricing.search([('code', '=', rec.vd_intake_region)], limit=1)
            if not pricing:
                rec.vd_quote_preview_html = '<i>Chưa có pricing region.</i>'
                continue

            san_unit = rec._get_san_unit_price(pricing, area, rec.vd_intake_car_access)
            found_pct = rec._get_foundation_pct(
                pricing, rec.vd_intake_foundation_type, area >= 70,
            )
            roof_pct = rec._get_roof_pct(pricing, rec.vd_intake_roof_type)
            found_cost = area * (found_pct / 100.0) * san_unit
            floor_cost = area * floors * san_unit
            roof_cost = area * (roof_pct / 100.0) * san_unit

            # Labels
            house_lbl = dict(self._fields['vd_intake_house_type'].selection).get(
                rec.vd_intake_house_type, 'NHÀ DÂN DỤNG'
            ) or 'NHÀ DÂN DỤNG'
            found_lbl = dict(self._fields['vd_intake_foundation_type'].selection).get(
                rec.vd_intake_foundation_type, 'MÓNG ĐƠN'
            ) or 'MÓNG ĐƠN'
            roof_lbl = dict(self._fields['vd_intake_roof_type'].selection).get(
                rec.vd_intake_roof_type, 'MÁI BẰNG'
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
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;">{found_lbl}</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{area:.0f} M2 x {found_pct:.0f}%</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(found_cost)} VNĐ</td>
                <td rowspan="3" style="padding:0.45rem 0.6rem;border:1px solid #1864ab;background:#fff;text-align:center;font-weight:700;font-size:13pt;color:#1a1a1a;vertical-align:middle;">{fmt(total_price)} VNĐ</td>
            </tr>
            <tr>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;">Tầng trệt</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{area:.0f}</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(floor_cost)} VNĐ</td>
            </tr>
            <tr>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;">{roof_lbl}</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:center;">{area:.0f} M2 x {roof_pct:.0f}%</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(san_unit)} VNĐ</td>
                <td style="padding:0.45rem 0.6rem;border:1px solid #93c5fd;background:#fff;text-align:right;">{fmt(roof_cost)} VNĐ</td>
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

    @api.depends('vd_intake_province_id')
    def _compute_intake_region(self):
        for rec in self:
            province = rec.vd_intake_province_id.name if rec.vd_intake_province_id else None
            if province in self._BAC_PROVINCES:
                rec.vd_intake_region = 'bac'
            elif province in self._TRUNG_PROVINCES:
                rec.vd_intake_region = 'trung'
            elif province:
                rec.vd_intake_region = 'nam'
            else:
                rec.vd_intake_region = False

    def _get_san_unit_price(self, pricing, area_per_floor, has_car):
        """Đơn giá sàn (đ/m²) tùy DT 1 sàn & ô tô vào được không."""
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

    def _get_foundation_pct(self, pricing, ftype, is_lon):
        if ftype == 'don':
            return pricing.mong_don_lon if is_lon else pricing.mong_don_nho
        if ftype == 'bang':
            return pricing.mong_bang_lon if is_lon else pricing.mong_bang_nho
        if ftype == 'coc':
            return pricing.mong_coc_lon if is_lon else pricing.mong_coc_nho
        return 0.0

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
        'vd_intake_area_m2', 'vd_intake_length_m', 'vd_intake_width_m',
        'vd_intake_floors_num',
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

            area = rec.vd_intake_area_m2 or 0.0
            floors = rec.vd_intake_floors_num or 1.0
            if area <= 0 or not rec.vd_intake_region:
                continue

            pricing = Pricing.search([('code', '=', rec.vd_intake_region)], limit=1)
            if not pricing:
                continue

            total_floor_area = area * floors

            # ===== Tính chi tiết: Móng + Sàn × tầng + Mái =====
            san_unit = rec._get_san_unit_price(pricing, area, rec.vd_intake_car_access)
            # Móng (chỉ áp dụng cho DT đất 1 sàn)
            found_pct = rec._get_foundation_pct(
                pricing, rec.vd_intake_foundation_type, area >= 70,
            ) / 100.0
            found_cost = area * found_pct * san_unit
            # Sàn (toàn bộ tầng)
            floor_cost = total_floor_area * san_unit
            # Mái (DT mái = DT 1 sàn)
            roof_pct = rec._get_roof_pct(pricing, rec.vd_intake_roof_type) / 100.0
            roof_cost = area * roof_pct * san_unit

            total = found_cost + floor_cost + roof_cost

            # Phụ phí móng cọc / móng băng
            if rec.vd_intake_foundation_type == 'coc':
                total *= 1 + (pricing.pct_mong_coc / 100.0)
            elif rec.vd_intake_foundation_type == 'bang':
                total *= 1 + (pricing.pct_mong_bang / 100.0)

            # Phụ phí tỉnh vùng cao (+300k/m² × total_floor_area)
            province_name = rec.vd_intake_province_id.name if rec.vd_intake_province_id else None
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
        # MỌI thay đổi stage_id (kể cả qua badge widget / auto-save / external API)
        # đều cần disable auto-tracking — server chưa config email sender, sẽ
        # raise "Invalid Operation: Unable to send message, please configure
        # the sender's email address" nếu để Odoo CRM tự gửi email tracking.
        if 'stage_id' in vals:
            self = self.with_context(mail_notrack=True, tracking_disable=True)
        result = super().write(vals)
        if 'stage_id' in vals:
            for rec in self:
                if rec.stage_is_lost and rec.active:
                    rec.with_context(skip_lost_archive=True).active = False
        return result

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
        done yet. NV vừa nói chuyện vừa điền popup."""
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
        # MỞ phiếu khai thác inline (mở rộng form) — NV vừa nói chuyện vừa điền.
        self.vd_intake_open = True
        return True

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
        """Lưu thông tin khai thác → đóng phiếu (quay về tóm tắt) + AUTO
        chuyển stage sang Báo giá (nếu chưa). Trả về effect rainbow_man."""
        self.ensure_one()
        filled = sum(1 for f in self._intake_data_fields if self[f])
        total = len(self._intake_data_fields)
        pct = round(filled * 100 / total) if total else 0
        kh = self.partner_name or self.contact_name or self.name or 'khách hàng'

        # Đóng phiếu khai thác → trở về tóm tắt
        write_vals = {'vd_intake_open': False}

        # AUTO chuyển stage sang "Báo giá" nếu đang ở new/potential & có data
        auto_quoted = False
        if filled > 0 and self.stage_code in (False, '', 'new', 'potential'):
            quote_stage = self.env.ref('vd_crm_lead.stage_quote', raise_if_not_found=False) \
                          or self.env['crm.stage'].search([('code', '=', 'quote')], limit=1)
            if quote_stage:
                old_stage_name = self.stage_id.name or ''
                write_vals['stage_id'] = quote_stage.id
                auto_quoted = (old_stage_name, quote_stage.name)

        # write override sẽ tự apply mail_notrack/tracking_disable cho stage_id
        self.write(write_vals)

        if auto_quoted:
            old_stage_name, new_stage_name = auto_quoted
            self.message_post(
                subtype_xmlid='mail.mt_note',
                body=_(
                    "✅ <b>Lưu khai thác + chuyển sang báo giá</b> — "
                    "từ <i>%s</i> sang <b>%s</b>."
                ) % (old_stage_name, new_stage_name),
            )

        if filled >= total - 1:
            message = (
                f'🎉 Khai thác XUẤT SẮC! ({filled}/{total} trường — {pct}%)\n'
                f'Chúc mừng bạn đã khai thác {kh} thành công! 🌈'
            )
            if auto_quoted:
                message += '\n→ Đã chuyển sang BÁO GIÁ. Lập file báo giá nhé!'
        elif filled >= total * 2 // 3:
            message = (
                f'👏 Khai thác tốt! ({filled}/{total} trường — {pct}%)\n'
            )
            if auto_quoted:
                message += '→ Đã chuyển sang BÁO GIÁ.'
            else:
                message += 'Bổ sung thêm các trường còn thiếu sau nhé!'
        else:
            message = (
                f'📝 Đã lưu — mới khai thác {filled}/{total} trường ({pct}%).\n'
                f'Cố gắng bổ sung thêm khi có cơ hội!'
            )

        return {
            'effect': {
                'fadeout': 'slow',
                'message': message,
                'type': 'rainbow_man',
                'img_url': '/vd_crm_lead/static/src/img/celebration.svg',
            },
        }

    # ============ PHASE A — WORKFLOW BUTTONS ============
    def action_mark_no_demand(self):
        """KH KHÔNG có nhu cầu → mở wizard nhập lý do → set stage = lost."""
        self.ensure_one()
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
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Đã chuyển sang Báo giá',
                'message': f'Lead "{self.name or ""}" đã sẵn sàng để báo giá.',
                'type': 'success',
                'sticky': False,
            },
        }

    # ============ PHASE B — BÁO GIÁ ============
    def _build_quote_snapshot_vals(self):
        """Thu thập tất cả field cần snapshot vào vd.quote.version."""
        self.ensure_one()
        Pricing = self.env['vd.pricing.region']
        pricing = Pricing.search([('code', '=', self.vd_intake_region or '')], limit=1)
        # Tính breakdown chi tiết (móng / sàn / mái / phụ phí)
        san_unit = pricing._get_san_unit_price_or_default(self.vd_intake_area_m2 or 0,
                                                          self.vd_intake_car_access) if hasattr(pricing, '_get_san_unit_price_or_default') else 0
        # Use existing method
        if pricing and self.vd_intake_area_m2:
            san_unit = self._get_san_unit_price(pricing, self.vd_intake_area_m2,
                                                 self.vd_intake_car_access)
            found_pct = self._get_foundation_pct(
                pricing, self.vd_intake_foundation_type, self.vd_intake_area_m2 >= 70,
            )
            roof_pct = self._get_roof_pct(pricing, self.vd_intake_roof_type)
        else:
            san_unit = 0; found_pct = 0; roof_pct = 0

        area = self.vd_intake_area_m2 or 0
        floors = self.vd_intake_floors_num or 1.0
        total_floor = area * floors
        found_cost = area * (found_pct / 100.0) * san_unit
        floor_cost = total_floor * san_unit
        roof_cost = area * (roof_pct / 100.0) * san_unit
        surcharge = self.vd_intake_estimate - (found_cost + floor_cost + roof_cost) if self.vd_intake_estimate else 0

        # Labels (text-readable cho snapshot)
        house_lbl = dict(self._fields['vd_intake_house_type'].selection).get(
            self.vd_intake_house_type, ''
        )
        if self.vd_intake_house_type == 'khac' and self.vd_intake_house_type_other:
            house_lbl += f' ({self.vd_intake_house_type_other})'
        found_lbl = dict(self._fields['vd_intake_foundation_type'].selection).get(
            self.vd_intake_foundation_type, ''
        )
        roof_lbl = dict(self._fields['vd_intake_roof_type'].selection).get(
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

    def _build_quote_context(self):
        """Build dict context để truyền vào docx template (Jinja placeholders).
        Tất cả intake data → key flat đơn giản cho NV viết template dễ."""
        self.ensure_one()
        from datetime import date
        Pricing = self.env['vd.pricing.region']
        pricing = Pricing.search([('code', '=', self.vd_intake_region or '')], limit=1)

        area = self.vd_intake_area_m2 or 0
        floors = self.vd_intake_floors_num or 1.0
        san_unit = self._get_san_unit_price(pricing, area, self.vd_intake_car_access) if pricing and area else 0
        found_pct = self._get_foundation_pct(pricing, self.vd_intake_foundation_type, area >= 70) if pricing else 0
        roof_pct = self._get_roof_pct(pricing, self.vd_intake_roof_type) if pricing else 0
        found_cost = area * (found_pct / 100.0) * san_unit
        floor_cost = area * floors * san_unit
        roof_cost = area * (roof_pct / 100.0) * san_unit
        total = self.vd_quote_price or self.vd_intake_estimate or 0

        house_lbl = dict(self._fields['vd_intake_house_type'].selection).get(
            self.vd_intake_house_type, 'NHÀ DÂN DỤNG'
        ) or 'NHÀ DÂN DỤNG'
        found_lbl = dict(self._fields['vd_intake_foundation_type'].selection).get(
            self.vd_intake_foundation_type, 'MÓNG ĐƠN'
        ) or 'MÓNG ĐƠN'
        roof_lbl = dict(self._fields['vd_intake_roof_type'].selection).get(
            self.vd_intake_roof_type, 'MÁI BẰNG'
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
            'area': f'{area:.0f}',
            'floors': f'{floors:.1f}'.rstrip('0').rstrip('.'),
            'total_floor_area': f'{area * floors:.0f}',
            'unit_price': fmt(san_unit),
            'found_pct': f'{found_pct:.0f}',
            'roof_pct': f'{roof_pct:.0f}',
            'found_cost': fmt(found_cost),
            'floor_cost': fmt(floor_cost),
            'roof_cost': fmt(roof_cost),
            'total_price': fmt(total),
            'total_price_int': int(total),
            # Tiến độ thanh toán (4 đợt)
            'tt1': fmt(total * 0.30),
            'tt2': fmt(total * 0.30),
            'tt3': fmt(total * 0.30),
            'tt4': fmt(total * 0.10),
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
            'MÁI NGÓI': ctx['house_type'],
            'MÓNG ĐƠN': ctx['foundation'],
        }

        # 2-STEP overlay với DejaVu Sans (Vietnamese support):
        # + Unicode normalization (NFC) để search match được text Vietnamese
        # + Redaction rect mở rộng 2px để whiteout sạch text cũ
        # + Bỏ qua replacement khi value trống/null (giữ text gốc)
        import unicodedata
        page = doc[page_idx]
        FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

        def search_robust(text):
            """Search với cả NFC + NFD + lowercase variants."""
            results = []
            for variant in {text, unicodedata.normalize('NFC', text),
                            unicodedata.normalize('NFD', text)}:
                try:
                    found = page.search_for(variant)
                    if found:
                        results.extend(found)
                        break  # tìm thấy rồi, không cần thử variant khác
                except Exception:
                    continue
            return results

        # Phase 1: collect rect + new text + whiteout (rect mở rộng để clean)
        to_insert = []
        for old_text, new_text in replacements.items():
            new_text = str(new_text or '').strip()
            old_text = str(old_text)
            # Skip nếu giá trị mới trống hoặc giống cũ
            if not new_text or old_text.strip() == new_text:
                continue
            rects = search_robust(old_text)
            for rect in rects:
                # Mở rộng rect 1.5px mỗi phía → whiteout clean, không lòi text cũ
                expanded = fitz.Rect(rect.x0 - 1.5, rect.y0 - 1,
                                      rect.x1 + 1.5, rect.y1 + 1)
                to_insert.append((expanded, new_text))
                page.add_redact_annot(expanded, fill=(1, 1, 1))

        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Phase 2: insert_textbox với DejaVu Sans
        for rect, new_text in to_insert:
            fsize = max(8, min(int(rect.height * 0.7), 13))
            try:
                page.insert_textbox(
                    rect, new_text,
                    fontfile=FONT_FILE, fontname='vd_dejavu',
                    fontsize=fsize, color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            except Exception:
                try:
                    page.insert_text(
                        (rect.x0 + 1, rect.y1 - 2), new_text,
                        fontfile=FONT_FILE, fontname='vd_dejavu_fb',
                        fontsize=fsize, color=(0, 0, 0),
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

        writer = PdfWriter()
        for i, page in enumerate(tpl_reader.pages):
            if i == target_idx:
                # Thay trang này bằng báo giá
                for new_p in baogia_reader.pages:
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
        """ƯU TIÊN: PyMuPDF overlay text → giữ NGUYÊN 100% template (font, ảnh, dấu mộc).
        1. .pdf + PyMuPDF overlay text (BEST: giữ nguyên hết, chỉ đổi data text)
        2. .pdf splice page (fallback: thay 1 trang QWeb-generated)
        3. .pdf AcroForm fill (fallback)
        4. .docx Jinja merge
        5. Default 1 trang QWeb (last resort)"""
        try:
            att = self._render_template_pdf_overlay_text()
            if att:
                return att
        except Exception:
            pass
        try:
            att = self._render_template_pdf_replace_page()
            if att:
                return att
        except Exception:
            pass
        try:
            att = self._render_template_pdf()
            if att:
                return att
        except Exception:
            pass
        try:
            att = self._render_template_docx()
            if att:
                return att
        except Exception:
            pass
        try:
            return self._generate_single_page_quote_pdf()
        except Exception:
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
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🔒 Đã chốt báo giá → Đàm phán',
                'message': f'Deadline đàm phán: {deadline.strftime("%d/%m/%Y")} (7 ngày)',
                'type': 'success',
                'sticky': False,
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

    def action_sign_contract(self):
        """✍️ Mở wizard ký HĐ + nhập tiền cọc (yêu cầu ≥ 50tr)."""
        self.ensure_one()
        if not self.vd_quote_locked:
            raise UserError(_('Phải chốt báo giá trước khi ký HĐ.'))
        if self.vd_contract_signed:
            raise UserError(_('Hợp đồng đã được ký rồi.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ký hợp đồng + nhận cọc'),
            'res_model': 'vd.contract.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'dialog_size': 'medium',
            },
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

    def _dashboard_is_manager(self):
        """Admin / Sales Manager / Settings → xem được data của TẤT CẢ NV."""
        u = self.env.user
        return (
            u.has_group('sales_team.group_sale_manager')
            or u.has_group('base.group_system')
            or u._is_admin()
        )

    def _dashboard_resolve_scope(self, user_id):
        """Trả về (user_record_or_None, scope_label, lead_user_domain, call_user_domain).
        - user_id = 'all' hoặc 0 → toàn bộ NV (chỉ cho phép manager)
        - user_id = int → 1 NV cụ thể (manager xem được mọi NV; NV thường chỉ chính họ)
        - user_id = None → mặc định: manager → 'all', NV thường → chính họ
        """
        is_manager = self._dashboard_is_manager()

        # Chuẩn hoá input
        if user_id in ('all', 0, '0'):
            user_id = 'all' if is_manager else self.env.user.id

        if user_id is None:
            user_id = 'all' if is_manager else self.env.user.id

        if user_id == 'all':
            # Toàn bộ NV — chỉ giới hạn lead có user_id != False để tránh đếm lead chưa giao
            return (
                None, 'Tất cả nhân viên',
                [('user_id', '!=', False)],
                [('user_id', '!=', False)],
            )

        # 1 NV cụ thể — NV thường không được xem NV khác
        target = self.env['res.users'].browse(int(user_id))
        if not is_manager and target.id != self.env.user.id:
            target = self.env.user
        return (
            target, target.name,
            [('user_id', '=', target.id)],
            [('user_id', '=', target.id)],
        )

    @api.model
    def dashboard_users(self):
        """Danh sách NV để manager chọn xem dashboard theo từng NV."""
        if not self._dashboard_is_manager():
            u = self.env.user
            return [{'id': u.id, 'name': u.name}]
        users = self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ], order='name')
        # Chỉ giữ NV có ít nhất 1 lead — bớt nhiễu
        sales_users = users.filtered(
            lambda u: self.env['crm.lead'].sudo().search_count([('user_id', '=', u.id)]) > 0
        )
        return [{'id': u.id, 'name': u.name, 'login': u.login} for u in sales_users]

    @api.model
    def dashboard_data(self, user_id=None):
        """Single-payload data for the OWL dashboard."""
        scope_user, scope_label, domain_user, call_user_domain = self._dashboard_resolve_scope(user_id)
        is_manager = self._dashboard_is_manager()

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
            'user': {
                'id': scope_user.id if scope_user else 0,
                'name': scope_label,
                'is_all': scope_user is None,
            },
            'is_manager': is_manager,
            'current_user_id': self.env.user.id,
            'selected_user_id': scope_user.id if scope_user else 0,
            'kpi': kpi,
            'errors': errors,
            'stages': stage_payload,
        }

    @api.model
    def dashboard_leads(self, stage_id, user_id=None, limit=80):
        scope_user, _label, domain_user, _call_dom = self._dashboard_resolve_scope(user_id)
        leads = self.search(
            domain_user + [('stage_id', '=', stage_id)],
            limit=limit,
            order='probability desc, callback_date asc, create_date desc',
        )
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
        } for l in leads]
