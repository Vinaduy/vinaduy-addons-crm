# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

TRÌNH BÀY (user chốt 2026-07-11): GIỮ ĐẦY ĐỦ nội dung, tổ chức bằng NHIỀU BẢNG
cho dễ học - dễ nhớ. Màu có QUY TẮC NHẤT QUÁN: mỗi callout 1 màu = 1 ý nghĩa cố
định xuyên suốt (KHÔNG loạn màu):
  - GHI NHỚ (cam)       : nguyên tắc cốt lõi
  - VIỆC PHẢI LÀM (xanh lá): việc hành động ngay - dạy NV làm gì
  - SAI LẦM CẦN TRÁNH (đỏ): lỗi thường gặp
  - CÂU MẪU NÊN NÓI (xanh dương): câu chữ để copy dùng
Bảng dùng chung 1 style xám nhạt. Banner bước nền slate. Không animation.

Thứ tự 8 bước: 1-Gửi mẫu nhà, 2-Gửi báo giá + đảm bảo chất lượng, 3-Phản hồi sau
1-2 ngày, 4-Nhắc khởi công + ký giữ giá, 5-Khai thác & xử lý vấn đề sau báo giá,
6-Gửi hợp đồng + phụ lục, 7-Khai thác & xử lý vấn đề hợp đồng, 8-Hẹn ký + khảo
sát đất.

Helper riêng prefix _tdbg_. Idempotent theo PHIÊN BẢN. Đảo đáp án mỗi lần thi do
overview.js xử lý chung. BẪY %: helper dùng '...' % (...) KHÔNG chứa % trong
template; bảng dựng bằng nối chuỗi (+) để width:50% an toàn.
"""
from odoo import api, models

_TDBG_VERSION = 'v4'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
_STYLE = (
    '<style>'
    '.vd-tdbg{max-width:820px;font-size:16.5px;line-height:1.72;color:#1f2937;}'
    '.vd-tdbg h2{font-size:23px;font-weight:800;color:#111827;margin:32px 0 12px;}'
    '.vd-tdbg h3{font-size:18px;font-weight:800;color:#111827;'
    'margin:22px 0 8px;padding-left:12px;border-left:4px solid #e8401f;}'
    '.vd-tdbg p{margin:0 0 12px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:0 0 14px;padding-left:24px;}'
    '.vd-tdbg li{margin:5px 0;}'
    '.vd-tdbg b{color:#111827;}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:12px 0 16px;font-size:15.5px;}'
    '.vd-tdbg th,.vd-tdbg td{border:1px solid #e5e7eb;padding:9px 12px;'
    'text-align:left;vertical-align:top;}'
    '.vd-tdbg th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-tdbg .cell-x{color:#b91c1c;font-weight:700;}'
    '.vd-tdbg .cell-v{color:#15803d;font-weight:700;}'
    '</style>'
)


# --- Callout: mỗi hàm 1 MÀU = 1 Ý NGHĨA cố định (template không chứa %) --------
def _callout(bar, bg, label_color, label, text):
    return (
        '<div style="background:%s;border-left:5px solid %s;border-radius:0 8px 8px 0;'
        'padding:12px 16px;margin:14px 0;">'
        '<div style="font-weight:800;color:%s;font-size:13.5px;letter-spacing:.3px;'
        'margin-bottom:4px;">%s</div><div>%s</div></div>'
    ) % (bg, bar, label_color, label, text)


def _key(text):
    return _callout('#e8401f', '#fff7ed', '#c2410c', '&#9873; GHI NHỚ', text)


def _todo(text):
    return _callout('#16a34a', '#f0fdf4', '#15803d', '&#9989; VIỆC PHẢI LÀM NGAY', text)


def _warn(text):
    return _callout('#dc2626', '#fef2f2', '#b91c1c', '&#9888;&#65039; SAI LẦM CẦN TRÁNH', text)


def _say(text):
    return _callout('#2563eb', '#eff6ff', '#1d4ed8', '&#128172; CÂU MẪU NÊN NÓI',
                    '<i>&#8220;' + text + '&#8221;</i>')


def _hero():
    return (
        '<div style="background:#e8401f;border-radius:14px;padding:30px 28px;'
        'margin-bottom:6px;">'
        '<div style="color:#ffe0d8;font-size:14px;font-weight:700;'
        'letter-spacing:2px;">KỸ NĂNG SALE &mdash; CHỐT HỢP ĐỒNG</div>'
        '<div style="color:#ffffff;font-size:29px;font-weight:800;margin-top:8px;'
        'line-height:1.2;">Theo đuổi khách hàng sau khi gửi báo giá</div>'
        '<div style="color:#fff2ee;font-size:16px;margin-top:12px;line-height:1.6;">'
        'Gửi báo giá chỉ là điểm BẮT ĐẦU, không phải kết thúc. Cả khóa dạy cách '
        'dẫn khách đi qua 8 bước tới lúc ký hợp đồng.</div></div>'
    )


def _step(num, title, sub):
    return (
        '<div style="background:#1e293b;border-radius:12px;padding:20px 24px;'
        'margin:40px 0 16px;">'
        '<div style="color:#f59e0b;font-size:13px;font-weight:800;'
        'letter-spacing:2px;">BƯỚC %s</div>'
        '<div style="color:#ffffff;font-size:23px;font-weight:800;margin-top:4px;'
        'line-height:1.25;">%s</div>'
        '<div style="color:#cbd5e1;font-size:14.5px;margin-top:7px;">%s</div></div>'
    ) % (num, title, sub)


def _table(head, rows, w0=None):
    """Dựng bảng bằng nối chuỗi (an toàn với %). head=list th; rows=list of list td."""
    th = ''.join(
        '<th' + (' style="width:%s;"' % w0 if (w0 and i == 0) else '') + '>' + h + '</th>'
        for i, h in enumerate(head))
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _vs(sai, dung):
    return ('<table><tr><th style="width:50%;" class="cell-x">&#10007; Nên tránh</th>'
            '<th class="cell-v">&#10003; Nên làm</th></tr>'
            '<tr><td>' + sai + '</td><td>' + dung + '</td></tr></table>')


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
        return [
            ('Hero', _hero()),
            ('Intro', self._tdbg_intro()),
            ('S1-MauNha', self._tdbg_maunha()),
            ('S2-BaoGia', self._tdbg_baogia()),
            ('S3-PhanHoi', self._tdbg_phanhoi()),
            ('S4-KhoiCong', self._tdbg_khoicong()),
            ('S5-KhaiThac', self._tdbg_khaithac()),
            ('S678-HopDong', self._tdbg_b678()),
            ('Gold', self._tdbg_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỞ ĐẦU
    # ------------------------------------------------------------------
    def _tdbg_intro(self):
        return (
            '<h2>Vì sao gửi báo giá xong KHÔNG được ngồi chờ?</h2>'
            '<p>Rất nhiều nhân viên mất khách chỉ vì nghĩ: <b>&#8220;Gửi báo giá rồi, '
            'giờ chờ khách gọi lại&#8221;</b>. Đây là sai lầm nghiêm trọng. Vì lúc này '
            'khách đang cùng lúc làm nhiều việc:</p>'
            + _table(
                ['Khách đang làm gì', 'Nghĩa là'],
                [['Xem <b>rất nhiều</b> đơn vị', 'Mình chỉ là 1 trong nhiều lựa chọn'],
                 ['Cân nhắc <b>tài chính</b>', 'Rất nhạy cảm với con số tổng'],
                 ['<b>Chưa hiểu hết</b> báo giá', 'Cần mình giải thích, dẫn dắt'],
                 ['Đang <b>so sánh</b> các bên', 'Ai chủ động hơn sẽ thắng'],
                 ['<b>Chưa biết nên hỏi gì</b>', 'Im lặng KHÔNG phải hết quan tâm']],
                w0='34%')
            + '<p>Nếu nhân viên không chủ động dẫn dắt, khách sẽ nghiêng dần sang đơn '
            'vị khác lúc nào không hay.</p>'

            + '<h3>Việc đầu tiên: chủ động ĐÔN ĐỐC khách xem báo giá</h3>'
            '<p>Gửi xong phải chủ động gọi/nhắn dò hỏi: khách đã <b>nhận</b> chưa, đã '
            '<b>mở xem</b> chưa, đã <b>đọc kỹ</b> chưa. Tuyệt đối không mặc định '
            '&#8220;gửi là khách sẽ xem&#8221;.</p>'
            + _warn('Thực tế nhiều khách KHÔNG xem báo giá, hoặc có xem nhưng CHƯA xem '
                    'kỹ &mdash; thậm chí lấy lý do &#8220;chưa xem&#8221;, &#8220;để '
                    'xem sau&#8221; để né trao đổi. Nếu mình tin ngay rồi ngồi chờ thì '
                    'báo giá nằm im, khách nguội dần rồi sang đối thủ.')
            + '<p>Vì sao phải đôn đốc? Vì trong báo giá của mình có những thứ khách bắt '
            'buộc phải đọc mới đánh giá đúng được giá trị:</p>'
            + _table(
                ['Trong báo giá có gì', 'Vai trò với khách'],
                [['<b>Phụ lục vật tư đầy đủ</b>', 'Chủng loại, thương hiệu, tiêu chuẩn &mdash; để khách so sánh chất lượng'],
                 ['<b>Tổng giá trị hợp đồng</b>', 'Con số đầy đủ, minh bạch &mdash; để khách cân đối tài chính']],
                w0='34%')
            + _key('Khách im lặng = quy trình đang bị DỪNG lại. Tuyệt đối không để '
                   'khách &#8220;treo&#8221;. Phải khéo léo hướng dẫn khách xem đúng '
                   'phụ lục vật tư và tổng giá trị hợp đồng.')

            + '<h3>Hành trình 8 bước phải thuộc lòng</h3>'
            + _table(
                ['Bước', 'Việc làm', 'Mục tiêu'],
                [['1', 'Gửi mẫu nhà tham khảo', 'Cho khách thêm ý tưởng, bộc lộ sở thích'],
                 ['2', 'Gửi báo giá &mdash; đảm bảo chất lượng', 'Báo giá khớp tài chính, đúng nhu cầu'],
                 ['3', 'Phản hồi sau 1&ndash;2 ngày', 'Biết khách đang nghĩ gì'],
                 ['4', 'Nhắc khởi công &amp; ký giữ giá', 'Tạo lý do quyết định sớm'],
                 ['5', 'Khai thác &amp; xử lý vấn đề sau báo giá', 'Gỡ hết khúc mắc (bước quan trọng nhất)'],
                 ['6', 'Gửi hợp đồng &amp; phụ lục', 'Chuyển sang giai đoạn ký'],
                 ['7', 'Khai thác &amp; xử lý vấn đề hợp đồng', 'Gỡ vướng mắc điều khoản'],
                 ['8', 'Hẹn ký hợp đồng &amp; khảo sát đất', 'Chốt lịch ký, đặt cọc']],
                w0='8%')
            + _key('Sau MỖI lần liên hệ, khách phải tiến thêm ít nhất 1 bước. Mỗi lần '
                   'trao đổi đều phải có mục tiêu rõ ràng, đưa khách gần hơn tới ký.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 1 — GỬI MẪU NHÀ
    # ------------------------------------------------------------------
    def _tdbg_maunha(self):
        return (
            _step('1', 'Gửi mẫu nhà cho khách tham khảo',
                  'Làm đầu tiên &mdash; nhưng KHÔNG ép khách chốt mẫu.')
            + '<p>Đây là việc nên làm sớm để khách có cơ sở hình dung. Nhưng phải nhớ '
            'rõ mục tiêu:</p>'
            '<ul>'
            '<li>Cho khách <b>thêm ý tưởng</b>.</li>'
            '<li>Cho khách thấy <b>nhiều lựa chọn</b>.</li>'
            '<li>Giúp khách <b>xác định sở thích</b>.</li>'
            '</ul>'
            + _vs('&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;<br/>&rArr; Ép khách '
                  'chốt mẫu, khách thấy áp lực.',
                  'Gửi mẫu gần nhu cầu để tham khảo, thích chi tiết nào thì mình điều '
                  'chỉnh thiết kế theo.')
            + _say('Em gửi thêm vài mẫu nhà có diện tích và mức đầu tư gần với nhu cầu '
                   'của anh/chị để mình tham khảo. Chi tiết nào anh/chị thích, bên em '
                   'sẽ điều chỉnh thiết kế theo đúng mong muốn của gia đình.')
            + _key('Khách KHÔNG mua mẫu nhà &mdash; khách mua giải pháp phù hợp với '
                   'gia đình mình. Mẫu nhà chỉ để khách hình dung và bộc lộ sở thích.')
            + _todo('Gửi 3&ndash;5 mẫu sát diện tích + mức đầu tư của khách, kèm đúng '
                    'câu mẫu ở trên. Mục tiêu là MỞ Ý TƯỞNG, không bắt khách chọn.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 2 — GỬI BÁO GIÁ & ĐẢM BẢO CHẤT LƯỢNG (trọng tâm khóa)
    # ------------------------------------------------------------------
    def _tdbg_baogia(self):
        return (
            _step('2', 'Gửi báo giá và đảm bảo chất lượng báo giá',
                  'Việc quan trọng bậc nhất: đã gửi thì báo giá phải THẬT CHUẨN.')
            + '<p>Báo giá không phải &#8220;một file gửi cho có&#8221; &mdash; nó là '
            '<b>vũ khí chốt hợp đồng</b>. Một khi đã quyết định gửi thì báo giá đó bắt '
            'buộc phải thật chuẩn. Tất cả nhân viên kinh doanh phải tập trung TỐI ĐA '
            'cho việc làm báo giá.</p>'
            + _key('Báo giá KHÔNG khớp tầm tài chính của khách = báo giá VÔ TÁC DỤNG. '
                   'Khách sẽ không quan tâm nữa và chuyển sang đối thủ để tham khảo tiếp. '
                   'Đây là lý do phải làm báo giá thật chuẩn trước khi gửi.')

            + '<h3>&#8220;Chuẩn&#8221; nghĩa là gì? &mdash; 3 điều kiện</h3>'
            + _table(
                ['Điều kiện', 'Ý nghĩa'],
                [['<b>1. Khớp tầm tài chính khách đưa ra</b><br/><span style="color:#b91c1c;">(quan trọng nhất)</span>',
                  'Tổng giá trị phải nằm TRONG khoảng ngân sách khách nói. Đây là yếu tố quyết định khách có quan tâm báo giá hay không.'],
                 ['<b>2. Phù hợp diện tích và công năng khách muốn</b>',
                  'Số tầng, số phòng, công năng phải cân đối được với tầm tài chính đó.'],
                 ['<b>3. Đúng mong muốn và phong cách</b>',
                  'Phong cách, mức hoàn thiện, thang máy / gara / sân... khớp điều khách mong.']],
                w0='34%')

            + '<h3>Báo giá lệch = hỏng cả cuộc chơi</h3>'
            '<p>Chỉ cần lệch nhu cầu là khách loại mình ngay, dù mình không hề biết:</p>'
            + _table(
                ['Khách nói / muốn', 'Nếu gửi lệch', 'Kết quả'],
                [['Tài chính khoảng <b>2,8 tỷ</b>', 'Gửi báo giá <b>3,8 tỷ</b>', '<span class="cell-x">SAI</span>'],
                 ['Thích phong cách <b>hiện đại</b>', 'Báo giá mẫu <b>tân cổ</b>', '<span class="cell-x">SAI</span>'],
                 ['Muốn xây <b>để ở</b>', 'Làm theo chuẩn <b>đầu tư</b>', '<span class="cell-x">SAI</span>']],
                w0='34%')
            + '<p>Nhiều khi khách muốn <b>diện tích rộng, công năng nhiều</b> nhưng '
            '<b>tài chính không đủ</b>. Nếu bê nguyên nhu cầu đó tính ra, chi phí sẽ '
            'cao hơn ngân sách rất nhiều. Việc của nhân viên là <b>cân đối</b>: tư vấn '
            'phương án diện tích + công năng vừa túi tiền khách, chứ không gửi một con '
            'số vượt xa rồi để khách tự sốc.</p>'
            + _warn('Khách nói tầm 2,8 tỷ mà gửi báo giá 3,8 tỷ. Khách nhìn con số đầu '
                    'đã thấy vượt quá xa &mdash; không đọc tiếp, không phản hồi, âm '
                    'thầm loại mình rồi đi tham khảo bên khác. Mình mất khách mà không '
                    'hề hay biết.')

            + '<h3>Trước khi bấm GỬI, tự trả lời 3 câu hỏi</h3>'
            + _table(
                ['Câu hỏi tự kiểm', 'Nếu CHƯA đạt'],
                [['<b>1. Có khớp tầm tài chính khách đưa ra không?</b> (ưu tiên số 1)',
                  'Vượt ngân sách &rArr; CHƯA gửi, phải cân đối lại phương án.'],
                 ['<b>2. Có phù hợp diện tích và công năng khách đưa ra không?</b>',
                  'Nhu cầu quá lớn so với ngân sách &rArr; tư vấn điều chỉnh trước.'],
                 ['<b>3. Có đúng mong muốn của khách chưa?</b>',
                  'Lệch phong cách / hoàn thiện / thang máy / gara &rArr; sửa cho khớp.']],
                w0='50%')
            + _key('Nếu mình là khách, mình cũng thấy báo giá này KHỚP TÚI TIỀN và hợp '
                   'lý &mdash; đó mới là báo giá đạt yêu cầu.')
            + _todo('Soát đủ 3 câu hỏi, ưu tiên số 1 là KHỚP TẦM TÀI CHÍNH. Còn lệch '
                    'tài chính / diện tích / công năng &rArr; DỪNG, cân đối lại phương '
                    'án rồi mới gửi. Đã gửi thì báo giá phải thật chuẩn.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 3 — PHẢN HỒI SAU 1-2 NGÀY
    # ------------------------------------------------------------------
    def _tdbg_phanhoi(self):
        return (
            _step('3', 'Sau 1&ndash;2 ngày bắt buộc lấy phản hồi',
                  'Gửi báo giá xong rồi im luôn = nguyên nhân mất rất nhiều khách.')
            + _warn('Gửi báo giá xong rồi IM LUÔN: không gọi, không nhắn, không hỏi. '
                    'Đây là sai lầm khiến mất rất nhiều khách hàng.')
            + '<h3>Mục tiêu cuộc gọi phản hồi</h3>'
            + _vs('Gọi để <b>ép khách ký</b> ngay.<br/>Hỏi cụt lủn &#8220;anh chị ký '
                  'chưa?&#8221;.',
                  'Gọi để <b>BIẾT khách đang nghĩ gì</b>.<br/>Khai thác suy nghĩ thật '
                  'của khách để dẫn tiếp.')
            + '<p>Bộ câu hỏi cần khai thác trong 1&ndash;2 ngày sau khi gửi:</p>'
            '<ul>'
            '<li>Anh/chị đã <b>xem báo giá</b> chưa?</li>'
            '<li>Thấy <b>phần nào hợp lý</b>? <b>Phần nào còn băn khoăn</b>?</li>'
            '<li><b>Mức đầu tư</b> có phù hợp không?</li>'
            '<li>Có <b>hạng mục nào</b> muốn điều chỉnh không?</li>'
            '</ul>'
            + '<h3>Khách im lặng &mdash; đừng vội kết luận &#8220;hết quan tâm&#8221;</h3>'
            + _table(
                ['Khách im lặng có thể vì', 'Việc mình cần làm'],
                [['Báo giá cao hơn dự kiến', 'Giải thích giá trị / cân đối lại phương án'],
                 ['Báo giá chưa đúng nhu cầu', 'Hỏi lại nhu cầu, chỉnh cho khớp'],
                 ['Chưa hiểu cách tính', 'Giải thích phụ lục, cách ra con số'],
                 ['Đang chờ đơn vị khác', 'Tạo khác biệt, nhắc lợi thế của mình'],
                 ['Chưa đủ niềm tin', 'Đưa chứng minh, công trình thực tế'],
                 ['Chưa biết nên hỏi gì', 'Chủ động gợi câu hỏi, dẫn dắt']],
                w0='40%')
            + _key('Khách im KHÔNG có nghĩa là hết quan tâm. Việc của nhân viên là '
                   'KHAI THÁC, không phải ĐOÁN.')
            + _todo('Đặt lịch nhắc: 1&ndash;2 ngày sau khi gửi báo giá là gọi lấy '
                    'phản hồi. Mục tiêu cuộc gọi là hiểu suy nghĩ khách, tuyệt đối '
                    'không ép ký.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 4 — KHỞI CÔNG + KÝ GIỮ GIÁ
    # ------------------------------------------------------------------
    def _tdbg_khoicong(self):
        return (
            _step('4', 'Nhắc thời gian khởi công và ký hợp đồng giữ giá',
                  'Đặc biệt cuối năm &mdash; khách nào cũng muốn xong trước Tết.')
            + '<p>Nếu khởi công muộn, khách sẽ gặp một loạt bất lợi &mdash; đây chính '
            'là lý do để khách cần quyết định sớm:</p>'
            + _table(
                ['Khởi công muộn dẫn tới', 'Hệ quả cho khách'],
                [['Thi công gấp', 'Chất lượng, an toàn dễ bị ảnh hưởng'],
                 ['Ảnh hưởng tiến độ', 'Khó kịp mốc ở trước Tết'],
                 ['Khó bàn giao', 'Dễ trễ hẹn, phát sinh'],
                 ['Khó hoàn thiện', 'Cuối năm thợ đông, làm gấp áp lực']],
                w0='40%')
            + _say('Nếu gia đình mình dự kiến ở nhà mới trước Tết thì nên triển khai '
                   'sớm để đảm bảo tiến độ. Để quá sát cuối năm thì việc hoàn thiện sẽ '
                   'rất áp lực.')
            + '<h3>Ký hợp đồng giữ giá (nếu công ty có chính sách)</h3>'
            '<p>Khi khách chưa khởi công ngay nhưng đã ưng phương án, có thể đề xuất '
            '<b>ký hợp đồng giữ giá</b> để khách chốt được mức giá hiện tại, tránh '
            'biến động khi vật tư tăng. Vừa lợi cho khách, vừa giúp mình giữ chân '
            'khách, không để trôi sang đối thủ trong lúc còn cân nhắc.</p>'
            + _say('Hiện bên em đang áp mức giá này, nếu anh/chị chốt phương án thì '
                   'mình có thể ký hợp đồng giữ giá để khóa mức giá hôm nay, sau này '
                   'vật tư tăng gia đình cũng không bị ảnh hưởng ạ.')
            + _key('Mục tiêu là giúp khách hiểu HỆ QUẢ của việc chậm quyết định, KHÔNG '
                   'gây áp lực vô lý, không dọa khách.')
            + _todo('Khéo gắn quyết định của khách với mốc thời gian (trước Tết / kịp '
                    'tiến độ) và đề xuất ký giữ giá nếu có chính sách.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 5 — KHAI THÁC & XỬ LÝ VẤN ĐỀ SAU BÁO GIÁ (quan trọng nhất)
    # ------------------------------------------------------------------
    def _tdbg_khaithac(self):
        return (
            _step('5', 'Khai thác và xử lý vấn đề sau báo giá',
                  'Bước quan trọng nhất: khách chưa ký thì chắc chắn còn vấn đề.')
            + '<p>Nếu khách chưa ký, chắc chắn còn vấn đề &mdash; nhân viên phải TÌM '
            'RA, không được tự suy đoán. Khai thác đủ theo <b>6 nhóm câu hỏi</b>:</p>'
            + _table(
                ['Nhóm', 'Câu hỏi cần khai thác'],
                [['<b>1. Báo giá</b>', 'Có phù hợp không? Có vượt tài chính không? Có cần điều chỉnh không?'],
                 ['<b>2. Thiết kế</b>', 'Có thích không? Cần thay đổi gì? Cần thêm công năng không?'],
                 ['<b>3. Mẫu nhà</b>', 'Đã đúng phong cách chưa? Có muốn tham khảo thêm không?'],
                 ['<b>4. Gia đình</b>', 'Đã thống nhất chưa? Ai là người quyết định? Cần trao đổi thêm với người thân không?'],
                 ['<b>5. Khởi công</b>', 'Dự kiến khi nào? Đang chờ việc gì không? Có vướng thủ tục không?'],
                 ['<b>6. Niềm tin</b>', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?']],
                w0='20%')
            + _key('Câu hỏi nhóm NIỀM TIN đắt giá nhất: giúp lộ ra rào cản THẬT SỰ '
                   'trước khi ký. Luôn kết thúc bằng câu hỏi này.')
            + _todo('Mỗi khách chưa chốt, chạy đủ 6 nhóm câu hỏi để tìm khúc mắc thật, '
                    'rồi XỬ LÝ dứt điểm từng cái. Luôn kết bằng câu hỏi niềm tin.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 6-7-8 — HỢP ĐỒNG
    # ------------------------------------------------------------------
    def _tdbg_b678(self):
        return (
            _step('6 &middot; 7 &middot; 8',
                  'Gửi hợp đồng &amp; phụ lục &rarr; xử lý vấn đề &rarr; hẹn ký &amp; khảo sát đất',
                  'Giai đoạn chốt: hết vấn đề sau báo giá thì phải chuyển bước ngay.')
            + '<h3>Bước 6 &mdash; Gửi hợp đồng và phụ lục</h3>'
            '<p>Khi khách đã <b>đồng ý báo giá + đồng ý phương án + hết vướng mắc lớn</b>, '
            'đừng nói chuyện chung chung nữa &mdash; gửi hợp đồng kèm <b>đầy đủ phụ '
            'lục</b> (vật tư, hạng mục, tổng giá trị) để khách nghiên cứu và nắm rõ '
            'mình cam kết những gì.</p>'
            + _say('Để gia đình xem kỹ các điều khoản, bên em gửi trước hợp đồng kèm '
                   'đầy đủ phụ lục để anh/chị đọc. Có nội dung nào cần giải thích hoặc '
                   'điều chỉnh, em trao đổi ngay để mình yên tâm trước khi ký.')

            + '<h3>Bước 7 &mdash; Khai thác và xử lý vấn đề hợp đồng</h3>'
            + _warn('Gửi hợp đồng xong rồi MẤT HÚT. Đây là sai lầm của rất nhiều nhân viên.')
            + '<p>Điều đúng: <b>sau 1&ndash;2 ngày chủ động hỏi lại</b> để khai thác '
            'và xử lý mọi vướng mắc trong hợp đồng:</p>'
            '<ul>'
            '<li>Anh/chị đã <b>xem hợp đồng và phụ lục</b> chưa?</li>'
            '<li>Có <b>điều khoản nào chưa rõ</b> không?</li>'
            '<li>Có nội dung nào muốn <b>trao đổi hoặc điều chỉnh</b> không?</li>'
            '</ul>'
            '<p>Khách còn băn khoăn về hợp đồng thì phải giải quyết <b>dứt điểm</b> '
            'ngay, không bỏ qua.</p>'

            + '<h3>Bước 8 &mdash; Hẹn ký hợp đồng và khảo sát đất</h3>'
            '<p>Khi khách đã đồng ý <b>báo giá + thiết kế + hợp đồng</b>, bước cuối cùng:</p>'
            + _table(
                ['Việc cần làm', 'Ghi chú'],
                [['Thống nhất <b>lịch ký hợp đồng</b>', 'Chốt ngày giờ cụ thể'],
                 ['Hẹn <b>lịch khảo sát đất</b> thực tế', 'Đo đạc, đánh giá hiện trạng'],
                 ['Trao đổi quy trình ký + <b>đặt cọc 50.000.000đ</b>', 'Theo quy định công ty (nếu áp dụng), để khách chủ động sắp xếp']],
                w0='44%')
            + _todo('Hết vấn đề sau báo giá &rArr; gửi hợp đồng + phụ lục ngay. Sau '
                    '1&ndash;2 ngày hỏi lại xử lý vấn đề hợp đồng, rồi chốt lịch KÝ + '
                    'KHẢO SÁT ĐẤT.')
        )

    # ------------------------------------------------------------------
    #  NGUYÊN TẮC VÀNG + BẢNG TỰ KIỂM
    # ------------------------------------------------------------------
    def _tdbg_gold(self):
        return (
            '<h2>&#127942; Nguyên tắc vàng</h2>'
            '<p style="font-size:18px;color:#111827;font-weight:700;">Nhân viên giỏi '
            'KHÔNG phải người gửi được NHIỀU báo giá, mà là người biết DẪN DẮT khách '
            'đi qua từng bước tới quyết định ký.</p>'
            '<p>Sau mỗi lần liên hệ, nếu khách tiến thêm một bước (phản hồi báo giá '
            '&rarr; gỡ vấn đề &rarr; xem hợp đồng &rarr; hẹn khảo sát...) thì khả năng '
            'ký tăng lên rất nhiều. Không bao giờ để khách im lặng quá lâu.</p>'

            + '<h3>Bảng tự kiểm sau MỖI lần liên hệ khách</h3>'
            + _table(
                ['#', 'Tự hỏi (Có / Chưa)'],
                [['1', 'Lần này khách đã <b>tiến thêm 1 bước</b> chưa?'],
                 ['2', 'Mình đã <b>biết khách đang nghĩ gì</b> chưa, hay chỉ đang đoán?'],
                 ['3', 'Còn <b>vấn đề nào chưa gỡ</b> (tài chính / thiết kế / gia đình / niềm tin)?'],
                 ['4', 'Đã hẹn <b>mốc liên hệ tiếp theo</b> chưa?'],
                 ['5', 'Lần này có <b>mục tiêu rõ ràng</b> đưa khách gần hơn tới ký không?']],
                w0='8%')
            + _key('Còn ô nào &#8220;Chưa&#8221; &mdash; đó chính là việc phải làm '
                   'trong lần liên hệ kế tiếp. Gửi báo giá là BẮT ĐẦU, không phải kết thúc.')
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
