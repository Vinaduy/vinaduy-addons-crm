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
import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timezone

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

    @api.model
    def verify_signature(self, raw_body, header):
        """Xác thực payload Meta qua header X-Hub-Signature-256 = HMAC-SHA256(body,
        app_secret). Trả True nếu hợp lệ HOẶC chưa cấu hình app_secret (GĐ1).
        raw_body: bytes."""
        apps = self.sudo().search([('active', '=', True), ('app_secret', '!=', False)])
        if not apps:
            return True  # chưa set app_secret → chưa enforce (sẽ enforce khi có)
        if not header or not header.startswith('sha256='):
            return False
        provided = header.split('=', 1)[1]
        if isinstance(raw_body, str):
            raw_body = raw_body.encode('utf-8')
        for app in apps:
            expected = hmac.new(app.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, provided):
                return True
        return False

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
    def _appsecret_proof(self):
        """Meta khuyến nghị kèm appsecret_proof = HMAC-SHA256(token, app_secret)
        cho mọi server-side call → chặn token bị dùng từ nơi khác."""
        self.ensure_one()
        secret = (self.app_id.app_secret or '').encode()
        token = (self.page_access_token or '').encode()
        if not secret or not token:
            return None
        return hmac.new(secret, token, hashlib.sha256).hexdigest()

    def _graph_params(self, extra=None):
        p = {'access_token': self.page_access_token}
        proof = self._appsecret_proof()
        if proof:
            p['appsecret_proof'] = proof
        if extra:
            p.update(extra)
        return p

    def _graph_post(self, path, payload=None, params=None):
        """POST tới Graph API. path = 'me/messages' / '<id>/comments' / '<page>/subscribed_apps'."""
        self.ensure_one()
        url = '%s/%s/%s' % (_GRAPH, self._gver, path)
        try:
            resp = requests.post(
                url,
                params=self._graph_params(params),
                json=payload or None,
                timeout=20,
            )
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.warning('[FB Graph] POST %s lỗi: %s', path, e)
            return {'error': str(e)}
        if resp.status_code != 200:
            _logger.warning('[FB Graph] POST %s status=%s body=%s', path, resp.status_code, data)
        return data

    def _graph_get(self, path, fields=None):
        """GET tới Graph API (vd lấy tên KH theo PSID)."""
        self.ensure_one()
        url = '%s/%s/%s' % (_GRAPH, self._gver, path)
        try:
            resp = requests.get(
                url, params=self._graph_params({'fields': fields} if fields else None),
                timeout=20,
            )
            return resp.json() if resp.content else {}
        except Exception as e:
            _logger.warning('[FB Graph] GET %s lỗi: %s', path, e)
            return {'error': str(e)}

    def _fetch_psid_name(self, psid):
        """Lấy tên hiển thị của khách theo PSID (best-effort)."""
        if not psid:
            return None
        data = self._graph_get(psid, fields='name')
        if isinstance(data, dict) and not data.get('error'):
            return data.get('name')
        return None

    def action_subscribe_page(self):
        """Đăng ký fanpage này nhận webhook events từ App (BẮT BUỘC để Meta đẩy
        tin nhắn/bình luận về). Tương đương: POST /<page_id>/subscribed_apps."""
        self.ensure_one()
        res = self._graph_post(
            '%s/subscribed_apps' % self.fb_page_id,
            params={'subscribed_fields': 'messages,messaging_postbacks,messaging_optins,feed'},
        )
        if isinstance(res, dict) and res.get('error'):
            raise UserError(_('Đăng ký webhook thất bại: %s') % res['error'])
        self.last_event_at = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('✅ Đã đăng ký fanpage "%s" nhận tin nhắn + bình luận.') % self.name,
                'type': 'success', 'sticky': False,
            },
        }

    # Quyền BẮT BUỘC để nhận tin nhắn + bình luận + trả lời.
    _REQUIRED_SCOPES = [
        'pages_messaging',          # nhận/gửi tin nhắn
        'pages_read_engagement',    # NHẬN bình luận (event feed)
        'pages_manage_engagement',  # TRẢ LỜI bình luận
        'pages_manage_metadata',    # đăng ký page nhận webhook (subscribed_apps)
        'pages_show_list',          # liệt kê page
    ]

    def action_check_token(self):
        """🔍 Soát Page Access Token: gọi debug_token (xem scope) + subscribed_apps
        (xem page đã subscribe field 'feed' chưa). Hiện kết quả ngay trên màn —
        khỏi phải SSH dò token thủ công."""
        self.ensure_one()
        app = self.app_id
        if not (app.app_id and app.app_secret):
            raise UserError(_('Chưa cấu hình App ID / App Secret ở màn Kết nối Facebook.'))
        if not self.page_access_token:
            raise UserError(_('Page chưa có Page Access Token.'))
        app_token = '%s|%s' % (app.app_id, app.app_secret)
        gver = self._gver

        # 1) Scope của token
        try:
            r = requests.get(
                '%s/%s/debug_token' % (_GRAPH, gver),
                params={'input_token': self.page_access_token, 'access_token': app_token},
                timeout=20,
            )
            data = (r.json() or {}).get('data', {}) if r.content else {}
        except Exception as e:
            raise UserError(_('Không gọi được Graph API: %s') % e)
        if not data or data.get('error'):
            raise UserError(_('Token không đọc được — kiểm tra lại App Secret/Token.\n%s')
                            % (r.text[:300] if r.content else ''))
        scopes = set(data.get('scopes') or [])
        have = [s for s in self._REQUIRED_SCOPES if s in scopes]
        missing = [s for s in self._REQUIRED_SCOPES if s not in scopes]

        # 2) Page đã subscribe field 'feed' chưa
        feed_state = '?'
        try:
            r2 = requests.get(
                '%s/%s/%s/subscribed_apps' % (_GRAPH, gver, self.fb_page_id),
                params={'access_token': self.page_access_token}, timeout=20,
            )
            d2 = r2.json() if r2.content else {}
            if isinstance(d2, dict) and d2.get('error'):
                feed_state = '⚠ không đọc được (%s)' % ((d2['error'].get('message') or '')[:70])
            else:
                fields_sub = []
                for sub in (d2.get('data') or []):
                    fields_sub += sub.get('subscribed_fields') or []
                feed_state = 'CÓ ✅' if 'feed' in fields_sub else 'CHƯA ❌ — bấm "Đăng ký nhận tin nhắn + bình luận"'
        except Exception:
            feed_state = '?'

        token_type = data.get('type')
        parts = ['Token: %s, loại %s.' % (data.get('is_valid'), token_type)]
        if token_type == 'USER':
            parts.append('⚠ ĐANG LÀ USER TOKEN — phải dán PAGE TOKEN (lấy qua /me/accounts).')
        parts.append('Có quyền: %s.' % (', '.join(have) or 'không có'))
        if missing:
            parts.append('THIẾU: %s.' % ', '.join(missing))
            parts.append('→ Lấy lại token đủ 5 quyền (gỡ app khỏi FB rồi cấp lại).')
        else:
            parts.append('Đủ toàn bộ quyền cần thiết.')
        parts.append('Feed (bình luận): %s.' % feed_state)

        ok = (not missing) and token_type == 'PAGE' and feed_state.startswith('CÓ')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Kiểm tra token — %s') % self.name,
                'message': '  •  '.join(parts),
                'type': 'success' if ok else 'warning',
                'sticky': True,
            },
        }

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
        # Lấy tên thật từ Graph nếu chưa biết (đẹp cho hộp thư + video demo)
        if not name:
            name = self._fetch_psid_name(psid)
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
        """Feed change (webhook): chỉ lấy item='comment'. Gộp vào hội thoại."""
        self.ensure_one()
        if value.get('item') != 'comment':
            return
        if value.get('verb') not in ('add', 'edited', None):
            return
        frm = value.get('from') or {}
        ts = value.get('created_time')
        ctime = datetime.utcfromtimestamp(int(ts)) if ts else fields.Datetime.now()
        self._ingest_comment(
            comment_id=value.get('comment_id'),
            post_id=value.get('post_id'),
            parent_id=value.get('parent_id'),
            from_id=frm.get('id'),
            from_name=frm.get('name'),
            body=value.get('message') or '',
            created_at=ctime,
        )

    def _ingest_comment(self, comment_id, post_id=None, parent_id=None,
                        from_id=None, from_name=None, body='', created_at=None):
        """Gộp inbox: nạp 1 bình luận thành hội thoại kind='comment' + 1 message.
        Dedup theo comment_id. Bỏ qua comment của chính page. Trả conv hoặc False."""
        self.ensure_one()
        comment_id = str(comment_id or '')
        if not comment_id:
            return False
        if str(from_id or '') == self.fb_page_id:
            return False  # comment của chính page → bỏ
        Msg = self.env['vd.fb.message'].sudo()
        if Msg.search_count([('comment_id', '=', comment_id)]):
            return False  # đã có
        Conv = self.env['vd.fb.conversation'].sudo()
        psid = str(from_id or '') or ('cmt-%s' % comment_id)
        conv = Conv.search([
            ('page_id', '=', self.id), ('kind', '=', 'comment'), ('psid', '=', psid),
        ], limit=1)
        if not conv:
            conv = Conv.create({
                'page_id': self.id, 'kind': 'comment', 'psid': psid,
                'customer_name': from_name or psid, 'post_id': str(post_id or ''),
            })
        elif from_name and conv.customer_name in (False, '', psid):
            conv.customer_name = from_name
        ts = created_at or fields.Datetime.now()
        Msg.create({
            'conversation_id': conv.id, 'direction': 'in', 'is_comment': True,
            'comment_id': comment_id, 'post_id': str(post_id or ''),
            'body': body or '', 'sent_at': ts,
        })
        conv.write({
            'last_message_at': ts, 'last_inbound_at': ts,
            'snippet': (body or '[bình luận]')[:200],
            'unread': conv.unread + 1, 'state': 'open',
        })
        self._maybe_link_lead(conv, body or '')
        return conv

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
            # Tự CHIA NV round-robin (như luồng Pancake) — dùng chung pool NV đang
            # bật nhận Pancake; nếu không thì lead rớt về Public user, NV không thấy.
            try:
                assignee = self.env['res.users'].sudo()._vd_pick_next_assignee(
                    source='pancake',
                    preferred_team_id=self.team_id.id if self.team_id else None)
                if assignee:
                    vals['user_id'] = assignee.id
                    if self.team_id:
                        vals['team_id'] = self.team_id.id
            except Exception:
                pass  # không có NV eligible / lỗi -> tạo lead không assignee, không chặn
            lead = Lead.create(vals)
        record.lead_id = lead.id

    # ---------- POLLING bình luận (Dev mode không đẩy webhook feed) ----------
    @staticmethod
    def _parse_fb_time(s):
        """'2026-06-12T15:16:11+0000' → naive UTC datetime (chuẩn lưu Odoo)."""
        if not s:
            return fields.Datetime.now()
        try:
            dt = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S%z')
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return fields.Datetime.now()

    def _pull_comments_once(self, limit_posts=25):
        """Quét bình luận mới qua Graph API → import vào vd.fb.comment (dedup).
        Dùng được ở Development mode (webhook feed không bắn). Trả số comment MỚI."""
        self.ensure_one()
        if not self.page_access_token:
            return 0
        url = '%s/%s/%s/feed' % (_GRAPH, self._gver, self.fb_page_id)
        params = self._graph_params({
            'fields': 'id,comments.limit(100){id,message,from,created_time,parent}',
            'limit': limit_posts,
        })
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json() if resp.content else {}
        except Exception as e:
            _logger.warning('[FB] pull comments lỗi: %s', e)
            return 0
        if isinstance(data, dict) and data.get('error'):
            _logger.warning('[FB] pull comments error: %s', data['error'])
            return 0
        new_count = 0
        for post in (data.get('data') or []):
            post_id = str(post.get('id') or '')
            for c in ((post.get('comments') or {}).get('data') or []):
                frm = c.get('from') or {}
                parent = c.get('parent') or {}
                conv = self._ingest_comment(
                    comment_id=c.get('id'),
                    post_id=post_id,
                    parent_id=parent.get('id'),
                    from_id=frm.get('id'),
                    from_name=frm.get('name'),
                    body=c.get('message') or '',
                    created_at=self._parse_fb_time(c.get('created_time')),
                )
                if conv:
                    new_count += 1
        self.last_event_at = fields.Datetime.now()
        return new_count

    def action_pull_comments(self):
        """Nút bấm tay: quét bình luận mới ngay (cho NV / lúc quay video)."""
        n = 0
        for page in self:
            n += page._pull_comments_once()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Đã quét xong — %s bình luận mới.') % n,
                'type': 'success', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @api.model
    def _cron_pull_comments(self):
        """Cron tự quét bình luận mọi page (vì Dev mode không có webhook feed)."""
        for page in self.search([('active', '=', True), ('page_access_token', '!=', False)]):
            try:
                page._pull_comments_once()
            except Exception:
                _logger.exception('[FB] cron pull comments lỗi page %s', page.id)

    def action_view_conversations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hội thoại — %s' % self.name,
            'res_model': 'vd.fb.conversation',
            'view_mode': 'list,form',
            'domain': [('page_id', '=', self.id)],
        }

    def action_create_test_conversation(self):
        """[TEST] Tạo 1 hội thoại giả + tin khách đầu tiên để thử cửa sổ chat
        trước khi quay video Facebook (không gọi Graph API, không gửi gì ra
        ngoài). Chỉ admin dùng."""
        self.ensure_one()
        now = fields.Datetime.now()
        Conv = self.env['vd.fb.conversation'].sudo()
        seq = Conv.search_count([('psid', '=like', 'TEST-%')]) + 1
        conv = Conv.create({
            'page_id': self.id,
            'psid': 'TEST-%03d' % seq,
            'customer_name': 'Khách thử nghiệm %d' % seq,
        })
        self.env['vd.fb.message'].sudo().create({
            'conversation_id': conv.id,
            'direction': 'in',
            'body': 'Chào shop, cho mình hỏi về sản phẩm với ạ?',
            'sent_at': now,
        })
        conv.write({
            'last_message_at': now, 'last_inbound_at': now,
            'snippet': 'Chào shop, cho mình hỏi về sản phẩm với ạ?',
            'unread': 1, 'state': 'open',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hội thoại thử nghiệm',
            'res_model': 'vd.fb.conversation',
            'res_id': conv.id,
            'view_mode': 'form',
            'target': 'current',
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
    # Gộp inbox (2026-06-13): 1 model chứa cả chat lẫn bình luận
    kind = fields.Selection(
        [('message', '💬 Tin nhắn'), ('comment', '📝 Bình luận')],
        string='Loại', default='message', required=True, index=True,
    )
    post_id = fields.Char(string='Bài viết (nếu là bình luận)')
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
        """Gửi trả lời cho khách + lưu tin out. Tự định tuyến theo kind:
        - message → Send API (Messenger)
        - comment → trả lời vào bình luận cuối khách gửi (reply_comment)."""
        self.ensure_one()
        if not text:
            raise UserError(_('Nội dung trả lời trống.'))
        msg_vals = {
            'conversation_id': self.id,
            'direction': 'out',
            'body': text,
            'sent_at': fields.Datetime.now(),
        }
        if self.kind == 'comment':
            last = self.message_ids.filtered(
                lambda m: m.is_comment and m.direction == 'in' and m.comment_id
            ).sorted('sent_at')
            if not last:
                raise UserError(_('Chưa xác định được bình luận để trả lời.'))
            cid = last[-1].comment_id
            res = self.page_id.reply_comment(cid, text)
            msg_vals.update({
                'is_comment': True,
                'comment_id': res.get('id') if isinstance(res, dict) else False,
                'post_id': self.post_id,
            })
        else:
            res = self.page_id.send_message(self.psid, text)
            msg_vals['mid'] = res.get('message_id') if isinstance(res, dict) else False
        err = res.get('error') if isinstance(res, dict) else None
        msg_vals['send_error'] = str(err) if err else False
        self.env['vd.fb.message'].sudo().create(msg_vals)
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

    def action_refresh(self):
        """Nút 'Tải lại' — re-read record để hứng tin nhắn webhook mới gửi tới
        (dùng khi quay video demo, không cần F5 cả trang)."""
        self.ensure_one()
        if self.unread:
            self.unread = 0
        return True

    def action_simulate_inbound(self):
        """[TEST] Giả lập 1 tin khách vừa gửi tới — thử bong bóng tin đến +
        luồng trả lời trước khi quay video. KHÔNG gọi Graph API. Chỉ admin."""
        self.ensure_one()
        now = fields.Datetime.now()
        body = 'Tin thử nghiệm lúc %s — shop trả lời giúp em nhé!' % now.strftime('%H:%M:%S')
        self.env['vd.fb.message'].sudo().create({
            'conversation_id': self.id,
            'direction': 'in',
            'body': body,
            'sent_at': now,
        })
        self.write({
            'last_message_at': now, 'last_inbound_at': now,
            'snippet': body[:200], 'unread': self.unread + 1, 'state': 'open',
        })
        return True


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
    # Gộp bình luận vào hội thoại (2026-06-13): message kiểu bình luận
    is_comment = fields.Boolean(string='Là bình luận', default=False)
    comment_id = fields.Char(string='Comment ID', index=True)
    post_id = fields.Char(string='Post ID')


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
