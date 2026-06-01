"""Wizard: nhập 1 hoặc nhiều NV + chọn các nhà mạng → TỰ chia đều số tổng đài.

Quy tắc chia (chốt với user 2026-06-01):
- Round-robin LEAST-LOADED: mỗi NV gán vào số ít NV nhất của từng mạng đã chọn.
- GIỮ ỔN ĐỊNH: NV đã có số của mạng đó → bỏ qua (không xáo trộn), trừ khi bật overwrite.
- Mạng chỉ có 1 số (iTel, Vietnamobile) → least-loaded = số đó → mọi NV dùng chung.
- Tie-break theo id để deterministic; cập nhật tải trong RAM giữa các NV để chia đều
  thật sự trong 1 lần chạy nhiều NV.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# (field boolean, carrier code, label) — chỉ các mạng dùng thực tế.
_CARRIER_FIELDS = [
    ('do_viettel', 'viettel', 'Viettel'),
    ('do_mobi', 'mobi', 'MobiFone'),
    ('do_vina', 'vina', 'Vinaphone'),
    ('do_vietnamobile', 'vietnamobile', 'Vietnamobile'),
    ('do_itelecom', 'itelecom', 'iTel'),
    ('do_gmobile', 'gmobile', 'Gmobile'),
]


class VdStringeeHotlineDistributeWizard(models.TransientModel):
    _name = 'vd.stringee.hotline.distribute.wizard'
    _description = 'Thêm NV & chia đều số tổng đài'

    user_ids = fields.Many2many(
        'res.users', string='Nhân viên',
        domain="[('share','=',False),('active','=',True)]",
        help='Chọn 1 hoặc nhiều NV cần chia số. Hệ thống tự gán mỗi NV vào số '
             'ít người dùng nhất của từng mạng đã chọn.',
    )
    do_viettel = fields.Boolean(string='Viettel', default=True)
    do_mobi = fields.Boolean(string='MobiFone', default=True)
    do_vina = fields.Boolean(string='Vinaphone', default=True)
    do_vietnamobile = fields.Boolean(string='Vietnamobile')
    do_itelecom = fields.Boolean(string='iTel')
    do_gmobile = fields.Boolean(string='Gmobile')
    overwrite = fields.Boolean(
        string='Gán lại nếu NV đã có số',
        help='Tắt (mặc định): NV đã có số của mạng đó thì giữ nguyên — không xáo '
             'trộn. Bật: ép gán lại NV vào số ít tải nhất của mạng đó.',
    )
    preview_text = fields.Char(
        string='Xem trước', compute='_compute_preview_text', readonly=True,
    )

    def _selected_carriers(self):
        """Trả list carrier code đang được tick."""
        self.ensure_one()
        return [code for fld, code, _label in _CARRIER_FIELDS if self[fld]]

    @api.depends('user_ids', 'do_viettel', 'do_mobi', 'do_vina',
                 'do_vietnamobile', 'do_itelecom', 'do_gmobile')
    def _compute_preview_text(self):
        Hotline = self.env['vd.stringee.hotline']
        for wiz in self:
            carriers = wiz._selected_carriers()
            if not wiz.user_ids or not carriers:
                wiz.preview_text = 'Chọn NV và ít nhất 1 nhà mạng.'
                continue
            parts = []
            for fld, code, label in _CARRIER_FIELDS:
                if code not in carriers:
                    continue
                n = Hotline.search_count([('active', '=', True), ('carrier', '=', code)])
                if n == 0:
                    parts.append('%s: CHƯA có số' % label)
                elif n == 1:
                    parts.append('%s: 1 số (dùng chung)' % label)
                else:
                    parts.append('%s: %d số (chia đều)' % (label, n))
            wiz.preview_text = '%d NV → %s' % (len(wiz.user_ids), ' · '.join(parts))

    def action_distribute(self):
        self.ensure_one()
        carriers = self._selected_carriers()
        if not self.user_ids:
            raise UserError(_('Chưa chọn nhân viên nào.'))
        if not carriers:
            raise UserError(_('Chưa chọn nhà mạng nào.'))

        Hotline = self.env['vd.stringee.hotline']
        assigned_pairs = 0   # đếm số lượt (NV × mạng) đã gán mới
        empty_carriers = []  # mạng được chọn nhưng chưa có số nào

        for code in carriers:
            hotlines = Hotline.search([('active', '=', True), ('carrier', '=', code)])
            if not hotlines:
                empty_carriers.append(code)
                continue
            # Tải hiện tại của từng số (cập nhật dần trong RAM khi gán).
            load = {h.id: len(h.assigned_user_ids) for h in hotlines}
            for user in self.user_ids:
                already = user.stringee_hotline_ids.filtered(
                    lambda h: h.active and h.carrier == code
                )
                if already and not self.overwrite:
                    continue  # giữ ổn định
                # Chọn số ít tải nhất; tie-break theo id để deterministic.
                target = min(hotlines, key=lambda h: (load[h.id], h.id))
                if target in already:
                    continue  # đã ở đúng số ít tải nhất rồi
                # overwrite: gỡ các số cùng mạng cũ trước khi gán số mới.
                if already:
                    user.stringee_hotline_ids = [(3, h.id) for h in already]
                    for h in already:
                        load[h.id] = max(0, load.get(h.id, 1) - 1)
                user.stringee_hotline_ids = [(4, target.id)]
                load[target.id] = load.get(target.id, 0) + 1
                assigned_pairs += 1

        msg = _('Đã chia số cho %d NV (%d lượt gán).') % (
            len(self.user_ids), assigned_pairs)
        if empty_carriers:
            labels = [l for _f, c, l in _CARRIER_FIELDS if c in empty_carriers]
            msg += _(' Bỏ qua mạng chưa có số: %s.') % ', '.join(labels)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Chia số xong'),
                'message': msg,
                'type': 'success' if not empty_carriers else 'warning',
                'sticky': bool(empty_carriers),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
