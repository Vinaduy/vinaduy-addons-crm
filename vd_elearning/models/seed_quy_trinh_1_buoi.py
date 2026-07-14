# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH CHUẨN XỬ LÝ KHÁCH MỚI TRONG 1
BUỔI" (Gọi điện -> Kết bạn Zalo -> Tạo nhóm -> Hoàn thiện nhóm -> Gửi mẫu nhà
-> Làm & gửi báo giá).

Toàn bộ quy trình phải hoàn tất trong 1 BUỔI (khoảng 4 tiếng) hoặc cùng lắm 1
NGÀY. Mỗi bước xong BẮT BUỘC kích hoạt bước kế tiếp, tuyệt đối không dừng lại
chờ đợi. Khóa gồm 6 bài chuyên sâu theo đúng tài liệu gốc.

GIAO DIỆN kiểu Streamlit: menu trái chọn từng bài (micro-learning) + hộp màu +
quiz chấm đúng/sai tức thì (thuần CSS input:checked, KHÔNG JS). vd_body
sanitize=False + render markup() nên HTML thô giữ nguyên.

Helper nối chuỗi (+) -> tránh bẫy %. MỌI class method dùng prefix RIÊNG _q1b_
để KHÔNG trùng tên với seed khác (xem reference-seed-method-name-collision).
Idempotent theo version lưu ở ir.config_parameter.
"""
from odoo import api, models

_Q1B_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.quy_trinh_1_buoi_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-q1b{font-size:16px;line-height:1.7;color:#1f2937;}'
    '.vd-q1b .vd-course{background:linear-gradient(180deg,#fff7f3 0%,#f5faff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-q1b h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-q1b h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-q1b p{margin:0 0 10px;}'
    '.vd-q1b ul,.vd-q1b ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-q1b li{margin:5px 0;}'
    '.vd-q1b b{color:#111827;}'
    '.vd-q1b table{border-collapse:collapse;width:100%;margin:8px 0 6px;font-size:15px;}'
    '.vd-q1b th,.vd-q1b td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-q1b th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-q1b .thok{background:#dcfce7;color:#15803d;}'
    '.vd-q1b .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-q1b .no{color:#b91c1c;font-weight:700;}'
    '.vd-q1b .yes{color:#15803d;font-weight:700;}'
    '.vd-q1b .navr,.vd-q1b .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-q1b .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-q1b .vc-side{flex:0 0 264px;}'
    '.vd-q1b .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-q1b .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-q1b .vc-navbtn:hover{background:#fff5f1;border-color:#ffd9c9;color:#e8401f;}'
    '.vd-q1b .vc-nbadge{flex:0 0 auto;display:inline-block;background:#fff1ec;color:#e8401f;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-q1b .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;}'
    '.vd-q1b .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-q1b .vc-panel{display:none;}'
    '.vd-q1b .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#e8401f;background:#fff1ec;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-q1b .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:9px 0;}'
    '.vd-q1b .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-q1b .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-q1b .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-q1b .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # công thức
    '.vd-q1b .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:10px 0;}'
    '.vd-q1b .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-q1b .fml .fml-b{color:#4c1d95;font-weight:600;}'
    # câu mẫu (script)
    '.vd-q1b .say{background:#ecfeff;border:2px dashed #22d3ee;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#155e75;font-style:italic;}'
    '.vd-q1b .say .sh{font-style:normal;font-weight:800;color:#0e7490;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:4px;}'
    # thứ tự đánh số
    '.vd-q1b .vc-order{margin:12px 0;border:1px solid #ffd9c9;border-radius:12px;overflow:hidden;}'
    '.vd-q1b .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #ffe3d6;background:#fffaf7;}'
    '.vd-q1b .vc-ostep:last-child{border-bottom:none;}'
    '.vd-q1b .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#e8401f;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-q1b .vc-ot{font-weight:800;color:#7c2d12;}'
    '.vd-q1b .vc-od{color:#9a3412;font-size:14.5px;}'
    # quiz
    '.vd-q1b .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
    '.vd-q1b .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-q1b .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-q1b .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-q1b .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-q1b .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-q1b .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-q1b .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-q1b .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-q1b .vc-layout{flex-direction:column;}'
    '.vd-q1b .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-q1b .vc-sidehead{width:100%;}'
    '.vd-q1b .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
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


def _say(text):
    return ('<div class="say"><div class="sh">&#128172; CÂU MẪU NÓI VỚI KHÁCH</div>'
            + text + '</div>')


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


class SlideChannelSeedQuyTrinh1Buoi(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_quy_trinh_1_buoi(self):
        ch = self.env.ref('vd_elearning.course_quy_trinh_1_buoi',
                          raise_if_not_found=False)
        if not ch:
            ch = self.sudo().search(
                [('name', 'ilike', 'xử lý khách mới trong 1 buổi')], limit=1)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _Q1B_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-q1b" style="%s">%s</div>'
                                 % (_WRAP, self._q1b_app())),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._q1b_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _Q1B_VERSION)
        return True

    # ==================================================================
    #  APP (menu trái + panel phải)
    # ==================================================================
    def _q1b_app(self):
        lessons = self._q1b_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'q1bL' + str(i)
            pid = 'q1bP' + str(i)
            radios += ('<input class="navr" type="radio" name="q1bnav" id="' + rid + '"'
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
            'KỸ NĂNG SALE &mdash; XỬ LÝ KHÁCH MỚI TRỌN GÓI 1 BUỔI</div>'
            '<div style="color:#fff;font-size:26px;font-weight:900;margin-top:6px;line-height:1.2;'
            'text-shadow:0 2px 8px rgba(0,0,0,.15);">'
            'Quy trình chuẩn: Gọi điện &rarr; Kết bạn Zalo &rarr; Tạo nhóm &rarr; '
            'Mẫu nhà &rarr; Báo giá</div>'
            '<div style="color:#fff8f4;font-size:14.5px;margin-top:9px;">'
            '&#9200; TOÀN BỘ quy trình phải xong trong <b>1 BUỔI (khoảng 4 tiếng)</b> '
            'hoặc cùng lắm <b>1 NGÀY</b>. &#128073; Bấm từng mục ở MENU BÊN TRÁI để học '
            'lần lượt &mdash; mỗi bài có trắc nghiệm chấm ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _q1b_tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    def _q1b_lessons(self):
        return [
            ('&#129504;', 'MỞ ĐẦU', 'Tư duy &amp; Dòng thời gian 1 buổi', self._q1b_l_open()),
            ('&#128222;', 'BÀI 1', 'Gọi điện tư vấn lần đầu', self._q1b_l1()),
            ('&#129309;', 'BÀI 2', 'Kết bạn Zalo', self._q1b_l2()),
            ('&#128101;', 'BÀI 3', 'Tạo nhóm Zalo', self._q1b_l3()),
            ('&#127916;', 'BÀI 4', 'Hoàn thiện nhóm (10 phút)', self._q1b_l4()),
            ('&#127968;', 'BÀI 5', 'Gửi mẫu nhà', self._q1b_l5()),
            ('&#128181;', 'BÀI 6', 'Làm &amp; gửi báo giá', self._q1b_l6()),
            ('&#127942;', 'TỔNG KẾT', 'Nguyên tắc vàng', self._q1b_l_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỞ ĐẦU
    # ------------------------------------------------------------------
    def _q1b_l_open(self):
        return (
            self._q1b_tag('TƯ DUY NỀN TẢNG')
            + '<h3>Một khách mới = một quy trình TRỌN GÓI trong 1 buổi</h3>'
            + _box('ok', 'Mục tiêu bắt buộc của MỌI chuyên viên tư vấn: từ lúc <b>gọi '
                   'điện tư vấn lần đầu</b> cho tới khi <b>gửi được báo giá</b>, tất cả '
                   'chỉ gói gọn trong <b>1 buổi sáng hoặc 1 buổi chiều (khoảng 4 tiếng)</b>, '
                   'cùng lắm là <b>trong 1 ngày</b>.')
            + '<p>Toàn bộ chuỗi công việc phải chạy LIÊN TỤC, không đứt đoạn: gọi điện '
            'tư vấn &rarr; kết bạn Zalo &rarr; tạo nhóm &rarr; hoàn thiện nhóm (đổi tên, '
            'ảnh, gửi video/lời chào/tổng hợp) &rarr; gửi mẫu nhà &rarr; làm và gửi báo '
            'giá. <b>Mỗi bước làm xong BẮT BUỘC kích hoạt bước kế tiếp.</b></p>'
            + _box('err', '<b>Sai lầm chí mạng:</b> để quy trình bị đứt ở một bước rồi '
                   'kéo dài sang 2&ndash;3 ngày. Rất nhiều chuyên viên gọi điện xong '
                   '2&ndash;3 ngày sau vẫn KHÔNG làm nổi báo giá &mdash; đây là lý do '
                   'mất khách nhiều nhất.')
            + '<h4>Vì sao phải nhanh và liền mạch?</h4>'
            + _nendont(
                ['Khách còn &#8220;nóng&#8221;, còn nhớ cuộc gọi &rarr; dễ tương tác',
                 'Thể hiện sự chuyên nghiệp, chuẩn quy trình',
                 'Chốt được báo giá ngay khi thông tin còn đầy đủ trong đầu'],
                ['Để nguội khách rồi mới quay lại &rarr; khách quên, nghiêng sang đối thủ',
                 'Dừng ở một bước rồi &#8220;chờ&#8221; thông tin, chờ khách rảnh',
                 'Coi cuộc gọi tư vấn là xong việc &mdash; nó mới chỉ là bước 1'])
            + '<h4>&#9201;&#65039; DÒNG THỜI GIAN CHUẨN (thuộc lòng)</h4>'
            + _order([
                ('KẾT THÚC CUỘC GỌI &rarr; BẤM &#8220;CHỐT BÁO GIÁ&#8221; NGAY',
                 'Phần mềm sinh file báo giá + sinh TÊN NHÓM ZALO mới ngay lúc đó.'),
                ('KẾT BẠN ZALO + gọi nhắc khách đồng ý',
                 'Gửi lời mời, 5 phút sau khách chưa đồng ý thì gọi lại nhắc ngay.'),
                ('TẠO NHÓM ZALO (mình + khách + trưởng phòng)',
                 'Kết bạn xong là tạo nhóm liền, KHÔNG xin phép khách.'),
                ('HOÀN THIỆN NHÓM trong 10 phút',
                 'Đổi tên + ảnh nhóm, gửi 4 video VTV, lời chào, tổng hợp cuộc gọi.'),
                ('GỬI MẪU NHÀ trong ~15 phút',
                 'Gửi 5&ndash;10 mẫu (20&ndash;30 nếu khách phân vân). KHÔNG chờ khách chốt mẫu.'),
                ('GIÃN ~2 TIẾNG &rarr; GỬI BÁO GIÁ',
                 'Cả chuỗi trên gói trong ~30 phút; báo giá đã có sẵn, đợi đủ 2 tiếng mới gửi cho tự nhiên.'),
            ])
            + _fml('1 KHÁCH MỚI = <b>Gọi + Chốt báo giá &rarr; Kết bạn &rarr; Tạo nhóm '
                   '&rarr; Hoàn thiện nhóm (10&#8242;) &rarr; Mẫu nhà (15&#8242;) &rarr; '
                   'Báo giá (sau 2 tiếng)</b>. Tất cả trong 1 BUỔI. Đứt bước nào = mất '
                   'khách bước đó.')
            + _quiz('q1b_open',
                    'Toàn bộ quy trình từ gọi điện lần đầu đến gửi báo giá nên hoàn tất trong bao lâu?',
                    [('Trong 1 buổi (khoảng 4 tiếng), cùng lắm là 1 ngày', True),
                     ('Trong khoảng 1 tuần cho thong thả', False),
                     ('Bao lâu cũng được, miễn là khách chốt mẫu xong', False),
                     ('Chỉ cần gọi điện là đủ, các bước sau tùy hứng', False)],
                    'Cả quy trình phải chạy liên tục trong 1 buổi, cùng lắm 1 ngày &mdash; không để đứt đoạn.'))

    # ------------------------------------------------------------------
    #  BÀI 1 - GỌI ĐIỆN
    # ------------------------------------------------------------------
    def _q1b_l1(self):
        return (
            self._q1b_tag('BÀI 1 &mdash; BƯỚC KHỞI ĐẦU')
            + '<h3>Gọi điện tư vấn lần đầu: lấy ĐỦ thông tin để sinh báo giá</h3>'
            + _box('ok', 'Nguyên tắc: khi gọi tư vấn, cố gắng <b>trao đổi càng lâu càng '
                   'tốt</b> (5&ndash;10 phút), <b>khai thác ĐẦY ĐỦ thông tin</b> để phần '
                   'mềm sinh ra được bảng báo giá.')
            + '<h4>Vì sao đây là bước quyết định?</h4>'
            + '<p>Nếu cuộc gọi thiếu thông tin thì phần mềm <b>không sinh được báo giá</b>, '
            'và quy trình xử lý khách <b>dừng lại ngay tại bước này</b>. Nhiều chuyên '
            'viên quen hỏi 1&ndash;2 ý (quen hỏi thời gian, quen hỏi tài chính&hellip;) '
            'rồi bỏ sót các ý khác.</p>'
            + _box('err', '<b>Sai lầm rất nghiêm trọng:</b> thiếu thông tin nên đợi kết '
                   'bạn Zalo rồi nhắn tin cá nhân hỏi tiếp, hoặc cố tình chờ liên hệ lại '
                   'để &#8220;xin nốt&#8221; thông tin. Cách này kéo dài thời gian xử lý '
                   '&rarr; không kịp làm báo giá &rarr; hỏng cả quy trình.')
            + '<h4>&#128273; QUY TẮC VÀNG: quên thông tin thì ĐIỀN TẠM, KHÔNG dừng lại</h4>'
            + '<p>Trong trường hợp lỡ quên hỏi một thông tin nào đó, <b>bắt buộc chọn tạm '
            'một phương án</b> để phần mềm vẫn sinh được báo giá &mdash; tuyệt đối không '
            'dừng để đi hỏi lại:</p>'
            + _table(['Thông tin bị quên', 'ĐIỀN TẠM phương án nào', 'Vì sao chọn vậy'],
                     [['Quên hỏi đường to hay đường nhỏ', '<b>Chọn ĐƯỜNG NHỎ</b>',
                       'Phương án an toàn cho chi phí vận chuyển/thi công; điều chỉnh sau nếu cần.'],
                      ['Quên hỏi thời gian khởi công', '<b>Chọn THÁNG KHỞI CÔNG GẦN NHẤT</b>',
                       'Ưu tiên tiến độ sớm; luôn có thể dời lại sau.'],
                      ['Quên hỏi công năng', '<b>Điền TẠM: 1 khách + 1 bếp + 3 phòng ngủ + 2 WC</b>',
                       'Công năng phổ biến, đủ để phần mềm ra được bảng báo giá (chỉ là ví dụ).']],
                     widths=['30%', '38%', '32%'])
            + _box('warn', 'Điền tạm là để KHÔNG dừng quy trình &mdash; không phải để làm '
                   'ẩu. Vẫn cố khai thác đủ nhất có thể; chỉ điền tạm cho ý nào thực sự bị bỏ sót.')
            + '<h4>&#9989; Kết thúc cuộc gọi = BẤM &#8220;CHỐT BÁO GIÁ&#8221; NGAY</h4>'
            + '<p>Khi kết thúc cuộc gọi, việc BẮT BUỘC ngay lập tức là bấm nút '
            '<b>&#8220;Chốt báo giá&#8221;</b>. Khi đó phần mềm sẽ:</p>'
            + '<ul><li>Sinh ra <b>file báo giá</b> cho khách.</li>'
            '<li>Sinh ra <b>tên nhóm Zalo mới</b> để bạn dùng tạo nhóm ở bước sau.</li></ul>'
            + _box('info', 'Vì vậy hãy tư vấn sao cho khi gác máy là đã có ĐỦ thông tin '
                   '&mdash; gác máy xong bấm chốt báo giá luôn, không chần chừ.')
            + _nendont(
                ['Trao đổi lâu, khai thác đủ mọi ý để sinh báo giá',
                 'Quên ý nào thì điền tạm phương án hợp lý ngay',
                 'Gác máy là bấm &#8220;Chốt báo giá&#8221; liền'],
                ['Quen hỏi 1&ndash;2 ý rồi bỏ sót phần còn lại',
                 'Dừng quy trình để chờ nhắn tin hỏi lại thông tin',
                 'Kết thúc cuộc gọi mà không chốt báo giá'])
            + _fml('Gọi điện = <b>Khai thác ĐỦ thông tin</b> &rarr; quên ý nào <b>ĐIỀN '
                   'TẠM</b> (đường nhỏ / tháng gần nhất / 1 khách 1 bếp 3 ngủ 2 wc) '
                   '&rarr; gác máy là <b>BẤM CHỐT BÁO GIÁ</b> (sinh file + tên nhóm Zalo).')
            + _quiz('q1b_1',
                    'Đang làm báo giá thì phát hiện quên hỏi khách đường to hay đường nhỏ. Phải làm gì?',
                    [('Dừng lại, chờ nhắn tin Zalo hỏi khách rồi mới làm tiếp', False),
                     ('Chọn tạm ĐƯỜNG NHỎ để phần mềm vẫn sinh được báo giá', True),
                     ('Hủy báo giá vì thiếu thông tin', False),
                     ('Gọi lại khách ngay dù vừa mới gác máy', False)],
                    'Quên thông tin thì điền tạm (đường nhỏ) để không dừng quy trình &mdash; tuyệt đối không chờ.'))

    # ------------------------------------------------------------------
    #  BÀI 2 - KẾT BẠN ZALO
    # ------------------------------------------------------------------
    def _q1b_l2(self):
        return (
            self._q1b_tag('BÀI 2 &mdash; MẮT XÍCH SỐNG CÒN')
            + '<h3>Kết bạn Zalo &mdash; gọi nhắc khách đồng ý NGAY</h3>'
            + _box('ok', 'Ngay sau khi kết thúc cuộc gọi tư vấn, bước tiếp theo là '
                   '<b>kết bạn Zalo với khách</b>. Đây là mắt xích rất quan trọng, vì '
                   'nếu không kết bạn được thì <b>toàn bộ quy trình sau đứng lại</b>.')
            + '<h4>Vì sao kết bạn Zalo lại là sống còn?</h4>'
            + _box('err', 'Không kết bạn &rarr; <b>không tạo được nhóm</b> &rarr; không '
                   'gọi được Zalo cho khách &rarr; <b>không gửi được báo giá</b>. (Quy '
                   'định: báo giá BẮT BUỘC gửi trong nhóm, CẤM gửi qua tin nhắn cá nhân.)')
            + '<p>Nhiều khách sẽ <b>không đồng ý kết bạn</b> hoặc đang bận nên chưa bấm '
            'đồng ý ngay. Nếu để mặc kệ, khách sẽ cố tình bỏ qua và mặc định là mình '
            'không tạo nhóm được. Về sau khách có nhắn tin cho mình thì mình vẫn không '
            'gọi Zalo được, không tạo nhóm được, không gửi báo giá được.</p>'
            + _box('warn', '<b>Quy luật tâm lý:</b> khách đã KHÔNG muốn kết bạn ở phút '
                   'đầu thì về sau càng KHÔNG muốn. Phải xử lý NGAY, đừng để nguội.')
            + '<h4>&#128222; Quy tắc bắt buộc: gọi điện nhắc NGAY</h4>'
            + '<p>Sau khi gửi lời mời kết bạn mà <b>5 phút</b> khách chưa đồng ý, chuyên '
            'viên <b>BẮT BUỘC gọi điện lại để nhắc</b> &mdash; không chờ đợi.</p>'
            + _say('&#8220;Anh ơi, em vừa gửi lời mời kết bạn Zalo cho mình rồi đấy ạ, '
                   'anh đồng ý giúp em để em lập nhóm gửi thông tin và báo giá cho gia '
                   'đình mình nhé!&#8221;')
            + _nendont(
                ['Gửi lời mời xong theo dõi ngay',
                 '5 phút khách chưa đồng ý &rarr; gọi điện nhắc liền',
                 'Coi kết bạn là điều kiện BẮT BUỘC để đi tiếp'],
                ['Gửi lời mời rồi để đó, không nhắc',
                 'Chờ khách tự đồng ý &#8220;lúc nào rảnh&#8221;',
                 'Định bụng nhắn tin cá nhân thay cho việc tạo nhóm'])
            + _box('info', '<b>Nhớ nguyên tắc:</b> bạn đã bỏ 5&ndash;10 phút gọi tư vấn '
                   'với khách; nếu gọi xong mà không kết bạn, không gửi báo giá thì cuộc '
                   'gọi đó gần như <b>vô nghĩa</b> &mdash; mất thời gian mà không giải '
                   'quyết được gì.')
            + _fml('Kết thúc cuộc gọi &rarr; <b>gửi lời mời kết bạn Zalo</b> &rarr; 5 '
                   'phút chưa đồng ý &rarr; <b>GỌI ĐIỆN NHẮC NGAY</b>. Không kết bạn = '
                   'không nhóm = không báo giá.')
            + _quiz('q1b_2',
                    'Đã gửi lời mời kết bạn Zalo, 5 phút sau khách vẫn chưa đồng ý. Nên làm gì?',
                    [('Chờ vài ngày xem khách có tự đồng ý không', False),
                     ('Gọi điện lại nhắc khách đồng ý kết bạn ngay lập tức', True),
                     ('Nhắn tin SMS hỏi thông tin để làm báo giá luôn', False),
                     ('Bỏ qua khách này vì khó tính', False)],
                    'Phải gọi điện nhắc NGAY &mdash; khách không kết bạn thì cả quy trình sau đứng lại.'))

    # ------------------------------------------------------------------
    #  BÀI 3 - TẠO NHÓM
    # ------------------------------------------------------------------
    def _q1b_l3(self):
        return (
            self._q1b_tag('BÀI 3 &mdash; KỶ LUẬT THÉP')
            + '<h3>Tạo nhóm Zalo &mdash; CẤM tuyệt đối nhắn tin cá nhân</h3>'
            + _box('ok', 'Kết bạn xong là <b>lập tức tạo nhóm Zalo</b>. Nhóm gồm: '
                   '<b>chuyên viên tư vấn + khách hàng + trưởng phòng</b>.')
            + '<h4>&#128683; Quy định thép: cấm nhắn tin riêng cá nhân với khách</h4>'
            + '<p>Kể cả khi khách chủ động nhắn tin cá nhân, việc của chuyên viên là '
            '<b>vẫn tạo nhóm</b> rồi trả lời câu hỏi của khách <b>trên nhóm</b> để lái '
            'khách sang thói quen nhắn tin trên nhóm. Zalo cá nhân <b>CHỈ được gọi điện, '
            'KHÔNG được nhắn tin</b>.</p>'
            + '<h4>Vì sao cấm nhắn cá nhân? (hậu quả rất khó xử lý về sau)</h4>'
            + _table(['Ai bị ảnh hưởng', 'Hậu quả khi khách chỉ quen làm việc cá nhân'],
                     [['<b>Người đi ký hợp đồng</b>', 'Rất khó đặt cọc &mdash; khách chỉ biết mỗi bạn, không tin người khác.'],
                      ['<b>Kế toán</b>', 'Rất khó thu tiền và viết hóa đơn vì khách không biết làm việc với ai.'],
                      ['<b>Phòng thiết kế</b>', 'Rất khó xử lý công việc thiết kế vì khách quen làm việc cá nhân với bạn.'],
                      ['<b>Phòng thi công</b>', 'Khó thi công; khách phản ánh về thi công thì chuyên viên không biết phản hồi.'],
                      ['<b>Chính chuyên viên</b>', 'Bị khách làm phiền, hỏi câu kỹ thuật mà mình không trả lời được.']],
                     widths=['26%', '74%'])
            + _box('err', '<b>Quy tắc bắt buộc:</b> KHÔNG hỏi ý kiến khách khi tạo nhóm '
                   '&mdash; <b>mặc định tạo nhóm luôn</b>, không cần xin phép. Vì nếu bạn '
                   'xin phép thì khách đương nhiên không đồng ý.')
            + '<p>Phải xây <b>tư duy làm việc nhóm</b> cho khách ngay từ giây phút đầu. '
            'Tuyệt đối không tương tác, không trả lời bất kỳ điều gì trên Zalo cá nhân '
            '&mdash; cá nhân chỉ được GỌI ĐIỆN, không nhắn tin.</p>'
            + _box('info', '<b>Nếu lỡ quên tạo nhóm / lỡ nhắn cá nhân:</b> cứ <b>âm thầm '
                   'tạo nhóm</b> và chuyển sang làm việc với khách trên nhóm, đồng thời '
                   '<b>dừng ngay</b> việc nhắn tin cá nhân.')
            + _nendont(
                ['Kết bạn xong tạo nhóm ngay (mình + khách + trưởng phòng)',
                 'Mặc định tạo nhóm, KHÔNG xin phép khách',
                 'Khách nhắn cá nhân &rarr; vẫn tạo nhóm, trả lời trên nhóm',
                 'Zalo cá nhân chỉ để GỌI ĐIỆN'],
                ['Hỏi &#8220;em lập nhóm được không ạ?&#8221; (khách sẽ từ chối)',
                 'Nhắn tin trao đổi/giải đáp trên Zalo cá nhân',
                 'Gửi báo giá qua tin nhắn cá nhân',
                 'Chần chừ chưa tạo nhóm vì ngại khách'])
            + _fml('Kết bạn &rarr; <b>TẠO NHÓM NGAY</b> (mình + khách + trưởng phòng), '
                   '<b>không xin phép</b>. CẤM nhắn cá nhân &mdash; cá nhân chỉ để gọi '
                   'điện. Mọi trao đổi lái LÊN NHÓM.')
            + _quiz('q1b_3',
                    'Khách chủ động nhắn tin vào Zalo CÁ NHÂN của bạn để hỏi. Xử lý đúng là gì?',
                    [('Trả lời luôn trên Zalo cá nhân cho tiện', False),
                     ('Vẫn tạo nhóm rồi trả lời câu hỏi của khách TRÊN NHÓM để lái khách lên nhóm', True),
                     ('Xin phép khách cho lập nhóm rồi mới tạo', False),
                     ('Gửi luôn báo giá qua tin nhắn cá nhân', False)],
                    'Cấm nhắn cá nhân &mdash; luôn tạo nhóm và trả lời trên nhóm; không cần xin phép khách.'))

    # ------------------------------------------------------------------
    #  BÀI 4 - HOÀN THIỆN NHÓM
    # ------------------------------------------------------------------
    def _q1b_l4(self):
        return (
            self._q1b_tag('BÀI 4 &mdash; TRONG 10 PHÚT')
            + '<h3>Hoàn thiện nhóm: đổi tên/ảnh + 4 video VTV + lời chào + tổng hợp</h3>'
            + _box('ok', 'Ngay sau khi tạo nhóm, tập thói quen làm LIỀN &amp; CÙNG LÚC '
                   'một chuỗi việc &mdash; tốt nhất hoàn tất trong <b>10 phút</b> kể từ '
                   'khi kết thúc cuộc gọi.')
            + '<h4>&#128204; 5 việc BẮT BUỘC làm ngay khi tạo nhóm xong</h4>'
            + _order([
                ('ĐỔI TÊN NHÓM', 'Đổi theo đúng tên nhóm phần mềm đã sinh khi bấm chốt báo giá.'),
                ('ĐỔI ẢNH ĐẠI DIỆN NHÓM', 'Dùng ảnh/logo theo quy định của công ty &mdash; nhận diện chuyên nghiệp.'),
                ('GỬI 4 VIDEO VTV', 'Nội dung tạo uy tín, khẳng định thương hiệu ngay từ đầu.'),
                ('GỬI LỜI CHÀO', 'Giới thiệu bản thân là người đồng hành, tạo thiện cảm.'),
                ('GỬI TỔNG HỢP THÔNG TIN CUỘC GỌI', 'Chốt lại đúng nhu cầu/công năng đã trao đổi &mdash; cho khách thấy mình lắng nghe kỹ.'),
            ])
            + '<h4>Vì sao phải gửi NGAY, đầy đủ, đúng lúc?</h4>'
            + _box('err', '<b>Sai lầm thường gặp:</b> quên gửi, đến lúc nhớ ra (1&ndash;2 '
                   'ngày sau) mới gửi thì <b>vô duyên, lệch chỗ, thông tin không đúng '
                   'thời điểm</b>, và chính mình cũng thấy ngại.')
            + '<p>Đây toàn là những thông tin quan trọng để khách <b>đánh giá sự chuyên '
            'nghiệp của công ty</b>. Không gửi thì khách <b>không có đủ dữ liệu</b> để '
            'đánh giá và tin tưởng.</p>'
            + _box('warn', 'Công ty sẽ <b>kiểm soát tất cả các nhóm Zalo</b> &mdash; vì '
                   'vậy phải đổ đầy đủ những tin nhắn trên vào nhóm, không được thiếu.')
            + _nendont(
                ['Làm cả 5 việc liền mạch trong 10 phút',
                 'Gửi đúng thời điểm khi khách còn nhớ cuộc gọi',
                 'Đổ đầy đủ nội dung để công ty kiểm soát được'],
                ['Quên, 1&ndash;2 ngày sau mới gửi (vô duyên, ngại)',
                 'Gửi thiếu, gửi lệch thứ tự',
                 'Bỏ qua vì nghĩ &#8220;để sau cũng được&#8221;'])
            + _fml('Tạo nhóm xong (trong 10 phút): <b>Đổi tên &rarr; Đổi ảnh &rarr; 4 '
                   'video VTV &rarr; Lời chào &rarr; Tổng hợp cuộc gọi</b>. Làm ngay, '
                   'đầy đủ, đúng lúc.')
            + _quiz('q1b_4',
                    'Sau khi tạo nhóm xong, trong 10 phút phải làm những việc nào?',
                    [('Chỉ cần đổi tên nhóm là đủ', False),
                     ('Đổi tên + đổi ảnh nhóm, gửi 4 video VTV, gửi lời chào, gửi tổng hợp thông tin cuộc gọi', True),
                     ('Chờ khách nhắn trước rồi mới gửi gì đó', False),
                     ('Gửi ngay báo giá để chốt cho nhanh', False)],
                    'Đủ 5 việc: đổi tên + ảnh, 4 video VTV, lời chào, tổng hợp cuộc gọi &mdash; trong 10 phút.'))

    # ------------------------------------------------------------------
    #  BÀI 5 - GỬI MẪU NHÀ
    # ------------------------------------------------------------------
    def _q1b_l5(self):
        return (
            self._q1b_tag('BÀI 5 &mdash; TRONG ~15 PHÚT')
            + '<h3>Gửi mẫu nhà đúng ý &mdash; nhưng TUYỆT ĐỐI không chờ khách chốt mẫu</h3>'
            + _box('ok', 'Khi gọi điện, cố gắng hiểu khách muốn làm kiểu nhà nào để sau '
                   'khi tạo nhóm gửi mẫu cho <b>chính xác với mong muốn</b> của khách. '
                   'Nên gửi xong mẫu nhà trong khoảng <b>15 phút</b>.')
            + '<h4>Trước tiên: giúp khách CHỐT một kiểu dáng</h4>'
            + '<p>Rất nhiều khách phân vân (nhà máy Nhật hay Thái, mái ngói hay vườn hiện '
            'đại&hellip;). Nhiệm vụ của chuyên viên là <b>giúp khách chốt loại nhà</b>, '
            'thống nhất một kiểu dáng ưng ý nhất để hai bên đồng thuận ngay từ tư vấn '
            'ban đầu. Làm không tốt việc này, khách sẽ nghĩ bạn <b>không hiểu khách, kém '
            'chuyên nghiệp</b> và chán nản.</p>'
            + '<h4>&#128681; SAI LẦM LỚN NHẤT: chờ khách chốt mẫu rồi mới làm báo giá</h4>'
            + _box('err', 'Tuyệt đối KHÔNG ngồi đợi khách chọn được 1 mẫu rồi mới làm báo '
                   'giá. Có thể gửi 10 mẫu, nhưng <b>không cần đợi khách chốt mẫu nào</b> '
                   'mới báo giá. Đây là sai lầm cực kỳ nghiêm trọng.')
            + _say('&#8220;Em gửi anh/chị mấy mẫu nhà để tham khảo thêm ạ. Anh/chị làm '
                   'mẫu nào cũng được, <b>giá cả như nhau</b>; việc chọn mẫu mình sẽ làm '
                   'ở bước sau khi ký hợp đồng, phòng thiết kế sẽ làm việc kỹ về mẫu với '
                   'anh/chị sau ạ.&#8221;')
            + '<h4>&#128209; Gửi bao nhiêu mẫu? &mdash; theo 3 tình huống</h4>'
            + _table(['Tình huống của khách', 'Cách gửi mẫu ĐÚNG'],
                     [['<b>Khách có định hướng</b> (đã biết thích kiểu gì)',
                       'Gửi <b>5&ndash;10 mẫu</b> phù hợp nhất với mong muốn của khách.'],
                      ['<b>Khách đã có mẫu sẵn</b> (tự gửi ảnh mẫu cho mình)',
                       'Chỉ gửi khoảng <b>5 mẫu GIỐNG NHẤT</b> với mẫu của khách. Nếu không tìm được mẫu nào giống thì <b>KHÔNG gửi mẫu nữa</b>, ngầm định làm theo mẫu của khách.'],
                      ['<b>Khách không biết chọn gì</b> (chưa có định hướng)',
                       'Gửi <b>20&ndash;30 mẫu</b> gồm cả các kiểu khách phân vân (vd 10 mẫu Nhật + 10 mẫu Thái). Phân vân càng nhiều thì số mẫu gấp đôi, gấp ba.']],
                     widths=['34%', '66%'])
            + _box('warn', '<b>Sai lầm nữa:</b> khách đã gửi mẫu của họ nhưng chuyên viên '
                   'lại gửi mẫu kiểu KHÁC, lệch hoàn toàn ý tưởng của khách &rarr; khách '
                   'thất vọng, thấy mình không đúng ý. Đã có mẫu của khách thì phải gửi '
                   'những mẫu GIỐNG NHẤT.')
            + _box('info', '<b>Bản chất việc gửi mẫu:</b> khách KHÔNG mua mẫu nhà &mdash; '
                   'gửi mẫu là để khách có thêm <b>ý tưởng, thêm lựa chọn</b>, chứ không '
                   'phải để khách chọn xong mẫu thì mình mới gửi báo giá.')
            + _nendont(
                ['Giúp khách chốt 1 kiểu dáng để hai bên thống nhất',
                 'Gửi 5&ndash;10 mẫu (20&ndash;30 nếu khách phân vân)',
                 'Khách có mẫu sẵn &rarr; gửi mẫu GIỐNG NHẤT',
                 'Nói rõ: làm mẫu nào giá cũng như nhau, chọn mẫu sau khi ký'],
                ['Ngồi đợi khách chốt mẫu rồi mới làm báo giá',
                 'Gửi mẫu lệch hẳn ý tưởng khách đã gửi',
                 'Ép khách phải chọn ngay 1 mẫu',
                 'Coi việc chọn mẫu là điều kiện để báo giá'])
            + _fml('Giúp khách chốt kiểu dáng &rarr; gửi mẫu (<b>5&ndash;10</b> / có mẫu '
                   'sẵn: <b>5 giống nhất</b> / phân vân: <b>20&ndash;30</b>) để khách có '
                   'ý tưởng &mdash; <b>KHÔNG chờ khách chốt mẫu mới báo giá</b>.')
            + _quiz('q1b_5',
                    'Khách chưa chọn được mẫu nhà cụ thể. Chuyên viên nên làm gì với việc báo giá?',
                    [('Đợi khách chốt xong 1 mẫu rồi mới làm báo giá', False),
                     ('Cứ gửi mẫu để khách tham khảo và VẪN làm báo giá &mdash; nói rõ mẫu nào giá cũng như nhau, chọn mẫu sau khi ký', True),
                     ('Ngừng quy trình cho đến khi khách quyết định mẫu', False),
                     ('Chỉ gửi đúng 1 mẫu và bắt khách chọn', False)],
                    'Không bao giờ chờ khách chốt mẫu mới báo giá &mdash; mẫu nào giá cũng như nhau, chọn mẫu là bước sau khi ký.'))

    # ------------------------------------------------------------------
    #  BÀI 6 - LÀM & GỬI BÁO GIÁ
    # ------------------------------------------------------------------
    def _q1b_l6(self):
        return (
            self._q1b_tag('BÀI 6 &mdash; BƯỚC ĐÍCH')
            + '<h3>Làm &amp; gửi báo giá: giãn ~2 tiếng, KHÔNG chờ đợi thêm</h3>'
            + _box('ok', 'Từ khi kết thúc cuộc gọi đến bước gửi mẫu nhà, cố gắng hoàn '
                   'thiện toàn bộ trong <b>30 phút</b>. Vì đã bấm &#8220;Chốt báo '
                   'giá&#8221; khi gác máy nên <b>file báo giá đã có sẵn</b> rồi.')
            + '<h4>&#9200; Vì sao phải GIÃN ~2 tiếng mới gửi báo giá?</h4>'
            + '<p>Không gửi file báo giá ngay lập tức. Nên giãn khoảng <b>2 tiếng</b> '
            '(tối thiểu 2 tiếng) rồi mới gửi. Nếu gửi sớm quá, khách sẽ nghĩ &#8220;dự '
            'toán cả một công trình mà làm trong mấy phút&#8221; &rarr; sinh nghi ngờ, '
            'đánh giá thiếu chuyên nghiệp.</p>'
            + _box('info', 'Trong 2 tiếng chờ đó, bạn đã hoàn tất kết bạn, tạo nhóm, gửi '
                   '4 video VTV, lời chào, tổng hợp nhu cầu, gửi mẫu nhà. Đủ 2 tiếng là '
                   'gửi báo giá &mdash; KHÔNG chờ thêm gì nữa.')
            + '<h4>&#128681; Những kiểu &#8220;chờ đợi&#8221; SAI LẦM (đều phải bỏ)</h4>'
            + _box('err', 'Không được lấy các lý do sau để trì hoãn báo giá:')
            + '<ul>'
            '<li>Đợi khách <b>chọn được mẫu nhà</b> rồi mới gửi báo giá.</li>'
            '<li>Đợi 1&ndash;2 ngày để <b>hỏi thêm một thông tin</b> còn thiếu rồi mới làm.</li>'
            '<li>Đợi khách <b>chốt kích thước chiều ngang, chiều rộng</b> (kích thước có thể chỉnh sau, không quan trọng).</li>'
            '<li>Đợi khách <b>thống nhất sổ đỏ, pháp lý</b>, hay đang phân vân <b>xây trên miếng đất nào</b>.</li>'
            '</ul>'
            + '<h4>&#9989; Chỉ cần thống nhất 3 điều này là LÀM BÁO GIÁ LUÔN</h4>'
            + _table(['Điều cần thống nhất', 'Vì sao đủ để báo giá'],
                     [['<b>Tổng diện tích trên 1 sàn</b>', 'Là cơ sở tính khối lượng &mdash; kích thước ngang/rộng lẻ có thể chỉnh sau.'],
                      ['<b>Tổng số m&#178; của cả căn nhà</b>', 'Quyết định quy mô, ra được con số tổng.'],
                      ['<b>Tầm tài chính khớp / cân đối được</b>', 'Đảm bảo báo giá nằm trong khả năng của khách.']],
                     widths=['42%', '58%'])
            + _box('warn', 'Thống nhất được 3 điều trên là <b>bắt buộc làm báo giá luôn '
                   'sau 2 tiếng</b>, kể cả khi vài thông tin khác chưa thật chính xác/đầy đủ.')
            + '<h4>&#128176; Ngoại lệ &amp; quy định ngân sách</h4>'
            + _table(['Tình huống tài chính', 'Xử lý'],
                     [['Chênh lệch tài chính <b>quá lớn</b> (khách thiếu 400&ndash;500 triệu)',
                       'Cân nhắc chưa gửi vội; liên hệ lại bàn bạc về khoản chênh trước khi làm báo giá.'],
                      ['Khách <b>thiếu khoảng 100 triệu</b> so với ngân sách công ty nhận (từ 800 triệu)',
                       'VẪN làm báo giá đầy đủ, rồi hướng khách vay mượn thêm / cố thêm.'],
                      ['Khách tài chính <b>quá nhỏ</b> (chỉ 500&ndash;600 triệu)',
                       'Bỏ qua; tài chính quá nhỏ thì có thể HỦY, không cần làm báo giá.']],
                     widths=['48%', '52%'])
            + _box('info', '<b>Vì sao báo giá quan trọng đến vậy?</b> Trong báo giá có '
                   'đầy đủ thông tin: <b>báo giá vật tư, thông tin pháp lý, hợp đồng thi '
                   'công</b> &mdash; là bộ dữ liệu then chốt gửi cho khách.')
            + _nendont(
                ['Thống nhất tổng DT/sàn + tổng m&#178; + tài chính &rarr; báo giá luôn',
                 'Giãn tối thiểu 2 tiếng rồi gửi cho tự nhiên',
                 'Thiếu ~100tr &rarr; vẫn báo giá, hướng khách xoay thêm',
                 'Tài chính quá nhỏ &rarr; mạnh dạn bỏ qua/hủy'],
                ['Đợi khách chốt mẫu / kích thước / pháp lý / miếng đất mới báo giá',
                 'Đợi 1&ndash;2 ngày hỏi thêm rồi mới làm',
                 'Gửi báo giá ngay tức thì (khách nghi làm ẩu)',
                 'Kéo báo giá sang ngày hôm sau'])
            + _fml('Báo giá đã sẵn từ lúc chốt. Thống nhất <b>tổng DT/sàn + tổng m&#178; '
                   '+ tài chính</b> &rarr; <b>GIÃN 2 TIẾNG rồi GỬI</b>. KHÔNG chờ mẫu/'
                   'kích thước/pháp lý. Thiếu ~100tr vẫn báo; quá nhỏ thì bỏ.')
            + _quiz('q1b_6',
                    'Khách đã thống nhất tổng diện tích sàn, tổng m² và tầm tài chính khớp, nhưng CHƯA chốt kích thước ngang/rộng và chưa chọn mẫu. Nên làm gì?',
                    [('Đợi khách chốt kích thước và chọn mẫu rồi mới làm báo giá', False),
                     ('Làm báo giá luôn (giãn ~2 tiếng rồi gửi) vì đã đủ 3 yếu tố cốt lõi', True),
                     ('Đợi 1&ndash;2 ngày hỏi thêm cho chắc rồi mới làm', False),
                     ('Gửi báo giá ngay lập tức không cần chờ', False)],
                    'Đủ tổng DT sàn + tổng m² + tài chính là làm báo giá luôn (giãn 2 tiếng), không chờ kích thước/mẫu.'))

    # ------------------------------------------------------------------
    #  TỔNG KẾT
    # ------------------------------------------------------------------
    def _q1b_l_gold(self):
        return (
            self._q1b_tag('&#127942; NGUYÊN TẮC VÀNG &mdash; TỔNG HỢP')
            + '<h3>Toàn bộ công thức của khóa học</h3>'
            + _box('ok', 'Một chuyên viên giỏi là người chạy TRỌN quy trình cho mỗi '
                   'khách mới trong 1 buổi, không để đứt bước nào. Cuộc gọi tư vấn chỉ '
                   'có nghĩa khi kéo được tới tận báo giá.')
            + _table(['Bước', 'Công thức thuộc lòng'],
                     [['<b>Mở đầu &mdash; Tư duy</b>', 'Cả quy trình gọn trong 1 BUỔI (4 tiếng), cùng lắm 1 ngày. Mỗi bước xong kích hoạt bước kế; không dừng chờ.'],
                      ['<b>Bài 1 &mdash; Gọi điện</b>', 'Khai thác ĐỦ thông tin; quên ý nào ĐIỀN TẠM (đường nhỏ / tháng gần nhất / 1 khách 1 bếp 3 ngủ 2 wc); gác máy là BẤM CHỐT BÁO GIÁ.'],
                      ['<b>Bài 2 &mdash; Kết bạn Zalo</b>', 'Gửi lời mời; 5 phút chưa đồng ý &rarr; GỌI NHẮC NGAY. Không kết bạn = không nhóm = không báo giá.'],
                      ['<b>Bài 3 &mdash; Tạo nhóm</b>', 'Kết bạn xong TẠO NHÓM NGAY (mình + khách + trưởng phòng), KHÔNG xin phép. CẤM nhắn cá nhân &mdash; cá nhân chỉ gọi điện.'],
                      ['<b>Bài 4 &mdash; Hoàn thiện nhóm</b>', 'Trong 10 phút: đổi tên + ảnh, 4 video VTV, lời chào, tổng hợp cuộc gọi.'],
                      ['<b>Bài 5 &mdash; Gửi mẫu nhà</b>', 'Giúp khách chốt kiểu dáng; gửi 5&ndash;10 mẫu (có mẫu sẵn: 5 giống nhất; phân vân: 20&ndash;30). KHÔNG chờ khách chốt mẫu mới báo giá.'],
                      ['<b>Bài 6 &mdash; Báo giá</b>', 'Đủ tổng DT sàn + tổng m&#178; + tài chính &rarr; GIÃN 2 TIẾNG rồi GỬI. Không chờ mẫu/kích thước/pháp lý. Thiếu ~100tr vẫn báo; quá nhỏ thì bỏ.']],
                     widths=['24%', '76%'])
            + _box('warn', 'Nguyên tắc bao trùm: <b>KHÔNG BAO GIỜ để quy trình dừng lại '
                   'chờ đợi.</b> Thiếu thông tin thì điền tạm; khách chưa quyết thì vẫn '
                   'đi tiếp. Gọi điện xong 2&ndash;3 ngày chưa có báo giá là thất bại.')
            + _quiz('q1b_gold',
                    'Đâu là nguyên tắc bao trùm toàn bộ khóa học này?',
                    [('Càng làm chậm, kỹ càng thì khách càng tin tưởng', False),
                     ('Không để quy trình dừng chờ đợi &mdash; thiếu thông tin thì điền tạm, khách chưa quyết vẫn đi tiếp, hoàn tất trong 1 buổi', True),
                     ('Chỉ cần gọi điện tốt là đủ, các bước sau không quan trọng', False),
                     ('Luôn chờ khách chốt mọi thứ rồi mới báo giá cho chắc', False)],
                    'Cốt lõi: chạy trọn quy trình trong 1 buổi, tuyệt đối không dừng chờ đợi.'))

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (bài THI chấm điểm)
    # ==================================================================
    def _q1b_questions(self):
        T, F = True, False
        return [
            ('Toàn bộ quy trình từ gọi điện lần đầu đến gửi báo giá phải hoàn tất trong bao lâu?',
             [('Trong 1 buổi (khoảng 4 tiếng), cùng lắm là 1 ngày', T),
              ('Trong khoảng 1 tuần', F),
              ('Trong 1 tháng', F),
              ('Bao lâu cũng được, miễn khách chốt mẫu', F)]),

            ('Nguyên tắc bao trùm khi một bước trong quy trình gặp trục trặc là gì?',
             [('Điền tạm / đi tiếp để KHÔNG dừng quy trình chờ đợi', T),
              ('Dừng lại chờ cho tới khi có đủ thông tin chính xác', F),
              ('Hủy khách và chuyển sang khách khác', F),
              ('Chờ khách chủ động liên hệ lại', F)]),

            ('Khi gọi điện tư vấn lần đầu, nên trao đổi với khách thế nào?',
             [('Trao đổi càng lâu càng tốt, khai thác ĐỦ thông tin để sinh được báo giá', T),
              ('Hỏi thật nhanh vài ý quen thuộc rồi cúp máy', F),
              ('Chỉ hỏi tài chính là đủ', F),
              ('Để khách nói, mình không cần hỏi gì thêm', F)]),

            ('Lỡ quên hỏi khách đường to hay đường nhỏ khi làm báo giá thì chọn tạm gì?',
             [('Chọn ĐƯỜNG NHỎ để phần mềm vẫn sinh được báo giá', T),
              ('Chọn đường to cho an toàn', F),
              ('Bỏ trống, không chọn', F),
              ('Dừng lại gọi hỏi khách ngay', F)]),

            ('Quên hỏi thời gian khởi công thì điền tạm phương án nào?',
             [('Chọn tháng khởi công GẦN NHẤT', T),
              ('Chọn tháng xa nhất trong năm', F),
              ('Để trống mục thời gian', F),
              ('Chọn đúng tháng hiện tại bắt buộc', F)]),

            ('Quên hỏi công năng thì điền tạm công năng ví dụ nào?',
             [('1 phòng khách + 1 bếp + 3 phòng ngủ + 2 WC', T),
              ('Nhà 1 phòng duy nhất', F),
              ('10 phòng ngủ cho chắc', F),
              ('Không điền, để phần mềm tự đoán', F)]),

            ('Ngay khi kết thúc cuộc gọi tư vấn, việc BẮT BUỘC phải làm là gì?',
             [('Bấm nút "Chốt báo giá" để phần mềm sinh file báo giá và tên nhóm Zalo mới', T),
              ('Nhắn tin Zalo cá nhân cảm ơn khách', F),
              ('Chờ 1 ngày rồi mới xử lý', F),
              ('Gọi lại khách ngay để hỏi thêm', F)]),

            ('Sau khi gửi lời mời kết bạn Zalo mà 5 phút khách chưa đồng ý, phải làm gì?',
             [('Gọi điện lại nhắc khách đồng ý kết bạn ngay lập tức', T),
              ('Chờ vài ngày xem khách có tự đồng ý không', F),
              ('Nhắn SMS xin thông tin để làm báo giá luôn', F),
              ('Bỏ qua khách này', F)]),

            ('Vì sao kết bạn Zalo là mắt xích sống còn?',
             [('Không kết bạn thì không tạo được nhóm, không gọi Zalo, không gửi được báo giá', T),
              ('Vì để lưu số điện thoại khách', F),
              ('Vì công ty yêu cầu đủ số bạn bè Zalo', F),
              ('Vì để nhắn tin cá nhân cho tiện', F)]),

            ('Báo giá được phép gửi cho khách qua kênh nào?',
             [('BẮT BUỘC gửi trong NHÓM; cấm gửi qua tin nhắn cá nhân', T),
              ('Gửi qua tin nhắn Zalo cá nhân cho nhanh', F),
              ('Gửi qua email cá nhân của nhân viên', F),
              ('Gửi kiểu nào cũng được', F)]),

            ('Nhóm Zalo tạo cho khách gồm tối thiểu những ai?',
             [('Chuyên viên tư vấn + khách hàng + trưởng phòng', T),
              ('Chỉ chuyên viên và khách hàng', F),
              ('Chuyên viên, khách hàng và kế toán', F),
              ('Chuyên viên, khách hàng và giám đốc', F)]),

            ('Khi tạo nhóm Zalo với khách, có cần xin phép khách không?',
             [('KHÔNG xin phép &mdash; mặc định tạo nhóm luôn (xin phép thì khách sẽ từ chối)', T),
              ('Phải xin phép, khách đồng ý mới tạo', F),
              ('Hỏi ý trưởng phòng trước, không cần hỏi khách', F),
              ('Chờ khách đề nghị lập nhóm mới tạo', F)]),

            ('Khách chủ động nhắn tin vào Zalo cá nhân của bạn để hỏi. Xử lý đúng?',
             [('Vẫn tạo nhóm và trả lời câu hỏi TRÊN NHÓM để lái khách lên nhóm', T),
              ('Trả lời luôn trên Zalo cá nhân cho tiện', F),
              ('Gửi báo giá qua tin nhắn cá nhân', F),
              ('Không trả lời gì cả', F)]),

            ('Với khách, Zalo CÁ NHÂN của nhân viên chỉ được dùng để làm gì?',
             [('Chỉ để GỌI ĐIỆN, không được nhắn tin trao đổi', T),
              ('Nhắn tin mọi thông tin cho tiện', F),
              ('Gửi báo giá và hợp đồng riêng', F),
              ('Chốt hợp đồng riêng với khách', F)]),

            ('Sau khi tạo nhóm xong, trong 10 phút phải làm những việc gì?',
             [('Đổi tên + đổi ảnh nhóm, gửi 4 video VTV, gửi lời chào, gửi tổng hợp thông tin cuộc gọi', T),
              ('Chỉ đổi tên nhóm', F),
              ('Chờ khách nhắn trước rồi mới làm', F),
              ('Gửi ngay báo giá cho nhanh', F)]),

            ('Vì sao phải gửi đầy đủ nội dung vào nhóm ngay (không để 1-2 ngày sau)?',
             [('Vì đó là thông tin để khách đánh giá sự chuyên nghiệp; gửi muộn thì vô duyên, lệch thời điểm', T),
              ('Vì công ty phạt tiền nếu gửi muộn', F),
              ('Vì Zalo sẽ tự xóa nhóm', F),
              ('Vì khách sẽ rời nhóm ngay', F)]),

            ('Khách chưa chọn được mẫu nhà. Chuyên viên nên xử lý việc báo giá thế nào?',
             [('Cứ gửi mẫu tham khảo và VẪN làm báo giá; nói rõ mẫu nào giá cũng như nhau, chọn mẫu là bước sau khi ký', T),
              ('Đợi khách chốt xong 1 mẫu rồi mới báo giá', F),
              ('Ngừng quy trình đến khi khách quyết mẫu', F),
              ('Bắt khách chọn ngay 1 mẫu', F)]),

            ('Khách đã tự gửi mẫu nhà của họ cho bạn. Nên gửi lại mẫu thế nào?',
             [('Gửi khoảng 5 mẫu GIỐNG NHẤT với mẫu của khách; không tìm được mẫu giống thì thôi không gửi', T),
              ('Gửi mẫu kiểu khác cho khách có lựa chọn mới lạ', F),
              ('Gửi 30 mẫu đủ mọi phong cách', F),
              ('Không gửi và ép khách theo mẫu công ty', F)]),

            ('Khách chưa biết chọn kiểu nhà nào (đang phân vân nhiều). Nên gửi bao nhiêu mẫu?',
             [('Gửi 20-30 mẫu gồm cả các kiểu khách phân vân (vd 10 Nhật + 10 Thái); phân vân nhiều thì gấp đôi gấp ba', T),
              ('Chỉ gửi đúng 1 mẫu đẹp nhất', F),
              ('Không gửi mẫu nào cả', F),
              ('Gửi 2 mẫu cho khách đỡ rối', F)]),

            ('Sau khi đã bấm chốt báo giá, nên gửi file báo giá cho khách khi nào?',
             [('Giãn tối thiểu ~2 tiếng rồi mới gửi, để khách không nghĩ báo giá làm ẩu trong vài phút', T),
              ('Gửi ngay lập tức khi vừa chốt', F),
              ('Đợi 2-3 ngày cho chắc chắn', F),
              ('Chỉ gửi khi khách đã chốt mẫu và kích thước', F)]),
        ]
