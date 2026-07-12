# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

GIAO DIỆN KIỂU STREAMLIT / MICRO-LEARNING (user chốt 2026-07-12): thay accordion
<details> (khó nhận ra chỗ bấm) bằng:
- MENU BÊN TRÁI (sidebar) chọn từng bài - mỗi nút là 1 bài, bấm hiện 1 bài (tránh
  quá tải). Nút menu rõ ràng, nút đang chọn tô cam.
- Trong mỗi bài: hộp màu (đỏ=sai lầm, vàng=lưu ý, xanh dương=mẹo, xanh lá=đúng)
  + bảng + QUIZ chọn đáp án A/B/C/D, phản hồi ĐÚNG/SAI TỨC THÌ (xanh/đỏ) và tự
  chỉ ra đáp án đúng khi chọn sai.
Tất cả bằng HTML/CSS THUẦN qua input[type=radio]:checked (KHÔNG cần JS - JS chèn
qua innerHTML không chạy). vd_body sanitize=False + render markup() nên HTML thô
giữ nguyên. Trang đọc bài KHÔNG re-render định kỳ (chỉ exam mới có timer) nên
trạng thái :checked được giữ.

BÁM SÁT tài liệu gốc + GIAI ĐOẠN 0 tạo nhóm. Helper nối chuỗi (+) -> tránh bẫy %.
Prefix _tdbg_. Idempotent theo version. Đảo đáp án bài THI do overview.js xử lý.
"""
from odoo import api, models

_TDBG_VERSION = 'v8-streamlit'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-tdbg{font-size:16px;line-height:1.7;color:#1f2937;}'
    '.vd-tdbg .vd-course{background:linear-gradient(180deg,#fff7f3 0%,#f5faff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-tdbg h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-tdbg h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-tdbg p{margin:0 0 10px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-tdbg li{margin:5px 0;}'
    '.vd-tdbg b{color:#111827;}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:10px 0;font-size:15px;}'
    '.vd-tdbg th,.vd-tdbg td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-tdbg th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-tdbg .no{color:#b91c1c;font-weight:700;}'
    # radio ẩn nhưng vẫn bật/tắt được qua <label for>
    '.vd-tdbg .navr,.vd-tdbg .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    # bố cục 2 cột
    '.vd-tdbg .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-tdbg .vc-side{flex:0 0 260px;}'
    '.vd-tdbg .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-tdbg .vc-navbtn{display:block;padding:12px 14px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14.5px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-tdbg .vc-navbtn:hover{background:#fff5f1;border-color:#ffd9c9;color:#e8401f;}'
    '.vd-tdbg .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-tdbg .vc-panel{display:none;}'
    '.vd-tdbg .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#e8401f;background:#fff1ec;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    # hộp màu
    '.vd-tdbg .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:12px 0;}'
    '.vd-tdbg .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-tdbg .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-tdbg .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-tdbg .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # quiz
    '.vd-tdbg .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:16px 0 4px;}'
    '.vd-tdbg .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-tdbg .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-tdbg .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-tdbg .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-tdbg .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-tdbg .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-tdbg .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-tdbg .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-tdbg .vc-layout{flex-direction:column;}'
    '.vd-tdbg .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-tdbg .vc-sidehead{width:100%;}'
    '.vd-tdbg .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
    '</style>'
)


# ---------------------------------------------------------------------------
#  HELPER (nối chuỗi -> không lo bẫy %)
# ---------------------------------------------------------------------------
def _box(kind, text):
    cls = {'err': 'b-err', 'warn': 'b-warn', 'info': 'b-info', 'ok': 'b-ok'}[kind]
    icon = {'err': '&#128680;', 'warn': '&#9888;&#65039;', 'info': '&#128161;', 'ok': '&#9989;'}[kind]
    return '<div class="box ' + cls + '">' + icon + ' ' + text + '</div>'


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _quiz(qid, question, options, explain):
    """Quiz tương tác thuần CSS. options = list (text, is_correct). Phản hồi tức thì."""
    letters = ['A', 'B', 'C', 'D', 'E']
    inputs = ''
    labels = ''
    correct = 0
    wrong = []
    for i, (text, ok) in enumerate(options):
        oid = qid + '_' + str(i)
        inputs += '<input class="qopt" type="radio" name="' + qid + '" id="' + oid + '">'
        labels += ('<label for="' + oid + '"><span class="qk">' + letters[i]
                   + '</span>' + text + '</label>')
        if ok:
            correct = i
        else:
            wrong.append(i)
    cid = qid + '_' + str(correct)
    # CSS động: hiện phản hồi + tô màu ô đã chọn + luôn tô xanh đáp án đúng khi chọn sai
    css = '#' + cid + ':checked ~ .fb-right{display:block}'
    if wrong:
        css += ','.join('#' + qid + '_' + str(w) + ':checked ~ .fb-wrong' for w in wrong) + '{display:block}'
    css += ('#' + cid + ':checked ~ .opts label[for=' + cid + ']'
            '{background:#dcfce7;border-color:#16a34a;color:#15803d}')
    for w in wrong:
        wid = qid + '_' + str(w)
        css += ('#' + wid + ':checked ~ .opts label[for=' + wid + ']'
                '{background:#fee2e2;border-color:#dc2626;color:#b91c1c}')
        css += ('#' + wid + ':checked ~ .opts label[for=' + cid + ']'
                '{background:#dcfce7;border-color:#16a34a;color:#15803d}')
    return ('<div class="quiz"><div class="qq">&#128221; Trắc nghiệm nhanh</div>'
            '<div class="qhint">' + question + ' &mdash; bấm chọn một đáp án:</div>'
            + inputs
            + '<div class="opts">' + labels + '</div>'
            '<div class="fb fb-right">&#127881; Chính xác! ' + explain + '</div>'
            '<div class="fb fb-wrong">&#9888;&#65039; Chưa đúng &mdash; ô tô XANH là '
            'đáp án đúng. ' + explain + '</div>'
            '<style>' + css + '</style></div>')


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

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-tdbg" style="%s">%s</div>'
                                 % (_WRAP, self._vd_tdbg_app())),
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
    #  APP: menu trái (chọn bài) + panel phải (nội dung 1 bài)
    # ==================================================================
    def _vd_tdbg_app(self):
        lessons = self._vd_tdbg_lessons()
        radios = ''
        navbtns = ''
        panels = ''
        rules = ''
        for i, (icon, menu, body) in enumerate(lessons):
            rid = 'vdL' + str(i)
            pid = 'vdP' + str(i)
            radios += ('<input class="navr" type="radio" name="vdnav" id="' + rid + '"'
                       + (' checked' if i == 0 else '') + '>')
            navbtns += '<label class="vc-navbtn" for="' + rid + '">' + icon + ' ' + menu + '</label>'
            panels += '<section class="vc-panel" id="' + pid + '">' + body + '</section>'
            rules += '#' + rid + ':checked ~ .vc-layout #' + pid + '{display:block}'
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + ']'
                      '{background:#e8401f;color:#fff;border-color:#e8401f}')
        hero = (
            '<div style="background:linear-gradient(120deg,#ff7a45 0%,#ff9e5e 55%,#ffb877 100%);'
            'border-radius:16px;padding:24px 26px;margin-bottom:14px;'
            'box-shadow:0 10px 30px rgba(255,122,69,.28);">'
            '<div style="color:#fff4ee;font-size:13px;font-weight:800;letter-spacing:2px;">'
            'KỸ NĂNG SALE &mdash; CHỐT HỢP ĐỒNG</div>'
            '<div style="color:#fff;font-size:27px;font-weight:900;margin-top:6px;line-height:1.2;'
            'text-shadow:0 2px 8px rgba(0,0,0,.15);">'
            'Quy trình theo đuổi khách hàng sau khi gửi báo giá</div>'
            '<div style="color:#fff8f4;font-size:14.5px;margin-top:9px;">'
            '&#128073; Bấm từng mục ở MENU BÊN TRÁI để học lần lượt. Mỗi bài có phần '
            'trắc nghiệm &mdash; chọn đáp án để biết đúng/sai ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    # ------------------------------------------------------------------
    #  DANH SÁCH BÀI HỌC: (icon, tên menu, nội dung panel)
    # ------------------------------------------------------------------
    def _vd_tdbg_lessons(self):
        return [
            ('&#129504;', 'Tư duy &amp; Sai lầm cần tránh', self._l_tuduy()),
            ('&#128101;', 'Quy tắc tạo nhóm', self._l_taonhom()),
            ('&#9989;', 'Bước 1: Kiểm tra báo giá', self._l_b1()),
            ('&#128222;', 'Bước 2: Lấy phản hồi', self._l_b2()),
            ('&#127968;', 'Bước 3: Gửi mẫu nhà', self._l_b3()),
            ('&#9200;', 'Bước 4: Thời gian khởi công', self._l_b4()),
            ('&#128269;', 'Bước 5: Khai thác khúc mắc', self._l_b5()),
            ('&#128196;', 'Bước 6: Gửi hợp đồng', self._l_b6()),
            ('&#128064;', 'Bước 7: Theo dõi hợp đồng', self._l_b7()),
            ('&#9997;&#65039;', 'Bước 8: Hẹn khảo sát &amp; ký', self._l_b8()),
            ('&#127942;', 'Nguyên tắc vàng', self._l_gold()),
        ]

    def _l_tuduy(self):
        return (
            self._tag('TƯ DUY NỀN TẢNG')
            + '<h3>Gửi báo giá là BẮT ĐẦU, không phải kết thúc</h3>'
            + _box('err', '<b>Sai lầm chí mạng:</b> Gửi báo giá xong rồi&hellip; im '
                   'lặng chờ khách gọi lại. Đây là nguyên nhân mất rất nhiều khách.')
            + '<p>Khách đang xây nhà thường cùng lúc: xem rất nhiều đơn vị &middot; '
            'chưa hiểu hết báo giá &middot; chưa biết nên hỏi gì &middot; đang cân '
            'nhắc tài chính &middot; đang so sánh. Không chủ động dẫn dắt thì khách '
            'nghiêng dần sang đơn vị khác.</p>'
            + '<h4>Tư duy đúng</h4>'
            + _box('info', '<b>Khách rất bận:</b> họ cần bạn chủ động nhắc và đồng hành.')
            + _box('info', '<b>Bán giải pháp, không bán giá:</b> tập trung vào giá trị '
                   'phù hợp gia đình khách, không chỉ so số tiền.')
            + '<p>Mục tiêu sau báo giá là từng bước đưa khách đi qua: <b>Báo giá &rarr; '
            'Phản hồi &rarr; Hiểu suy nghĩ &rarr; Giải quyết khúc mắc &rarr; Gửi hợp '
            'đồng &rarr; Giải quyết hợp đồng &rarr; Hẹn khảo sát &rarr; Ký</b>.</p>'
            + _box('warn', 'Nếu khách im lặng thì quy trình đang bị DỪNG lại. Không '
                   'được để khách &#8220;treo&#8221;.')
            + _quiz('qz_tuduy',
                    'Sau khi gửi báo giá 24h mà khách chưa phản hồi, hành động nào chuyên nghiệp nhất?',
                    [('Gọi điện giục khách ký hợp đồng ngay', False),
                     ('Nhắn/gọi hỏi thăm khách đã nhận báo giá chưa và có cần giải thích thêm không', True),
                     ('Tiếp tục im lặng chờ thêm 1 tuần', False)],
                    'Chủ động quan tâm để hiểu khách nghĩ gì &mdash; không ép, không bỏ mặc.'))

    def _l_taonhom(self):
        return (
            self._tag('GIAI ĐOẠN 0 &mdash; BẮT BUỘC ĐẦU TIÊN')
            + '<h3>Quy tắc tạo nhóm</h3>'
            + _box('warn', 'Ngay sau khi gọi điện xong: bấm nút <b>&#8220;Chốt báo '
                   'giá&#8221;</b> rồi <b>LẬP TỨC tạo nhóm Zalo</b> &mdash; chưa nhắn '
                   'tin trao đổi vội.')
            + _box('err', '<b>CẤM nhắn tin riêng (Zalo cá nhân) với khách.</b> Zalo cá '
                   'nhân chỉ dùng để GỌI ĐIỆN; còn nhắn tin thì lái khách lên nhóm.')
            + '<h4>Vì sao cấm nhắn tin riêng?</h4>'
            + _table(['Rủi ro', 'Vì sao xảy ra'],
                     [['<b>Ký hợp đồng về sau rất khó</b>',
                       'Khách chỉ biết/quan tâm mỗi người tư vấn cá nhân (bạn), không quan tâm ai khác trong nhóm.'],
                      ['<b>Khó chuyển giao thiết kế - thi công</b>',
                       'Khách quen làm việc cá nhân, chỉ biết người ban đầu; về sau không muốn làm việc với người khác/tập thể.'],
                      ['<b>Kế toán thu tiền khó</b>',
                       'Khách không biết phải làm việc với ai để thanh toán.']],
                     widths=['32%', '68%'])
            + '<h4>Quy trình tạo nhóm bắt buộc</h4>'
            + '<ol>'
            '<li>Tạo nhóm gồm tối thiểu: <b>bản thân + khách hàng + trưởng phòng</b>.</li>'
            '<li>Ngay sau khi tạo: <b>đổi ảnh đại diện = logo công ty</b> + <b>đổi tên '
            'nhóm theo quy tắc quy định</b>.</li>'
            '<li>Gửi lên nhóm theo thứ tự: <b>(1) 4 video VTV</b> (đầu tiên) &rarr; '
            '<b>(2) lời chào giới thiệu bản thân</b> &rarr; <b>(3) tổng hợp nhu cầu '
            'công năng khách</b> &rarr; <b>(4) tối thiểu 20 mẫu nhà</b>.</li>'
            '<li>Đủ các bước trên mới nhắn tin trao đổi bình thường &mdash; luôn trên nhóm.</li>'
            '</ol>'
            + _box('ok', 'Đưa khách làm quen với việc làm việc trên NHÓM ngay từ tin '
                   'nhắn đầu tiên.')
            + _quiz('qz_nhom',
                    'Khách nhắn Zalo cá nhân hỏi thêm về giá ngay sau khi bạn gọi tư vấn xong. Nên làm gì?',
                    [('Trả lời chi tiết ngay trên Zalo cá nhân cho nhanh', False),
                     ('Tạo nhóm (mình + khách + trưởng phòng), đổi ảnh/tên, gửi 4 video VTV + giới thiệu + nhu cầu + 20 mẫu nhà, rồi trao đổi trên nhóm', True),
                     ('Bảo khách cứ gọi điện, không nhắn tin gì', False),
                     ('Chờ trưởng phòng nhắn cho khách trước', False)],
                    'Chốt báo giá + tạo nhóm ngay; không phản hồi ở Zalo cá nhân.'))

    def _l_b1(self):
        return (
            self._tag('BƯỚC 1')
            + '<h3>Kiểm tra chất lượng báo giá trước khi gửi</h3>'
            + _box('warn', 'Đừng gửi kiểu &#8220;Em gửi anh/chị tham khảo nhé&#8221;. '
                   'Nếu chính nhân viên còn không tự tin thì khách càng không tin.')
            + '<h4>Tự trả lời 3 câu trước khi bấm gửi</h4>'
            '<ol>'
            '<li><b>Đúng nhu cầu khách không?</b> (tài chính, phong cách, mục đích xây)</li>'
            '<li><b>Giải quyết vấn đề tài chính chưa?</b> (vượt ngân sách? phương án '
            'tối ưu? giảm chi phí? giải thích rõ vì sao ra số tiền?)</li>'
            '<li><b>Đúng mong muốn chưa?</b> (số tầng, phòng, phong cách, mức hoàn '
            'thiện, thang máy, gara, sân &mdash; tất cả phải khớp)</li>'
            '</ol>'
            + _table(['Khách nói / muốn', 'Nếu gửi lệch', 'Kết quả'],
                     [['Tài chính khoảng 2,8 tỷ', 'Gửi báo giá 3,8 tỷ', '<span class="no">SAI</span>'],
                      ['Khách thích hiện đại', 'Báo giá theo mẫu tân cổ', '<span class="no">SAI</span>'],
                      ['Khách muốn xây để ở', 'Làm theo tiêu chuẩn đầu tư', '<span class="no">SAI</span>']],
                     widths=['36%', '40%', '24%'])
            + _box('ok', '&#8220;Nếu mình là khách, mình cũng thấy báo giá này hợp '
                   'lý&#8221; &mdash; đó mới là báo giá đạt yêu cầu.')
            + _quiz('qz_b1',
                    'Khách nói tài chính ~2,8 tỷ, báo giá bạn tính ra 3,8 tỷ. Nên làm gì?',
                    [('Cứ gửi 3,8 tỷ, báo cao để còn thương lượng giảm', False),
                     ('Gửi 3,8 tỷ kèm câu &#8220;anh/chị tham khảo nhé&#8221;', False),
                     ('Cân đối lại phương án diện tích/công năng cho khớp tầm 2,8 tỷ rồi mới gửi', True),
                     ('Gửi luôn để khách thấy đẳng cấp', False)],
                    'Báo giá lệch tầm tài chính là vô tác dụng &mdash; phải cân đối cho khớp ngân sách.'))

    def _l_b2(self):
        return (
            self._tag('BƯỚC 2')
            + '<h3>Sau 1&ndash;2 ngày bắt buộc lấy phản hồi</h3>'
            + _box('err', 'Sai lầm lớn nhất: gửi báo giá xong rồi <b>im luôn</b> &mdash; '
                   'không gọi, không nhắn, không hỏi.')
            + '<p><b>Mục tiêu:</b> không phải gọi để ép ký, mà để BIẾT khách đang nghĩ '
            'gì. Ví dụ khai thác: đã xem báo giá chưa? thấy phần nào hợp lý? phần nào '
            'băn khoăn? mức đầu tư phù hợp? có hạng mục nào muốn điều chỉnh?</p>'
            + '<h4>Khách im lặng KHÔNG có nghĩa là hết quan tâm</h4>'
            + _table(['Có thể khách im vì'],
                     [['Báo giá cao hơn dự kiến'], ['Báo giá chưa đúng nhu cầu'],
                      ['Chưa hiểu cách tính'], ['Đang chờ đơn vị khác'],
                      ['Chưa thấy đủ niềm tin'], ['Chưa biết nên hỏi gì']])
            + _box('info', 'Việc của nhân viên là KHAI THÁC, không phải ĐOÁN.')
            + _quiz('qz_b2',
                    'Gửi báo giá đã 2 ngày, khách không phản hồi. Nên làm gì?',
                    [('Coi như khách hết quan tâm, chuyển sang khách khác', False),
                     ('Chờ thêm 1 tuần cho khách tự nhắn lại', False),
                     ('Chủ động gọi/nhắn khai thác: đã xem chưa, băn khoăn gì, mức đầu tư có phù hợp không', True),
                     ('Nhắn &#8220;anh/chị ký chưa ạ?&#8221; để chốt nhanh', False)],
                    'Im lặng là tín hiệu cần tìm hiểu; mục tiêu là hiểu khách, không ép ký.'))

    def _l_b3(self):
        return (
            self._tag('BƯỚC 3')
            + '<h3>Gửi mẫu nhà cho khách tham khảo</h3>'
            + _box('info', 'Việc bắt buộc &mdash; nhưng KHÔNG được ép khách chốt mẫu. '
                   'Mục tiêu: thêm ý tưởng, nhiều lựa chọn, xác định sở thích.')
            + _table(['&#10007; KHÔNG nói', '&#10003; NÊN nói'],
                     [['&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;',
                       '&#8220;Em gửi thêm một số mẫu có diện tích và mức đầu tư gần nhu cầu của anh/chị để tham khảo. Chi tiết nào thích, bên em điều chỉnh thiết kế theo.&#8221;']],
                     widths=['40%', '60%'])
            + _box('ok', 'Khách KHÔNG mua mẫu nhà &mdash; khách mua giải pháp phù hợp '
                   'với gia đình mình.')
            + _quiz('qz_b3',
                    'Câu nào KHÔNG nên nói khi gửi mẫu nhà?',
                    [('&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;', True),
                     ('&#8220;Em gửi vài mẫu gần nhu cầu để mình tham khảo.&#8221;', False),
                     ('&#8220;Thích chi tiết nào bên em điều chỉnh thiết kế theo.&#8221;', False),
                     ('&#8220;Mấy mẫu này để anh chị có thêm ý tưởng ạ.&#8221;', False)],
                    'Ép khách chốt mẫu tạo áp lực; khách mua giải pháp, không mua mẫu.'))

    def _l_b4(self):
        return (
            self._tag('BƯỚC 4')
            + '<h3>Tạo cảm giác cần quyết định về thời gian khởi công</h3>'
            + '<p>Đặc biệt cuối năm &mdash; khách nào cũng muốn xây xong trước Tết. '
            'Khởi công muộn dễ dẫn tới: thi công gấp, ảnh hưởng tiến độ, khó bàn giao, '
            'khó hoàn thiện.</p>'
            + _box('info', '<b>Câu mẫu:</b> &#8220;Nếu gia đình mình dự kiến ở nhà mới '
                   'trước Tết thì nên triển khai sớm để đảm bảo tiến độ. Để quá sát '
                   'cuối năm thì việc hoàn thiện sẽ rất áp lực.&#8221;')
            + _box('warn', 'Mục tiêu KHÔNG phải gây áp lực vô lý, mà giúp khách hiểu rõ '
                   'hệ quả của việc chậm quyết định.')
            + _quiz('qz_b4',
                    'Khách còn chần chừ trong khi đã cuối năm. Nên nói thế nào?',
                    [('&#8220;Không ký nhanh là giá tăng gấp đôi đấy ạ.&#8221;', False),
                     ('&#8220;Công ty sắp hết suất nhận công trình rồi.&#8221;', False),
                     ('&#8220;Nếu muốn ở nhà mới trước Tết thì nên triển khai sớm để đảm bảo tiến độ, để sát cuối năm hoàn thiện rất áp lực.&#8221;', True),
                     ('&#8220;Anh/chị phải khởi công ngay trong tuần này.&#8221;', False)],
                    'Giúp khách hiểu hệ quả của việc chậm, không dọa dẫm hay ép buộc.'))

    def _l_b5(self):
        return (
            self._tag('BƯỚC 5 &mdash; QUAN TRỌNG NHẤT')
            + '<h3>Khai thác toàn bộ khúc mắc</h3>'
            + _box('warn', 'Khách chưa ký thì chắc chắn còn vấn đề &mdash; nhân viên '
                   'phải TÌM RA, không được tự suy đoán.')
            + _table(['Nhóm', 'Câu hỏi cần khai thác'],
                     [['1. Báo giá', 'Có phù hợp không? Vượt tài chính không? Cần điều chỉnh không?'],
                      ['2. Thiết kế', 'Có thích không? Thay đổi gì? Thêm công năng không?'],
                      ['3. Mẫu nhà', 'Đúng phong cách chưa? Muốn tham khảo thêm không?'],
                      ['4. Gia đình', 'Đã thống nhất chưa? Ai quyết định? Trao đổi thêm với người thân không?'],
                      ['5. Khởi công', 'Dự kiến khi nào? Đang chờ việc gì? Vướng thủ tục không?'],
                      ['6. Niềm tin', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?']],
                     widths=['20%', '80%'])
            + _box('ok', 'Câu hỏi nhóm 6 &mdash; Niềm tin giúp phát hiện RÀO CẢN THẬT '
                   'SỰ trước khi ký.')
            + _quiz('qz_b5',
                    'Khách ưng báo giá và thiết kế nhưng vẫn chưa ký. Câu hỏi nào lộ ra rào cản thật nhất?',
                    [('&#8220;Có vượt tài chính không ạ?&#8221;', False),
                     ('&#8220;Đã đúng phong cách chưa ạ?&#8221;', False),
                     ('&#8220;Dự kiến khởi công khi nào ạ?&#8221;', False),
                     ('&#8220;Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?&#8221;', True)],
                    'Câu hỏi Niềm tin buộc khách nói ra rào cản còn ẩn giấu.'))

    def _l_b6(self):
        return (
            self._tag('BƯỚC 6')
            + '<h3>Khi không còn khúc mắc thì gửi hợp đồng</h3>'
            + '<p>Khi khách đã <b>đồng ý báo giá + đồng ý phương án + không còn vướng '
            'mắc lớn</b> thì đừng nói chuyện chung chung nữa &mdash; chuyển sang gửi '
            'hợp đồng (kèm phụ lục) để khách nghiên cứu.</p>'
            + _box('info', '<b>Câu mẫu:</b> &#8220;Để gia đình có thời gian xem kỹ các '
                   'điều khoản, bên em gửi trước hợp đồng để anh/chị đọc. Có nội dung '
                   'nào cần giải thích hoặc điều chỉnh, em trao đổi ngay để mình yên '
                   'tâm trước khi ký.&#8221;')
            + _quiz('qz_b6',
                    'Khi nào là thời điểm ĐÚNG để chuyển sang gửi hợp đồng?',
                    [('Ngay khi vừa gửi báo giá, để tạo áp lực chốt', False),
                     ('Khi khách đã đồng ý báo giá + phương án và không còn vướng mắc lớn', True),
                     ('Khi khách mới chỉ hỏi giá lần đầu', False),
                     ('Khi khách còn nhiều băn khoăn nhưng mình muốn thúc', False)],
                    'Chỉ gửi hợp đồng khi đã hết khúc mắc lớn.'))

    def _l_b7(self):
        return (
            self._tag('BƯỚC 7')
            + '<h3>Theo dõi hợp đồng</h3>'
            + _box('err', 'Sai lầm của nhiều nhân viên: gửi hợp đồng xong rồi <b>mất hút</b>.')
            + '<p><b>Điều đúng:</b> sau 1&ndash;2 ngày phải hỏi &mdash; đã xem hợp đồng '
            'chưa? có điều khoản nào chưa rõ? có nội dung nào muốn trao đổi thêm?</p>'
            + _box('warn', 'Nếu khách còn băn khoăn thì KHÔNG được bỏ qua &mdash; phải '
                   'giải quyết ngay.')
            + _quiz('qz_b7',
                    'Đã gửi hợp đồng 2 ngày, chưa thấy phản hồi. Nên làm gì?',
                    [('Chờ khách tự đọc xong rồi ký gửi lại', False),
                     ('Chủ động hỏi lại: đã xem chưa, điều khoản nào chưa rõ, muốn trao đổi gì thêm', True),
                     ('Nhắn giục khách ký ngay cho kịp', False),
                     ('Coi như khách không quan tâm nữa', False)],
                    'Gửi hợp đồng xong phải theo dõi, chủ động hỏi lại &mdash; &#8220;mất hút&#8221; là sai lầm.'))

    def _l_b8(self):
        return (
            self._tag('BƯỚC 8')
            + '<h3>Hẹn khảo sát và ký hợp đồng</h3>'
            + '<p>Khi khách đã <b>đồng ý báo giá + thiết kế + hợp đồng</b>, bước tiếp theo:</p>'
            '<ul>'
            '<li>Đề nghị lên lịch <b>khảo sát thực tế</b>.</li>'
            '<li>Thống nhất <b>lịch ký hợp đồng</b>.</li>'
            '<li>Trao đổi rõ quy trình ký kết và khoản <b>đặt cọc 50.000.000 đồng</b> '
            'theo quy định công ty (nếu áp dụng) để khách chủ động sắp xếp.</li>'
            '</ul>'
            + _quiz('qz_b8',
                    'Khách đã đồng ý báo giá, thiết kế và hợp đồng. Bước tiếp theo là gì?',
                    [('Gửi thêm một bộ báo giá mới để khách so sánh', False),
                     ('Quay lại gửi mẫu nhà từ đầu', False),
                     ('Đề nghị lịch khảo sát + thống nhất lịch ký, làm rõ quy trình và khoản đặt cọc', True),
                     ('Chờ khách tự đến công ty ký', False)],
                    'Đã đồng ý cả 3 thì chốt lịch khảo sát + ký và làm rõ đặt cọc 50 triệu.'))

    def _l_gold(self):
        return (
            self._tag('&#127942; NGUYÊN TẮC VÀNG')
            + '<h3>Dẫn dắt khách qua từng bước</h3>'
            + _box('ok', 'Một nhân viên kinh doanh giỏi không phải là người gửi được '
                   'NHIỀU báo giá, mà là người biết DẪN DẮT khách hàng đi qua từng '
                   'bước của hành trình ra quyết định.')
            + '<p>Nếu sau mỗi lần liên hệ, khách tiến thêm một bước (phản hồi báo giá, '
            'giải quyết khúc mắc, xem hợp đồng, hẹn khảo sát...) thì khả năng ký hợp '
            'đồng tăng lên rất nhiều.</p>'
            + _box('warn', 'Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi '
                   'lần tương tác đều phải có mục tiêu rõ ràng và đưa khách tiến gần '
                   'hơn tới quyết định ký hợp đồng.')
            + _quiz('qz_gold',
                    'Theo nguyên tắc vàng, nhân viên kinh doanh GIỎI là người thế nào?',
                    [('Người gửi được nhiều báo giá nhất trong tháng', False),
                     ('Người biết dẫn dắt khách qua từng bước tới quyết định ký', True),
                     ('Người có giá chào thấp nhất cho khách', False),
                     ('Người gọi cho khách nhiều lần nhất trong ngày', False)],
                    'Giỏi = dẫn dắt khách tiến từng bước, không phải gửi thật nhiều báo giá.'))

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (bài THI chấm điểm) - bám sát file + tạo nhóm.
    # ==================================================================
    def _vd_tdbg_questions(self):
        T, F = True, False
        return [
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
