# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

Bám SÁT tài liệu gốc (Theo đuổi khách hàng sau báo giá.pdf): giữ nguyên tư duy
"gửi báo giá là điểm BẮT ĐẦU" + hành trình 8 bước, viết chi tiết - chuyên nghiệp
cho nhân viên MỚI đọc xong là làm được: sơ đồ hành trình, bảng so sánh SAI/ĐÚNG,
khung công thức, câu chốt thuộc lòng, bảng câu hỏi khai thác và bảng tự kiểm.

Khóa KHÔNG có ảnh nguồn => thiết kế typography lớn thay ảnh (hero + banner PHẦN
+ ô công thức). Helper riêng prefix _tdbg_ (xem reference-seed-method-name-
collision) - KHÔNG dùng _pN trần. Idempotent theo PHIÊN BẢN.

BẪY %: mọi % literal trong NỘI DUNG để 1 dấu; chỉ escape %% bên trong các hàm
helper module có dùng '...' % (...). (xem reference-course-writing-format)

Đảo thứ tự đáp án mỗi lần thi đã do overview.js (startExam -> _shuffle) xử lý
CHUNG cho mọi khóa => không cần cấu hình riêng ở seed.
"""
from odoo import api, models
from .seed_kh_tiem_nang import _WRAP, _box, _formula, _apply, _advice, _mistake
from .seed_khong_tuoi import _chot

_TDBG_VERSION = 'v2'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

# ---------------------------------------------------------------------------
#  HIỆU ỨNG TOÀN KHÓA (nối chuỗi thuần - KHÔNG dùng % format -> % an toàn)
# ---------------------------------------------------------------------------
_STYLE = (
    '<style>'
    '.vd-tdbg .vd-hero{position:relative;overflow:hidden;}'
    '.vd-tdbg .vd-hero::after{content:"";position:absolute;top:0;left:-65%;'
    'width:45%;height:100%;background:linear-gradient(120deg,'
    'rgba(255,255,255,0) 0%,rgba(255,255,255,.5) 50%,rgba(255,255,255,0) 100%);'
    'transform:skewX(-22deg);animation:vdShine 3.6s ease-in-out infinite;}'
    '.vd-tdbg .vd-phan{animation:vdRise .6s ease both;}'
    '.vd-tdbg .vd-step{transition:transform .3s ease,box-shadow .3s ease;}'
    '.vd-tdbg .vd-step:hover{transform:translateY(-5px);'
    'box-shadow:0 16px 36px rgba(2,6,23,.26);}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:6px 0 4px;}'
    '.vd-tdbg .vd-pulse{display:inline-block;animation:vdPulse 1.5s ease-in-out infinite;}'
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
        '<div style="color:#ffffff;font-size:46px;font-weight:900;line-height:1.08;'
        'letter-spacing:1px;text-shadow:0 3px 10px rgba(0,0,0,.28);">%s</div>'
        '<div style="color:#fff4f0;font-size:17px;font-weight:600;margin-top:16px;'
        'max-width:820px;margin-left:auto;margin-right:auto;">%s</div></div>'
    ) % (title_small, title_big, sub)


def _phan(num, title, sub):
    """Banner CHƯƠNG (BƯỚC N) - nền slate sang, số mờ lớn phía sau."""
    return (
        '<div class="vd-phan" style="position:relative;overflow:hidden;'
        'background:linear-gradient(135deg,#1e293b 0%%,#334155 100%%);'
        'border-radius:18px;padding:24px 28px;margin:38px 0 20px;'
        'box-shadow:0 12px 30px rgba(2,6,23,.24);">'
        '<div style="position:absolute;right:18px;top:-26px;font-size:130px;'
        'font-weight:900;color:rgba(255,255,255,.07);line-height:1;">%s</div>'
        '<div style="position:relative;color:#fbbf24;font-size:15px;font-weight:800;'
        'letter-spacing:3px;text-transform:uppercase;">BƯỚC %s</div>'
        '<div style="position:relative;color:#ffffff;font-size:26px;font-weight:900;'
        'margin-top:4px;line-height:1.2;">%s</div>'
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


def _say(inner):
    """Ô CÂU MẪU NÊN NÓI (xanh dương, in nghiêng) - để NV copy dùng ngay."""
    return ('<div style="border-left:5px solid #2563eb;background:#eff6ff;'
            'border-radius:0 12px 12px 0;padding:14px 18px;margin:12px 0;'
            'font-size:16px;font-style:italic;color:#1e3a8a;font-weight:600;">'
            '&#128231; Câu mẫu nên nói: &#8220;%s&#8221;</div>') % inner


class SlideChannelSeedTheoDuoiBaoGia(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_theo_duoi_bao_gia(self):
        ch = self.env.ref('vd_elearning.course_theo_duoi_bao_gia',
                          raise_if_not_found=False)
        if not ch:
            ch = self.sudo().search(
                [('name', 'ilike', 'theo đuổi khách')], limit=1)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _TDBG_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        merged = ''.join(body for _title, body in self._vd_tdbg_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-tdbg" style="%s">%s</div>'
                                 % (_WRAP, merged)),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_tdbg_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _TDBG_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG
    # ==================================================================
    def _vd_tdbg_pages(self):
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;line-height:1.7;'
        # Thứ tự thực tế (user chốt): 1-Gửi mẫu nhà, 2-Gửi báo giá + đảm bảo
        # chất lượng, 3-Phản hồi sau 2 ngày, 4-Nhắc khởi công + ký giữ giá,
        # 5-Khai thác & xử lý vấn đề sau báo giá, 6-Gửi hợp đồng + phụ lục,
        # 7-Khai thác & xử lý vấn đề hợp đồng, 8-Hẹn ký + khảo sát đất.
        return [
            ('Hero', self._tdbg_hero()),
            ('Intro', self._tdbg_intro(lead)),
            ('S1-MauNha', self._tdbg_maunha(lead)),
            ('S2-BaoGia', self._tdbg_baogia(lead)),
            ('S3-PhanHoi', self._tdbg_phanhoi(lead)),
            ('S4-KhoiCong', self._tdbg_khoicong(lead)),
            ('S5-KhaiThac', self._tdbg_khaithac(lead)),
            ('S678-HopDong', self._tdbg_b678(lead)),
            ('Gold', self._tdbg_gold(lead)),
        ]

    def _tdbg_hero(self):
        return _hero(
            'Kỹ năng Sale &mdash; Chốt hợp đồng',
            'THEO ĐUỔI KHÁCH SAU KHI GỬI BÁO GIÁ',
            'Gửi báo giá KHÔNG phải là kết thúc &mdash; đó chỉ là ĐIỂM BẮT ĐẦU '
            'của quá trình chốt hợp đồng. Cả khóa dạy em cách DẪN DẮT khách đi '
            'qua 8 bước, không bao giờ để khách &#8220;treo&#8221;.')

    # ------------------------------------------------------------------
    #  MỞ ĐẦU — TƯ DUY NỀN TẢNG + HÀNH TRÌNH 8 BƯỚC
    # ------------------------------------------------------------------
    def _tdbg_intro(self, lead):
        def _flow(order, label, color):
            return (
                '<div class="vd-step" style="flex:1 1 150px;min-width:140px;'
                'background:#ffffff;border:2px solid ' + color + ';border-top:6px solid '
                + color + ';border-radius:14px;padding:14px 12px;text-align:center;'
                'box-shadow:0 8px 20px rgba(2,6,23,.10);">'
                '<div style="font-size:13px;font-weight:900;color:' + color + ';'
                'letter-spacing:1px;">' + order + '</div>'
                '<div style="font-size:14.5px;font-weight:800;color:#0f172a;'
                'margin-top:6px;line-height:1.3;">' + label + '</div></div>')
        flows = (
            _flow('BƯỚC 1', 'Gửi mẫu nhà tham khảo', '#b45309')
            + _flow('BƯỚC 2', 'Gửi báo giá &mdash; đảm bảo chất lượng', '#0369a1')
            + _flow('BƯỚC 3', 'Phản hồi sau 1&ndash;2 ngày', '#7c3aed')
            + _flow('BƯỚC 4', 'Nhắc khởi công &amp; ký giữ giá', '#be123c')
            + _flow('BƯỚC 5', 'Khai thác &amp; xử lý vấn đề sau báo giá', '#dc2626')
            + _flow('BƯỚC 6', 'Gửi hợp đồng &amp; phụ lục', '#0d9488')
            + _flow('BƯỚC 7', 'Khai thác &amp; xử lý vấn đề hợp đồng', '#0891b2')
            + _flow('BƯỚC 8', 'Hẹn ký hợp đồng &amp; khảo sát đất', '#15803d'))
        return (
            '<h2 style="font-size:22px;font-weight:900;color:#1e293b;'
            'margin:26px 0 10px;">&#127919; Vì sao gửi báo giá xong KHÔNG được ngồi chờ?</h2>'

            + _quote('Gửi báo giá chỉ là điểm BẮT ĐẦU của quá trình chốt hợp đồng, '
                     'không phải là kết thúc.')
            + '<p style="' + lead + '">Rất nhiều nhân viên MẤT khách chỉ vì một suy '
            'nghĩ sai: <b>&#8220;Em gửi báo giá rồi, giờ chờ khách gọi lại&#8221;</b>. '
            'Đây là <b>sai lầm nghiêm trọng</b>. Vì khách đang xây nhà thường:</p>'
            + '<table><tbody>'
            '<tr><td style="padding:6px 10px;">&#128269; Xem <b>rất nhiều</b> đơn vị</td>'
            '<td style="padding:6px 10px;">&#128176; Đang cân nhắc <b>tài chính</b></td></tr>'
            '<tr><td style="padding:6px 10px;">&#129300; <b>Chưa hiểu hết</b> báo giá</td>'
            '<td style="padding:6px 10px;">&#9878;&#65039; Đang <b>so sánh</b> các bên</td></tr>'
            '<tr><td style="padding:6px 10px;" colspan="2">&#10067; <b>Chưa biết nên hỏi gì</b> &mdash; nên khách im lặng chứ không phải hết quan tâm</td></tr>'
            '</tbody></table>'

            + _h('&#128227; Việc ĐẦU TIÊN: chủ động ĐÔN ĐỐC khách xem báo giá')
            + '<p style="' + lead + '">Gửi báo giá xong, việc bắt buộc phải làm ngay là '
            '<b>chủ động gọi/nhắn dò hỏi tình hình</b>: khách đã <b>nhận</b> được báo '
            'giá chưa, đã <b>mở ra xem</b> chưa, đã <b>đọc kỹ</b> chưa. KHÔNG được mặc '
            'định &#8220;gửi là khách sẽ xem&#8221;.</p>'
            + _mistake(
                '<p style="margin:0;">Thực tế rất nhiều khách <b>không xem</b> báo giá, '
                'hoặc có xem nhưng <b>chưa xem kỹ</b> &mdash; thậm chí lấy lý do '
                '&#8220;anh/chị chưa xem&#8221;, &#8220;để xem sau&#8221; để tránh trao '
                'đổi. Nếu nhân viên tin ngay và ngồi chờ &rArr; báo giá nằm im, khách '
                'nguội dần rồi nghiêng sang đối thủ.</p>')
            + _box('#0369a1', '#eff6ff', '&#128196;', 'Trong báo giá có gì mà PHẢI đôn đốc khách xem?',
                   '<p style="margin-bottom:0;">Báo giá của mình có <b>PHỤ LỤC VẬT TƯ '
                   'đầy đủ</b> (chủng loại, thương hiệu, tiêu chuẩn) và <b>TỔNG GIÁ TRỊ '
                   'HỢP ĐỒNG đầy đủ</b> &mdash; đây chính là thứ khách cần để so sánh '
                   'và ra quyết định. Khách chưa xem kỹ phần này thì <b>chưa thể đánh '
                   'giá đúng</b> giá trị mình mang lại. Vì vậy phải khéo léo '
                   '<b>đôn đốc, hướng dẫn khách xem đúng các mục quan trọng</b> trong '
                   'báo giá.</p>')
            + '<p style="font-size:16px;color:#b91c1c;font-weight:800;margin:12px 0;">'
            '&#128073; Nếu nhân viên không CHỦ ĐỘNG dẫn dắt và đôn đốc, khách sẽ dần '
            'nghiêng về đơn vị khác.</p>'

            + _formula(
                'Mục tiêu sau khi gửi báo giá KHÔNG phải là ngồi chờ khách ký, mà là '
                '<b>chủ động đôn đốc khách xem báo giá</b> rồi <b>từng bước đưa khách '
                'đi qua 8 giai đoạn</b> tới lúc ký hợp đồng. '
                '<span style="color:#dc2626;">Khách im lặng = quy trình đang bị DỪNG '
                'lại</span> &mdash; tuyệt đối không để khách &#8220;treo&#8221;.')

            + _h('&#128506;&#65039; Hành trình 8 bước phải thuộc lòng')
            + '<div style="display:flex;flex-wrap:wrap;gap:12px;margin:16px 0;'
            'justify-content:center;">' + flows + '</div>'
            + _box('#2563eb', '#eff6ff', '&#128221;', 'Nguyên tắc xuyên suốt',
                   '<p style="margin-bottom:0;">Sau <b>mỗi lần liên hệ</b>, khách phải '
                   '<b>tiến thêm ít nhất 1 bước</b> (phản hồi báo giá &rarr; gỡ khúc '
                   'mắc &rarr; xem hợp đồng &rarr; hẹn khảo sát...). Mỗi lần tương tác '
                   'đều phải có <b>mục tiêu rõ ràng</b>, đưa khách gần hơn tới quyết '
                   'định ký.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 2 — GỬI BÁO GIÁ và ĐẢM BẢO CHẤT LƯỢNG BÁO GIÁ (nội dung chuyên sâu)
    # ------------------------------------------------------------------
    def _tdbg_baogia(self, lead):
        return (
            _phan('2', 'GỬI BÁO GIÁ và ĐẢM BẢO CHẤT LƯỢNG BÁO GIÁ',
                  'Việc QUAN TRỌNG BẬC NHẤT của sale: một khi đã quyết định gửi thì báo giá PHẢI thật chuẩn.')

            + '<h2 style="font-size:21px;font-weight:900;color:#0f172a;margin:8px 0 10px;">'
            '&#128200; Làm báo giá CHUẨN &mdash; kỹ năng sống còn của nhân viên kinh doanh</h2>'
            + '<p style="' + lead + '">Đây là nội dung <b>chuyên sâu</b>, cả nhân viên '
            'phải hiểu và làm cho bằng được. Báo giá không phải &#8220;một file gửi cho '
            'có&#8221; &mdash; nó là <b>vũ khí chốt hợp đồng</b>. Một khi đã quyết định '
            'gửi báo giá cho khách thì báo giá đó <b>bắt buộc phải THẬT CHUẨN</b>.</p>'

            + _quote('Nếu báo giá không khớp tầm tài chính của khách, báo giá đó KHÔNG '
                     'có tác dụng &mdash; khách sẽ không quan tâm nữa và chuyển sang đối '
                     'thủ để tham khảo tiếp.')

            + _h('&#127919; &#8220;Chuẩn&#8221; ở đây nghĩa là gì?')
            + '<p style="' + lead + '">Một báo giá được coi là CHUẨN khi hội đủ '
            '<b>3 điều kiện</b> &mdash; và điều kiện SỐ 1 là quan trọng nhất:</p>'
            + '<table><thead><tr>'
            '<th style="width:34%;text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Điều kiện</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Ý nghĩa</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:8px 10px;color:#b91c1c;"><b>1. KHỚP TẦM TÀI CHÍNH khách đưa ra</b></td>'
            '<td style="padding:8px 10px;">Con số tổng phải nằm TRONG khoảng ngân sách khách nói. Đây là yếu tố QUYẾT ĐỊNH khách có quan tâm báo giá hay không.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>2. Phù hợp DIỆN TÍCH và CÔNG NĂNG khách muốn</b></td>'
            '<td style="padding:8px 10px;">Số tầng, số phòng, công năng khách yêu cầu phải cân đối được với tầm tài chính đó.</td></tr>'
            '<tr><td style="padding:8px 10px;"><b>3. Đúng MONG MUỐN và phong cách</b></td>'
            '<td style="padding:8px 10px;">Phong cách, mức hoàn thiện, thang máy/gara/sân... khớp điều khách mong.</td></tr>'
            '</tbody></table>'

            + _formula(
                'Báo giá KHÔNG khớp tầm tài chính = báo giá VÔ TÁC DỤNG. '
                '<span style="color:#dc2626;">Khách hết quan tâm &rarr; quay sang đối '
                'thủ.</span> Vì vậy: <b>tập trung TỐI ĐA làm báo giá khớp tầm tài chính '
                '+ diện tích + công năng &mdash; rồi mới gửi.</b>')

            + _h('&#9888;&#65039; Vì sao KHÔNG khớp tài chính là hỏng cả cuộc chơi?')
            + _mistake(
                '<p style="margin:0;">Khách nói tầm <b>2,8 tỷ</b> nhưng nhân viên gửi '
                'báo giá <b>3,8 tỷ</b>. Khách nhìn con số đầu tiên đã thấy '
                '&#8220;vượt quá xa&#8221; &rArr; không đọc tiếp, không phản hồi, âm '
                'thầm loại mình khỏi danh sách và tiếp tục tham khảo đơn vị khác. Mình '
                'mất khách mà không hề hay biết.</p>')
            + '<p style="' + lead + '">Nhiều khi khách muốn <b>diện tích rộng, công '
            'năng nhiều</b>, nhưng <b>tầm tài chính không đủ</b> để làm hết. Nếu bê '
            'nguyên nhu cầu đó tính ra, chi phí sẽ <b>cao hơn ngân sách rất nhiều</b>. '
            'Nhiệm vụ của nhân viên là <b>cân đối</b>: tư vấn phương án diện tích + '
            'công năng <b>vừa với túi tiền</b> khách, chứ không phải gửi một con số '
            'vượt xa rồi để khách tự sốc.</p>'

            + _h('&#9989; Trước khi bấm GỬI, tự trả lời 3 câu hỏi kiểm tra')
            + _box('#0369a1', '#eff6ff', '&#10068;', 'Câu hỏi 1 (quan trọng nhất) &mdash; Báo giá có KHỚP TẦM TÀI CHÍNH khách đưa ra không?',
                   '<p style="margin-bottom:0;">Tổng giá trị có nằm trong khoảng ngân '
                   'sách khách nói không? Nếu vượt &rArr; <b>CHƯA gửi</b>, phải cân đối '
                   'lại phương án cho khớp trước.</p>')
            + _box('#7c3aed', '#faf5ff', '&#10068;', 'Câu hỏi 2 &mdash; Báo giá có phù hợp DIỆN TÍCH và CÔNG NĂNG khách đưa ra không?',
                   '<p style="margin-bottom:0;">Diện tích, số tầng, công năng khách '
                   'muốn có cân đối được với tầm tài chính đó không? Nếu nhu cầu quá '
                   'lớn so với ngân sách &rArr; phải tư vấn điều chỉnh cho hợp lý rồi '
                   'mới báo giá.</p>')
            + _box('#16a34a', '#f0fdf4', '&#10068;', 'Câu hỏi 3 &mdash; Báo giá có đúng MONG MUỐN của khách chưa?',
                   '<p style="margin-bottom:0;">Phong cách, mức hoàn thiện, thang máy '
                   '&middot; gara &middot; sân... phải KHỚP điều khách mong.</p>')

            + _chot('Một khi đã quyết định gửi báo giá thì báo giá đó phải THẬT CHUẨN. '
                    'Nếu mình là khách, mình cũng thấy báo giá này KHỚP TÚI TIỀN và hợp '
                    'lý &mdash; đó mới là báo giá đạt yêu cầu.')

            + _apply('<p style="margin-bottom:0;">Trước khi bấm GỬI, soát đủ '
                     '<b>3 câu hỏi</b>, ưu tiên số 1 là <b>KHỚP TẦM TÀI CHÍNH</b>. '
                     '<span class="vd-pulse">&#10145;</span> Còn lệch tài chính / diện '
                     'tích / công năng &rArr; DỪNG, cân đối lại phương án rồi mới gửi. '
                     'Báo giá lệch tài chính = tự đẩy khách sang đối thủ.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 3 — SAU 1–2 NGÀY BẮT BUỘC LẤY PHẢN HỒI
    # ------------------------------------------------------------------
    def _tdbg_phanhoi(self, lead):
        return (
            _phan('3', 'SAU 1&ndash;2 NGÀY BẮT BUỘC PHẢI LẤY PHẢN HỒI',
                  'Gửi báo giá xong rồi im luôn = nguyên nhân mất RẤT nhiều khách.')

            + _mistake('<p style="margin:0;">Gửi báo giá xong&hellip; <b>im luôn</b>: '
                       'không gọi, không nhắn, không hỏi. Đây là sai lầm khiến mất rất '
                       'nhiều khách hàng.</p>')

            + _h('Mục tiêu cuộc gọi phản hồi')
            + _vs(
                'Gọi để <b>ép khách ký</b> ngay.<br/>Gọi để hỏi cụt lủn '
                '&#8220;anh chị ký chưa?&#8221;.',
                'Gọi để <b>BIẾT khách đang nghĩ gì</b>.<br/>Khai thác suy nghĩ thật '
                'của khách để dẫn tiếp.')
            + '<p style="' + lead + '">Bộ câu hỏi cần khai thác được trong 1&ndash;2 '
            'ngày sau khi gửi:</p>'
            + '<ul style="' + lead + '">'
            '<li>Anh/chị đã <b>xem báo giá</b> chưa?</li>'
            '<li>Anh/chị thấy <b>phần nào hợp lý</b>?</li>'
            '<li><b>Phần nào còn băn khoăn</b>?</li>'
            '<li><b>Mức đầu tư</b> có phù hợp không?</li>'
            '<li>Có <b>hạng mục nào</b> muốn điều chỉnh không?</li></ul>'

            + _h('Khách IM LẶNG &mdash; đừng vội kết luận &#8220;hết quan tâm&#8221;')
            + _quote('Khách im không có nghĩa là khách không quan tâm. Đó là một tín '
                     'hiệu CẦN TÌM HIỂU, không phải để đoán.')
            + '<table><thead><tr>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Khách im lặng có thể vì&hellip;</th>'
            '</tr></thead><tbody>'
            '<tr><td style="padding:7px 10px;">&#128176; Báo giá <b>cao hơn dự kiến</b></td></tr>'
            '<tr><td style="padding:7px 10px;">&#127919; Báo giá <b>chưa đúng nhu cầu</b></td></tr>'
            '<tr><td style="padding:7px 10px;">&#129300; <b>Chưa hiểu cách tính</b></td></tr>'
            '<tr><td style="padding:7px 10px;">&#9203; <b>Đang chờ</b> đơn vị khác</td></tr>'
            '<tr><td style="padding:7px 10px;">&#129309; <b>Chưa đủ niềm tin</b></td></tr>'
            '<tr><td style="padding:7px 10px;">&#10067; <b>Chưa biết nên hỏi gì</b></td></tr>'
            '</tbody></table>'
            + _chot('Việc của nhân viên là KHAI THÁC, không phải ĐOÁN.')

            + _apply('<p style="margin-bottom:0;">Đặt lịch nhắc: <b>1&ndash;2 ngày</b> '
                     'sau khi gửi báo giá &rArr; gọi lấy phản hồi. '
                     '<span class="vd-pulse">&#10145;</span> Mục tiêu cuộc gọi là '
                     '<b>hiểu suy nghĩ khách</b>, tuyệt đối không ép ký.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 1 — GỬI MẪU NHÀ THAM KHẢO (làm ĐẦU TIÊN)
    # ------------------------------------------------------------------
    def _tdbg_maunha(self, lead):
        return (
            _phan('1', 'GỬI MẪU NHÀ CHO KHÁCH THAM KHẢO',
                  'Làm ĐẦU TIÊN &mdash; nhưng tuyệt đối KHÔNG ép khách chốt mẫu nhà.')

            + _h('Mục tiêu khi gửi mẫu nhà')
            + '<ul style="' + lead + '">'
            '<li>Cho khách có <b>thêm ý tưởng</b>.</li>'
            '<li>Cho khách nhìn thấy <b>nhiều lựa chọn</b>.</li>'
            '<li>Giúp khách <b>xác định sở thích</b>.</li></ul>'

            + _vs(
                '&#8220;Anh chị <b>chọn giúp em một mẫu</b> nhé.&#8221;<br/>&rArr; Ép '
                'khách chốt mẫu &mdash; khách thấy áp lực.',
                'Gửi mẫu <b>gần với nhu cầu</b> để khách tham khảo, thích chi tiết nào '
                'thì bên em <b>điều chỉnh thiết kế</b> theo.')
            + _say('Em gửi thêm một số mẫu nhà có diện tích và mức đầu tư gần với nhu '
                   'cầu của anh/chị để mình tham khảo. Nếu có chi tiết nào anh/chị '
                   'thích, bên em sẽ điều chỉnh thiết kế theo đúng mong muốn của gia đình.')

            + _box('#9333ea', '#faf5ff', '&#128161;', 'Vì sao không được ép chốt mẫu',
                   '<p style="margin-bottom:0;">Khách <b>không mua mẫu nhà</b>. Khách '
                   'mua <b>giải pháp phù hợp</b> với gia đình mình. Mẫu nhà chỉ là công '
                   'cụ để khách hình dung và bộc lộ sở thích.</p>')

            + _apply('<p style="margin-bottom:0;">Gửi 3&ndash;5 mẫu nhà <b>sát diện '
                     'tích + mức đầu tư</b> của khách kèm đúng câu mẫu ở trên. '
                     '<span class="vd-pulse">&#10145;</span> Mục tiêu là mở ý tưởng, '
                     'KHÔNG bắt khách chọn.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 4 — NHẮC THỜI GIAN KHỞI CÔNG và KÝ HỢP ĐỒNG GIỮ GIÁ (nếu có)
    # ------------------------------------------------------------------
    def _tdbg_khoicong(self, lead):
        return (
            _phan('4', 'NHẮC THỜI GIAN KHỞI CÔNG và KÝ HỢP ĐỒNG GIỮ GIÁ',
                  'Rất quan trọng, đặc biệt cuối năm &mdash; khách nào cũng muốn xong trước Tết.')

            + '<p style="' + lead + '">Nếu khởi công muộn, khách sẽ gặp một loạt bất lợi '
            '&mdash; đây chính là lý do để khách cần quyết định sớm:</p>'
            + '<table><tbody>'
            '<tr><td style="padding:7px 10px;">&#9201;&#65039; <b>Thi công gấp</b></td>'
            '<td style="padding:7px 10px;">&#128201; Dễ <b>ảnh hưởng tiến độ</b></td></tr>'
            '<tr><td style="padding:7px 10px;">&#128230; <b>Khó bàn giao</b></td>'
            '<td style="padding:7px 10px;">&#128295; <b>Khó hoàn thiện</b></td></tr>'
            '</tbody></table>'

            + _say('Nếu gia đình mình dự kiến ở nhà mới trước Tết thì mình nên triển '
                   'khai sớm để đảm bảo tiến độ. Nếu để quá sát thời điểm cuối năm thì '
                   'việc hoàn thiện sẽ rất áp lực.')

            + _box('#dc2626', '#fef2f2', '&#9888;&#65039;', 'Ranh giới phải nhớ',
                   '<p style="margin-bottom:0;">Mục tiêu <b>KHÔNG phải gây áp lực vô '
                   'lý</b>, mà giúp khách <b>hiểu rõ hệ quả</b> của việc chậm quyết '
                   'định. Nhắc bằng thiện chí, không dọa, không thúc ép lộ liễu.</p>')

            + _h('&#128273; Ký hợp đồng GIỮ GIÁ (nếu công ty có chính sách)')
            + '<p style="' + lead + '">Khi khách chưa khởi công ngay nhưng đã ưng '
            'phương án, có thể đề xuất <b>ký hợp đồng giữ giá</b> để khách '
            '<b>chốt được mức giá hiện tại</b>, tránh biến động khi vật tư tăng. Đây '
            'vừa là lợi ích cho khách, vừa giúp mình <b>giữ chân khách</b>, không để '
            'khách trôi sang đối thủ trong lúc còn cân nhắc.</p>'
            + _say('Hiện bên em đang áp mức giá này, nếu anh/chị chốt phương án thì '
                   'mình có thể ký hợp đồng giữ giá để khóa mức giá hôm nay, sau này '
                   'vật tư có tăng gia đình cũng không bị ảnh hưởng ạ.')

            + _apply('<p style="margin-bottom:0;">Khéo gắn quyết định của khách với '
                     '<b>mốc thời gian</b> (trước Tết / mùa khô / kịp tiến độ) và '
                     '<b>đề xuất ký giữ giá</b> nếu có chính sách. '
                     '<span class="vd-pulse">&#10145;</span> Cho khách thấy chi phí của '
                     'việc CHẬM, không dọa khách.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 5 — KHAI THÁC và XỬ LÝ VẤN ĐỀ SAU BÁO GIÁ (quan trọng nhất)
    # ------------------------------------------------------------------
    def _tdbg_khaithac(self, lead):
        def _grp(num, title, color, rows):
            head = ('<tr><td colspan="1" style="background:' + color + ';color:#fff;'
                    'font-weight:800;padding:8px 12px;border-radius:8px 8px 0 0;">'
                    + num + '. ' + title + '</td></tr>')
            body = ''.join(
                '<tr><td style="padding:7px 12px;border-bottom:1px solid #eef2f7;">'
                '&#8226; ' + r + '</td></tr>' for r in rows)
            return ('<table style="margin:12px 0;box-shadow:0 6px 16px '
                    'rgba(2,6,23,.08);border-radius:8px;overflow:hidden;">'
                    + head + body + '</table>')
        return (
            _phan('5', 'KHAI THÁC và XỬ LÝ VẤN ĐỀ SAU BÁO GIÁ',
                  'BƯỚC QUAN TRỌNG NHẤT: khách chưa ký thì CHẮC CHẮN còn vấn đề.')

            + _quote('Nếu khách chưa ký, chắc chắn còn vấn đề. Nhân viên phải TÌM RA '
                     '&mdash; không được tự suy đoán.')

            + _h('6 nhóm câu hỏi phải khai thác đủ')
            + _grp('1', 'Báo giá', '#0369a1',
                   ['Có phù hợp không?', 'Có vượt tài chính không?',
                    'Có cần điều chỉnh không?'])
            + _grp('2', 'Thiết kế', '#7c3aed',
                   ['Có thích không?', 'Có cần thay đổi gì?',
                    'Có cần thêm công năng?'])
            + _grp('3', 'Mẫu nhà', '#b45309',
                   ['Đã đúng phong cách chưa?', 'Có muốn tham khảo thêm không?'])
            + _grp('4', 'Gia đình', '#be123c',
                   ['Đã thống nhất chưa?', 'Ai là người quyết định?',
                    'Có cần trao đổi thêm với người thân không?'])
            + _grp('5', 'Khởi công', '#0d9488',
                   ['Dự kiến khi nào?', 'Có đang chờ việc gì không?',
                    'Có vướng thủ tục không?'])
            + _grp('6', 'Niềm tin', '#dc2626',
                   ['Còn điều gì khiến anh/chị chưa yên tâm khi lựa chọn bên em?'])

            + _box('#dc2626', '#fef2f2', '&#128273;', 'Câu hỏi NIỀM TIN &mdash; đắt giá nhất',
                   '<p style="margin-bottom:0;">Câu &#8220;<b>Còn điều gì khiến anh/chị '
                   'chưa yên tâm khi chọn bên em?</b>&#8221; giúp phát hiện <b>rào cản '
                   'THẬT SỰ</b> trước khi bước sang giai đoạn ký kết. Đừng bỏ qua câu '
                   'này.</p>')

            + _chot('Khách chưa ký = còn khúc mắc chưa được gỡ. Nhiệm vụ của em là '
                    'KHAI THÁC cho ra, không phải ngồi đoán rồi bỏ cuộc.')

            + _apply('<p style="margin-bottom:0;">Mỗi khách chưa chốt, chạy đủ '
                     '<b>6 nhóm câu hỏi</b> để tìm khúc mắc thật. '
                     '<span class="vd-pulse">&#10145;</span> Luôn kết bằng câu hỏi '
                     '<b>NIỀM TIN</b> để lộ rào cản cuối cùng.</p>')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 6-7-8 — GỬI HĐ & PHỤ LỤC → XỬ LÝ VẤN ĐỀ HĐ → HẸN KÝ & KHẢO SÁT ĐẤT
    # ------------------------------------------------------------------
    def _tdbg_b678(self, lead):
        return (
            _phan('6&nbsp;&middot;&nbsp;7&nbsp;&middot;&nbsp;8', 'GỬI HỢP ĐỒNG &amp; PHỤ LỤC &rarr; XỬ LÝ VẤN ĐỀ HỢP ĐỒNG &rarr; HẸN KÝ &amp; KHẢO SÁT ĐẤT',
                  'Giai đoạn chốt: khi hết vấn đề sau báo giá thì PHẢI chuyển bước, không nói chung chung.')

            + _h('BƯỚC 6 &mdash; GỬI HỢP ĐỒNG và PHỤ LỤC')
            + '<p style="' + lead + '">Khi khách đã: <b>đồng ý báo giá + đồng ý phương '
            'án + không còn vướng mắc lớn</b> &rArr; đừng tiếp tục nói chuyện chung '
            'chung, phải chuyển sang bước tiếp theo: <b>gửi hợp đồng kèm đầy đủ phụ lục '
            'để khách nghiên cứu</b>. Phụ lục (vật tư, hạng mục, tổng giá trị) phải gửi '
            'kèm để khách nắm rõ mình cam kết những gì.</p>'
            + _say('Để gia đình mình có thời gian xem kỹ các điều khoản, bên em sẽ gửi '
                   'trước hợp đồng kèm đầy đủ phụ lục để anh/chị đọc. Nếu có nội dung '
                   'nào cần giải thích hoặc điều chỉnh, em sẽ trao đổi ngay để mình yên '
                   'tâm trước khi ký.')

            + _h('BƯỚC 7 &mdash; KHAI THÁC và XỬ LÝ VẤN ĐỀ HỢP ĐỒNG (đừng gửi xong rồi mất hút)')
            + _mistake('<p style="margin:0;">Gửi hợp đồng &mdash; xong &mdash; '
                       '<b>mất hút</b>. Đây là sai lầm của rất nhiều nhân viên.</p>')
            + '<p style="' + lead + '">Điều ĐÚNG phải làm: <b>sau 1&ndash;2 ngày phải '
            'chủ động hỏi lại</b> để khai thác và xử lý mọi vướng mắc trong hợp đồng:</p>'
            + '<ul style="' + lead + '">'
            '<li>Anh/chị đã <b>xem hợp đồng và phụ lục</b> chưa?</li>'
            '<li>Có <b>điều khoản nào chưa rõ</b> không?</li>'
            '<li>Có <b>nội dung nào</b> muốn trao đổi hoặc điều chỉnh không?</li></ul>'
            + '<p style="font-size:16px;color:#b91c1c;font-weight:800;margin:8px 0;">'
            '&#128073; Khách còn băn khoăn về hợp đồng &rArr; KHÔNG được bỏ qua, phải '
            'giải quyết DỨT ĐIỂM ngay.</p>'

            + _h('BƯỚC 8 &mdash; HẸN KÝ HỢP ĐỒNG và KHẢO SÁT ĐẤT')
            + '<p style="' + lead + '">Khi khách đã: <b>đồng ý báo giá + đồng ý thiết '
            'kế + đồng ý hợp đồng</b> &rArr; bước cuối cùng là:</p>'
            + '<ul style="' + lead + '">'
            '<li><b>Thống nhất lịch ký hợp đồng</b>.</li>'
            '<li>Đề nghị <b>lên lịch khảo sát đất</b> thực tế.</li>'
            '<li>Trao đổi rõ nội dung cần chuẩn bị: quy trình ký kết và khoản '
            '<b>đặt cọc 50.000.000 đồng</b> theo quy định công ty (nếu áp dụng), để '
            'khách chủ động sắp xếp.</li></ul>'

            + _apply('<p style="margin-bottom:0;">Hết vấn đề sau báo giá &rArr; '
                     '<b>gửi hợp đồng + phụ lục ngay</b>, đừng để nguội. '
                     '<span class="vd-pulse">&#10145;</span> Gửi xong đặt lịch '
                     '<b>1&ndash;2 ngày hỏi lại</b> xử lý vấn đề hợp đồng, rồi chốt '
                     'lịch <b>ký + khảo sát đất</b>.</p>')
        )

    # ------------------------------------------------------------------
    #  NGUYÊN TẮC VÀNG + BẢNG TỰ KIỂM
    # ------------------------------------------------------------------
    def _tdbg_gold(self, lead):
        return (
            '<div style="background:linear-gradient(135deg,#b8860b 0%,#8a6508 100%);'
            'border-radius:18px;padding:26px 28px;margin:38px 0 18px;text-align:center;'
            'box-shadow:0 14px 34px rgba(184,134,11,.35);">'
            '<div style="color:#fff8e1;font-size:15px;font-weight:800;letter-spacing:3px;'
            'text-transform:uppercase;">&#127942; Nguyên tắc vàng</div>'
            '<div style="color:#ffffff;font-size:23px;font-weight:900;margin-top:8px;'
            'line-height:1.35;">Nhân viên giỏi KHÔNG phải người gửi được NHIỀU báo giá, '
            'mà là người biết DẪN DẮT khách đi qua từng bước tới quyết định ký.</div></div>'

            + '<p style="' + lead + '">Nếu sau mỗi lần liên hệ, khách hàng tiến thêm '
            'một bước (phản hồi báo giá &rarr; gỡ khúc mắc &rarr; xem hợp đồng &rarr; '
            'hẹn khảo sát...) thì khả năng ký hợp đồng <b>tăng lên rất nhiều</b>.</p>'

            + _chot('Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi lần '
                    'tương tác đều phải có mục tiêu rõ ràng và đưa khách tiến GẦN HƠN '
                    'tới quyết định ký hợp đồng.')

            + _h('&#9989; Bảng tự kiểm sau MỖI lần liên hệ khách (Có/Chưa)')
            + '<table><thead><tr>'
            '<th style="width:8%;text-align:center;padding:8px;border-bottom:2px solid #e2e8f0;">#</th>'
            '<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #e2e8f0;">Tự hỏi</th>'
            '</tr></thead><tbody>'
            '<tr><td style="text-align:center;padding:7px;">1</td>'
            '<td style="padding:7px 10px;">Lần liên hệ này khách đã <b>tiến thêm 1 bước</b> chưa?</td></tr>'
            '<tr><td style="text-align:center;padding:7px;">2</td>'
            '<td style="padding:7px 10px;">Mình đã <b>biết khách đang nghĩ gì</b> chưa, hay chỉ đang đoán?</td></tr>'
            '<tr><td style="text-align:center;padding:7px;">3</td>'
            '<td style="padding:7px 10px;">Còn <b>khúc mắc nào</b> chưa được gỡ (báo giá / thiết kế / gia đình / niềm tin)?</td></tr>'
            '<tr><td style="text-align:center;padding:7px;">4</td>'
            '<td style="padding:7px 10px;">Đã hẹn <b>mốc liên hệ tiếp theo</b> chưa (không để khách treo)?</td></tr>'
            '<tr><td style="text-align:center;padding:7px;">5</td>'
            '<td style="padding:7px 10px;">Lần tương tác này có <b>mục tiêu rõ ràng</b> đưa khách gần hơn tới ký không?</td></tr>'
            '</tbody></table>'
            + '<p style="' + lead + '">Còn ô nào &#8220;Chưa&#8221; &rArr; đó chính là '
            'việc phải làm trong lần liên hệ kế tiếp.</p>'

            + _box('#16a34a', '#f0fdf4', '&#127919;', 'Kết luận phải nhớ',
                   '<p style="margin-bottom:0;">Gửi báo giá là <b>BẮT ĐẦU</b>, không '
                   'phải kết thúc. Dẫn khách qua đủ <b>8 bước</b>, không bao giờ để '
                   'khách im lặng quá lâu &mdash; đó là cách nhân viên bình thường trở '
                   'thành nhân viên CHỐT được hợp đồng.</p>')
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    #  Thiết kế có ĐỘ KHÓ: đáp án nhiễu đều hợp lý, khiến NV phải phân vân.
    # ==================================================================
    def _vd_tdbg_questions(self):
        T, F = True, False
        return [
            ('Theo khóa học, gửi báo giá cho khách nên được hiểu là gì?',
             [('Điểm BẮT ĐẦU của quá trình chốt hợp đồng', T),
              ('Bước cuối cùng, sau đó chỉ việc chờ khách gọi lại', F),
              ('Dấu hiệu khách đã gần như đồng ý ký', F),
              ('Thời điểm nên ngừng liên hệ để khách tự cân nhắc', F)]),

            ('Khi khách IM LẶNG sau khi nhận báo giá, cách hiểu ĐÚNG là gì?',
             [('Quy trình đang bị dừng lại - cần chủ động tìm hiểu, không được để khách treo', T),
              ('Khách đã hết quan tâm, nên chuyển sang khách khác', F),
              ('Khách đang hài lòng nên không cần hỏi thêm', F),
              ('Nên chờ thêm ít nhất 1 tuần rồi mới liên hệ lại', F)]),

            ('Trước khi bấm GỬI báo giá, 3 câu hỏi tự kiểm bắt buộc theo thứ tự ưu tiên là gì?',
             [('Có khớp tầm tài chính khách đưa ra không + có phù hợp diện tích/công năng không + có đúng mong muốn khách không', T),
              ('Giá có rẻ hơn đối thủ không, có khuyến mãi không, có tặng quà không', F),
              ('Khách có gấp không, có thiện chí không, có dễ tính không', F),
              ('Không cần tự hỏi, cứ gửi kèm câu "anh/chị tham khảo nhé"', F)]),

            ('Khách nói tầm tài chính khoảng 2,8 tỷ nhưng nhân viên gửi báo giá 3,8 tỷ. Hậu quả ĐÚNG NHẤT là gì?',
             [('Báo giá không khớp tầm tài chính nên vô tác dụng - khách hết quan tâm và chuyển sang đối thủ tham khảo', T),
              ('Khách vẫn ký vì nghĩ chất lượng chắc chắn cao hơn', F),
              ('Không sao, vì cứ báo cao để còn thương lượng giảm dần', F),
              ('Khách sẽ tự xin giảm giá rồi ký luôn', F)]),

            ('Sau khi gửi báo giá bao lâu thì BẮT BUỘC phải lấy phản hồi từ khách?',
             [('Sau 1-2 ngày', T),
              ('Sau 1-2 tuần', F),
              ('Chỉ khi khách chủ động nhắn lại', F),
              ('Sau đúng 1 tháng', F)]),

            ('Mục tiêu THỰC SỰ của cuộc gọi lấy phản hồi sau báo giá là gì?',
             [('Để biết khách đang nghĩ gì, khai thác suy nghĩ thật của khách', T),
              ('Để ép khách ký hợp đồng ngay trong cuộc gọi', F),
              ('Để thông báo báo giá sắp hết hạn', F),
              ('Để hỏi khách đã chuyển tiền cọc chưa', F)]),

            ('Đâu là câu KHÔNG nên nói khi gửi mẫu nhà cho khách tham khảo?',
             [('"Anh chị chọn giúp em một mẫu nhé"', T),
              ('"Em gửi vài mẫu gần nhu cầu để mình tham khảo"', F),
              ('"Thích chi tiết nào bên em điều chỉnh thiết kế theo"', F),
              ('"Mấy mẫu này để anh chị có thêm ý tưởng ạ"', F)]),

            ('Vì sao KHÔNG được ép khách chốt mẫu nhà?',
             [('Vì khách không mua mẫu nhà, khách mua giải pháp phù hợp với gia đình mình', T),
              ('Vì mẫu nhà nào cũng giống nhau nên không cần chọn', F),
              ('Vì công ty không cho phép thay đổi mẫu', F),
              ('Vì chọn mẫu là việc của bộ phận thiết kế, không liên quan khách', F)]),

            ('Vì sao phải CHỦ ĐỘNG đôn đốc khách xem kỹ báo giá?',
             [('Vì nhiều khách không xem hoặc chưa xem kỹ, trong khi báo giá có phụ lục vật tư đầy đủ và tổng giá trị hợp đồng để khách đánh giá đúng', T),
              ('Vì để khách thấy mình sốt ruột mà ký cho nhanh', F),
              ('Vì công ty bắt buộc phải gọi đủ số cuộc mỗi ngày', F),
              ('Vì báo giá sẽ tự hết hạn nếu khách không xem ngay', F)]),

            ('Khi nhắc khách về thời gian khởi công (bước 4), ranh giới ĐÚNG là gì?',
             [('Giúp khách hiểu hệ quả của việc chậm quyết định, KHÔNG gây áp lực vô lý', T),
              ('Dọa khách rằng giá sẽ tăng gấp đôi nếu không ký ngay', F),
              ('Nói công ty sắp hết suất nhận công trình', F),
              ('Ép khách phải khởi công trong tuần này', F)]),

            ('Khách muốn diện tích rộng, công năng nhiều nhưng tầm tài chính KHÔNG đủ. Trước khi báo giá nên làm gì?',
             [('Cân đối, tư vấn phương án diện tích/công năng vừa với túi tiền khách rồi mới báo giá', T),
              ('Cứ tính đủ nhu cầu ra giá thật cao rồi gửi, khách tự liệu', F),
              ('Bỏ hết công năng khách muốn để hạ giá xuống thấp nhất', F),
              ('Gửi luôn báo giá vượt ngân sách để khách thấy đẳng cấp', F)]),

            ('Bước nào được khóa học coi là QUAN TRỌNG NHẤT trong quy trình theo đuổi?',
             [('Khai thác và xử lý vấn đề sau báo giá của khách', T),
              ('Gửi báo giá thật nhanh', F),
              ('Gửi thật nhiều mẫu nhà', F),
              ('Nhắc khách về tiền đặt cọc', F)]),

            ('Nếu khách vẫn CHƯA ký, nhân viên nên hiểu điều gì?',
             [('Chắc chắn còn vấn đề chưa được gỡ, phải tìm ra chứ không tự suy đoán', T),
              ('Khách keo kiệt nên bỏ qua, tìm khách mới', F),
              ('Do giá của mình cao, không thể làm gì thêm', F),
              ('Khách sẽ tự ký khi nào sẵn sàng, không cần làm gì', F)]),

            ('Trong 6 nhóm câu hỏi khai thác khúc mắc, nhóm nào giúp lộ ra RÀO CẢN THẬT SỰ trước khi ký?',
             [('Nhóm Niềm tin: "Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?"', T),
              ('Nhóm Báo giá: "Có vượt tài chính không?"', F),
              ('Nhóm Mẫu nhà: "Đã đúng phong cách chưa?"', F),
              ('Nhóm Khởi công: "Dự kiến khi nào?"', F)]),

            ('Nhóm câu hỏi "Gia đình" khi khai thác khúc mắc gồm ý nào?',
             [('Đã thống nhất chưa? Ai là người quyết định? Có cần trao đổi thêm với người thân không?', T),
              ('Nhà bao nhiêu tầng, mấy phòng ngủ?', F),
              ('Đã xem hợp đồng chưa, điều khoản nào chưa rõ?', F),
              ('Có vướng thủ tục pháp lý gì không?', F)]),

            ('Khi nào là thời điểm ĐÚNG để chuyển sang GỬI HỢP ĐỒNG và PHỤ LỤC (bước 6)?',
             [('Khi khách đã đồng ý báo giá, đồng ý phương án và không còn vướng mắc lớn', T),
              ('Ngay khi vừa gửi báo giá, để tạo áp lực chốt', F),
              ('Khi khách mới chỉ hỏi giá lần đầu', F),
              ('Khi khách còn nhiều băn khoăn nhưng mình muốn thúc', F)]),

            ('Sai lầm phổ biến ở bước KHAI THÁC và XỬ LÝ VẤN ĐỀ HỢP ĐỒNG (bước 7) là gì?',
             [('Gửi hợp đồng xong rồi mất hút, không chủ động hỏi lại để xử lý vướng mắc', T),
              ('Hỏi lại khách sau 1-2 ngày về điều khoản', F),
              ('Giải thích dứt điểm ngay khi khách còn băn khoăn', F),
              ('Gửi kèm lời mời khách trao đổi thêm', F)]),

            ('Sau khi gửi hợp đồng và phụ lục, sau bao lâu nên chủ động hỏi lại khách?',
             [('Sau 1-2 ngày', T),
              ('Chỉ hỏi khi khách chủ động liên hệ', F),
              ('Sau 2-3 tuần cho khách đủ thời gian', F),
              ('Không cần hỏi, chờ khách ký gửi lại', F)]),

            ('Ở bước 8 (bước cuối), khi khách đã đồng ý báo giá - thiết kế - hợp đồng thì việc tiếp theo là gì?',
             [('Thống nhất lịch ký hợp đồng, hẹn lịch khảo sát đất và trao đổi rõ quy trình + khoản đặt cọc', T),
              ('Gửi thêm một bộ báo giá mới để khách so sánh', F),
              ('Quay lại bước gửi mẫu nhà từ đầu', F),
              ('Chờ khách tự đến công ty ký', F)]),

            ('Theo NGUYÊN TẮC VÀNG, một nhân viên kinh doanh GIỎI được định nghĩa thế nào?',
             [('Người biết dẫn dắt khách đi qua từng bước tới quyết định ký, không phải người gửi được nhiều báo giá', T),
              ('Người gửi được nhiều báo giá nhất trong tháng', F),
              ('Người có giá chào thấp nhất cho khách', F),
              ('Người gọi cho khách nhiều lần nhất trong ngày', F)]),
        ]
