# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

BÁM SÁT TÀI LIỆU GỐC (Theo đuổi khách hàng sau báo giá.pdf) - trình bày TUẦN TỰ
theo đúng 8 bước của file (không tách theo tầng Bloom nữa vì làm rời mạch file).
Bổ sung GIAI ĐOẠN 0 - QUY TẮC TẠO NHÓM (user chốt 2026-07-12): sau khi gọi điện
xong phải bấm "chốt báo giá" + tạo nhóm Zalo, CẤM nhắn tin riêng cá nhân.

Trình bày: card + bảng + màu CÓ QUY TẮC cố định (GHI NHỚ=cam, VIỆC PHẢI LÀM=xanh
lá, SAI LẦM=đỏ, CÂU MẪU=xanh dương), FULL chiều ngang, KHÔNG cắt nội dung. Helper
dựng bằng nối chuỗi (+) -> tránh bẫy %. Prefix _tdbg_. Idempotent theo version.
Đảo đáp án mỗi lần thi do overview.js xử lý chung.
"""
from odoo import api, models

_TDBG_VERSION = 'v6-file'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
_STYLE = (
    '<style>'
    '.vd-tdbg{font-size:16.5px;line-height:1.72;color:#1f2937;}'
    '.vd-tdbg h2{font-size:22px;font-weight:800;color:#111827;margin:26px 0 10px;}'
    '.vd-tdbg h3{font-size:18px;font-weight:800;color:#111827;'
    'margin:20px 0 8px;padding-left:12px;border-left:4px solid #e8401f;}'
    '.vd-tdbg p{margin:0 0 12px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:0 0 12px;padding-left:24px;}'
    '.vd-tdbg li{margin:5px 0;}'
    '.vd-tdbg b{color:#111827;}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:10px 0 14px;font-size:15.5px;}'
    '.vd-tdbg th,.vd-tdbg td{border:1px solid #e5e7eb;padding:9px 12px;'
    'text-align:left;vertical-align:top;}'
    '.vd-tdbg th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-tdbg .ok{color:#15803d;font-weight:700;}'
    '.vd-tdbg .no{color:#b91c1c;font-weight:700;}'
    '</style>'
)


def _callout(bar, bg, label_color, label, text):
    return (
        '<div style="background:' + bg + ';border-left:5px solid ' + bar + ';'
        'border-radius:0 8px 8px 0;padding:12px 16px;margin:14px 0;">'
        '<div style="font-weight:800;color:' + label_color + ';font-size:13.5px;'
        'letter-spacing:.3px;margin-bottom:4px;">' + label + '</div>'
        '<div>' + text + '</div></div>')


def _key(text):
    return _callout('#e8401f', '#fff7ed', '#c2410c', '&#9873; GHI NHỚ', text)


def _todo(text):
    return _callout('#16a34a', '#f0fdf4', '#15803d', '&#9989; VIỆC PHẢI LÀM', text)


def _warn(text):
    return _callout('#dc2626', '#fef2f2', '#b91c1c', '&#9940; CẤM / SAI LẦM CẦN TRÁNH', text)


def _say(text):
    return _callout('#2563eb', '#eff6ff', '#1d4ed8', '&#128172; CÂU MẪU NÊN NÓI',
                    '<i>&#8220;' + text + '&#8221;</i>')


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _vs(sai, dung):
    return ('<table><tr><th style="width:50%;" class="no">&#10007; KHÔNG nên</th>'
            '<th class="ok">&#10003; NÊN làm</th></tr>'
            '<tr><td>' + sai + '</td><td>' + dung + '</td></tr></table>')


def _hero():
    return (
        '<div style="background:#e8401f;border-radius:16px;padding:30px 28px;'
        'margin-bottom:8px;">'
        '<div style="color:#ffe0d8;font-size:14px;font-weight:700;'
        'letter-spacing:2px;">KỸ NĂNG SALE &mdash; CHỐT HỢP ĐỒNG</div>'
        '<div style="color:#ffffff;font-size:29px;font-weight:900;margin-top:8px;'
        'line-height:1.2;">Quy trình theo đuổi khách hàng sau khi gửi báo giá</div>'
        '<div style="color:#fff2ee;font-size:16px;margin-top:12px;line-height:1.6;">'
        'Gửi báo giá KHÔNG phải là kết thúc &mdash; đó chỉ là ĐIỂM BẮT ĐẦU của quá '
        'trình chốt hợp đồng. Nhiệm vụ của nhân viên là từng bước dẫn khách đi tới '
        'lúc ký, không bao giờ để khách &#8220;treo&#8221;.</div></div>')


def _step(num, title, sub):
    return (
        '<div style="background:#1e293b;border-radius:12px;padding:20px 24px;'
        'margin:40px 0 16px;">'
        '<div style="color:#f59e0b;font-size:13px;font-weight:800;'
        'letter-spacing:2px;">' + num + '</div>'
        '<div style="color:#ffffff;font-size:23px;font-weight:800;margin-top:4px;'
        'line-height:1.25;">' + title + '</div>'
        '<div style="color:#cbd5e1;font-size:14.5px;margin-top:7px;">' + sub + '</div></div>')


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
    #  NỘI DUNG (bám sát file: Mục tiêu -> Giai đoạn 0 -> 8 bước -> Vàng)
    # ==================================================================
    def _vd_tdbg_pages(self):
        return [
            ('Hero', _hero()),
            ('MucTieu', self._tdbg_muctieu()),
            ('TaoNhom', self._tdbg_taonhom()),
            ('B1', self._tdbg_b1()),
            ('B2', self._tdbg_b2()),
            ('B3', self._tdbg_b3()),
            ('B4', self._tdbg_b4()),
            ('B5', self._tdbg_b5()),
            ('B6', self._tdbg_b6()),
            ('B7', self._tdbg_b7()),
            ('B8', self._tdbg_b8()),
            ('Gold', self._tdbg_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỤC TIÊU KHÓA HỌC + SƠ ĐỒ HÀNH TRÌNH (bám sát file)
    # ------------------------------------------------------------------
    def _tdbg_muctieu(self):
        return (
            '<h2>Mục tiêu khóa học</h2>'
            '<p>Đào tạo nhân viên hiểu rằng: <b>gửi báo giá không phải là kết thúc</b>. '
            'Thực tế, gửi báo giá chỉ là <b>điểm bắt đầu</b> của quá trình chốt hợp '
            'đồng. Rất nhiều nhân viên mất khách vì nghĩ: <i>&#8220;Em đã gửi báo giá '
            'rồi, giờ chờ khách gọi lại&#8221;</i> &mdash; đây là sai lầm nghiêm trọng.</p>'
            '<p>Khách hàng đang xây nhà thường: xem rất nhiều đơn vị &middot; chưa hiểu '
            'hết báo giá &middot; chưa biết nên hỏi gì &middot; đang cân nhắc tài chính '
            '&middot; đang so sánh. Nếu nhân viên không chủ động dẫn dắt, khách sẽ dần '
            'nghiêng về đơn vị khác.</p>'

            '<h2>Mục tiêu sau khi gửi báo giá</h2>'
            '<p>Sau khi gửi báo giá, mục tiêu <b>KHÔNG PHẢI</b> là chờ khách ký, mà là '
            'từng bước đưa khách đi qua các giai đoạn:</p>'
            + _table(['Giai đoạn khách đi qua'],
                     [['Báo giá'], ['&darr; Khách phản hồi'], ['&darr; Hiểu suy nghĩ khách'],
                      ['&darr; Giải quyết toàn bộ khúc mắc'], ['&darr; Gửi hợp đồng'],
                      ['&darr; Giải quyết hợp đồng'], ['&darr; Hẹn khảo sát'],
                      ['&darr; Ký hợp đồng']])
            + _key('Nếu khách im lặng thì quy trình đang bị DỪNG lại. Không được để '
                   'khách &#8220;treo&#8221;.'))

    # ------------------------------------------------------------------
    #  GIAI ĐOẠN 0 — QUY TẮC TẠO NHÓM (BỔ SUNG)
    # ------------------------------------------------------------------
    def _tdbg_taonhom(self):
        return (
            _step('GIAI ĐOẠN 0', 'QUY TẮC TẠO NHÓM (bắt buộc đầu tiên)',
                  'Ngay sau khi gọi điện cho khách xong &mdash; bấm "Chốt báo giá" và LẬP TỨC tạo nhóm.')
            + '<p>Ngay sau khi gọi điện tư vấn cho khách xong, việc đầu tiên bắt buộc '
            'là <b>bấm nút &#8220;Chốt báo giá&#8221;</b> trên hệ thống, sau đó '
            '<b>LẬP TỨC tạo nhóm Zalo</b> với khách. Đây là quy định bắt buộc, làm '
            'trước cả khi bước vào 8 bước theo đuổi.</p>'

            + '<h3>Vì sao CẤM nhắn tin riêng với khách?</h3>'
            + _warn('CẤM TUYỆT ĐỐI mọi nhân viên nhắn tin riêng (Zalo cá nhân) với '
                    'khách hàng. Zalo cá nhân CHỈ được dùng để GỌI ĐIỆN.')
            + '<p>Nhắn tin riêng với khách kéo theo rất nhiều hệ lụy về sau:</p>'
            + _table(['Rủi ro', 'Vì sao xảy ra'],
                     [['<b>Ký hợp đồng về sau rất khó</b>',
                       'Khách chỉ quan tâm và biết mỗi người tư vấn cá nhân (bạn), không quan tâm và không biết bất kỳ ai khác trong nhóm &mdash; nên khi đi ký hợp đồng sẽ rất khó.'],
                      ['<b>Khó chuyển giao cho phòng ban khác</b> (thiết kế, thi công)',
                       'Khách quen làm việc với cá nhân, chỉ biết người làm việc ban đầu; về sau làm việc nhóm/tập thể thì khách không muốn làm việc với bất kỳ ai khác.'],
                      ['<b>Kế toán thu tiền cũng khó</b>',
                       'Khách không biết phải làm việc với ai để thanh toán.']],
                     widths=['34%', '66%'])
            + _key('Quy định công ty: KHÔNG nhắn tin riêng cá nhân. Phải đưa khách '
                   'LÀM QUEN với việc làm việc trên NHÓM ngay từ tin nhắn đầu tiên. '
                   'Zalo cá nhân chỉ để gọi điện; còn nhắn tin thì cố gắng lái khách '
                   'lên nhóm &mdash; mọi thông tin phản hồi TRÊN NHÓM, không phản hồi '
                   'ở Zalo cá nhân.')

            + '<h3>Quy trình tạo nhóm bắt buộc</h3>'
            + '<p><b>1. Tạo nhóm ngay sau khi gọi điện xong.</b> Thành viên tối thiểu:</p>'
            '<ul>'
            '<li>Bản thân mình (nhân viên tư vấn)</li>'
            '<li>Khách hàng</li>'
            '<li>Trưởng phòng</li>'
            '</ul>'
            + '<p><b>2. Ngay sau khi tạo nhóm, bắt buộc làm 2 việc:</b></p>'
            + _table(['Việc', 'Yêu cầu'],
                     [['Đổi ảnh đại diện nhóm', 'Dùng LOGO của công ty'],
                      ['Đổi tên nhóm Zalo', 'Theo đúng quy tắc / quy định đặt tên']],
                     widths=['38%', '62%'])
            + '<p><b>3. Gửi nội dung lên nhóm theo ĐÚNG thứ tự sau:</b></p>'
            + _table(['Thứ tự', 'Nội dung phải gửi'],
                     [['<b>1</b> (gửi đầu tiên)', 'Gửi <b>4 video VTV</b>'],
                      ['<b>2</b>', 'Gửi lời chào &amp; giới thiệu bản thân'],
                      ['<b>3</b>', 'Gửi bản tổng hợp nhu cầu &amp; công năng của khách hàng'],
                      ['<b>4</b>', 'Gửi mẫu nhà cho khách xem thêm &mdash; <b>tối thiểu 20 mẫu nhà</b>']],
                     widths=['16%', '84%'])
            + _todo('Chỉ khi đã tạo nhóm đúng quy định (đủ 3 thành viên, đổi ảnh + tên) '
                    'và gửi đủ 4 nội dung trên (4 video VTV &rarr; giới thiệu &rarr; '
                    'tổng hợp nhu cầu &rarr; tối thiểu 20 mẫu nhà) thì mới bắt đầu nhắn '
                    'tin trao đổi bình thường &mdash; và luôn trao đổi TRÊN NHÓM.'))

    # ------------------------------------------------------------------
    #  BƯỚC 1 — KIỂM TRA CHẤT LƯỢNG BÁO GIÁ TRƯỚC KHI GỬI
    # ------------------------------------------------------------------
    def _tdbg_b1(self):
        return (
            _step('BƯỚC 1', 'Kiểm tra chất lượng báo giá TRƯỚC khi gửi',
                  'Nếu chính nhân viên còn không tự tin thì khách càng không tin.')
            + '<p>Đừng bao giờ gửi báo giá theo kiểu <i>&#8220;Em gửi anh/chị tham '
            'khảo nhé&#8221;</i>. Trước khi bấm gửi, phải tự trả lời được 3 câu hỏi.</p>'

            + '<h3>1. Báo giá có ĐÚNG NHU CẦU khách không?</h3>'
            + _table(['Khách nói / muốn', 'Nếu gửi lệch', 'Kết quả'],
                     [['Tài chính khoảng 2,8 tỷ', 'Lại gửi báo giá 3,8 tỷ', '<span class="no">SAI</span>'],
                      ['Khách thích hiện đại', 'Lại báo giá theo mẫu tân cổ', '<span class="no">SAI</span>'],
                      ['Khách muốn xây để ở', 'Lại làm theo tiêu chuẩn đầu tư', '<span class="no">SAI</span>']],
                     widths=['36%', '40%', '24%'])

            + '<h3>2. Báo giá có GIẢI QUYẾT vấn đề tài chính chưa?</h3>'
            '<p>Tự soát &mdash; nếu chưa trả lời được thì CHƯA nên gửi:</p>'
            '<ul>'
            '<li>Có vượt ngân sách không?</li>'
            '<li>Có phương án tối ưu không?</li>'
            '<li>Có phương án giảm chi phí không?</li>'
            '<li>Có giải thích rõ vì sao lại ra số tiền đó không?</li>'
            '</ul>'

            + '<h3>3. Báo giá có ĐÚNG MONG MUỐN của khách chưa?</h3>'
            '<p>Tất cả phải KHỚP: bao nhiêu tầng &middot; bao nhiêu phòng &middot; '
            'phong cách gì &middot; mức hoàn thiện nào &middot; có thang máy không '
            '&middot; có gara không &middot; có sân không.</p>'
            + _key('Nhân viên phải tự tin: &#8220;Nếu mình là khách, mình cũng thấy '
                   'báo giá này hợp lý&#8221;. Đó mới là báo giá đạt yêu cầu.'))

    # ------------------------------------------------------------------
    #  BƯỚC 2 — SAU 1-2 NGÀY BẮT BUỘC LẤY PHẢN HỒI
    # ------------------------------------------------------------------
    def _tdbg_b2(self):
        return (
            _step('BƯỚC 2', 'Sau 1&ndash;2 ngày bắt buộc phải lấy phản hồi',
                  'Gửi báo giá xong rồi im luôn = nguyên nhân mất rất nhiều khách.')
            + _warn('Sai lầm lớn nhất: gửi báo giá xong&hellip; im luôn &mdash; không '
                    'gọi, không nhắn, không hỏi.')
            + '<h3>Mục tiêu: không phải gọi để ép ký, mà để BIẾT khách đang nghĩ gì</h3>'
            '<p>Ví dụ phải khai thác được:</p>'
            '<ul>'
            '<li>Anh/chị đã xem báo giá chưa?</li>'
            '<li>Anh/chị thấy phần nào hợp lý?</li>'
            '<li>Phần nào còn băn khoăn?</li>'
            '<li>Mức đầu tư có phù hợp không?</li>'
            '<li>Có hạng mục nào anh/chị muốn điều chỉnh không?</li>'
            '</ul>'
            + '<h3>Khách im lặng KHÔNG có nghĩa là hết quan tâm</h3>'
            '<p>Đó là tín hiệu cần tìm hiểu. Có thể vì:</p>'
            + _table(['Lý do khách im lặng'],
                     [['Báo giá cao hơn dự kiến'], ['Báo giá chưa đúng nhu cầu'],
                      ['Chưa hiểu cách tính'], ['Đang chờ đơn vị khác'],
                      ['Chưa thấy đủ niềm tin'], ['Chưa biết nên hỏi gì']])
            + _key('Việc của nhân viên là KHAI THÁC, không phải ĐOÁN.'))

    # ------------------------------------------------------------------
    #  BƯỚC 3 — GỬI MẪU NHÀ CHO KHÁCH THAM KHẢO
    # ------------------------------------------------------------------
    def _tdbg_b3(self):
        return (
            _step('BƯỚC 3', 'Gửi mẫu nhà cho khách tham khảo',
                  'Việc bắt buộc &mdash; nhưng KHÔNG được ép khách chốt mẫu nhà.')
            + '<p>Mục tiêu: cho khách có thêm ý tưởng &middot; cho khách nhìn thấy '
            'nhiều lựa chọn &middot; giúp khách xác định sở thích.</p>'
            + _vs('&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;',
                  '&#8220;Em gửi thêm một số mẫu nhà có diện tích và mức đầu tư gần với '
                  'nhu cầu của anh/chị để mình tham khảo.&#8221;')
            + _say('Em gửi thêm một số mẫu nhà có diện tích và mức đầu tư gần với nhu '
                   'cầu của anh/chị để mình tham khảo. Nếu có chi tiết nào anh/chị '
                   'thích, bên em sẽ điều chỉnh thiết kế theo đúng mong muốn của gia đình.')
            + _key('Khách KHÔNG mua mẫu nhà. Khách mua giải pháp phù hợp với gia đình '
                   'mình. Vì vậy không được ép khách chốt mẫu nhà.'))

    # ------------------------------------------------------------------
    #  BƯỚC 4 — TẠO CẢM GIÁC CẦN QUYẾT ĐỊNH VỀ THỜI GIAN KHỞI CÔNG
    # ------------------------------------------------------------------
    def _tdbg_b4(self):
        return (
            _step('BƯỚC 4', 'Tạo cảm giác cần quyết định về thời gian khởi công',
                  'Rất quan trọng, đặc biệt cuối năm &mdash; khách nào cũng muốn xây xong trước Tết.')
            + '<p>Nếu khởi công muộn: thi công gấp &middot; dễ ảnh hưởng tiến độ '
            '&middot; khó bàn giao &middot; khó hoàn thiện. Nhân viên phải chủ động '
            'nhắc khách về yếu tố thời gian.</p>'
            + _say('Nếu gia đình mình dự kiến ở nhà mới trước Tết thì mình nên triển '
                   'khai sớm để đảm bảo tiến độ. Nếu để quá sát thời điểm cuối năm thì '
                   'việc hoàn thiện sẽ rất áp lực.')
            + _key('Mục tiêu KHÔNG phải gây áp lực vô lý, mà giúp khách hiểu rõ hệ quả '
                   'của việc chậm quyết định.'))

    # ------------------------------------------------------------------
    #  BƯỚC 5 — KHAI THÁC TOÀN BỘ KHÚC MẮC (quan trọng nhất)
    # ------------------------------------------------------------------
    def _tdbg_b5(self):
        return (
            _step('BƯỚC 5', 'Khai thác toàn bộ khúc mắc',
                  'Bước quan trọng nhất: khách chưa ký thì chắc chắn còn vấn đề.')
            + '<p>Nếu khách chưa ký, chắc chắn còn vấn đề &mdash; nhân viên phải TÌM '
            'RA, không được tự suy đoán. Những nhóm câu hỏi cần khai thác:</p>'
            + _table(['Nhóm', 'Câu hỏi cần khai thác'],
                     [['<b>1. Báo giá</b>', 'Có phù hợp không? Có vượt tài chính không? Có cần điều chỉnh không?'],
                      ['<b>2. Thiết kế</b>', 'Có thích không? Có cần thay đổi gì? Có cần thêm công năng?'],
                      ['<b>3. Mẫu nhà</b>', 'Đã đúng phong cách chưa? Có muốn tham khảo thêm không?'],
                      ['<b>4. Gia đình</b>', 'Đã thống nhất chưa? Ai là người quyết định? Có cần trao đổi thêm với người thân không?'],
                      ['<b>5. Khởi công</b>', 'Dự kiến khi nào? Có đang chờ việc gì không? Có vướng thủ tục không?'],
                      ['<b>6. Niềm tin</b>', 'Còn điều gì khiến anh/chị chưa yên tâm khi lựa chọn bên em?']],
                     widths=['18%', '82%'])
            + _key('Câu hỏi nhóm 6 &mdash; Niềm tin (&#8220;Còn điều gì khiến anh/chị '
                   'chưa yên tâm khi lựa chọn bên em?&#8221;) rất quan trọng vì giúp '
                   'phát hiện RÀO CẢN THẬT SỰ trước khi bước sang giai đoạn ký kết.'))

    # ------------------------------------------------------------------
    #  BƯỚC 6 — KHI KHÔNG CÒN KHÚC MẮC THÌ GỬI HỢP ĐỒNG
    # ------------------------------------------------------------------
    def _tdbg_b6(self):
        return (
            _step('BƯỚC 6', 'Khi không còn khúc mắc thì gửi hợp đồng',
                  'Đủ điều kiện thì phải chuyển bước, không nói chuyện chung chung nữa.')
            + '<p>Khi khách đã: <b>đồng ý báo giá + đồng ý phương án + không còn vướng '
            'mắc lớn</b> thì không tiếp tục nói chuyện chung chung, phải chuyển sang '
            'bước tiếp theo: <b>gửi hợp đồng để khách nghiên cứu</b>.</p>'
            + _say('Để gia đình mình có thời gian xem kỹ các điều khoản, bên em sẽ gửi '
                   'trước hợp đồng để anh/chị đọc. Nếu có nội dung nào cần giải thích '
                   'hoặc điều chỉnh, em sẽ trao đổi ngay để mình yên tâm trước khi ký.'))

    # ------------------------------------------------------------------
    #  BƯỚC 7 — THEO DÕI HỢP ĐỒNG
    # ------------------------------------------------------------------
    def _tdbg_b7(self):
        return (
            _step('BƯỚC 7', 'Theo dõi hợp đồng',
                  'Gửi hợp đồng xong rồi mất hút là sai lầm của rất nhiều nhân viên.')
            + _warn('Sai lầm của nhiều nhân viên: gửi hợp đồng &mdash; xong &mdash; mất hút.')
            + '<p>Điều đúng phải làm: <b>sau 1&ndash;2 ngày phải hỏi</b>:</p>'
            '<ul>'
            '<li>Anh/chị đã xem hợp đồng chưa?</li>'
            '<li>Có điều khoản nào chưa rõ không?</li>'
            '<li>Có nội dung nào mình muốn trao đổi thêm không?</li>'
            '</ul>'
            + _key('Nếu khách còn băn khoăn thì KHÔNG được bỏ qua &mdash; phải giải '
                   'quyết ngay.'))

    # ------------------------------------------------------------------
    #  BƯỚC 8 — HẸN KHẢO SÁT VÀ KÝ HỢP ĐỒNG
    # ------------------------------------------------------------------
    def _tdbg_b8(self):
        return (
            _step('BƯỚC 8', 'Hẹn khảo sát và ký hợp đồng',
                  'Khi khách đã đồng ý báo giá + thiết kế + hợp đồng.')
            + '<p>Bước tiếp theo là:</p>'
            '<ul>'
            '<li>Đề nghị lên lịch khảo sát thực tế.</li>'
            '<li>Đồng thời thống nhất lịch ký hợp đồng.</li>'
            '</ul>'
            '<p>Trao đổi rõ các nội dung cần chuẩn bị, bao gồm quy trình ký kết và '
            'khoản <b>đặt cọc 50.000.000 đồng</b> theo quy định của công ty (nếu áp '
            'dụng), để khách chủ động sắp xếp.</p>')

    # ------------------------------------------------------------------
    #  NGUYÊN TẮC VÀNG
    # ------------------------------------------------------------------
    def _tdbg_gold(self):
        return (
            '<h2>&#127942; Nguyên tắc vàng</h2>'
            '<p style="font-size:18px;color:#111827;font-weight:700;">Một nhân viên '
            'kinh doanh giỏi không phải là người gửi được nhiều báo giá, mà là người '
            'biết dẫn dắt khách hàng đi qua từng bước của hành trình ra quyết định.</p>'
            '<p>Nếu sau mỗi lần liên hệ, khách hàng tiến thêm một bước (phản hồi báo '
            'giá, giải quyết khúc mắc, xem hợp đồng, hẹn khảo sát...) thì khả năng ký '
            'hợp đồng sẽ tăng lên rất nhiều.</p>'
            + _key('Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi lần '
                   'tương tác đều phải có mục tiêu rõ ràng và đưa khách tiến gần hơn '
                   'tới quyết định ký hợp đồng.'))

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM - bám sát file + quy tắc tạo nhóm.
    #  Đáp án nhiễu đều hợp lý để NV phải phân vân. (đáp án, đúng?)
    # ==================================================================
    def _vd_tdbg_questions(self):
        T, F = True, False
        return [
            # ---- QUY TẮC TẠO NHÓM (Giai đoạn 0) ----
            ('Ngay sau khi gọi điện tư vấn cho khách xong, việc BẮT BUỘC phải làm là gì?',
             [('Bấm nút "Chốt báo giá" rồi lập tức tạo nhóm Zalo với khách', T),
              ('Nhắn tin Zalo cá nhân hỏi thăm khách', F),
              ('Chờ khách chủ động nhắn lại rồi mới xử lý', F),
              ('Gửi ngay báo giá qua Zalo cá nhân cho nhanh', F)]),

            ('Vì sao công ty CẤM nhân viên nhắn tin riêng (Zalo cá nhân) với khách?',
             [('Vì khách chỉ biết/quen làm việc với cá nhân nên sau này ký hợp đồng, chuyển giao thiết kế - thi công và kế toán thu tiền đều rất khó', T),
              ('Vì nhắn tin riêng tốn thời gian của nhân viên', F),
              ('Vì công ty muốn kiểm soát nội dung tin nhắn cá nhân', F),
              ('Vì Zalo cá nhân hay bị khóa', F)]),

            ('Với khách hàng, Zalo CÁ NHÂN của nhân viên CHỈ được dùng để làm gì?',
             [('Chỉ để gọi điện; còn nhắn tin thì phải lái khách lên nhóm, phản hồi mọi thông tin trên nhóm', T),
              ('Để nhắn tin trao đổi mọi thông tin cho tiện', F),
              ('Để gửi báo giá và hợp đồng riêng cho khách', F),
              ('Để chốt hợp đồng riêng với khách', F)]),

            ('Khi tạo nhóm Zalo với khách, thành viên TỐI THIỂU phải gồm những ai?',
             [('Bản thân nhân viên + khách hàng + trưởng phòng', T),
              ('Chỉ cần nhân viên và khách hàng', F),
              ('Nhân viên, khách hàng và kế toán', F),
              ('Nhân viên, khách hàng và giám đốc', F)]),

            ('Ngay sau khi tạo nhóm, 2 việc BẮT BUỘC phải làm là gì?',
             [('Đổi ảnh đại diện nhóm bằng logo công ty và đổi tên nhóm theo quy tắc quy định', T),
              ('Thêm khách vào nhóm và gửi ngay báo giá', F),
              ('Đổi ảnh đại diện và mời thêm bạn bè khách', F),
              ('Đặt tên nhóm theo tên khách và gắn ghim tin nhắn', F)]),

            ('Nội dung PHẢI gửi ĐẦU TIÊN lên nhóm là gì?',
             [('4 video VTV', T),
              ('Lời chào giới thiệu bản thân', F),
              ('Bảng tổng hợp nhu cầu công năng của khách', F),
              ('Các mẫu nhà tham khảo', F)]),

            ('Khi tạo nhóm, phải gửi TỐI THIỂU bao nhiêu mẫu nhà lên nhóm cho khách tham khảo?',
             [('Tối thiểu 20 mẫu nhà', T),
              ('Tối thiểu 5 mẫu nhà', F),
              ('Đúng 1 mẫu nhà khách chọn', F),
              ('Không cần gửi mẫu nhà lên nhóm', F)]),

            # ---- 8 BƯỚC (bám sát file) ----
            ('Theo khóa học, gửi báo giá cho khách nên được hiểu là gì?',
             [('Điểm BẮT ĐẦU của quá trình chốt hợp đồng', T),
              ('Bước cuối cùng, sau đó chỉ việc chờ khách gọi lại', F),
              ('Dấu hiệu khách đã gần như đồng ý ký', F),
              ('Thời điểm nên ngừng liên hệ để khách tự cân nhắc', F)]),

            ('Bước 1 - trước khi bấm gửi báo giá, nhân viên phải tự trả lời mấy câu hỏi?',
             [('3 câu: đúng nhu cầu, giải quyết tài chính, đúng mong muốn của khách', T),
              ('1 câu: giá có rẻ hơn đối thủ không', F),
              ('2 câu: khách có tiền không và có gấp không', F),
              ('Không cần tự hỏi, cứ gửi kèm "anh/chị tham khảo nhé"', F)]),

            ('Khách nói tài chính khoảng 2,8 tỷ nhưng nhân viên lại gửi báo giá 3,8 tỷ. Đây là?',
             [('SAI - báo giá không đúng nhu cầu tài chính của khách', T),
              ('Đúng, vì nên chào cao để còn thương lượng giảm', F),
              ('Đúng, vì khách sẽ thấy chất lượng cao hơn', F),
              ('Không quan trọng, miễn là gửi nhanh', F)]),

            ('Một báo giá được coi là ĐẠT YÊU CẦU khi nào?',
             [('Khi "nếu mình là khách, mình cũng thấy báo giá này hợp lý"', T),
              ('Khi có tổng giá trị cao nhất có thể', F),
              ('Khi gửi trước đối thủ', F),
              ('Khi trình bày nhiều màu sắc, đẹp mắt', F)]),

            ('Sau khi gửi báo giá bao lâu thì BẮT BUỘC phải lấy phản hồi từ khách?',
             [('Sau 1-2 ngày', T),
              ('Sau 1-2 tuần', F),
              ('Chỉ khi khách chủ động nhắn lại', F),
              ('Sau đúng 1 tháng', F)]),

            ('Mục tiêu THỰC SỰ của cuộc gọi lấy phản hồi (bước 2) là gì?',
             [('Để biết khách đang nghĩ gì, khai thác suy nghĩ thật của khách', T),
              ('Để ép khách ký hợp đồng ngay trong cuộc gọi', F),
              ('Để thông báo báo giá sắp hết hạn', F),
              ('Để hỏi khách đã chuyển tiền cọc chưa', F)]),

            ('Khi khách IM LẶNG sau khi nhận báo giá, cách hiểu ĐÚNG là gì?',
             [('Là tín hiệu cần tìm hiểu, khách im không có nghĩa là hết quan tâm', T),
              ('Khách đã hết quan tâm, nên chuyển sang khách khác', F),
              ('Khách đang hài lòng nên không cần hỏi thêm', F),
              ('Nên chờ thêm ít nhất 1 tuần rồi mới liên hệ lại', F)]),

            ('Đâu là câu KHÔNG nên nói khi gửi mẫu nhà cho khách tham khảo (bước 3)?',
             [('"Anh chị chọn giúp em một mẫu nhé"', T),
              ('"Em gửi vài mẫu gần nhu cầu để mình tham khảo"', F),
              ('"Thích chi tiết nào bên em điều chỉnh thiết kế theo"', F),
              ('"Mấy mẫu này để anh chị có thêm ý tưởng ạ"', F)]),

            ('Vì sao KHÔNG được ép khách chốt mẫu nhà?',
             [('Vì khách không mua mẫu nhà, khách mua giải pháp phù hợp với gia đình mình', T),
              ('Vì mẫu nhà nào cũng giống nhau nên không cần chọn', F),
              ('Vì công ty không cho phép thay đổi mẫu', F),
              ('Vì chọn mẫu là việc của bộ phận thiết kế', F)]),

            ('Khi nhắc khách về thời gian khởi công (bước 4), mục tiêu ĐÚNG là gì?',
             [('Giúp khách hiểu rõ hệ quả của việc chậm quyết định, KHÔNG gây áp lực vô lý', T),
              ('Dọa khách rằng giá sẽ tăng gấp đôi nếu không ký ngay', F),
              ('Nói công ty sắp hết suất nhận công trình', F),
              ('Ép khách phải khởi công trong tuần này', F)]),

            ('Trong 6 nhóm câu hỏi khai thác (bước 5), nhóm nào giúp phát hiện RÀO CẢN THẬT SỰ trước khi ký?',
             [('Nhóm Niềm tin: "Còn điều gì khiến anh/chị chưa yên tâm khi lựa chọn bên em?"', T),
              ('Nhóm Báo giá: "Có vượt tài chính không?"', F),
              ('Nhóm Mẫu nhà: "Đã đúng phong cách chưa?"', F),
              ('Nhóm Khởi công: "Dự kiến khi nào?"', F)]),

            ('Sai lầm phổ biến ở bước THEO DÕI HỢP ĐỒNG (bước 7) là gì?',
             [('Gửi hợp đồng xong rồi mất hút, không hỏi lại sau 1-2 ngày', T),
              ('Hỏi lại khách sau 1-2 ngày về điều khoản', F),
              ('Giải quyết ngay khi khách còn băn khoăn', F),
              ('Gửi kèm lời mời khách trao đổi thêm', F)]),

            ('Theo NGUYÊN TẮC VÀNG, một nhân viên kinh doanh GIỎI được định nghĩa thế nào?',
             [('Người biết dẫn dắt khách đi qua từng bước tới quyết định ký, không phải người gửi được nhiều báo giá', T),
              ('Người gửi được nhiều báo giá nhất trong tháng', F),
              ('Người có giá chào thấp nhất cho khách', F),
              ('Người gọi cho khách nhiều lần nhất trong ngày', F)]),
        ]
