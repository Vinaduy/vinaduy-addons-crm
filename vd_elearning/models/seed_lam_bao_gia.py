# -*- coding: utf-8 -*-
"""Seed nội dung + bài thi cho khóa "LÀM BÁO GIÁ" (Kỹ năng Sale).

Chèn NGAY SAU khóa "Quy trình xử lý khách mới trong 1 buổi" (Tạo nhóm - Báo giá):
khóa 1 buổi dừng ở bước gửi mẫu nhà, khóa này chuyên sâu về NGHỆ THUẬT ĐIỀU PHỐI
BÁO GIÁ theo Quy trình lai 4 bước "Thả con săn sắt, bắt con cá mập":
  Bước 1: Gọi điện lọc nhu cầu & sàng lọc tài chính
  Bước 2: Tạo nhóm Zalo & gửi BÁO GIÁ KHÁI TOÁN (không gửi file chi tiết)
  Bước 3: Giáo dục khách bằng hình ảnh thực tế -> đẩy thiện chí lên 70%
  Bước 4: Dùng file báo giá chi tiết làm "mồi nhử" để CHỐT CUỘC HẸN trực tiếp

GIAO DIỆN giống khóa "Tạo nhóm + Làm báo giá" (menu trái chọn từng bài kiểu
Streamlit + hộp màu + câu mẫu + quiz chấm đúng/sai tức thì thuần CSS input:checked,
KHÔNG JS). vd_body sanitize=False + render markup() nên HTML thô giữ nguyên.

Helper nối chuỗi (+) -> tránh bẫy %. MỌI class method dùng prefix RIÊNG _lbg_ để
KHÔNG trùng tên với seed khác (xem reference-seed-method-name-collision).
Idempotent theo version lưu ở ir.config_parameter.
"""
from odoo import api, models

_LBG_VERSION = 'v1-hybrid-4-steps'
_PARAM_KEY = 'vd_elearning.lam_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-lbg{font-size:16px;line-height:1.7;color:#1f2937;'
    'width:96vw;max-width:1720px;position:relative;left:50%;transform:translateX(-50%);'
    'margin-top:-1.3cm;}'
    '.vd-lbg .vd-course{background:linear-gradient(180deg,#fff7f3 0%,#f5faff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-lbg h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-lbg h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-lbg p{margin:0 0 10px;}'
    '.vd-lbg ul,.vd-lbg ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-lbg li{margin:5px 0;}'
    '.vd-lbg b{color:#111827;}'
    '.vd-lbg table{border-collapse:collapse;width:100%;margin:8px 0 6px;font-size:15px;}'
    '.vd-lbg th,.vd-lbg td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-lbg th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-lbg .thok{background:#dcfce7;color:#15803d;}'
    '.vd-lbg .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-lbg .no{color:#b91c1c;font-weight:700;}'
    '.vd-lbg .yes{color:#15803d;font-weight:700;}'
    '.vd-lbg .navr,.vd-lbg .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-lbg .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-lbg .vc-side{flex:0 0 300px;}'
    '.vd-lbg .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-lbg .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-lbg .vc-navbtn:hover{background:#fff5f1;border-color:#ffd9c9;color:#e8401f;}'
    '.vd-lbg .vc-nbadge{flex:0 0 auto;display:inline-block;background:#fff1ec;color:#e8401f;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-lbg .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;white-space:nowrap;}'
    '.vd-lbg .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-lbg .vc-panel{display:none;}'
    '.vd-lbg .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#e8401f;background:#fff1ec;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-lbg .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:9px 0;}'
    '.vd-lbg .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-lbg .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-lbg .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-lbg .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # công thức
    '.vd-lbg .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:10px 0;}'
    '.vd-lbg .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-lbg .fml .fml-b{color:#4c1d95;font-weight:600;}'
    # câu mẫu (script)
    '.vd-lbg .say{background:#ecfeff;border:2px dashed #22d3ee;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#155e75;font-style:italic;}'
    '.vd-lbg .say .sh{font-style:normal;font-weight:800;color:#0e7490;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:4px;}'
    # thứ tự đánh số
    '.vd-lbg .vc-order{margin:12px 0;border:1px solid #ffd9c9;border-radius:12px;overflow:hidden;}'
    '.vd-lbg .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #ffe3d6;background:#fffaf7;}'
    '.vd-lbg .vc-ostep:last-child{border-bottom:none;}'
    '.vd-lbg .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#e8401f;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-lbg .vc-ot{font-weight:800;color:#7c2d12;}'
    '.vd-lbg .vc-od{color:#9a3412;font-size:14.5px;}'
    # flow (dòng chảy 4 bước)
    '.vd-lbg .flow{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin:12px 0;}'
    '.vd-lbg .flow .fstep{flex:1 1 200px;background:#fff7ed;border:2px solid #fed7aa;'
    'border-radius:12px;padding:12px 14px;position:relative;}'
    '.vd-lbg .flow .fstep b{color:#c2410c;display:block;margin-bottom:3px;}'
    '.vd-lbg .flow .fstep span{font-size:14px;color:#7c2d12;}'
    # quiz
    '.vd-lbg .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
    '.vd-lbg .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-lbg .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-lbg .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-lbg .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-lbg .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-lbg .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-lbg .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-lbg .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-lbg .vc-layout{flex-direction:column;}'
    '.vd-lbg .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-lbg .vc-sidehead{width:100%;}'
    '.vd-lbg .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
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


def _flow(steps):
    out = '<div class="flow">'
    for t, d in steps:
        out += '<div class="fstep"><b>' + t + '</b><span>' + d + '</span></div>'
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


class SlideChannelSeedLamBaoGia(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_lam_bao_gia(self):
        ch = self.env.ref('vd_elearning.course_lam_bao_gia',
                          raise_if_not_found=False)
        if not ch:
            ch = self.sudo().search([('name', '=', 'Làm báo giá')], limit=1)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _LBG_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-lbg" style="%s">%s</div>'
                                 % (_WRAP, self._lbg_app())),
            'sequence': 1, 'is_published': True,
        })

        questions = self._lbg_questions()
        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - %d câu' % len(questions),
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in questions:
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _LBG_VERSION)
        return True

    # ==================================================================
    #  APP (menu trái + panel phải)
    # ==================================================================
    def _lbg_app(self):
        lessons = self._lbg_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'lbgL' + str(i)
            pid = 'lbgP' + str(i)
            radios += ('<input class="navr" type="radio" name="lbgnav" id="' + rid + '"'
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
            'KỸ NĂNG SALE &mdash; NGHỆ THUẬT ĐIỀU PHỐI BÁO GIÁ</div>'
            '<div style="color:#fff;font-size:26px;font-weight:900;margin-top:6px;line-height:1.2;'
            'text-shadow:0 2px 8px rgba(0,0,0,.15);">'
            'Làm báo giá: Thả con săn sắt &rarr; bắt con cá mập</div>'
            '<div style="color:#fff8f4;font-size:14.5px;margin-top:9px;">'
            '&#127907; Cho khách biết GIÁ để họ an tâm, nhưng GIỮ file chi tiết để ép khách '
            'phải gặp mặt. &#128073; Bấm từng mục ở MENU BÊN TRÁI để học lần lượt &mdash; '
            'mỗi bài có trắc nghiệm chấm ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _lbg_tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    def _lbg_lessons(self):
        return [
            ('&#129504;', 'MỞ ĐẦU', 'Tư duy & 2 sai lầm', self._lbg_l_open()),
            ('&#128222;', 'BƯỚC 1', 'Gọi lọc nhu cầu & tài chính', self._lbg_l1()),
            ('&#128172;', 'BƯỚC 2', 'Gửi báo giá khái toán', self._lbg_l2()),
            ('&#128248;', 'BƯỚC 3', 'Nuôi thiện chí bằng hình ảnh', self._lbg_l3()),
            ('&#127907;', 'BƯỚC 4', 'File chi tiết làm mồi nhử', self._lbg_l4()),
            ('&#127942;', 'TỔNG KẾT', 'Công thức & thực hành', self._lbg_l_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỞ ĐẦU
    # ------------------------------------------------------------------
    def _lbg_l_open(self):
        return (
            self._lbg_tag('TƯ DUY NỀN TẢNG')
            + '<h3>Đừng biến mình thành "cỗ máy làm báo giá miễn phí"</h3>'
            + _box('ok', 'Trong ngành xây nhà trọn gói, sai lầm lớn nhất của một Sale non '
                   'tay là biến mình thành <b>"cỗ máy làm báo giá miễn phí"</b> cho thị '
                   'trường. Khóa này giúp bạn làm chủ <b>Quy trình lai 4 bước</b> để '
                   '<b>nắm đằng chuôi</b> trong mọi cuộc đàm phán.')
            + '<p>Trước khi học phương pháp mới, phải nhìn thẳng vào <b>2 sai lầm thực '
            'tế</b> mà anh em Sale hay mắc &mdash; hiểu vì sao chúng khiến ta mất khách '
            'thì mới thấm được vì sao phải làm khác đi.</p>'

            + '<h4>&#128680; SAI LẦM 1 &mdash; Gửi báo giá CHI TIẾT quá nhanh</h4>'
            + _box('err', 'Khách vừa gọi, mình làm ngày đêm, 2&ndash;3 tiếng sau gửi ngay '
                   'một file Excel chi tiết (từ danh mục vật tư đến phụ lục hợp đồng) và '
                   'nghĩ thế là chuyên nghiệp. Nhưng thực tế: <b>khách xem xong rồi im lặng.</b>')
            + '<ul>'
            '<li><b>Vì sao họ im lặng?</b> Dù tài chính rất khớp với bảng giá, họ vẫn im '
            'vì đã có trong tay "vũ khí" của bạn. Họ dùng chính file Excel chi tiết đó gửi '
            'cho 3&ndash;4 nhà thầu khác: <i>"Bên kia báo thế này, ông làm rẻ hơn được không?"</i></li>'
            '<li><b>Hậu quả:</b> bạn bị <b>"cắt cầu"</b> hoặc bị kéo vào cuộc chiến phá '
            'giá. Mất cơ hội giải thích vì sao thanh thép này đắt hơn, loại sơn kia tốt '
            'hơn. Bạn tự biến mình thành một lựa chọn <b>thuần túy về con số</b>.</li>'
            '</ul>'

            + '<h4>&#128680; SAI LẦM 2 &mdash; Giấu giá quá lâu, nhắn tin suông</h4>'
            + _box('err', 'Sợ rủi ro ở sai lầm 1, nhiều bạn chuyển sang cực đoan ngược '
                   'lại: tạo nhóm Zalo, nhắn tin dông dài về vật tư, <b>giấu nhẹm</b> con '
                   'số, đợi khi cảm thấy khách thiện chí 70% mới chịu cho biết giá.')
            + '<ul>'
            '<li><b>Rủi ro:</b> khách bỏ ra hàng tỷ đồng, họ cần <b>sự an toàn và minh '
            'bạch</b>. Nhắn thao thao mà không cho một con số cụ thể, họ nghĩ bạn <b>mập '
            'mờ, thiếu năng lực</b> hoặc đang "nhìn mặt bắt hình dong" để hét giá.</li>'
            '<li><b>Hậu quả:</b> khách <b>rời nhóm</b> vì mệt mỏi và thấy tốn thời gian.</li>'
            '</ul>'

            + '<h4>&#128202; BẢNG SO SÁNH 2 TRƯỜNG HỢP</h4>'
            + _table(['Tiêu chí', 'TH1: Gửi chi tiết ngay', 'TH2: Giấu giá, nhắn suông'],
                     [['<b>Tốc độ phản hồi</b>', 'Cực nhanh, có vẻ chuyên nghiệp', 'Chậm, cần thời gian xây niềm tin'],
                      ['<b>Rủi ro rò rỉ dữ liệu</b>', '<span class="no">Rất cao</span> &mdash; khách rải đinh so giá', '<span class="yes">Rất thấp</span> &mdash; giữ được phụ lục vật tư'],
                      ['<b>Tỷ lệ khách "im lặng"</b>', '<span class="no">Rất lớn</span> &mdash; xem xong đi dò giá', '<span class="yes">Thấp</span> &mdash; khách phải tương tác mới có thông tin'],
                      ['<b>Kiểm soát cuộc chơi</b>', '<span class="no">Mất</span> &mdash; quyền chủ động sang khách', '<span class="yes">Cao</span> &mdash; mình dẫn dắt từng bước'],
                      ['<b>Khả năng chốt HĐ</b>', 'Thấp &mdash; dễ sa vào cuộc chiến giá', 'Cao &mdash; chỉ khách thiện chí đi đến cuối']],
                     widths=['22%', '39%', '39%'])

            + '<h4>&#127907; TRIẾT LÝ: "Thả con săn sắt, bắt con cá mập"</h4>'
            + _box('ok', '<b>Quy trình lai</b> đúc kết ưu điểm của CẢ hai: vẫn cho khách '
                   'biết giá nhanh để họ không sốt ruột (ưu điểm TH1), nhưng <b>giấu file '
                   'chi tiết</b> để tạo nhóm tương tác và sàng lọc thiện chí (ưu điểm TH2). '
                   'Nói gọn: <b>cho khách biết GIÁ để an tâm, GIỮ file chi tiết để ép khách '
                   'phải gặp mặt.</b>')
            + _flow([
                ('BƯỚC 1', 'Gọi điện lọc nhu cầu & sàng lọc tài chính'),
                ('BƯỚC 2', 'Gửi BÁO GIÁ KHÁI TOÁN qua Zalo (sau 1&ndash;2h)'),
                ('BƯỚC 3', 'Gửi hình ảnh thực tế &rarr; đẩy thiện chí lên 70%'),
                ('BƯỚC 4', 'Dùng file chi tiết làm "mồi nhử" chốt cuộc hẹn'),
            ])
            + _fml('Không gửi file chi tiết ngay (tránh bị "cắt cầu", so giá) &mdash; nhưng '
                   'cũng KHÔNG giấu giá quá lâu (tránh mất kiên nhẫn). <b>Gửi KHÁI TOÁN '
                   'sớm để giữ khách, giữ CHI TIẾT để ép gặp mặt.</b>')
            + _quiz('lbg_open',
                    'Vì sao gửi file báo giá CHI TIẾT cho khách quá sớm lại nguy hiểm?',
                    [('Khách dùng chính file đó đi so giá 3-4 nhà thầu khác, mình bị "cắt cầu" và cuốn vào cuộc chiến phá giá', True),
                     ('Vì làm file chi tiết rất mất thời gian của nhân viên', False),
                     ('Vì khách sẽ đòi giảm giá ngay lập tức trong cùng ngày', False),
                     ('Vì phần mềm CRM không cho phép gửi file sớm', False)],
                    'File chi tiết bị khách mang đi rải đinh so giá &mdash; mình tự biến thành một lựa chọn thuần về con số.'))

    # ------------------------------------------------------------------
    #  BƯỚC 1 - GỌI LỌC NHU CẦU & TÀI CHÍNH
    # ------------------------------------------------------------------
    def _lbg_l1(self):
        return (
            self._lbg_tag('BƯỚC 1 &mdash; THIẾT LẬP RANH GIỚI TÀI CHÍNH')
            + '<h3>Cuộc gọi đầu tiên: khai thác nhu cầu & đo lường túi tiền</h3>'
            + _box('ok', 'Khi nhận data khách, nhiệm vụ trong <b>5 phút đầu</b> KHÔNG phải '
                   'là thao thao bất tuyệt về công ty, mà là <b>khai thác thông tin</b> và '
                   '<b>đo lường tài chính</b> để làm được báo giá khớp túi tiền.')
            + '<h4>&#128269; Hỏi RÕ nhu cầu</h4>'
            + '<ul>'
            '<li><b>Diện tích đất</b>, <b>số tầng</b> dự kiến.</li>'
            '<li><b>Phong cách</b> (hiện đại, tân cổ điển&hellip;).</li>'
            '<li><b>Số lượng thành viên</b> ở &rarr; suy ra công năng, số phòng.</li>'
            '</ul>'
            + '<h4>&#128176; Hỏi KHÉO tài chính (đừng hỏi thô)</h4>'
            + _box('err', 'TUYỆT ĐỐI không hỏi trắng phớ <i>"Anh có bao nhiêu tiền?"</i> '
                   '&mdash; khách thấy bị dò xét, mất thiện cảm.')
            + _say('&#8220;Dạ anh/chị dự kiến tích lũy ngân sách khoảng bao nhiêu cho phần '
                   'xây thô và hoàn thiện, để em chọn <b>phân khúc vật tư tối ưu nhất</b> '
                   'cho mình ạ?&#8221;')
            + '<p>Cách hỏi này biến câu "moi tiền" thành câu "vì lợi ích của khách" &mdash; '
            'khách trả lời tự nhiên hơn nhiều.</p>'
            + '<h4>&#128204; Chốt hạ cuộc gọi để mở đường tạo nhóm</h4>'
            + _say('&#8220;Em đã nắm rõ nhu cầu của anh/chị. Khoảng <b>1 tiếng</b> nữa em '
                   'lập nhóm Zalo để gửi anh/chị <b>Bảng ước lượng khoảng giá (báo giá '
                   'khái toán)</b> cùng vài mẫu nhà tương tự để tham khảo trước nhé.&#8221;')
            + _box('info', '<b>Vì sao phải chốt câu này?</b> Nó tạo <b>lý do chính đáng</b> '
                   'để kết bạn và lập nhóm ở bước sau, đồng thời đặt kỳ vọng đúng: khách '
                   'sẽ nhận KHÁI TOÁN (khoảng giá), không phải file chi tiết.')
            + _nendont(
                ['Hỏi đủ: diện tích, số tầng, phong cách, số người ở',
                 'Hỏi khéo tài chính theo hướng "chọn vật tư tối ưu cho anh"',
                 'Chốt hẹn ~1h nữa lập nhóm gửi KHÁI TOÁN'],
                ['Nói thao thao về công ty, quên khai thác nhu cầu',
                 'Hỏi thô "anh có bao nhiêu tiền"',
                 'Hứa gửi ngay "báo giá chi tiết" (sai kỳ vọng)'])
            + _fml('Cuộc gọi đầu = <b>Khai thác nhu cầu</b> (đất/tầng/phong cách/số người) '
                   '+ <b>đo tài chính khéo</b> (chọn vật tư tối ưu) &rarr; chốt hẹn '
                   '<b>~1h nữa lập nhóm gửi KHÁI TOÁN</b>.')
            + _quiz('lbg_1',
                    'Cách hỏi tài chính khéo léo nhất với khách xây nhà là gì?',
                    [('"Anh/chị dự kiến ngân sách khoảng bao nhiêu để em chọn phân khúc vật tư tối ưu nhất ạ?"', True),
                     ('"Anh có bao nhiêu tiền để xây?"', False),
                     ('Không hỏi tài chính, cứ làm báo giá cao nhất rồi tính sau', False),
                     ('"Anh vay được ngân hàng bao nhiêu?"', False)],
                    'Hỏi tài chính theo hướng "để chọn vật tư tối ưu cho khách" &mdash; khách trả lời tự nhiên, không thấy bị dò xét.'))

    # ------------------------------------------------------------------
    #  BƯỚC 2 - GỬI BÁO GIÁ KHÁI TOÁN
    # ------------------------------------------------------------------
    def _lbg_l2(self):
        return (
            self._lbg_tag('BƯỚC 2 &mdash; GIẢI TỎA GIÁ MÀ KHÔNG LỘ FILE')
            + '<h3>Tạo nhóm Zalo & gửi "Báo giá khái toán" (sau 1&ndash;2 tiếng)</h3>'
            + _box('err', '<b>TUYỆT ĐỐI không</b> gửi file Excel có phụ lục vật tư chi '
                   'tiết ở bước này. Chỉ gửi một <b>Bảng tổng hợp chi phí dự kiến</b> viết '
                   'bằng tin nhắn văn bản hoặc ảnh chụp bảng tính tổng.')
            + '<h4>&#128241; Ai vào nhóm?</h4>'
            + '<p>Tạo nhóm gồm: <b>bạn + khách hàng</b>, có thể thêm <b>vợ/chồng khách</b> '
            'và <b>kiến trúc sư</b> của bạn để tăng độ uy tín.</p>'
            + '<h4>&#128172; Mẫu tin nhắn BẮT BUỘC gửi khái toán</h4>'
            + _say('&#8220;Chào anh/chị, dựa trên nhu cầu xây nhà quy mô <b>[số tầng]</b> '
                   'tầng, diện tích <b>[số m&#178;]</b>, em gửi anh/chị khoảng giá dự kiến:<br>'
                   '&bull; Phần thô + Nhân công: &hellip; VNĐ<br>'
                   '&bull; Phần hoàn thiện (gói khá &ndash; tốt): &hellip; VNĐ<br>'
                   '&bull; <b>Tổng ngân sách dự kiến: từ [mức thấp] đến [mức cao] VNĐ.</b><br>'
                   'Gói này bên em cam kết <b>chìa khóa trao tay, không phát sinh</b> ạ.&#8221;')
            + _box('ok', '<b>Vì sao khái toán lại lợi hại?</b> Con số này giúp khách '
                   '<b>giải tỏa thắc mắc về giá</b>, thấy khớp tài chính &mdash; nhưng '
                   '<b>KHÔNG thể mang đi ép giá</b> nhà thầu khác, vì nó làm gì có chi tiết '
                   'vật tư để bóc tách!')
            + '<h4>&#9200; Vì sao giãn 1&ndash;2 tiếng mới gửi?</h4>'
            + '<p>Gửi ngay lập tức khiến khách nghĩ <i>"dự toán cả công trình mà làm mấy '
            'phút"</i> &rarr; sinh nghi ngờ. Giãn 1&ndash;2 tiếng cho <b>tự nhiên và '
            'chuyên nghiệp</b> hơn.</p>'
            + _nendont(
                ['Gửi bảng TỔNG HỢP khoảng giá bằng tin nhắn / ảnh chụp',
                 'Nêu rõ "chìa khóa trao tay, không phát sinh"',
                 'Giãn 1-2 tiếng rồi mới gửi cho tự nhiên'],
                ['Gửi file Excel có phụ lục vật tư chi tiết',
                 'Gửi bảng có bóc tách đơn giá từng hạng mục',
                 'Gửi ngay tức thì khiến khách nghi làm ẩu'])
            + _fml('Bước 2 = <b>Tạo nhóm</b> &rarr; sau 1&ndash;2h gửi <b>KHÁI TOÁN</b> '
                   '(chỉ TỔNG khoảng giá + "chìa khóa trao tay"), <b>KHÔNG file chi '
                   'tiết</b>. Khách an tâm về giá nhưng không có gì để đi so.')
            + _quiz('lbg_2',
                    'Ở bước 2 (tạo nhóm), nên gửi cho khách cái gì?',
                    [('Bảng tổng hợp KHOẢNG GIÁ dự kiến (khái toán) bằng tin nhắn/ảnh, không kèm phụ lục vật tư chi tiết', True),
                     ('File Excel chi tiết đầy đủ đơn giá và phụ lục vật tư', False),
                     ('Chưa gửi gì cả, đợi khách hỏi giá mới gửi', False),
                     ('Hợp đồng thi công để khách ký luôn', False)],
                    'Chỉ gửi khái toán (tổng khoảng giá) &mdash; giải tỏa giá cho khách nhưng không cho họ file chi tiết để đi so.'))

    # ------------------------------------------------------------------
    #  BƯỚC 3 - NUÔI THIỆN CHÍ BẰNG HÌNH ẢNH
    # ------------------------------------------------------------------
    def _lbg_l3(self):
        return (
            self._lbg_tag('BƯỚC 3 &mdash; GIÁO DỤC KHÁCH, KHÔNG NHẮN SUÔNG')
            + '<h3>Nuôi dưỡng trên nhóm: nói chuyện bằng BẰNG CHỨNG trực quan</h3>'
            + _box('ok', 'Sau khi gửi khái toán, khách sẽ hỏi sâu hơn về vật tư. Đây là '
                   'lúc áp dụng kỹ thuật của TH2 nhưng <b>nâng cấp lên</b>: không nhắn tin '
                   'suông, hãy <b>nói chuyện bằng bằng chứng trực quan</b>.')
            + '<h4>&#128248; Khách hỏi thép, xi măng, gạch &rarr; gửi HÌNH ẢNH thật</h4>'
            + '<p>Đừng chỉ gõ chữ. Hãy gửi ngay <b>hình ảnh, video thực tế</b> bạn hoặc kỹ '
            'sư đang <b>nghiệm thu cốt thép</b>, đổ bê tông tại công trình của công ty.</p>'
            + _say('&#8220;Dạ anh/chị xem, đây là hình ảnh thực tế bên em đổ bê tông cho '
                   'nhà anh A tuần trước. Bên em dùng hoàn toàn <b>ống nhựa loại 1</b> và '
                   '<b>dây điện chống cháy</b>, có giấy kiểm định rõ ràng &mdash; lát nữa '
                   'em chụp giấy gửi vào nhóm mình xem nhé.&#8221;')
            + '<h4>&#127891; Biến mình thành CHUYÊN GIA tư vấn</h4>'
            + '<p>Chia sẻ kinh nghiệm làm nhà: lưu ý khi làm móng, chống thấm&hellip; Biến '
            'mình thành người tư vấn <b>tận tâm</b>, chứ không phải người bán hàng bản năng. '
            'Giá trị được xây <b>TRƯỚC</b> khi khách nhìn thấy con số chi tiết.</p>'
            + '<h4>&#128064; Dấu hiệu khách đạt 70% thiện chí</h4>'
            + _box('info', 'Khi khách bắt đầu hỏi những câu sau &rarr; lập tức chuyển sang '
                   'Bước 4:')
            + '<ul>'
            '<li>Hỏi về <b>tiến độ thanh toán</b>, dòng tiền.</li>'
            '<li>Hỏi <b>thời gian thi công</b> mất bao lâu.</li>'
            '<li>Nhờ tư vấn kỹ hơn về <b>phong thủy, hướng bếp</b>.</li>'
            '</ul>'
            + _nendont(
                ['Gửi ảnh/video nghiệm thu thực tế thay vì nhắn suông',
                 'Kèm bằng chứng: giấy kiểm định, vật tư loại 1',
                 'Chia sẻ kinh nghiệm để thành chuyên gia tận tâm',
                 'Bắt tín hiệu 70% (hỏi tiến độ/thời gian/phong thủy)'],
                ['Chỉ gõ chữ giải thích vật tư, không hình ảnh',
                 'Đổ một lúc hết mọi thông tin rồi im',
                 'Bỏ lỡ tín hiệu thiện chí, không chuyển bước 4',
                 'Gửi file chi tiết ngay khi khách vừa hỏi sâu'])
            + _fml('Bước 3 = <b>Giáo dục bằng HÌNH ẢNH/VIDEO thật</b> (nghiệm thu, vật tư '
                   'loại 1, giấy kiểm định) + tư vấn như chuyên gia. Chờ tín hiệu <b>70% '
                   'thiện chí</b> (hỏi tiến độ/thời gian/phong thủy) &rarr; sang Bước 4.')
            + _quiz('lbg_3',
                    'Đâu là dấu hiệu khách đã đạt khoảng 70% thiện chí để chuyển sang chốt hẹn?',
                    [('Khách hỏi về tiến độ thanh toán, thời gian thi công, hoặc nhờ tư vấn phong thủy/hướng bếp', True),
                     ('Khách xem tin nhắn rồi không trả lời', False),
                     ('Khách hỏi giá rẻ hơn được không', False),
                     ('Khách bảo để suy nghĩ thêm rồi im lặng', False)],
                    'Khách hỏi tiến độ/thời gian thi công/phong thủy = đã hình dung mình sống trong nhà đó &rarr; đủ chín để chốt hẹn.'))

    # ------------------------------------------------------------------
    #  BƯỚC 4 - FILE CHI TIẾT LÀM MỒI NHỬ
    # ------------------------------------------------------------------
    def _lbg_l4(self):
        return (
            self._lbg_tag('BƯỚC 4 &mdash; BƯỚC QUYẾT ĐỊNH')
            + '<h3>Dùng file báo giá chi tiết làm "mồi nhử" để CHỐT HẸN</h3>'
            + _box('err', '<b>Nguyên tắc thép:</b> KHÔNG BAO GIỜ gửi file báo giá chi tiết '
                   'qua Zalo. File chi tiết là <b>phần thưởng</b>, và khách phải "trả giá" '
                   'bằng một <b>cuộc hẹn trực tiếp</b> để có được nó.')
            + '<h4>&#127907; Vì sao file chi tiết là "mồi nhử"?</h4>'
            + '<p>Đây là thứ khách MUỐN nhất (bản dự toán từng hạng mục, phụ lục vật tư '
            'chính xác). Nếu gửi qua Zalo, bạn mất luôn con bài cuối cùng để kéo khách ra '
            'khỏi màn hình điện thoại. Giữ nó lại &rarr; khách buộc phải <b>gặp mặt</b> '
            '&mdash; nơi tỷ lệ chốt hợp đồng luôn <b>cao nhất</b>.</p>'
            + '<h4>&#128172; Kịch bản chốt hẹn kinh điển</h4>'
            + _say('&#8220;Anh/chị ơi, em và đội ngũ kiến trúc sư đã hoàn thiện xong '
                   '<b>Bản dự toán chi tiết từng hạng mục</b> và <b>Phụ lục chủng loại vật '
                   'tư</b> chính xác 99% cho nhà mình rồi ạ.<br>'
                   'Tuy nhiên bảng này dài gần <b>10 trang</b> với rất nhiều danh mục kỹ '
                   'thuật và ký hiệu chuyên ngành. Nếu gửi qua Zalo, anh/chị đọc sẽ rất dễ '
                   '<b>bị rối</b> và không hình dung hết quyền lợi của mình.<br>'
                   'Cuối tuần này thứ Bảy hay Chủ Nhật anh/chị tiện, em xin phép <b>mang '
                   'bảng dự toán kèm hộp mẫu vật tư thực tế</b> qua nhà, hoặc mời anh/chị '
                   'ghé văn phòng/công trình để em giải thích rõ trong <b>20 phút</b> nhé?&#8221;')
            + _box('info', 'Mẹo: luôn cho khách chọn <b>Thứ Bảy hay Chủ Nhật</b> (2 lựa '
                   'chọn đóng) thay vì hỏi "anh có rảnh không" (câu mở dễ bị từ chối). '
                   'Kèm <b>hộp mẫu vật tư thật</b> để cuộc hẹn có sức nặng.')
            + '<h4>&#9989; 3 việc bạn đã làm được nhờ quy trình này</h4>'
            + _order([
                ('Cho khách biết KHOẢNG GIÁ từ đầu', 'Khách tin tưởng và ở lại nhóm, không sốt ruột bỏ đi.'),
                ('Thể hiện NĂNG LỰC chuyên gia', 'Bằng hình ảnh thực tế, giấy kiểm định trên nhóm Zalo.'),
                ('BẢO VỆ chất xám & ép gặp mặt', 'Không lộ file chi tiết; ép khách vào thế phải gặp trực tiếp &mdash; nơi tỷ lệ chốt cao nhất.'),
            ])
            + _nendont(
                ['Giữ file chi tiết làm "mồi nhử" để chốt hẹn',
                 'Cho khách chọn Thứ Bảy / Chủ Nhật (lựa chọn đóng)',
                 'Mang kèm hộp mẫu vật tư thật khi gặp',
                 'Nhấn "bảng 10 trang dễ rối, gặp em giải thích 20 phút"'],
                ['Gửi file báo giá chi tiết qua Zalo cho xong',
                 'Hỏi mở "anh có rảnh không" (dễ bị từ chối)',
                 'Chốt hẹn nhưng không có mẫu vật tư/lý do gặp',
                 'Nản lòng gửi luôn chi tiết khi khách nài nỉ'])
            + _fml('Bước 4 = <b>KHÔNG gửi file chi tiết qua Zalo</b>. Dùng nó làm mồi nhử: '
                   '"bảng 10 trang dễ rối &rarr; em mang qua + mẫu vật tư, giải thích 20 '
                   'phút". Cho chọn <b>T7 hay CN</b>. Gặp mặt = tỷ lệ chốt cao nhất.')
            + _quiz('lbg_4',
                    'Khi khách đã thiện chí ~70% và liên tục đòi gửi file báo giá chi tiết qua Zalo, phải làm gì?',
                    [('Khéo léo từ chối gửi qua Zalo, dùng file chi tiết làm lý do chốt một cuộc HẸN TRỰC TIẾP (kèm mẫu vật tư)', True),
                     ('Gửi luôn file chi tiết qua Zalo cho khách hài lòng', False),
                     ('Gửi một nửa file, giữ lại một nửa', False),
                     ('Bảo khách tự lên văn phòng lấy nếu muốn', False)],
                    'File chi tiết là phần thưởng đổi bằng cuộc hẹn &mdash; gặp trực tiếp là nơi tỷ lệ chốt hợp đồng cao nhất.'))

    # ------------------------------------------------------------------
    #  TỔNG KẾT
    # ------------------------------------------------------------------
    def _lbg_l_gold(self):
        return (
            self._lbg_tag('&#127942; TỔNG HỢP KIẾN THỨC')
            + '<h3>Tổng kết Quy trình lai 4 bước & bài tập thực hành</h3>'
            + _box('ok', '<b>Một câu cốt lõi:</b> cho khách biết GIÁ (khái toán) để họ an '
                   'tâm ở lại, nhưng GIỮ file chi tiết làm mồi nhử để ép khách gặp mặt '
                   '&mdash; nơi tỷ lệ chốt hợp đồng cao nhất.')
            + '<h4>&#128273; 4 BƯỚC &mdash; nhớ nhanh</h4>'
            + '<ul>'
            '<li><b>Bước 1 &mdash; Gọi lọc nhu cầu & tài chính:</b> hỏi đất/tầng/phong '
            'cách/số người; hỏi khéo tài chính; chốt hẹn ~1h nữa lập nhóm gửi khái toán.</li>'
            '<li><b>Bước 2 &mdash; Gửi báo giá khái toán:</b> tạo nhóm, sau 1&ndash;2h gửi '
            'TỔNG khoảng giá bằng tin nhắn/ảnh; KHÔNG gửi file chi tiết.</li>'
            '<li><b>Bước 3 &mdash; Nuôi thiện chí bằng hình ảnh:</b> gửi ảnh/video nghiệm '
            'thu, vật tư loại 1, giấy kiểm định; chờ tín hiệu 70%.</li>'
            '<li><b>Bước 4 &mdash; File chi tiết làm mồi nhử:</b> không gửi qua Zalo; dùng '
            'nó chốt cuộc hẹn trực tiếp (cho chọn T7/CN, mang mẫu vật tư).</li>'
            '</ul>'
            + '<h4>&#128221; Bảng công thức thuộc lòng</h4>'
            + _table(['Bước', 'Công thức thuộc lòng'],
                     [['<b>Bước 1 &mdash; Gọi lọc</b>', 'Khai thác nhu cầu (đất/tầng/phong cách/số người) + hỏi khéo tài chính ("để chọn vật tư tối ưu cho anh"); chốt hẹn ~1h nữa lập nhóm gửi KHÁI TOÁN.'],
                      ['<b>Bước 2 &mdash; Khái toán</b>', 'Tạo nhóm; sau 1&ndash;2h gửi TỔNG khoảng giá (tin nhắn/ảnh) + "chìa khóa trao tay, không phát sinh". KHÔNG file chi tiết = khách không có gì để đi so.'],
                      ['<b>Bước 3 &mdash; Nuôi 70%</b>', 'Không nhắn suông; gửi HÌNH ẢNH/VIDEO thật (nghiệm thu, giấy kiểm định). Tín hiệu 70% = khách hỏi tiến độ/thời gian/phong thủy.'],
                      ['<b>Bước 4 &mdash; Mồi nhử</b>', 'KHÔNG gửi file chi tiết qua Zalo. "Bảng 10 trang dễ rối &rarr; em mang qua + mẫu vật tư, giải thích 20 phút". Cho chọn T7/CN. Gặp mặt = chốt cao nhất.']],
                     widths=['24%', '76%'])
            + _box('warn', 'Nguyên tắc bao trùm: <b>KHÔNG gửi file chi tiết quá sớm</b> '
                   '(bị so giá) và <b>KHÔNG giấu giá quá lâu</b> (mất kiên nhẫn). Giữ đúng '
                   'điểm cân bằng: khái toán sớm &mdash; chi tiết đổi bằng cuộc hẹn.')
            + '<h4>&#128170; BÀI TẬP THỰC HÀNH (đóng vai theo cặp)</h4>'
            + _box('info', 'Chia cặp thực hành: <b>một người</b> đóng khách khó tính liên '
                   'tục đòi gửi file Excel qua Zalo; <b>một người</b> đóng Sale áp dụng '
                   'kịch bản Bước 4 để <b>từ chối khéo</b> và chốt bằng được cuộc hẹn '
                   'trực tiếp. Đổi vai và lặp lại đến khi nhuần nhuyễn.')
            + _quiz('lbg_gold',
                    'Đâu là nguyên tắc bao trùm toàn bộ Quy trình lai 4 bước làm báo giá?',
                    [('Không gửi file chi tiết quá sớm (tránh bị so giá) và không giấu giá quá lâu (tránh mất khách) — khái toán sớm, chi tiết đổi bằng cuộc hẹn', True),
                     ('Luôn gửi file báo giá chi tiết càng nhanh càng tốt', False),
                     ('Giấu giá hoàn toàn cho đến khi khách ký hợp đồng', False),
                     ('Chỉ cần gửi nhiều mẫu nhà là khách sẽ chốt', False)],
                    'Điểm cân bằng: gửi KHÁI TOÁN sớm để giữ khách, GIỮ file chi tiết làm mồi nhử ép khách gặp mặt.'))

    # ==================================================================
    #  BÀI THI CHẤM ĐIỂM
    # ==================================================================
    def _lbg_questions(self):
        T, F = True, False
        return [
            ('Triết lý cốt lõi của Quy trình lai làm báo giá là gì?',
             [('Thả con săn sắt bắt con cá mập: cho khách biết GIÁ để an tâm, GIỮ file chi tiết để ép gặp mặt', T),
              ('Gửi file báo giá chi tiết càng nhanh càng tốt', F),
              ('Giấu hoàn toàn mọi con số cho đến khi ký hợp đồng', F),
              ('Báo giá thật cao rồi giảm dần cho khách vui', F)]),

            ('Sai lầm của việc gửi file báo giá CHI TIẾT quá nhanh là gì?',
             [('Khách dùng file đó đi so giá 3-4 nhà thầu khác, mình bị "cắt cầu" và cuốn vào cuộc chiến phá giá', T),
              ('Khách sẽ ký hợp đồng ngay lập tức', F),
              ('Phần mềm CRM bị lỗi khi xuất file nhanh', F),
              ('Khách không đọc file vì quá dài', F)]),

            ('Sai lầm của việc giấu giá quá lâu, chỉ nhắn tin suông là gì?',
             [('Khách mất kiên nhẫn, thấy mình mập mờ/thiếu năng lực và rời nhóm', T),
              ('Khách sẽ tự tăng ngân sách', F),
              ('Không có rủi ro gì, đây là cách tốt nhất', F),
              ('Khách sẽ gửi tiền cọc trước', F)]),

            ('Trong 5 phút đầu của cuộc gọi đầu tiên, nhiệm vụ chính là gì?',
             [('Khai thác nhu cầu (đất/tầng/phong cách/số người) và đo lường tài chính của khách', T),
              ('Thao thao bất tuyệt giới thiệu về công ty', F),
              ('Chốt hợp đồng ngay trong cuộc gọi', F),
              ('Đọc bảng giá chi tiết cho khách nghe', F)]),

            ('Cách hỏi tài chính khéo léo nhất là?',
             [('"Anh/chị dự kiến ngân sách khoảng bao nhiêu để em chọn phân khúc vật tư tối ưu nhất ạ?"', T),
              ('"Anh có bao nhiêu tiền để xây nhà?"', F),
              ('"Anh vay ngân hàng được bao nhiêu?"', F),
              ('Không hỏi, cứ báo giá cao nhất', F)]),

            ('Ở bước 2 (tạo nhóm Zalo), gửi cho khách cái gì?',
             [('Bảng tổng hợp KHOẢNG GIÁ dự kiến (khái toán) bằng tin nhắn/ảnh, KHÔNG kèm phụ lục vật tư', T),
              ('File Excel chi tiết đầy đủ đơn giá và phụ lục vật tư', F),
              ('Hợp đồng thi công để ký ngay', F),
              ('Không gửi gì, đợi khách hỏi', F)]),

            ('Vì sao báo giá KHÁI TOÁN an toàn hơn báo giá chi tiết?',
             [('Nó giải tỏa thắc mắc về giá cho khách nhưng không có chi tiết vật tư để khách mang đi ép giá nhà thầu khác', T),
              ('Vì làm khái toán nhanh hơn nên đỡ mất công', F),
              ('Vì khái toán luôn cao hơn nên lãi nhiều', F),
              ('Vì khách không hiểu khái toán là gì', F)]),

            ('Vì sao nên giãn 1-2 tiếng rồi mới gửi báo giá khái toán?',
             [('Gửi ngay tức thì khiến khách nghĩ "dự toán cả công trình mà làm mấy phút" -> nghi ngờ, thiếu chuyên nghiệp', T),
              ('Để khách quên mất là đã hỏi giá', F),
              ('Vì phần mềm cần 2 tiếng để tính', F),
              ('Để khách đi hỏi nhà thầu khác trước', F)]),

            ('Ở bước 3, khi khách hỏi sâu về thép/xi măng/gạch, nên làm gì?',
             [('Gửi HÌNH ẢNH/VIDEO thực tế nghiệm thu cốt thép, vật tư loại 1, giấy kiểm định — không nhắn suông', T),
              ('Chỉ gõ chữ giải thích cho nhanh', F),
              ('Gửi ngay file báo giá chi tiết cho khách xem vật tư', F),
              ('Bảo khách tự tra cứu trên mạng', F)]),

            ('Dấu hiệu khách đã đạt khoảng 70% thiện chí là gì?',
             [('Khách hỏi về tiến độ thanh toán, thời gian thi công, hoặc nhờ tư vấn phong thủy/hướng bếp', T),
              ('Khách xem tin nhắn rồi im lặng', F),
              ('Khách đòi giảm giá', F),
              ('Khách bảo để suy nghĩ thêm', F)]),

            ('Nguyên tắc thép ở bước 4 (chốt hẹn) là gì?',
             [('KHÔNG BAO GIỜ gửi file báo giá chi tiết qua Zalo — dùng nó làm mồi nhử để chốt cuộc hẹn trực tiếp', T),
              ('Gửi file chi tiết qua Zalo rồi gọi điện chốt', F),
              ('Gửi file chi tiết kèm hợp đồng để ký online', F),
              ('Đăng file chi tiết lên nhóm cho mọi người xem', F)]),

            ('Vì sao phải giữ file chi tiết để ép khách gặp mặt trực tiếp?',
             [('Vì gặp mặt trực tiếp là nơi tỷ lệ chốt hợp đồng luôn cao nhất', T),
              ('Vì file chi tiết tốn giấy in', F),
              ('Vì công ty cấm gửi file qua mạng', F),
              ('Vì khách không có Zalo', F)]),

            ('Cách mời khách hẹn gặp hiệu quả nhất là?',
             [('Cho khách chọn "Thứ Bảy hay Chủ Nhật" (lựa chọn đóng) và mang kèm hộp mẫu vật tư thật', T),
              ('Hỏi mở "anh có rảnh không" rồi chờ khách trả lời', F),
              ('Bảo khách tự sắp xếp thời gian rồi báo lại', F),
              ('Chỉ nhắn tin "khi nào rảnh thì qua công ty"', F)]),

            ('Lý do khéo léo để từ chối gửi file chi tiết qua Zalo là gì?',
             [('"Bảng dài gần 10 trang nhiều danh mục kỹ thuật, gửi qua Zalo anh/chị dễ bị rối — em gặp giải thích 20 phút cho rõ"', T),
              ('"Công ty không cho phép gửi file"', F),
              ('"File này bí mật không được gửi"', F),
              ('"Anh phải đặt cọc thì em mới gửi"', F)]),

            ('Ba việc quy trình lai giúp bạn đạt được là gì?',
             [('Khách biết khoảng giá nên ở lại nhóm; thể hiện năng lực chuyên gia; bảo vệ chất xám và ép được khách gặp mặt', T),
              ('Gửi báo giá nhanh, nhiều mẫu nhà, và giảm giá sâu', F),
              ('Chốt hợp đồng qua điện thoại mà không cần gặp', F),
              ('Thu tiền cọc trước khi làm báo giá', F)]),

            ('Nguyên tắc bao trùm của cả khóa học này là gì?',
             [('Không gửi file chi tiết quá sớm (tránh so giá) và không giấu giá quá lâu (tránh mất khách) — khái toán sớm, chi tiết đổi bằng cuộc hẹn', T),
              ('Luôn gửi file chi tiết càng nhanh càng tốt', F),
              ('Giấu mọi con số đến khi khách ký', F),
              ('Báo giá thật thấp để thắng đối thủ', F)]),
        ]
