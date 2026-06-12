# -*- coding: utf-8 -*-
"""Hộp thư hội thoại FACEBOOK (kết nối THẲNG Meta Graph API) — GĐ1 nền tảng.

Khác Pancake (vd_pancake_page): module này KHÔNG qua trung gian, mà nối trực
tiếp Meta Graph API:
  - Nhận tin nhắn + bình luận qua WEBHOOK Meta gửi tới
        https://<odoo>/vd_crm/fb/webhook
  - Gửi trả lời qua Graph API (Send API + comment reply).

Cấu trúc:
  vd.fb.app          — cấu hình App Meta (app_id, app_secret, verify_token).
  vd.fb.page         — fanpage đã kết nối (fb_page_id + page_access_token).
  vd.fb.conversation — 1 hội thoại với 1 khách (theo PSID).
  vd.fb.message      — từng tin nhắn trong hội thoại (in/out).
  vd.fb.comment      — bình luận dưới bài/quảng cáo.

⚠️ Cần phía Facebook: App Business + quyền pages_messaging /
   pages_manage_engagement + App Review của Meta. Chưa duyệt chỉ nhắn được
   tài khoản test.
"""
import logging
import re
import secrets
from datetime import datetime

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_GRAPH = 'https://graph.facebook.com'
_VN_PHONE_RE = re.compile(r'(?:\+84|0)\d{9,10}')


# ============================================================
# APP — cấu hình App Meta (1 record là đủ; cho phép nhiều nếu cần)
# ============================================================
class VdFbApp(models.Model):
    _name = 'vd.fb.app'
    _description = 'Facebook App (Meta) Config'
    _order = 'id'

    name = fields.Char(string='Tên App', required=True, default='VINADUY Facebook App')
    app_id = fields.Char(string='App ID', help='Lấy ở developers.facebook.com → App → Settings → Basic.')
    app_secret = fields.Char(string='App Secret')
    verify_token = fields.Char(
        string='Verify Token', readonly=True, copy=False,
        help='Token tự sinh — dán vào Meta khi cấu hình Webhook (Verify Token).',
    )
    graph_version = fields.Char(string='Graph API version', default='v21.0', required=True)
    active = fields.Boolean(default=True)
    webhook_url = fields.Char(string='Webhook URL', compute='_compute_webhook_url')
    page_ids = fields.One2many('vd.fb.page', 'app_id', string='Fanpage')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('verify_token'):
                vals['verify_token'] = secrets.token_urlsafe(20)
        return super().create(vals_list)

    def _compute_webhook_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.webhook_url = ('%s/vd_crm/fb/webhook' % base.rstrip('/')) if base else ''

    def action_rotate_verify_token(self):
        for rec in self:
            rec.verify_token = secrets.token_urlsafe(20)
        return True

    # ---------- WEBHOOK dispatch ----------
    @api.model
    def handle_webhook(self, payload):
        """Xử lý payload Meta gửi tới. Cấu trúc:
        {object: 'page', entry: [{id: <page_id>, messaging: [...], changes: [...]}]}
        """
        if not isinstance(payload, dict):
            return
        Page = self.env['vd.fb.page'].sudo()
        for entry in (payload.get('entry') or []):
            page_fbid = str(entry.get('id') or '')
            page = Page.search([('fb_page_id', '=', page_fbid)], limit=1)
            if not page:
                _logger.info('[FB webhook] page %s chưa kết nối — bỏ qua', page_fbid)
                continue
            page.last_event_at = fields.Datetime.now()
            # 1) Tin nhắn (Messenger)
            for ev in (entry.get('messaging') or []):
                try:
                    page._process_messaging(ev)
                except Exception:
                    _logger.exception('[FB webhook] lỗi xử lý messaging %s', ev)
            # 2) Bình luận / feed
            for ch in (entry.get('changes') or []):
                try:
                    if ch.get('field') == 'feed':
                        page._process_feed_change(ch.get('value') or {})
                except Exception:
                    _logger.exception('[FB webhook] lỗi xử lý feed %s', ch)
        return True


# ============================================================
# PAGE — 1 fanpage đã kết nối
# ============================================================
class VdFbPage(models.Model):
    _name = 'vd.fb.page'
    _description = 'Facebook Page (kết nối thẳng Meta)'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Tên page', required=True)
    fb_page_id = fields.Char(string='Facebook Page ID', required=True, index=True)
    platform = fields.Selection(
        [('facebook', 'Facebook'), ('instagram', 'Instagram')],
        string='Nền tảng', default='facebook', required=True,
    )
    page_access_token = fields.Char(string='Page Access Token', required=True)
    app_id = fields.Many2one('vd.fb.app', string='App', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)
    auto_create_lead = fields.Boolean(
        string='Tự tạo KH khi có SĐT', default=True,
        help='Khi tin nhắn/comment có chứa SĐT → tự tạo crm.lead gắn vào hội thoại.',
    )
    team_id = fields.Many2one('crm.team', string='Team mặc định')
    last_event_at = fields.Datetime(string='Sự kiện lần cuối', readonly=True)
    conversation_count = fields.Integer(compute='_compute_counts')
    comment_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        Conv = self.env['vd.fb.conversation'].sudo()
        Cmt = self.env['vd.fb.comment'].sudo()
        for rec in self:
            rec.conversation_count = Conv.search_count([('page_id', '=', rec.id)])
            rec.comment_count = Cmt.search_count([('page_id', '=', rec.id)])

    @property
    def _gver(self):
        return (self.app_id.graph_version or 'v21.0')

    # ---------- Graph API ----------
    def _graph_post(self, path, payload):
        """POST tới Graph API. path = 'me/messages' hoặc '<id>/comments'."""
        self.ensure_one()
        url = '%s/%s/%s' % (_GRAPH, self._gver, path)
        try:
            resp = requests.post(
                url,
                params={'access_token': self.page_access_token},
                json=payload,
                timeout=20,
            )
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.warning('[FB Graph] POST %s lỗi: %s', path, e)
            return {'error': str(e)}
        if resp.status_code != 200:
            _logger.warning('[FB Graph] POST %s status=%s body=%s', path, resp.status_code, data)
        return data

    def send_message(self, psid, text):
        """Gửi tin nhắn tới khách (PSID) qua Send API."""
        self.ensure_one()
        return self._graph_post('me/messages', {
            'recipient': {'id': psid},
            'message': {'text': text},
            'messaging_type': 'RESPONSE',
        })

    def reply_comment(self, comment_id, text):
        """Trả lời 1 bình luận."""
        self.ensure_one()
        return self._graph_post('%s/comments' % comment_id, {'message': text})

    # ---------- Webhook handlers ----------
    def _find_or_create_conversation(self, psid, name=None):
        self.ensure_one()
        Conv = self.env['vd.fb.conversation'].sudo()
        conv = Conv.search([('page_id', '=', self.id), ('psid', '=', psid)], limit=1)
        if not conv:
            conv = Conv.create({
                'page_id': self.id,
                'psid': psid,
                'customer_name': name or psid,
            })
        elif name and conv.customer_name in (False, '', psid):
            conv.customer_name = name
        return conv

    def _process_messaging(self, ev):
        """1 messaging event: tin nhắn vào/ra, echo, postback."""
        self.ensure_one()
        sender = str((ev.get('sender') or {}).get('id') or '')
        recipient = str((ev.get('recipient') or {}).get('id') or '')
        msg = ev.get('message') or {}
        if not msg:
            return  # delivery/read/postback — bỏ qua ở GĐ1
        mid = msg.get('mid')
        is_echo = bool(msg.get('is_echo'))  # tin do PAGE gửi (kể cả từ Odoo/khác)
        # PSID khách = bên KHÔNG phải page
        psid = recipient if is_echo else sender
        if not psid or psid == self.fb_page_id:
            psid = sender if sender != self.fb_page_id else recipient
        Msg = self.env['vd.fb.message'].sudo()
        if mid and Msg.search_count([('mid', '=', mid)]):
            return  # dedup
        conv = self._find_or_create_conversation(psid)
        text = msg.get('text') or ''
        atts = msg.get('attachments') or []
        att_url = (atts[0].get('payload') or {}).get('url') if atts else False
        att_type = atts[0].get('type') if atts else False
        ts = ev.get('timestamp')
        sent_at = datetime.utcfromtimestamp(int(ts) / 1000) if ts else fields.Datetime.now()
        Msg.create({
            'conversation_id': conv.id,
            'direction': 'out' if is_echo else 'in',
            'body': text,
            'mid': mid,
            'attachment_type': att_type,
            'attachment_url': att_url,
            'sent_at': sent_at,
        })
        conv.write({
            'last_message_at': sent_at,
            'snippet': (text or ('[%s]' % att_type if att_type else ''))[:200],
        })
        if not is_echo:
            conv.write({
                'last_inbound_at': sent_at,
                'unread': conv.unread + 1,
                'state': 'open',
            })
            self._maybe_link_lead(conv, text)

    def _process_feed_change(self, value):
        """Feed change: chỉ lấy item='comment', verb='add'."""
        self.ensure_one()
        if value.get('item') != 'comment':
            return
        if value.get('verb') not in ('add', 'edited', None):
            return
        comment_id = str(value.get('comment_id') or '')
        if not comment_id:
            return
        Cmt = self.env['vd.fb.comment'].sudo()
        existing = Cmt.search([('comment_id', '=', comment_id)], limit=1)
        frm = value.get('from') or {}
        # Bỏ qua comment do chính page tạo (tránh tự nhân đôi)
        if str(frm.get('id') or '') == self.fb_page_id:
            return
        ts = value.get('created_time')
        ctime = datetime.utcfromtimestamp(int(ts)) if ts else fields.Datetime.now()
        body = value.get('message') or ''
        vals = {
            'page_id': self.id,
            'post_id': str(value.get('post_id') or ''),
            'comment_id': comment_id,
            'parent_comment_id': str(value.get('parent_id') or ''),
            'from_id': str(frm.get('id') or ''),
            'from_name': frm.get('name') or '',
            'body': body,
            'created_time': ctime,
        }
        if existing:
            existing.write({'body': body})
        else:
            cmt = Cmt.create(vals)
            self._maybe_link_lead(cmt, body)

    def _maybe_link_lead(self, record, text):
        """Nếu text chứa SĐT VN và record chưa gắn lead → (tuỳ chọn) tạo lead."""
        self.ensure_one()
        if record.lead_id or not self.auto_create_lead:
            return
        m = _VN_PHONE_RE.search(text or '')
        if not m:
            return
        phone = m.group(0)
        Lead = self.env['crm.lead'].sudo()
        lead = Lead.search([('phone', '=', phone)], limit=1)
        if not lead:
            name = getattr(record, 'customer_name', False) or getattr(record, 'from_name', '') or phone
            vals = {
                'name': '(Fanpage) %s' % name,
                'partner_name': name if name != phone else '',
                'phone': phone,
                'type': 'lead',
                'description': '📨 Tạo từ hội thoại Facebook (%s)' % self.name,
            }
            if self.team_id:
                vals['team_id'] = self.team_id.id
            lead = Lead.create(vals)
        record.lead_id = lead.id

    def action_view_conversations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hội thoại — %s' % self.name,
            'res_model': 'vd.fb.conversation',
            'view_mode': 'list,form',
            'domain': [('page_id', '=', self.id)],
        }


# ============================================================
# CONVERSATION
# ============================================================
class VdFbConversation(models.Model):
    _name = 'vd.fb.conversation'
    _description = 'Hội thoại Facebook'
    _order = 'last_message_at desc, id desc'
    _rec_name = 'customer_name'

    page_id = fields.Many2one('vd.fb.page', string='Page', required=True, ondelete='cascade', index=True)
    psid = fields.Char(string='PSID khách', required=True, index=True)
    customer_name = fields.Char(string='Tên khách')
    lead_id = fields.Many2one('crm.lead', string='Khách hàng (CRM)', index=True)
    user_id = fields.Many2one('res.users', string='NV phụ trách', index=True)
    message_ids = fields.One2many('vd.fb.message', 'conversation_id', string='Tin nhắn')
    last_message_at = fields.Datetime(string='Tin gần nhất')
    last_inbound_at = fields.Datetime(string='Khách nhắn gần nhất')
    snippet = fields.Char(string='Tin cuối')
    unread = fields.Integer(string='Chưa đọc', default=0)
    state = fields.Selection(
        [('open', 'Đang mở'), ('done', 'Đã xong')],
        default='open', string='Trạng thái',
    )
    platform = fields.Selection(related='page_id.platform', store=True)
    reply_text = fields.Text(string='Soạn trả lời', store=False)

    def action_send_reply(self):
        self.ensure_one()
        text = (self.reply_text or '').strip()
        res = self.post_reply(text)
        self.reply_text = False
        if isinstance(res, dict) and res.get('error'):
            raise UserError(_('Gửi thất bại: %s') % res['error'])
        return True

    def post_reply(self, text):
        """Gửi trả lời cho khách + lưu tin out."""
        self.ensure_one()
        if not text:
            raise UserError(_('Nội dung trả lời trống.'))
        res = self.page_id.send_message(self.psid, text)
        err = res.get('error') if isinstance(res, dict) else None
        self.env['vd.fb.message'].sudo().create({
            'conversation_id': self.id,
            'direction': 'out',
            'body': text,
            'mid': res.get('message_id') if isinstance(res, dict) else False,
            'sent_at': fields.Datetime.now(),
            'send_error': str(err) if err else False,
        })
        self.write({
            'last_message_at': fields.Datetime.now(),
            'snippet': text[:200],
            'unread': 0,
        })
        return res

    def action_mark_done(self):
        self.write({'state': 'done', 'unread': 0})

    def action_mark_read(self):
        self.write({'unread': 0})


# ============================================================
# MESSAGE
# ============================================================
class VdFbMessage(models.Model):
    _name = 'vd.fb.message'
    _description = 'Tin nhắn Facebook'
    _order = 'sent_at, id'

    conversation_id = fields.Many2one('vd.fb.conversation', required=True, ondelete='cascade', index=True)
    direction = fields.Selection([('in', 'Khách gửi'), ('out', 'Page gửi')], required=True)
    body = fields.Text(string='Nội dung')
    mid = fields.Char(string='Message ID', index=True)
    attachment_type = fields.Char(string='Loại đính kèm')
    attachment_url = fields.Char(string='Link đính kèm')
    sent_at = fields.Datetime(string='Thời điểm', default=lambda s: fields.Datetime.now())
    send_error = fields.Char(string='Lỗi gửi')


# ============================================================
# COMMENT
# ============================================================
class VdFbComment(models.Model):
    _name = 'vd.fb.comment'
    _description = 'Bình luận Facebook'
    _order = 'created_time desc, id desc'

    page_id = fields.Many2one('vd.fb.page', string='Page', required=True, ondelete='cascade', index=True)
    post_id = fields.Char(string='Post ID', index=True)
    comment_id = fields.Char(string='Comment ID', required=True, index=True)
    parent_comment_id = fields.Char(string='Comment cha')
    from_id = fields.Char(string='Người bình luận (ID)')
    from_name = fields.Char(string='Người bình luận')
    body = fields.Text(string='Nội dung')
    created_time = fields.Datetime(string='Thời điểm')
    lead_id = fields.Many2one('crm.lead', string='Khách hàng (CRM)')
    replied = fields.Boolean(string='Đã trả lời', default=False)
    state = fields.Selection(
        [('open', 'Mới'), ('done', 'Đã xử lý')],
        default='open', string='Trạng thái',
    )
    reply_text = fields.Text(string='Soạn trả lời', store=False)

    def action_send_reply(self):
        self.ensure_one()
        text = (self.reply_text or '').strip()
        if not text:
            raise UserError(_('Nội dung trả lời trống.'))
        res = self.page_id.reply_comment(self.comment_id, text)
        self.reply_text = False
        self.replied = True
        if isinstance(res, dict) and res.get('error'):
            raise UserError(_('Gửi thất bại: %s') % res['error'])
        return True
