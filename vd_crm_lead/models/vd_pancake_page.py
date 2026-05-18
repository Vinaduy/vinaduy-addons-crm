# -*- coding: utf-8 -*-
"""Pancake page integration — config + webhook secret per Facebook page.

Mỗi page Pancake = 1 record. Webhook trỏ vào URL:
  https://<odoo>/vd_crm/pancake/webhook/<webhook_secret>

Admin tạo record với page_id Pancake + page_access_token, hệ thống auto-sinh
webhook_secret (UUID4). Khi Pancake gửi event 'messaging' tới URL có secret
khớp, controller sẽ tạo crm.lead và auto-assign round-robin cho NV còn
được nhận Pancake (vd_can_receive_pancake = True).
"""
import json
import logging
import re
import secrets
from datetime import datetime, timedelta

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_PANCAKE_API_BASE = 'https://pages.fm/api/public_api/v1'
_VN_PHONE_RE = re.compile(r'(?:\+84|0)\d{9,10}')


class VdPancakePage(models.Model):
    _name = 'vd.pancake.page'
    _description = 'Pancake Page Integration'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Tên page',
        required=True,
        help='Tên hiển thị (vd: "Fanpage VINADUY chính").',
    )
    page_id = fields.Char(
        string='Pancake Page ID',
        required=True,
        index=True,
        help='ID page Facebook trong Pancake (lấy từ Pancake → Settings → Tools).',
    )
    platform = fields.Selection(
        [('facebook', 'Facebook (Fanpage)'),
         ('tiktok', 'TikTok'),
         ('instagram', 'Instagram'),
         ('other', 'Khác')],
        string='Nền tảng',
        default='facebook',
        required=True,
        help='Quy định prefix tên KH: Facebook → (Fanpage), TikTok → (Tiktok), '
             'Instagram → (Instagram), Khác → (Pancake).',
    )

    @api.onchange('page_access_token')
    def _onchange_token_extract_page_id(self):
        """Auto-extract page_id thực từ JWT khi admin paste token.
        Pancake JWT payload có format: {"id": "...", "timestamp": ...}
        — id này là page_id để gọi REST API (có thể khác với slug trong URL).
        """
        if not self.page_access_token:
            return
        import base64
        parts = self.page_access_token.split('.')
        if len(parts) < 2:
            return
        try:
            payload_b64 = parts[1] + '==' * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            jwt_id = payload.get('id')
            if jwt_id and self.page_id != jwt_id:
                self.page_id = jwt_id
                return {'warning': {
                    'title': 'Page ID đã tự cập nhật',
                    'message': 'Page ID lấy từ JWT token: %s (khác với giá trị bạn nhập). '
                               'Đây là page_id chính xác cho API Pancake.' % jwt_id,
                }}
        except Exception:
            pass

    @api.onchange('page_id')
    def _onchange_page_id_detect_platform(self):
        """Auto-suggest platform khi user nhập page_id:
        - All-digit → Facebook (FB page_id là số dài)
        - Starts with 'ttm_' hoặc chứa chữ → TikTok
        """
        if self.page_id and not self.platform:
            if self.page_id.isdigit():
                self.platform = 'facebook'
            elif self.page_id.startswith('ttm_') or self.page_id.startswith('tt_'):
                self.platform = 'tiktok'
    page_access_token = fields.Char(
        string='Page Access Token',
        help='Token Pancake cấp cho page (dùng để gọi API REST nếu cần).',
    )
    webhook_secret = fields.Char(
        string='Webhook secret',
        readonly=True,
        copy=False,
        help='Secret được nối vào URL webhook để xác thực request. Tự sinh khi tạo.',
    )
    webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_webhook_url',
        help='Copy URL này dán vào Pancake → Settings → Tools → Webhook URL.',
    )
    active = fields.Boolean(default=True)
    auto_create_lead = fields.Boolean(
        string='Tự tạo KH từ webhook',
        default=True,
        help='Bật: mỗi event "messaging" mới sẽ tạo crm.lead + auto-assign NV. '
             'Tắt: ghi log nhưng KHÔNG tạo lead (dùng khi muốn pause tạm thời).',
    )
    team_id = fields.Many2one(
        'crm.team', string='Team mặc định',
        help='Nếu set, lead từ page này ưu tiên chia cho NV thuộc team này. '
             'Để trống = chia cho tất cả NV eligible.',
    )
    last_event_at = fields.Datetime(
        string='Webhook lần cuối',
        readonly=True,
        help='Thời điểm Pancake gọi webhook gần nhất (mọi event_type).',
    )
    lead_count = fields.Integer(
        string='Tổng KH đã nhận',
        compute='_compute_lead_count',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('webhook_secret'):
                vals['webhook_secret'] = secrets.token_urlsafe(24)
        return super().create(vals_list)

    @api.depends('webhook_secret')
    def _compute_webhook_url(self):
        # Lấy base URL từ system parameter (admin set qua Settings → Technical)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.webhook_secret and base:
                rec.webhook_url = '%s/vd_crm/pancake/webhook/%s' % (base.rstrip('/'), rec.webhook_secret)
            else:
                rec.webhook_url = ''

    def _compute_lead_count(self):
        Lead = self.env['crm.lead'].sudo()
        for rec in self:
            rec.lead_count = Lead.search_count([('vd_pancake_page_id', '=', rec.id)])

    def action_rotate_secret(self):
        """Sinh lại secret mới (URL webhook đổi → cập nhật bên Pancake)."""
        for rec in self:
            rec.webhook_secret = secrets.token_urlsafe(24)
        return True

    @property
    def name_prefix(self):
        """Prefix tên KH theo platform: '(Fanpage)', '(Tiktok)', ..."""
        self.ensure_one()
        return {
            'facebook': '(Fanpage)',
            'tiktok': '(Tiktok)',
            'instagram': '(Instagram)',
            'other': '(Pancake)',
        }.get(self.platform, '(Pancake)')

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'KH từ %s' % self.name,
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('vd_pancake_page_id', '=', self.id)],
        }

    # ============================================================
    # SYNC từ Pancake REST API — kéo conversations N ngày gần nhất
    # Dùng để khôi phục lead bị mất / backup khi webhook fail.
    # API spec: https://developer.pancake.biz/openapi/openapi.yaml
    # ============================================================

    def action_sync_from_pancake(self, days=7, max_conversations=200):
        """Kéo conversations từ Pancake REST API → tạo crm.lead cho KH có SĐT.

        :param days: lấy conversations updated trong N ngày gần nhất (default 7).
        :param max_conversations: trần số conv kéo về 1 lần (bảo vệ rate limit).
        :return: notification dict cho frontend.
        """
        self.ensure_one()
        if not self.page_access_token:
            raise UserError(_('Thiếu Page Access Token — không gọi được API Pancake.'))

        created, skipped_no_phone, skipped_existing, errors = 0, 0, 0, 0
        Lead = self.env['crm.lead'].sudo()
        ResUsers = self.env['res.users'].sudo()

        # Pancake API yêu cầu BẮT BUỘC since (date) + until (date) + page_number.
        # Format: YYYY-MM-DD. Timestamp/ISO format gây 500.
        since_str = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        until_str = datetime.utcnow().strftime('%Y-%m-%d')
        url = '%s/pages/%s/conversations' % (_PANCAKE_API_BASE, self.page_id)

        page_number = 1
        total_seen = 0
        while total_seen < max_conversations:
            params = {
                'access_token': self.page_access_token,
                'since': since_str,
                'until': until_str,
                'page_number': page_number,
                'tags': '-1',  # all tags
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                _logger.exception('Pancake sync %s: API lỗi — %s', self.name, e)
                raise UserError(_('Lỗi gọi Pancake API: %s') % e)

            if not data.get('success'):
                raise UserError(_('Pancake API trả lỗi: %s') % data.get('message', 'unknown'))

            conversations = data.get('conversations') or []
            if not conversations:
                break

            for conv in conversations:
                try:
                    res = self._sync_one_conversation(conv, Lead, ResUsers)
                    if res == 'created':
                        created += 1
                    elif res == 'no_phone':
                        skipped_no_phone += 1
                    elif res == 'existing':
                        skipped_existing += 1
                except Exception as e:
                    errors += 1
                    _logger.exception('Sync conv %s lỗi: %s', conv.get('id'), e)

            total_seen += len(conversations)
            page_number += 1
            if len(conversations) < 60:
                break  # hết trang

        self.last_event_at = fields.Datetime.now()
        msg = _('Đồng bộ Pancake "%s": tạo %s, bỏ qua %s (không SĐT), %s (đã có), %s lỗi') % (
            self.name, created, skipped_no_phone, skipped_existing, errors,
        )
        _logger.info(msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đồng bộ xong'),
                'message': msg,
                'type': 'success' if errors == 0 else 'warning',
                'sticky': False,
            },
        }

    def _sync_one_conversation(self, conv, Lead, ResUsers):
        """Process 1 conversation dict từ Pancake API → tạo lead nếu có SĐT.
        Return: 'created' | 'existing' | 'no_phone'
        """
        self.ensure_one()
        conv_id = conv.get('id')
        if not conv_id:
            return 'no_phone'

        # Dedup trước
        existing = Lead.search([
            ('vd_pancake_page_id', '=', self.id),
            ('vd_pancake_conversation_id', '=', conv_id),
        ], limit=1)
        if existing:
            return 'existing'

        # Customer info từ conversation
        from_info = conv.get('from') or {}
        customer_id = from_info.get('id') or from_info.get('page_customer_id') or ''
        customer_name = (from_info.get('name') or '').strip()

        # Skip nếu sender là chính page
        if customer_id and str(customer_id) == str(self.page_id):
            return 'no_phone'
        if customer_name and customer_name.lower() == (self.name or '').lower():
            return 'no_phone'

        # Lấy SĐT: ưu tiên customer endpoint, fallback grep snippet
        phone = self._fetch_customer_phone(customer_id) if customer_id else ''
        if not phone:
            snippet = conv.get('snippet') or ''
            m = _VN_PHONE_RE.search(snippet)
            if m:
                phone = m.group(0)

        if not phone:
            return 'no_phone'

        # Round-robin pick NV
        assignee = ResUsers._vd_pick_next_assignee(
            source='pancake',
            preferred_team_id=self.team_id.id if self.team_id else None,
        )

        display_name = customer_name or phone
        vals = {
            'name': '%s %s' % (self.name_prefix, display_name),
            'partner_name': customer_name or '',
            'phone': phone,
            'description': '📨 Đồng bộ từ Pancake REST API\nconversation_id: %s\nsnippet: %s' % (
                conv_id, (conv.get('snippet') or '')[:300],
            ),
            'vd_pancake_page_id': self.id,
            'vd_pancake_conversation_id': conv_id,
            'vd_pancake_customer_id': str(customer_id),
            'type': 'lead',
        }
        if assignee:
            vals['user_id'] = assignee.id
            if self.team_id:
                vals['team_id'] = self.team_id.id
        Lead.create(vals)
        return 'created'

    def _fetch_customer_phone(self, customer_id):
        """Gọi Pancake API lấy SĐT của 1 page_customer."""
        self.ensure_one()
        url = '%s/pages/%s/page_customers/%s' % (_PANCAKE_API_BASE, self.page_id, customer_id)
        try:
            resp = requests.get(url, params={'access_token': self.page_access_token}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning('Pancake fetch customer %s lỗi: %s', customer_id, e)
            return ''
        cust = data.get('customer') or data.get('data') or data
        phones = cust.get('phone_numbers') or cust.get('phones') or []
        if phones:
            first = phones[0]
            if isinstance(first, dict):
                return first.get('number') or first.get('phone') or ''
            elif isinstance(first, str):
                return first
        # Một số response để phone ở field 'phone'
        return cust.get('phone') or ''
