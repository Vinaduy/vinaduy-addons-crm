"""Wizard hiển thị lịch sử huỷ KH (readonly).

Mở khi NV bấm nút "🚫 ĐÃ HUỶ" trên lead form (chỉ hiện khi stage=lost).
Hiển thị: ai huỷ, khi nào, lý do, manual/auto cron, message log.
"""

from odoo import _, api, fields, models


class VdLeadCancelHistoryWizard(models.TransientModel):
    _name = 'vd.lead.cancel.history.wizard'
    _description = 'Lịch sử huỷ KH (readonly)'

    lead_id = fields.Many2one(
        'crm.lead', required=True, ondelete='cascade', readonly=True,
    )
    lead_name = fields.Char(related='lead_id.name', readonly=True)
    lead_phone = fields.Char(related='lead_id.phone', readonly=True)
    stage_name = fields.Char(
        related='lead_id.stage_id.name', readonly=True,
        string='Stage hiện tại',
    )

    # Người huỷ — ưu tiên vd_lost_user_id (mới); fallback write_uid (data cũ)
    actor_display = fields.Char(
        string='Người huỷ', compute='_compute_actor', store=False,
    )
    actor_user_id = fields.Many2one(
        'res.users', string='User huỷ', compute='_compute_actor', store=False,
    )
    is_auto_label = fields.Char(
        string='Loại huỷ', compute='_compute_actor', store=False,
    )
    lost_date = fields.Datetime(
        related='lead_id.vd_lost_date', readonly=True, string='Thời điểm huỷ',
    )
    lost_reason = fields.Text(
        related='lead_id.vd_lost_reason', readonly=True, string='Lý do',
    )

    # Lịch sử mail.message liên quan (audit trail)
    history_html = fields.Html(
        string='Lịch sử thao tác', compute='_compute_history_html',
        sanitize=False, readonly=True,
    )

    @api.depends('lead_id')
    def _compute_actor(self):
        for w in self:
            lead = w.lead_id
            if not lead:
                w.actor_display = ''
                w.actor_user_id = False
                w.is_auto_label = ''
                continue
            if lead.vd_lost_is_auto:
                w.actor_display = '🤖 Hệ thống (cron auto-trash)'
                w.actor_user_id = False
                w.is_auto_label = '🤖 TỰ ĐỘNG'
            elif lead.vd_lost_user_id:
                u = lead.vd_lost_user_id
                w.actor_user_id = u
                w.actor_display = f'{u.name} ({u.login})'
                w.is_auto_label = '👤 NHÂN VIÊN'
            else:
                # Fallback data cũ: dùng write_uid
                u = lead.write_uid
                w.actor_user_id = u
                w.actor_display = (
                    f'{u.name} ({u.login}) — suy luận từ write_uid (data cũ)'
                    if u else 'Không xác định'
                )
                w.is_auto_label = '❓ KHÔNG RÕ (data cũ — backfill từ write_uid)'

    @api.depends('lead_id')
    def _compute_history_html(self):
        """Render bảng mail.message liên quan: stage change + Khách KHÔNG có nhu cầu."""
        for w in self:
            lead = w.lead_id
            if not lead:
                w.history_html = ''
                continue
            messages = self.env['mail.message'].sudo().search(
                [
                    ('model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                ],
                order='date desc',
                limit=30,
            )
            if not messages:
                w.history_html = '<i>Không có message log nào.</i>'
                continue
            rows = []
            for m in messages:
                author = ''
                if m.author_id:
                    u = self.env['res.users'].sudo().search(
                        [('partner_id', '=', m.author_id.id)], limit=1,
                    )
                    author = u.login if u else m.author_id.name or ''
                body = (m.body or '').strip()
                # Strip HTML thô nhẹ — chỉ giữ text + b/i/br
                date_str = fields.Datetime.context_timestamp(
                    w, m.date or fields.Datetime.now()
                ).strftime('%d/%m/%Y %H:%M:%S')
                rows.append(
                    f'<tr>'
                    f'<td style="padding:0.4rem;border:1px solid #ddd;white-space:nowrap;font-size:0.8rem;color:#666;">{date_str}</td>'
                    f'<td style="padding:0.4rem;border:1px solid #ddd;white-space:nowrap;font-size:0.8rem;font-weight:600;color:#0b3d77;">{author or "—"}</td>'
                    f'<td style="padding:0.4rem;border:1px solid #ddd;font-size:0.85rem;">{body}</td>'
                    f'</tr>'
                )
            w.history_html = (
                '<table style="width:100%;border-collapse:collapse;">'
                '<thead><tr style="background:#5c8fb8;color:#fff;">'
                '<th style="padding:0.45rem;border:1px solid #1864ab;text-align:left;font-size:0.82rem;">Thời gian</th>'
                '<th style="padding:0.45rem;border:1px solid #1864ab;text-align:left;font-size:0.82rem;">Tác giả</th>'
                '<th style="padding:0.45rem;border:1px solid #1864ab;text-align:left;font-size:0.82rem;">Nội dung</th>'
                '</tr></thead><tbody>'
                + ''.join(rows)
                + '</tbody></table>'
            )

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
