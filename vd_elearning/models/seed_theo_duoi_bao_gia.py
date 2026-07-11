# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

TÁI CẤU TRÚC THEO THANG BLOOM (user chốt 2026-07-11): nội dung gốc được phân
theo 6 cấp độ tư duy (Ghi nhớ -> Hiểu -> Áp dụng -> Phân tích -> Đánh giá ->
Sáng tạo). Mỗi cấp = 1 thẻ (card) MÀU RIÊNG nhất quán, gồm:
  - Mục tiêu đầu ra (động từ Bloom)
  - Nội dung cốt lõi (công thức / quy trình chuẩn hóa từ tài liệu gốc)
  - Đánh giá / Thực hành (câu hỏi mẫu tương ứng cấp độ)
GIỮ NGUYÊN toàn bộ nội dung, chỉ sắp xếp lại theo tầng tư duy. FULL chiều ngang
(không giới hạn max-width). 20 câu thi giữ nguyên, sắp lại theo cụm Bloom.

BẪY %: mọi helper dựng chuỗi bằng nối (+), KHÔNG dùng '...' % (...) -> % literal
an toàn tuyệt đối. Khối <style> là chuỗi thuần. Đảo đáp án mỗi lần thi do
overview.js xử lý chung. Prefix _tdbg_ (xem reference-seed-method-name-collision).
"""
from odoo import api, models

_TDBG_VERSION = 'v5-bloom'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-tdbg{font-size:16.5px;line-height:1.72;color:#1f2937;}'
    '.vd-tdbg h2{font-size:23px;font-weight:800;color:#111827;margin:30px 0 12px;}'
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


# ---------------------------------------------------------------------------
#  HELPER dựng chuỗi bằng nối (+) -> KHÔNG lo bẫy %.
# ---------------------------------------------------------------------------
def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _sub(icon, label, color, inner):
    """Khối con trong 1 thẻ Bloom: nhãn màu + nội dung."""
    return (
        '<div style="margin:16px 0 4px;">'
        '<div style="font-weight:800;color:' + color + ';font-size:12.5px;'
        'letter-spacing:.6px;text-transform:uppercase;margin-bottom:6px;">'
        + icon + '&nbsp; ' + label + '</div>'
        '<div>' + inner + '</div></div>')


def _card(num, name, en, icon, color, bg, objectives, content, assess):
    """1 thẻ 1 cấp độ Bloom - viền + header màu riêng."""
    return (
        '<div style="border:1px solid #e5e7eb;border-radius:16px;background:#ffffff;'
        'margin:22px 0;box-shadow:0 6px 22px rgba(2,6,23,.07);overflow:hidden;">'
        '<div style="background:' + bg + ';border-bottom:3px solid ' + color + ';'
        'padding:16px 22px;display:flex;align-items:center;gap:14px;">'
        '<div style="width:48px;height:48px;border-radius:14px;background:' + color + ';'
        'color:#fff;font-size:24px;display:flex;align-items:center;justify-content:center;'
        'flex:0 0 48px;">' + icon + '</div>'
        '<div><div style="font-size:12px;font-weight:800;color:' + color + ';'
        'letter-spacing:1.5px;text-transform:uppercase;">CẤP ' + str(num) + ' &middot; ' + en + '</div>'
        '<div style="font-size:22px;font-weight:900;color:#0f172a;line-height:1.15;">'
        + name + '</div></div></div>'
        '<div style="padding:6px 22px 20px;">'
        + _sub('&#127919;', 'Mục tiêu đầu ra', color, objectives)
        + _sub('&#128218;', 'Nội dung cốt lõi', color, content)
        + _sub('&#9997;&#65039;', 'Đánh giá / Thực hành', color, assess)
        + '</div></div>')


def _say(text):
    """Câu mẫu nên nói - để NV copy dùng."""
    return (
        '<div style="border-left:4px solid #2563eb;background:#eff6ff;'
        'border-radius:0 8px 8px 0;padding:10px 14px;margin:8px 0;font-style:italic;'
        'color:#1e3a8a;">&#128172; &#8220;' + text + '&#8221;</div>')


def _qsample(q, options):
    """Câu hỏi mẫu - hiện 4 đáp án, đánh dấu đáp án đúng."""
    lis = ''
    for t, c in options:
        mark = '&#9989; ' if c else '&#9675; '
        col = 'color:#15803d;font-weight:700;' if c else 'color:#475569;'
        lis += '<li style="' + col + '">' + mark + t + '</li>'
    return (
        '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;'
        'padding:12px 16px;margin:8px 0;">'
        '<div style="font-weight:700;color:#0f172a;margin-bottom:6px;">'
        '&#10067; ' + q + '</div>'
        '<ul style="margin:0;list-style:none;padding-left:2px;">' + lis + '</ul></div>')


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
    #  NỘI DUNG (6 cấp Bloom)
    # ==================================================================
    def _vd_tdbg_pages(self):
        return [
            ('Hero', self._tdbg_hero()),
            ('Map', self._tdbg_map()),
            ('L1', self._tdbg_l1_remember()),
            ('L2', self._tdbg_l2_understand()),
            ('L3', self._tdbg_l3_apply()),
            ('L4', self._tdbg_l4_analyze()),
            ('L5', self._tdbg_l5_evaluate()),
            ('L6', self._tdbg_l6_create()),
            ('Gold', self._tdbg_gold()),
        ]

    def _tdbg_hero(self):
        return (
            '<div style="background:#e8401f;border-radius:16px;padding:30px 28px;'
            'margin-bottom:8px;">'
            '<div style="color:#ffe0d8;font-size:14px;font-weight:700;'
            'letter-spacing:2px;">KỸ NĂNG SALE &mdash; CHỐT HỢP ĐỒNG</div>'
            '<div style="color:#ffffff;font-size:29px;font-weight:900;margin-top:8px;'
            'line-height:1.2;">Quy trình theo đuổi khách hàng sau khi gửi báo giá</div>'
            '<div style="color:#fff2ee;font-size:16px;margin-top:12px;line-height:1.6;">'
            'Khóa học chia theo 6 cấp độ tư duy (Bloom): từ GHI NHỚ quy trình đến '
            'SÁNG TẠO kịch bản theo đuổi của riêng bạn. Học lần lượt từng cấp, cấp sau '
            'dựa trên cấp trước.</div></div>')

    def _tdbg_map(self):
        dot = ('<span style="display:inline-block;width:12px;height:12px;'
               'border-radius:50%;background:')
        rows = [
            [dot + '#2563eb;"></span>', '&#129504; Ghi nhớ', 'Nhận diện, Liệt kê, Gọi tên',
             'Công thức 8 bước, 6 nhóm câu hỏi, các mốc thời gian'],
            [dot + '#0d9488;"></span>', '&#128161; Hiểu', 'Giải thích, Phân biệt, Diễn giải',
             'Vì sao báo giá phải khớp tài chính, vì sao đôn đốc khách xem báo giá'],
            [dot + '#ea580c;"></span>', '&#128736;&#65039; Áp dụng', 'Vận dụng, Sử dụng, Thực hiện',
             '3 câu tự kiểm trước khi gửi, câu mẫu, cân đối phương án'],
            [dot + '#b45309;"></span>', '&#128269; Phân tích', 'Phân tích, Phân loại, So sánh',
             'Phân loại khúc mắc theo 6 nhóm, phân tích lý do khách chưa ký'],
            [dot + '#e11d48;"></span>', '&#9878;&#65039; Đánh giá', 'Biện luận, Đánh giá, Quyết định',
             'Đánh giá báo giá đạt chuẩn chưa, quyết định thời điểm chuyển bước'],
            [dot + '#7c3aed;"></span>', '&#127912; Sáng tạo', 'Thiết kế, Xây dựng, Soạn thảo',
             'Tự thiết kế kế hoạch theo đuổi 8 bước cho một khách thật'],
        ]
        return (
            '<h2>&#128506;&#65039; Bản đồ khóa học theo thang Bloom</h2>'
            + _table(['', 'Cấp độ', 'Động từ mục tiêu', 'Nội dung trọng tâm'], rows,
                     widths=['4%', '16%', '26%', '54%']))

    # ------------------------------------------------------------------
    #  CẤP 1 — GHI NHỚ (Remember)
    # ------------------------------------------------------------------
    def _tdbg_l1_remember(self):
        obj = ('<ul>'
               '<li><b>Nhận diện</b> được: gửi báo giá là ĐIỂM BẮT ĐẦU, không phải kết thúc.</li>'
               '<li><b>Liệt kê</b> đúng thứ tự Công thức 8 bước theo đuổi.</li>'
               '<li><b>Gọi tên</b> 6 nhóm câu hỏi khai thác khúc mắc.</li>'
               '<li><b>Ghi nhớ</b> các mốc thời gian bắt buộc.</li></ul>')
        content = (
            '<p><b>Nguyên tắc nền:</b> Gửi báo giá = bắt đầu quá trình chốt. '
            '<span class="no">Khách im lặng = quy trình đang bị DỪNG lại</span> '
            '&mdash; tuyệt đối không để khách &#8220;treo&#8221;.</p>'
            + '<p><b>Công thức 8 bước phải thuộc lòng:</b></p>'
            + _table(['Bước', 'Việc làm', 'Mục tiêu'],
                     [['1', 'Gửi mẫu nhà tham khảo', 'Cho khách thêm ý tưởng'],
                      ['2', 'Gửi báo giá &mdash; đảm bảo chất lượng', 'Khớp tài chính, đúng nhu cầu'],
                      ['3', 'Phản hồi sau 1&ndash;2 ngày', 'Biết khách đang nghĩ gì'],
                      ['4', 'Nhắc khởi công &amp; ký giữ giá', 'Tạo lý do quyết định sớm'],
                      ['5', 'Khai thác &amp; xử lý vấn đề sau báo giá', 'Gỡ hết khúc mắc (quan trọng nhất)'],
                      ['6', 'Gửi hợp đồng &amp; phụ lục', 'Chuyển sang giai đoạn ký'],
                      ['7', 'Khai thác &amp; xử lý vấn đề hợp đồng', 'Gỡ vướng mắc điều khoản'],
                      ['8', 'Hẹn ký hợp đồng &amp; khảo sát đất', 'Chốt lịch ký, đặt cọc']],
                     widths=['8%', '46%', '46%'])
            + '<p><b>6 nhóm câu hỏi khai thác:</b> (1) Báo giá &middot; (2) Thiết kế '
            '&middot; (3) Mẫu nhà &middot; (4) Gia đình &middot; (5) Khởi công &middot; '
            '(6) Niềm tin.</p>'
            + '<p><b>Mốc thời gian cần nhớ:</b></p>'
            + _table(['Việc', 'Mốc'],
                     [['Lấy phản hồi sau khi gửi báo giá', 'Sau 1&ndash;2 ngày'],
                      ['Hỏi lại sau khi gửi hợp đồng', 'Sau 1&ndash;2 ngày'],
                      ['Khoản đặt cọc khi ký (nếu áp dụng)', '50.000.000 đồng']],
                     widths=['60%', '40%']))
        assess = _qsample(
            'Bước nào được coi là QUAN TRỌNG NHẤT trong quy trình theo đuổi?',
            [('Khai thác và xử lý vấn đề sau báo giá', True),
             ('Gửi báo giá thật nhanh', False),
             ('Gửi thật nhiều mẫu nhà', False),
             ('Nhắc khách về tiền đặt cọc', False)])
        return _card(1, 'GHI NHỚ', 'REMEMBER', '&#129504;', '#2563eb', '#eff6ff',
                     obj, content, assess)

    # ------------------------------------------------------------------
    #  CẤP 2 — HIỂU (Understand)
    # ------------------------------------------------------------------
    def _tdbg_l2_understand(self):
        obj = ('<ul>'
               '<li><b>Giải thích</b> vì sao báo giá lệch tài chính là vô tác dụng.</li>'
               '<li><b>Giải thích</b> vì sao phải chủ động đôn đốc khách xem báo giá.</li>'
               '<li><b>Phân biệt</b> &#8220;khách im lặng&#8221; với &#8220;khách hết quan tâm&#8221;.</li>'
               '<li><b>Diễn giải</b> vì sao không được ép khách chốt mẫu nhà.</li></ul>')
        content = (
            '<p><b>Vì sao không được ngồi chờ?</b> Khi nhận báo giá, khách đang xem '
            'nhiều đơn vị, cân nhắc tài chính, chưa hiểu hết báo giá và đang so sánh. '
            'Không chủ động dẫn dắt thì khách nghiêng dần sang bên khác.</p>'
            + '<p><b>Vì sao phải đôn đốc khách xem báo giá?</b> Nhiều khách không xem '
            'hoặc chưa xem kỹ, thậm chí lấy lý do &#8220;chưa xem&#8221; để né. Trong '
            'báo giá có <b>phụ lục vật tư đầy đủ</b> và <b>tổng giá trị hợp đồng</b> '
            '&mdash; khách phải đọc mới đánh giá đúng giá trị mình mang lại.</p>'
            + '<p><b>&#8220;Báo giá chuẩn&#8221; nghĩa là gì?</b></p>'
            + _table(['Điều kiện', 'Ý nghĩa'],
                     [['<b>1. Khớp tầm tài chính khách đưa ra</b> <span class="no">(quan trọng nhất)</span>',
                       'Tổng giá trị nằm TRONG ngân sách khách nói &mdash; yếu tố quyết định khách có quan tâm hay không.'],
                      ['<b>2. Phù hợp diện tích và công năng</b>',
                       'Số tầng, số phòng, công năng cân đối được với tầm tài chính đó.'],
                      ['<b>3. Đúng mong muốn và phong cách</b>',
                       'Phong cách, mức hoàn thiện, thang máy / gara / sân... khớp điều khách mong.']],
                     widths=['38%', '62%'])
            + '<p><b>Báo giá lệch tài chính = vô tác dụng:</b> khách nhìn con số vượt '
            'xa là loại mình ngay, âm thầm sang đối thủ. <b>Không ép chốt mẫu nhà</b> '
            'vì khách không mua mẫu &mdash; khách mua giải pháp phù hợp với gia đình.</p>'
            + '<p><b>Khách im lặng KHÔNG phải hết quan tâm</b> &mdash; có thể vì: báo '
            'giá cao hơn dự kiến, chưa đúng nhu cầu, chưa hiểu cách tính, đang chờ bên '
            'khác, hoặc chưa đủ niềm tin.</p>')
        assess = _qsample(
            'Khách nói tầm 2,8 tỷ nhưng nhân viên gửi báo giá 3,8 tỷ. Hậu quả đúng nhất là gì?',
            [('Báo giá không khớp tài chính nên vô tác dụng, khách hết quan tâm và chuyển sang đối thủ', True),
             ('Khách vẫn ký vì nghĩ chất lượng cao hơn', False),
             ('Không sao, vì báo cao để còn thương lượng giảm', False),
             ('Khách sẽ tự xin giảm giá rồi ký luôn', False)])
        return _card(2, 'HIỂU', 'UNDERSTAND', '&#128161;', '#0d9488', '#f0fdfa',
                     obj, content, assess)

    # ------------------------------------------------------------------
    #  CẤP 3 — ÁP DỤNG (Apply)
    # ------------------------------------------------------------------
    def _tdbg_l3_apply(self):
        obj = ('<ul>'
               '<li><b>Vận dụng</b> 3 câu tự kiểm trước khi bấm gửi báo giá.</li>'
               '<li><b>Sử dụng</b> đúng câu mẫu ở từng bước.</li>'
               '<li><b>Thực hiện</b> cân đối phương án khi nhu cầu vượt ngân sách.</li></ul>')
        content = (
            '<p><b>3 câu tự kiểm BẮT BUỘC trước khi gửi báo giá:</b></p>'
            + _table(['Câu hỏi tự kiểm', 'Nếu CHƯA đạt'],
                     [['<b>1. Có khớp tầm tài chính khách đưa ra không?</b> (ưu tiên số 1)',
                       'Vượt ngân sách &rArr; CHƯA gửi, cân đối lại phương án.'],
                      ['<b>2. Có phù hợp diện tích và công năng không?</b>',
                       'Nhu cầu quá lớn so với ngân sách &rArr; tư vấn điều chỉnh trước.'],
                      ['<b>3. Có đúng mong muốn của khách chưa?</b>',
                       'Lệch phong cách / hoàn thiện &rArr; sửa cho khớp rồi mới gửi.']],
                     widths=['52%', '48%'])
            + '<p><b>Cân đối khi nhu cầu vượt tiền:</b> khách muốn diện tích rộng, '
            'công năng nhiều nhưng tài chính không đủ &rArr; tư vấn phương án vừa túi '
            'tiền, KHÔNG gửi con số vượt xa rồi để khách tự sốc.</p>'
            + '<p><b>Bộ câu mẫu nên nói (copy dùng ngay):</b></p>'
            + _say('Em gửi thêm vài mẫu nhà có diện tích và mức đầu tư gần với nhu cầu '
                   'của anh/chị để mình tham khảo. Chi tiết nào thích, bên em điều '
                   'chỉnh thiết kế theo đúng mong muốn gia đình.')
            + _say('Nếu gia đình dự kiến ở nhà mới trước Tết thì nên triển khai sớm để '
                   'đảm bảo tiến độ, để quá sát cuối năm việc hoàn thiện sẽ rất áp lực.')
            + _say('Bên em có thể ký hợp đồng giữ giá để khóa mức giá hôm nay, sau này '
                   'vật tư tăng gia đình cũng không bị ảnh hưởng ạ.')
            + _say('Bên em gửi trước hợp đồng kèm đầy đủ phụ lục để anh/chị đọc, nội '
                   'dung nào cần giải thích em trao đổi ngay trước khi ký.'))
        assess = _qsample(
            'Đâu là câu KHÔNG nên nói khi gửi mẫu nhà cho khách tham khảo?',
            [('&#8220;Anh chị chọn giúp em một mẫu nhé&#8221;', True),
             ('&#8220;Em gửi vài mẫu gần nhu cầu để mình tham khảo&#8221;', False),
             ('&#8220;Thích chi tiết nào bên em điều chỉnh thiết kế theo&#8221;', False),
             ('&#8220;Mấy mẫu này để anh chị có thêm ý tưởng ạ&#8221;', False)])
        return _card(3, 'ÁP DỤNG', 'APPLY', '&#128736;&#65039;', '#ea580c', '#fff7ed',
                     obj, content, assess)

    # ------------------------------------------------------------------
    #  CẤP 4 — PHÂN TÍCH (Analyze)
    # ------------------------------------------------------------------
    def _tdbg_l4_analyze(self):
        obj = ('<ul>'
               '<li><b>Phân tích</b> nguyên nhân vì sao khách chưa ký.</li>'
               '<li><b>Phân loại</b> khúc mắc của khách vào đúng 1 trong 6 nhóm.</li>'
               '<li><b>So sánh</b> các tình huống báo giá lệch nhu cầu.</li></ul>')
        content = (
            '<p><b>Khách chưa ký = chắc chắn còn vấn đề.</b> Phải TÌM RA, không tự suy '
            'đoán. Khai thác đủ 6 nhóm câu hỏi:</p>'
            + _table(['Nhóm', 'Câu hỏi cần khai thác'],
                     [['<b>1. Báo giá</b>', 'Có phù hợp không? Có vượt tài chính không? Có cần điều chỉnh không?'],
                      ['<b>2. Thiết kế</b>', 'Có thích không? Cần thay đổi gì? Cần thêm công năng không?'],
                      ['<b>3. Mẫu nhà</b>', 'Đã đúng phong cách chưa? Có muốn tham khảo thêm không?'],
                      ['<b>4. Gia đình</b>', 'Đã thống nhất chưa? Ai là người quyết định? Cần trao đổi thêm với người thân không?'],
                      ['<b>5. Khởi công</b>', 'Dự kiến khi nào? Đang chờ việc gì không? Có vướng thủ tục không?'],
                      ['<b>6. Niềm tin</b>', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?']],
                     widths=['18%', '82%'])
            + '<p><b>So sánh tình huống báo giá lệch nhu cầu:</b></p>'
            + _table(['Khách muốn', 'Nếu gửi lệch', 'Kết quả'],
                     [['Tài chính ~2,8 tỷ', 'Gửi báo giá 3,8 tỷ', '<span class="no">SAI</span>'],
                      ['Phong cách hiện đại', 'Báo giá mẫu tân cổ', '<span class="no">SAI</span>'],
                      ['Xây để ở', 'Làm theo chuẩn đầu tư', '<span class="no">SAI</span>']],
                     widths=['34%', '34%', '32%']))
        assess = _qsample(
            'Trong 6 nhóm câu hỏi, nhóm nào giúp lộ ra RÀO CẢN THẬT SỰ trước khi ký?',
            [('Nhóm Niềm tin: "Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?"', True),
             ('Nhóm Báo giá: "Có vượt tài chính không?"', False),
             ('Nhóm Mẫu nhà: "Đã đúng phong cách chưa?"', False),
             ('Nhóm Khởi công: "Dự kiến khi nào?"', False)])
        return _card(4, 'PHÂN TÍCH', 'ANALYZE', '&#128269;', '#b45309', '#fffbeb',
                     obj, content, assess)

    # ------------------------------------------------------------------
    #  CẤP 5 — ĐÁNH GIÁ (Evaluate)
    # ------------------------------------------------------------------
    def _tdbg_l5_evaluate(self):
        obj = ('<ul>'
               '<li><b>Biện luận</b> một báo giá đã đạt chuẩn hay chưa.</li>'
               '<li><b>Quyết định</b> đúng thời điểm chuyển bước (gửi hợp đồng, hẹn ký).</li>'
               '<li><b>Đánh giá</b> chất lượng mỗi lần liên hệ khách.</li></ul>')
        content = (
            '<p><b>Tiêu chí đánh giá báo giá ĐẠT:</b> &#8220;Nếu mình là khách, mình '
            'cũng thấy báo giá này khớp túi tiền và hợp lý&#8221; &mdash; đủ 3 điều '
            'kiện (tài chính, diện tích/công năng, mong muốn).</p>'
            + '<p><b>Quyết định thời điểm chuyển bước:</b></p>'
            + _table(['Chuyển bước khi', 'Điều kiện đủ'],
                     [['Gửi hợp đồng + phụ lục (bước 6)', 'Khách đã đồng ý báo giá + phương án + hết vướng mắc lớn'],
                      ['Hẹn ký + khảo sát đất (bước 8)', 'Khách đã đồng ý báo giá + thiết kế + hợp đồng']],
                     widths=['42%', '58%'])
            + '<p><b>Sai lầm cần tránh (tự đánh giá để loại bỏ):</b> gửi báo giá xong '
            '&#8220;im luôn&#8221;; gửi hợp đồng xong &#8220;mất hút&#8221;. Cả hai '
            'đều làm quy trình đứng lại.</p>'
            + '<p><b>Bảng tự kiểm sau MỖI lần liên hệ:</b></p>'
            + _table(['#', 'Tự hỏi (Có / Chưa)'],
                     [['1', 'Lần này khách đã <b>tiến thêm 1 bước</b> chưa?'],
                      ['2', 'Mình đã <b>biết khách đang nghĩ gì</b> chưa, hay chỉ đoán?'],
                      ['3', 'Còn <b>vấn đề nào chưa gỡ</b> (tài chính / thiết kế / gia đình / niềm tin)?'],
                      ['4', 'Đã hẹn <b>mốc liên hệ tiếp theo</b> chưa?'],
                      ['5', 'Lần này có <b>mục tiêu rõ ràng</b> đưa khách gần hơn tới ký không?']],
                     widths=['8%', '92%']))
        assess = _qsample(
            'Sai lầm phổ biến ở bước khai thác và xử lý vấn đề hợp đồng (bước 7) là gì?',
            [('Gửi hợp đồng xong rồi mất hút, không chủ động hỏi lại để xử lý vướng mắc', True),
             ('Hỏi lại khách sau 1-2 ngày về điều khoản', False),
             ('Giải thích dứt điểm ngay khi khách còn băn khoăn', False),
             ('Gửi kèm lời mời khách trao đổi thêm', False)])
        return _card(5, 'ĐÁNH GIÁ', 'EVALUATE', '&#9878;&#65039;', '#e11d48', '#fff1f2',
                     obj, content, assess)

    # ------------------------------------------------------------------
    #  CẤP 6 — SÁNG TẠO (Create)
    # ------------------------------------------------------------------
    def _tdbg_l6_create(self):
        obj = ('<ul>'
               '<li><b>Thiết kế</b> kế hoạch theo đuổi 8 bước cho một khách thật.</li>'
               '<li><b>Xây dựng</b> bộ câu hỏi khai thác riêng theo tình huống khách.</li>'
               '<li><b>Soạn thảo</b> các câu chốt / câu mẫu phù hợp từng khách.</li></ul>')
        content = (
            '<p>Đây là cấp cao nhất: bạn tự VẬN DỤNG toàn bộ quy trình để làm ra sản '
            'phẩm của riêng mình. Chọn <b>1 khách đang theo đuổi</b> và điền vào mẫu '
            'kế hoạch dưới đây.</p>'
            + _table(['Mục', 'Bạn tự điền'],
                     [['Khách &amp; tình trạng hiện tại', 'VD: đã gửi báo giá 2 ngày, chưa phản hồi'],
                      ['Đang ở bước nào (1&ndash;8)', '&hellip;'],
                      ['Bước tiếp theo &amp; mục tiêu', '&hellip;'],
                      ['Dự đoán khúc mắc (theo 6 nhóm)', '&hellip;'],
                      ['Câu hỏi khai thác sẽ dùng', '&hellip;'],
                      ['Câu mẫu / câu chốt sẽ nói', '&hellip;'],
                      ['Mốc liên hệ tiếp theo', '&hellip;']],
                     widths=['38%', '62%']))
        assess = (
            '<p><b>Bài thực hành (nộp cho trưởng nhóm):</b> Soạn hoàn chỉnh kế hoạch '
            'theo đuổi 8 bước cho 1 khách thật đang theo &mdash; nêu rõ bước hiện tại, '
            'khúc mắc dự đoán, bộ câu hỏi khai thác và câu chốt sẽ dùng. '
            '<b>Tiêu chí đạt:</b> mỗi lần liên hệ trong kế hoạch đều đưa khách tiến '
            'thêm ít nhất 1 bước.</p>')
        return _card(6, 'SÁNG TẠO', 'CREATE', '&#127912;', '#7c3aed', '#f5f3ff',
                     obj, content, assess)

    def _tdbg_gold(self):
        return (
            '<h2>&#127942; Nguyên tắc vàng</h2>'
            '<p style="font-size:18px;color:#111827;font-weight:700;">Nhân viên giỏi '
            'KHÔNG phải người gửi được NHIỀU báo giá, mà là người biết DẪN DẮT khách '
            'đi qua từng bước tới quyết định ký.</p>'
            '<p>Sau mỗi lần liên hệ, nếu khách tiến thêm một bước thì khả năng ký tăng '
            'lên rất nhiều. Không bao giờ để khách im lặng quá lâu &mdash; gửi báo giá '
            'là BẮT ĐẦU, không phải kết thúc.</p>')

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM - sắp theo cụm Bloom (Nhớ -> Đánh giá).
    #  Đáp án nhiễu đều hợp lý để NV phải phân vân. (đáp án, đúng?)
    # ==================================================================
    def _vd_tdbg_questions(self):
        T, F = True, False
        return [
            # ---- CẤP 1: GHI NHỚ ----
            ('Theo khóa học, gửi báo giá cho khách nên được hiểu là gì?',
             [('Điểm BẮT ĐẦU của quá trình chốt hợp đồng', T),
              ('Bước cuối cùng, sau đó chỉ việc chờ khách gọi lại', F),
              ('Dấu hiệu khách đã gần như đồng ý ký', F),
              ('Thời điểm nên ngừng liên hệ để khách tự cân nhắc', F)]),

            ('Sau khi gửi báo giá bao lâu thì BẮT BUỘC phải lấy phản hồi từ khách?',
             [('Sau 1-2 ngày', T),
              ('Sau 1-2 tuần', F),
              ('Chỉ khi khách chủ động nhắn lại', F),
              ('Sau đúng 1 tháng', F)]),

            ('Bước nào được khóa học coi là QUAN TRỌNG NHẤT trong quy trình theo đuổi?',
             [('Khai thác và xử lý vấn đề sau báo giá của khách', T),
              ('Gửi báo giá thật nhanh', F),
              ('Gửi thật nhiều mẫu nhà', F),
              ('Nhắc khách về tiền đặt cọc', F)]),

            ('Sau khi gửi hợp đồng và phụ lục, sau bao lâu nên chủ động hỏi lại khách?',
             [('Sau 1-2 ngày', T),
              ('Chỉ hỏi khi khách chủ động liên hệ', F),
              ('Sau 2-3 tuần cho khách đủ thời gian', F),
              ('Không cần hỏi, chờ khách ký gửi lại', F)]),

            # ---- CẤP 2: HIỂU ----
            ('Khi khách IM LẶNG sau khi nhận báo giá, cách hiểu ĐÚNG là gì?',
             [('Quy trình đang bị dừng lại - cần chủ động tìm hiểu, không được để khách treo', T),
              ('Khách đã hết quan tâm, nên chuyển sang khách khác', F),
              ('Khách đang hài lòng nên không cần hỏi thêm', F),
              ('Nên chờ thêm ít nhất 1 tuần rồi mới liên hệ lại', F)]),

            ('Khách nói tầm tài chính khoảng 2,8 tỷ nhưng nhân viên gửi báo giá 3,8 tỷ. Hậu quả ĐÚNG NHẤT là gì?',
             [('Báo giá không khớp tầm tài chính nên vô tác dụng - khách hết quan tâm và chuyển sang đối thủ tham khảo', T),
              ('Khách vẫn ký vì nghĩ chất lượng chắc chắn cao hơn', F),
              ('Không sao, vì cứ báo cao để còn thương lượng giảm dần', F),
              ('Khách sẽ tự xin giảm giá rồi ký luôn', F)]),

            ('Mục tiêu THỰC SỰ của cuộc gọi lấy phản hồi sau báo giá là gì?',
             [('Để biết khách đang nghĩ gì, khai thác suy nghĩ thật của khách', T),
              ('Để ép khách ký hợp đồng ngay trong cuộc gọi', F),
              ('Để thông báo báo giá sắp hết hạn', F),
              ('Để hỏi khách đã chuyển tiền cọc chưa', F)]),

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

            ('Nếu khách vẫn CHƯA ký, nhân viên nên hiểu điều gì?',
             [('Chắc chắn còn vấn đề chưa được gỡ, phải tìm ra chứ không tự suy đoán', T),
              ('Khách keo kiệt nên bỏ qua, tìm khách mới', F),
              ('Do giá của mình cao, không thể làm gì thêm', F),
              ('Khách sẽ tự ký khi nào sẵn sàng, không cần làm gì', F)]),

            # ---- CẤP 3: ÁP DỤNG ----
            ('Trước khi bấm GỬI báo giá, 3 câu hỏi tự kiểm bắt buộc theo thứ tự ưu tiên là gì?',
             [('Có khớp tầm tài chính khách đưa ra không + có phù hợp diện tích/công năng không + có đúng mong muốn khách không', T),
              ('Giá có rẻ hơn đối thủ không, có khuyến mãi không, có tặng quà không', F),
              ('Khách có gấp không, có thiện chí không, có dễ tính không', F),
              ('Không cần tự hỏi, cứ gửi kèm câu "anh/chị tham khảo nhé"', F)]),

            ('Đâu là câu KHÔNG nên nói khi gửi mẫu nhà cho khách tham khảo?',
             [('"Anh chị chọn giúp em một mẫu nhé"', T),
              ('"Em gửi vài mẫu gần nhu cầu để mình tham khảo"', F),
              ('"Thích chi tiết nào bên em điều chỉnh thiết kế theo"', F),
              ('"Mấy mẫu này để anh chị có thêm ý tưởng ạ"', F)]),

            ('Khách muốn diện tích rộng, công năng nhiều nhưng tầm tài chính KHÔNG đủ. Trước khi báo giá nên làm gì?',
             [('Cân đối, tư vấn phương án diện tích/công năng vừa với túi tiền khách rồi mới báo giá', T),
              ('Cứ tính đủ nhu cầu ra giá thật cao rồi gửi, khách tự liệu', F),
              ('Bỏ hết công năng khách muốn để hạ giá xuống thấp nhất', F),
              ('Gửi luôn báo giá vượt ngân sách để khách thấy đẳng cấp', F)]),

            ('Khi nhắc khách về thời gian khởi công (bước 4), ranh giới ĐÚNG là gì?',
             [('Giúp khách hiểu hệ quả của việc chậm quyết định, KHÔNG gây áp lực vô lý', T),
              ('Dọa khách rằng giá sẽ tăng gấp đôi nếu không ký ngay', F),
              ('Nói công ty sắp hết suất nhận công trình', F),
              ('Ép khách phải khởi công trong tuần này', F)]),

            # ---- CẤP 4: PHÂN TÍCH ----
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

            # ---- CẤP 5: ĐÁNH GIÁ ----
            ('Sai lầm phổ biến ở bước KHAI THÁC và XỬ LÝ VẤN ĐỀ HỢP ĐỒNG (bước 7) là gì?',
             [('Gửi hợp đồng xong rồi mất hút, không chủ động hỏi lại để xử lý vướng mắc', T),
              ('Hỏi lại khách sau 1-2 ngày về điều khoản', F),
              ('Giải thích dứt điểm ngay khi khách còn băn khoăn', F),
              ('Gửi kèm lời mời khách trao đổi thêm', F)]),

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
