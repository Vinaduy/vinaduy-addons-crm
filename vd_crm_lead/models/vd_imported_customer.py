# -*- coding: utf-8 -*-
"""DANH SÁCH KHÁCH HÀNG nhập từ Pancake (export Excel).

Import 1 lần toàn bộ danh sách khách → chia ĐỀU cho các NV đang nhận số
(vd_can_receive_pancake). Mỗi NV chỉ THẤY khách của mình (ir.rule); quản lý/
admin thấy tất cả. Mỗi cột có `help` để NV rê chuột biết ý nghĩa.
"""
import re

from odoo import api, fields, models


def _norm_phone(p):
    d = re.sub(r'[^0-9]', '', p or '')
    if d.startswith('84'):
        d = '0' + d[2:]
    return d


class VdImportedCustomer(models.Model):
    _name = 'vd.imported.customer'
    _description = 'Danh sách khách hàng (import Pancake)'
    # Khách HỦY xuống CUỐI; còn lại ưu tiên khách CÓ THÔNG TIN lên đầu.
    _order = 'cancelled, info_score desc, id desc'
    _rec_name = 'name'

    _CANCEL_CATEGORIES = [
        ('no_budget', 'Không đủ ngân sách'),
        ('competitor', 'Đã chọn bên khác'),
        ('cancel_plan', 'Hủy / hoãn kế hoạch xây'),
        ('wrong_number', 'Sai số / không đúng số'),
        ('no_need', 'Không có nhu cầu'),
        ('other', 'Lý do khác'),
    ]

    # Các trường tính "độ đầy đủ thông tin" để xếp khách nhiều thông tin lên trước.
    _INFO_FIELDS = ('status', 'address', 'area', 'house_type', 'floors', 'func',
                    'func_note', 'land_type', 'position', 'budget', 'red_book',
                    'timeline', 'email')

    name = fields.Char(
        string='Tên khách', index=True,
        help='Tên đầy đủ của khách hàng lấy từ Pancake.')
    phone = fields.Char(
        string='Điện thoại', index=True,
        help='Số điện thoại khách. Bấm gọi/kết bạn Zalo theo số này.')
    email = fields.Char(string='Email', help='Địa chỉ email của khách (nếu có).')
    status = fields.Char(
        string='Trạng thái', index=True,
        help='Trạng thái chăm sóc trên Pancake, ví dụ: ĐÃ GỬI BÁO GIÁ, '
             'KHÁCH MỚI, KHÔNG NGHE MÁY...')
    address = fields.Char(
        string='Địa chỉ', help='Tỉnh/thành hoặc địa chỉ khách khai.')
    timeline = fields.Char(
        string='Thời gian', help='Thời gian dự kiến khách muốn xây (nếu có).')
    area = fields.Char(
        string='Diện tích', help='Kích thước/diện tích đất-nhà, ví dụ 5x15.')
    house_type = fields.Char(
        string='Kiểu nhà', help='Kiểu nhà khách muốn: mái bằng/mái Nhật/mái Thái...')
    floors = fields.Char(string='Số tầng', help='Số tầng dự kiến.')
    func = fields.Char(
        string='Công năng', help='Yêu cầu công năng (số phòng ngủ, vệ sinh...).')
    func_note = fields.Text(
        string='Ghi chú công năng', help='Ghi chú thêm về công năng khách yêu cầu.')
    land_type = fields.Char(
        string='Loại đất', help='Loại đất: liền thổ / ao ruộng san lấp...')
    position = fields.Char(
        string='Vị trí', help='Vị trí lô đất, đường xe vào, chỗ để vật tư...')
    budget = fields.Char(
        string='Ngân sách', help='Ngân sách dự kiến khách khai (tầm tài chính).')
    red_book = fields.Char(
        string='Sổ đỏ', help='Tình trạng sổ đỏ / giấy phép xây dựng.')
    age = fields.Char(string='Tuổi', help='Tuổi khách (xem hợp tuổi xây nhà).')
    total_calls = fields.Integer(
        string='Tổng cuộc gọi', help='Tổng số cuộc gọi đã thực hiện với khách này.')
    customer_group = fields.Char(
        string='Nhóm khách', index=True,
        help='Nguồn khách: TIKTOK / FACEBOOK / ZALO...')
    created_raw = fields.Char(
        string='Ngày tạo', help='Ngày khách được tạo trên Pancake.')
    birthday = fields.Char(string='Ngày sinh', help='Ngày sinh khách (nếu có).')
    last_update = fields.Char(
        string='Cập nhật cuối', help='Lần cập nhật gần nhất trên Pancake.')
    tags = fields.Char(
        string='Nhãn', help='Các nhãn Pancake gắn cho khách (Khách chốt, Tiềm '
        'năng, Không nghe máy...).')
    user_id = fields.Many2one(
        'res.users', string='Nhân viên phụ trách', index=True, ondelete='set null',
        help='Nhân viên được chia khách này. NV chỉ thấy khách của mình.')
    active = fields.Boolean(default=True)
    phone_norm = fields.Char(
        string='SĐT chuẩn hoá', compute='_compute_phone_norm', store=True, index=True,
        help='Số điện thoại đã chuẩn hoá (bỏ ký tự lạ, +84→0) để so khớp/gọi.')
    info_score = fields.Integer(
        string='Độ đầy đủ thông tin', compute='_compute_info_score', store=True,
        help='Số trường có dữ liệu — khách nhiều thông tin xếp lên trước.')
    converted_lead_id = fields.Many2one(
        'crm.lead', string='Đã chuyển thành lead', ondelete='set null',
        help='Khi gọi kết nối thành công, khách OMI chuyển thành lead quản lý này.')
    cancelled = fields.Boolean(
        string='Đã hủy', default=False, index=True,
        help='Khách đã bị NV bấm HỦY — xuống cuối bảng SỐ OMI, không xoá.')
    cancel_category = fields.Selection(
        selection='_sel_cancel_categories', string='Nhóm lý do hủy')
    cancel_reason = fields.Text(string='Lý do hủy (chi tiết)')

    @api.model
    def _sel_cancel_categories(self):
        return self._CANCEL_CATEGORIES

    @api.depends('phone')
    def _compute_phone_norm(self):
        for r in self:
            r.phone_norm = _norm_phone(r.phone)

    @api.depends(*_INFO_FIELDS)
    def _compute_info_score(self):
        for r in self:
            r.info_score = sum(1 for f in self._INFO_FIELDS if (r[f] or '').strip())

    @api.model
    def vd_omi_list(self):
        """Danh sách SỐ OMI của NV đang đăng nhập — thẻ (không cột), ưu tiên khách
        NHIỀU THÔNG TIN lên đầu. NV chỉ thấy của mình (ir.rule).

        `calls` = số cuộc NV ĐÃ GỌI số này (từ stringee_call, KHÔNG phải total_calls
        lịch sử import từ Pancake)."""
        recs = self.search([('user_id', '=', self.env.uid), ('active', '=', True)])
        # Đếm cuộc gọi THẬT của NV tới từng số (đuôi 9 chữ số). Lọc user_id trước
        # (index) rồi regexp trên tập nhỏ. KHÔNG chèn ORM giữa execute và fetchall.
        tails = list({(r.phone_norm or '')[-9:] for r in recs if r.phone_norm})
        calls_by_tail = {}
        if tails:
            self.env.cr.execute(
                "SELECT right(regexp_replace(callee_number,'[^0-9]','','g'),9) AS t, "
                "count(*) FROM stringee_call WHERE user_id = %s AND "
                "right(regexp_replace(callee_number,'[^0-9]','','g'),9) IN %s GROUP BY t",
                (self.env.uid, tuple(tails)))
            calls_by_tail = dict(self.env.cr.fetchall())
        return [{
            'id': r.id, 'name': r.name or '(không tên)', 'phone': r.phone or '',
            'status': r.status or '', 'address': r.address or '',
            'area': r.area or '', 'house_type': r.house_type or '',
            'floors': r.floors or '', 'func': r.func or '',
            'land_type': r.land_type or '', 'position': r.position or '',
            'budget': r.budget or '', 'red_book': r.red_book or '',
            'timeline': r.timeline or '', 'customer_group': r.customer_group or '',
            'tags': r.tags or '', 'info_score': r.info_score or 0,
            'calls': calls_by_tail.get((r.phone_norm or '')[-9:], 0),
            'cancelled': r.cancelled,
            'cancel_category': r.cancel_category or '',
        } for r in recs]

    @api.model
    def vd_omi_cancel_categories(self):
        """Danh sách nhóm lý do hủy cho popup chọn khi bấm HỦY."""
        return [{'key': k, 'label': v} for k, v in self._CANCEL_CATEGORIES]

    @api.model
    def vd_omi_take(self, rec_id):
        """LẤY KHÁCH VỀ: chuyển khách OMI thành lead của NV → hiện ở bảng KHÁCH MỚI
        (stage 'Khách mới'). Archive bản ghi OMI. Chỉ NV sở hữu / quản lý."""
        rec = self.sudo().browse(int(rec_id or 0))
        if not rec.exists():
            return {'ok': False}
        u = self.env.user
        if not (rec.user_id.id == u.id or u._is_admin()
                or u.has_group('base.group_system')
                or u.has_group('vd_crm_lead.vd_crm_group_deputy_director')):
            return {'ok': False}
        Lead = self.env['crm.lead'].sudo()
        d = rec.phone_norm or ''
        lead = Lead.search([('phone', 'like', '%' + d[-9:])], limit=1) if len(d) >= 9 else Lead
        owner = rec.user_id.id or u.id
        if lead:
            if not lead.user_id:
                lead.user_id = owner
        else:
            info = []
            for lbl, val in (('Trạng thái', rec.status), ('Nguồn', rec.customer_group),
                             ('Địa chỉ', rec.address), ('Diện tích', rec.area),
                             ('Kiểu nhà', rec.house_type), ('Số tầng', rec.floors),
                             ('Ngân sách', rec.budget), ('Loại đất', rec.land_type),
                             ('Công năng', rec.func), ('Nhãn', rec.tags)):
                if val:
                    info.append('%s: %s' % (lbl, val))
            vals = {
                'name': rec.name or rec.phone or 'Khách OMI',
                'contact_name': rec.name or '', 'phone': rec.phone,
                'user_id': owner, 'type': 'lead',
                'description': '📥 Lấy khách về từ SỐ OMI.\n' + '\n'.join(info),
            }
            stage = self.env.ref('vd_crm_lead.stage_new', raise_if_not_found=False)
            if stage:
                vals['stage_id'] = stage.id
            lead = Lead.create(vals)
        rec.write({'active': False, 'converted_lead_id': lead.id})
        return {'ok': True, 'lead_id': lead.id}

    @api.model
    def vd_omi_cancel(self, rec_id, category=None, note=None):
        """HỦY KHÁCH OMI: chọn lý do → đánh dấu cancelled (xuống CUỐI bảng), KHÔNG
        xoá. Chỉ NV sở hữu / quản lý mới hủy được."""
        rec = self.sudo().browse(int(rec_id or 0))
        if not rec.exists():
            return False
        u = self.env.user
        allowed = (rec.user_id.id == u.id or u._is_admin()
                   or u.has_group('base.group_system')
                   or u.has_group('vd_crm_lead.vd_crm_group_deputy_director'))
        if not allowed:
            return False
        vals = {'cancelled': True}
        if category:
            vals['cancel_category'] = category
        if note:
            vals['cancel_reason'] = note
        rec.write(vals)
        return True
