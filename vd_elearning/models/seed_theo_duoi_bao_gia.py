# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

TRÌNH BÀY TỐI GIẢN (user chốt 2026-07-11): bỏ animation, bỏ ô/khung/màu rối
mắt. Chỉ dùng 1 màu nhấn (#e8401f), nền slate cho banner bước, còn lại là chữ
sạch để nhân viên DỄ ĐỌC - DỄ NHỚ. Toàn bộ typography (h2/h3/p/ul/table) do khối
<style> scope .vd-tdbg lo, nội dung viết HTML thuần. Chỉ 2 kiểu callout: "Ghi
nhớ" và "Câu mẫu".

Thứ tự 8 bước (thực tế): 1-Gửi mẫu nhà, 2-Gửi báo giá + đảm bảo chất lượng,
3-Phản hồi sau 1-2 ngày, 4-Nhắc khởi công + ký giữ giá, 5-Khai thác & xử lý vấn
đề sau báo giá, 6-Gửi hợp đồng + phụ lục, 7-Khai thác & xử lý vấn đề hợp đồng,
8-Hẹn ký + khảo sát đất.

Helper riêng prefix _tdbg_ (xem reference-seed-method-name-collision). Idempotent
theo PHIÊN BẢN. Đảo đáp án mỗi lần thi do overview.js xử lý chung.
"""
from odoo import api, models

_TDBG_VERSION = 'v3'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_ACCENT = '#e8401f'

# Base typography - scope .vd-tdbg. Không dùng % format -> % an toàn.
_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
_STYLE = (
    '<style>'
    '.vd-tdbg{max-width:800px;font-size:16.5px;line-height:1.72;color:#1f2937;}'
    '.vd-tdbg h2{font-size:23px;font-weight:800;color:#111827;margin:34px 0 12px;}'
    '.vd-tdbg h3{font-size:18px;font-weight:800;color:#111827;'
    'margin:22px 0 8px;padding-left:12px;border-left:4px solid #e8401f;}'
    '.vd-tdbg p{margin:0 0 12px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:0 0 14px;padding-left:24px;}'
    '.vd-tdbg li{margin:5px 0;}'
    '.vd-tdbg b{color:#111827;}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:12px 0 16px;font-size:15.5px;}'
    '.vd-tdbg th,.vd-tdbg td{border:1px solid #e5e7eb;padding:9px 12px;'
    'text-align:left;vertical-align:top;}'
    '.vd-tdbg th{background:#f9fafb;font-weight:800;color:#374151;}'
    '</style>'
)


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
    """Banner 1 bước - nền slate, tối giản."""
    return (
        '<div style="background:#1e293b;border-radius:12px;padding:20px 24px;'
        'margin:38px 0 16px;">'
        '<div style="color:#f59e0b;font-size:13px;font-weight:800;'
        'letter-spacing:2px;">BƯỚC %s</div>'
        '<div style="color:#ffffff;font-size:23px;font-weight:800;margin-top:4px;'
        'line-height:1.25;">%s</div>'
        '<div style="color:#cbd5e1;font-size:14.5px;margin-top:7px;">%s</div></div>'
    ) % (num, title, sub)


def _key(text):
    """Callout DUY NHẤT cho điểm cần nhớ - nền ấm nhạt, gạch trái màu nhấn."""
    return (
        '<div style="background:#fff7ed;border-left:4px solid %s;'
        'border-radius:0 8px 8px 0;padding:12px 16px;margin:14px 0;">'
        '<b style="color:#c2410c;">&#9888;&#65039; Ghi nhớ:</b> %s</div>'
    ) % (_ACCENT, text)


def _say(text):
    """Câu mẫu nên nói - in nghiêng, gạch xám, không màu mè."""
    return (
        '<div style="border-left:3px solid #cbd5e1;padding:6px 16px;margin:12px 0;'
        'color:#374151;font-style:italic;">'
        '&#128172; Câu mẫu: &#8220;%s&#8221;</div>'
    ) % text


def _vs(sai, dung):
    """Bảng 2 cột Nên tránh / Nên làm - dùng style bảng chung, không tô nền đậm."""
    return (
        '<table><tr><th style="width:50%%;">&#10007; Nên tránh</th>'
        '<th>&#10003; Nên làm</th></tr>'
        '<tr><td>%s</td><td>%s</td></tr></table>'
    ) % (sai, dung)


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
        steps = [
            'Gửi mẫu nhà tham khảo',
            'Gửi báo giá &mdash; đảm bảo chất lượng',
            'Phản hồi sau 1&ndash;2 ngày',
            'Nhắc khởi công &amp; ký giữ giá',
            'Khai thác &amp; xử lý vấn đề sau báo giá',
            'Gửi hợp đồng &amp; phụ lục',
            'Khai thác &amp; xử lý vấn đề hợp đồng',
            'Hẹn ký hợp đồng &amp; khảo sát đất',
        ]
        li = ''.join('<li><b>%s</b></li>' % s for s in steps)
        return (
            '<h2>Vì sao gửi báo giá xong KHÔNG được ngồi chờ?</h2>'
            '<p>Nhiều nhân viên mất khách chỉ vì nghĩ: <b>&#8220;Gửi báo giá rồi, '
            'giờ chờ khách gọi lại&#8221;</b>. Đây là sai lầm. Khách xây nhà thường '
            'xem nhiều đơn vị, đang cân nhắc tài chính, chưa hiểu hết báo giá và đang '
            'so sánh. Nếu mình không chủ động dẫn dắt, khách sẽ nghiêng dần sang đơn '
            'vị khác.</p>'

            '<h3>Việc đầu tiên: chủ động ĐÔN ĐỐC khách xem báo giá</h3>'
            '<p>Gửi xong phải chủ động gọi/nhắn dò hỏi: khách đã <b>nhận</b> chưa, đã '
            '<b>mở xem</b> chưa, đã <b>đọc kỹ</b> chưa. Thực tế nhiều khách không xem, '
            'hoặc xem chưa kỹ, thậm chí lấy lý do &#8220;chưa xem&#8221; để tránh trao '
            'đổi. Nếu mình tin ngay rồi ngồi chờ thì báo giá nằm im, khách nguội dần.</p>'
            '<p>Trong báo giá của mình có <b>phụ lục vật tư đầy đủ</b> và <b>tổng giá '
            'trị hợp đồng</b> &mdash; đây là thứ khách cần để so sánh và ra quyết định. '
            'Khách chưa xem kỹ phần này thì chưa thể đánh giá đúng giá trị mình mang '
            'lại. Vì vậy phải khéo léo hướng dẫn khách xem đúng các mục quan trọng.</p>'
            + _key('Khách im lặng nghĩa là quy trình đang bị DỪNG lại &mdash; tuyệt '
                   'đối không để khách &#8220;treo&#8221;.')

            + '<h3>Hành trình 8 bước</h3>'
            '<ol>' + li + '</ol>'
            '<p>Nguyên tắc xuyên suốt: <b>sau mỗi lần liên hệ, khách phải tiến thêm '
            'ít nhất 1 bước</b>. Mỗi lần trao đổi đều phải có mục tiêu rõ ràng, đưa '
            'khách gần hơn tới quyết định ký.</p>'
        )

    # ------------------------------------------------------------------
    #  BƯỚC 1 — GỬI MẪU NHÀ
    # ------------------------------------------------------------------
    def _tdbg_maunha(self):
        return (
            _step('1', 'Gửi mẫu nhà cho khách tham khảo',
                  'Làm đầu tiên &mdash; nhưng KHÔNG ép khách chốt mẫu.')
            + '<p>Mục tiêu khi gửi mẫu nhà:</p>'
            '<ul>'
            '<li>Cho khách <b>thêm ý tưởng</b>.</li>'
            '<li>Cho khách thấy <b>nhiều lựa chọn</b>.</li>'
            '<li>Giúp khách <b>xác định sở thích</b>.</li>'
            '</ul>'
            + _vs('&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221; &mdash; ép khách '
                  'chốt mẫu, khách thấy áp lực.',
                  'Gửi mẫu gần nhu cầu để tham khảo, thích chi tiết nào thì mình điều '
                  'chỉnh thiết kế theo.')
            + _say('Em gửi thêm vài mẫu nhà có diện tích và mức đầu tư gần với nhu cầu '
                   'của anh/chị để mình tham khảo. Chi tiết nào anh/chị thích, bên em '
                   'sẽ điều chỉnh thiết kế theo đúng mong muốn của gia đình.')
            + _key('Khách không mua mẫu nhà &mdash; khách mua giải pháp phù hợp với '
                   'gia đình mình. Mẫu nhà chỉ để khách hình dung và bộc lộ sở thích.')
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
            'buộc phải thật chuẩn. Cả nhân viên phải tập trung tối đa cho việc này.</p>'

            + _key('Báo giá không khớp tầm tài chính của khách = báo giá VÔ TÁC DỤNG. '
                   'Khách sẽ không quan tâm nữa và chuyển sang đối thủ để tham khảo tiếp.')

            + '<h3>&#8220;Chuẩn&#8221; nghĩa là gì? &mdash; 3 điều kiện</h3>'
            '<table>'
            '<tr><th style="width:34%;">Điều kiện</th><th>Ý nghĩa</th></tr>'
            '<tr><td><b>1. Khớp tầm tài chính khách đưa ra</b> (quan trọng nhất)</td>'
            '<td>Tổng giá trị phải nằm TRONG khoảng ngân sách khách nói. Đây là yếu tố '
            'quyết định khách có quan tâm báo giá hay không.</td></tr>'
            '<tr><td><b>2. Phù hợp diện tích và công năng khách muốn</b></td>'
            '<td>Số tầng, số phòng, công năng phải cân đối được với tầm tài chính đó.</td></tr>'
            '<tr><td><b>3. Đúng mong muốn và phong cách</b></td>'
            '<td>Phong cách, mức hoàn thiện, thang máy / gara / sân... khớp điều khách mong.</td></tr>'
            '</table>'

            + '<h3>Vì sao lệch tài chính là hỏng cả cuộc chơi?</h3>'
            '<p>Khách nói tầm <b>2,8 tỷ</b> nhưng mình gửi báo giá <b>3,8 tỷ</b>. '
            'Khách nhìn con số đầu đã thấy vượt quá xa &mdash; không đọc tiếp, không '
            'phản hồi, âm thầm loại mình rồi tiếp tục tham khảo bên khác. Mình mất '
            'khách mà không hề hay biết.</p>'
            '<p>Nhiều khi khách muốn <b>diện tích rộng, công năng nhiều</b> nhưng '
            '<b>tài chính không đủ</b>. Nếu bê nguyên nhu cầu đó tính ra, chi phí sẽ '
            'cao hơn ngân sách rất nhiều. Việc của nhân viên là <b>cân đối</b>: tư vấn '
            'phương án diện tích + công năng vừa túi tiền khách, chứ không gửi một con '
            'số vượt xa rồi để khách tự sốc.</p>'

            + '<h3>Trước khi bấm GỬI, tự trả lời 3 câu hỏi</h3>'
            '<ol>'
            '<li><b>Có khớp tầm tài chính khách đưa ra không?</b> (ưu tiên số 1) '
            '&mdash; vượt ngân sách thì CHƯA gửi, phải cân đối lại.</li>'
            '<li><b>Có phù hợp diện tích và công năng khách đưa ra không?</b> '
            '&mdash; nhu cầu quá lớn so với ngân sách thì tư vấn điều chỉnh trước.</li>'
            '<li><b>Có đúng mong muốn của khách chưa?</b> &mdash; phong cách, mức hoàn '
            'thiện, thang máy / gara / sân...</li>'
            '</ol>'
            + _key('Một khi đã quyết định gửi thì báo giá phải thật chuẩn. Nếu mình là '
                   'khách, mình cũng thấy báo giá này khớp túi tiền và hợp lý &mdash; '
                   'đó mới là báo giá đạt yêu cầu.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 3 — PHẢN HỒI SAU 1-2 NGÀY
    # ------------------------------------------------------------------
    def _tdbg_phanhoi(self):
        return (
            _step('3', 'Sau 1&ndash;2 ngày bắt buộc lấy phản hồi',
                  'Gửi báo giá xong rồi im luôn = nguyên nhân mất rất nhiều khách.')
            + '<p>Sai lầm lớn nhất: gửi báo giá xong rồi <b>im luôn</b> &mdash; không '
            'gọi, không nhắn, không hỏi. Mục tiêu cuộc gọi phản hồi không phải để ép '
            'ký, mà để <b>biết khách đang nghĩ gì</b>.</p>'
            '<p>Bộ câu hỏi cần khai thác:</p>'
            '<ul>'
            '<li>Anh/chị đã <b>xem báo giá</b> chưa?</li>'
            '<li>Thấy <b>phần nào hợp lý</b>, <b>phần nào còn băn khoăn</b>?</li>'
            '<li><b>Mức đầu tư</b> có phù hợp không?</li>'
            '<li>Có <b>hạng mục nào</b> muốn điều chỉnh không?</li>'
            '</ul>'
            '<p>Khách im lặng <b>không</b> có nghĩa là hết quan tâm. Có thể vì: báo giá '
            'cao hơn dự kiến, chưa đúng nhu cầu, chưa hiểu cách tính, đang chờ đơn vị '
            'khác, hoặc chưa đủ niềm tin.</p>'
            + _key('Việc của nhân viên là KHAI THÁC, không phải ĐOÁN. Đặt lịch nhắc '
                   '1&ndash;2 ngày sau khi gửi để gọi lấy phản hồi.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 4 — KHỞI CÔNG + KÝ GIỮ GIÁ
    # ------------------------------------------------------------------
    def _tdbg_khoicong(self):
        return (
            _step('4', 'Nhắc thời gian khởi công và ký hợp đồng giữ giá',
                  'Đặc biệt cuối năm &mdash; khách nào cũng muốn xong trước Tết.')
            + '<p>Nếu khởi công muộn, khách dễ gặp bất lợi: thi công gấp, ảnh hưởng '
            'tiến độ, khó bàn giao, khó hoàn thiện. Nhân viên chủ động nhắc khách về '
            'yếu tố thời gian.</p>'
            + _say('Nếu gia đình mình dự kiến ở nhà mới trước Tết thì nên triển khai '
                   'sớm để đảm bảo tiến độ. Để quá sát cuối năm thì việc hoàn thiện sẽ '
                   'rất áp lực.')
            + '<h3>Ký hợp đồng giữ giá (nếu công ty có chính sách)</h3>'
            '<p>Khi khách chưa khởi công ngay nhưng đã ưng phương án, có thể đề xuất '
            '<b>ký hợp đồng giữ giá</b> để khách chốt được mức giá hiện tại, tránh '
            'biến động khi vật tư tăng. Vừa lợi cho khách, vừa giúp mình giữ chân '
            'khách, không để trôi sang đối thủ.</p>'
            + _say('Hiện bên em đang áp mức giá này, nếu anh/chị chốt phương án thì '
                   'mình có thể ký hợp đồng giữ giá để khóa mức giá hôm nay, sau này '
                   'vật tư tăng gia đình cũng không bị ảnh hưởng ạ.')
            + _key('Mục tiêu là giúp khách hiểu hệ quả của việc chậm quyết định, '
                   'KHÔNG gây áp lực vô lý, không dọa khách.')
        )

    # ------------------------------------------------------------------
    #  BƯỚC 5 — KHAI THÁC & XỬ LÝ VẤN ĐỀ SAU BÁO GIÁ (quan trọng nhất)
    # ------------------------------------------------------------------
    def _tdbg_khaithac(self):
        return (
            _step('5', 'Khai thác và xử lý vấn đề sau báo giá',
                  'Bước quan trọng nhất: khách chưa ký thì chắc chắn còn vấn đề.')
            + '<p>Nếu khách chưa ký, chắc chắn còn vấn đề &mdash; nhân viên phải tìm '
            'ra, không được tự suy đoán. Khai thác đủ theo <b>6 nhóm</b>:</p>'
            '<table>'
            '<tr><th style="width:26%;">Nhóm</th><th>Câu hỏi cần khai thác</th></tr>'
            '<tr><td><b>1. Báo giá</b></td><td>Có phù hợp không? Có vượt tài chính '
            'không? Có cần điều chỉnh không?</td></tr>'
            '<tr><td><b>2. Thiết kế</b></td><td>Có thích không? Cần thay đổi gì? Cần '
            'thêm công năng không?</td></tr>'
            '<tr><td><b>3. Mẫu nhà</b></td><td>Đã đúng phong cách chưa? Có muốn tham '
            'khảo thêm không?</td></tr>'
            '<tr><td><b>4. Gia đình</b></td><td>Đã thống nhất chưa? Ai là người quyết '
            'định? Cần trao đổi thêm với người thân không?</td></tr>'
            '<tr><td><b>5. Khởi công</b></td><td>Dự kiến khi nào? Đang chờ việc gì '
            'không? Có vướng thủ tục không?</td></tr>'
            '<tr><td><b>6. Niềm tin</b></td><td>Còn điều gì khiến anh/chị chưa yên tâm '
            'khi chọn bên em?</td></tr>'
            '</table>'
            + _key('Câu hỏi nhóm NIỀM TIN đắt giá nhất: giúp lộ ra rào cản thật sự '
                   'trước khi ký. Luôn kết thúc bằng câu hỏi này.')
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
            '<p>Sai lầm phổ biến: gửi hợp đồng xong rồi <b>mất hút</b>. Điều đúng: '
            '<b>sau 1&ndash;2 ngày chủ động hỏi lại</b>:</p>'
            '<ul>'
            '<li>Anh/chị đã <b>xem hợp đồng và phụ lục</b> chưa?</li>'
            '<li>Có <b>điều khoản nào chưa rõ</b> không?</li>'
            '<li>Có nội dung nào muốn <b>trao đổi hoặc điều chỉnh</b> không?</li>'
            '</ul>'
            '<p>Khách còn băn khoăn về hợp đồng thì phải giải quyết <b>dứt điểm</b> '
            'ngay, không bỏ qua.</p>'

            + '<h3>Bước 8 &mdash; Hẹn ký hợp đồng và khảo sát đất</h3>'
            '<p>Khi khách đã đồng ý <b>báo giá + thiết kế + hợp đồng</b>, bước cuối:</p>'
            '<ul>'
            '<li><b>Thống nhất lịch ký hợp đồng.</b></li>'
            '<li>Đề nghị <b>lên lịch khảo sát đất</b> thực tế.</li>'
            '<li>Trao đổi rõ quy trình ký kết và khoản <b>đặt cọc 50.000.000 đồng</b> '
            'theo quy định công ty (nếu áp dụng) để khách chủ động sắp xếp.</li>'
            '</ul>'
        )

    # ------------------------------------------------------------------
    #  NGUYÊN TẮC VÀNG + BẢNG TỰ KIỂM
    # ------------------------------------------------------------------
    def _tdbg_gold(self):
        return (
            '<h2>Nguyên tắc vàng</h2>'
            '<p style="font-size:18px;color:#111827;font-weight:700;">Nhân viên giỏi '
            'không phải người gửi được NHIỀU báo giá, mà là người biết DẪN DẮT khách '
            'đi qua từng bước tới quyết định ký.</p>'
            '<p>Sau mỗi lần liên hệ, nếu khách tiến thêm một bước (phản hồi báo giá '
            '&rarr; gỡ vấn đề &rarr; xem hợp đồng &rarr; hẹn khảo sát...) thì khả năng '
            'ký tăng lên rất nhiều. Không bao giờ để khách im lặng quá lâu.</p>'

            + '<h3>Bảng tự kiểm sau mỗi lần liên hệ khách</h3>'
            '<table>'
            '<tr><th style="width:8%;">#</th><th>Tự hỏi (Có / Chưa)</th></tr>'
            '<tr><td>1</td><td>Lần này khách đã <b>tiến thêm 1 bước</b> chưa?</td></tr>'
            '<tr><td>2</td><td>Mình đã <b>biết khách đang nghĩ gì</b> chưa, hay chỉ '
            'đang đoán?</td></tr>'
            '<tr><td>3</td><td>Còn <b>vấn đề nào chưa gỡ</b> (tài chính / thiết kế / '
            'gia đình / niềm tin)?</td></tr>'
            '<tr><td>4</td><td>Đã hẹn <b>mốc liên hệ tiếp theo</b> chưa?</td></tr>'
            '<tr><td>5</td><td>Lần này có <b>mục tiêu rõ ràng</b> đưa khách gần hơn '
            'tới ký không?</td></tr>'
            '</table>'
            '<p>Còn ô nào &#8220;Chưa&#8221; &mdash; đó chính là việc phải làm trong '
            'lần liên hệ kế tiếp.</p>'
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
