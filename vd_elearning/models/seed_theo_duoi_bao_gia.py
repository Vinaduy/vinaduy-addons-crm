# -*- coding: utf-8 -*-
"""Seed nội dung + 30 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

GIAO DIỆN kiểu Streamlit: menu trái chọn từng bài (micro-learning) + hộp màu +
quiz chấm đúng/sai tức thì (thuần CSS input:checked, KHÔNG JS). vd_body
sanitize=False + render markup() nên HTML thô giữ nguyên.

BẢN NÂNG CẤP (user chốt 2026-07-12): mỗi bước chuyên sâu hơn (nên/không nên, công
thức, cần tránh). Bỏ bước "Gửi mẫu nhà" (gộp vào Quy tắc tạo nhóm - thứ tự gửi
Zalo). Thêm bước "Tín hiệu tiềm năng -> Bám đuổi". Đổi tên Bước 2="Lấy phản hồi
báo giá", Bước 7="Lấy phản hồi hợp đồng". Bước 4 bổ sung lý do thời gian. Bước 5
bỏ nhóm Thiết kế + giải thích vì sao + công thức + sai lầm. Bước 6 chủ động gửi
hợp đồng. Bước 8 nhấn đặt cọc 50tr + giọng nói tự tin. Nguyên tắc vàng tổng hợp
toàn bộ công thức.

Helper nối chuỗi (+) -> tránh bẫy %. Prefix _tdbg_. Idempotent theo version.
"""
from odoo import api, models

_TDBG_VERSION = 'v13-2bg-screenshot-30q'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-tdbg{font-size:16.5px;line-height:1.9;color:#293244;letter-spacing:.1px;}'
    '.vd-tdbg .vd-course{background:linear-gradient(180deg,#fff7f3 0%,#f5faff 100%);'
    'border-radius:18px;padding:16px;}'
    # tieu de lon: chu to, gach chan cam de tach hẳn phan
    '.vd-tdbg h3{font-size:24px;font-weight:900;color:#0f172a;margin:4px 0 18px;line-height:1.3;'
    'padding-bottom:11px;border-bottom:3px solid #ffd0bd;}'
    # tieu de nho: thanh nhan cam ben trai + chu cam, cach xa phan tren de "tho"
    '.vd-tdbg h4{font-size:18.5px;font-weight:800;color:#c2410c;margin:30px 0 12px;line-height:1.4;'
    'padding:2px 0 2px 13px;border-left:5px solid #f97316;}'
    '.vd-tdbg p{margin:0 0 16px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:2px 0 18px;padding-left:24px;}'
    '.vd-tdbg li{margin:10px 0;line-height:1.85;}'
    '.vd-tdbg b{color:#0f172a;font-weight:800;}'
    # chu nhan manh (vang) + chu "khoa" (do)
    '.vd-tdbg .hl{background:linear-gradient(180deg,transparent 55%,#fff3a8 55%);font-weight:800;color:#7c4a03;padding:0 2px;}'
    '.vd-tdbg table{border-collapse:separate;border-spacing:0;width:100%;margin:14px 0 18px;font-size:15.5px;'
    'line-height:1.65;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(2,6,23,.05);}'
    '.vd-tdbg th,.vd-tdbg td{border-bottom:1px solid #eef1f5;border-right:1px solid #eef1f5;padding:12px 15px;text-align:left;vertical-align:top;}'
    '.vd-tdbg tr td:last-child,.vd-tdbg tr th:last-child{border-right:0;}'
    '.vd-tdbg tr:last-child td{border-bottom:0;}'
    '.vd-tdbg th{background:#eef2f9;font-weight:800;color:#334155;font-size:14.5px;letter-spacing:.3px;}'
    '.vd-tdbg td{background:#fff;}'
    '.vd-tdbg tr:nth-child(even) td{background:#fafbfd;}'
    '.vd-tdbg .thok{background:#dcfce7;color:#15803d;}'
    '.vd-tdbg .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-tdbg .no{color:#b91c1c;font-weight:800;font-size:15px;letter-spacing:.5px;}'
    '.vd-tdbg .yes{color:#15803d;font-weight:800;}'
    '.vd-tdbg .navr,.vd-tdbg .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-tdbg .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-tdbg .vc-side{flex:0 0 264px;}'
    '.vd-tdbg .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-tdbg .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-tdbg .vc-navbtn:hover{background:#fff5f1;border-color:#ffd9c9;color:#e8401f;}'
    '.vd-tdbg .vc-nbadge{flex:0 0 auto;display:inline-block;background:#fff1ec;color:#e8401f;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-tdbg .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;}'
    '.vd-tdbg .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:30px 34px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-tdbg .vc-panel{display:none;}'
    '.vd-tdbg .vc-tag{display:inline-block;font-size:12.5px;font-weight:800;letter-spacing:1.2px;'
    'color:#e8401f;background:#fff1ec;padding:5px 13px;border-radius:20px;margin-bottom:12px;text-transform:uppercase;}'
    # hop mau (callout): to hon, thoang hon, chu ro
    '.vd-tdbg .box{border-left:5px solid;border-radius:0 10px 10px 0;padding:14px 18px;margin:16px 0;'
    'font-size:16px;line-height:1.75;}'
    '.vd-tdbg .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-tdbg .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-tdbg .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-tdbg .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # công thức (khung tim) - noi bat, cach xa
    '.vd-tdbg .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:14px;padding:16px 20px;margin:20px 0;box-shadow:0 4px 16px rgba(124,58,237,.1);}'
    '.vd-tdbg .fml .fh{font-weight:800;color:#6d28d9;font-size:13px;letter-spacing:.8px;margin-bottom:7px;}'
    '.vd-tdbg .fml .fml-b{color:#4c1d95;font-weight:600;font-size:16.5px;line-height:1.75;}'
    # thứ tự đánh số
    '.vd-tdbg .vc-order{margin:12px 0;border:1px solid #ffd9c9;border-radius:12px;overflow:hidden;}'
    '.vd-tdbg .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #ffe3d6;background:#fffaf7;}'
    '.vd-tdbg .vc-ostep:last-child{border-bottom:none;}'
    '.vd-tdbg .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#e8401f;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-tdbg .vc-ot{font-weight:800;color:#7c2d12;}'
    '.vd-tdbg .vc-od{color:#9a3412;font-size:14.5px;}'
    # quiz
    '.vd-tdbg .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
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


def _fml(text):
    return ('<div class="fml"><div class="fh">&#128208; CÔNG THỨC THUỘC LÒNG</div>'
            '<div class="fml-b">' + text + '</div></div>')


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _nendont(nen, khong):
    nl = ''.join('<li>' + x + '</li>' for x in nen)
    kl = ''.join('<li>' + x + '</li>' for x in khong)
    return ('<table><tr><th style="width:50%;" class="thok">&#9989; NÊN</th>'
            '<th class="thno">&#10060; KHÔNG NÊN</th></tr>'
            '<tr><td><ul style="margin:0;">' + nl + '</ul></td>'
            '<td><ul style="margin:0;">' + kl + '</ul></td></tr></table>')


def _order(steps):
    out = '<div class="vc-order">'
    for i, (t, d) in enumerate(steps):
        out += ('<div class="vc-ostep"><div class="vc-onum">' + str(i + 1) + '</div>'
                '<div><div class="vc-ot">' + t + '</div>'
                + ('<div class="vc-od">' + d + '</div>' if d else '') + '</div></div>')
    return out + '</div>'


def _quiz(qid, question, options, explain):
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
            + inputs + '<div class="opts">' + labels + '</div>'
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
            'channel_id': ch.id, 'name': 'Bài thi - 30 câu',
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
    #  APP
    # ==================================================================
    def _vd_tdbg_app(self):
        lessons = self._vd_tdbg_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'vdL' + str(i)
            pid = 'vdP' + str(i)
            radios += ('<input class="navr" type="radio" name="vdnav" id="' + rid + '"'
                       + (' checked' if i == 0 else '') + '>')
            badge_html = ('<span class="vc-nbadge">' + badge + '</span>') if badge else ''
            navbtns += ('<label class="vc-navbtn" for="' + rid + '">' + badge_html
                        + '<span class="vc-ntitle">' + icon + ' ' + title + '</span></label>')
            panels += '<section class="vc-panel" id="' + pid + '">' + body + '</section>'
            rules += '#' + rid + ':checked ~ .vc-layout #' + pid + '{display:block}'
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + ']'
                      '{background:#e8401f;color:#fff;border-color:#e8401f}')
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + '] .vc-nbadge'
                      '{background:#ffffff;color:#e8401f}')
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

    def _vd_tdbg_lessons(self):
        return [
            ('&#128170;', 'BƯỚC 1', 'Tự tin báo giá', self._l_b1()),
            ('&#128269;', 'BƯỚC 2', 'Khai thác vấn đề', self._l_b2()),
            ('&#128196;', 'BƯỚC 3', 'Gửi hợp đồng', self._l_b6()),
            ('&#128064;', 'BƯỚC 4', 'Lấy phản hồi hợp đồng', self._l_b7()),
            ('&#9997;&#65039;', 'BƯỚC 5', 'Hẹn khảo sát &amp; ký (chốt)', self._l_b8()),
            ('&#127942;', 'TỔNG KẾT', 'Nguyên tắc vàng', self._l_gold()),
        ]

    # ------------------------------------------------------------------
    #  (Đã bỏ bài "Tư duy & Sai lầm cần tránh": gộp vào TỔNG KẾT - Nguyên
    #   tắc vàng. Đã bỏ bài "Quy tắc tạo nhóm": trùng nội dung khóa khác.)
    # ------------------------------------------------------------------
    def _l_b1(self):
        return (
            self._tag('BƯỚC 1 &mdash; NỀN MÓNG CỦA CẢ QUY TRÌNH')
            + '<h3>Tự tin báo giá</h3>'
            + _box('ok', '<b>Công thức cốt lõi:</b> nhân viên phải THỰC SỰ TỰ TIN rằng '
                   'báo giá này là phương án <b>ưng ý nhất</b> với khách &mdash; tức là '
                   'báo giá <b>khớp với tầm tài chính</b> của khách. Chính mình còn không '
                   'tin thì khách càng không tin.')
            + '<p>Sự tự tin đó KHÔNG đến từ cảm tính, mà đến từ việc bạn đã <span '
            'class="hl">cân đối được tài chính</span> và <span class="hl">hiểu chắc năng '
            'lực thật</span> của khách. Đây là <b>nền móng</b>: làm chắc Bước 1 thì các '
            'bước theo đuổi phía sau mới có ý nghĩa.</p>'

            + '<h4>1&#65039;&#8419; Tự trả lời 3 câu trước khi bấm gửi</h4>'
            + _table(['Câu tự kiểm', 'Kiểm tra điều gì', 'Nếu CHƯA đạt'],
                     [['<b>Đúng nhu cầu khách?</b>', 'Tài chính, phong cách, mục đích xây có khớp không', 'Chưa gửi &mdash; hỏi lại nhu cầu, sửa cho khớp'],
                      ['<b>Giải quyết tài chính?</b>', 'Có vượt ngân sách? có phương án tối ưu/giảm chi phí? có giải thích rõ vì sao ra số tiền?', 'Cân đối lại phương án rồi mới gửi'],
                      ['<b>Đúng mong muốn?</b>', 'Số tầng, phòng, phong cách, mức hoàn thiện, thang máy, gara, sân', 'Sửa cho tất cả KHỚP']],
                     widths=['22%', '52%', '26%'])
            + _box('warn', 'Đừng gửi kiểu &#8220;Em gửi anh/chị tham khảo nhé&#8221; khi '
                   'chính mình còn chưa chắc. Nếu chính nhân viên còn không tự tin thì '
                   'khách càng không tin.')

            + '<h4>2&#65039;&#8419; XỬ LÝ theo mức CHÊNH LỆCH tài chính (thuộc lòng)</h4>'
            + '<p>Đây là phần quan trọng nhất của Bước 1. Tùy mức chênh giữa <b>giá trị '
            'báo giá</b> và <b>tầm tài chính thật</b> của khách mà xử lý khác nhau:</p>'
            + _table(['Mức chênh lệch', 'Cách xử lý BẮT BUỘC'],
                     [['<b>Khớp / chênh &le; 100 triệu</b>',
                       '<span class="yes">TỰ TIN GỬI</span> &mdash; báo giá đã ưng ý, cân đối tốt.'],
                      ['<b>Chênh trên 100 triệu (đến ~300 triệu)</b>',
                       'BÀN BẠC lại với khách để cân đối cho phù hợp <b>rồi mới quyết định gửi</b>: (a) GIẢM DIỆN TÍCH cho khớp, HOẶC (b) xác định khách có thể CỐ THÊM tài chính (vay/mượn/xoay/vay ngân hàng) hay không &mdash; rồi vẫn cố gắng GỬI báo giá.'],
                      ['<b>Chênh QUÁ LỚN, không xoay được</b>',
                       'Ví dụ khách muốn xây 1 tỷ nhưng chỉ có 600 triệu và không có cách kiếm thêm &rarr; trường hợp này có thể KHÔNG gửi. Nhân viên tự cân nhắc quyết định.']],
                     widths=['30%', '70%'])
            + _box('info', '<b>Chốt chắc năng lực tài chính THẬT của khách.</b> Nhiều '
                   'khách chỉ có đúng khoản để &#8220;quay đầu&#8221;; nhưng nhiều khách '
                   'vẫn có thể vay thêm, mượn thêm, xoay xở thêm, hoặc xác định vay ngân '
                   'hàng. Nhiệm vụ của bạn là HỎI RÕ và chốt chắc: khách có thể cố tới '
                   'mức nào? Cân đối được tầm tài chính là <b>phương án tối thượng</b> để '
                   'đi đến thành công.')

            + '<h4>3&#65039;&#8419; Định hướng công ty: VẪN PHẢI gửi báo giá (trừ ca cực đoan)</h4>'
            + '<p>Chiến lược của công ty: toàn bộ nhân viên cố gắng tối đa <b>gửi báo giá '
            'ngay trong NGÀY ĐẦU</b>, cùng ngày với ngày gọi điện tư vấn. Kể cả khi báo '
            'giá cao hơn mong muốn của khách, định hướng vẫn là <b>phải gửi</b> để khách '
            'có cơ hội nhìn thấy báo giá của mình.</p>'
            + _box('ok', '<b>Vì sao vẫn phải gửi dù chưa thuyết phục được tầm tài chính '
                   'ban đầu?</b> Vì có gửi thì khách mới nhìn thấy: bảng báo giá, <b>danh '
                   'mục vật tư</b>, hình ảnh trong báo giá, các <b>vật tư không có trong '
                   'hợp đồng</b>. Khách sẽ suy nghĩ, tính toán. Không gửi = khách không có '
                   'gì để cân nhắc, và mất luôn cơ hội.')
            + _box('info', '<b>Khách mang báo giá đi so sánh là chuyện HẾT SỨC BÌNH '
                   'THƯỜNG &mdash; đừng sợ.</b> Không một khách nào bỏ ra cả tỷ đồng xây '
                   'nhà (khoản tiền lớn cả đời) mà chỉ hỏi đúng một đơn vị rồi ký ngay. '
                   'Gần như 100% khách đều xin 3&ndash;5 báo giá của nhiều nhà thầu để đặt '
                   'cạnh nhau so sánh &mdash; đó là nhu cầu CHÍNH ĐÁNG của người bỏ tiền, '
                   'không phải khách &#8220;chê&#8221; mình. Điều mấu chốt: <b>muốn được '
                   'so sánh thì trước hết PHẢI có báo giá của mình trong tay khách</b>. '
                   'Nếu vì sợ bị so sánh mà không gửi, khách chỉ còn báo giá của đối thủ '
                   'để cân nhắc &mdash; mình tự loại mình khỏi cuộc chơi. Ngược lại, khi '
                   'báo giá của mình nằm trên bàn cùng các đơn vị khác, mình MỚI có cơ hội '
                   'chứng minh: vật tư tốt hơn, hạng mục đầy đủ hơn, tư vấn tận tâm hơn. '
                   'Vậy nên tư duy đúng là <b>cứ TỰ TIN GỬI, rồi chủ động đồng hành để '
                   'khách thấy mình là lựa chọn hợp lý nhất</b>.')
            + _box('info', '<b>Nguyên tắc CHỤP MÀN HÌNH báo giá:</b> sau khi gửi file, hãy '
                   '<b>chụp màn hình</b> bảng báo giá (nhất là <b>tổng giá trị hợp đồng</b> '
                   'và <b>đơn giá theo m&#178;</b>) gửi cho khách dễ nhìn. Dù khách nói '
                   '&#8220;chưa xem/đang xem&#8221;, chắc chắn khách ĐÃ liếc qua tổng giá '
                   'trị và đơn giá &mdash; đó là điểm để bắt chuyện khai thác sau này.')

            + '<h4>&#128260; Chiến thuật QUAN TRỌNG: GỬI 2 BÁO GIÁ song song khi khách nhất quyết giữ diện tích lớn</h4>'
            + '<p>Đây là tình huống rất hay gặp và <b>cực kỳ quan trọng</b>: khi bạn đã '
            'trao đổi với khách về việc cần <b>cắt giảm diện tích</b> cho phù hợp tầm tài '
            'chính, nhưng khách <b>nhất quyết không nghe</b>, vẫn yêu cầu làm đúng diện '
            'tích lớn đó &mdash; trong khi tài chính của khách vẫn còn <b>thiếu từ 100 đến '
            '300 triệu</b>. Cách xử lý đúng là chủ động làm <b>2 bảng báo giá</b>:</p>'
            + _order([
                ('Làm BÁO GIÁ 1 &mdash; theo ĐÚNG diện tích khách yêu cầu',
                 'Tôn trọng mong muốn của khách: làm một báo giá đầy đủ theo diện tích lớn mà khách nhất quyết giữ.'),
                ('CHỦ ĐỘNG làm thêm BÁO GIÁ 2 &mdash; diện tích đã cắt giảm cho phù hợp',
                 'Bạn tự tay làm thêm báo giá thứ hai, chủ động cắt giảm diện tích để tổng tiền khớp với tầm tài chính thật của khách.'),
                ('GỬI CẢ 2 báo giá CÙNG MỘT THỜI ĐIỂM',
                 'Gửi đồng thời 2 bảng báo giá cho khách, để khách tự đặt 2 mức TỔNG TIỀN cạnh nhau mà so sánh.'),
            ])
            + _box('warn', '<b>Vì sao phải làm vậy?</b> Nếu chỉ gửi báo giá theo diện tích '
                   'lớn khách yêu cầu thì tổng tiền RẤT CAO; gửi xong khách nhìn con số đó '
                   'sẽ nản, không quan tâm nữa rồi trôi mất. Khi có thêm báo giá thứ hai '
                   'với diện tích phù hợp &mdash; tài chính đương nhiên phù hợp hơn vì '
                   'diện tích đã cắt giảm &mdash; khách có cơ hội cân nhắc và thường sẽ '
                   'nghiêng về phương án vừa túi tiền.')
            + _box('ok', '<b>Câu KHẲNG ĐỊNH bắt buộc phải nói với khách:</b> &#8220;Em đảm '
                   'bảo với diện tích đã cắt giảm này, bên em vẫn thiết kế ĐỦ công năng và '
                   'ĐỦ số phòng ngủ như anh/chị mong muốn ạ.&#8221; &mdash; phải nói CHẮC '
                   'để khách yên tâm rằng cắt diện tích KHÔNG có nghĩa là thiếu tiện nghi.')

            + '<h4>&#10060; Những SAI LẦM khiến báo giá bị &#8220;kẹt&#8221;</h4>'
            + '<ul>'
            '<li><b>Cuộc gọi đầu không khai thác tầm tài chính thật</b> &mdash; không hỏi '
            'khách thực sự bỏ ra được bao nhiêu, cố thêm tối đa được bao nhiêu.</li>'
            '<li><b>Không đưa phương án bàn bạc</b> để chọn diện tích phù hợp nhất với tầm '
            'tài chính của khách.</li>'
            '<li><b>Đã cân đối tài chính xong nhưng vẫn không gửi</b> &mdash; chênh chỉ '
            'khoảng 10&ndash;20% tổng giá trị, đã giải quyết triệt để năng lực tài chính '
            'thật của khách, vậy mà <b>lưỡng lự 2&ndash;3 ngày</b> vẫn không chịu gửi báo giá.</li>'
            '</ul>'
            + _nendont(
                ['Cân đối khớp tầm tài chính rồi TỰ TIN gửi',
                 'Chốt chắc khách cố thêm được tới đâu (vay/mượn/xoay)',
                 'Gửi ngay trong ngày đầu &mdash; chênh 200&ndash;300tr vẫn cố gửi',
                 'Giải thích rõ vì sao ra con số đó'],
                ['Gửi báo giá vượt xa ngân sách mà chưa bàn bạc',
                 'Bỏ qua khai thác tài chính ở cuộc gọi đầu',
                 'Đã cân đối xong vẫn lưỡng lự 2&ndash;3 ngày không gửi',
                 'Gửi kèm câu &#8220;anh/chị tham khảo nhé&#8221; khi mình chưa chắc'])
            + _fml('Tự tin báo giá = <b>Cân đối KHỚP tài chính</b> (chênh &gt;100tr thì '
                   'bàn lại; 100&ndash;300tr thì giảm diện tích/khách cố thêm) &rarr; '
                   '<b>GỬI ngay trong ngày đầu</b>. Cân đối tài chính là phương án tối '
                   'thượng; trừ ca chênh quá lớn không xoay được &rarr; vẫn phải gửi bằng mọi giá.'))

    # ------------------------------------------------------------------
    def _l_b2(self):
        return (
            self._tag('BƯỚC 2 &mdash; TRÁI TIM CỦA QUY TRÌNH')
            + '<h3>Khai thác vấn đề</h3>'
            + _box('ok', 'Sau khi gửi báo giá <b>1&ndash;2 ngày</b>, nhân viên BẮT BUỘC '
                   'quay lại với khách để KHAI THÁC. Không phải &#8220;hỏi thăm tình '
                   'hình&#8221; cho có, mà phải <b>khai thác liên tục MỌI thông tin, thái '
                   'độ, biểu cảm, cảm xúc, nhận xét</b> của khách về báo giá &mdash; để '
                   'nắm bắt được <b>TÂM LÝ và MONG MUỐN THẬT</b> của khách.')
            + _box('err', '<b>Sai lầm lớn nhất:</b> gửi báo giá xong rồi im luôn, hoặc '
                   'chỉ gọi &#8220;hỏi tình hình&#8221; chứ thực sự KHÔNG nắm bắt được tâm '
                   'lý, mong muốn của khách để GIẢI QUYẾT. Gọi mà không ra vấn đề = cuộc '
                   'gọi vô nghĩa.')

            + '<h4>&#128241; Quy trình tiếp cận: NHẮN trước &mdash; GỌI sau (gọi ÍT nhưng HIỆU QUẢ)</h4>'
            + _order([
                ('NHẮN TIN dò hỏi TRÊN NHÓM trước',
                 'Sau 1&ndash;2 ngày, nhắn tin trên nhóm để dò tình hình trước khi gọi.'),
                ('Khách nói &#8220;đang xem&#8221; hoặc nhắn 2&ndash;3 lần không trả lời &rarr; GỌI ĐIỆN NGAY',
                 'Khách nói &#8220;đang xem&#8221; nghĩa là khách ĐÃ xem nhưng lấy lý do trì hoãn &mdash; phải gọi để trao đổi luôn.'),
                ('GỌI ÍT NHƯNG HIỆU QUẢ',
                 'Chỉ cần 1 cuộc gọi, nhưng cuộc đó PHẢI khai thác ra được vấn đề khách đang vướng. Đã mất công gọi thì phải RA kết quả, phải lấy được lý do cuối cùng.'),
            ])
            + _box('info', '<b>Đã mất công gọi thì CHỐT luôn:</b> &#8220;Bên em làm báo giá '
                   'với tầm tài chính như vậy thì anh/chị mới xây được ạ. Đây là mức giá '
                   'tốt nhất, chính xác nhất, không có gì thay đổi. Anh/chị thấy mức này ổn '
                   'chưa, có cần điều chỉnh gì không? Nếu tài chính hơi vượt thì bên em '
                   'cân nhắc lại diện tích cho phù hợp.&#8221;')

            + '<h4>1&#65039;&#8419; 4 ý BẮT BUỘC khai thác được</h4>'
            + _table(['Câu hỏi cụ thể', 'Để làm gì'],
                     [['&#8220;Anh/chị đã <b>xem kỹ báo giá</b> và <b>phụ lục vật tư</b> chưa ạ?&#8221;',
                       'Xác nhận khách ĐÃ đọc &mdash; nhiều khách chưa mở ra xem.'],
                      ['&#8220;Anh/chị thấy <b>phần nào hợp lý</b>, <b>phần nào còn băn khoăn</b>?&#8221;',
                       'Tìm ĐÚNG điểm khách đang lăn tăn để xử lý.'],
                      ['&#8220;<b>Mức đầu tư</b> này có phù hợp với dự tính của gia đình không ạ?&#8221;',
                       'Kiểm tra có khớp tài chính không &mdash; điểm quyết định.'],
                      ['&#8220;Có <b>hạng mục nào</b> anh/chị muốn điều chỉnh thêm không?&#8221;',
                       'Mở đường để chỉnh phương án, giữ khách tiếp tục trao đổi.']],
                     widths=['54%', '46%'])
            + '<p>Khách im lặng KHÔNG có nghĩa là hết quan tâm &mdash; có thể vì: báo giá '
            'cao hơn dự kiến &middot; chưa đúng nhu cầu &middot; chưa hiểu cách tính '
            '&middot; đang chờ đơn vị khác &middot; chưa đủ niềm tin &middot; chưa biết '
            'nên hỏi gì. Việc của nhân viên là <span class="hl">KHAI THÁC, không ĐOÁN</span>.</p>'

            + '<h4>2&#65039;&#8419; 5 NHÓM khúc mắc phải TÌM RA (khách chưa ký = còn vấn đề)</h4>'
            + _table(['Nhóm khai thác', 'Hỏi gì', 'Vì sao QUAN TRỌNG'],
                     [['<b>1. Báo giá</b>', 'Có phù hợp? Có vượt tài chính? Cần điều chỉnh?',
                       'Tài chính là rào cản SỐ 1 &mdash; lệch tiền là khách bỏ.'],
                      ['<b>2. Mẫu nhà</b>', 'Đã đúng phong cách chưa? Muốn tham khảo thêm?',
                       'Khách chưa ưng &#8220;hình hài&#8221; ngôi nhà thì chưa quyết.'],
                      ['<b>3. Gia đình</b>', 'Đã thống nhất chưa? AI là người quyết định? Cần bàn thêm với người thân?',
                       'Rất nhiều ca đổ vỡ vì thuyết phục sai người &mdash; người quyết thật chưa gật.'],
                      ['<b>4. Khởi công</b>', 'Dự kiến khi nào? Đang chờ việc gì? Vướng thủ tục?',
                       'Biết mốc thời gian để tạo lý do thúc tiến độ (thi công gấp).'],
                      ['<b>5. Niềm tin</b>', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?',
                       'Lộ ra RÀO CẢN THẬT SỰ còn ẩn giấu &mdash; thứ đang chặn khách ký.']],
                     widths=['16%', '42%', '42%'])
            + _box('warn', '<b>Cốt lõi:</b> phần lớn vấn đề của khách nằm ở <b>BẢNG BÁO '
                   'GIÁ và TẦM TÀI CHÍNH</b>. Mọi lý do khác chỉ là phụ. Việc số 1 là làm '
                   'cho <b>bảng báo giá cân đối được</b> với tài chính của khách.')
            + _box('info', '<b>Điểm đặc biệt lưu ý &mdash; &#8220;gia đình chưa bàn&#8221;:</b> '
                   'khách hay lấy lý do phải bàn với gia đình. Nhưng <b>bản thân khách phải '
                   'OK trước thì gia đình mới OK</b>. Vậy nên phải làm cho CHÍNH khách chốt '
                   'được tương đối đã, đừng để khách mượn cớ &#8220;gia đình&#8221; mà trôi.')

            + '<h4>3&#65039;&#8419; Khách TƯƠNG TÁC = tín hiệu tiềm năng &rarr; BÁM ĐUỔI ngay</h4>'
            + '<p>Nếu khách có BẤT KỲ tương tác nào &mdash; hỏi về giá, về phụ lục vật tư, '
            'hay một câu hỏi rất nhỏ &mdash; thì đó là <b>tín hiệu khách RẤT tiềm '
            'năng</b>: khách đã đọc, đã suy nghĩ, đang quan tâm. Câu hỏi dù nhỏ cũng là '
            'cánh cửa mở.</p>'
            + _nendont(
                ['Trả lời NHANH, nhiệt tình, rõ ràng',
                 'Dùng chính câu hỏi đó làm cầu nối khai thác thêm',
                 'Xếp khách này vào diện ƯU TIÊN bám đuổi'],
                ['Trả lời qua loa/cụt lủn rồi để nguội',
                 'Để câu hỏi &#8220;treo&#8221; vài ngày mới trả lời',
                 'Coi câu hỏi nhỏ là không quan trọng'])

            + '<h4>4&#65039;&#8419; MỌI cuộc gọi phải đề cập THI CÔNG GẤP</h4>'
            + '<p>Trong mọi cuộc gọi, nhân viên <b>luôn luôn</b> phải đề cập chuyện <b>thi '
            'công gấp</b>. Đặc biệt cuối năm, ai cũng muốn xây xong, bàn giao trước Tết '
            '&mdash; không ký sớm thì KHÔNG kịp:</p>'
            + _table(['Việc cần thời gian', 'Vì sao ảnh hưởng tiến độ'],
                     [['<b>Thiết kế bản vẽ</b>', 'Tối thiểu 1 tháng; khách duyệt chậm có khi mất tới 2 tháng.'],
                      ['<b>Chuẩn bị thợ</b>', 'Không thỏa thuận sớm thì không bố trí, chuẩn bị thợ kịp.'],
                      ['<b>Các phòng ban chuẩn bị</b>', 'Vật tư, kế hoạch, dự toán, nhân lực &mdash; đều cần thời gian.'],
                      ['<b>Hoàn thiện cuối</b>', 'Nội thất, dọn dẹp, sân vườn &mdash; không bố trí sớm thì không kịp Tết.']],
                     widths=['30%', '70%'])
            + _box('info', '<b>Câu mẫu:</b> &#8220;Nếu gia đình muốn ở nhà mới trước Tết '
                   'thì mình nên chốt sớm ạ. Vì riêng thiết kế đã mất 1&ndash;2 tháng, rồi '
                   'còn chuẩn bị thợ, vật tư, dự toán, nhân lực; sát cuối năm thì nội thất, '
                   'sân vườn, dọn dẹp sẽ rất gấp.&#8221; &mdash; giúp khách HIỂU hệ quả, '
                   'KHÔNG dọa dẫm.')

            + '<h4>&#10060; Những SAI LẦM khi khai thác</h4>'
            + '<ul>'
            '<li>Gọi hỏi <b>chung chung</b> &#8220;anh xem báo giá chưa?&#8221;; khách nói '
            '&#8220;đang xem&#8221; thì chỉ đáp &#8220;vâng anh xem đi&#8221; rồi tắt máy '
            '&mdash; KHÔNG khai thác được gì.</li>'
            '<li>Gọi <b>rất nhiều cuộc</b> nhưng không cuộc nào ra kết quả (không biết '
            'khách đã ưng chưa, có thấy đắt/cao không, vật tư có đáp ứng không, đã bàn gia '
            'đình chưa, thời gian thi công thế nào).</li>'
            '<li>Chỉ hỏi <b>tình hình</b> chứ không nắm bắt được TÂM LÝ, MONG MUỐN của '
            'khách để giải quyết.</li>'
            '<li>Bỏ sót nhóm <b>Gia đình / Niềm tin</b> &rarr; thuyết phục sai người, hoặc '
            'khách lăn tăn ngầm rồi im lặng bỏ đi &mdash; mất khách không rõ lý do.</li>'
            '<li>Gửi báo giá xong <b>không biết làm gì</b>, không biết hỏi gì, không biết '
            'bước tiếp theo &mdash; hay gặp ở nhân viên mới.</li>'
            '</ul>'
            + _nendont(
                ['Nhắn dò trước, khách &#8220;đang xem&#8221; thì GỌI ngay',
                 'Gọi ÍT nhưng phải khai thác RA vấn đề (1 cuộc hiệu quả)',
                 'Khai thác đủ 5 nhóm, luôn kết bằng câu hỏi NIỀM TIN',
                 'Mọi cuộc gọi đều nhắc THI CÔNG GẤP',
                 'Chốt để CHÍNH khách OK trước, rồi mới tới gia đình'],
                ['Hỏi chung chung rồi &#8220;vâng anh xem đi&#8221; tắt máy',
                 'Gọi nhiều cuộc mà không cuộc nào ra kết quả',
                 'Chỉ hỏi tình hình, không nắm tâm lý khách',
                 'Đoán mò thay vì hỏi thẳng',
                 'Để khách mượn cớ &#8220;gia đình chưa bàn&#8221; rồi trôi'])
            + _fml('Khai thác vấn đề = <b>Nhắn dò &rarr; GỌI (ít nhưng hiệu quả)</b> để '
                   'moi bằng được TÂM LÝ thật. Đủ 5 nhóm: <b>Báo giá &mdash; Mẫu nhà '
                   '&mdash; Gia đình &mdash; Khởi công &mdash; Niềm tin</b> (cốt lõi vẫn là '
                   'BÁO GIÁ + TÀI CHÍNH). Mọi cuộc gọi nhắc THI CÔNG GẤP. Bản thân khách '
                   'OK trước &rarr; gia đình mới OK.'))

    # ------------------------------------------------------------------
    def _l_b6(self):
        return (
            self._tag('BƯỚC 3')
            + '<h3>Chủ động gửi hợp đồng</h3>'
            + '<p>Khi nhân viên cảm thấy: khách <b>không hỏi gì thêm</b>, HOẶC khách '
            '<b>đang để ý báo giá</b> của mình, HOẶC khách đã có <b>một vài phản hồi</b> '
            'về báo giá &mdash; <b>kết hợp với thời gian khởi công đang gấp</b> &mdash; '
            'thì phải <b>chủ động</b> đề cập sẽ gửi file hợp đồng cho khách tham khảo, '
            'hoặc <b>cố tình tạo tình huống</b> để gửi hợp đồng.</p>'
            + _box('ok', '<b>Mục đích:</b> gửi hợp đồng để có <b>LÝ DO chính đáng</b> '
                   'dồn khách vào việc hẹn gặp ký. Hành động sớm &mdash; không chần chừ.')
            + _box('info', '<b>Dấu hiệu ĐỦ ĐIỀU KIỆN để gửi hợp đồng mẫu:</b> chỉ cần '
                   'khách đã có <b>ít nhất 2&ndash;3 phản hồi</b> về báo giá, VÀ bạn đã '
                   'chốt được rằng <b>với tầm tài chính đó khách OK với báo giá</b> '
                   '&mdash; thì chuyên viên tư vấn <b>phải chủ động gửi HỢP ĐỒNG MẪU</b> '
                   'cho khách ngay, không cần chờ thêm tín hiệu nào khác.')
            + _box('info', '<b>Câu mẫu:</b> &#8220;Để gia đình chủ động xem trước các '
                   'điều khoản, bên em gửi luôn file hợp đồng để anh/chị tham khảo. Có '
                   'chỗ nào cần giải thích em trao đổi ngay, rồi mình sắp lịch gặp để '
                   'hoàn tất cho kịp tiến độ ạ.&#8221;')
            + _nendont(
                ['Chủ động gửi khi thấy khách để ý / có phản hồi + thời gian gấp',
                 'Tạo tình huống hợp lý để gửi hợp đồng',
                 'Gửi kèm lời hẹn sắp lịch gặp ký',
                 'Hành động SỚM, dứt khoát'],
                ['Chần chừ chờ khách tự hỏi đến hợp đồng',
                 'Nói chuyện chung chung, không chuyển bước',
                 'Chờ &#8220;khi nào khách sẵn sàng&#8221;'])
            + _box('err', '<b>Nếu chần chừ:</b> khách nguội dần, đối thủ chen vào, mất '
                   'lý do để hẹn gặp &mdash; cơ hội chốt trôi qua.')
            + _fml('Khách để ý/có phản hồi + thời gian gấp &rarr; <b>CHỦ ĐỘNG gửi hợp '
                   'đồng ngay</b> để lấy LÝ DO hẹn gặp ký. Không chần chừ.')
            + _quiz('qz_b6',
                    'Khi nào nên chủ động gửi hợp đồng cho khách?',
                    [('Chờ đến khi khách tự hỏi về hợp đồng', False),
                     ('Khi thấy khách để ý/không hỏi thêm/có vài phản hồi về báo giá + thời gian khởi công gấp &rarr; chủ động gửi để có lý do hẹn ký', True),
                     ('Chỉ gửi khi khách đã đồng ý tất cả bằng văn bản', False),
                     ('Không bao giờ gửi trước khi khách yêu cầu', False)],
                    'Chủ động gửi hợp đồng để tạo lý do dồn khách hẹn gặp ký &mdash; không chần chừ.'))

    # ------------------------------------------------------------------
    def _l_b7(self):
        return (
            self._tag('BƯỚC 4')
            + '<h3>Lấy phản hồi hợp đồng</h3>'
            + _box('err', 'Sai lầm: gửi hợp đồng xong rồi <b>mất hút</b>. Phải chủ động '
                   'sau 1&ndash;2 ngày để LẤY PHẢN HỒI về hợp đồng.')
            + '<p>Khi nhận hợp đồng, khách sẽ thắc mắc &mdash; nhân viên phải <b>lựa để '
            'dò xem khách có băn khoăn những điểm này không</b> để còn xử lý:</p>'
            + _table(['# ', 'Khách hay thắc mắc về', 'Nhân viên xử lý thế nào'],
                     [['1', '<b>Phụ lục vật tư</b> (thắc mắc nhiều nhất)', 'KHẲNG ĐỊNH đây là vật tư TỐT trên thị trường &mdash; nói chắc, có dẫn chứng.'],
                      ['2', '<b>Các đợt ứng</b> (tiến độ thanh toán)', 'Giải thích rõ từng đợt ứng gắn với tiến độ thi công.'],
                      ['3', '<b>Tiền bảo hành</b>', 'Nêu rõ mức giữ lại/tiền bảo hành theo hợp đồng.'],
                      ['4', '<b>Thời gian bảo hành</b>', 'Nêu rõ thời hạn bảo hành công trình.'],
                      ['5', '<b>Tiến độ thi công</b>', 'Cam kết mốc tiến độ, cách kiểm soát.'],
                      ['6', '<b>Vài vấn đề khác</b> về hợp đồng', 'Chủ động hỏi để phát hiện và giải quyết ngay.']],
                     widths=['6%', '34%', '60%'])
            + _nendont(
                ['Chủ động hỏi lại sau 1&ndash;2 ngày',
                 'Lựa dò đủ 6 nhóm thắc mắc trên',
                 'Khẳng định mạnh mẽ về chất lượng vật tư',
                 'Giải quyết dứt điểm từng băn khoăn'],
                ['Gửi hợp đồng xong im luôn',
                 'Nói mơ hồ về vật tư/bảo hành/đợt ứng',
                 'Bỏ qua khi khách còn lăn tăn'])
            + _fml('Gửi hợp đồng &rarr; sau 1&ndash;2 ngày LẤY PHẢN HỒI. Dò 6 điểm: '
                   '<b>Phụ lục vật tư (khẳng định tốt) &mdash; Đợt ứng &mdash; Tiền bảo '
                   'hành &mdash; Thời gian bảo hành &mdash; Tiến độ &mdash; Khác</b>.')
            + _quiz('qz_b7',
                    'Khi gửi hợp đồng, khách thường thắc mắc NHIỀU NHẤT về điều gì, và nhân viên phải làm gì?',
                    [('Về màu sắc bản vẽ &mdash; đổi lại cho khách', False),
                     ('Về phụ lục vật tư &mdash; phải KHẲNG ĐỊNH đây là vật tư tốt trên thị trường', True),
                     ('Về tên công ty &mdash; giải thích lịch sử công ty', False),
                     ('Không cần quan tâm, chờ khách ký', False)],
                    'Phụ lục vật tư là thắc mắc chính &mdash; phải khẳng định chắc chắn về chất lượng.'))

    # ------------------------------------------------------------------
    def _l_b8(self):
        return (
            self._tag('BƯỚC 5 &mdash; BƯỚC QUYẾT ĐỊNH')
            + '<h3>Hẹn khảo sát và ký hợp đồng</h3>'
            + _box('ok', 'Đây là bước CHỐT cơ bản của một nhân viên kinh doanh. Làm tốt '
                   'bước này (hẹn thành công) thì Sếp đi ký tỷ lệ thành công rất cao '
                   '&mdash; <b>10 khách ký được 9</b>.')
            + '<h4>Trước khi đi hẹn, PHẢI đảm bảo</h4>'
            + '<ul>'
            '<li><b>Tất cả khúc mắc về hợp đồng đã được giải quyết</b> &mdash; khách '
            'KHÔNG còn thắc mắc gì về hợp đồng nữa. Phải HỎI KỸ lại khách về các khúc '
            'mắc hợp đồng trước khi hẹn.</li>'
            '<li><b>Trao đổi trước về việc đặt cọc 50.000.000đ</b> (ưu tiên TIỀN MẶT).</li>'
            '</ul>'
            + _box('warn', '<b>Vì sao phải chốt tiền cọc TRƯỚC?</b> Nếu không thỏa '
                   'thuận trước, khi về ký khách hay lấy lý do &#8220;chưa chuẩn bị '
                   'tiền&#8221; hoặc &#8220;tiền gửi ngân hàng chưa rút được&#8221;. Khi '
                   'mình đề cập tiền cọc, khách sẽ có <b>tâm lý chuẩn bị ký cao hơn</b>.')
            + _box('err', '<b>NGUYÊN TẮC BẮT BUỘC khi thực hiện bước này &mdash; GIỌNG '
                   'NÓI:</b> phải TỰ TIN, nói MẠNH, nói CHẮC, KHÔNG rụt rè. Nói theo '
                   'kiểu KHẲNG ĐỊNH, giọng TO và CHẮC.')
            + _nendont(
                ['Hỏi kỹ, chốt hết khúc mắc hợp đồng TRƯỚC khi hẹn',
                 'Chủ động chốt đặt cọc 50 triệu (ưu tiên tiền mặt)',
                 'Giọng tự tin, mạnh, chắc, khẳng định',
                 'Thống nhất lịch khảo sát + lịch ký rõ ràng'],
                ['Hẹn khi khách còn thắc mắc hợp đồng',
                 'Né tránh, không nhắc chuyện tiền cọc',
                 'Nói rụt rè, ngập ngừng, thiếu chắc chắn',
                 'Để lịch hẹn mơ hồ &#8220;khi nào rảnh&#8221;'])
            + _fml('Bước chốt = <b>Hết khúc mắc HĐ + Chốt cọc 50tr (tiền mặt) + Giọng '
                   'TỰ TIN, MẠNH, CHẮC, KHẲNG ĐỊNH</b> &rarr; hẹn khảo sát + ký. Hẹn '
                   'tốt = 10 ký 9.')
            + _quiz('qz_b8',
                    'Nguyên tắc quan trọng nhất về CÁCH NÓI khi thực hiện bước hẹn ký là gì?',
                    [('Nói nhẹ nhàng, rào trước đón sau cho khách thoải mái', False),
                     ('Giọng tự tin, nói mạnh, nói chắc, khẳng định &mdash; không rụt rè', True),
                     ('Nói thật nhanh cho xong', False),
                     ('Để khách nói là chính, mình chỉ nghe', False)],
                    'Bước chốt cần giọng tự tin, mạnh, chắc, khẳng định &mdash; kèm chốt cọc 50tr trước.'))

    # ------------------------------------------------------------------
    def _l_gold(self):
        return (
            self._tag('&#127942; TỔNG KẾT &amp; TƯ DUY NỀN TẢNG')
            + '<h3>Nguyên tắc vàng: gửi báo giá là BẮT ĐẦU, không phải kết thúc</h3>'
            + _box('err', '<b>Sai lầm chí mạng:</b> gửi báo giá xong rồi&hellip; im lặng '
                   'chờ khách gọi lại. Đây là nguyên nhân mất RẤT nhiều khách.')
            + '<p>Khách đang xây nhà thường cùng lúc: xem rất nhiều đơn vị &middot; chưa '
            'hiểu hết báo giá &middot; chưa biết nên hỏi gì &middot; đang cân nhắc tài '
            'chính &middot; đang so sánh. Không chủ động dẫn dắt thì khách nghiêng dần '
            'sang đơn vị khác. Vì vậy toàn bộ khóa học này xoay quanh một tư duy: <b>sau '
            'khi gửi báo giá, việc theo đuổi mới thật sự bắt đầu</b>.</p>'
            + '<h4>Tư duy đúng của người bán hàng giỏi</h4>'
            + _nendont(
                ['Chủ động nhắc &amp; đồng hành cùng khách sau báo giá',
                 'Bán GIẢI PHÁP phù hợp gia đình khách, không chỉ bán giá',
                 'Mỗi lần liên hệ đưa khách tiến thêm ít nhất 1 bước'],
                ['Gửi xong rồi ngồi chờ khách gọi lại',
                 'Chỉ chăm chăm so sánh con số tiền với đối thủ',
                 'Để khách &#8220;treo&#8221;, im lặng quá lâu'])
            + _box('ok', 'Nhân viên GIỎI không phải người gửi nhiều báo giá nhất, mà là '
                   'người biết DẪN DẮT khách qua từng bước tới quyết định ký. Sau mỗi lần '
                   'liên hệ, khách phải tiến thêm ít nhất 1 bước.')
            + _fml('Dòng chảy sau báo giá: <b>Báo giá &rarr; Phản hồi &rarr; Hiểu suy '
                   'nghĩ &rarr; Gỡ khúc mắc &rarr; Gửi hợp đồng &rarr; Gỡ khúc mắc HĐ '
                   '&rarr; Hẹn ký</b>. Khách im lặng = quy trình đang DỪNG lại &rarr; '
                   'phải chủ động nối tiếp.')
            + '<h4>&#128221; Bảng công thức TOÀN KHÓA (thuộc lòng)</h4>'
            + _table(['Bước', 'Công thức thuộc lòng'],
                     [['<b>Bước 1 &mdash; Tự tin báo giá</b>', 'Cân đối KHỚP tài chính rồi TỰ TIN gửi ngay trong ngày đầu (chênh trên 100tr thì bàn lại: giảm diện tích/khách cố thêm; trừ ca chênh quá lớn không xoay được). Khách nhất quyết giữ diện tích lớn mà vẫn thiếu 100&ndash;300tr &rarr; GỬI 2 BÁO GIÁ song song (đúng diện tích + diện tích cắt giảm) để khách so sánh. Chụp màn hình tổng giá trị + đơn giá/m&#178; cho khách dễ nhìn.'],
                      ['<b>Bước 2 &mdash; Khai thác vấn đề</b>', 'Nhắn dò &rarr; GỌI (ít nhưng hiệu quả) để moi TÂM LÝ thật. Đủ 5 nhóm: Báo giá &mdash; Mẫu nhà &mdash; Gia đình &mdash; Khởi công &mdash; Niềm tin (cốt lõi BÁO GIÁ + TÀI CHÍNH). Mọi cuộc gọi nhắc THI CÔNG GẤP; bản thân khách OK trước thì gia đình mới OK.'],
                      ['<b>Bước 3 &mdash; Gửi hợp đồng</b>', 'Khách có ít nhất 2&ndash;3 phản hồi về báo giá + đã OK với tầm tài chính &rarr; CHỦ ĐỘNG gửi HỢP ĐỒNG MẪU để có lý do hẹn ký. Không chần chừ.'],
                      ['<b>Bước 4 &mdash; Phản hồi hợp đồng</b>', 'Dò 6 điểm: Phụ lục vật tư (KHẲNG ĐỊNH tốt) &mdash; Đợt ứng &mdash; Tiền bảo hành &mdash; Thời gian bảo hành &mdash; Tiến độ &mdash; Khác.'],
                      ['<b>Bước 5 &mdash; Hẹn &amp; ký (CHỐT)</b>', 'Hết khúc mắc HĐ + chốt cọc 50tr (tiền mặt) + giọng TỰ TIN, MẠNH, CHẮC, KHẲNG ĐỊNH. Hẹn tốt = 10 ký 9.']],
                     widths=['26%', '74%'])
            + _box('warn', 'Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi lần '
                   'tương tác đều phải có mục tiêu rõ ràng và đưa khách tiến gần hơn tới '
                   'quyết định ký.')
            + _quiz('qz_tuduy',
                    'Sau khi gửi báo giá 24h mà khách chưa phản hồi, hành động nào chuyên nghiệp nhất?',
                    [('Gọi điện giục khách ký hợp đồng ngay', False),
                     ('Nhắn/gọi hỏi thăm khách đã nhận báo giá chưa và có cần giải thích thêm không', True),
                     ('Tiếp tục im lặng chờ thêm 1 tuần', False),
                     ('Xóa khách khỏi danh sách theo dõi', False)],
                    'Chủ động quan tâm để hiểu khách nghĩ gì &mdash; không ép, không bỏ mặc.')
            + _quiz('qz_gold',
                    'Theo nguyên tắc vàng, nhân viên kinh doanh GIỎI là người thế nào?',
                    [('Người gửi được nhiều báo giá nhất trong tháng', False),
                     ('Người biết dẫn dắt khách qua từng bước tới quyết định ký', True),
                     ('Người có giá chào thấp nhất cho khách', False),
                     ('Người gọi cho khách nhiều lần nhất trong ngày', False)],
                    'Giỏi = dẫn dắt khách tiến từng bước tới ký, không phải gửi thật nhiều báo giá.'))

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (bài THI chấm điểm)
    # ==================================================================
    def _vd_tdbg_questions(self):
        T, F = True, False
        return [
            ('Tư duy nền tảng: sau khi gửi báo giá cho khách thì?',
             [('Đó mới là BẮT ĐẦU - việc theo đuổi khách thật sự bắt đầu từ đây', T),
              ('Đó là kết thúc, ngồi chờ khách gọi lại', F),
              ('Xóa khách khỏi danh sách nếu 1 ngày chưa phản hồi', F),
              ('Chỉ cần so sánh giá với đối thủ là đủ', F)]),

            ('Sau khi gửi báo giá 24h mà khách chưa phản hồi, hành động nào chuyên nghiệp nhất?',
             [('Nhắn/gọi hỏi thăm khách đã nhận báo giá chưa và có cần giải thích thêm không', T),
              ('Gọi điện giục khách ký hợp đồng ngay', F),
              ('Tiếp tục im lặng chờ thêm 1 tuần', F),
              ('Bỏ mặc, coi như khách không quan tâm', F)]),

            ('Bước 1 - CÔNG THỨC cốt lõi của "tự tin báo giá" là gì?',
             [('Nhân viên thực sự tự tin báo giá là phương án ưng ý nhất và KHỚP tầm tài chính của khách', T),
              ('Báo giá càng cao càng thể hiện đẳng cấp', F),
              ('Gửi thật nhanh, không cần cân đối tài chính', F),
              ('Báo giá thấp nhất thị trường để chắc thắng', F)]),

            ('Bước 1 - báo giá chênh TRÊN 100 triệu so với tầm tài chính khách thì phải làm gì?',
             [('Bàn bạc lại với khách để điều chỉnh, cân đối tài chính cho phù hợp rồi mới quyết định gửi', T),
              ('Cứ gửi luôn con số cao, không cần bàn bạc', F),
              ('Hủy khách ngay lập tức', F),
              ('Chờ khách tự liên hệ lại', F)]),

            ('Bước 1 - báo giá chênh khoảng 100-300 triệu thì cách xử lý ĐÚNG là?',
             [('Trao đổi giảm diện tích cho khớp HOẶC xác định khách cố thêm được tài chính (vay/mượn/xoay), rồi vẫn cố gắng gửi báo giá', T),
              ('Không gửi báo giá vì chênh quá nhiều', F),
              ('Lưỡng lự chờ 2-3 ngày rồi mới quyết', F),
              ('Tự giảm giá trị báo giá cho bằng tài chính khách mà không đổi diện tích', F)]),

            ('Bước 1 - chiến lược công ty về THỜI ĐIỂM gửi báo giá là gì?',
             [('Cố gắng tối đa gửi báo giá ngay trong NGÀY ĐẦU, cùng ngày gọi điện tư vấn', T),
              ('Gửi sau 1 tuần cho khách sốt ruột', F),
              ('Chỉ gửi khi khách chốt xong mẫu nhà', F),
              ('Gửi bất cứ khi nào rảnh, không quan trọng', F)]),

            ('Bước 1 - vì sao VẪN phải gửi báo giá dù chưa thuyết phục được tầm tài chính ban đầu (chênh 200-300tr)?',
             [('Để khách có cơ hội nhìn thấy báo giá, danh mục vật tư, hình ảnh - có cơ sở để so sánh, cân nhắc, tính toán', T),
              ('Để ép khách phải ký ngay', F),
              ('Vì công ty phạt nếu không gửi', F),
              ('Không cần lý do, cứ gửi cho xong', F)]),

            ('Bước 1 - trường hợp nào CÓ THỂ không gửi báo giá?',
             [('Chênh lệch quá lớn không xoay được, ví dụ khách muốn xây 1 tỷ nhưng chỉ có 600 triệu và không có cách kiếm thêm', T),
              ('Bất cứ khi nào báo giá cao hơn mong muốn khách', F),
              ('Khi khách chưa chọn được mẫu nhà', F),
              ('Khi chênh khoảng 100-200 triệu', F)]),

            ('Bước 1 - một báo giá được coi là CHUẨN khi nào?',
             [('Đúng tài chính + đúng nhu cầu + đúng mong muốn của khách', T),
              ('Có tổng giá trị cao nhất có thể', F),
              ('Gửi trước đối thủ', F),
              ('Trình bày nhiều màu sắc, đẹp mắt', F)]),

            ('Bước 2 - khi khai thác phản hồi báo giá, cách hỏi nào ĐÚNG nhất?',
             [('Hỏi cụ thể: đã xem kỹ báo giá + phụ lục chưa, băn khoăn gì, mức đầu tư có phù hợp, muốn điều chỉnh gì', T),
              ('Hỏi chung chung "anh xem chưa ạ?" rồi thôi', F),
              ('Hỏi "anh chị ký chưa ạ?" để chốt nhanh', F),
              ('Không hỏi, chờ khách tự nhắn lại', F)]),

            ('Sau khi gửi báo giá bao lâu thì BẮT BUỘC phải lấy phản hồi từ khách?',
             [('Sau 1-2 ngày', T),
              ('Sau 1-2 tuần', F),
              ('Chỉ khi khách chủ động nhắn lại', F),
              ('Sau đúng 1 tháng', F)]),

            ('Bước 2 - 1-2 ngày sau khi gửi báo giá, khách nhắn hỏi một câu nhỏ về phụ lục vật tư. Nghĩa là gì?',
             [('Tín hiệu khách RẤT tiềm năng - phải trả lời nhanh và bám đuổi ngay', T),
              ('Khách chỉ hỏi cho có, không cần quan tâm', F),
              ('Khách đang làm khó, nên né trả lời', F),
              ('Chờ gom nhiều câu hỏi rồi trả lời một lần', F)]),

            ('Bước 2 - vì sao trong mọi cuộc gọi phải nhắc khách ký sớm (thi công gấp) nếu muốn ở nhà mới trước Tết?',
             [('Vì thiết kế mất 1-2 tháng, còn chuẩn bị thợ, vật tư, dự toán, nhân lực, rồi nội thất/sân vườn - không kịp bàn giao', T),
              ('Vì giá sẽ tăng gấp đôi nếu ký muộn', F),
              ('Vì công ty sắp hết suất nhận công trình', F),
              ('Vì khách phải khởi công ngay trong tuần', F)]),

            ('Bước 2 - nguyên tắc gọi điện khi khai thác, và khách nói "anh đang xem" nghĩa là gì?',
             [('Gọi ÍT nhưng HIỆU QUẢ (1 cuộc phải khai thác ra vấn đề); khách "đang xem" = đã xem nhưng trì hoãn nên phải gọi ngay', T),
              ('Gọi thật nhiều cuộc cho tới khi khách chốt', F),
              ('Khách "đang xem" thì cứ chờ thêm vài ngày', F),
              ('Đáp "vâng anh xem đi" rồi tắt máy', F)]),

            ('Bước 2 - nhóm câu hỏi nào giúp phát hiện RÀO CẢN THẬT SỰ trước khi ký?',
             [('Nhóm Niềm tin: "Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?"', T),
              ('Nhóm Báo giá: "Có vượt tài chính không?"', F),
              ('Nhóm Mẫu nhà: "Đã đúng phong cách chưa?"', F),
              ('Nhóm Khởi công: "Dự kiến khi nào?"', F)]),

            ('Bước 2 - sai lầm nguy hiểm khi khai thác khúc mắc chưa đủ là gì?',
             [('Bỏ sót nhóm Gia đình/Niềm tin → thuyết phục sai người hoặc khách lăn tăn ngầm rồi bỏ đi, mất khách không rõ lý do', T),
              ('Hỏi kỹ cả 5 nhóm câu hỏi', F),
              ('Luôn kết thúc bằng câu hỏi niềm tin', F),
              ('Ghi lại khúc mắc để xử lý dứt điểm', F)]),

            ('Bước 3 - khi nào nên CHỦ ĐỘNG gửi hợp đồng cho khách?',
             [('Khi thấy khách để ý/có vài phản hồi về báo giá + thời gian khởi công gấp → gửi để có lý do hẹn ký, không chần chừ', T),
              ('Chờ đến khi khách tự hỏi về hợp đồng', F),
              ('Chỉ gửi khi khách đã đồng ý mọi thứ bằng văn bản', F),
              ('Không bao giờ gửi trước khi khách yêu cầu', F)]),

            ('Bước 4 - khi gửi hợp đồng, khách thắc mắc NHIỀU NHẤT về điều gì và nhân viên phải làm gì?',
             [('Về phụ lục vật tư - phải KHẲNG ĐỊNH đây là vật tư tốt trên thị trường', T),
              ('Về màu sắc bản vẽ - đổi lại cho khách', F),
              ('Về tên công ty - kể lịch sử công ty', F),
              ('Không cần quan tâm, chờ khách ký', F)]),

            ('Bước 5 - nguyên tắc quan trọng nhất về CÁCH NÓI khi hẹn ký là gì?',
             [('Giọng tự tin, nói mạnh, nói chắc, khẳng định - không rụt rè', T),
              ('Nói nhẹ nhàng, rào trước đón sau', F),
              ('Nói thật nhanh cho xong', F),
              ('Để khách nói là chính, mình chỉ nghe', F)]),

            ('Bước 5 - vì sao phải trao đổi trước về việc đặt cọc 50 triệu (ưu tiên tiền mặt)?',
             [('Vì nếu không thỏa thuận trước, khi về ký khách hay lấy lý do chưa chuẩn bị tiền; đề cập cọc giúp khách có tâm lý chuẩn bị ký cao hơn', T),
              ('Vì công ty cần tiền gấp', F),
              ('Vì để thử xem khách có tiền không', F),
              ('Vì đặt cọc là thủ tục không quan trọng', F)]),

            ('Bước 1 - khách NHẤT QUYẾT giữ diện tích lớn mà tài chính vẫn thiếu 100-300 triệu, cách xử lý chuyên nghiệp nhất là?',
             [('Làm 2 báo giá: một theo đúng diện tích khách yêu cầu + một chủ động cắt giảm diện tích cho phù hợp, gửi CÙNG LÚC để khách so sánh', T),
              ('Chỉ gửi báo giá theo diện tích lớn khách yêu cầu', F),
              ('Từ chối làm báo giá vì khách không nghe', F),
              ('Tự ý cắt diện tích rồi chỉ gửi mỗi bản đã cắt', F)]),

            ('Bước 1 - vì sao khi làm 2 báo giá phải GỬI CẢ HAI CÙNG MỘT THỜI ĐIỂM?',
             [('Để khách đặt 2 mức tổng tiền cạnh nhau so sánh; nếu chỉ gửi bản diện tích lớn giá cao thì khách sẽ nản và trôi mất', T),
              ('Để khách rối trí không kịp so sánh', F),
              ('Vì công ty quy định luôn phải gửi 2 file', F),
              ('Để có cớ tính thêm phí thiết kế', F)]),

            ('Bước 1 - khi gửi báo giá bản diện tích đã CẮT GIẢM, câu khẳng định bắt buộc phải nói với khách là gì?',
             [('"Với diện tích cắt giảm này bên em vẫn thiết kế ĐỦ công năng và ĐỦ số phòng ngủ như anh/chị mong muốn"', T),
              ('"Diện tích nhỏ thì đành chấp nhận thiếu phòng ạ"', F),
              ('"Anh/chị tự cân nhắc, em không đảm bảo được"', F),
              ('Không cần nói thêm gì, cứ gửi là được', F)]),

            ('Bước 1 - nguyên tắc CHỤP MÀN HÌNH báo giá là gì?',
             [('Chụp màn hình bảng báo giá, nhất là tổng giá trị hợp đồng và đơn giá theo m2, gửi cho khách dễ nhìn', T),
              ('Chỉ gửi file PDF, tuyệt đối không chụp gì', F),
              ('Chụp màn hình để gửi khoe cho khách khác', F),
              ('Không nên cho khách thấy tổng giá trị hợp đồng', F)]),

            ('Bước 1 - khi khách mang báo giá đi so sánh với đơn vị khác, tư duy ĐÚNG của nhân viên là?',
             [('Đó là chuyện bình thường; muốn được so sánh thì PHẢI gửi báo giá, rồi chủ động chứng minh mình là lựa chọn hợp lý nhất', T),
              ('Giấu báo giá để khách không đem đi so sánh được', F),
              ('Nói xấu đối thủ để khách sợ không dám so sánh', F),
              ('Không gửi báo giá nữa vì sợ bị so sánh', F)]),

            ('Bước 3 - dấu hiệu ĐỦ ĐIỀU KIỆN để chủ động gửi HỢP ĐỒNG MẪU cho khách là gì?',
             [('Khách đã có ít nhất 2-3 phản hồi về báo giá và đã OK với tầm tài chính của báo giá đó', T),
              ('Khách chưa phản hồi lần nào về báo giá', F),
              ('Khách mới chỉ vừa nhận được file báo giá', F),
              ('Phải chờ đến khi khách tự yêu cầu hợp đồng', F)]),

            ('Bước 2 - 5 NHÓM khúc mắc bắt buộc phải khai thác gồm những gì?',
             [('Báo giá - Mẫu nhà - Gia đình - Khởi công - Niềm tin', T),
              ('Báo giá - Màu sơn - Nội thất - Phong thủy - Hàng xóm', F),
              ('Chỉ cần hỏi về giá là đủ', F),
              ('Tên công ty - Lịch sử - Giải thưởng - Quy mô - Địa chỉ', F)]),

            ('Bước 4 - điểm nào sau đây KHÔNG nằm trong "6 điểm" cần dò khi lấy phản hồi hợp đồng?',
             [('Màu sắc bản vẽ', T),
              ('Phụ lục vật tư', F),
              ('Các đợt ứng (tiến độ thanh toán)', F),
              ('Tiến độ thi công', F)]),

            ('Tổng kết - sau MỖI lần liên hệ với khách, mục tiêu tối thiểu phải đạt được là gì?',
             [('Đưa khách tiến thêm ÍT NHẤT 1 bước tới quyết định ký', T),
              ('Chỉ cần chào hỏi cho khách nhớ mặt là được', F),
              ('Nhắc đi nhắc lại rằng giá mình rẻ hơn đối thủ', F),
              ('Không cần mục tiêu, gọi cho vui vẻ là chính', F)]),
        ]
