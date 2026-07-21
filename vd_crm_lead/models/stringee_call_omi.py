# -*- coding: utf-8 -*-
"""SỐ OMI — gọi kết nối THÀNH CÔNG thì số tự chuyển về NV gọi.

Khi 1 cuộc gọi tới số OMI được KH bắt máy thật (answer_time set trong
stringee.call.handle_event), số OMI đó chuyển thành crm.lead do CHÍNH NV gọi
quản lý, và bản ghi OMI được archive (không hiện trong SỐ OMI nữa).
"""
import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)


def _norm(p):
    d = re.sub(r'[^0-9]', '', p or '')
    if d.startswith('84'):
        d = '0' + d[2:]
    return d


class StringeeCallOmi(models.Model):
    _inherit = 'stringee.call'

    def _vd_omi_convert_on_answer(self):
        """Chuyển số OMI (nếu có) tương ứng số bị gọi sang lead của NV gọi.
        Bọc savepoint + nuốt lỗi để KHÔNG chặn xử lý webhook cuộc gọi."""
        for call in self:
            if not (call.user_id and call.callee_number and call.answer_time):
                continue
            d = _norm(call.callee_number)
            if len(d) < 9:
                continue
            try:
                with self.env.cr.savepoint():
                    Omi = self.env['vd.imported.customer'].sudo()
                    omi = Omi.search(
                        [('phone_norm', '=', d), ('active', '=', True)], limit=1)
                    if not omi:
                        continue
                    Lead = self.env['crm.lead'].sudo()
                    # Đã có lead trùng số? -> gán về NV gọi nếu chưa có ai quản lý.
                    lead = Lead.search([('phone', 'like', '%' + d[-9:])], limit=1)
                    if lead:
                        if not lead.user_id:
                            lead.user_id = call.user_id.id
                    else:
                        lead = Lead.create({
                            'name': omi.name or omi.phone or 'Khách OMI',
                            'contact_name': omi.name or '',
                            'phone': omi.phone,
                            'user_id': call.user_id.id,
                            'type': 'lead',
                            'description': '📞 Khách OMI — tự chuyển về khi gọi '
                                           'kết nối thành công.',
                        })
                    omi.write({'active': False, 'converted_lead_id': lead.id})
                    _logger.info('OMI convert: %s -> lead %s (NV %s)',
                                 omi.phone, lead.id, call.user_id.login)
            except Exception:
                _logger.exception('OMI convert on answer lỗi (call %s)', call.name)
