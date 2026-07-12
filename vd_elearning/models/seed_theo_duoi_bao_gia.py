# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
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

_TDBG_VERSION = 'v9-deep'
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
    '.vd-tdbg .thok{background:#dcfce7;color:#15803d;}'
    '.vd-tdbg .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-tdbg .no{color:#b91c1c;font-weight:700;}'
    '.vd-tdbg .navr,.vd-tdbg .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-tdbg .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-tdbg .vc-side{flex:0 0 264px;}'
    '.vd-tdbg .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-tdbg .vc-navbtn{display:block;padding:12px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14.5px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;text-align:center;}'
    '.vd-tdbg .vc-navbtn:hover{background:#fff5f1;border-color:#ffd9c9;color:#e8401f;}'
    '.vd-tdbg .vc-nbadge{display:inline-block;background:#fff1ec;color:#e8401f;font-size:11px;'
    'font-weight:800;letter-spacing:1.5px;padding:3px 12px;border-radius:20px;margin-bottom:7px;}'
    '.vd-tdbg .vc-ntitle{display:block;font-weight:700;line-height:1.3;}'
    '.vd-tdbg .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-tdbg .vc-panel{display:none;}'
    '.vd-tdbg .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#e8401f;background:#fff1ec;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-tdbg .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:12px 0;}'
    '.vd-tdbg .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-tdbg .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-tdbg .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-tdbg .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # công thức
    '.vd-tdbg .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:14px 0;}'
    '.vd-tdbg .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-tdbg .fml .fml-b{color:#4c1d95;font-weight:600;}'
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
            ('&#129504;', 'MỞ ĐẦU', 'Tư duy &amp; Sai lầm cần tránh', self._l_tuduy()),
            ('&#128101;', 'GIAI ĐOẠN 0', 'Quy tắc tạo nhóm', self._l_taonhom()),
            ('&#9989;', 'BƯỚC 1', 'Kiểm tra báo giá', self._l_b1()),
            ('&#128222;', 'BƯỚC 2', 'Lấy phản hồi báo giá', self._l_b2()),
            ('&#127919;', 'BƯỚC 3', 'Tín hiệu tiềm năng &rarr; Bám đuổi', self._l_b3()),
            ('&#9200;', 'BƯỚC 4', 'Thời gian khởi công', self._l_b4()),
            ('&#128269;', 'BƯỚC 5', 'Khai thác &amp; xử lý khúc mắc', self._l_b5()),
            ('&#128196;', 'BƯỚC 6', 'Gửi hợp đồng', self._l_b6()),
            ('&#128064;', 'BƯỚC 7', 'Lấy phản hồi hợp đồng', self._l_b7()),
            ('&#9997;&#65039;', 'BƯỚC 8', 'Hẹn khảo sát &amp; ký (chốt)', self._l_b8()),
            ('&#127942;', 'TỔNG KẾT', 'Nguyên tắc vàng', self._l_gold()),
        ]

    # ------------------------------------------------------------------
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
            + _nendont(
                ['Chủ động nhắc &amp; đồng hành cùng khách sau báo giá',
                 'Bán GIẢI PHÁP phù hợp gia đình khách, không chỉ bán giá',
                 'Mỗi lần liên hệ đưa khách tiến thêm 1 bước'],
                ['Gửi xong rồi ngồi chờ khách gọi lại',
                 'Chỉ chăm chăm so sánh con số tiền với đối thủ',
                 'Để khách &#8220;treo&#8221;, im lặng quá lâu'])
            + _fml('Sau báo giá: <b>Báo giá &rarr; Phản hồi &rarr; Hiểu suy nghĩ &rarr; '
                   'Gỡ khúc mắc &rarr; Gửi hợp đồng &rarr; Gỡ khúc mắc HĐ &rarr; Hẹn ký</b>. '
                   'Khách im lặng = quy trình đang DỪNG lại.')
            + _quiz('qz_tuduy',
                    'Sau khi gửi báo giá 24h mà khách chưa phản hồi, hành động nào chuyên nghiệp nhất?',
                    [('Gọi điện giục khách ký hợp đồng ngay', False),
                     ('Nhắn/gọi hỏi thăm khách đã nhận báo giá chưa và có cần giải thích thêm không', True),
                     ('Tiếp tục im lặng chờ thêm 1 tuần', False)],
                    'Chủ động quan tâm để hiểu khách nghĩ gì &mdash; không ép, không bỏ mặc.'))

    # ------------------------------------------------------------------
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
            + '<h4>Tạo nhóm thế nào?</h4>'
            + '<p>Nhóm gồm tối thiểu <b>bản thân + khách hàng + trưởng phòng</b>. Ngay '
            'sau khi tạo: <b>đổi ảnh đại diện = logo công ty</b> + <b>đổi tên nhóm '
            'theo quy tắc quy định</b>.</p>'
            + '<h4>&#128204; THỨ TỰ GỬI TIN NHẮN ZALO (thuộc lòng &mdash; gửi ĐÚNG thứ tự)</h4>'
            + _order([
                ('4 VIDEO VTV', 'Nội dung PHẢI gửi ĐẦU TIÊN &mdash; tạo uy tín, khẳng định thương hiệu ngay từ đầu.'),
                ('LỜI CHÀO &amp; GIỚI THIỆU BẢN THÂN', 'Giới thiệu mình là người đồng hành, tạo thiện cảm.'),
                ('TỔNG HỢP NHU CẦU &amp; CÔNG NĂNG KHÁCH', 'Chốt lại đúng những gì khách muốn &mdash; cho khách thấy mình đã lắng nghe kỹ.'),
                ('TỐI THIỂU 20 MẪU NHÀ', 'Cho khách thêm ý tưởng, nhiều lựa chọn, tự xác định sở thích &mdash; KHÔNG ép khách chốt mẫu.'),
                ('SAU ĐÓ MỚI NHẮN TIN BÌNH THƯỜNG', 'Đủ 4 nội dung trên mới trao đổi tiếp &mdash; và luôn trao đổi TRÊN NHÓM.'),
            ])
            + _box('info', '<b>Về mẫu nhà:</b> khách KHÔNG mua mẫu nhà &mdash; khách mua '
                   'giải pháp phù hợp với gia đình. Gửi mẫu để khách có ý tưởng và bộc '
                   'lộ sở thích.')
            + _nendont(
                ['Gửi đủ &amp; đúng thứ tự 4 nội dung rồi mới trao đổi',
                 'Gửi tối thiểu 20 mẫu để khách có nhiều lựa chọn',
                 'Luôn phản hồi trên NHÓM'],
                ['Nhảy cóc, gửi mẫu nhà trước cả video VTV',
                 'Ép khách &#8220;chọn giúp em 1 mẫu&#8221;',
                 'Trả lời khách ở Zalo cá nhân'])
            + _fml('Chốt báo giá &rarr; Tạo nhóm (mình + khách + trưởng phòng) &rarr; '
                   'Đổi ảnh (logo) + đổi tên &rarr; <b>VTV &rarr; Giới thiệu &rarr; Nhu '
                   'cầu &rarr; 20 mẫu nhà</b> &rarr; rồi mới nhắn tin.')
            + _quiz('qz_nhom',
                    'Sau khi tạo nhóm, nội dung phải gửi ĐẦU TIÊN theo đúng thứ tự là gì?',
                    [('4 video VTV', True),
                     ('Lời chào giới thiệu bản thân', False),
                     ('Gửi ngay 20 mẫu nhà', False),
                     ('Bảng báo giá chi tiết', False)],
                    'Thứ tự: 4 video VTV &rarr; giới thiệu &rarr; tổng hợp nhu cầu &rarr; 20 mẫu nhà.'))

    # ------------------------------------------------------------------
    def _l_b1(self):
        return (
            self._tag('BƯỚC 1')
            + '<h3>Kiểm tra chất lượng báo giá trước khi gửi</h3>'
            + _box('warn', 'Đừng gửi kiểu &#8220;Em gửi anh/chị tham khảo nhé&#8221;. '
                   'Nếu chính nhân viên còn không tự tin thì khách càng không tin.')
            + '<h4>Tự trả lời 3 câu trước khi bấm gửi</h4>'
            + _table(['Câu tự kiểm', 'Kiểm tra điều gì', 'Nếu CHƯA đạt'],
                     [['<b>1. Đúng nhu cầu khách?</b>', 'Tài chính, phong cách, mục đích xây có khớp không', 'Chưa gửi &mdash; hỏi lại nhu cầu, sửa cho khớp'],
                      ['<b>2. Giải quyết tài chính?</b>', 'Có vượt ngân sách? có phương án tối ưu/giảm chi phí? có giải thích rõ vì sao ra số tiền?', 'Cân đối lại phương án rồi mới gửi'],
                      ['<b>3. Đúng mong muốn?</b>', 'Số tầng, phòng, phong cách, mức hoàn thiện, thang máy, gara, sân', 'Sửa cho tất cả KHỚP']],
                     widths=['22%', '52%', '26%'])
            + _table(['Khách muốn', 'Nếu gửi lệch', 'Kết quả'],
                     [['Tài chính ~2,8 tỷ', 'Gửi báo giá 3,8 tỷ', '<span class="no">SAI</span>'],
                      ['Thích hiện đại', 'Báo giá mẫu tân cổ', '<span class="no">SAI</span>'],
                      ['Xây để ở', 'Làm theo tiêu chuẩn đầu tư', '<span class="no">SAI</span>']],
                     widths=['34%', '40%', '26%'])
            + _nendont(
                ['Cân đối cho khớp tầm tài chính rồi mới gửi',
                 'Giải thích rõ được vì sao ra con số đó',
                 'Tự tin: "mình là khách cũng thấy hợp lý"'],
                ['Gửi báo giá vượt xa ngân sách khách',
                 'Gửi kèm câu "anh/chị tham khảo nhé"',
                 'Gửi khi chính mình còn chưa chắc'])
            + _fml('Báo giá CHUẨN = <b>Đúng tài chính + Đúng nhu cầu + Đúng mong muốn</b>. '
                   'Lệch 1 trong 3 &rarr; CHƯA gửi.')
            + _quiz('qz_b1',
                    'Khách nói tài chính ~2,8 tỷ, báo giá bạn tính ra 3,8 tỷ. Nên làm gì?',
                    [('Cứ gửi 3,8 tỷ, báo cao để còn thương lượng giảm', False),
                     ('Gửi 3,8 tỷ kèm câu &#8220;anh/chị tham khảo nhé&#8221;', False),
                     ('Cân đối lại phương án diện tích/công năng cho khớp tầm 2,8 tỷ rồi mới gửi', True),
                     ('Gửi luôn để khách thấy đẳng cấp', False)],
                    'Báo giá lệch tầm tài chính là vô tác dụng &mdash; phải cân đối cho khớp.'))

    # ------------------------------------------------------------------
    def _l_b2(self):
        return (
            self._tag('BƯỚC 2')
            + '<h3>Lấy phản hồi báo giá (sau 1&ndash;2 ngày)</h3>'
            + _box('err', 'Sai lầm lớn nhất: gửi báo giá xong rồi <b>im luôn</b> &mdash; '
                   'không gọi, không nhắn, không hỏi.')
            + '<p>Mục tiêu KHÔNG phải gọi để ép ký, mà để <b>BIẾT khách đang nghĩ gì</b>. '
            'Muốn vậy phải hỏi <b>đúng và cụ thể</b> từng ý &mdash; không hỏi chung chung '
            'kiểu &#8220;anh xem chưa ạ?&#8221; rồi thôi.</p>'
            + '<h4>4 ý BẮT BUỘC phải khai thác được</h4>'
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
            + '<h4>Khách im lặng KHÔNG có nghĩa là hết quan tâm</h4>'
            + '<p>Có thể vì: báo giá cao hơn dự kiến &middot; chưa đúng nhu cầu &middot; '
            'chưa hiểu cách tính &middot; đang chờ đơn vị khác &middot; chưa đủ niềm '
            'tin &middot; chưa biết nên hỏi gì.</p>'
            + _nendont(
                ['Hỏi cụ thể từng ý (xem kỹ chưa, băn khoăn gì, tài chính, điều chỉnh)',
                 'Coi im lặng là tín hiệu cần TÌM HIỂU',
                 'Ghi lại phản hồi để dẫn sang bước sau'],
                ['Hỏi chung chung "anh xem chưa ạ?" rồi thôi',
                 'Đoán mò lý do khách im',
                 'Gọi để ép ký ngay'])
            + _fml('Việc của nhân viên là <b>KHAI THÁC, không phải ĐOÁN</b>. Hỏi đủ 4 ý: '
                   '<b>Đã xem kỹ? &mdash; Băn khoăn gì? &mdash; Tài chính hợp không? &mdash; Muốn chỉnh gì?</b>')
            + _quiz('qz_b2',
                    'Gọi lấy phản hồi báo giá, cách hỏi nào ĐÚNG nhất?',
                    [('&#8220;Anh xem báo giá chưa ạ?&#8221; rồi dừng', False),
                     ('Hỏi cụ thể: đã xem kỹ báo giá + phụ lục chưa, phần nào băn khoăn, mức đầu tư có phù hợp, muốn điều chỉnh gì', True),
                     ('&#8220;Anh chị ký chưa ạ?&#8221;', False),
                     ('Không hỏi, chờ khách tự nhắn', False)],
                    'Phải hỏi cụ thể từng ý để hiểu khách nghĩ gì, không hỏi chung chung.'))

    # ------------------------------------------------------------------
    def _l_b3(self):
        return (
            self._tag('BƯỚC 3 &mdash; NHẬN DIỆN TÍN HIỆU')
            + '<h3>Khách tương tác = tín hiệu tiềm năng &rarr; BÁM ĐUỔI</h3>'
            + _box('ok', 'Sau khi gửi báo giá 1&ndash;2 ngày, nếu khách có BẤT KỲ tương '
                   'tác nào &mdash; hỏi về giá, về phụ lục vật tư, hay một câu hỏi rất '
                   'nhỏ &mdash; thì đó là <b>tín hiệu khách RẤT tiềm năng</b>.')
            + '<p><b>Vì sao?</b> Khách chịu hỏi tức là khách <b>đã đọc</b>, <b>đã suy '
            'nghĩ</b> và <b>đang quan tâm</b>. Câu hỏi dù nhỏ cũng là cánh cửa mở &mdash; '
            'đừng bao giờ coi nhẹ.</p>'
            + _box('err', '<b>Cần tránh:</b> trả lời qua loa cho xong rồi để nguội. Một '
                   'câu hỏi nhỏ bị bỏ lỡ = một khách tiềm năng trôi mất.')
            + '<h4>Khách hỏi thì phải làm gì?</h4>'
            + _nendont(
                ['Trả lời NHANH, nhiệt tình, rõ ràng',
                 'Dùng chính câu hỏi đó làm cầu nối khai thác thêm',
                 'Chủ động đẩy khách sang bước tiếp (hẹn gọi, gửi thêm thông tin)',
                 'Xếp khách này vào diện ƯU TIÊN bám đuổi'],
                ['Trả lời cụt lủn rồi im',
                 'Để câu hỏi &#8220;treo&#8221; vài ngày mới trả lời',
                 'Coi câu hỏi nhỏ là không quan trọng'])
            + _fml('<b>Khách HỎI = Khách QUAN TÂM &rarr; BÁM ĐUỔI NGAY.</b> Tương tác '
                   'càng sớm, tín hiệu càng mạnh.')
            + _quiz('qz_b3',
                    '2 ngày sau khi gửi báo giá, khách nhắn hỏi một câu nhỏ về phụ lục vật tư. Điều này nghĩa là gì?',
                    [('Khách chỉ hỏi cho có, không cần quan tâm nhiều', False),
                     ('Tín hiệu khách RẤT tiềm năng &mdash; phải trả lời nhanh và bám đuổi ngay', True),
                     ('Khách đang làm khó, nên né trả lời', False),
                     ('Chờ gom nhiều câu hỏi rồi trả lời một lần', False)],
                    'Khách chịu hỏi là đã đọc và đang quan tâm &mdash; đây là lúc phải bám đuổi.'))

    # ------------------------------------------------------------------
    def _l_b4(self):
        return (
            self._tag('BƯỚC 4')
            + '<h3>Tạo cảm giác cần quyết định về thời gian khởi công</h3>'
            + '<p>Đặc biệt cuối năm, khách nào cũng muốn <b>xây xong, bàn giao trước '
            'Tết</b>. Nhưng nếu KHÔNG ký hợp đồng sớm thì <b>không kịp</b> &mdash; và '
            'đây là những lý do CÓ THẬT cần cho khách hiểu:</p>'
            + _table(['Việc cần thời gian', 'Vì sao ảnh hưởng tiến độ'],
                     [['<b>Thiết kế bản vẽ</b>', 'Mất tối thiểu 1 tháng; khách duyệt bản vẽ chậm có khi mất tới 2 tháng.'],
                      ['<b>Chuẩn bị thợ</b>', 'Nếu 2 bên không thỏa thuận sớm thì không bố trí, chuẩn bị thợ kịp.'],
                      ['<b>Các phòng ban chuẩn bị</b>', 'Phòng vật tư, phòng kế hoạch, phòng dự toán, phòng nhân lực &mdash; tất cả đều cần thời gian.'],
                      ['<b>Hoàn thiện cuối</b>', 'Nội thất, dọn dẹp, sân vườn (nếu có) &mdash; không bố trí sớm thì không kịp Tết.']],
                     widths=['30%', '70%'])
            + _box('info', '<b>Câu mẫu:</b> &#8220;Nếu gia đình muốn ở nhà mới trước '
                   'Tết thì mình nên chốt sớm ạ. Vì riêng thiết kế đã mất khoảng 1&ndash;2 '
                   'tháng, rồi còn chuẩn bị thợ, vật tư, dự toán, nhân lực; sát cuối năm '
                   'thì nội thất, sân vườn, dọn dẹp sẽ rất gấp.&#8221;')
            + _nendont(
                ['Cho khách thấy rõ chuỗi thời gian: thiết kế &rarr; thợ &rarr; thi công &rarr; hoàn thiện',
                 'Nhắc bằng thiện chí, giúp khách chủ động',
                 'Gắn quyết định của khách với mốc &#8220;trước Tết&#8221;'],
                ['Dọa &#8220;không ký là giá tăng gấp đôi&#8221;',
                 'Nói &#8220;sắp hết suất&#8221; kiểu ép buộc',
                 'Bắt khách khởi công ngay tuần này'])
            + _fml('Không ký sớm = KHÔNG kịp bàn giao trước Tết. Chuỗi: <b>Thiết kế '
                   '(1&ndash;2 tháng) + Chuẩn bị thợ + 4 phòng ban + Hoàn thiện (nội '
                   'thất/sân vườn/dọn dẹp)</b>. Mục tiêu: giúp khách HIỂU hệ quả, không '
                   'gây áp lực vô lý.')
            + _quiz('qz_b4',
                    'Vì sao phải nhắc khách ký sớm nếu muốn ở nhà mới trước Tết?',
                    [('Vì giá sẽ tăng gấp đôi nếu ký muộn', False),
                     ('Vì thiết kế mất 1&ndash;2 tháng, còn phải chuẩn bị thợ, vật tư, dự toán, nhân lực, rồi nội thất/sân vườn &mdash; không kịp bàn giao', True),
                     ('Vì công ty sắp hết suất nhận công trình', False),
                     ('Vì khách phải khởi công ngay trong tuần', False)],
                    'Cho khách hiểu chuỗi thời gian thật để chủ động quyết định &mdash; không dọa dẫm.'))

    # ------------------------------------------------------------------
    def _l_b5(self):
        return (
            self._tag('BƯỚC 5 &mdash; QUAN TRỌNG NHẤT')
            + '<h3>Khai thác &amp; xử lý khúc mắc</h3>'
            + _box('warn', 'Khách chưa ký thì chắc chắn còn vấn đề &mdash; nhân viên '
                   'phải TÌM RA, không được tự suy đoán.')
            + '<p>Mỗi nhóm câu hỏi khai thác một loại rào cản khác nhau. Phải hiểu '
            '<b>vì sao</b> khai thác thì mới hỏi trúng:</p>'
            + _table(['Nhóm khai thác', 'Hỏi gì', 'Vì sao QUAN TRỌNG'],
                     [['<b>1. Báo giá</b>', 'Có phù hợp? Có vượt tài chính? Cần điều chỉnh?',
                       'Tài chính là rào cản số 1 &mdash; lệch tiền là khách bỏ.'],
                      ['<b>2. Mẫu nhà</b>', 'Đã đúng phong cách chưa? Muốn tham khảo thêm?',
                       'Khách chưa ưng &#8220;hình hài&#8221; ngôi nhà thì chưa quyết.'],
                      ['<b>3. Gia đình</b>', 'Đã thống nhất chưa? AI là người quyết định? Cần bàn thêm với người thân?',
                       'Rất nhiều ca đổ vỡ vì mình thuyết phục sai người &mdash; người quyết thật chưa gật.'],
                      ['<b>4. Khởi công</b>', 'Dự kiến khi nào? Đang chờ việc gì? Vướng thủ tục?',
                       'Biết mốc thời gian để tạo lý do thúc tiến độ (Bước 4).'],
                      ['<b>5. Niềm tin</b>', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?',
                       'Lộ ra RÀO CẢN THẬT SỰ còn ẩn giấu &mdash; thứ đang chặn khách ký.']],
                     widths=['16%', '42%', '42%'])
            + _box('err', '<b>Sai lầm khi KHÔNG khai thác đủ:</b>')
            + '<ul>'
            '<li>Bỏ sót nhóm <b>Gia đình</b> &rarr; thuyết phục mãi một người trong khi '
            'người quyết định thật chưa đồng ý &rarr; công cốc.</li>'
            '<li>Bỏ qua nhóm <b>Niềm tin</b> &rarr; khách vẫn lăn tăn ngầm rồi im lặng '
            'bỏ đi &mdash; mình <b>mất khách mà không rõ lý do</b>.</li>'
            '<li>Chỉ hỏi <b>giá</b> mà quên các nhóm còn lại &rarr; xử lý sai trọng tâm, '
            'khách thấy mình không hiểu nhu cầu.</li>'
            '<li><b>Đoán mò</b> thay vì hỏi &rarr; xử lý nhầm vấn đề, càng làm khách xa.</li>'
            '</ul>'
            + _fml('Khai thác đủ <b>5 nhóm: Báo giá &mdash; Mẫu nhà &mdash; Gia đình '
                   '&mdash; Khởi công &mdash; Niềm tin</b>. LUÔN kết bằng câu hỏi NIỀM '
                   'TIN. Chưa ký = còn khúc mắc, phải TÌM RA rồi XỬ LÝ dứt điểm.')
            + _quiz('qz_b5',
                    'Đâu là sai lầm nguy hiểm khi khai thác khúc mắc chưa đủ?',
                    [('Hỏi kỹ cả 5 nhóm câu hỏi', False),
                     ('Bỏ sót nhóm Gia đình/Niềm tin &rarr; thuyết phục sai người hoặc khách lăn tăn ngầm rồi bỏ đi, mất khách không rõ lý do', True),
                     ('Luôn kết thúc bằng câu hỏi niềm tin', False),
                     ('Ghi lại khúc mắc để xử lý dứt điểm', False)],
                    'Thiếu nhóm Gia đình/Niềm tin là mất khách mà không hiểu vì sao.'))

    # ------------------------------------------------------------------
    def _l_b6(self):
        return (
            self._tag('BƯỚC 6')
            + '<h3>Chủ động gửi hợp đồng</h3>'
            + '<p>Khi nhân viên cảm thấy: khách <b>không hỏi gì thêm</b>, HOẶC khách '
            '<b>đang để ý báo giá</b> của mình, HOẶC khách đã có <b>một vài phản hồi</b> '
            'về báo giá &mdash; <b>kết hợp với thời gian khởi công đang gấp</b> &mdash; '
            'thì phải <b>chủ động</b> đề cập sẽ gửi file hợp đồng cho khách tham khảo, '
            'hoặc <b>cố tình tạo tình huống</b> để gửi hợp đồng.</p>'
            + _box('ok', '<b>Mục đích:</b> gửi hợp đồng để có <b>LÝ DO chính đáng</b> '
                   'dồn khách vào việc hẹn gặp ký. Hành động sớm &mdash; không chần chừ.')
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
            self._tag('BƯỚC 7')
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
            self._tag('BƯỚC 8 &mdash; BƯỚC QUYẾT ĐỊNH')
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
            self._tag('&#127942; NGUYÊN TẮC VÀNG &mdash; TỔNG HỢP')
            + '<h3>Toàn bộ công thức của khóa học</h3>'
            + _box('ok', 'Nhân viên giỏi KHÔNG phải người gửi nhiều báo giá, mà là '
                   'người biết DẪN DẮT khách qua từng bước tới quyết định ký. Sau mỗi '
                   'lần liên hệ, khách phải tiến thêm ít nhất 1 bước.')
            + _table(['Giai đoạn / Bước', 'Công thức thuộc lòng'],
                     [['<b>Giai đoạn 0 &mdash; Tạo nhóm</b>', 'Chốt báo giá &rarr; tạo nhóm (mình + khách + trưởng phòng) &rarr; đổi ảnh (logo) + tên &rarr; gửi <b>VTV &rarr; Giới thiệu &rarr; Nhu cầu &rarr; 20 mẫu nhà</b>. CẤM nhắn tin riêng.'],
                      ['<b>Bước 1 &mdash; Kiểm tra báo giá</b>', 'Báo giá CHUẨN = Đúng tài chính + Đúng nhu cầu + Đúng mong muốn. Lệch 1 trong 3 &rarr; chưa gửi.'],
                      ['<b>Bước 2 &mdash; Phản hồi báo giá</b>', 'KHAI THÁC không ĐOÁN. Hỏi 4 ý: Đã xem kỹ? &mdash; Băn khoăn gì? &mdash; Tài chính hợp? &mdash; Muốn chỉnh gì?'],
                      ['<b>Bước 3 &mdash; Tín hiệu tiềm năng</b>', 'Khách HỎI = Khách QUAN TÂM &rarr; BÁM ĐUỔI NGAY. Không coi nhẹ câu hỏi nhỏ.'],
                      ['<b>Bước 4 &mdash; Thời gian khởi công</b>', 'Không ký sớm = không kịp Tết: thiết kế 1&ndash;2 tháng + thợ + 4 phòng ban + hoàn thiện. Giúp khách HIỂU, không dọa.'],
                      ['<b>Bước 5 &mdash; Khai thác khúc mắc</b>', 'Đủ 5 nhóm: Báo giá &mdash; Mẫu nhà &mdash; Gia đình &mdash; Khởi công &mdash; Niềm tin. Luôn kết bằng NIỀM TIN.'],
                      ['<b>Bước 6 &mdash; Gửi hợp đồng</b>', 'Khách để ý + thời gian gấp &rarr; CHỦ ĐỘNG gửi HĐ để có lý do hẹn ký. Không chần chừ.'],
                      ['<b>Bước 7 &mdash; Phản hồi hợp đồng</b>', 'Dò 6 điểm: Phụ lục vật tư (KHẲNG ĐỊNH tốt) &mdash; Đợt ứng &mdash; Tiền bảo hành &mdash; Thời gian bảo hành &mdash; Tiến độ &mdash; Khác.'],
                      ['<b>Bước 8 &mdash; Hẹn &amp; ký (CHỐT)</b>', 'Hết khúc mắc HĐ + chốt cọc 50tr (tiền mặt) + giọng TỰ TIN, MẠNH, CHẮC, KHẲNG ĐỊNH. Hẹn tốt = 10 ký 9.']],
                     widths=['26%', '74%'])
            + _box('warn', 'Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi '
                   'lần tương tác đều phải có mục tiêu rõ ràng và đưa khách tiến gần '
                   'hơn tới quyết định ký.')
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
             [('Chỉ để gọi điện; còn nhắn tin thì phải lái khách lên nhóm', T),
              ('Để nhắn tin trao đổi mọi thông tin cho tiện', F),
              ('Để gửi báo giá và hợp đồng riêng cho khách', F),
              ('Để chốt hợp đồng riêng với khách', F)]),

            ('Khi tạo nhóm Zalo, thành viên TỐI THIỂU phải gồm những ai?',
             [('Bản thân nhân viên + khách hàng + trưởng phòng', T),
              ('Chỉ cần nhân viên và khách hàng', F),
              ('Nhân viên, khách hàng và kế toán', F),
              ('Nhân viên, khách hàng và giám đốc', F)]),

            ('Thứ tự gửi tin nhắn Zalo lên nhóm ĐÚNG là gì?',
             [('4 video VTV → giới thiệu bản thân → tổng hợp nhu cầu công năng → tối thiểu 20 mẫu nhà', T),
              ('20 mẫu nhà → báo giá → video VTV → giới thiệu', F),
              ('Giới thiệu → báo giá → hợp đồng → video VTV', F),
              ('Gửi tùy ý, nội dung nào trước cũng được', F)]),

            ('Nội dung PHẢI gửi ĐẦU TIÊN lên nhóm là gì?',
             [('4 video VTV', T),
              ('Lời chào giới thiệu bản thân', F),
              ('Bảng tổng hợp nhu cầu công năng của khách', F),
              ('Các mẫu nhà tham khảo', F)]),

            ('Khi tạo nhóm, phải gửi TỐI THIỂU bao nhiêu mẫu nhà lên nhóm?',
             [('Tối thiểu 20 mẫu nhà', T),
              ('Tối thiểu 5 mẫu nhà', F),
              ('Đúng 1 mẫu nhà khách chọn', F),
              ('Không cần gửi mẫu nhà', F)]),

            ('Bước 1 - một báo giá được coi là CHUẨN khi nào?',
             [('Đúng tài chính + đúng nhu cầu + đúng mong muốn của khách', T),
              ('Có tổng giá trị cao nhất có thể', F),
              ('Gửi trước đối thủ', F),
              ('Trình bày nhiều màu sắc, đẹp mắt', F)]),

            ('Khách nói tài chính ~2,8 tỷ nhưng nhân viên gửi báo giá 3,8 tỷ. Đây là?',
             [('SAI - báo giá không khớp tài chính của khách nên vô tác dụng', T),
              ('Đúng, vì nên chào cao để còn thương lượng giảm', F),
              ('Đúng, vì khách sẽ thấy chất lượng cao hơn', F),
              ('Không quan trọng, miễn là gửi nhanh', F)]),

            ('Bước 2 - khi lấy phản hồi báo giá, cách hỏi nào ĐÚNG nhất?',
             [('Hỏi cụ thể: đã xem kỹ báo giá + phụ lục chưa, băn khoăn gì, mức đầu tư có phù hợp, muốn điều chỉnh gì', T),
              ('Hỏi chung chung "anh xem chưa ạ?" rồi thôi', F),
              ('Hỏi "anh chị ký chưa ạ?" để chốt nhanh', F),
              ('Không hỏi, chờ khách tự nhắn lại', F)]),

            ('Sau khi gửi báo giá bao lâu thì BẮT BUỘC phải lấy phản hồi từ khách?',
             [('Sau 1-2 ngày', T),
              ('Sau 1-2 tuần', F),
              ('Chỉ khi khách chủ động nhắn lại', F),
              ('Sau đúng 1 tháng', F)]),

            ('Bước 3 - 1-2 ngày sau khi gửi báo giá, khách nhắn hỏi một câu nhỏ về phụ lục vật tư. Nghĩa là gì?',
             [('Tín hiệu khách RẤT tiềm năng - phải trả lời nhanh và bám đuổi ngay', T),
              ('Khách chỉ hỏi cho có, không cần quan tâm', F),
              ('Khách đang làm khó, nên né trả lời', F),
              ('Chờ gom nhiều câu hỏi rồi trả lời một lần', F)]),

            ('Bước 4 - vì sao phải nhắc khách ký sớm nếu muốn ở nhà mới trước Tết?',
             [('Vì thiết kế mất 1-2 tháng, còn chuẩn bị thợ, vật tư, dự toán, nhân lực, rồi nội thất/sân vườn - không kịp bàn giao', T),
              ('Vì giá sẽ tăng gấp đôi nếu ký muộn', F),
              ('Vì công ty sắp hết suất nhận công trình', F),
              ('Vì khách phải khởi công ngay trong tuần', F)]),

            ('Bước 4 - mục tiêu khi nhắc khách về thời gian khởi công là gì?',
             [('Giúp khách hiểu rõ hệ quả của việc chậm quyết định, KHÔNG gây áp lực vô lý', T),
              ('Dọa khách rằng giá sẽ tăng gấp đôi', F),
              ('Nói công ty sắp hết suất nhận công trình', F),
              ('Ép khách phải khởi công trong tuần này', F)]),

            ('Bước 5 - nhóm câu hỏi nào giúp phát hiện RÀO CẢN THẬT SỰ trước khi ký?',
             [('Nhóm Niềm tin: "Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?"', T),
              ('Nhóm Báo giá: "Có vượt tài chính không?"', F),
              ('Nhóm Mẫu nhà: "Đã đúng phong cách chưa?"', F),
              ('Nhóm Khởi công: "Dự kiến khi nào?"', F)]),

            ('Bước 5 - sai lầm nguy hiểm khi khai thác khúc mắc chưa đủ là gì?',
             [('Bỏ sót nhóm Gia đình/Niềm tin → thuyết phục sai người hoặc khách lăn tăn ngầm rồi bỏ đi, mất khách không rõ lý do', T),
              ('Hỏi kỹ cả 5 nhóm câu hỏi', F),
              ('Luôn kết thúc bằng câu hỏi niềm tin', F),
              ('Ghi lại khúc mắc để xử lý dứt điểm', F)]),

            ('Bước 6 - khi nào nên CHỦ ĐỘNG gửi hợp đồng cho khách?',
             [('Khi thấy khách để ý/có vài phản hồi về báo giá + thời gian khởi công gấp → gửi để có lý do hẹn ký, không chần chừ', T),
              ('Chờ đến khi khách tự hỏi về hợp đồng', F),
              ('Chỉ gửi khi khách đã đồng ý mọi thứ bằng văn bản', F),
              ('Không bao giờ gửi trước khi khách yêu cầu', F)]),

            ('Bước 7 - khi gửi hợp đồng, khách thắc mắc NHIỀU NHẤT về điều gì và nhân viên phải làm gì?',
             [('Về phụ lục vật tư - phải KHẲNG ĐỊNH đây là vật tư tốt trên thị trường', T),
              ('Về màu sắc bản vẽ - đổi lại cho khách', F),
              ('Về tên công ty - kể lịch sử công ty', F),
              ('Không cần quan tâm, chờ khách ký', F)]),

            ('Bước 8 - nguyên tắc quan trọng nhất về CÁCH NÓI khi hẹn ký là gì?',
             [('Giọng tự tin, nói mạnh, nói chắc, khẳng định - không rụt rè', T),
              ('Nói nhẹ nhàng, rào trước đón sau', F),
              ('Nói thật nhanh cho xong', F),
              ('Để khách nói là chính, mình chỉ nghe', F)]),

            ('Bước 8 - vì sao phải trao đổi trước về việc đặt cọc 50 triệu (ưu tiên tiền mặt)?',
             [('Vì nếu không thỏa thuận trước, khi về ký khách hay lấy lý do chưa chuẩn bị tiền; đề cập cọc giúp khách có tâm lý chuẩn bị ký cao hơn', T),
              ('Vì công ty cần tiền gấp', F),
              ('Vì để thử xem khách có tiền không', F),
              ('Vì đặt cọc là thủ tục không quan trọng', F)]),
        ]
