"""Wizard ĐỀ XUẤT HỦY — NV chọn 1 trong 4 nhóm lý do, mỗi nhóm có form
khai thác chi tiết khác nhau. Submit → KH vào thùng rác (stage=lost).

User spec 2026-05-29 round 7:
4 nhóm: Không đủ ngân sách / Đã chọn bên khác / Hủy kế hoạch xây / Nhầm số.
- Không đủ ngân sách: hiển thị KH budget + phần mềm tính + chênh lệch
- Đã chọn bên khác: bên nào, tham khảo bao lâu, lý do mất chốt, lý do KH chọn
- Hủy kế hoạch xây: tại sao, bao lâu, hủy như nào
- Nhầm số: nhầm như nào
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdLeadLostWizard(models.TransientModel):
    _name = 'vd.lead.lost.wizard'
    _description = 'Wizard đề xuất hủy khách'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    lead_name = fields.Char(related='lead_id.name', readonly=True)

    reason_category = fields.Selection([
        ('no_budget', '💸 Không đủ ngân sách'),
        ('competitor', '🏗️ Đã chọn bên khác'),
        ('cancel_plan', '🚫 Hủy kế hoạch xây'),
        ('wrong_number', '❌ Nhầm số'),
    ], string='Nhóm lý do', required=True, default='no_budget')

    # ===== Block 1: Không đủ ngân sách =====
    # Pull data từ lead → display read-only để NV thấy rõ chênh lệch
    kh_budget_display = fields.Char(
        string='KH dự kiến', compute='_compute_budget_info', store=False,
    )
    quote_price_display = fields.Char(
        string='Phần mềm tính', compute='_compute_budget_info', store=False,
    )
    budget_gap_display = fields.Char(
        string='Chênh lệch', compute='_compute_budget_info', store=False,
    )
    no_budget_note = fields.Text(
        string='Ghi chú thêm',
        help='NV ghi chú thêm: KH có ý định tăng ngân sách không? '
             'Hoãn lại bao lâu để tích thêm tiền? Phương án xây nhỏ hơn?',
    )

    # ===== Block 2: Đã chọn bên khác =====
    competitor_name = fields.Char(string='Tên bên KH chọn')
    competitor_review_duration = fields.Char(
        string='Tham khảo bên đó bao lâu rồi?',
        help='VD: 2 tuần, 1 tháng, chưa lâu lắm...',
    )
    competitor_why_lost = fields.Text(
        string='Tại sao bên mình không chốt được?',
        help='Giá đắt hơn? Tư vấn chậm? Thiếu mẫu nhà? Vướng mắc gì?',
    )
    competitor_why_chose = fields.Text(
        string='Tại sao KH chọn bên đó?',
        help='Bên đó báo giá rẻ hơn? Quen người quen? Có ưu đãi gì?',
    )

    # ===== Block 3: Hủy kế hoạch xây =====
    cancel_plan_why = fields.Text(string='Tại sao hủy?')
    cancel_plan_duration = fields.Char(
        string='Hủy trong bao lâu?',
        help='VD: hủy hẳn, hoãn 6 tháng, hoãn vô thời hạn...',
    )
    cancel_plan_how = fields.Text(
        string='Hủy như nào?',
        help='KH chuyển đầu tư sang việc khác? Gặp khó khăn cá nhân? '
             'Gia đình không đồng ý? Đất chưa làm được sổ?',
    )

    # ===== Block 4: Nhầm số =====
    wrong_number_detail = fields.Text(
        string='Nhầm như nào?',
        help='VD: SĐT của KH khác, hotline doanh nghiệp, KH nói nhầm '
             'họ không có nhu cầu xây nhà...',
    )

    @api.depends('lead_id')
    def _compute_budget_info(self):
        """Render hiển thị ngân sách + giá phần mềm + chênh lệch (VNĐ)."""
        def _fmt(n):
            try:
                return f'{n:,.0f}'.replace(',', '.') + ' đ'
            except Exception:
                return '0 đ'

        for wiz in self:
            lead = wiz.lead_id
            kh_amount = lead.vd_intake_budget_amount or 0
            kh_label = ''
            if lead.vd_intake_budget_range:
                kh_label = dict(
                    lead._fields['vd_intake_budget_range'].selection
                ).get(lead.vd_intake_budget_range, '')
            quote = lead.vd_quote_price or lead.vd_intake_estimate or 0
            gap = (quote - kh_amount) if (quote and kh_amount) else 0

            wiz.kh_budget_display = (
                f'{kh_label} ({_fmt(kh_amount)})' if kh_label else _fmt(kh_amount)
            ) or 'Chưa nhập'
            wiz.quote_price_display = _fmt(quote) if quote else 'Chưa có báo giá'
            wiz.budget_gap_display = (
                f'⚠️ Thiếu {_fmt(gap)}' if gap > 0
                else f'✅ Dư {_fmt(-gap)}' if gap < 0
                else '—'
            )

    def _build_reason_summary(self):
        """Đóng gói toàn bộ data form thành 1 text block để lưu lead.vd_lost_reason."""
        self.ensure_one()
        cat_lbl = dict(self._fields['reason_category'].selection).get(
            self.reason_category, self.reason_category,
        )
        parts = [f'[{cat_lbl}]']

        if self.reason_category == 'no_budget':
            parts.append(f'• KH dự kiến: {self.kh_budget_display}')
            parts.append(f'• Phần mềm tính: {self.quote_price_display}')
            parts.append(f'• Chênh lệch: {self.budget_gap_display}')
            if self.no_budget_note:
                parts.append(f'• Ghi chú: {self.no_budget_note.strip()}')

        elif self.reason_category == 'competitor':
            if self.competitor_name:
                parts.append(f'• Bên khác: {self.competitor_name}')
            if self.competitor_review_duration:
                parts.append(f'• Đã tham khảo: {self.competitor_review_duration}')
            if self.competitor_why_lost:
                parts.append(f'• Tại sao mình mất chốt: {self.competitor_why_lost.strip()}')
            if self.competitor_why_chose:
                parts.append(f'• Tại sao KH chọn bên đó: {self.competitor_why_chose.strip()}')

        elif self.reason_category == 'cancel_plan':
            if self.cancel_plan_why:
                parts.append(f'• Tại sao hủy: {self.cancel_plan_why.strip()}')
            if self.cancel_plan_duration:
                parts.append(f'• Hủy bao lâu: {self.cancel_plan_duration}')
            if self.cancel_plan_how:
                parts.append(f'• Hủy như nào: {self.cancel_plan_how.strip()}')

        elif self.reason_category == 'wrong_number':
            if self.wrong_number_detail:
                parts.append(f'• Nhầm như nào: {self.wrong_number_detail.strip()}')

        return '\n'.join(parts)

    def _validate(self):
        """Đảm bảo NV nhập đủ thông tin theo category đã chọn."""
        self.ensure_one()
        cat = self.reason_category
        if cat == 'competitor':
            if not (self.competitor_name or '').strip():
                raise UserError(_('Vui lòng nhập tên bên KH đã chọn.'))
            if not (self.competitor_why_lost or '').strip() and not (self.competitor_why_chose or '').strip():
                raise UserError(_(
                    'Vui lòng khai thác lý do (tại sao mất chốt / tại sao KH chọn bên đó).'
                ))
        elif cat == 'cancel_plan':
            if not (self.cancel_plan_why or '').strip():
                raise UserError(_('Vui lòng ghi lý do hủy.'))
        elif cat == 'wrong_number':
            if not (self.wrong_number_detail or '').strip():
                raise UserError(_('Vui lòng mô tả nhầm như thế nào.'))
        # no_budget: không bắt buộc note (đã có data ngân sách tự pull)

    def action_confirm_lost(self):
        """Set stage lead = lost + lưu lý do gộp."""
        self.ensure_one()
        self._validate()

        lost_stage = self.env.ref('vd_crm_lead.stage_lost', raise_if_not_found=False)
        if not lost_stage:
            lost_stage = self.env['crm.stage'].search([('code', '=', 'lost')], limit=1)
        if not lost_stage:
            raise UserError(_('Không tìm thấy stage "Khách hủy".'))

        full_reason = self._build_reason_summary()
        old_stage = self.lead_id.stage_id.name or ''

        vals = {
            'stage_id': lost_stage.id,
            'vd_lost_reason': full_reason,
            'vd_lost_date': fields.Datetime.now(),
            'vd_lost_user_id': self.env.user.id,
            'vd_lost_is_auto': False,
            # Phase 2: đề xuất hủy CHỜ admin duyệt — chưa archive.
            'vd_cancel_state': 'proposed',
            'vd_cancel_category': self.reason_category,
        }

        self.lead_id.with_context(mail_notrack=True, tracking_disable=True).write(vals)
        self.lead_id.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "🗑️ <b>ĐỀ XUẤT HỦY</b> — chuyển từ <i>%s</i> sang <b>%s</b>."
                "<br/><pre>%s</pre>"
            ) % (old_stage, lost_stage.name, full_reason),
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'main',
        }
