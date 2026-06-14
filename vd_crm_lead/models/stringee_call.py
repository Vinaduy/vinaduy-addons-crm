"""Extend stringee.call with a back-link to the (standard) crm.lead, and update
lead activity stats when a call reaches a terminal state.
"""
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StringeeCall(models.Model):
    _inherit = 'stringee.call'

    lead_id = fields.Many2one('crm.lead', string='Khách hàng', ondelete='set null', index=True)
    lead_stage_name = fields.Char(related='lead_id.stage_id.name', string='Stage KH')
    lead_probability = fields.Float(related='lead_id.probability', string='Tỉ lệ chốt')

    # ================= Tra số / định tuyến cuộc gọi đến =================

    @api.model
    def _vd_find_lead_by_phone(self, number, user_id=None):
        """Tìm crm.lead theo số điện thoại (khớp 9 chữ số cuối — bỏ qua 0/84).

        - user_id truyền vào → ưu tiên lead của NV đó trước, rồi nới ra mọi NV.
        - active_test=False: link cả KH đã hủy (archived).
        Trả 1 record crm.lead (rỗng nếu không có).
        """
        digits = re.sub(r'\D', '', number or '')
        Lead = self.env['crm.lead'].with_context(active_test=False)
        if len(digits) < 8:
            return Lead.browse()
        last9 = digits[-9:]
        domain = ['|', ('phone', 'like', last9), ('mobile', 'like', last9)]
        if user_id:
            owned = Lead.search(
                domain + [('user_id', '=', user_id)], limit=1, order='create_date desc')
            if owned:
                return owned
        return Lead.search(domain, limit=1, order='create_date desc')

    @api.model
    def _vd_lookup_number_owner(self, number, current_uid=None):
        """Tra số → KH + NV quản lý (cho keypad gọi tay hiển thị khi nhập số)."""
        lead = self._vd_find_lead_by_phone(number)
        if not lead:
            return {'found': False}
        owner = lead.user_id
        return {
            'found': True,
            'lead_id': lead.id,
            'lead_name': lead.name or (number or ''),
            'owner_id': owner.id or False,
            'owner_name': owner.name or '',
            'is_mine': bool(owner and owner.id == current_uid),
            'owned_by_other': bool(owner and owner.id != current_uid),
        }

    @api.model
    def _vd_ensure_dialed_lead(self, number, user_id):
        """Số mới gọi tay xong → tạo KH mới với tên = chính SĐT (user spec 2026-06-13).
        Đã có KH (bất kỳ NV nào) → KHÔNG tạo trùng."""
        existing = self._vd_find_lead_by_phone(number)
        if existing:
            return {'created': False, 'lead_id': existing.id, 'name': existing.name}
        digits = re.sub(r'\D', '', number or '')
        display = ('0' + digits[-9:]) if len(digits) >= 9 else (number or '')
        new_stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False)
        lead = self.env['crm.lead'].create({
            'name': display,
            'phone': display,
            'user_id': user_id or self.env.user.id,
            'type': 'opportunity',
            'stage_id': new_stage.id if new_stage else False,
            'description': 'Tự tạo từ bàn phím gọi tay.',
        })
        return {'created': True, 'lead_id': lead.id, 'name': lead.name}

    @api.model
    def _vd_resolve_inbound_user(self, caller, callee):
        """Khách gọi vào → ƯU TIÊN ring NV BÁN HÀNG quản lý KH theo số khách `caller`.

        BUG cũ (2026-06-14): chỉ lấy lead MỚI NHẤT → dính lead rác 'KH Gọi Đến'
        do public/admin sở hữu (mỗi inbound tự tạo 1 lead) → ring nhầm admin
        (có stringee_user_id) thay vì NV thật. Sửa: duyệt TẤT CẢ lead trùng số,
        bỏ qua public/admin/NV chưa cấu hình, lấy NV bán hàng gọi-được mới nhất.
        Không có → fallback NV gán DID (super)."""
        digits = re.sub(r'\D', '', caller or '')
        if len(digits) >= 8:
            last9 = digits[-9:]
            sys_g = self.env.ref('base.group_system', raise_if_not_found=False)
            sale_g = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
            leads = self.env['crm.lead'].with_context(active_test=False).search(
                ['|', ('phone', 'like', last9), ('mobile', 'like', last9)],
                order='create_date desc')
            for ld in leads:
                u = ld.user_id
                if (u and u.active and u.stringee_user_id and not u.share
                        and (not sys_g or sys_g not in u.groups_id)
                        and (not sale_g or sale_g in u.groups_id)):
                    return u
        return super()._vd_resolve_inbound_user(caller, callee)

    def action_open_lead(self):
        self.ensure_one()
        if not self.lead_id:
            from odoo.exceptions import UserError
            raise UserError("Cuộc gọi này chưa được link với khách hàng nào.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_wrong_number(self):
        """Đánh dấu cuộc gọi 'không đúng số' → tự động chuyển KH sang stage Hủy
        với reason 'wrong_lead'. KH bị archive theo workflow gán lost stage có sẵn."""
        from odoo.exceptions import UserError
        from odoo import _
        self.ensure_one()
        lead = self.lead_id
        if not lead:
            raise UserError(_("Cuộc gọi chưa link với KH — không thể đánh dấu sai số."))
        if lead.stage_is_lost:
            raise UserError(_("KH đã ở trạng thái Hủy."))
        lost_stage = self.env.ref('vd_crm_lead.stage_lost', raise_if_not_found=False)
        if not lost_stage:
            lost_stage = self.env['crm.stage'].search(
                [('code', '=', 'lost')], limit=1
            ) or self.env['crm.stage'].search([('is_lost', '=', True)], limit=1)
        if not lost_stage:
            raise UserError(_("Chưa cấu hình stage Hủy (lost)."))
        old_stage = lead.stage_id.name or ''
        full_reason = (
            "[❌ Sai số / nhầm lead] "
            "Đánh dấu từ cuộc gọi #%s (%s)" % (self.id, self.callee_number or '—')
        )
        lead.with_context(mail_notrack=True, tracking_disable=True).write({
            'stage_id': lost_stage.id,
            'vd_lost_reason': full_reason,
            'vd_lost_date': fields.Datetime.now(),
            'vd_lost_user_id': self.env.user.id,
            'vd_lost_is_auto': False,
        })
        lead.message_post(
            subtype_xmlid='mail.mt_note',
            body=_(
                "📵 <b>Sai số</b> — chuyển từ <i>%s</i> sang <b>%s</b>.<br/>%s"
            ) % (old_stage, lost_stage.name, full_reason),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã chuyển vào thùng rác'),
                'message': _('KH "%s" đã được đánh dấu sai số.') % (lead.name or ''),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_lead_activity()
        # Push bus notification để FAB widget refresh ngay khi pre-create
        # placeholder cho Web SDK call (state=initiated → vd_in_call=True)
        for rec in records:
            rec._broadcast_state()
        return records

    def write(self, vals):
        old_states = {c.id: c.state for c in self} if 'state' in vals else {}
        result = super().write(vals)
        if {'state', 'duration', 'callee_number'} & vals.keys():
            self._sync_lead_activity()
        if 'state' in vals:
            for c in self:
                if old_states.get(c.id) != c.state:
                    c._broadcast_state()
        return result

    def _broadcast_state(self):
        """Push bus.bus notification so any open lead form auto-refreshes UI."""
        self.ensure_one()
        partner = self.user_id.partner_id if self.user_id else False
        if not partner:
            return
        terminal_msg = self._terminal_message() if self.state in (
            'ended', 'no_answer', 'busy', 'declined', 'cancelled', 'failed',
        ) else ''
        try:
            self.env['bus.bus']._sendone(partner, 'vd_stringee_call_state', {
                'call_id': self.id,
                'lead_id': self.lead_id.id if self.lead_id else False,
                'state': self.state,
                'answer_time': fields.Datetime.to_string(self.answer_time) if self.answer_time else False,
                'terminal_message': terminal_msg,
            })
        except Exception:
            _logger.warning("Bus push failed for call %s", self.id, exc_info=True)

    def _terminal_message(self):
        """Vietnamese end-state message shown as a toast on the lead form."""
        self.ensure_one()
        mapping = {
            'declined': 'Khách hàng từ chối cuộc gọi',
            'busy':     'Máy bận',
            'no_answer': 'Khách hàng không bắt máy',
            'cancelled': 'Cuộc gọi bị huỷ',
            'failed':   'Cuộc gọi thất bại',
            'ended':    'Cuộc gọi đã kết thúc',
        }
        return mapping.get(self.state, '')

    def _sync_lead_activity(self):
        """Push call info back to the matched lead so the dashboard can rank it.

        For inbound calls from numbers we've never seen, auto-create a 'Khách mới'
        lead so the call doesn't fall on the floor. Outbound calls without a match
        are left unlinked — they were placed manually and the agent owns linking.

        Lưu ý: dùng with_context(active_test=False) khi search theo phone — KH
        đã hủy (archived) vẫn cần được link với cuộc gọi để Lịch sử cuộc gọi
        trên form KH (kể cả KH hủy) hiển thị đầy đủ.
        """
        Lead = self.env['crm.lead'].with_context(active_test=False)
        for call in self:
            lead = call.lead_id
            phone = call.callee_number if call.direction == 'outbound' else call.caller_number
            if not lead and phone:
                lead = Lead.search([
                    '|', ('phone', '=', phone), ('mobile', '=', phone),
                    ('user_id', '=', call.user_id.id or self.env.user.id),
                ], limit=1, order='create_date desc')
                if not lead:
                    lead = Lead.search([
                        '|', ('phone', '=', phone), ('mobile', '=', phone),
                    ], limit=1, order='create_date desc')
                if not lead and call.direction == 'inbound':
                    new_stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False)
                    lead = Lead.create({
                        'name': f'KH gọi đến {phone}',
                        'phone': phone,
                        'user_id': call.user_id.id or False,
                        'type': 'opportunity',
                        'stage_id': new_stage.id if new_stage else False,
                        'description': 'Tự động tạo từ cuộc gọi đến.',
                    })
                if lead:
                    call.with_context(skip_sync=True).lead_id = lead.id
            if not lead:
                continue
            vals = {}
            if not lead.last_call_date or (call.start_time and call.start_time > lead.last_call_date):
                vals['last_call_date'] = call.start_time
            if call.state == 'answered' or (call.state == 'ended' and call.duration > 0):
                vals['last_answered_date'] = call.answer_time or call.start_time
                vals['no_answer_streak'] = 0
            elif call.state in ('no_answer', 'busy', 'declined', 'cancelled', 'failed'):
                vals['no_answer_streak'] = lead.no_answer_streak + 1
            # call_count giờ là computed field (lead.py) auto-sync từ call_ids
            # → KHÔNG cần manual increment ở đây (logic cũ dùng _origin.id bị sai).
            if vals:
                lead.write(vals)
