# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau thi cho khoa "Vat tu" (course_vat_tu_xay_tho).

Doi tuong: nhan vien sale TRAI NGANH, khong biet va kho nho ten vat tu. Khoa
giup nho + phan biet: VAT TU TRONG HOP DONG (tho: be tong, sat thep, xi mang,
gach xay, ong nuoc, day dien; hoan thien: cua nhom, son, gach men, cau thang...)
theo thuong hieu Mien Bac / Mien Nam, va VAT TU KHONG TRONG HOP DONG (thang may,
noi that, chong set...). Bam theo file "Vat tu trong hop dong.pptx".
Anh dat o static/src/img/vattu. Bai thi 20 cau gay PHAN VAN (trao thuong hieu
Bac/Nam, trao kich thuoc) de ep nho chinh xac + ap dung tu van.

Idempotent theo VERSION. Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _advice, _proof, _mistake

_VT_VERSION = 'v2'
_PARAM_KEY = 'vd_elearning.vattu_seed_version'
_IMG = '/vd_elearning/static/src/img/vattu/'


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


class SlideChannelSeedVatTu(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_vat_tu(self):
        ch = self.env.ref('vd_elearning.course_vat_tu_xay_tho', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _VT_VERSION:
            return True

        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_vt_pages())
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
        for text, answers in self._vd_vt_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _VT_VERSION)
        return True

    # ==================================================================
    def _vd_vt_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Vat tu la gi', self._p1(h2, h3, lead)),
            ('2. Vat tu tho (trong HD)', self._p2(h2, h3, lead)),
            ('3. Vat tu hoan thien (trong HD)', self._p3(h2, h3, lead)),
            ('4. Ket luan - meo nho', self._p5(h2, h3, lead)),
        ]

    def _p1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#1e3a8a,#3730a3);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.85;font-weight:700;">'
            'KIẾN THỨC CƠ BẢN VỀ XÂY DỰNG</div>'
            '<div style="font-size:25px;font-weight:900;margin-top:4px;">VẬT TƯ TRONG HỢP ĐỒNG</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Dành cho nhân viên mới '
            '(kể cả trái ngành) &mdash; nhớ tên vật tư, phân biệt thương hiệu theo vùng và '
            'biết cái gì CÓ / KHÔNG có trong hợp đồng.</div></div>'

            '<h2 style="' + h2 + '">&#129521; "Vật tư" là gì?</h2>'
            '<p style="' + lead + '"><b>Vật tư</b> là <b>toàn bộ vật liệu</b> dùng để xây nên '
            'ngôi nhà: từ bê tông, sắt thép, xi măng, gạch&hellip; cho đến sơn, cửa, gạch men, '
            'cầu thang. Khách rất hay hỏi <i>"bên em dùng vật tư hãng gì?"</i> &mdash; bạn phải '
            '<b>trả lời trôi chảy</b> thì khách mới tin.</p>'

            + _note(
                '<p style="margin-bottom:0;"><b>Quan trọng nhất với sale:</b> nhớ <b>tên vật tư</b> '
                'và <b>thương hiệu theo vùng (Miền Bắc / Miền Nam)</b> để khi khách hỏi là trả '
                'lời được ngay, tạo niềm tin.</p>'
            )

            + '<table><thead><tr><th style="width:230px;">Nhóm vật tư trong hợp đồng</th><th>Gồm</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">Vật tư thô</b></td>'
            '<td>Bê tông, sắt thép, xi măng, gạch xây, ống nước, dây điện</td></tr>'
            '<tr><td><b style="color:#16a34a;">Vật tư hoàn thiện</b></td>'
            '<td>Cửa nhôm, sơn, công tắc, đèn, gạch men, cầu thang, mái ngói&hellip;</td></tr>'
            '</tbody></table>'
            '<p style="font-size:14px;color:#64748b;font-style:italic;">(Phần "vật tư KHÔNG '
            'nằm trong hợp đồng" sẽ học ở một khóa riêng.)</p>'
            + _core('Vật tư = vật liệu xây nhà. Khóa này tập trung <b>vật tư TRONG hợp đồng</b>: nhớ <b>tên</b> + <b>thương hiệu theo vùng Bắc/Nam</b>.')
        )

    def _p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN A &mdash; VẬT TƯ THÔ (nằm trong hợp đồng)</h2>'
            '<p style="' + lead + '">Vật tư thô là phần "xương sống" của nhà. Thương hiệu '
            '<b>khác nhau giữa Miền Bắc và Miền Nam</b> &mdash; nhớ theo bảng.</p>'

            '<h3 style="' + h3 + '">1) Bê tông</h3>'
            + _gallery(_fig('image12.jpg', 'Bê tông thương phẩm'), _fig('image18.jpg'))
            + '<p><b>100% công ty dùng bê tông thương phẩm MÁC 300</b> (bê tông trộn sẵn chở '
            'đến bằng xe bồn). Chỉ dùng <b>bê tông trộn thủ công (cũng mác 300)</b> khi '
            '<b>ngõ hẻm nhỏ, ô tô không vào được</b>.</p>'

            '<h3 style="' + h3 + '">2) Sắt thép</h3>'
            + _gallery(_fig('image21.jpg'), _fig('image24.jpg'))
            + '<table><thead><tr><th style="text-align:center;">MIỀN BẮC</th>'
            '<th style="text-align:center;">MIỀN NAM</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;">Sắt <b>Hòa Phát</b>, <b>Việt Nhật</b>, <b>Việt Úc</b></td>'
            '<td style="text-align:center;">Sắt <b>Pomina</b>, <b>Sắt Miền Nam</b></td></tr>'
            '</tbody></table>'
            '<p style="font-size:14px;color:#64748b;">(Hoặc sắt thép tương đương.)</p>'

            '<h3 style="' + h3 + '">3) Xi măng</h3>'
            + _gallery(_fig('image30.jpg'), _fig('image37.jpg'))
            + '<table><thead><tr><th style="text-align:center;">MIỀN BẮC</th>'
            '<th style="text-align:center;">MIỀN NAM</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;"><b>Hoàng Thạch</b>, <b>Hoàng Long</b>, <b>Nghi Sơn</b> (kèm Vissai &amp; Vicem)</td>'
            '<td style="text-align:center;"><b>Hà Tiên</b>, <b>Insee</b> (kèm Vissai &amp; Vicem)</td></tr>'
            '</tbody></table>'

            '<h3 style="' + h3 + '">4) Gạch xây &middot; 5) Ống nước &middot; 6) Dây điện</h3>'
            + _gallery(_fig('image25.png', 'Gạch xây'), _fig('image23.png', 'Ống nước'),
                       _fig('image28.jpg', 'Dây điện'))
            + '<table><thead><tr><th>Vật tư</th><th style="text-align:center;">MIỀN BẮC</th>'
            '<th style="text-align:center;">MIỀN NAM</th></tr></thead><tbody>'
            '<tr><td><b>Gạch xây</b></td><td style="text-align:center;">Gạch <b>đặc 3 chấm</b></td>'
            '<td style="text-align:center;">Gạch <b>4 - 6 lỗ</b></td></tr>'
            '<tr><td><b>Ống nước</b></td><td style="text-align:center;">Ống <b>Tiền Phong</b></td>'
            '<td style="text-align:center;">Ống <b>Bình Minh</b></td></tr>'
            '<tr><td><b>Dây điện</b></td><td style="text-align:center;">Dây <b>Trần Phú</b></td>'
            '<td style="text-align:center;">Dây <b>Cadivi</b></td></tr>'
            '</tbody></table>'
            + _core(
                'Bê tông <b>thương phẩm mác 300</b>. Nhớ cặp Bắc/Nam: Ống nước <b>Tiền Phong / '
                'Bình Minh</b> &middot; Dây điện <b>Trần Phú / Cadivi</b> &middot; Gạch <b>3 chấm / 4-6 lỗ</b>.'
            )
        )

    def _p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN B &mdash; VẬT TƯ HOÀN THIỆN (nằm trong hợp đồng)</h2>'
            '<p style="' + lead + '">Là phần làm cho nhà "đẹp và dùng được": cửa, sơn, gạch '
            'men, thiết bị&hellip;</p>'

            '<h3 style="' + h3 + '">Cửa nhôm &middot; Sơn &middot; Điện</h3>'
            + _gallery(_fig('image34.jpg', 'Cửa nhôm'), _fig('image35.jpg'), _fig('image33.jpg'))
            + '<table><tbody>'
            '<tr><td style="width:180px;"><b>Cửa nhôm</b></td><td>Nhôm <b>Xingfa Việt Nam</b> (cả Miền Bắc và Miền Nam).</td></tr>'
            '<tr><td><b>Sơn</b></td><td>Sơn <b>Nippon</b> &mdash; thi công <b>2 lớp lót + 2 lớp màu</b>.</td></tr>'
            '<tr><td><b>Công tắc</b></td><td><b>Panasonic</b>.</td></tr>'
            '<tr><td><b>Đèn</b></td><td><b>Rạng Đông</b>.</td></tr>'
            '</tbody></table>'

            '<h3 style="' + h3 + '">Đá &middot; Thạch cao &middot; Thiết bị nước</h3>'
            + _gallery(_fig('image36.jpg'), _fig('image42.jpg'), _fig('image40.jpg'))
            + '<table><tbody>'
            '<tr><td style="width:180px;"><b>Đá</b></td><td><b>Đá đen rừng</b>.</td></tr>'
            '<tr><td><b>Thạch cao</b></td><td><b>Thạch cao Hà Nội</b>.</td></tr>'
            '<tr><td><b>Bình nóng lạnh</b></td><td><b>Rossi</b>.</td></tr>'
            '<tr><td><b>Bồn nước</b></td><td><b>1000 L</b>.</td></tr>'
            '</tbody></table>'

            '<h3 style="' + h3 + '">Gạch men (chú ý kích thước)</h3>'
            + '<table><thead><tr><th>Loại gạch</th><th style="text-align:center;">Kích thước</th></tr></thead><tbody>'
            '<tr><td><b>Gạch lát nền</b></td><td style="text-align:center;"><b>80 x 80</b></td></tr>'
            '<tr><td><b>Gạch ốp WC</b></td><td style="text-align:center;"><b>40 x 80</b></td></tr>'
            '<tr><td><b>Gạch nền WC</b></td><td style="text-align:center;"><b>40 x 80</b></td></tr>'
            '</tbody></table>'
            '<p style="font-size:14px;color:#64748b;">Thương hiệu gạch men: <b>Takao &amp; Catalan</b>.</p>'

            '<h3 style="' + h3 + '">Cầu thang &middot; Mái ngói &middot; Khung kèo</h3>'
            + _gallery(_fig('image45.jpg', 'Mái ngói'), _fig('image47.jpg', 'Cầu thang'), _fig('image41.jpg'))
            + '<table><tbody>'
            '<tr><td style="width:200px;"><b>Tay vịn &amp; trụ cầu thang</b></td><td>Gỗ <b>Lim Nam Phi</b>.</td></tr>'
            '<tr><td><b>Lan can cầu thang</b></td><td>Kính <b>cường lực 10 ly</b>.</td></tr>'
            '<tr><td><b>Đá cầu thang</b></td><td><b>Đá đen rừng</b>.</td></tr>'
            '<tr><td><b>Mái ngói</b></td><td><b>Viglacera</b>.</td></tr>'
            '<tr><td><b>Khung kèo</b></td><td><b>Thép siêu nhẹ</b>.</td></tr>'
            '</tbody></table>'
            + _core(
                'Cửa <b>Xingfa</b> &middot; Sơn <b>Nippon (2 lót + 2 màu)</b> &middot; Công tắc '
                '<b>Panasonic</b> &middot; Đèn <b>Rạng Đông</b> &middot; Gạch nền <b>80x80</b>, WC '
                '<b>40x80</b> &middot; Mái <b>Viglacera</b> &middot; Lan can kính <b>10 ly</b>.'
            )
        )

    def _p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127942; KẾT LUẬN &mdash; MẸO NHỚ</h2>'
            + _advice(
                '<p><b>Mẹo nhớ thương hiệu theo vùng (Bắc / Nam):</b></p>'
                '<ul>'
                '<li>Ống nước: <b>Tiền Phong</b> (Bắc) / <b>Bình Minh</b> (Nam).</li>'
                '<li>Dây điện: <b>Trần Phú</b> (Bắc) / <b>Cadivi</b> (Nam).</li>'
                '<li>Xi măng: <b>Hoàng Thạch - Nghi Sơn</b> (Bắc) / <b>Hà Tiên - Insee</b> (Nam).</li>'
                '<li>Sắt: <b>Hòa Phát - Việt Nhật - Việt Úc</b> (Bắc) / <b>Pomina - Miền Nam</b> (Nam).</li>'
                '<li>Gạch xây: <b>đặc 3 chấm</b> (Bắc) / <b>4-6 lỗ</b> (Nam).</li>'
                '</ul>'
                '<p style="margin-bottom:0;">Hàng dùng chung 2 miền: Cửa <b>Xingfa</b>, Sơn '
                '<b>Nippon</b>, Đèn <b>Rạng Đông</b>, Công tắc <b>Panasonic</b>.</p>'
            )
            + _core(
                'Khi khách hỏi vật tư: nói <b>đúng thương hiệu theo vùng của khách</b> + nhấn '
                '<b>"đây là vật tư trong hợp đồng"</b>; rồi chủ động nói <b>những gì KHÔNG trong '
                'hợp đồng</b> để minh bạch.'
            )
            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Ống nước / dây điện Miền Bắc và Miền Nam dùng hãng nào?</li>'
            '<li>Công ty dùng bê tông loại gì, mác bao nhiêu?</li>'
            '<li>Gạch lát nền và gạch WC kích thước bao nhiêu? (80x80 và 40x80)</li>'
            '<li>Cửa nhôm, sơn, đèn dùng hãng gì?</li>'
            '<li>Cầu thang: tay vịn/trụ bằng gì, lan can kính mấy ly? (gỗ Lim Nam Phi, kính 10 ly)</li>'
            '</ol>'
        )

    # ==================================================================
    #  20 CAU HOI (dap an gay PHAN VAN - trao thuong hieu Bac/Nam, kich thuoc).
    # ==================================================================
    def _vd_vt_questions(self):
        T, F = True, False
        return [
            ('Công ty dùng loại bê tông nào là chủ yếu?',
             [('100% bê tông thương phẩm mác 300', T),
              ('Bê tông trộn thủ công mác 200', F),
              ('Bê tông thương phẩm mác 100', F),
              ('Không dùng bê tông', F)]),

            ('Khi nào mới dùng bê tông trộn thủ công?',
             [('Khi ngõ hẻm nhỏ, ô tô (xe bồn) không vào được', T),
              ('Khi khách muốn tiết kiệm', F),
              ('Khi xây nhà cao tầng', F),
              ('Luôn luôn dùng trộn thủ công', F)]),

            ('Sắt thép Miền Bắc thường dùng hãng nào?',
             [('Hòa Phát, Việt Nhật, Việt Úc', T),
              ('Pomina, Sắt Miền Nam', F),
              ('Cadivi, Trần Phú', F),
              ('Hà Tiên, Insee', F)]),

            ('Sắt thép Miền Nam thường dùng hãng nào?',
             [('Pomina, Sắt Miền Nam', T),
              ('Hòa Phát, Việt Nhật, Việt Úc', F),
              ('Tiền Phong, Bình Minh', F),
              ('Hoàng Thạch, Nghi Sơn', F)]),

            ('Xi măng Miền Bắc gồm những hãng nào?',
             [('Hoàng Thạch, Hoàng Long, Nghi Sơn', T),
              ('Hà Tiên, Insee', F),
              ('Pomina, Hòa Phát', F),
              ('Tiền Phong, Bình Minh', F)]),

            ('Xi măng Miền Nam gồm những hãng nào?',
             [('Hà Tiên, Insee', T),
              ('Hoàng Thạch, Nghi Sơn', F),
              ('Trần Phú, Cadivi', F),
              ('Việt Nhật, Việt Úc', F)]),

            ('Gạch xây ở Miền Bắc và Miền Nam khác nhau thế nào?',
             [('Miền Bắc gạch đặc 3 chấm, Miền Nam gạch 4-6 lỗ', T),
              ('Miền Bắc gạch 4-6 lỗ, Miền Nam gạch đặc 3 chấm', F),
              ('Cả hai miền đều dùng gạch 4-6 lỗ', F),
              ('Cả hai miền đều dùng gạch đặc 3 chấm', F)]),

            ('Ống nước Miền Bắc / Miền Nam dùng hãng nào?',
             [('Miền Bắc: Tiền Phong — Miền Nam: Bình Minh', T),
              ('Miền Bắc: Bình Minh — Miền Nam: Tiền Phong', F),
              ('Cả hai miền: Cadivi', F),
              ('Miền Bắc: Trần Phú — Miền Nam: Cadivi', F)]),

            ('Dây điện Miền Bắc / Miền Nam dùng hãng nào?',
             [('Miền Bắc: Trần Phú — Miền Nam: Cadivi', T),
              ('Miền Bắc: Cadivi — Miền Nam: Trần Phú', F),
              ('Cả hai miền: Tiền Phong', F),
              ('Miền Bắc: Bình Minh — Miền Nam: Trần Phú', F)]),

            ('Cửa nhôm dùng loại nào?',
             [('Nhôm Xingfa Việt Nam (cả Miền Bắc và Miền Nam)', T),
              ('Nhôm Xingfa chỉ ở Miền Bắc, Miền Nam dùng hãng khác', F),
              ('Cửa gỗ Lim Nam Phi', F),
              ('Cửa nhựa lõi thép', F)]),

            ('Sơn dùng hãng gì và thi công mấy lớp?',
             [('Sơn Nippon — 2 lớp lót + 2 lớp màu', T),
              ('Sơn Nippon — 1 lớp lót + 1 lớp màu', F),
              ('Sơn Dulux — 2 lớp lót + 2 lớp màu', F),
              ('Sơn Nippon — 3 lớp màu, không lót', F)]),

            ('Công tắc và đèn dùng hãng nào?',
             [('Công tắc Panasonic, đèn Rạng Đông', T),
              ('Công tắc Rạng Đông, đèn Panasonic', F),
              ('Công tắc Cadivi, đèn Nippon', F),
              ('Công tắc Panasonic, đèn Philips', F)]),

            ('Bình nóng lạnh và bồn nước trong hợp đồng là gì?',
             [('Bình nóng lạnh Rossi, bồn nước 1000L', T),
              ('Bình nóng lạnh 1000L, bồn nước Rossi', F),
              ('Bình nóng lạnh Ariston, bồn nước 500L', F),
              ('Bình nóng lạnh Rossi, bồn nước 2000L', F)]),

            ('Gạch lát nền có kích thước bao nhiêu?',
             [('80 x 80', T),
              ('40 x 80', F),
              ('60 x 60', F),
              ('30 x 30', F)]),

            ('Gạch ốp và gạch nền nhà vệ sinh (WC) có kích thước bao nhiêu?',
             [('40 x 80', T),
              ('80 x 80', F),
              ('20 x 20', F),
              ('50 x 50', F)]),

            ('Mái ngói và khung kèo dùng loại nào?',
             [('Ngói Viglacera, khung kèo thép siêu nhẹ', T),
              ('Ngói Takao, khung kèo gỗ Lim', F),
              ('Ngói Catalan, khung kèo sắt Pomina', F),
              ('Ngói Viglacera, khung kèo bê tông', F)]),

            ('Tay vịn - trụ cầu thang và lan can cầu thang làm bằng gì?',
             [('Tay vịn/trụ gỗ Lim Nam Phi, lan can kính cường lực 10 ly', T),
              ('Tay vịn/trụ gỗ Lim Nam Phi, lan can kính 5 ly', F),
              ('Tay vịn/trụ inox, lan can kính cường lực 10 ly', F),
              ('Tay vịn/trụ gỗ thường, lan can sắt', F)]),

            ('Đá ốp (đá cầu thang) dùng loại đá nào?',
             [('Đá đen rừng', T),
              ('Đá trắng Ý', F),
              ('Đá hoa cương đỏ', F),
              ('Đá Thạch cao Hà Nội', F)]),

            ('Trần thạch cao dùng loại nào?',
             [('Thạch cao Hà Nội', T),
              ('Thạch cao Hà Tiên', F),
              ('Thạch cao Insee', F),
              ('Thạch cao Viglacera', F)]),

            ('Gạch men (gạch lát) dùng thương hiệu nào?',
             [('Takao và Catalan', T),
              ('Viglacera và Hà Tiên', F),
              ('Nippon và Panasonic', F),
              ('Tiền Phong và Bình Minh', F)]),
        ]
