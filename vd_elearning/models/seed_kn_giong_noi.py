# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa "KỸ NĂNG GIỌNG NÓI" (Kỹ năng Sale).

Bám SÁT tài liệu gốc (Giọng nói.txt - sếp Hinh): GIỮ NGUYÊN cấu trúc 5 PHẦN và
mọi mục con, KHÔNG cắt nội dung. Trình bày sạch - chuyên nghiệp: banner CHƯƠNG
(PHẦN 1..5), tiêu đề mục con, câu trích in nghiêng, bảng so sánh, 4 ô công thức
TO-RÕ-ĐỀU-CÓ NHỊP, và các khung khung chuẩn (công thức / áp dụng / tình huống /
lời khuyên / sai lầm / câu chốt).

Khóa KHÔNG có ảnh nguồn => thiết kế typography lớn thay ảnh. Hiệu ứng toàn khóa
qua khối <style> (quét sáng tiêu đề, trồi lên, hover ô công thức).

Channel "Kỹ năng giọng nói" TẠO QUA UI (id 22, không có xmlid) => seed TÌM THEO
TÊN. Helper riêng prefix _kgn_ (xem reference-seed-method-name-collision).
Idempotent theo PHIÊN BẢN. LƯU Ý bẫy %: % literal trong NỘI DUNG để 1 dấu; chỉ
escape %% bên trong các hàm helper có dùng '...' % (...).
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_KGN_VERSION = 'v2'
_PARAM_KEY = 'vd_elearning.kn_giong_noi_seed_version'

# ---------------------------------------------------------------------------
#  HIỆU ỨNG TOÀN KHÓA (nối chuỗi thuần - KHÔNG dùng % format -> % an toàn)
# ---------------------------------------------------------------------------
_STYLE = (
    '<style>'
    '.vd-kgn .vd-hero{position:relative;overflow:hidden;}'
    '.vd-kgn .vd-hero::after{content:"";position:absolute;top:0;left:-65%;'
    'width:45%;height:100%;background:linear-gradient(120deg,'
    'rgba(255,255,255,0) 0%,rgba(255,255,255,.5) 50%,rgba(255,255,255,0) 100%);'
    'transform:skewX(-22deg);animation:vdShine 3.6s ease-in-out infinite;}'
    '.vd-kgn .vd-phan{animation:vdRise .6s ease both;}'
    '.vd-kgn .vd-tile{transition:transform .3s ease,box-shadow .3s ease;}'
    '.vd-kgn .vd-tile:hover{transform:translateY(-6px);'
    'box-shadow:0 18px 40px rgba(2,6,23,.30);}'
    '.vd-kgn table{border-collapse:collapse;width:100%;margin:6px 0 4px;}'
    '.vd-kgn .vd-pulse{display:inline-block;animation:vdPulse 1.5s ease-in-out infinite;}'
    '@keyframes vdShine{0%{left:-65%}55%{left:135%}100%{left:135%}}'
    '@keyframes vdRise{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}'
    '@keyframes vdPulse{0%,100%{transform:translateX(0)}50%{transform:translateX(7px)}}'
    '</style>'
)


def _hero(title_small, title_big, sub):
    """Tiêu đề SIÊU LỚN đầu khóa - đỏ cam thương hiệu + quét sáng."""
    return (
        '<div class="vd-hero" style="background:linear-gradient(135deg,'
        '#f5523c 0%%,#d62f12 100%%);border-radius:22px;padding:44px 28px;'
        'margin:4px 0 8px;text-align:center;'
        'box-shadow:0 16px 40px rgba(214,47,18,.40);">'
        '<div style="color:#ffe6df;font-size:17px;font-weight:800;letter-spacing:4px;'
        'text-transform:uppercase;margin-bottom:10px;">%s</div>'
        '<div style="color:#ffffff;font-size:58px;font-weight:900;line-height:1.04;'
        'letter-spacing:1px;text-shadow:0 3px 10px rgba(0,0,0,.28);">%s</div>'
        '<div style="color:#fff4f0;font-size:17px;font-weight:600;margin-top:16px;'
        'max-width:800px;margin-left:auto;margin-right:auto;">%s</div></div>'
    ) % (title_small, title_big, sub)


def _phan(num, title, sub):
    """Banner CHƯƠNG (PHẦN N) - nền slate sang, số mờ lớn phía sau."""
    return (
        '<div class="vd-phan" style="position:relative;overflow:hidden;'
        'background:linear-gradient(135deg,#1e293b 0%%,#334155 100%%);'
        'border-radius:18px;padding:24px 28px;margin:36px 0 20px;'
        'box-shadow:0 12px 30px rgba(2,6,23,.24);">'
        '<div style="position:absolute;right:18px;top:-26px;font-size:130px;'
        'font-weight:900;color:rgba(255,255,255,.07);line-height:1;">%s</div>'
        '<div style="position:relative;color:#fbbf24;font-size:15px;font-weight:800;'
        'letter-spacing:3px;text-transform:uppercase;">PHẦN %s</div>'
        '<div style="position:relative;color:#ffffff;font-size:27px;font-weight:900;'
        'margin-top:4px;line-height:1.18;">%s</div>'
        '<div style="position:relative;color:#cbd5e1;font-size:14.5px;font-weight:600;'
        'margin-top:8px;">%s</div></div>'
    ) % (num, num, title, sub)


def _h(title):
    """Tiêu đề MỤC CON - thanh đỏ bên trái, chữ đậm."""
    return ('<h3 style="font-size:18px;font-weight:900;color:#0f172a;'
            'margin:24px 0 10px;padding-left:14px;'
            'border-left:5px solid #e8401f;">%s</h3>') % title


def _quote(text):
    """Câu trích dạy nghề (in nghiêng) - khung đỏ nhạt sang."""
    return ('<div style="border-left:5px solid #e8401f;background:#fff7f5;'
            'border-radius:0 12px 12px 0;padding:14px 18px;margin:14px 0;'
            'font-size:16.5px;font-style:italic;color:#7f1d1d;font-weight:600;">'
            '&#128172; %s</div>') % text


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
    return ('<div style="display:flex;flex-wrap:wrap;gap:16px;margin:18px 0;'
            'justify-content:center;">%s</div>') % ''.join(tiles)


def _vs(sai, dung):
    """Bảng 2 cột SAI (đỏ) / ĐÚNG (xanh)."""
    return ('<table><thead><tr>'
            '<th style="width:50%%;color:#dc2626;text-align:left;'
            'border-bottom:2px solid #fecaca;padding:6px 10px;">&#10060; SAI</th>'
            '<th style="color:#16a34a;text-align:left;'
            'border-bottom:2px solid #bbf7d0;padding:6px 10px;">&#9989; ĐÚNG</th>'
            '</tr></thead><tbody><tr>'
            '<td style="vertical-align:top;padding:8px 10px;background:#fef2f2;">%s</td>'
            '<td style="vertical-align:top;padding:8px 10px;background:#f0fdf4;">%s</td>'
            '</tr></tbody></table>') % (sai, dung)


class SlideChannelSeedKnGiongNoi(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_kn_giong_noi(self):
        ch = self.sudo().search([('name', 'ilike', 'giọng nói')], limit=1)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _KGN_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        merged = ''.join(body for _title, body in self._vd_kgn_pages())
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
    #  NỘI DUNG (đủ 5 PHẦN bám sát file gốc)
    # ==================================================================
    def _vd_kgn_pages(self):
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;line-height:1.7;'
        return [
            ('Hero', self._kgn_hero(lead)),
            ('P1', self._kgn_p1(lead)),
            ('P2', self._kgn_p2(lead)),
            ('P3', self._kgn_p3(lead)),
            ('P4', self._kgn_p4(lead)),
            ('P5', self._kgn_p5(lead)),
        ]

    def _kgn_hero(self, lead):
        return _hero(
            'Kỹ năng Sale &mdash; Gọi điện', 'KỸ NĂNG GIỌNG NÓI',
            'Khi gọi điện, khách KHÔNG thấy mặt em, không thấy công ty &mdash; thứ '
            'DUY NHẤT khách cảm nhận là GIỌNG NÓI. Cả khóa gói gọn trong 4 chữ: '
            'TO &mdash; RÕ &mdash; ĐỀU &mdash; CÓ NHỊP.')

    # ------------------------------------------------------------------
    #  PHẦN 1 — NHẬN DIỆN VẤN ĐỀ
    # ------------------------------------------------------------------
    def _kgn_p1(self, lead):
        return (
            _phan('1', 'NHẬN DIỆN VẤN ĐỀ',
                  'Giọng nói đang là thứ làm các em MẤT KHÁCH mà không hề biết.')

            + _h('1. Sự thật đầu tiên &mdash; Khách KHÔNG hề thấy mặt các em')
            + _quote('Khi gọi điện cho khách: khách không nhìn thấy quần áo các em, '
                     'không thấy thái độ các em, không thấy công ty các em to hay nhỏ.')
            + '<p style="' + lead + '">&#128073; Thứ <b>DUY NHẤT</b> khách cảm nhận '
            'được là <b>GIỌNG NÓI</b>. Và trong đầu khách sẽ hình thành đánh giá '
            'chỉ sau <b>10&ndash;30 giây đầu tiên</b>.</p>'

            + _h('2. Khách KHÔNG phân tích &mdash; Khách CẢM NHẬN')
            + '<p style="' + lead + '">Khách không ngồi phân tích logic xem: em có '
            'học xây dựng không, em có kinh nghiệm không, công ty em bao nhiêu năm. '
            '&#128073; Khách chỉ <b>CẢM</b>. Và khách cảm qua những thứ này:</p>'
            + '<table><tbody>'
            '<tr><td style="padding:6px 10px;">&#128266; Giọng <b>to</b> hay <b>nhỏ</b></td>'
            '<td style="padding:6px 10px;">&#128170; Giọng <b>chắc</b> hay <b>run</b></td></tr>'
            '<tr><td style="padding:6px 10px;">&#9889; Giọng <b>nhanh gọn</b> hay <b>chậm chạp</b></td>'
            '<td style="padding:6px 10px;">&#128293; Giọng <b>có năng lượng</b> hay <b>buồn ngủ</b></td></tr>'
            '</tbody></table>'

            + _h('3. 4 kiểu giọng đang GIẾT sale')
            + '<table><thead><tr>'
            '<th style="width:44%;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Kiểu giọng</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Khách nghĩ ngay trong đầu</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:8px 10px;">&#10060; <b>Giọng nhỏ</b></td>'
            '<td style="padding:8px 10px;">&#8220;Sale này thiếu tự tin.&#8221;</td></tr>'
            '<tr><td style="padding:8px 10px;">&#10060; <b>Giọng chậm</b></td>'
            '<td style="padding:8px 10px;">&#8220;Không chuyên nghiệp &mdash; nói chuyện mất thời gian.&#8221;</td></tr>'
            '<tr><td style="padding:8px 10px;">&#10060; <b>Vừa nói vừa nghĩ</b><br/>'
            '<span style="color:#94a3b8;">(&#8220;à thì&hellip; để em xem&hellip; em nghĩ là&hellip;&#8221;)</span></td>'
            '<td style="padding:8px 10px;">&#8220;Chưa chắc &mdash; chưa rõ &mdash; chưa hiểu việc.&#8221;</td></tr>'
            '<tr><td style="padding:8px 10px;">&#10060; <b>Giọng buồn ngủ, không nhiệt</b></td>'
            '<td style="padding:8px 10px;">&#8220;Chính sale còn không hào hứng, sao tôi phải nghe?&#8221;</td></tr>'
            '</tbody></table>'
            + '<p style="font-size:16px;color:#b91c1c;font-weight:800;margin:10px 0;">'
            '&#128683; Khách KHÔNG nói ra, nhưng khách CÚP MÁY.</p>'

            + _h('4. Điều nguy hiểm nhất: Sale KHÔNG biết mình đang yếu')
            + _quote('Các em không mất khách vì thiếu kiến thức, mà mất khách vì '
                     'giọng nói làm khách không muốn nghe tiếp.')
            + '<p style="' + lead + '">Khách cúp máy: <b>không chửi &mdash; không phản '
            'hồi &mdash; không phàn nàn</b>, nhưng <b>không bao giờ quay lại</b>. Đây '
            'là kiểu mất khách nguy hiểm nhất, vì sale tưởng &#8220;chắc khách bận&#8221;, '
            '&#8220;chắc khách chưa có nhu cầu&#8221;. &#128073; <b>KHÔNG PHẢI &mdash; '
            'là do GIỌNG NÓI.</b></p>'

            + _h('5. So sánh để các bạn thấy ĐAU')
            + _quote('Hai công ty giống nhau 100%: giá giống nhau, dịch vụ giống nhau, '
                     'hồ sơ giống nhau &mdash; công ty nào có sale GIỌNG NÓI TỰ TIN hơn '
                     'thì công ty đó ký được hợp đồng.')
            + _formula(
                'Trong thực tế: <b>70% khách KHÔNG ký vì lý do chuyên môn</b> &mdash; '
                '<b>70% khách ký vì CẢM GIÁC TIN</b>. Và '
                '<span style="color:#dc2626;">giọng nói</span> là thứ tạo cảm giác '
                'tin <b>nhanh nhất</b>.')

            + _h('6. Chốt một câu để các bạn NHỚ')
            + _chot('Giọng nói yếu = Khách đánh giá công ty yếu = Khách <b>không giao '
                    'nhà trăm triệu &mdash; hàng tỷ</b> cho mình. Đây không phải kỹ '
                    'năng phụ &mdash; đây là <b>KỸ NĂNG SỐNG CÒN</b> của sale gọi điện.')

            + _apply(
                '<p style="margin-bottom:0;">Khách đánh giá em qua <b>giọng nói trong '
                '30 giây đầu</b>, trước cả kiến thức. <span class="vd-pulse">&#10145;'
                '</span> Trước mỗi cuộc gọi, tự hỏi: &#8220;Giọng mình đã đủ to, chắc, '
                'có nhiệt chưa?&#8221;</p>')
        )

    # ------------------------------------------------------------------
    #  PHẦN 2 — 4 NGUYÊN TẮC GIỌNG NÓI BẮT BUỘC
    # ------------------------------------------------------------------
    def _kgn_p2(self, lead):
        return (
            _phan('2', '4 NGUYÊN TẮC GIỌNG NÓI BẮT BUỘC',
                  'Áp dụng cho 100% cuộc gọi tư vấn khách hàng.')

            + _box('#2563eb', '#eff6ff', '&#128221;', 'Lưu ý trước khi đọc',
                   '<p style="margin-bottom:0;">Giọng nói <b>không phải cảm xúc cá '
                   'nhân</b>. Giọng nói là <b>CÔNG CỤ BÁN HÀNG</b>. Đã gọi cho khách '
                   '&rArr; bắt buộc dùng <b>giọng bán hàng</b>, không dùng giọng '
                   'sinh hoạt.</p>')

            + _h('NGUYÊN TẮC 1 &mdash; Nói TO hơn bình thường 20&ndash;30%')
            + _vs(
                'Nghĩ rằng mình nói &#8220;vừa đủ&#8221;.<br/>Nghĩ rằng nói nhỏ là '
                'lịch sự.<br/>Nghĩ rằng khách nghe rõ là được. &rArr; Tất cả đều sai.',
                '<b>Giọng phải đủ lực</b>, khách nghe rõ &mdash; chắc &mdash; không '
                'phải căng tai. Nói <b>to hơn cảm giác của chính mình một chút</b>.')
            + '<p style="' + lead + '"><b>Quy tắc tự kiểm tra:</b> nếu tự nghe lại '
            'thấy &#8220;vừa tai&#8221; &rArr; thực tế khách nghe sẽ là <b>hơi nhỏ</b>. '
            '&#9888;&#65039; Không phải hét &mdash; là nói <b>có lực, có độ chắc, có '
            'tự tin</b>.</p>'

            + _h('NGUYÊN TẮC 2 &mdash; Nói NHANH hơn nói chuyện đời thường')
            + _vs(
                'Nói chậm tạo cảm giác: thiếu năng lượng, thiếu chủ động, mất thời '
                'gian. &rArr; Khách không kiên nhẫn nghe người nói chậm, dù nội dung đúng.',
                'Nhanh hơn tốc độ nói hàng ngày, <b>nhịp nói liền mạch</b>, không kéo '
                'chữ, không ngắt câu vô lý.')
            + '<p style="' + lead + '">&#9888;&#65039; <b>Nhanh &ne; vội. Nhanh &ne; '
            'líu.</b> Nhanh là <b>chủ động dẫn dắt</b> cuộc nói chuyện. &#128073; '
            'Tốc độ nói = mức độ tự tin mà khách cảm nhận.</p>'

            + _h('NGUYÊN TẮC 3 &mdash; Nói ĐỀU, tuyệt đối không &#8220;vừa nghĩ vừa nói&#8221;')
            + _box('#dc2626', '#fef2f2', '&#9940;', 'Những cụm từ bị CẤM tuyệt đối khi gọi khách',
                   '<p style="margin:0;font-size:16px;">&#8220;Ờ&hellip;&#8221; &nbsp;&middot;&nbsp; '
                   '&#8220;À thì&hellip;&#8221; &nbsp;&middot;&nbsp; &#8220;Em nghĩ '
                   'là&hellip;&#8221; &nbsp;&middot;&nbsp; &#8220;Để em xem đã&hellip;&#8221; '
                   '&nbsp;&middot;&nbsp; &#8220;Cái này thì&hellip;&#8221;</p>')
            + '<p style="' + lead + '">Chỉ cần <b>1&ndash;2 lần ngập ngừng</b>, khách '
            'sẽ tự đánh giá: &#8220;Sale này chưa chắc &mdash; chưa hiểu rõ &mdash; '
            'chưa chuyên&#8221;.</p>'
            + _advice(
                '<p style="margin-bottom:0;"><b>Quy tắc bắt buộc:</b> chưa rõ thì '
                '<b>dừng &mdash; sắp câu &mdash; rồi mới nói</b>. Không nghĩ đến đâu '
                'nói đến đó. Không để khách nghe thấy mình đang phân vân. Khách không '
                'cần biết mình đang nghĩ gì &mdash; khách chỉ cần nghe <b>câu trả lời '
                'chắc chắn</b>.</p>')

            + _h('NGUYÊN TẮC 4 &mdash; Giọng phải CÓ NHIỆT, không được lạnh')
            + _vs(
                '<b>Giọng lạnh</b> là: không cảm xúc, không nhấn nhá, không sinh khí. '
                '&rArr; Khách thấy &#8220;sale còn không hào hứng, sao mình phải nghe?&#8221;',
                'Không cần giả vui, không cần diễn &mdash; nhưng <b>bắt buộc phải có '
                'năng lượng</b>. Cùng một câu: giọng lạnh &rArr; khách nghe cho xong; '
                'giọng có nhiệt &rArr; khách <b>sẵn sàng nghe tiếp</b>.')
            + '<p style="' + lead + '">&#128073; Nhiệt không đến từ lời nói, mà đến '
            'từ <b>CÁCH nói</b>.</p>'

            + _box('#9333ea', '#faf5ff', '&#9997;&#65039;', 'Tự đánh giá sau khi đọc phần này',
                   '<ul style="margin:0;">'
                   '<li>Tôi có đang nói <b>nhỏ</b> hơn mức chuẩn sale không?</li>'
                   '<li>Tôi có đang nói <b>chậm</b> vì sợ nói sai không?</li>'
                   '<li>Tôi có hay <b>vừa nghĩ vừa nói</b> không?</li>'
                   '<li>Giọng tôi có đang <b>thiếu sinh khí</b> không?</li></ul>'
                   '<p style="margin:8px 0 0;">&#128073; Nếu <b>CÓ từ 1 câu trở lên</b> '
                   '&rArr; giọng nói hiện tại đang <b>làm giảm tỷ lệ chốt khách</b>.</p>')

            + _chot('Khách không đánh giá tôi qua kiến thức trước, mà đánh giá tôi qua '
                    '<b>GIỌNG NÓI trong 30 giây đầu</b>.')
        )

    # ------------------------------------------------------------------
    #  PHẦN 3 — CÔNG THỨC GIỌNG NÓI CHUẨN
    # ------------------------------------------------------------------
    def _kgn_p3(self, lead):
        return (
            _phan('3', 'CÔNG THỨC GIỌNG NÓI CHUẨN',
                  'Đọc &rarr; áp dụng NGAY khi gọi khách. Chỉ cần nhớ 4 chữ.')

            + _formula(
                'Chỉ cần nhớ 4 chữ: <span style="font-size:20px;">TO &mdash; RÕ '
                '&mdash; ĐỀU &mdash; CÓ NHỊP</span>. Áp dụng đúng 4 chữ này &rArr; '
                'giọng nói tự động chuyên nghiệp hơn <b>70%</b>.')

            + _quad(
                _tile('TO', 'ĐỦ LỰC', 'Khách nghe rõ - chắc. KHÔNG phải hét, KHÔNG gằn giọng.',
                      '#0369a1', '#0ea5e9'),
                _tile('RÕ', 'KHÔNG NUỐT CHỮ', 'Mỗi chữ tròn âm, cuối câu không rơi giọng.',
                      '#7c3aed', '#a855f7'),
                _tile('ĐỀU', 'KHÔNG LUNG TUNG', 'Tốc độ ổn định từ đầu đến cuối, không tụt hơi.',
                      '#b45309', '#f59e0b'),
                _tile('CÓ NHỊP', 'BIẾT DỪNG - NHẤN', 'Nói theo từng cụm ý, nhấn vào từ khóa.',
                      '#15803d', '#22c55e'))

            + _h('1. TO &mdash; Nói đủ lực (KHÔNG phải hét)')
            + '<p style="' + lead + '"><b>Hiểu đúng chữ &#8220;TO&#8221;:</b> TO = '
            'khách nghe rõ ràng &mdash; chắc chắn. TO &ne; hét. TO &ne; gằn giọng.</p>'
            + '<p style="' + lead + '"><b>Cách áp dụng NGAY:</b> khi gọi khách, nói '
            'to hơn bình thường <b>20&ndash;30%</b>. Nếu tự nghe lại thấy &#8220;vừa '
            'tai&#8221; &rArr; vẫn là nhỏ. <b>Tự kiểm tra:</b> nếu khách phải hỏi lại '
            '&#8220;Em nói gì cơ?&#8221; &rArr; giọng chưa đạt chuẩn TO. &#128073; '
            'Giọng TO = giọng của người tự tin.</p>'

            + _h('2. RÕ &mdash; Không nuốt chữ')
            + _vs(
                'Nói nhanh nhưng <b>nuốt chữ</b>.<br/>Nói liền không tách âm.<br/>'
                'Cuối câu nói nhỏ dần. &rArr; Khách nghe mệt, dù không nói ra.',
                'Mỗi chữ phải <b>tròn âm</b>.<br/>Cuối câu <b>không rơi giọng</b>.<br/>'
                'Không &#8220;lướt&#8221; chữ cho nhanh.')
            + '<table><thead><tr>'
            '<th style="width:50%;text-align:left;padding:6px 10px;color:#dc2626;">&#10060; Sai</th>'
            '<th style="text-align:left;padding:6px 10px;color:#16a34a;">&#9989; Đúng</th>'
            '</tr></thead><tbody><tr>'
            '<td style="padding:8px 10px;background:#fef2f2;font-style:italic;">&#8220;bênemchuyênxâynhàtrọngói&hellip;&#8221;</td>'
            '<td style="padding:8px 10px;background:#f0fdf4;font-style:italic;">&#8220;Bên em chuyên xây nhà trọn gói ạ.&#8221;</td>'
            '</tr></tbody></table>'
            + '<p style="' + lead + '">&#128073; RÕ = khách nghe <b>không cần cố</b>.</p>'

            + _h('3. ĐỀU &mdash; Không nhanh chậm lung tung')
            + _vs(
                'Lúc đầu nói nhanh.<br/>Gặp đoạn khó &rarr; nói chậm lại.<br/>Cuối câu '
                'nhỏ dần. &rArr; Khách cảm nhận ngay: sale thiếu chắc chắn.',
                'Tốc độ <b>ổn định</b> từ đầu đến cuối.<br/>Không &#8220;tụt hơi&#8221; '
                'giữa chừng.<br/>Không kéo dài câu vô lý.')
            + '<p style="' + lead + '"><b>Cách làm đơn giản:</b> tưởng tượng mình đang '
            '<b>đọc tin tức</b>, không phải đang nói chuyện phiếm. &#128073; ĐỀU = '
            'chuyên nghiệp.</p>'

            + _h('4. CÓ NHỊP &mdash; Biết dừng, biết nhấn')
            + '<p style="' + lead + '">Đây là phần <b>quan trọng nhất</b>, nhưng lại '
            '<b>dễ làm nhất</b>. <b>Nhịp = chỗ dừng + chỗ nhấn.</b> Quy tắc nhớ nhanh: '
            '<b>nói theo từng cụm ý, không nói một hơi</b>.</p>'
            + '<div style="background:#f0fdf4;border-left:5px solid #22c55e;'
            'border-radius:0 12px 12px 0;padding:14px 18px;margin:12px 0;'
            'font-size:16.5px;font-style:italic;color:#14532d;">'
            '&#8220;Bên em chuyên <b>xây nhà trọn gói</b>, &#47;&#47; em gọi để tư vấn '
            'phương án <b>phù hợp ngân sách</b> &#47;&#47; cho anh chị ạ.&#8221;</div>'
            + '<p style="' + lead + '">Dừng nhẹ sau mỗi cụm, nhấn vào từ khóa '
            '(<b>xây nhà trọn gói</b>, <b>phù hợp ngân sách</b>). &#128073; Có nhịp = '
            'khách <b>dễ nghe &mdash; dễ hiểu &mdash; dễ tin</b>.</p>'

            + _apply('<p style="margin-bottom:0;">Nhẩm <b>TO &mdash; RÕ &mdash; ĐỀU '
                     '&mdash; CÓ NHỊP</b> ngay trước khi bấm gọi. Chỉ 3 giây, giọng '
                     'sẽ tự điều chỉnh.</p>')
        )

    # ------------------------------------------------------------------
    #  PHẦN 4 — THỰC HÀNH GIỌNG NÓI BẮT BUỘC
    # ------------------------------------------------------------------
    def _kgn_p4(self, lead):
        return (
            _phan('4', 'THỰC HÀNH GIỌNG NÓI BẮT BUỘC',
                  'Áp dụng hằng ngày &mdash; Không được bỏ qua.')

            + _box('#2563eb', '#eff6ff', '&#128221;', 'Lưu ý quan trọng',
                   '<p style="margin-bottom:0;">Giọng nói <b>không tự tốt lên</b> nếu '
                   'chỉ đọc lý thuyết. Giọng nói chỉ cải thiện khi <b>lặp lại mỗi '
                   'ngày</b>, dù chỉ vài phút.</p>')

            + _h('A. Quy định thực hành hằng ngày (BẮT BUỘC)')
            + '<p style="' + lead + '"><b>100% nhân viên kinh doanh phải luyện giọng '
            'mỗi ngày</b>, không phụ thuộc: có khách hay không, có bận hay không. '
            'Thời gian luyện: <b>5&ndash;10 phút/ngày</b>. &#128073; Không luyện = '
            'giọng yếu = mất khách.</p>'

            + _h('B. Bài thực hành cố định mỗi ngày (5&ndash;10 phút)')
            + '<table><thead><tr>'
            '<th style="width:36%;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Bài</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Cách làm</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:8px 10px;"><b>Bài 1 &mdash; Đọc &amp; ghi âm</b><br/>'
            '<span style="color:#94a3b8;">(3 phút)</span></td>'
            '<td style="padding:8px 10px;">Chọn 01 đoạn tư vấn chuẩn (~30 giây), đọc '
            'thành tiếng, ghi âm bằng điện thoại. Tự nghe lại và trả lời: Giọng đã TO '
            'chưa? Có ĐỀU không? Nghe có buồn ngủ không? &rArr; Nếu 1 câu trả lời '
            '&#8220;CHƯA&#8221; thì đọc lại lần 2.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>Bài 2 &mdash; Đọc nhanh hơn 20%</b><br/>'
            '<span style="color:#94a3b8;">(2 phút)</span></td>'
            '<td style="padding:8px 10px;">Đọc lại đúng đoạn vừa đọc, tăng tốc độ '
            '~20%, vẫn giữ: rõ chữ, không nuốt âm, không líu. Mục tiêu: đánh thức năng '
            'lượng giọng, tránh giọng chậm &mdash; rề rà &mdash; buồn ngủ. '
            '&#9888;&#65039; Không cần hoàn hảo, chỉ cần nhanh hơn hôm qua.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>Bài 3 &mdash; Gọi nội bộ luyện giọng</b><br/>'
            '<span style="color:#94a3b8;">(2&ndash;5 phút)</span></td>'
            '<td style="padding:8px 10px;">2 người/1 nhóm, luân phiên: 1 người gọi '
            '&mdash; 1 người giả làm khách. <b>CHỈ nhận xét GIỌNG</b> (tuyệt đối không '
            'nhận xét nội dung, không sửa kịch bản). Chỉ trả lời 3 câu: Nghe có rõ '
            'không? Có đều không? Có năng lượng không? &rArr; Mỗi người 1&ndash;2 phút '
            'là đủ.</td></tr>'
            '</tbody></table>'

            + _h('C. Chuẩn bị BẮT BUỘC trước mỗi cuộc gọi thật (30 giây)')
            + '<table><thead><tr>'
            '<th style="width:30%;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Bước</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Làm gì</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:8px 10px;"><b>Bước 1 &mdash; Tư thế</b></td>'
            '<td style="padding:8px 10px;">Ngồi <b>thẳng lưng</b>, hai chân chạm đất, '
            'không nằm, không ngả ghế. &rArr; Tư thế sai thì giọng yếu.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>Bước 2 &mdash; Nhẩm công thức</b></td>'
            '<td style="padding:8px 10px;">Trong đầu đọc nhanh: <b>TO &mdash; RÕ '
            '&mdash; ĐỀU &mdash; CÓ NHỊP</b>. Chỉ cần 3 giây, giọng sẽ tự điều chỉnh.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>Bước 3 &mdash; Thử giọng 1 câu</b></td>'
            '<td style="padding:8px 10px;">Nói thử: &#8220;Bên em chuyên xây nhà trọn '
            'gói, em gọi để tư vấn phương án phù hợp ngân sách ạ.&#8221; &rArr; Nếu '
            'nghe còn yếu thì nói lại lần nữa rồi mới gọi khách.</td></tr>'
            '</tbody></table>'

            + _h('D. Thực hành với AI?')
            + '<p style="' + lead + '">Ưu tiên theo thứ tự: <b>(1) Đồng nghiệp trong '
            'nhóm &rarr; (2) Trưởng nhóm &rarr; (3) Tự ghi âm &mdash; tự nghe lại</b> '
            '(nếu không có ai). &#128073; Không có lý do &#8220;không có người luyện '
            'cùng&#8221;.</p>'

            + _h('E. Những điều BỊ CẤM khi gọi khách')
            + _box('#dc2626', '#fef2f2', '&#9940;', 'Tuyệt đối không',
                   '<ul style="margin:0;">'
                   '<li>Vừa gọi vừa làm việc khác.</li>'
                   '<li>Vừa gọi vừa nằm, dựa ghế.</li>'
                   '<li>Gọi khi giọng đang mệt, chưa khởi động.</li>'
                   '<li>Gọi khách mà chưa thử giọng trước.</li></ul>'
                   '<p style="margin:8px 0 0;">&#128073; Vi phạm nhiều lần = <b>lỗi '
                   'hành vi sale</b>.</p>')

            + _h('F. Dấu hiệu biết mình đang tiến bộ')
            + _advice('<p style="margin-bottom:0;">Sau <b>3&ndash;5 ngày</b> luyện '
                      'đúng cách: khách nghe máy lâu hơn, khách phản hồi nhiều hơn, ít '
                      'bị cúp máy sớm, cuộc gọi dễ nói chuyện hơn. &#128073; Đó là dấu '
                      'hiệu giọng nói đang phát huy tác dụng.</p>')

            + _chot('Không có giọng nói tốt trong một ngày, nhưng có giọng nói KÉM MÃI '
                    'nếu không luyện mỗi ngày. <b>Luyện giọng = luyện bán hàng.</b>')
        )

    # ------------------------------------------------------------------
    #  PHẦN 5 — QUY ĐỊNH ÁP DỤNG BẮT BUỘC
    # ------------------------------------------------------------------
    def _kgn_p5(self, lead):
        def hq(text):
            return ('<div style="color:#b91c1c;font-weight:700;margin-top:6px;">'
                    '&#9888;&#65039; Hậu quả nếu không làm: %s</div>') % text
        return (
            _phan('5', 'QUY ĐỊNH ÁP DỤNG BẮT BUỘC',
                  'Không phải gợi ý &mdash; không phải khuyến khích.')

            + _box('#dc2626', '#fef2f2', '&#9888;&#65039;', 'Lưu ý quan trọng',
                   '<p style="margin-bottom:0;">Các quy định dưới đây không nhằm làm '
                   'khó nhân viên, mà để <b>tránh mất khách, mất hợp đồng, mất thu '
                   'nhập cá nhân</b>. Không thực hiện = tự chấp nhận bị thiệt.</p>')

            + _h('I. Quy định bắt buộc khi gọi khách hàng')
            + '<p style="' + lead + '"><b>1. Tư thế gọi điện (bắt buộc):</b> ngồi '
            '<b>thẳng lưng</b>, hai chân chạm đất, không nằm, không ngả ghế, không dựa '
            'lưng thoải mái. Vì sao? Tư thế sai &rarr; giọng yếu &rarr; khách cảm nhận '
            'sale thiếu tự tin.' + hq('khách nghe giọng mệt, mất kiên nhẫn, cúp máy '
            'sớm &rarr; sale mất cơ hội nói tiếp dù nội dung đúng.') + '</p>'
            + '<p style="' + lead + '"><b>2. Tập trung 100% khi gọi (bắt buộc):</b> '
            'không vừa gọi vừa gõ máy, không vừa gọi vừa xem điện thoại khác, không '
            'vừa gọi vừa làm việc khác. Khách nghe được ngay sự thiếu tập trung qua '
            'giọng nói.' + hq('giọng ngập ngừng, câu nói thiếu mạch lạc, khách đánh '
            'giá &#8220;sale này không chuyên &mdash; không tôn trọng mình&#8221; '
            '&rarr; khách không quay lại dù giá tốt.') + '</p>'
            + '<p style="' + lead + '"><b>3. Bắt buộc khởi động giọng trước mỗi cuộc '
            'gọi:</b> nói thử ít nhất 1 câu + nhẩm công thức <b>TO &mdash; RÕ &mdash; '
            'ĐỀU &mdash; CÓ NHỊP</b>. Không được gọi khách khi giọng mệt, giọng yếu, '
            'giọng chưa sẵn sàng.' + hq('30 giây đầu nói sai giọng, khách đã đánh giá '
            'xong &mdash; dù nói hay về sau cũng không cứu được cuộc gọi.') + '</p>'

            + _h('II. Quy định luyện giọng hằng ngày (bắt buộc)')
            + '<p style="' + lead + '"><b>1. Phải luyện giọng mỗi ngày &mdash; không '
            'có ngoại lệ:</b> có khách hay không vẫn phải luyện, bận hay không vẫn '
            'phải luyện, mỗi ngày 5&ndash;10 phút. &#128073; Giọng nói là công cụ '
            'kiếm tiền, không luyện là tự bỏ tiền.</p>'
            + '<p style="' + lead + '"><b>2. Không luyện giọng = tự mất lợi thế:</b> '
            'gọi nhiều nhưng khách không nghe lâu, không phản hồi, không hẹn gặp; dễ '
            'sinh tâm lý &#8220;khách khó&#8221;, &#8220;thị trường khó&#8221;, '
            '&#8220;không có nhu cầu&#8221;. &#128073; Thực tế không phải khách khó, '
            'mà là <b>GIỌNG NÓI YẾU</b>.</p>'

            + _h('III. Những thiệt hại thực tế nếu không tuân thủ')
            + '<table><thead><tr>'
            '<th style="width:36%;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Thiệt hại</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Diễn ra thế nào</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:8px 10px;"><b>1. Mất khách mà không biết vì sao</b></td>'
            '<td style="padding:8px 10px;">Khách không phản hồi, không từ chối rõ ràng, '
            'khách &#8220;im lặng&#8221;. &rArr; Đây là kiểu mất khách nguy hiểm nhất.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>2. Mất cơ hội tăng thu nhập</b></td>'
            '<td style="padding:8px 10px;">Giọng yếu &rarr; ít cuộc gọi chất lượng '
            '&rarr; ít hợp đồng &rarr; thu nhập thấp hơn đồng nghiệp. Cùng data &mdash; '
            'cùng kịch bản, người giọng tốt luôn làm được nhiều hơn.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>3. Mất lợi thế ngay từ 30 giây đầu</b></td>'
            '<td style="padding:8px 10px;">Khách chỉ cần 30 giây để quyết định có nghe '
            'tiếp hay không. Nếu giọng nhỏ &mdash; chậm &mdash; thiếu năng lượng, khách '
            'đã quyết định xong trước khi bạn nói hết câu đầu tiên.</td></tr>'
            '</tbody></table>'

            + '<h2 style="font-size:20px;font-weight:900;color:#1e293b;margin:22px 0 8px;">'
            '&#127942; IV. Câu nhân viên phải GHI NHỚ</h2>'
            + _chot('Không ai cướp khách của bạn &mdash; bạn <b>tự mất khách vì giọng '
                    'nói yếu</b>. Không luyện giọng = <b>tự bỏ tiền ra khỏi túi mình</b>.')

            + _apply(
                '<p>Bảng tự kiểm trước MỖI cuộc gọi (Có/Không):</p>'
                '<ol>'
                '<li>Đã ngồi <b>thẳng lưng</b>, hai chân chạm đất chưa?</li>'
                '<li>Đã <b>tắt việc khác</b>, tập trung 100% chưa?</li>'
                '<li>Đã <b>thử giọng 1 câu</b> + nhẩm TO-RÕ-ĐỀU-CÓ NHỊP chưa?</li>'
                '<li>Giọng đã <b>đủ to, có nhiệt</b>, không buồn ngủ chưa?</li>'
                '<li>Hôm nay đã <b>luyện giọng 5&ndash;10 phút</b> chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào &#8220;Không&#8221; &rArr; sửa '
                'ngay trước khi bấm gọi khách.</p>')
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

            ('Khách KHÔNG phân tích mà chủ yếu làm gì?',
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
             [('"Ờ...", "À thì...", "Em nghĩ là...", "Để em xem đã...", "Cái này thì..."', T),
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

            ('Trong bài luyện hằng ngày, khi gọi nội bộ luyện giọng được nhận xét điều gì?',
             [('CHỈ nhận xét GIỌNG (rõ/đều/năng lượng), không nhận xét nội dung hay kịch bản', T),
              ('Nhận xét cả nội dung lẫn kịch bản', F),
              ('Chấm điểm trình độ chuyên môn', F),
              ('Không cần nhận xét gì', F)]),

            ('Câu nhân viên phải ghi nhớ cuối khóa là gì?',
             [('"Không ai cướp khách của bạn, bạn tự mất khách vì giọng nói yếu; không luyện giọng = tự bỏ tiền khỏi túi"', T),
              ('"Khách khó nên không chốt được là bình thường"', F),
              ('"Giọng nói không quan trọng bằng giá rẻ"', F),
              ('"Cứ gọi nhiều ắt có khách, không cần luyện giọng"', F)]),
        ]
