# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau thi cho khoa "Vat tu NGOAI hop dong" (course_b3).

Doi tuong: nhan vien sale TRAI NGANH. Khoa giup hieu va nho nhung hang muc
KHONG nam trong bao gia tron goi (coc be tong, thang may, noi that, den suoi/
NLMT, tuong rao/san cong, gieng khoan/be ngam, chong set, ban bep/chau rua) va
cach Vinaduy xu ly tung hang muc -> de tu van minh bach, tranh tranh chap.
Bam theo file "Vat tu ngoai hop dong.pptx". Anh o static/src/img/vattu_ngoai.

Idempotent theo VERSION. Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _advice, _proof, _mistake

_VTN_VERSION = 'v3'
_PARAM_KEY = 'vd_elearning.vattu_ngoai_seed_version'
_IMG = '/vd_elearning/static/src/img/vattu_ngoai/'


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
        '<figure style="margin:0;flex:1 1 360px;min-width:300px;max-width:560px;">'
        '<img src="%s%s" style="width:100%%;height:300px;object-fit:cover;border-radius:14px;'
        'box-shadow:0 6px 20px rgba(32,36,58,.20);"/>%s</figure>'
    ) % (_IMG, name, c)


def _gallery(*figs):
    return ('<div style="display:flex;flex-wrap:wrap;gap:12px;margin:14px 0;">%s</div>'
            % ''.join(figs))


class SlideChannelSeedVatTuNgoai(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_vat_tu_ngoai(self):
        ch = self.env.ref('vd_elearning.course_b3', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _VTN_VERSION:
            return True

        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_vtn_pages())
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
        for text, answers in self._vd_vtn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _VTN_VERSION)
        return True

    # ==================================================================
    def _vd_vtn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Vat tu ngoai HD la gi', self._vtn_p1(h2, h3, lead)),
            ('2. Coc be tong - Thang may', self._vtn_p2(h2, h3, lead)),
            ('3. Noi that - Ban bep chau rua', self._vtn_p3(h2, h3, lead)),
            ('4. Den suoi NLMT - Tuong rao san cong', self._vtn_p4(h2, h3, lead)),
            ('5. Gieng khoan be ngam - Chong set', self._vtn_p5(h2, h3, lead)),
            ('6. Ket luan', self._vtn_p6(h2, h3, lead)),
        ]

    def _vtn_p1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#7c2d12,#b45309);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.9;font-weight:700;">'
            'KIẾN THỨC CƠ BẢN VỀ XÂY DỰNG</div>'
            '<div style="font-size:25px;font-weight:900;margin-top:4px;">VẬT TƯ NGOÀI HỢP ĐỒNG</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Những hạng mục KHÔNG nằm '
            'trong báo giá trọn gói &mdash; sale phải nói rõ với khách để tránh hiểu lầm.</div></div>'

            '<h2 style="' + h2 + '">&#9888;&#65039; Vì sao phần này CỰC KỲ quan trọng?</h2>'
            '<p style="' + lead + '">Khách hay nghĩ <i>"xây trọn gói là có hết mọi thứ"</i>. '
            'Nếu sale <b>không nói trước</b> những hạng mục ngoài hợp đồng, đến lúc quyết toán '
            'khách sẽ <b>cãi nhau, mất niềm tin</b>. Vì vậy bạn phải thuộc danh sách này và '
            '<b>chủ động báo khách ngay từ khâu tư vấn</b>.</p>'

            + _mistake(
                '<p style="margin-bottom:0;">Sai lầm lớn nhất: để khách <b>tự hiểu</b> rằng '
                'trọn gói đã bao gồm thang máy, nội thất, sân vườn&hellip; &rarr; khi báo phát '
                'sinh, khách cảm thấy bị "vẽ thêm tiền".</p>'
            )

            + '<h2 style="' + h2 + '">Danh sách hạng mục NGOÀI hợp đồng</h2>'
            '<table><thead><tr><th style="width:56px;">#</th><th>Hạng mục không nằm trong báo giá trọn gói</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;">1</td><td><b>Ép cọc bê tông móng</b> &middot; <b>Thang máy</b></td></tr>'
            '<tr><td style="text-align:center;">2</td><td><b>Nội thất</b> (giường, tủ, bàn ghế, tivi, điều hòa, rèm, tủ bếp&hellip;)</td></tr>'
            '<tr><td style="text-align:center;">3</td><td><b>Đèn sưởi</b> &middot; <b>Năng lượng mặt trời</b></td></tr>'
            '<tr><td style="text-align:center;">4</td><td><b>Tường rào, cổng, sân vườn</b></td></tr>'
            '<tr><td style="text-align:center;">5</td><td><b>Giếng khoan, bể nước ngầm</b> &middot; <b>Hệ thống chống sét</b></td></tr>'
            '<tr><td style="text-align:center;">6</td><td><b>Bàn bếp, chậu rửa</b></td></tr>'
            '</tbody></table>'
            + _core('Khóa này = danh sách những thứ <b>KHÔNG có sẵn</b> trong giá trọn gói. Thuộc để <b>báo khách trước</b>, tránh tranh chấp.')
        )

    def _vtn_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">1) CỌC BÊ TÔNG và THANG MÁY</h2>'
            + _gallery(_fig('image11.jpg', 'Cọc bê tông'), _fig('image27.jpg', 'Thang máy'))
            + '<h3 style="' + h3 + '">Cọc bê tông</h3>'
            '<p>Cọc bê tông <b>chưa nằm trong chi phí phần móng cọc</b> vì lúc báo giá '
            '<b>chưa biết phải ép sâu bao nhiêu</b>. Do đó:</p>'
            + _proof(
                '<p style="margin-bottom:0;">Phần cọc được <b>tính khi thi công thực tế</b>: ép '
                'hết <b>bao nhiêu mét, bao nhiêu cọc</b> thì chủ nhà trả bấy nhiêu theo đơn giá '
                '&mdash; "ép tới đâu tính tới đó".</p>'
            )
            + '<h3 style="' + h3 + '">Thang máy</h3>'
            '<ul>'
            '<li>Đơn giá trọn gói <b>chưa bao gồm thang máy</b>.</li>'
            '<li>Thang máy có nhiều loại (truyền thống, thang kính; hàng liên doanh / nhập khẩu) '
            '&rarr; <b>chi phí khác nhau</b>.</li>'
            '<li>Vinaduy <b>không chuyên thi công thang máy</b>, chỉ <b>hỗ trợ làm hố thang</b> '
            'nếu khách có nhu cầu (thang truyền thống).</li>'
            '</ul>'
            + _core('Cọc bê tông: <b>tính theo thực tế khi ép</b>. Thang máy: <b>không gồm trong giá</b>, Vinaduy chỉ hỗ trợ <b>hố thang</b>.')
        )

    def _vtn_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">2) NỘI THẤT và BÀN BẾP, CHẬU RỬA</h2>'
            + _gallery(_fig('image21.jpg', 'Nội thất'), _fig('image30.png'), _fig('image32.jpg', 'Bàn bếp - Chậu rửa'))
            + '<h3 style="' + h3 + '">Nội thất</h3>'
            '<p>Gồm: <b>giường, tủ, bàn ghế, tivi, tủ lạnh, điều hòa, máy giặt, rèm cửa, vách kệ '
            'trang trí, tủ bếp trên và cánh tủ dưới</b>.</p>'
            '<ul>'
            '<li><b>Không nằm</b> trong đơn giá thi công trọn gói.</li>'
            '<li>Vinaduy <b>vẫn thi công nội thất</b> nhưng <b>bóc tách hợp đồng riêng</b> sau '
            'khi đã thống nhất hợp đồng trọn gói.</li>'
            '</ul>'
            + '<h3 style="' + h3 + '">Bàn bếp, chậu rửa</h3>'
            '<ul>'
            '<li>Đơn giá trọn gói <b>chưa bao gồm</b> bàn bếp và chậu rửa &rarr; <b>báo thêm</b>.</li>'
            '<li>Bàn bếp / tủ bếp thường <b>đi kèm nội thất</b>; đa số chủ nhà <b>tự làm</b> theo sở thích.</li>'
            '</ul>'
            + _core('Nội thất + bàn bếp/chậu rửa: <b>ngoài giá trọn gói</b>. Vinaduy làm nội thất theo <b>hợp đồng riêng</b>.')
        )

    def _vtn_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">3) ĐÈN SƯỞI, NĂNG LƯỢNG MẶT TRỜI và 4) TƯỜNG RÀO, SÂN CỔNG</h2>'
            + _gallery(_fig('image31.png', 'Năng lượng mặt trời'), _fig('image33.jpg', 'Đèn sưởi'),
                       _fig('image25.jpg', 'Tường rào'), _fig('image20.jpg', 'Sân cổng'))
            + '<h3 style="' + h3 + '">Đèn sưởi &amp; Năng lượng mặt trời</h3>'
            '<ul>'
            '<li>Bình nước nóng <b>năng lượng mặt trời chưa tính</b> trong đơn giá &mdash; vì '
            '<b>mỗi nhà vệ sinh đã có sẵn 1 bình nóng lạnh</b> kèm theo.</li>'
            '<li>Khách muốn lắp NLMT &rarr; Vinaduy <b>chỉ thiết kế ống chờ</b>.</li>'
            '<li><b>Pin năng lượng mặt trời</b>: Vinaduy <b>không nhận thi công</b>, không báo giá.</li>'
            '</ul>'
            + '<h3 style="' + h3 + '">Tường rào, sân cổng</h3>'
            '<ul>'
            '<li>Vinaduy <b>có thi công</b> tường rào, sân cổng nhưng <b>báo giá riêng</b>.</li>'
            '<li>Báo giá <b>sau khi thi công được ~60% nhà</b>, vì lúc đầu <b>chưa xác định</b> '
            'diện tích, kích thước, mẫu mã, khối lượng.</li>'
            '<li>Sẽ cùng chủ nhà đo và chốt mẫu khi đã <b>dựng được khung nhà</b> rồi mới báo giá.</li>'
            '</ul>'
            + _core('NLMT: chưa tính (đã có bình nóng lạnh), pin NLMT <b>không nhận</b>. Tường rào/sân cổng: <b>có làm, báo giá riêng</b> sau ~60% nhà.')
        )

    def _vtn_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">5) GIẾNG KHOAN, BỂ NƯỚC NGẦM và HỆ THỐNG CHỐNG SÉT</h2>'
            + _gallery(_fig('image29.jpg', 'Giếng khoan - Bể ngầm'), _fig('image28.jpg'),
                       _fig('image26.jpg', 'Hệ thống chống sét'))
            + '<h3 style="' + h3 + '">Giếng khoan &amp; Bể nước ngầm</h3>'
            '<table><thead><tr><th style="width:160px;">Hạng mục</th><th>Vinaduy xử lý</th></tr></thead><tbody>'
            '<tr><td><b>Giếng khoan</b></td><td><b>KHÔNG thi công</b>, chỉ <b>giới thiệu đơn vị</b> uy tín, giá rẻ.</td></tr>'
            '<tr><td><b>Bể nước ngầm</b></td><td><b>CÓ thi công</b> nhưng <b>báo giá sau</b> dựa trên <b>thể tích bể</b>.</td></tr>'
            '</tbody></table>'
            + _note(
                '<p style="margin-bottom:0;">Dễ nhầm! <b>Giếng khoan = KHÔNG làm</b> (giới thiệu '
                'đơn vị). <b>Bể nước ngầm = CÓ làm</b> (báo giá theo thể tích).</p>'
            )
            + '<h3 style="' + h3 + '">Hệ thống chống sét</h3>'
            '<p>Vinaduy <b>không nhận thi công chống sét</b> (chỉ giới thiệu đơn vị chuyên), vì '
            'hạng mục này đòi hỏi <b>công nghệ, máy móc, quy cách riêng</b>; Vinaduy chỉ chuyên '
            '<b>xây trọn gói</b>.</p>'
            + _core('Giếng khoan: <b>không làm</b> (giới thiệu). Bể ngầm: <b>có làm</b>, báo giá theo thể tích. Chống sét: <b>không nhận</b> (giới thiệu).')
        )

    def _vtn_p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127942; KẾT LUẬN &mdash; PHÂN LOẠI CÁCH XỬ LÝ</h2>'
            '<table><thead><tr><th style="width:42%;">Cách Vinaduy xử lý</th><th>Gồm hạng mục</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">CÓ làm &mdash; báo giá riêng</b></td>'
            '<td>Nội thất (HĐ riêng) &middot; Bàn bếp/chậu rửa &middot; Tường rào/sân cổng &middot; '
            'Bể nước ngầm &middot; Cọc bê tông (tính theo thực tế)</td></tr>'
            '<tr><td><b style="color:#dc2626;">KHÔNG làm &mdash; giới thiệu đơn vị</b></td>'
            '<td>Giếng khoan &middot; Hệ thống chống sét &middot; Pin năng lượng mặt trời</td></tr>'
            '<tr><td><b style="color:#2563eb;">Chỉ hỗ trợ một phần</b></td>'
            '<td>Thang máy (chỉ làm hố thang) &middot; NLMT (chỉ chừa ống chờ)</td></tr>'
            '</tbody></table>'
            + _advice(
                '<p><b>Kịch bản tư vấn:</b> ngay từ đầu nói với khách: <i>"Báo giá trọn gói của '
                'bên em đã gồm phần xây dựng và hoàn thiện cơ bản. Còn các phần như <b>thang máy, '
                'nội thất, sân vườn tường rào, giếng khoan, chống sét, bàn bếp</b> sẽ được tư vấn '
                'và báo giá riêng ạ."</i></p>'
                '<p style="margin-bottom:0;">Nói trước = chuyên nghiệp, minh bạch, khách tin tưởng.</p>'
            )
            + _core('Nói TRƯỚC các hạng mục ngoài hợp đồng = tránh tranh chấp, giữ uy tín.')
            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Kể tối thiểu 5 hạng mục KHÔNG nằm trong hợp đồng.</li>'
            '<li>Cọc bê tông được tính chi phí thế nào?</li>'
            '<li>Giếng khoan và bể nước ngầm: cái nào Vinaduy làm, cái nào không?</li>'
            '<li>Vì sao năng lượng mặt trời chưa được tính trong đơn giá?</li>'
            '<li>Thang máy: Vinaduy hỗ trợ phần gì?</li>'
            '</ol>'
        )

    # ==================================================================
    #  20 CAU HOI (dap an gay PHAN VAN). (dap an, dung?)
    # ==================================================================
    def _vd_vtn_questions(self):
        T, F = True, False
        return [
            ('Hạng mục nào sau đây KHÔNG nằm trong hợp đồng báo giá trọn gói?',
             [('Thang máy, nội thất, chống sét, giếng khoan', T),
              ('Bê tông, sắt thép, xi măng', F),
              ('Cửa nhôm, sơn, gạch men', F),
              ('Ống nước, dây điện, gạch xây', F)]),

            ('Chi phí cọc bê tông (móng cọc) được tính như thế nào?',
             [('Tính theo thực tế khi thi công: ép hết bao nhiêu mét/cọc thì trả bấy nhiêu theo đơn giá', T),
              ('Đã bao gồm trọn gói trong đơn giá ban đầu', F),
              ('Tính theo diện tích sàn của nhà', F),
              ('Tính theo số tầng của nhà', F)]),

            ('Vì sao cọc bê tông chưa được tính chính xác trong báo giá ban đầu?',
             [('Vì chưa biết phải ép sâu bao nhiêu, chưa xác định được khối lượng', T),
              ('Vì cọc bê tông rất rẻ nên bỏ qua', F),
              ('Vì khách không bao giờ cần ép cọc', F),
              ('Vì cọc do khách tự mua', F)]),

            ('Với thang máy, Vinaduy hỗ trợ phần gì?',
             [('Chỉ hỗ trợ thi công hố thang (nếu khách cần thang truyền thống)', T),
              ('Thi công trọn gói cả thang máy, đã tính trong giá', F),
              ('Tặng miễn phí thang máy', F),
              ('Không liên quan gì đến thang máy', F)]),

            ('Nội thất (giường, tủ, bàn ghế, tivi, điều hòa...) được xử lý thế nào?',
             [('Không nằm trong giá trọn gói; Vinaduy vẫn làm nhưng bóc tách hợp đồng riêng', T),
              ('Đã bao gồm đầy đủ trong giá trọn gói', F),
              ('Vinaduy không bao giờ làm nội thất', F),
              ('Bắt buộc khách phải mua của Vinaduy', F)]),

            ('Bàn bếp và chậu rửa nằm trong hay ngoài đơn giá trọn gói?',
             [('Ngoài đơn giá, phải báo thêm; thường đi kèm nội thất', T),
              ('Trong đơn giá trọn gói', F),
              ('Vinaduy không nhận làm bàn bếp', F),
              ('Được tặng kèm miễn phí', F)]),

            ('Vì sao bình nước nóng năng lượng mặt trời CHƯA được tính trong đơn giá?',
             [('Vì mỗi nhà vệ sinh đã có sẵn 1 bình nóng lạnh kèm theo', T),
              ('Vì năng lượng mặt trời bị cấm', F),
              ('Vì khách luôn từ chối dùng', F),
              ('Vì quá đắt nên không nhà nào lắp', F)]),

            ('Nếu khách muốn lắp năng lượng mặt trời thì Vinaduy làm gì?',
             [('Chỉ thiết kế (chừa) ống chờ', T),
              ('Lắp trọn gói miễn phí', F),
              ('Từ chối tuyệt đối, không hỗ trợ gì', F),
              ('Tự ý lắp mà không hỏi khách', F)]),

            ('Pin năng lượng mặt trời thì Vinaduy xử lý ra sao?',
             [('Không nhận thi công, không báo giá', T),
              ('Thi công trọn gói trong hợp đồng', F),
              ('Chỉ chừa ống chờ như bình NLMT', F),
              ('Bắt buộc mọi nhà phải lắp', F)]),

            ('Tường rào, sân cổng được báo giá vào thời điểm nào?',
             [('Báo giá riêng sau khi thi công được khoảng 60% nhà', T),
              ('Báo giá ngay trong hợp đồng trọn gói ban đầu', F),
              ('Không bao giờ báo giá vì không làm', F),
              ('Báo giá trước khi khởi công', F)]),

            ('Vì sao tường rào/sân cổng chưa báo giá ngay từ đầu?',
             [('Vì chưa xác định được diện tích, kích thước, mẫu mã, khối lượng', T),
              ('Vì Vinaduy không bao giờ làm tường rào', F),
              ('Vì tường rào luôn miễn phí', F),
              ('Vì khách không được phép làm tường rào', F)]),

            ('Giếng khoan: Vinaduy xử lý thế nào?',
             [('Không thi công, chỉ giới thiệu đơn vị uy tín, giá rẻ', T),
              ('Có thi công và đã tính trong giá trọn gói', F),
              ('Có thi công, báo giá theo thể tích', F),
              ('Bắt buộc nhà nào cũng phải khoan giếng', F)]),

            ('Bể nước ngầm: Vinaduy xử lý thế nào?',
             [('Có thi công nhưng báo giá sau, dựa trên thể tích bể', T),
              ('Không thi công, chỉ giới thiệu đơn vị', F),
              ('Đã bao gồm sẵn trong giá trọn gói', F),
              ('Chỉ thiết kế ống chờ', F)]),

            ('Cặp "giếng khoan" và "bể nước ngầm" khác nhau ở chỗ nào?',
             [('Giếng khoan: KHÔNG làm (giới thiệu); Bể ngầm: CÓ làm (báo giá theo thể tích)', T),
              ('Giếng khoan: CÓ làm; Bể ngầm: KHÔNG làm', F),
              ('Cả hai đều không làm', F),
              ('Cả hai đều đã gồm trong giá trọn gói', F)]),

            ('Hệ thống chống sét: Vinaduy xử lý thế nào?',
             [('Không nhận thi công, chỉ giới thiệu đơn vị chuyên', T),
              ('Thi công và đã tính trong giá trọn gói', F),
              ('Tặng miễn phí cho mọi nhà', F),
              ('Bắt buộc khách phải làm với Vinaduy', F)]),

            ('Vì sao Vinaduy không nhận thi công chống sét?',
             [('Vì đòi hỏi công nghệ, máy móc, quy cách riêng; Vinaduy chỉ chuyên xây trọn gói', T),
              ('Vì chống sét là bất hợp pháp', F),
              ('Vì không nhà nào cần chống sét', F),
              ('Vì chống sét quá rẻ', F)]),

            ('Nhóm hạng mục nào Vinaduy "CÓ làm nhưng báo giá riêng"?',
             [('Nội thất, bàn bếp/chậu rửa, tường rào/sân cổng, bể nước ngầm', T),
              ('Giếng khoan, chống sét, pin năng lượng mặt trời', F),
              ('Bê tông, sắt thép, xi măng', F),
              ('Cửa nhôm, sơn, mái ngói', F)]),

            ('Nhóm hạng mục nào Vinaduy "KHÔNG làm, chỉ giới thiệu đơn vị"?',
             [('Giếng khoan, hệ thống chống sét, pin năng lượng mặt trời', T),
              ('Nội thất, bàn bếp, tường rào', F),
              ('Bể nước ngầm, cọc bê tông', F),
              ('Thang máy (hố thang), ống chờ NLMT', F)]),

            ('Sai lầm lớn nhất của sale khi tư vấn về phạm vi hợp đồng là gì?',
             [('Để khách tự hiểu "trọn gói là có hết" rồi đến lúc báo phát sinh khách thấy bị vẽ thêm tiền', T),
              ('Nói rõ các hạng mục ngoài hợp đồng ngay từ đầu', F),
              ('Báo giá minh bạch từng phần', F),
              ('Giới thiệu đơn vị uy tín cho hạng mục không nhận', F)]),

            ('Cách tư vấn đúng về các hạng mục ngoài hợp đồng là gì?',
             [('Chủ động nói rõ ngay từ khâu tư vấn để minh bạch, tránh tranh chấp', T),
              ('Giấu không nói để khách dễ chốt hợp đồng', F),
              ('Chỉ nói khi khách thắc mắc lúc quyết toán', F),
              ('Hứa làm tất cả miễn phí rồi tính sau', F)]),
        ]
