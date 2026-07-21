# -*- coding: utf-8 -*-
"""DANH SÁCH KHÁCH HÀNG nhập từ Pancake (export Excel).

Import 1 lần toàn bộ danh sách khách → chia ĐỀU cho các NV đang nhận số
(vd_can_receive_pancake). Mỗi NV chỉ THẤY khách của mình (ir.rule); quản lý/
admin thấy tất cả. Mỗi cột có `help` để NV rê chuột biết ý nghĩa.
"""
from odoo import fields, models


class VdImportedCustomer(models.Model):
    _name = 'vd.imported.customer'
    _description = 'Danh sách khách hàng (import Pancake)'
    _order = 'id desc'
    _rec_name = 'name'

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
