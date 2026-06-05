"""Wizard "CHƯA BÁO GIÁ — KHÁCH THAM KHẢO" — round 11.

NV gặp KH chưa đủ điều kiện làm báo giá (thiếu ngân sách, chưa có đất,
chưa xong pháp lý, chưa muốn xây ngay) → bấm CHƯA BÁO GIÁ → wizard mở
form khai thác chi tiết theo 4 nhóm + đặt ngày gọi lại → KH tự chuyển
từ KHÁCH MỚI sang THAM KHẢO (👀 icon).
"""
import json
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdLeadNoQuoteWizard(models.TransientModel):
    _name = 'vd.lead.no_quote.wizard'
    _description = 'Wizard chuyển KH sang THAM KHẢO (chưa báo giá)'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)

    category = fields.Selection([
        ('financial', '💰 Tài chính'),
        ('land', '🌍 Đất đai'),
        ('legal', '📜 Pháp lý giấy tờ'),
        ('timing', '⏰ Thời gian xây'),
    ], string='Lý do', required=True, default='financial')

    # ===== 1. Tài chính =====
    fi_have = fields.Char(
        string='KH hiện có sẵn bao nhiêu?',
        help='VD: 500 triệu, 1 tỷ, gần đủ, mới có 30%...',
    )
    fi_need = fields.Char(
        string='Cần thêm bao nhiêu?',
        help='Khoảng cách so với ngân sách dự kiến của VINADUY.',
    )
    fi_when_enough = fields.Char(
        string='Khi nào đủ tiền?',
        help='VD: 6 tháng nữa, sau Tết, đợi bán đất khác...',
    )
    fi_note = fields.Text(string='Ghi chú thêm — Tài chính')

    # ===== 2. Đất đai =====
    la_status = fields.Selection([
        ('finding', '🔍 Đang tìm đất'),
        ('negotiating', '🤝 Đang thương lượng mua'),
        ('partial', '🧩 Có đất nhưng cần gộp / chia'),
        ('disputed', '⚠️ Đất đang tranh chấp / chưa rõ ràng'),
    ], string='Tình trạng đất hiện tại')
    la_where = fields.Char(
        string='Vị trí đất KH đang nhắm?',
        help='Khu vực, tỉnh, lý do chọn nơi đó.',
    )
    la_when_have = fields.Char(
        string='Dự kiến khi nào có đất?',
        help='VD: 2 tháng nữa, sau khi xong sang tên...',
    )
    la_note = fields.Text(string='Ghi chú thêm — Đất đai')

    # ===== 3. Pháp lý giấy tờ =====
    le_missing = fields.Char(
        string='Giấy tờ gì còn thiếu?',
        help='VD: chưa có sổ đỏ, đang sang tên, chưa cấp phép...',
    )
    le_who_handles = fields.Char(
        string='Ai đang lo? Bên nào xử lý?',
        help='KH tự đi làm? Văn phòng nào hỗ trợ?',
    )
    le_when_done = fields.Char(
        string='Khi nào xong?',
        help='Dự kiến KH có đủ giấy tờ vào lúc nào.',
    )
    le_note = fields.Text(string='Ghi chú thêm — Pháp lý')

    # ===== 4. Thời gian xây =====
    ti_when_start = fields.Char(
        string='Khi nào muốn khởi công?',
        help='VD: cuối năm 2026, qua Tết, đợi vợ về nước...',
    )
    ti_why_wait = fields.Text(
        string='Lý do hoãn / chưa muốn xây ngay?',
        help='VD: chưa được tuổi, đợi con đi học xong, lý do gia đình...',
    )
    ti_note = fields.Text(string='Ghi chú thêm — Thời gian')

    # ===== Ngày gọi lại — bắt buộc =====
    callback_date = fields.Date(
        string='Ngày gọi lại',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=14),
        help='Ngày NV phải gọi lại để follow up KH này. Dashboard THAM KHẢO '
             'sẽ hiển thị nút GỌI LẠI khi đến ngày này.',
    )

    # Các trường wizard cần LƯU/KHÔI PHỤC khi mở lại (bỏ lead_id/lead_name).
    @api.model
    def _no_quote_persist_fields(self):
        return [
            'category',
            'fi_have', 'fi_need', 'fi_when_enough', 'fi_note',
            'la_status', 'la_where', 'la_when_have', 'la_note',
            'le_missing', 'le_who_handles', 'le_when_done', 'le_note',
            'ti_when_start', 'ti_why_wait', 'ti_note',
            'callback_date',
        ]

    @api.model
    def default_get(self, fields_list):
        """Mở lại wizard cho KH ĐÃ ở THAM KHẢO → nạp lại dữ liệu đã chọn trước
        đó (user spec 2026-06-05) từ lead.vd_no_quote_data (JSON)."""
        res = super().default_get(fields_list)
        lead_id = self.env.context.get('default_lead_id')
        if not lead_id:
            return res
        lead = self.env['crm.lead'].browse(lead_id)
        loaded = False
        if lead.vd_no_quote_data:
            try:
                data = json.loads(lead.vd_no_quote_data)
                for k, v in data.items():
                    if k in self._fields and v not in (None, ''):
                        res[k] = v
                loaded = True
            except Exception:
                loaded = False
        if not loaded:
            # Fallback (data cũ chưa có JSON): tối thiểu nạp lý do + ngày gọi lại.
            if lead.vd_no_quote_category:
                res['category'] = lead.vd_no_quote_category
            if lead.vd_no_quote_callback_date:
                res['callback_date'] = lead.vd_no_quote_callback_date
        return res

    def _build_reason_summary(self):
        """Đóng gói toàn bộ data thành text block lưu vào lead."""
        self.ensure_one()
        cat_lbl = dict(self._fields['category'].selection).get(self.category, self.category)
        parts = [f'[{cat_lbl}]']

        if self.category == 'financial':
            if self.fi_have:
                parts.append(f'• KH có sẵn: {self.fi_have}')
            if self.fi_need:
                parts.append(f'• Cần thêm: {self.fi_need}')
            if self.fi_when_enough:
                parts.append(f'• Khi nào đủ: {self.fi_when_enough}')
            if self.fi_note:
                parts.append(f'• Ghi chú: {self.fi_note.strip()}')

        elif self.category == 'land':
            if self.la_status:
                la_lbl = dict(self._fields['la_status'].selection).get(self.la_status, '')
                parts.append(f'• Tình trạng: {la_lbl}')
            if self.la_where:
                parts.append(f'• Vị trí: {self.la_where}')
            if self.la_when_have:
                parts.append(f'• Khi nào có: {self.la_when_have}')
            if self.la_note:
                parts.append(f'• Ghi chú: {self.la_note.strip()}')

        elif self.category == 'legal':
            if self.le_missing:
                parts.append(f'• Giấy tờ thiếu: {self.le_missing}')
            if self.le_who_handles:
                parts.append(f'• Ai lo: {self.le_who_handles}')
            if self.le_when_done:
                parts.append(f'• Khi nào xong: {self.le_when_done}')
            if self.le_note:
                parts.append(f'• Ghi chú: {self.le_note.strip()}')

        elif self.category == 'timing':
            if self.ti_when_start:
                parts.append(f'• Khi nào khởi công: {self.ti_when_start}')
            if self.ti_why_wait:
                parts.append(f'• Lý do hoãn: {self.ti_why_wait.strip()}')
            if self.ti_note:
                parts.append(f'• Ghi chú: {self.ti_note.strip()}')

        parts.append(f'📅 Ngày gọi lại: {self.callback_date.strftime("%d/%m/%Y")}')
        return '\n'.join(parts)

    def _validate(self):
        """Đảm bảo NV nhập đủ thông tin theo category + ngày gọi lại hợp lệ."""
        self.ensure_one()
        # Ngày gọi lại KHÔNG quá 1 tháng kể từ hôm nay (user spec 2026-06-05).
        today = fields.Date.today()
        if self.callback_date:
            if self.callback_date < today:
                raise UserError(_('Ngày gọi lại không được ở quá khứ.'))
            max_cb = today + relativedelta(months=1)
            if self.callback_date > max_cb:
                raise UserError(_(
                    'Ngày gọi lại không được quá 1 tháng kể từ hôm nay '
                    '(tối đa %s).') % max_cb.strftime('%d/%m/%Y'))
        cat = self.category
        if cat == 'financial' and not (self.fi_have or self.fi_when_enough or self.fi_note):
            raise UserError(_('Vui lòng khai thác ít nhất 1 trường tài chính.'))
        if cat == 'land' and not (self.la_status or self.la_where or self.la_note):
            raise UserError(_('Vui lòng khai thác ít nhất tình trạng / vị trí đất.'))
        if cat == 'legal' and not (self.le_missing or self.le_note):
            raise UserError(_('Vui lòng ghi giấy tờ KH còn thiếu.'))
        if cat == 'timing' and not (self.ti_when_start or self.ti_why_wait or self.ti_note):
            raise UserError(_('Vui lòng ghi khi nào KH muốn xây / lý do hoãn.'))

    def action_confirm_no_quote(self):
        """Set lead vào state CHƯA BÁO GIÁ + lưu lý do + callback date.
        Lead sẽ tự xuất hiện trong THAM KHẢO bucket (logic ở
        dashboard_leads_reference) thay vì KHÁCH MỚI."""
        self.ensure_one()
        self._validate()

        summary = self._build_reason_summary()
        # Đóng gói toàn bộ field wizard -> JSON để mở lại hiện đúng dữ liệu cũ.
        data = {}
        for f in self._no_quote_persist_fields():
            v = self[f]
            if f == 'callback_date' and v:
                v = fields.Date.to_string(v)
            data[f] = v or ''
        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write({
            'vd_no_quote_state': 'pending',
            'vd_no_quote_category': self.category,
            'vd_no_quote_reason': summary,
            'vd_no_quote_data': json.dumps(data, ensure_ascii=False),
            'vd_no_quote_callback_date': self.callback_date,
            'vd_no_quote_date': fields.Datetime.now(),
            'vd_no_quote_user_id': self.env.user.id,
            # callback_date trên crm.lead là Datetime → combine date+time(9h sáng)
            'callback_date': datetime.combine(self.callback_date, time(9, 0)),
        })
        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "👀 <b>CHƯA BÁO GIÁ — chuyển sang THAM KHẢO</b><br/>"
                "<pre>%s</pre>"
            ) % summary,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'main',
        }
