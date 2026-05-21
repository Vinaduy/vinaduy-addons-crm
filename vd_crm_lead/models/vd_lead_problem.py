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
