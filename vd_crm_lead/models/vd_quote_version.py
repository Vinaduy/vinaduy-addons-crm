"""Phiên bản báo giá — snapshot mỗi lần NV bấm "Lưu báo giá".

Lưu CẢ 2 (theo yêu cầu user):
- Snapshot full: copy toàn bộ field từ lead/quote vào version mới
- Diff so với version trước: log những gì thay đổi vào `changes_log`

Quy trình:
- NV chỉnh báo giá trong panel → bấm "💾 Lưu báo giá" → tạo version mới
  (version_no auto-increment trong scope của lead)
- Có thể tạo nhiều version → KH duyệt qua các version
- Khi NV bấm "🔒 Chốt báo giá" → version cuối được set state='locked'
  + lead.stage chuyển sang Đàm phán
"""

from odoo import _, api, fields, models


class VdQuoteVersion(models.Model):
    _name = 'vd.quote.version'
    _description = 'Phiên bản báo giá'
    _order = 'lead_id, version_no desc'
    _rec_name = 'display_name'

    lead_id = fields.Many2one(
        'crm.lead', string='Lead', required=True, ondelete='cascade', index=True,
    )
    version_no = fields.Integer(string='V', readonly=True, copy=False)
    display_name = fields.Char(compute='_compute_display_name', store=False)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('locked', 'Đã chốt'),
    ], default='draft', readonly=True, copy=False)

    template_id = fields.Many2one('vd.quote.template', string='Template áp dụng',
                                   ondelete='restrict')

    # ========== Snapshot KH ==========
    kh_name = fields.Char(string='Tên KH')
    kh_phone = fields.Char(string='SĐT')
    kh_address = fields.Char(string='Địa chỉ KH')
    region_label = fields.Char(string='Vùng (Bắc/Trung/Nam)')

    # ========== Snapshot kỹ thuật ==========
    length_m = fields.Float(string='Dài (m)', digits=(8, 2))
    width_m = fields.Float(string='Rộng (m)', digits=(8, 2))
    area_m2 = fields.Float(string='DT 1 sàn (m²)', digits=(10, 1))
    floors = fields.Float(string='Số tầng', digits=(10, 1))
    house_type_label = fields.Char(string='Kiểu nhà')
    foundation_label = fields.Char(string='Loại móng')
    roof_label = fields.Char(string='Loại mái')

    # ========== Snapshot pricing breakdown ==========
    san_unit_price = fields.Monetary(string='Đơn giá sàn (đ/m²)',
                                       currency_field='currency_id')
    found_pct = fields.Float(string='% Móng', digits=(5, 2))
    roof_pct = fields.Float(string='% Mái', digits=(5, 2))
    found_cost = fields.Monetary(string='Tiền móng', currency_field='currency_id')
    floor_cost = fields.Monetary(string='Tiền sàn', currency_field='currency_id')
    roof_cost = fields.Monetary(string='Tiền mái', currency_field='currency_id')
    surcharge = fields.Monetary(string='Phụ phí', currency_field='currency_id')
    estimate_total = fields.Monetary(string='Đơn giá ước tính', currency_field='currency_id')

    # ========== Giá NV CHỐT BÁO ==========
    quote_price = fields.Monetary(string='Giá BÁO cho KH', currency_field='currency_id',
                                    help='Số tiền NV chốt báo (có thể khác estimate).')

    # ========== Vật liệu / thanh toán / ghi chú ==========
    material = fields.Char(string='Vật liệu chính')
    payment_schedule = fields.Text(string='Tiến độ thanh toán')
    notes = fields.Text(string='Ghi chú báo giá')

    # ========== Diff so với version trước ==========
    changes_log = fields.Text(string='Thay đổi so với V trước', readonly=True)

    # ========== File PDF tự generate ==========
    pdf_attachment_id = fields.Many2one('ir.attachment', string='File PDF', copy=False)

    currency_id = fields.Many2one('res.currency', compute='_compute_vnd_currency')

    create_date = fields.Datetime(readonly=True)
    create_uid = fields.Many2one('res.users', readonly=True)

    def _compute_vnd_currency(self):
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        for rec in self:
            rec.currency_id = vnd

    @api.depends('version_no', 'state', 'create_date', 'create_uid', 'quote_price')
    def _compute_display_name(self):
        for rec in self:
            ts = fields.Datetime.context_timestamp(rec, rec.create_date).strftime('%H:%M %d/%m') if rec.create_date else ''
            user = rec.create_uid.name or ''
            lock = ' 🔒' if rec.state == 'locked' else ''
            price = ''
            if rec.quote_price:
                price = f' • {rec.quote_price:,.0f}đ'.replace(',', '.')
            rec.display_name = f'V{rec.version_no} ({ts}) — {user}{price}{lock}'

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-increment version_no per lead
        for vals in vals_list:
            if not vals.get('version_no') and vals.get('lead_id'):
                last = self.search(
                    [('lead_id', '=', vals['lead_id'])],
                    order='version_no desc', limit=1,
                )
                vals['version_no'] = (last.version_no + 1) if last else 1
        return super().create(vals_list)

    def action_view_pdf(self):
        """Mở/tải PDF của version này. Nếu chưa có → generate."""
        self.ensure_one()
        if not self.pdf_attachment_id:
            self._generate_pdf()
        if not self.pdf_attachment_id:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.pdf_attachment_id.id}?download=true',
            'target': 'self',
        }

    def _generate_pdf(self):
        """Render QWeb report PDF + lưu vào ir.attachment."""
        self.ensure_one()
        report = self.env.ref('vd_crm_lead.action_vd_quote_report', raise_if_not_found=False)
        if not report:
            return False
        pdf_content, _content_type = report._render_qweb_pdf(report.report_name, [self.id])
        att = self.env['ir.attachment'].create({
            'name': f'BaoGia_V{self.version_no}_{self.lead_id.name or "lead"}.pdf',
            'type': 'binary',
            'datas': __import__('base64').b64encode(pdf_content),
            'res_model': 'vd.quote.version',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.pdf_attachment_id = att
        return att

    def _build_diff_log(self, prev):
        """Build text diff: so sánh self với prev → list field nào thay đổi."""
        if not prev:
            return _('🆕 Báo giá đầu tiên (V1).')
        compare_fields = [
            ('quote_price', 'Giá báo'),
            ('estimate_total', 'Đơn giá ước tính'),
            ('area_m2', 'Diện tích sàn'),
            ('floors', 'Số tầng'),
            ('house_type_label', 'Kiểu nhà'),
            ('foundation_label', 'Loại móng'),
            ('roof_label', 'Loại mái'),
            ('material', 'Vật liệu'),
            ('payment_schedule', 'Tiến độ TT'),
            ('notes', 'Ghi chú'),
        ]
        changes = []
        for fname, label in compare_fields:
            old, new = getattr(prev, fname), getattr(self, fname)
            if old != new:
                if isinstance(old, float) and isinstance(new, float):
                    if abs((old or 0) - (new or 0)) < 0.01:
                        continue
                    diff = (new or 0) - (old or 0)
                    sign = '↑' if diff > 0 else '↓'
                    changes.append(f'{label}: {old:,.0f} → {new:,.0f} ({sign}{abs(diff):,.0f})'.replace(',', '.'))
                else:
                    old_s = (str(old) if old else '∅')[:50]
                    new_s = (str(new) if new else '∅')[:50]
                    changes.append(f'{label}: "{old_s}" → "{new_s}"')
        if not changes:
            return _('(Không có thay đổi đáng kể so với V%d.)') % prev.version_no
        return _('Thay đổi so với V%d:\n• %s') % (prev.version_no, '\n• '.join(changes))
