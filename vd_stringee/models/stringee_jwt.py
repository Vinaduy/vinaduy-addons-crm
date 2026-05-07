"""Stringee JWT generator.

Spec: https://developer.stringee.com/docs/getting-started/authentication
- Header MUST include cty='stringee-api;v=1'
- REST API token claims: {jti, iss, exp, rest:true}
- User token claims: {jti, iss, exp, userId}
"""
import logging
import time
import uuid

import jwt as pyjwt

from odoo import api, models

_logger = logging.getLogger(__name__)

# Token TTL — Stringee allows up to 30 days; we use 1 hour for REST and 24h for user.
_REST_TOKEN_TTL = 3600
_USER_TOKEN_TTL = 24 * 3600


class StringeeJwt(models.AbstractModel):
    _name = 'stringee.jwt'
    _description = 'Stringee JWT helper'

    @api.model
    def _get_credentials(self):
        Param = self.env['ir.config_parameter'].sudo()
        sid = (Param.get_param('vd_stringee.api_key_sid') or '').strip()
        secret = (Param.get_param('vd_stringee.api_key_secret') or '').strip()
        return sid, secret

    @api.model
    def _encode(self, claims):
        sid, secret = self._get_credentials()
        if not sid or not secret:
            _logger.warning("Stringee credentials missing (api_key_sid/api_key_secret)")
            return ''
        headers = {'typ': 'JWT', 'alg': 'HS256', 'cty': 'stringee-api;v=1'}
        token = pyjwt.encode(claims, secret, algorithm='HS256', headers=headers)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token

    @api.model
    def gen_rest_token(self):
        sid, _secret = self._get_credentials()
        if not sid:
            return ''
        now = int(time.time())
        return self._encode({
            'jti': f'{sid}-{uuid.uuid4().hex}',
            'iss': sid,
            'exp': now + _REST_TOKEN_TTL,
            'rest_api': True,
        })

    @api.model
    def gen_user_token(self, user_id):
        sid, _secret = self._get_credentials()
        if not sid or not user_id:
            return ''
        now = int(time.time())
        return self._encode({
            'jti': f'{sid}-{uuid.uuid4().hex}',
            'iss': sid,
            'exp': now + _USER_TOKEN_TTL,
            'userId': str(user_id),
        })
