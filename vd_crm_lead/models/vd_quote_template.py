"""Template báo giá — admin upload BẤT KỲ format file (.docx, .xlsx, .pdf, .png...)
NV chọn template từ dropdown trong panel báo giá → có thể download tham khảo
hoặc tự tạo PDF báo giá Vietnamese-style từ data."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdQuoteTemplateCategory(models.Model):
    """Nhóm template báo giá — phân loại 4 chiều:
    - region: Vùng miền (Bắc/Trung/Nam)
    - floor_range: Số tầng (1T / 2-4T / 5+T)
    - foundation: Loại móng (Đơn/Băng/Cọc) — match crm.lead.vd_intake_foundation_type
    - roof_simple: Loại mái (Bằng/Ngói) — gom từ 11 giá trị mái của lead

    Khi NV chọn intake (vùng, tầng, móng, mái) ở lead form, dropdown
    template auto-filter category match cả 4 chiều.
    """
    _name = 'vd.quote.template.category'
    _description = 'Nhóm template báo giá'
    _order = 'sequence, name'

    name = fields.Char(string='Tên nhóm', required=True, translate=False)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Màu', default=0,
                            help='Mã màu (0-11) cho badge nhóm')
    description = fields.Char(string='Mô tả ngắn')
    template_count = fields.Integer(string='Số template',
                                     compute='_compute_template_count')
    active = fields.Boolean(default=True)

    # ===== 4 chiều phân loại (auto-filter trên lead) =====
    region = fields.Selection([
        ('bac', 'Miền Bắc'),
        ('trung', 'Miền Trung'),
        ('nam', 'Miền Nam'),
    ], string='Vùng miền',
       help='Match với vd_intake_region của lead (tự compute từ tỉnh thành).')
    floor_range = fields.Selection([
        ('1', '1 Tầng'),
        ('2_4', '2-4 Tầng'),
        ('5_plus', '5+ Tầng'),
    ], string='Số tầng',
       help='Phân loại theo vd_intake_floors_num: 1 / 2-4 / 5+.')
    foundation = fields.Selection([
        ('don', 'Móng đơn'),
        ('bang', 'Móng băng'),
        ('coc', 'Móng cọc'),
    ], string='Loại móng',
       help='Match trực tiếp với vd_intake_foundation_type của lead.')
    roof_simple = fields.Selection([
        ('bang', 'Mái bằng'),
        ('ngoi', 'Mái ngói / nghiêng'),
    ], string='Loại mái',
       help='Mái bằng = mai_bang. Mái ngói = các loại nhật/thái/tôn/'
            'trang trí (gom chung 1 nhóm).')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tên nhóm template không được trùng.'),
    ]

    @api.depends()
    def _compute_template_count(self):
        Tpl = self.env['vd.quote.template']
        for rec in self:
            rec.template_count = Tpl.search_count([('category_id', '=', rec.id)])


class VdQuoteTemplate(models.Model):
    _name = 'vd.quote.template'
    _description = 'Template báo giá'
    _order = 'category_id, sequence, id'

    name = fields.Char(string='Tên template', required=True,
                        help='Vd: Bảng báo giá nhà mái ngói móng đơn 2025')
    category_id = fields.Many2one(
        'vd.quote.template.category', string='Nhóm template',
        ondelete='set null',
        help='Nhóm template (vd: Mái Nhật / Mái Thái / Miền Bắc / Miền Nam) '
             'để dễ tìm + lọc trong dropdown chọn của NV.',
    )
    description = fields.Text(string='Mô tả',
                               help='Áp dụng cho loại nhà nào, vùng nào, mùa nào...')
    file_attachment = fields.Binary(string='File template', required=True,
                                     attachment=True, copy=False)
    file_name = fields.Char(string='Tên file')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Ghi chú nội bộ')

    # Override display_name của Odoo: thêm prefix [Nhóm] để NV dễ nhận diện
    # trong dropdown chọn template (vd.quote.template_id Many2one).
    @api.depends('name', 'category_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.category_id:
                rec.display_name = f'[{rec.category_id.name}] {rec.name or ""}'
            else:
                rec.display_name = rec.name or ''

    # Cấu hình PDF: trang nào là "BẢNG BÁO GIÁ CHI TIẾT" cần thay data?
    # Mặc định = 3 (giống file mẫu Lệ Chi của VINADUY).
    # Khi merge, hệ thống giữ nguyên các trang khác, chỉ thay 1 trang này.
    quote_page_index = fields.Integer(
        string='Trang báo giá (1-based)', default=3,
        help='Số thứ tự trang BẢNG BÁO GIÁ CHI TIẾT trong file PDF mẫu '
             '(đếm từ 1). Mặc định = 3. Hệ thống sẽ giữ nguyên 100% các '
             'trang khác, chỉ thay trang này bằng data của KH.',
    )

    def action_create_placeholder_version(self):
        """🔧 Convert file mẫu Lệ Chi → version có {{placeholder}}.
        - Tìm các giá trị cụ thể (Chị Lệ Chi, 16/04/2025, Cần Thơ, 120 M2...)
        - Thay bằng {{KH_NAME}}, {{TODAY}}, {{ADDRESS}}... in màu tím
        - Output: file PDF mới để upload lại làm template chuẩn (work 100%
          với mọi KH, không phụ thuộc text matching nữa).
        """
        self.ensure_one()
        if not self.file_attachment:
            raise UserError(_('Chưa có file template để xử lý.'))
        fname = (self.file_name or '').lower()
        if not fname.endswith('.pdf'):
            raise UserError(_('Chỉ hỗ trợ file PDF.'))

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise UserError(_('Thiếu thư viện PyMuPDF. Yêu cầu admin: pip install PyMuPDF'))

        import base64, io, unicodedata
        pdf_bytes = base64.b64decode(self.file_attachment)
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        page_idx = (self.quote_page_index or 3) - 1
        if page_idx < 0 or page_idx >= len(doc):
            doc.close()
            raise UserError(_('Trang báo giá (%d) ngoài phạm vi (file có %d trang).')
                              % (self.quote_page_index, len(doc)))

        # Map các giá trị cụ thể của Lệ Chi → placeholder
        replacements = [
            ('Chị Lệ Chi', '{{KH_NAME}}'),
            ('16/04/2025', '{{TODAY}}'),
            ('Cần Thơ', '{{ADDRESS}}'),
            ('1.383.480.000 VNĐ', '{{TOTAL_PRICE}} VNĐ'),
            ('226.800.000 VNĐ', '{{FOUND_COST}} VNĐ'),
            ('756.000.000 VNĐ', '{{FLOOR_COST}} VNĐ'),
            ('400.680.000 VNĐ', '{{ROOF_COST}} VNĐ'),
            ('120 M2 x 30%', '{{AREA}} M2 x {{FOUND_PCT}}%'),
            ('120 M2 x 53%', '{{AREA}} M2 x {{ROOF_PCT}}%'),
            ('6.300.000 VNĐ', '{{UNIT_PRICE}} VNĐ'),
            ('MÁI NGÓI', '{{HOUSE_TYPE}}'),
            ('MÓNG ĐƠN', '{{FOUNDATION}}'),
        ]

        FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        page = doc[page_idx]

        def search_robust(text):
            for variant in {text, unicodedata.normalize('NFC', text),
                            unicodedata.normalize('NFD', text)}:
                try:
                    found = page.search_for(variant)
                    if found:
                        return found
                except Exception:
                    continue
            return []

        # Phase 1: collect rect + whiteout
        to_insert = []
        for old_text, placeholder in replacements:
            rects = search_robust(old_text)
            for rect in rects:
                expanded = fitz.Rect(rect.x0 - 1.5, rect.y0 - 1,
                                      rect.x1 + 1.5, rect.y1 + 1)
                to_insert.append((expanded, placeholder))
                page.add_redact_annot(expanded, fill=(1, 1, 1))

        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # Phase 2: insert placeholder (màu tím để dễ nhận diện)
        for rect, placeholder in to_insert:
            fsize = max(7, min(int(rect.height * 0.65), 11))
            try:
                page.insert_textbox(
                    rect, placeholder,
                    fontfile=FONT_FILE, fontname='vd_dejavu',
                    fontsize=fsize, color=(0.55, 0.1, 0.55),  # tím để nổi bật
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            except Exception:
                try:
                    page.insert_text(
                        (rect.x0 + 1, rect.y1 - 2), placeholder,
                        fontfile=FONT_FILE, fontname='vd_dejavu_fb',
                        fontsize=fsize, color=(0.55, 0.1, 0.55),
                    )
                except Exception:
                    pass

        out = io.BytesIO()
        doc.save(out, garbage=4, deflate=True)
        doc.close()
        out.seek(0)
        new_pdf = out.read()

        if not to_insert:
            raise UserError(_(
                'Không tìm thấy giá trị nào để thay (Chị Lệ Chi, 120 M2 x 30%...).\n'
                'File template này có thể không phải file mẫu Lệ Chi gốc, '
                'hoặc text được lưu khác encoding.'
            ))

        # Tạo attachment để download
        att = self.env['ir.attachment'].create({
            'name': f'TEMPLATE_PLACEHOLDER_{self.name or "vinaduy"}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(new_pdf),
            'res_model': 'vd.quote.template',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{att.id}?download=true',
            'target': 'self',
        }
