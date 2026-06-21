# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau thi cho khoa "Mong" (course_a2 - "Mong nha").

Doi tuong: nhan vien sale TRAI NGANH. Khoa giup hieu va phan biet: dat thi cong
(lien tho / yeu), 3 loai mong (don / bang / coc), coc be tong duc san, 2 phuong
phap ep (ep tai / ep neo), cac loai coc it dung. Bam theo file "Mong.pptx".
Anh dat o static/src/img/mong. Bai thi 20 cau co dap an gay PHAN VAN (so lieu
giua cac loai bi trao doi cho nhau de ep NV nho chinh xac).

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _advice, _proof, _mistake

_MO_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.mong_seed_version'
_IMG = '/vd_elearning/static/src/img/mong/'


def _core(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">&#11088; ĐIỀU CẦN NHỚ</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _note(inner):
    return _box('#0ea5e9', '#ecfeff', '&#128161;', 'Hiểu cho dễ', inner)


def _fig(name, cap=''):
    c = ''
    if cap:
        c = ('<figcaption style="font-size:12.5px;color:#64748b;text-align:center;'
             'margin-top:5px;font-weight:600;">%s</figcaption>') % cap
    return (
        '<figure style="margin:0;flex:1 1 230px;min-width:190px;max-width:330px;">'
        '<img src="%s%s" style="width:100%%;height:190px;object-fit:cover;border-radius:12px;'
        'box-shadow:0 4px 14px rgba(32,36,58,.18);"/>%s</figure>'
    ) % (_IMG, name, c)


def _gallery(*figs):
    return ('<div style="display:flex;flex-wrap:wrap;gap:12px;margin:14px 0;">%s</div>'
            % ''.join(figs))


class SlideChannelSeedMong(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_mong(self):
        ch = self.env.ref('vd_elearning.course_a2', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _MO_VERSION:
            return True

        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_mo_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': '<div style="%s">%s</div>' % (_WRAP, merged),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_mo_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _MO_VERSION)
        return True

    # ==================================================================
    def _vd_mo_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Mong la gi', self._p1(h2, h3, lead)),
            ('2. Dat thi cong', self._p2(h2, h3, lead)),
            ('3. Mong don', self._p3(h2, h3, lead)),
            ('4. Mong bang', self._p4(h2, h3, lead)),
            ('5. Mong coc', self._p5(h2, h3, lead)),
            ('6. So sanh 3 loai mong', self._p6(h2, h3, lead)),
            ('7. Coc be tong + ep coc', self._p7(h2, h3, lead)),
            ('8. Coc it dung - Ket luan', self._p8(h2, h3, lead)),
        ]

    def _p1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#1e3a8a,#3730a3);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.85;font-weight:700;">'
            'KIẾN THỨC CƠ BẢN VỀ XÂY DỰNG</div>'
            '<div style="font-size:25px;font-weight:900;margin-top:4px;">MÓNG NHÀ</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Dành cho nhân viên mới '
            '(kể cả trái ngành) &mdash; hiểu và phân biệt các loại móng và cách ép cọc.</div></div>'

            '<h2 style="' + h2 + '">&#127959;&#65039; "Móng" là gì?</h2>'
            '<p style="' + lead + '"><b>Móng</b> là <b>phần nằm dưới cùng của ngôi nhà, chìm '
            'dưới mặt đất</b>, có nhiệm vụ <b>đỡ toàn bộ sức nặng của căn nhà và truyền xuống '
            'nền đất</b>. Móng yếu thì nhà nứt, lún, nghiêng &mdash; nên đây là phần '
            '<b>quan trọng nhất</b> quyết định nhà bền hay không.</p>'

            + _note(
                '<p style="margin-bottom:0;"><b>Vì sao sale phải biết về móng?</b> Vì <b>loại '
                'đất</b> của khách quyết định <b>loại móng</b>, mà loại móng ảnh hưởng trực tiếp '
                'đến <b>chi phí</b>. Hiểu móng, bạn mới giải thích được cho khách vì sao báo giá '
                'cao/thấp và tư vấn đúng.</p>'
            )

            + '<h2 style="' + h2 + '">Khóa này gồm gì?</h2>'
            '<table><thead><tr><th style="width:210px;">Phần</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Đất thi công</b></td><td>Đất liền thổ &middot; Đất yếu</td></tr>'
            '<tr><td><b>3 loại móng</b></td><td>Móng đơn &middot; Móng băng &middot; Móng cọc</td></tr>'
            '<tr><td><b>Ép cọc bê tông</b></td><td>Cọc đúc sẵn &middot; Ép tải &middot; Ép neo</td></tr>'
            '<tr><td><b>Cọc ít dùng</b></td><td>Cọc tre / cừ tràm &middot; Cọc khoan nhồi</td></tr>'
            '</tbody></table>'
            + _core('Móng = phần dưới cùng đỡ cả ngôi nhà. <b>Đất nào &rarr; móng đó &rarr; chi phí đó.</b>')
        )

    def _p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 1 &mdash; ĐẤT THI CÔNG</h2>'
            '<p style="' + lead + '">Trước khi chọn móng phải biết đất của khách là loại nào. '
            'Có <b>2 loại đất</b>:</p>'
            + _gallery(_fig('image24.jpg', 'Đất liền thổ (đất cứng tự nhiên)'),
                       _fig('image16.jpg', 'Đất yếu (ao hồ, san lấp)'))
            + '<table><thead><tr><th style="width:34%;">Tiêu chí</th>'
            '<th style="text-align:center;">ĐẤT LIỀN THỔ</th>'
            '<th style="text-align:center;">ĐẤT YẾU</th></tr></thead><tbody>'
            '<tr><td><b>Bản chất</b></td>'
            '<td style="text-align:center;">Đất <b>cứng tự nhiên</b>, chưa đào bới san lấp</td>'
            '<td style="text-align:center;">Đất <b>ao hồ, san lấp</b>, có bùn, ẩm</td></tr>'
            '<tr><td><b>Ví dụ</b></td>'
            '<td style="text-align:center;">Đất nền cứng lâu năm</td>'
            '<td style="text-align:center;">Đất phân lô khu đô thị, san lấp từ ruộng ao, đất ven sông</td></tr>'
            '<tr><td><b>Móng phù hợp</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">Móng đơn / Móng băng</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">Móng cọc</td></tr>'
            '</tbody></table>'
            + _core('Đất <b>liền thổ</b> (cứng) &rarr; móng đơn/băng. Đất <b>yếu</b> (ao hồ, san lấp) &rarr; <b>phải dùng móng cọc</b>.')
        )

    def _p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MÓNG 1 &mdash; MÓNG ĐƠN (Móng cốc)</h2>'
            + _gallery(_fig('image30.jpg'), _fig('image25.jpg'), _fig('image26.jpg'), _fig('image15.jpg'))
            + '<h3 style="' + h3 + '">Gồm 3 bộ phận</h3>'
            '<table><thead><tr><th style="width:160px;">Bộ phận</th><th>Mô tả</th></tr></thead><tbody>'
            '<tr><td><b>Đế móng</b></td><td>Các đế móng <b>KHÔNG liên kết với nhau</b> (tách rời từng cục).</td></tr>'
            '<tr><td><b>Đoạn cột</b></td><td>Nối <b>đế móng và dầm móng</b> với nhau bằng 1 đoạn cột.</td></tr>'
            '<tr><td><b>Dầm móng</b></td><td><b>Khóa các đế móng</b> lại với nhau.</td></tr>'
            '</tbody></table>'
            '<table><thead><tr><th style="width:160px;">Thông tin</th><th></th></tr></thead><tbody>'
            '<tr><td><b>Áp dụng</b></td><td>Đất <b>cứng, liền thổ</b>.</td></tr>'
            '<tr><td><b>Chi phí</b></td><td><b style="color:#16a34a;">RẺ NHẤT</b> trong 3 loại móng.</td></tr>'
            '<tr><td><b>Sử dụng</b></td><td>Nhà <b>1 tầng</b> (2 tầng nếu tài chính thấp).</td></tr>'
            '</tbody></table>'
            + _core('Móng đơn = <b>3 bộ phận</b> &middot; đế <b>tách rời</b> &middot; đất cứng &middot; <b>rẻ nhất</b> &middot; nhà 1 tầng.')
        )

    def _p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MÓNG 2 &mdash; MÓNG BĂNG</h2>'
            + _gallery(_fig('image20.jpg'), _fig('image17.jpg'), _fig('image18.jpg'), _fig('image23.jpg'))
            + '<h3 style="' + h3 + '">Gồm 2 bộ phận</h3>'
            '<table><thead><tr><th style="width:160px;">Bộ phận</th><th>Mô tả</th></tr></thead><tbody>'
            '<tr><td><b>Đế móng</b></td><td>Đế móng <b>chạy dài, liền mạch</b> (không tách rời như móng đơn).</td></tr>'
            '<tr><td><b>Dầm móng</b></td><td><b>Liền với đế móng</b>.</td></tr>'
            '</tbody></table>'
            '<table><tbody>'
            '<tr><td style="width:160px;"><b>Áp dụng</b></td><td>Đất <b>cứng, liền thổ</b>.</td></tr>'
            '<tr><td><b>Chi phí</b></td><td><b style="color:#d97706;">TRUNG BÌNH</b>.</td></tr>'
            '<tr><td><b>Sử dụng</b></td><td>Nhà <b>2 - 3 tầng</b>.</td></tr>'
            '</tbody></table>'
            + _note(
                '<p style="margin-bottom:0;"><b>Phân biệt nhanh với móng đơn:</b> móng đơn có đế '
                '<b>tách rời từng cục</b> (3 bộ phận), còn móng băng có đế <b>chạy dài liền mạch</b> '
                '(2 bộ phận).</p>'
            )
            + _core('Móng băng = <b>2 bộ phận</b> &middot; đế <b>chạy dài liền mạch</b> &middot; đất cứng &middot; <b>trung bình</b> &middot; nhà 2-3 tầng.')
        )

    def _p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MÓNG 3 &mdash; MÓNG CỌC</h2>'
            + _gallery(_fig('image27.jpg'), _fig('image29.jpg'), _fig('image28.png'))
            + '<p style="' + lead + '">Khi đất yếu (ao hồ, san lấp) thì phải <b>ép cọc xuống '
            'sâu</b> tới lớp đất cứng để giữ nhà. Phía trên cọc là phần móng gồm:</p>'
            '<table><thead><tr><th style="width:160px;">Bộ phận</th><th>Mô tả</th></tr></thead><tbody>'
            '<tr><td><b>Cọc bê tông</b></td><td>Ép sâu xuống đất &mdash; là <b>chi phí phát sinh</b> thêm của móng cọc.</td></tr>'
            '<tr><td><b>Đài móng</b></td><td>Đế móng <b>thu về thành đài móng</b>; các đài móng <b>KHÔNG liền nhau</b>.</td></tr>'
            '<tr><td><b>Dầm móng</b></td><td><b>Liền với đài móng</b>.</td></tr>'
            '</tbody></table>'
            '<table><tbody>'
            '<tr><td style="width:160px;"><b>Áp dụng</b></td><td>Đất <b>yếu, ao hồ san lấp</b>.</td></tr>'
            '<tr><td><b>Chi phí</b></td><td>Phần đài + dầm móng <b>bằng móng băng</b>, nhưng <b>đắt hơn</b> vì phát sinh <b>tiền cọc bê tông</b>.</td></tr>'
            '<tr><td><b>Sử dụng</b></td><td>Nhà <b>2 - 5 tầng</b>.</td></tr>'
            '</tbody></table>'
            + _core('Móng cọc = dùng cho <b>đất yếu</b> &middot; có <b>cọc bê tông</b> ép xuống + đài móng + dầm &middot; <b>đắt hơn</b> (tiền cọc) &middot; nhà 2-5 tầng.')
        )

    def _p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">SO SÁNH NHANH 3 LOẠI MÓNG</h2>'
            '<table><thead><tr><th>Tiêu chí</th>'
            '<th style="text-align:center;">Móng đơn</th>'
            '<th style="text-align:center;">Móng băng</th>'
            '<th style="text-align:center;">Móng cọc</th></tr></thead><tbody>'
            '<tr><td><b>Số bộ phận</b></td>'
            '<td style="text-align:center;">3</td>'
            '<td style="text-align:center;">2</td>'
            '<td style="text-align:center;">Cọc + đài + dầm</td></tr>'
            '<tr><td><b>Đế móng</b></td>'
            '<td style="text-align:center;">Tách rời</td>'
            '<td style="text-align:center;">Chạy dài liền mạch</td>'
            '<td style="text-align:center;">Thu về đài móng (rời)</td></tr>'
            '<tr><td><b>Loại đất</b></td>'
            '<td style="text-align:center;">Cứng, liền thổ</td>'
            '<td style="text-align:center;">Cứng, liền thổ</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">Yếu, ao hồ</td></tr>'
            '<tr><td><b>Chi phí</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">Rẻ nhất</td>'
            '<td style="text-align:center;color:#d97706;font-weight:800;">Trung bình</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">Đắt hơn (có cọc)</td></tr>'
            '<tr><td><b>Số tầng</b></td>'
            '<td style="text-align:center;">1 tầng</td>'
            '<td style="text-align:center;">2 - 3 tầng</td>'
            '<td style="text-align:center;">2 - 5 tầng</td></tr>'
            '</tbody></table>'
            + _advice(
                '<p style="margin-bottom:0;">Nhớ theo trục: <b>đất càng yếu / nhà càng cao tầng '
                '&rarr; móng càng phức tạp &rarr; càng đắt</b>. Móng đơn (1 tầng, rẻ) &rarr; móng '
                'băng (2-3 tầng) &rarr; móng cọc (đất yếu, 2-5 tầng, đắt nhất).</p>'
            )
        )

    def _p7(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">ÉP CỌC BÊ TÔNG ĐÚC SẴN</h2>'
            + _gallery(_fig('image33.jpg'), _fig('image36.jpg'))
            + '<table><tbody>'
            '<tr><td style="width:180px;"><b>Kích thước</b></td><td><b>20x20 cm</b> và <b>25x25 cm</b>.</td></tr>'
            '<tr><td><b>Chiều dài</b></td><td><b>5 - 6 m</b> mỗi đoạn.</td></tr>'
            '<tr><td><b>Đơn giá Miền Bắc</b></td><td>Khoảng <b>200k / 1 m dài</b>.</td></tr>'
            '<tr><td><b>Đơn giá Miền Nam</b></td><td>Khoảng <b>270k / 1 m dài</b>.</td></tr>'
            '</tbody></table>'

            '<h2 style="' + h2 + '">2 PHƯƠNG PHÁP ÉP CỌC: ÉP TẢI vs ÉP NEO</h2>'
            + _gallery(_fig('image34.jpg', 'Ép tải'), _fig('image39.jpg', 'Ép neo'))
            + '<table><thead><tr><th style="width:30%;">Tiêu chí</th>'
            '<th style="text-align:center;">ÉP TẢI</th>'
            '<th style="text-align:center;">ÉP NEO</th></tr></thead><tbody>'
            '<tr><td><b>Cách làm</b></td>'
            '<td style="text-align:center;">Dùng máy có <b>tải trọng</b> đè cọc xuống</td>'
            '<td style="text-align:center;">Dùng <b>mũi khoan dẫn hướng</b> rồi đóng cọc</td></tr>'
            '<tr><td><b>Tải trọng ép được</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">60 - 120 tấn</td>'
            '<td style="text-align:center;font-weight:800;">40 tấn</td></tr>'
            '<tr><td><b>Ngõ hẻm</b></td>'
            '<td style="text-align:center;">Từ <b>2,5 m trở lên</b></td>'
            '<td style="text-align:center;">Dưới <b>1,5 m</b> (hẻm nhỏ vẫn làm được)</td></tr>'
            '<tr><td><b>Nhược điểm</b></td>'
            '<td style="text-align:center;color:#dc2626;">Làm <b>rung đất, nứt nhà bên cạnh</b></td>'
            '<td style="text-align:center;color:#dc2626;">Ép được <b>tải trọng thấp</b></td></tr>'
            '<tr><td><b>Ưu điểm</b></td>'
            '<td style="text-align:center;">Tải trọng lớn, chắc</td>'
            '<td style="text-align:center;"><b>Không ảnh hưởng nhà hàng xóm</b></td></tr>'
            '<tr><td><b>Chi phí 1 ca ép</b></td>'
            '<td style="text-align:center;">Khoảng <b>30 triệu</b></td>'
            '<td style="text-align:center;">Khoảng <b>15 triệu</b></td></tr>'
            '</tbody></table>'
            + _mistake(
                '<p style="margin-bottom:0;">Dễ nhầm số liệu! <b>Ép tải</b>: tải trọng LỚN (60-120 '
                'tấn), hẻm RỘNG (2,5m+), giá CAO (~30tr), nhưng RUNG đất. <b>Ép neo</b>: tải trọng '
                'THẤP (40 tấn), hẻm NHỎ (dưới 1,5m), giá THẤP (~15tr), không ảnh hưởng hàng xóm.</p>'
            )
        )

    def _p8(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">LOẠI CỌC ÍT SỬ DỤNG (tham khảo)</h2>'
            + _gallery(_fig('image42.jpg'), _fig('image37.jpg'), _fig('image40.jpg'), _fig('image44.jpg'))
            + '<table><thead><tr><th style="width:180px;">Loại cọc</th><th>Đặc điểm</th></tr></thead><tbody>'
            '<tr><td><b>Cọc tre</b> (Miền Bắc)<br/><b>Cọc cừ tràm</b> (Miền Nam)</td>'
            '<td>Cọc tự nhiên, <b>dài khoảng 2 m</b>, đơn giá <b>~500k / 1 m&sup2; trọn gói</b>. '
            'Yêu cầu nền đất phải <b>ẩm, nhiều nước</b> &mdash; nếu đất khô lâu cọc sẽ <b>mục</b>.</td></tr>'
            '<tr><td><b>Cọc khoan nhồi</b> (cả nước)</td>'
            '<td>Đơn giá <b>~700 - 800k / 1 m dài trọn gói</b>.</td></tr>'
            '</tbody></table>'
            + _gallery(_fig('image45.jpg', 'Miền Tây sông nước'))
            + _note(
                '<p style="margin-bottom:0;"><b>Miền Tây là miền sông nước</b> &rarr; nền đất rất '
                'yếu nên <b>100% phải dùng ép cọc</b>.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; NHẬN BIẾT NHANH &mdash; KẾT LUẬN</h2>'
            + _core(
                '1) Xem <b>đất</b>: liền thổ (cứng) hay yếu (ao hồ). '
                '2) Đất cứng &rarr; <b>móng đơn</b> (1 tầng, rẻ nhất) hoặc <b>móng băng</b> (2-3 tầng). '
                '3) Đất yếu &rarr; <b>móng cọc</b> (ép cọc, đắt hơn). '
                '4) Ép cọc: hẻm rộng dùng <b>ép tải</b>, hẻm nhỏ dùng <b>ép neo</b>.'
            )
            + _advice(
                '<p><b>Kịch bản tư vấn ngắn:</b> luôn hỏi <b>đất của khách là đất gì</b> '
                '(đất thổ cư lâu năm hay đất san lấp/phân lô) và <b>nhà mấy tầng</b> &mdash; từ đó '
                'biết loại móng và giải thích vì sao chi phí cao/thấp.</p>'
            )
            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Đất yếu thì dùng móng gì? (móng cọc)</li>'
            '<li>Móng đơn mấy bộ phận, móng băng mấy bộ phận? (3 và 2)</li>'
            '<li>Móng nào rẻ nhất? (móng đơn)</li>'
            '<li>Cọc bê tông đúc sẵn kích thước và dài bao nhiêu? (20x20 &amp; 25x25 cm, dài 5-6 m)</li>'
            '<li>Ép tải và ép neo khác nhau ở tải trọng, hẻm, giá thế nào?</li>'
            '</ol>'
        )

    # ==================================================================
    #  20 CAU HOI (dap an gay PHAN VAN - trao so lieu giua cac loai). (dap an, dung?)
    # ==================================================================
    def _vd_mo_questions(self):
        T, F = True, False
        return [
            ('Đất liền thổ là loại đất nào?',
             [('Đất cứng tự nhiên, chưa qua đào bới san lấp, không có bùn nước', T),
              ('Đất ao hồ được san lấp, còn lớp bùn ẩm', F),
              ('Đất phân lô khu đô thị san từ ruộng', F),
              ('Đất ven sông nhiều nước', F)]),

            ('Đâu KHÔNG phải là đất yếu?',
             [('Đất cứng tự nhiên lâu năm chưa san lấp', T),
              ('Đất ao hồ san lấp', F),
              ('Đất phân lô khu đô thị san từ ruộng ao', F),
              ('Đất ven sông', F)]),

            ('Đất yếu (ao hồ, san lấp) thì BẮT BUỘC dùng loại móng nào?',
             [('Móng cọc', T),
              ('Móng đơn', F),
              ('Móng băng', F),
              ('Móng đơn hoặc móng băng đều được', F)]),

            ('Móng ĐƠN có bao nhiêu bộ phận?',
             [('3 bộ phận (đế móng, đoạn cột, dầm móng)', T),
              ('2 bộ phận (đế móng, dầm móng)', F),
              ('4 bộ phận', F),
              ('1 bộ phận duy nhất', F)]),

            ('Móng BĂNG có bao nhiêu bộ phận?',
             [('2 bộ phận (đế móng, dầm móng)', T),
              ('3 bộ phận (đế móng, đoạn cột, dầm móng)', F),
              ('4 bộ phận', F),
              ('1 bộ phận', F)]),

            ('Đặc điểm ĐẾ MÓNG của móng ĐƠN là gì?',
             [('Các đế móng KHÔNG liên kết với nhau (tách rời)', T),
              ('Đế móng chạy dài, liền mạch', F),
              ('Đế móng thu về thành đài móng', F),
              ('Không có đế móng', F)]),

            ('Đặc điểm ĐẾ MÓNG của móng BĂNG là gì?',
             [('Đế móng chạy dài, liền mạch', T),
              ('Các đế móng tách rời từng cục', F),
              ('Đế móng nằm trên cọc bê tông', F),
              ('Không có đế móng, chỉ có cọc', F)]),

            ('Trong 3 loại móng, loại nào chi phí RẺ NHẤT?',
             [('Móng đơn', T),
              ('Móng băng', F),
              ('Móng cọc', F),
              ('Ba loại bằng giá nhau', F)]),

            ('Chi phí của móng BĂNG được xếp ở mức nào?',
             [('Trung bình', T),
              ('Rẻ nhất', F),
              ('Đắt nhất', F),
              ('Miễn phí', F)]),

            ('Móng ĐƠN thường dùng cho nhà mấy tầng?',
             [('Nhà 1 tầng (2 tầng nếu tài chính thấp)', T),
              ('Nhà 2 - 3 tầng', F),
              ('Nhà 2 - 5 tầng', F),
              ('Nhà trên 5 tầng', F)]),

            ('Móng BĂNG thường dùng cho nhà mấy tầng?',
             [('Nhà 2 - 3 tầng', T),
              ('Nhà 1 tầng', F),
              ('Nhà 2 - 5 tầng', F),
              ('Nhà trên 10 tầng', F)]),

            ('Móng CỌC thường dùng cho nhà mấy tầng?',
             [('Nhà 2 - 5 tầng', T),
              ('Nhà 1 tầng', F),
              ('Nhà 2 - 3 tầng', F),
              ('Chỉ nhà cấp 4', F)]),

            ('Vì sao móng CỌC đắt hơn móng băng dù phần đài và dầm tương đương?',
             [('Vì phát sinh thêm tiền cọc bê tông ép xuống đất', T),
              ('Vì dùng nhiều dầm móng hơn', F),
              ('Vì đế móng chạy dài hơn', F),
              ('Vì phải xây thêm 1 tầng', F)]),

            ('Cọc bê tông đúc sẵn có kích thước nào?',
             [('20x20 cm và 25x25 cm', T),
              ('25x25 cm và 30x30 cm', F),
              ('20x20 cm và 30x30 cm', F),
              ('15x15 cm và 20x20 cm', F)]),

            ('Cọc bê tông đúc sẵn có chiều dài khoảng bao nhiêu mỗi đoạn?',
             [('5 - 6 m', T),
              ('2 m', F),
              ('10 - 12 m', F),
              ('3 - 4 m', F)]),

            ('Đơn giá cọc bê tông đúc sẵn theo vùng là bao nhiêu?',
             [('Miền Bắc ~200k/m, Miền Nam ~270k/m', T),
              ('Miền Bắc ~270k/m, Miền Nam ~200k/m', F),
              ('Cả hai miền ~500k/m', F),
              ('Miền Bắc ~200k/m, Miền Nam ~200k/m', F)]),

            ('Phương pháp ÉP TẢI ép được tải trọng bao nhiêu?',
             [('Khoảng 60 - 120 tấn', T),
              ('Khoảng 40 tấn', F),
              ('Khoảng 15 - 30 tấn', F),
              ('Khoảng 200 tấn', F)]),

            ('Phương pháp ÉP NEO phù hợp với điều kiện nào?',
             [('Ngõ hẻm nhỏ dưới 1,5 m, không ảnh hưởng nhà hàng xóm', T),
              ('Ngõ hẻm rộng từ 2,5 m trở lên, làm rung đất', F),
              ('Chỉ dùng cho đất cứng liền thổ', F),
              ('Ép được tải trọng 60 - 120 tấn', F)]),

            ('Nhược điểm của ÉP TẢI là gì?',
             [('Làm rung đất, dễ gây nứt nhà bên cạnh', T),
              ('Ép được tải trọng quá thấp', F),
              ('Không làm được ở hẻm rộng', F),
              ('Giá quá rẻ nên kém chất lượng', F)]),

            ('So sánh chi phí 1 ca ép: ép tải và ép neo?',
             [('Ép tải ~30 triệu, ép neo ~15 triệu', T),
              ('Ép tải ~15 triệu, ép neo ~30 triệu', F),
              ('Cả hai ~30 triệu', F),
              ('Cả hai ~15 triệu', F)]),
        ]
