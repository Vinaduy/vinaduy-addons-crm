"""CALL-WATCH — giám sát NV gọi KH MỚI (user spec 2026-06-04, sửa 2026-06-05).

Luật (chốt với user):
  * Cuộc gọi tính 1 NGÀY = có >=1 cuộc gọi ĐI (outbound) trong ngày đó, BẤT KỂ
    thời lượng/nghe máy (user 2026-06-05: cuộc declined 1s vẫn tính — chỉ cần
    NV bấm gọi). KHÔNG dùng field `duration`.
  * KH MỚI = chỉ pill "Khách mới" THẬT trên dashboard (loại THAM KHẢO / CHƯA GỌI
    ĐƯỢC / HUỶ / THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ). Trong 7 NGÀY LÀM VIỆC kể từ ngày
    thêm, NV phải gọi ở >= 3 NGÀY LÀM VIỆC khác nhau.
  * Ngày làm việc = T2..T7, BỎ Chủ nhật + ngày lễ (ir.config_parameter
    'vd_crm_lead.holidays', danh sách YYYY-MM-DD admin tự khai báo).
  * 15h mỗi ngày làm việc (cron): KH "chưa gọi" (chưa đạt 3 ngày & hôm nay chưa
    gọi hợp lệ) -> cảnh báo (banner đỏ + lưu tập cảnh báo). Sang ngày làm việc kế,
    nếu tập cảnh báo hôm trước CHƯA gọi hết -> KHOÁ bảng Khách mới của NV.
  * Tự gỡ khoá khi NV gọi hết tập bị cảnh báo (cron + check live trên dashboard).

Toàn bộ ngưỡng đọc từ ir.config_parameter để admin chỉnh không cần sửa code.
"""

from collections import defaultdict
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


class ResUsersCallWatch(models.Model):
    _inherit = 'res.users'

    # Khoá bảng KHÁCH MỚI do không gọi đủ (song song vd_problem_lock).
    vd_call_lock = fields.Boolean(
        string='Khoá Khách mới (chưa gọi)', default=False, copy=False,
        help='True khi NV không gọi hết tập KH bị cảnh báo hôm trước. '
             'Dashboard chặn mở bảng KHÁCH MỚI. Tự gỡ khi gọi xong.',
    )
    vd_call_lock_reason = fields.Char(string='Lý do khoá gọi', copy=False)
    # Mốc + tập KH bị cảnh báo ở lần cron 15h gần nhất (seed cho ngày kế đánh giá khoá).
    vd_call_warned_date = fields.Date(string='Ngày cảnh báo gọi gần nhất', copy=False)
    vd_call_warned_lead_ids = fields.Char(
        string='KH bị cảnh báo (csv id)', copy=False,
        help='Danh sách id KH "chưa gọi" tại lần cảnh báo 15h gần nhất.',
    )


class CrmLeadCallWatch(models.Model):
    _inherit = 'crm.lead'

    # ------------------------------------------------------------------ config
    @api.model
    def _vd_callwatch_config(self):
        ICP = self.env['ir.config_parameter'].sudo()

        def _i(key, default):
            try:
                return int(ICP.get_param(key, default) or default)
            except (TypeError, ValueError):
                return default

        return {
            'enabled': (ICP.get_param('vd_crm_lead.callwatch_enabled', '1') or '1') != '0',
            'window_workdays': _i('vd_crm_lead.callwatch_window_workdays', 7),
            'required_days': _i('vd_crm_lead.callwatch_required_days', 3),
            # lock_all=True: còn SÓT KH chưa gọi -> khoá ("phải gọi hết").
            # lock_all=False: chỉ khoá khi KHÔNG gọi cái nào trong tập cảnh báo.
            'lock_all': (ICP.get_param('vd_crm_lead.callwatch_lock_all', '1') or '1') != '0',
        }

    # ----------------------------------------------------------- ngày làm việc
    @api.model
    def _vd_callwatch_holidays(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('vd_crm_lead.holidays', '') or ''
        out = set()
        for tok in raw.replace(';', ',').replace('\n', ',').split(','):
            tok = tok.strip()
            if not tok:
                continue
            try:
                out.add(fields.Date.to_date(tok))
            except Exception:
                pass
        return out

    @api.model
    def _vd_is_workday(self, d, holidays=None):
        """T2..T7 (weekday 0..5), bỏ Chủ nhật (6) + ngày lễ."""
        if holidays is None:
            holidays = self._vd_callwatch_holidays()
        return d.weekday() != 6 and d not in holidays

    @api.model
    def _vd_prev_workday(self, d):
        hol = self._vd_callwatch_holidays()
        x = d - timedelta(days=1)
        while not self._vd_is_workday(x, hol):
            x -= timedelta(days=1)
        return x

    @api.model
    def _vd_add_workdays(self, d, n):
        """Trả ngày cách `d` đúng n NGÀY LÀM VIỆC (không tính ngày d)."""
        hol = self._vd_callwatch_holidays()
        cur, cnt = d, 0
        while cnt < n:
            cur += timedelta(days=1)
            if self._vd_is_workday(cur, hol):
                cnt += 1
        return cur

    @api.model
    def _vd_localdate(self, dt):
        """datetime (naive UTC trong Odoo) -> date theo giờ VN."""
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(_VN_TZ).date()

    @api.model
    def _vd_vn_today(self):
        return self._vd_localdate(fields.Datetime.now())

    # --------------------------------------------------- cuộc gọi / ngày gọi
    @api.model
    def _vd_lead_call_workdays(self, lead_ids):
        """{lead_id: set(NGÀY có >=1 cuộc gọi ĐI)}.

        User 2026-06-05: ĐẾM MỌI cuộc gọi đi (bỏ ngưỡng >5s cũ). Cuộc declined
        1 giây vẫn tính là "đã gọi trong ngày" — chỉ cần NV bấm gọi. Đếm theo
        NGÀY (giờ VN) của start_time; nhiều cuộc cùng ngày = 1 ngày."""
        res = defaultdict(set)
        if not lead_ids:
            return res
        calls = self.env['stringee.call'].sudo().search([
            ('lead_id', 'in', list(lead_ids)),
            ('direction', '=', 'outbound'),
            ('start_time', '!=', False),
        ])
        for c in calls:
            d = self._vd_localdate(c.start_time)
            if d:
                res[c.lead_id.id].add(d)
        return res

    @api.model
    def _vd_callwatch_new_bucket(self, user):
        """Recordset KH MỚI THẬT của NV — KHỚP đúng pill "Khách mới" trên
        dashboard (user 2026-06-05). Loại KH thuộc bảng KHÁC:
          - THAM KHẢO (vd_no_quote_state='pending') + HUỶ (active=False) +
            THI CÔNG GẤP / XỬ LÝ VẤN ĐỀ (locked+complete): đã bị domain
            _dashboard_new_bucket_domain loại sẵn.
          - CHƯA GỌI ĐƯỢC (_dashboard_unreachable_ids): trừ thêm ở đây."""
        leads = self.search(self._dashboard_new_bucket_domain([('user_id', '=', user.id)]))
        if not leads:
            return leads
        # User spec 2026-06-07: KH đã "TƯ VẤN QUA ZALO" VÀ đã có BÁO GIÁ CHI TIẾT
        # (vd_intake_complete) → Zalo là kênh tư vấn hợp lệ → MIỄN yêu cầu gọi.
        # Chưa có báo giá chi tiết thì vẫn phải gọi đủ như bình thường.
        leads = leads.filtered(
            lambda l: not (l.vd_zalo_consulted_date and l.vd_intake_complete))
        if not leads:
            return leads
        notcalled = set(self._dashboard_unreachable_ids(leads))   # read-only
        if notcalled:
            leads = leads.filtered(lambda l: l.id not in notcalled)
        return leads

    @api.model
    def _vd_callwatch_uncalled(self, user, cfg, today=None):
        """Recordset KH MỚI mà NV CHƯA gọi xong: chưa đạt required_days ngày gọi
        VÀ hôm nay chưa có cuộc gọi."""
        today = today or self._vd_vn_today()
        leads = self._vd_callwatch_new_bucket(user)
        if not leads:
            return leads
        daymap = self._vd_lead_call_workdays(leads.ids)
        keep_ids = []
        for ld in leads:
            days = daymap.get(ld.id, set())
            if len(days) >= cfg['required_days']:
                continue          # đã đạt chuẩn -> thôi
            if today in days:
                continue          # hôm nay đã gọi rồi
            keep_ids.append(ld.id)
        return self.browse(keep_ids)

    @api.model
    def _vd_parse_ids(self, csv):
        out = set()
        for t in (csv or '').split(','):
            t = t.strip()
            if t.isdigit():
                out.add(int(t))
        return out

    # --------------------------------------------------------------- cron 15h
    @api.model
    def _vd_cron_eval_call_lock(self):
        """CRON 15h ngày làm việc: cảnh báo + áp/gỡ khoá bảng Khách mới."""
        cfg = self._vd_callwatch_config()
        Users = self.env['res.users'].sudo()
        if not cfg['enabled']:
            locked = Users.search([('vd_call_lock', '=', True)])
            if locked:
                locked.write({'vd_call_lock': False, 'vd_call_lock_reason': False})
            return True
        today = self._vd_vn_today()
        if not self._vd_is_workday(today):
            return True   # ngày nghỉ -> không cảnh báo, không khoá
        prevwd = self._vd_prev_workday(today)
        sales = Users.search([
            ('share', '=', False), ('active', '=', True),
            ('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id),
        ])
        for u in sales:
            uncalled_ids = set(self._vd_callwatch_uncalled(u, cfg, today).ids)
            warned_ids = self._vd_parse_ids(u.vd_call_warned_lead_ids)
            vals = {}
            if u.vd_call_warned_date == prevwd and warned_ids:
                # KH đã cảnh báo hôm trước & VẪN chưa gọi tới hôm nay
                still = warned_ids & uncalled_ids
                if cfg['lock_all']:
                    should_lock = bool(still)               # còn sót -> khoá
                else:
                    should_lock = (still == warned_ids)     # không gọi cái nào -> khoá
                if should_lock and not u.vd_call_lock:
                    vals['vd_call_lock'] = True
                    vals['vd_call_lock_reason'] = (
                        'Còn %d/%d KH bị cảnh báo ngày %s chưa gọi (>5s).'
                        % (len(still), len(warned_ids), prevwd.strftime('%d/%m'))
                    )
                elif not still and u.vd_call_lock:
                    vals.update({'vd_call_lock': False, 'vd_call_lock_reason': False})
            elif u.vd_call_lock and not uncalled_ids:
                # không có mốc hợp lệ nhưng đã gọi sạch -> gỡ khoá
                vals.update({'vd_call_lock': False, 'vd_call_lock_reason': False})
            # tập "chưa gọi" HÔM NAY trở thành tập cảnh báo cho ngày làm việc kế
            vals['vd_call_warned_date'] = today
            vals['vd_call_warned_lead_ids'] = ','.join(str(i) for i in sorted(uncalled_ids))
            u.write(vals)
        return True

    # ----------------------------------------------------- admin mở khoá ngay
    @api.model
    def vd_admin_clear_call_lock(self, user_id):
        """ADMIN/quản lý mở khoá NGAY bảng Khách mới cho 1 NV (user spec
        2026-06-04). Xoá cờ khoá + lý do + tập cảnh báo đang treo để cron 15h
        kế KHÔNG dùng lại tập cũ mà đánh giá từ đầu (ân hạn trọn ngày)."""
        if not self._dashboard_is_manager():
            raise AccessError(_('Chỉ quản lý/admin được mở khoá bảng Khách mới.'))
        u = self.env['res.users'].sudo().browse(int(user_id))
        if u.exists():
            u.write({
                'vd_call_lock': False,
                'vd_call_lock_reason': False,
                'vd_call_warned_date': False,
                'vd_call_warned_lead_ids': False,
            })
        return True

    # ------------------------------------------------------ payload dashboard
    @api.model
    def _vd_callwatch_payload(self, scope_user, cfg=None):
        """Dữ liệu banner "khách chưa gọi" + trạng thái khoá cho 1 NV.
        Kèm AUTO-UNLOCK live: đang khoá mà tập cảnh báo đã gọi xong -> gỡ ngay."""
        cfg = cfg or self._vd_callwatch_config()
        base = {
            'enabled': cfg['enabled'], 'locked': False, 'reason': '',
            'uncalled_count': 0, 'uncalled_leads': [],
            'required_days': cfg['required_days'],
            'window_workdays': cfg['window_workdays'],
        }
        if not scope_user or not cfg['enabled']:
            return base
        today = self._vd_vn_today()
        uncalled = self._vd_callwatch_uncalled(scope_user, cfg, today)
        uncalled_ids = set(uncalled.ids)
        # AUTO-UNLOCK live: KH bị cảnh báo đã gọi hết -> gỡ khoá ngay (không chờ cron).
        if scope_user.vd_call_lock:
            warned = self._vd_parse_ids(scope_user.vd_call_warned_lead_ids)
            if warned and not (warned & uncalled_ids):
                scope_user.sudo().write({'vd_call_lock': False, 'vd_call_lock_reason': False})
        daymap = self._vd_lead_call_workdays(list(uncalled_ids)) if uncalled_ids else {}
        leads_payload = []
        for ld in uncalled[:60]:
            ndays = len(daymap.get(ld.id, set()))
            added = self._vd_localdate(ld.create_date) if ld.create_date else today
            deadline = self._vd_add_workdays(added, cfg['window_workdays'])
            leads_payload.append({
                'id': ld.id,
                'name': ld.name or ld.partner_name or 'KH',
                'phone': ld.phone or ld.mobile or '',
                'days': ndays,
                'required': cfg['required_days'],
                'deadline': deadline.strftime('%d/%m'),
                'overdue': today > deadline,
            })
        # User spec 2026-06-10: khoá CHƯA GỌI ĐỦ chỉ khoá các KH KHÁC trong bảng;
        # các KH bị NHẮC (warned) vẫn mở được để NV gọi → tự gỡ. allowed_ids =
        # tập KH bị cảnh báo hôm trước (đang giữ khoá).
        allowed_ids = (sorted(self._vd_parse_ids(scope_user.vd_call_warned_lead_ids))
                       if scope_user.vd_call_lock else [])
        base.update({
            'locked': bool(scope_user.vd_call_lock),
            'reason': scope_user.vd_call_lock_reason or '',
            'uncalled_count': len(uncalled_ids),
            'uncalled_leads': leads_payload,
            'allowed_ids': allowed_ids,
        })
        return base
