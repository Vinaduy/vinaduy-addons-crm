# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa "KỸ NĂNG GIỌNG NÓI" (Kỹ năng Sale).

Biến tài liệu gốc (Giọng nói.txt - sếp Hinh: nhận diện vấn đề + 4 nguyên tắc +
công thức TO-RÕ-ĐỀU-CÓ NHỊP + thực hành hằng ngày + quy định bắt buộc) thành 1
khóa trình bày dễ hiểu - dễ nhớ - dễ áp dụng cho nhân viên MỚI, theo FORM chuẩn
khóa học VINADUY: TIÊU ĐỀ LỚN có hiệu ứng, khung công thức, tình huống, lời
khuyên, chứng minh, sai lầm, câu chốt thuộc lòng và ô "ÁP DỤNG NGAY".

Khóa KHÔNG có ảnh nguồn => dùng thiết kế typography lớn + thẻ màu + 4 ô công
thức (TO-RÕ-ĐỀU-CÓ NHỊP) thay cho ảnh. Hiệu ứng toàn khóa qua khối <style>.

Channel "Kỹ năng giọng nói" được TẠO QUA UI (id 22, không có xmlid) => seed TÌM
THEO TÊN thay vì env.ref. Helper riêng dùng prefix _kgn_ (xem
reference-seed-method-name-collision). Idempotent theo PHIÊN BẢN.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_KGN_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.kn_giong_noi_seed_version'

# ---------------------------------------------------------------------------
#  HIỆU ỨNG TOÀN KHÓA (nối chuỗi thuần - KHÔNG dùng % format -> % an toàn)
# ---------------------------------------------------------------------------
_STYLE = (
    '<style>'
    '.vd-kgn .vd-card{animation:vdRise .7s ease both;}'
    '.vd-kgn .vd-hero{position:relative;overflow:hidden;}'
    '.vd-kgn .vd-hero::after{content:"";position:absolute;top:0;left:-65%;'
    'width:45%;height:100%;background:linear-gradient(120deg,'
    'rgba(255,255,255,0) 0%,rgba(255,255,255,.55) 50%,rgba(255,255,255,0) 100%);'
    'transform:skewX(-22deg);animation:vdShine 3.4s ease-in-out infinite;}'
    '.vd-kgn .vd-tile{transition:transform .3s ease,box-shadow .3s ease;}'
    '.vd-kgn .vd-tile:hover{transform:translateY(-6px);'
    'box-shadow:0 18px 40px rgba(2,6,23,.30);}'
    '.vd-kgn .vd-pulse{display:inline-block;animation:vdPulse 1.5s ease-in-out infinite;}'
    '@keyframes vdShine{0%{left:-65%}55%{left:135%}100%{left:135%}}'
    '@keyframes vdRise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}'
    '@keyframes vdPulse{0%,100%{transform:translateX(0)}50%{transform:translateX(7px)}}'
    '</style>'
)


def _hero(title_small, title_big, sub):
    """Tiêu đề SIÊU LỚN - ấn tượng (đỏ cam thương hiệu) + hiệu ứng quét sáng."""
    return (
        '<div class="vd-hero" style="background:linear-gradient(135deg,'
        '#f5523c 0%%,#d62f12 100%%);border-radius:22px;padding:42px 28px;'
        'margin:4px 0 28px;text-align:center;'
        'box-shadow:0 16px 40px rgba(214,47,18,.40);">'
        '<div style="color:#ffe6df;font-size:17px;font-weight:800;letter-spacing:4px;'
        'text-transform:uppercase;margin-bottom:10px;">%s</div>'
        '<div style="color:#ffffff;font-size:56px;font-weight:900;line-height:1.04;'
        'letter-spacing:1px;text-shadow:0 3px 10px rgba(0,0,0,.28);">%s</div>'
        '<div style="color:#fff4f0;font-size:17px;font-weight:600;margin-top:16px;'
        'max-width:780px;margin-left:auto;margin-right:auto;">%s</div></div>'
    ) % (title_small, title_big, sub)


def _card(c1, c2, icon, title, inner):
    """Thẻ - đầu thẻ gradient màu, trồi lên khi hiện (vdRise)."""
    return (
        '<div class="vd-card" style="border:1px solid #e2e8f0;border-radius:18px;'
        'margin:24px 0;overflow:hidden;box-shadow:0 10px 30px rgba(2,6,23,.10);">'
        '<div style="background:linear-gradient(135deg,%s 0%%,%s 100%%);'
        'padding:16px 20px;color:#fff;font-size:22px;font-weight:900;'
        'letter-spacing:.5px;">%s %s</div>'
        '<div style="padding:18px 20px;">%s</div></div>'
    ) % (c1, c2, icon, title, inner)


def _tile(big, name, desc, c1, c2):
    """1 ô lớn trong bộ công thức 4 chữ (TO-RÕ-ĐỀU-CÓ NHỊP)."""
    return (
        '<div class="vd-tile" style="flex:1 1 220px;min-width:200px;'
        'background:linear-gradient(135deg,%s 0%%,%s 100%%);border-radius:18px;'
        'padding:22px 18px;text-align:center;color:#fff;'
        'box-shadow:0 10px 26px rgba(2,6,23,.18);">'
        '<div style="font-size:40px;font-weight:900;line-height:1;'
        'text-shadow:0 2px 6px rgba(0,0,0,.22);">%s</div>'
        '<div style="font-size:18px;font-weight:800;margin-top:8px;'
        'letter-spacing:1px;">%s</div>'
        '<div style="font-size:13.5px;font-weight:600;margin-top:8px;'
        'opacity:.95;">%s</div></div>'
    ) % (c1, c2, big, name, desc)


def _quad(*tiles):
    return ('<div style="display:flex;flex-wrap:wrap;gap:16px;margin:20px 0;'
            'justify-content:center;">%s</div>') % ''.join(tiles)


class SlideChannelSeedKnGiongNoi(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_kn_giong_noi(self):
        # Channel tạo qua UI (id 22) - tìm theo TÊN (en_US/vi_VN đều "Kỹ năng giọng nói").
        ch = self.sudo().search([('name', 'ilike', 'giọng nói')], limit=1)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _KGN_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:30px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_kgn_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-kgn" style="%s">%s</div>'
                                 % (_WRAP, merged)),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_kgn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _KGN_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (5 phần)
    # ==================================================================
    def _vd_kgn_pages(self):
        h2 = 'font-size:20px;font-weight:900;color:#1e293b;margin:20px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#b91c1c;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('Nhận diện vấn đề', self._kgn_p1(h2, h3, lead)),
            ('4 nguyên tắc bắt buộc', self._kgn_p2(h2, h3, lead)),
            ('Công thức TO-RÕ-ĐỀU-CÓ NHỊP', self._kgn_p3(h2, h3, lead)),
            ('Thực hành hằng ngày', self._kgn_p4(h2, h3, lead)),
            ('Quy định bắt buộc', self._kgn_p5(h2, h3, lead)),
        ]

    # ------------------------------------------------------------------
    def _kgn_p1(self, h2, h3, lead):
        return (
            _hero('Kỹ năng Sale &mdash; Gọi điện', 'GIỌNG NÓI',
                  'Khi gọi điện, khách KHÔNG thấy mặt em, không thấy công ty &mdash; '
                  'thứ DUY NHẤT khách cảm nhận là GIỌNG NÓI. Khách đánh giá chỉ trong '
                  '10&ndash;30 giây đầu.')

            + '<p style="' + lead + '">Sự thật đầu tiên: <b>khách không hề thấy mặt em</b>. '
            'Không thấy quần áo, không thấy thái độ, không thấy công ty to hay nhỏ. '
            'Khách <b>không phân tích</b> em học xây dựng chưa, kinh nghiệm bao nhiêu '
            '&mdash; khách chỉ <b>CẢM</b>, và cảm qua giọng: <b>to hay nhỏ, chắc hay '
            'run, nhanh gọn hay chậm chạp, có năng lượng hay buồn ngủ</b>.</p>'

            + _formula(
                '70% khách KHÔNG ký vì lý do chuyên môn &mdash; <b>70% khách ký vì '
                'CẢM GIÁC TIN</b>. Và <span style="color:#dc2626;">giọng nói</span> là '
                'thứ tạo cảm giác tin <b>nhanh nhất</b>.'
            )

            + _card('#b91c1c', '#ef4444', '&#10060;', '4 KIỂU GIỌNG ĐANG GIẾT SALE',
                    '<table><thead><tr><th style="width:42%;">Kiểu giọng</th>'
                    '<th>Khách nghĩ ngay trong đầu</th></tr></thead><tbody>'
                    '<tr><td><b>Giọng nhỏ</b></td><td>"Sale này thiếu tự tin."</td></tr>'
                    '<tr><td><b>Giọng chậm</b></td><td>"Không chuyên nghiệp &mdash; nói chuyện mất thời gian."</td></tr>'
                    '<tr><td><b>Vừa nói vừa nghĩ</b><br/>("à thì&hellip; để em xem&hellip;")</td>'
                    '<td>"Chưa chắc &mdash; chưa rõ &mdash; chưa hiểu việc."</td></tr>'
                    '<tr><td><b>Giọng buồn ngủ, không nhiệt</b></td>'
                    '<td>"Chính sale còn không hào hứng, sao tôi phải nghe?"</td></tr>'
                    '</tbody></table>'
                    '<p style="margin-bottom:0;color:#b91c1c;font-weight:800;">'
                    '&#128683; Khách KHÔNG nói ra, nhưng khách CÚP MÁY.</p>')

            + _mistake(
                '<p style="margin-bottom:0;">Điều nguy hiểm nhất: <b>sale không biết '
                'mình đang yếu</b>. Khách cúp máy mà không chửi, không phản hồi, không '
                'phàn nàn &mdash; nhưng <b>không bao giờ quay lại</b>. Sale lại tưởng '
                '"chắc khách bận", "chắc khách chưa có nhu cầu". KHÔNG PHẢI &mdash; là '
                'do GIỌNG NÓI.</p>'
            )

            + _chot(
                'Giọng nói yếu = Khách đánh giá công ty yếu = Khách <b>không giao nhà '
                'trăm triệu &mdash; hàng tỷ</b> cho mình. Đây không phải kỹ năng phụ '
                '&mdash; đây là <b>kỹ năng sống còn</b> của sale gọi điện.'
            )

            + _apply(
                '<p style="margin-bottom:0;">Ghi nhớ: khách đánh giá em qua <b>giọng '
                'nói trong 30 giây đầu</b>, trước cả kiến thức. <span class="vd-pulse">'
                '&#10145;</span> Trước mỗi cuộc gọi, tự hỏi: "Giọng mình đã đủ to, '
                'chắc, có nhiệt chưa?"</p>'
            )
        )

    # ------------------------------------------------------------------
    def _kgn_p2(self, h2, h3, lead):
        def ng(num, c1, c2, title, sai, dung):
            return _card(c1, c2, '&#9889;', 'NGUYÊN TẮC %s &mdash; %s' % (num, title),
                         '<table><thead><tr>'
                         '<th style="width:50%%;color:#dc2626;text-align:center;">&#10060; SAI</th>'
                         '<th style="color:#16a34a;text-align:center;">&#9989; ĐÚNG</th>'
                         '</tr></thead><tbody><tr><td>%s</td><td>%s</td></tr>'
                         '</tbody></table>' % (sai, dung))
        return (
            '<h2 style="' + h2 + '">4 NGUYÊN TẮC GIỌNG NÓI BẮT BUỘC</h2>'
            '<p style="' + lead + '">Áp dụng cho <b>100% cuộc gọi</b> tư vấn khách. '
            'Nhớ kỹ: <b>giọng nói không phải cảm xúc cá nhân &mdash; giọng nói là CÔNG '
            'CỤ BÁN HÀNG</b>. Đã gọi khách thì bắt buộc dùng <b>giọng bán hàng</b>, '
            'không dùng giọng sinh hoạt.</p>'

            + ng('1', '#0369a1', '#0ea5e9', 'NÓI TO HƠN BÌNH THƯỜNG 20&ndash;30%',
                 'Nghĩ mình nói "vừa đủ"; nghĩ nói nhỏ là lịch sự. Tự nghe thấy "vừa '
                 'tai" &rArr; thực tế khách nghe là <b>hơi nhỏ</b>.',
                 'Giọng <b>đủ lực</b>, khách nghe rõ &mdash; chắc &mdash; không phải '
                 'căng tai. Nói to hơn cảm giác của chính mình một chút. <b>Không phải '
                 'hét</b> &mdash; là nói có lực, có độ chắc, có tự tin.')

            + ng('2', '#7c3aed', '#a855f7', 'NÓI NHANH HƠN ĐỜI THƯỜNG',
                 'Nói chậm &rArr; thiếu năng lượng, thiếu chủ động, mất thời gian. '
                 'Khách <b>không kiên nhẫn</b> nghe người nói chậm dù nội dung đúng.',
                 'Nhanh hơn tốc độ nói hàng ngày, nhịp <b>liền mạch</b>, không kéo chữ, '
                 'không ngắt câu vô lý. <b>Nhanh &ne; vội, nhanh &ne; líu</b> &mdash; '
                 'nhanh là <b>chủ động dẫn dắt</b>. Tốc độ nói = mức tự tin khách cảm nhận.')

            + ng('3', '#b45309', '#f59e0b', 'NÓI ĐỀU - KHÔNG VỪA NGHĨ VỪA NÓI',
                 'Các cụm bị CẤM: "Ờ&hellip;", "À thì&hellip;", "Em nghĩ là&hellip;", '
                 '"Để em xem đã&hellip;". Chỉ 1&ndash;2 lần ngập ngừng &rArr; khách đánh '
                 'giá "chưa chắc, chưa chuyên".',
                 '<b>Chưa rõ thì dừng &mdash; sắp câu &mdash; rồi mới nói.</b> Không '
                 'nghĩ đến đâu nói đến đó. Khách không cần biết mình đang nghĩ gì, '
                 'khách chỉ cần nghe <b>câu trả lời chắc chắn</b>.')

            + ng('4', '#15803d', '#22c55e', 'GIỌNG PHẢI CÓ NHIỆT - KHÔNG LẠNH',
                 'Giọng lạnh = không cảm xúc, không nhấn nhá, không sinh khí &rArr; '
                 'khách thấy "sale còn không hào hứng, sao mình phải nghe?".',
                 'Không cần giả vui, không cần diễn &mdash; nhưng bắt buộc <b>có năng '
                 'lượng</b>. Cùng một câu: giọng lạnh &rArr; khách nghe cho xong; giọng '
                 'có nhiệt &rArr; khách <b>sẵn sàng nghe tiếp</b>. Nhiệt đến từ CÁCH nói.')

            + _box('#2563eb', '#eff6ff', '&#9997;&#65039;', 'Tự đánh giá trung thực',
                   '<ul style="margin:0;">'
                   '<li>Tôi có đang nói <b>nhỏ</b> hơn mức chuẩn sale không?</li>'
                   '<li>Tôi có đang nói <b>chậm</b> vì sợ nói sai không?</li>'
                   '<li>Tôi có hay <b>vừa nghĩ vừa nói</b> không?</li>'
                   '<li>Giọng tôi có đang <b>thiếu sinh khí</b> không?</li></ul>'
                   '<p style="margin:8px 0 0;">Nếu CÓ từ 1 câu trở lên &rArr; giọng nói '
                   'hiện tại đang <b>làm giảm tỷ lệ chốt khách</b>.</p>')

            + _chot(
                'Khách không đánh giá tôi qua kiến thức trước, mà đánh giá tôi qua '
                '<b>giọng nói trong 30 giây đầu</b>.'
            )
        )

    # ------------------------------------------------------------------
    def _kgn_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÔNG THỨC GIỌNG NÓI CHUẨN &mdash; chỉ cần nhớ 4 chữ</h2>'
            '<p style="' + lead + '">Đọc &rArr; <b>áp dụng NGAY khi gọi khách</b>. Áp '
            'dụng đúng 4 chữ này, giọng nói tự động chuyên nghiệp hơn <b>70%</b>.</p>'

            + _quad(
                _tile('TO', 'ĐỦ LỰC', 'Khách nghe rõ - chắc. KHÔNG phải hét, KHÔNG gằn giọng.',
                      '#0369a1', '#0ea5e9'),
                _tile('RÕ', 'KHÔNG NUỐT CHỮ', 'Mỗi chữ tròn âm, cuối câu không rơi giọng.',
                      '#7c3aed', '#a855f7'),
                _tile('ĐỀU', 'KHÔNG LUNG TUNG', 'Tốc độ ổn định từ đầu đến cuối, không tụt hơi.',
                      '#b45309', '#f59e0b'),
                _tile('CÓ NHỊP', 'BIẾT DỪNG - NHẤN', 'Nói theo từng cụm ý, nhấn vào từ khóa.',
                      '#15803d', '#22c55e'))

            + _card('#0369a1', '#0ea5e9', '&#128226;', 'TO - nói đủ lực (không phải hét)',
                    '<p style="margin:0;">TO = khách nghe <b>rõ ràng &mdash; chắc chắn</b>. '
                    'TO &ne; hét, TO &ne; gằn giọng. Khi gọi, nói to hơn bình thường '
                    '<b>20&ndash;30%</b>. Nếu tự nghe thấy "vừa tai" &rArr; vẫn là nhỏ. '
                    'Nếu khách phải hỏi lại "Em nói gì cơ?" &rArr; giọng <b>chưa đạt</b>.</p>')

            + _card('#7c3aed', '#a855f7', '&#128172;', 'RÕ - không nuốt chữ',
                    '<p style="margin:0 0 8px;">Sai lầm: nói nhanh nhưng <b>nuốt chữ</b>, '
                    'nói liền không tách âm, cuối câu nhỏ dần &rArr; khách nghe mệt.</p>'
                    '<table><thead><tr><th style="width:50%;color:#dc2626;">&#10060; Sai</th>'
                    '<th style="color:#16a34a;">&#9989; Đúng</th></tr></thead><tbody>'
                    '<tr><td><i>"bênemchuyênxâynhàtrọngói&hellip;"</i></td>'
                    '<td><i>"Bên em chuyên xây nhà trọn gói ạ."</i></td></tr>'
                    '</tbody></table>'
                    '<p style="margin:8px 0 0;">RÕ = khách nghe <b>không cần cố</b>.</p>')

            + _card('#b45309', '#f59e0b', '&#9201;&#65039;', 'ĐỀU - không nhanh chậm lung tung',
                    '<p style="margin:0;">Giọng KHÔNG đều: đầu nói nhanh, gặp đoạn khó '
                    'chậm lại, cuối câu nhỏ dần &rArr; khách thấy sale <b>thiếu chắc '
                    'chắn</b>. Cách làm đơn giản: tưởng tượng mình <b>đang đọc tin tức</b>, '
                    'không phải nói chuyện phiếm. ĐỀU = chuyên nghiệp.</p>')

            + _card('#15803d', '#22c55e', '&#127925;', 'CÓ NHỊP - biết dừng, biết nhấn',
                    '<p style="margin:0 0 8px;">Quan trọng nhất nhưng dễ làm nhất. '
                    '<b>Nhịp = chỗ dừng + chỗ nhấn</b>. Nói theo từng cụm ý, không nói '
                    'một hơi:</p>'
                    '<div style="background:#f0fdf4;border-left:5px solid #22c55e;'
                    'border-radius:10px;padding:12px 14px;font-style:italic;">'
                    '"Bên em chuyên <b>xây nhà trọn gói</b>, &#47;&#47; em gọi để tư vấn '
                    'phương án <b>phù hợp ngân sách</b> &#47;&#47; cho anh chị ạ."</div>'
                    '<p style="margin:8px 0 0;">Dừng nhẹ sau mỗi cụm, nhấn vào từ khóa '
                    '(<b>xây nhà trọn gói</b>, <b>phù hợp ngân sách</b>). Có nhịp = '
                    'khách dễ nghe &mdash; dễ hiểu &mdash; dễ tin.</p>')

            + _apply(
                '<p style="margin-bottom:0;">Nhẩm <b>TO &mdash; RÕ &mdash; ĐỀU &mdash; '
                'CÓ NHỊP</b> ngay trước khi bấm gọi. Chỉ 3 giây, giọng sẽ tự điều chỉnh.</p>'
            )
        )

    # ------------------------------------------------------------------
    def _kgn_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">THỰC HÀNH GIỌNG NÓI BẮT BUỘC (hằng ngày)</h2>'
            '<p style="' + lead + '">Giọng nói <b>không tự tốt lên</b> nếu chỉ đọc lý '
            'thuyết. Giọng chỉ cải thiện khi <b>lặp lại mỗi ngày</b>, dù chỉ vài phút. '
            '100% nhân viên kinh doanh phải luyện <b>5&ndash;10 phút/ngày</b> &mdash; '
            'có khách hay không, bận hay không, vẫn phải luyện.</p>'

            + _card('#0369a1', '#0ea5e9', '&#127908;', '3 BÀI LUYỆN CỐ ĐỊNH MỖI NGÀY',
                    '<table><thead><tr><th style="width:34%;">Bài</th><th>Cách làm</th>'
                    '</tr></thead><tbody>'
                    '<tr><td><b>Bài 1 &mdash; Đọc &amp; ghi âm</b> (3 phút)</td>'
                    '<td>Chọn 1 đoạn tư vấn ~30 giây, đọc thành tiếng, ghi âm. Tự nghe '
                    'lại: Giọng đã TO chưa? Có ĐỀU không? Nghe có buồn ngủ không? &mdash; '
                    '1 câu "chưa" &rArr; đọc lại lần 2.</td></tr>'
                    '<tr><td><b>Bài 2 &mdash; Đọc nhanh hơn 20%</b> (2 phút)</td>'
                    '<td>Đọc lại đúng đoạn đó, tăng tốc ~20%, vẫn rõ chữ, không nuốt âm, '
                    'không líu. Mục tiêu: đánh thức năng lượng giọng. Chỉ cần <b>nhanh '
                    'hơn hôm qua</b>.</td></tr>'
                    '<tr><td><b>Bài 3 &mdash; Gọi nội bộ luyện giọng</b> (2&ndash;5 phút)</td>'
                    '<td>2 người/nhóm, luân phiên 1 gọi &mdash; 1 giả khách. CHỈ nhận xét '
                    'GIỌNG (không nhận xét nội dung, không sửa kịch bản): Nghe rõ không? '
                    'Đều không? Có năng lượng không?</td></tr>'
                    '</tbody></table>')

            + _card('#15803d', '#22c55e', '&#9989;', 'CHUẨN BỊ 30 GIÂY TRƯỚC MỖI CUỘC GỌI THẬT',
                    '<table><thead><tr><th style="width:34%;">Bước</th><th>Làm gì</th>'
                    '</tr></thead><tbody>'
                    '<tr><td><b>1. Tư thế</b></td><td>Ngồi <b>thẳng lưng</b>, hai chân '
                    'chạm đất, không nằm, không ngả ghế. Tư thế sai &rArr; giọng yếu.</td></tr>'
                    '<tr><td><b>2. Nhẩm công thức</b></td><td>Đọc nhanh trong đầu: '
                    '<b>TO &mdash; RÕ &mdash; ĐỀU &mdash; CÓ NHỊP</b>.</td></tr>'
                    '<tr><td><b>3. Thử giọng 1 câu</b></td><td>"Bên em chuyên xây nhà '
                    'trọn gói, em gọi để tư vấn phương án phù hợp ngân sách ạ." Nghe còn '
                    'yếu &rArr; nói lại rồi mới gọi khách.</td></tr>'
                    '</tbody></table>')

            + _box('#dc2626', '#fef2f2', '&#9940;', 'NHỮNG ĐIỀU BỊ CẤM khi gọi khách',
                   '<ul style="margin:0;">'
                   '<li>Vừa gọi vừa làm việc khác (gõ máy, xem điện thoại khác).</li>'
                   '<li>Vừa gọi vừa nằm, dựa ghế.</li>'
                   '<li>Gọi khi giọng đang mệt, chưa khởi động.</li>'
                   '<li>Gọi khách mà chưa thử giọng trước.</li></ul>'
                   '<p style="margin:8px 0 0;">Vi phạm nhiều lần = <b>lỗi hành vi sale</b>.</p>')

            + _advice(
                '<p style="margin-bottom:0;">Dấu hiệu tiến bộ sau <b>3&ndash;5 ngày</b> '
                'luyện đúng: khách nghe máy lâu hơn, phản hồi nhiều hơn, ít bị cúp máy '
                'sớm, cuộc gọi dễ nói chuyện hơn.</p>'
            )

            + _chot(
                'Không có giọng nói tốt trong một ngày, nhưng có giọng nói kém mãi nếu '
                '<b>không luyện mỗi ngày</b>. Luyện giọng = luyện bán hàng.'
            )
        )

    # ------------------------------------------------------------------
    def _kgn_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">QUY ĐỊNH ÁP DỤNG BẮT BUỘC</h2>'
            '<p style="' + lead + '">Đây <b>không phải gợi ý</b>, không phải khuyến '
            'khích. Các quy định này để <b>tránh mất khách, mất hợp đồng, mất thu nhập '
            'cá nhân</b>. Không thực hiện = tự chấp nhận bị thiệt.</p>'

            + '<table><thead><tr><th style="width:38%;">Quy định bắt buộc</th>'
            '<th>Hậu quả nếu KHÔNG làm</th></tr></thead><tbody>'
            '<tr><td><b>1. Tư thế:</b> ngồi thẳng lưng, 2 chân chạm đất, không nằm/ngả ghế</td>'
            '<td>Khách nghe giọng mệt &rArr; mất kiên nhẫn &rArr; cúp máy sớm.</td></tr>'
            '<tr><td><b>2. Tập trung 100%:</b> không vừa gọi vừa làm việc khác</td>'
            '<td>Giọng ngập ngừng, thiếu mạch lạc &rArr; khách thấy "không chuyên, '
            'không tôn trọng mình".</td></tr>'
            '<tr><td><b>3. Khởi động giọng:</b> thử 1 câu + nhẩm TO-RÕ-ĐỀU-CÓ NHỊP</td>'
            '<td>30 giây đầu sai giọng &rArr; khách đã đánh giá xong, nói hay về sau '
            'cũng không cứu được.</td></tr>'
            '<tr><td><b>4. Luyện giọng mỗi ngày</b> 5&ndash;10 phút (không ngoại lệ)</td>'
            '<td>Gọi nhiều nhưng khách không nghe lâu, không phản hồi, không hẹn gặp.</td></tr>'
            '</tbody></table>'

            + _mistake(
                '<p style="margin-bottom:0;">Không luyện giọng dễ sinh tâm lý đổ lỗi: '
                '"khách khó", "thị trường khó", "không có nhu cầu". <b>Thực tế không '
                'phải khách khó &mdash; mà là GIỌNG NÓI YẾU.</b> Cùng data, cùng kịch '
                'bản, người giọng tốt luôn làm được nhiều hơn.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Kết luận phải nhớ</h2>'
            + _formula(
                'Khách quyết định nghe tiếp hay không chỉ trong <b>30 giây đầu</b>. '
                'Giọng <span style="color:#dc2626;">nhỏ / chậm / thiếu năng lượng</span> '
                '&rArr; khách quyết định xong <b>trước khi em nói hết câu đầu tiên</b>. '
                'Vũ khí của em: <b>TO &mdash; RÕ &mdash; ĐỀU &mdash; CÓ NHỊP</b>.'
            )

            + _chot(
                'Không ai cướp khách của bạn &mdash; bạn <b>tự mất khách vì giọng nói '
                'yếu</b>. Không luyện giọng = tự bỏ tiền ra khỏi túi mình.'
            )

            + _apply(
                '<p>Bảng tự kiểm trước MỖI cuộc gọi (Có/Không):</p>'
                '<ol>'
                '<li>Đã ngồi <b>thẳng lưng</b>, hai chân chạm đất chưa?</li>'
                '<li>Đã <b>tắt việc khác</b>, tập trung 100% chưa?</li>'
                '<li>Đã <b>thử giọng 1 câu</b> + nhẩm TO-RÕ-ĐỀU-CÓ NHỊP chưa?</li>'
                '<li>Giọng đã <b>đủ to, có nhiệt</b>, không buồn ngủ chưa?</li>'
                '<li>Hôm nay đã <b>luyện giọng 5&ndash;10 phút</b> chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; sửa ngay trước '
                'khi bấm gọi khách.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    # ==================================================================
    def _vd_kgn_questions(self):
        T, F = True, False
        return [
            ('Khi gọi điện, thứ DUY NHẤT khách cảm nhận được về em là gì?',
             [('Giọng nói', T),
              ('Quần áo em mặc', F),
              ('Quy mô công ty to hay nhỏ', F),
              ('Bằng cấp xây dựng của em', F)]),

            ('Khách hình thành đánh giá về sale trong khoảng thời gian nào?',
             [('10-30 giây đầu tiên', T),
              ('Sau 10 phút nói chuyện', F),
              ('Sau khi gặp mặt trực tiếp', F),
              ('Sau khi xem hồ sơ công ty', F)]),

            ('Khách KHÔNG phân tích logic mà chủ yếu làm gì?',
             [('Khách CẢM - qua giọng to/nhỏ, chắc/run, nhanh/chậm, có nhiệt/buồn ngủ', T),
              ('Khách tính toán số năm kinh nghiệm của sale', F),
              ('Khách tra cứu chuyên môn xây dựng của sale', F),
              ('Khách so sánh bằng cấp các sale', F)]),

            ('Giọng NHỎ khiến khách nghĩ ngay điều gì?',
             [('"Sale này thiếu tự tin"', T),
              ('"Sale này rất chuyên nghiệp"', F),
              ('"Sale này nhiệt tình"', F),
              ('"Công ty này lớn"', F)]),

            ('Giọng "vừa nói vừa nghĩ" (à thì... để em xem...) khiến khách hiểu gì?',
             [('"Chưa chắc - chưa rõ - chưa hiểu việc"', T),
              ('"Sale đang suy nghĩ kỹ cho mình"', F),
              ('"Sale rất cẩn thận"', F),
              ('"Sale có nhiều kinh nghiệm"', F)]),

            ('Vì sao kiểu mất khách do giọng nói là nguy hiểm nhất?',
             [('Khách cúp máy không chửi/phản hồi/phàn nàn nhưng không bao giờ quay lại, sale lại tưởng khách bận', T),
              ('Vì khách sẽ kiện công ty', F),
              ('Vì khách báo xấu lên mạng', F),
              ('Vì khách đòi lại tiền', F)]),

            ('Theo tài liệu, tỷ lệ khách ký hợp đồng vì CẢM GIÁC TIN là bao nhiêu?',
             [('Khoảng 70%', T),
              ('Khoảng 10%', F),
              ('Khoảng 30%', F),
              ('0% - khách chỉ ký vì giá', F)]),

            ('Giọng nói nên được hiểu là gì?',
             [('Là CÔNG CỤ BÁN HÀNG, không phải cảm xúc cá nhân', T),
              ('Là cảm xúc cá nhân, muốn sao cũng được', F),
              ('Là việc của bộ phận đào tạo, không phải của sale', F),
              ('Là yếu tố không quan trọng khi gọi điện', F)]),

            ('Nguyên tắc 1 yêu cầu nói to hơn bình thường bao nhiêu?',
             [('20-30%', T),
              ('200%', F),
              ('Nói càng nhỏ càng lịch sự', F),
              ('Giữ nguyên như nói chuyện đời thường', F)]),

            ('"Nói to" trong giọng sale được hiểu đúng là gì?',
             [('Nói có lực, chắc, tự tin - KHÔNG phải hét, không gằn giọng', T),
              ('Hét thật to vào điện thoại', F),
              ('Gằn giọng cho khách sợ', F),
              ('Nói nhỏ nhẹ cho lịch sự', F)]),

            ('Về tốc độ, chuẩn giọng sale là gì?',
             [('Nhanh hơn nói chuyện đời thường, liền mạch, nhưng nhanh không phải vội/líu', T),
              ('Nói thật chậm để khách nghe kỹ', F),
              ('Nói thật vội và líu cho nhanh xong', F),
              ('Lúc nhanh lúc chậm tùy hứng', F)]),

            ('Những cụm từ nào BỊ CẤM khi gọi khách?',
             [('"Ờ...", "À thì...", "Em nghĩ là...", "Để em xem đã..."', T),
              ('"Bên em chuyên xây nhà trọn gói ạ"', F),
              ('"Dạ vâng em nghe anh chị ạ"', F),
              ('"Em tư vấn phương án phù hợp ngân sách"', F)]),

            ('Khi chưa rõ câu trả lời, nguyên tắc 3 yêu cầu làm gì?',
             [('Dừng - sắp câu - rồi mới nói, không nghĩ đến đâu nói đến đó', T),
              ('Cứ vừa nghĩ vừa nói cho liền mạch', F),
              ('Nói "à thì để em xem" cho khách chờ', F),
              ('Im lặng bỏ cuộc gọi', F)]),

            ('Giọng có NHIỆT khác giọng lạnh ở chỗ nào?',
             [('Không cần giả vui hay diễn, nhưng bắt buộc có năng lượng để khách sẵn sàng nghe tiếp', T),
              ('Phải diễn thật nhiều cảm xúc giả', F),
              ('Phải cười nói liên tục', F),
              ('Giọng lạnh mới chuyên nghiệp', F)]),

            ('Công thức giọng nói chuẩn gồm 4 chữ nào?',
             [('TO - RÕ - ĐỀU - CÓ NHỊP', T),
              ('TO - NHANH - LỚN - MẠNH', F),
              ('NHỎ - CHẬM - ĐỀU - LẠNH', F),
              ('VUI - BUỒN - GIẬN - HỜN', F)]),

            ('Chữ "RÕ" trong công thức nghĩa là gì?',
             [('Mỗi chữ tròn âm, cuối câu không rơi giọng, không nuốt chữ', T),
              ('Nói thật to như hét', F),
              ('Nói thật nhanh cho xong', F),
              ('Nói nhỏ dần ở cuối câu', F)]),

            ('Chữ "CÓ NHỊP" được áp dụng thế nào?',
             [('Nói theo từng cụm ý, dừng nhẹ sau mỗi cụm và nhấn vào từ khóa', T),
              ('Nói một hơi không ngừng', F),
              ('Đọc đều đều như máy không nhấn nhá', F),
              ('Ngắt câu vô lý ở giữa từ', F)]),

            ('Trước mỗi cuộc gọi thật, 3 bước chuẩn bị 30 giây là gì?',
             [('Tư thế (ngồi thẳng) - Nhẩm công thức TO-RÕ-ĐỀU-CÓ NHỊP - Thử giọng 1 câu', T),
              ('Uống nước - Mở nhạc - Nằm thư giãn', F),
              ('Xem điện thoại - Trả lời tin nhắn - Rồi gọi', F),
              ('Gọi luôn không cần chuẩn bị', F)]),

            ('Tư thế gọi điện bắt buộc là gì?',
             [('Ngồi thẳng lưng, hai chân chạm đất, không nằm, không ngả ghế', T),
              ('Nằm dài cho thoải mái', F),
              ('Ngả lưng dựa ghế thư giãn', F),
              ('Tư thế nào cũng được, không ảnh hưởng giọng', F)]),

            ('Câu nhân viên phải ghi nhớ cuối khóa là gì?',
             [('"Không ai cướp khách của bạn, bạn tự mất khách vì giọng nói yếu; không luyện giọng = tự bỏ tiền khỏi túi"', T),
              ('"Khách khó nên không chốt được là bình thường"', F),
              ('"Giọng nói không quan trọng bằng giá rẻ"', F),
              ('"Cứ gọi nhiều ắt có khách, không cần luyện giọng"', F)]),
        ]
