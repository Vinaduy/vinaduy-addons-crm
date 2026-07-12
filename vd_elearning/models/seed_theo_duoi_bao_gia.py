# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "QUY TRÌNH THEO ĐUỔI KHÁCH HÀNG SAU KHI
GỬI BÁO GIÁ" (Kỹ năng Sale).

GIAO DIỆN TƯƠNG TÁC + PROGRESSIVE DISCLOSURE (user chốt 2026-07-12):
- Mỗi bài học = 1 thẻ <details> bấm-mở (bấm đến đâu hiện đến đó -> tránh quá tải).
- Trong mỗi bài đi theo lũy tiến: LÝ THUYẾT RÚT GỌN -> nút "Xem ví dụ thực tế"
  (<details>) -> nút "Làm bài tập tình huống" (<details>) chứa tình huống + nút
  "Xem đáp án & giải thích" (<details> lồng).
- Dùng <details>/<summary> NATIVE HTML (không cần JS): vd_body sanitize=False +
  render qua markup() nên HTML thô giữ nguyên; JS chèn qua innerHTML KHÔNG chạy
  nên KHÔNG dùng script. Accordion là tính năng gốc trình duyệt.

BÁM SÁT tài liệu gốc + GIAI ĐOẠN 0 quy tắc tạo nhóm. FULL chiều ngang, KHÔNG cắt
nội dung. Helper dựng bằng nối chuỗi (+) -> tránh bẫy %. Prefix _tdbg_. Idempotent
theo version. Đảo đáp án mỗi lần thi do overview.js xử lý chung.
"""
from odoo import api, models

_TDBG_VERSION = 'v7-interactive'
_PARAM_KEY = 'vd_elearning.theo_duoi_bao_gia_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

# Dùng ký tự chevron literal trong CSS content (utf-8) để tránh escape \25B8.
_STYLE = (
    '<style>'
    '.vd-tdbg{font-size:16.5px;line-height:1.72;color:#1f2937;}'
    '.vd-tdbg h2{font-size:22px;font-weight:800;color:#111827;margin:22px 0 10px;}'
    '.vd-tdbg h3{font-size:17px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-tdbg p{margin:0 0 10px;}'
    '.vd-tdbg ul,.vd-tdbg ol{margin:0 0 10px;padding-left:24px;}'
    '.vd-tdbg li{margin:5px 0;}'
    '.vd-tdbg b{color:#111827;}'
    '.vd-tdbg table{border-collapse:collapse;width:100%;margin:8px 0 12px;font-size:15.5px;}'
    '.vd-tdbg th,.vd-tdbg td{border:1px solid #e5e7eb;padding:8px 12px;text-align:left;vertical-align:top;}'
    '.vd-tdbg th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-tdbg .no{color:#b91c1c;font-weight:700;}'
    '.vd-tdbg .ok{color:#15803d;font-weight:700;}'
    # --- ẩn marker mặc định của summary ---
    '.vd-tdbg summary{list-style:none;cursor:pointer;user-select:none;}'
    '.vd-tdbg summary::-webkit-details-marker{display:none;}'
    '.vd-tdbg summary::marker{content:"";}'
    # --- Thẻ bài học ---
    '.vd-tdbg details.vd-lesson{border-radius:12px;margin:16px 0;overflow:hidden;'
    'box-shadow:0 4px 16px rgba(2,6,23,.08);}'
    '.vd-tdbg summary.vd-lsum{position:relative;background:#1e293b;'
    'padding:16px 22px 16px 50px;}'
    '.vd-tdbg summary.vd-lsum::before{content:"\\203A";position:absolute;left:22px;top:14px;'
    'color:#f59e0b;font-size:24px;font-weight:800;transition:transform .2s;}'
    '.vd-tdbg details[open]>summary.vd-lsum::before{transform:rotate(90deg);}'
    '.vd-tdbg .vd-ltag{color:#f59e0b;font-size:12.5px;font-weight:800;letter-spacing:2px;}'
    '.vd-tdbg .vd-ltitle{color:#fff;font-size:20px;font-weight:800;margin-top:2px;line-height:1.25;}'
    '.vd-tdbg .vd-lsub{color:#cbd5e1;font-size:13.5px;margin-top:5px;}'
    '.vd-tdbg .vd-lbody{padding:8px 22px 18px;border:1px solid #e5e7eb;'
    'border-top:none;border-radius:0 0 12px 12px;}'
    # --- nhãn Lý thuyết ---
    '.vd-tdbg .vd-th{font-size:12px;font-weight:800;letter-spacing:.5px;'
    'color:#0369a1;text-transform:uppercase;margin:8px 0 6px;}'
    # --- nút Xem ví dụ ---
    '.vd-tdbg details.vd-ex{border:1px solid #bfdbfe;border-radius:10px;'
    'margin:12px 0;background:#f5faff;}'
    '.vd-tdbg summary.vd-exsum{padding:11px 16px;font-weight:800;color:#1d4ed8;font-size:15px;}'
    '.vd-tdbg .vd-exbody{padding:2px 16px 12px;}'
    # --- nút Làm bài tập ---
    '.vd-tdbg details.vd-task{border:2px solid #ea580c;border-radius:10px;margin:14px 0;background:#fff;}'
    '.vd-tdbg summary.vd-tasksum{padding:13px 16px;font-weight:800;color:#fff;'
    'background:#ea580c;font-size:15.5px;}'
    '.vd-tdbg .vd-taskbody{padding:14px 16px;}'
    '.vd-tdbg .vd-situation{font-style:italic;color:#7c2d12;background:#fff7ed;'
    'border-radius:8px;padding:10px 14px;margin:0 0 10px;}'
    '.vd-tdbg .vd-opt{border:1px solid #e5e7eb;border-radius:8px;padding:9px 12px;margin:6px 0;}'
    '.vd-tdbg .vd-optk{display:inline-block;width:24px;height:24px;line-height:24px;'
    'text-align:center;border-radius:50%;background:#f1f5f9;font-weight:800;'
    'margin-right:8px;color:#334155;}'
    '.vd-tdbg details.vd-ans{margin-top:8px;}'
    '.vd-tdbg summary.vd-anssum{color:#15803d;font-weight:800;padding:8px 0;}'
    '.vd-tdbg .vd-ansbody{background:#f0fdf4;border-left:4px solid #16a34a;'
    'border-radius:0 8px 8px 0;padding:10px 14px;}'
    # --- callout ---
    '.vd-tdbg .vd-key{background:#fff7ed;border-left:5px solid #e8401f;'
    'border-radius:0 8px 8px 0;padding:11px 15px;margin:12px 0;}'
    '.vd-tdbg .vd-key b{color:#c2410c;}'
    '</style>'
)


# ---------------------------------------------------------------------------
#  HELPER (nối chuỗi -> không lo bẫy %)
# ---------------------------------------------------------------------------
def _key(text):
    return '<div class="vd-key"><b>&#9873; Ghi nhớ:</b> ' + text + '</div>'


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _theory(inner):
    return '<div class="vd-th">&#128218; Lý thuyết rút gọn</div>' + inner


def _example(inner):
    return ('<details class="vd-ex"><summary class="vd-exsum">&#128204; Xem ví dụ thực tế</summary>'
            '<div class="vd-exbody">' + inner + '</div></details>')


def _opts(items):
    labels = ['A', 'B', 'C', 'D', 'E']
    lis = ''
    for i, t in enumerate(items):
        lis += ('<div class="vd-opt"><span class="vd-optk">' + labels[i] + '</span>'
                + t + '</div>')
    return lis


def _exercise(situation, options, answer):
    return ('<details class="vd-task"><summary class="vd-tasksum">'
            '&#9997;&#65039; Làm bài tập tình huống</summary>'
            '<div class="vd-taskbody">'
            '<div class="vd-situation">' + situation + '</div>'
            + _opts(options) +
            '<details class="vd-ans"><summary class="vd-anssum">'
            '&#128161; Xem đáp án &amp; giải thích</summary>'
            '<div class="vd-ansbody">' + answer + '</div></details>'
            '</div></details>')


def _lesson(tag, title, sub, inner, is_open=False):
    op = ' open' if is_open else ''
    return ('<details class="vd-lesson"' + op + '><summary class="vd-lsum">'
            '<div class="vd-ltag">' + tag + '</div>'
            '<div class="vd-ltitle">' + title + '</div>'
            '<div class="vd-lsub">' + sub + '</div></summary>'
            '<div class="vd-lbody">' + inner + '</div></details>')


def _hero():
    return (
        '<div style="background:#e8401f;border-radius:16px;padding:28px 26px;margin-bottom:10px;">'
        '<div style="color:#ffe0d8;font-size:14px;font-weight:700;letter-spacing:2px;">'
        'KỸ NĂNG SALE &mdash; CHỐT HỢP ĐỒNG</div>'
        '<div style="color:#ffffff;font-size:28px;font-weight:900;margin-top:8px;line-height:1.2;">'
        'Quy trình theo đuổi khách hàng sau khi gửi báo giá</div>'
        '<div style="color:#fff2ee;font-size:15.5px;margin-top:12px;line-height:1.6;">'
        'Gửi báo giá KHÔNG phải là kết thúc &mdash; đó chỉ là ĐIỂM BẮT ĐẦU của quá '
        'trình chốt hợp đồng.</div></div>'
        '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;'
        'padding:12px 16px;margin:10px 0 4px;color:#1e3a8a;font-size:14.5px;">'
        '&#128070; <b>Cách học:</b> Bấm vào từng mục để mở nội dung. Trong mỗi bài đi '
        'theo thứ tự: <b>Lý thuyết</b> &rarr; bấm <b>Xem ví dụ thực tế</b> &rarr; bấm '
        '<b>Làm bài tập tình huống</b> rồi tự chọn đáp án trước khi mở phần giải thích.</div>')


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
    #  NỘI DUNG - mỗi bài 1 thẻ <details> tương tác
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

    def _tdbg_muctieu(self):
        inner = (
            _theory(
                '<p>Đào tạo nhân viên hiểu: gửi báo giá <b>không phải là kết thúc</b>, '
                'mà là <b>điểm bắt đầu</b> của quá trình chốt hợp đồng. Rất nhiều nhân '
                'viên mất khách vì nghĩ &#8220;gửi báo giá rồi, giờ chờ khách gọi lại&#8221;.</p>'
                '<p>Sau khi gửi báo giá, mục tiêu KHÔNG phải là chờ khách ký, mà là '
                'từng bước đưa khách đi qua: <b>Báo giá &rarr; Phản hồi &rarr; Hiểu suy '
                'nghĩ khách &rarr; Giải quyết khúc mắc &rarr; Gửi hợp đồng &rarr; Giải '
                'quyết hợp đồng &rarr; Hẹn khảo sát &rarr; Ký hợp đồng</b>.</p>')
            + _key('Nếu khách im lặng thì quy trình đang bị DỪNG lại. Không được để '
                   'khách &#8220;treo&#8221;.')
            + _example(
                '<p>Khách hàng đang xây nhà thường cùng lúc: xem rất nhiều đơn vị '
                '&middot; chưa hiểu hết báo giá &middot; chưa biết nên hỏi gì &middot; '
                'đang cân nhắc tài chính &middot; đang so sánh. Nếu nhân viên không chủ '
                'động dẫn dắt, khách sẽ dần nghiêng về đơn vị khác.</p>'))
        return _lesson('MỤC TIÊU KHÓA HỌC', 'Gửi báo giá là bắt đầu, không phải kết thúc',
                       'Bấm để mở &middot; hiểu tư duy nền tảng của cả khóa.', inner,
                       is_open=True)

    def _tdbg_taonhom(self):
        inner = (
            _theory(
                '<p>Ngay sau khi gọi điện tư vấn cho khách xong: <b>bấm nút "Chốt báo '
                'giá"</b> rồi <b>LẬP TỨC tạo nhóm Zalo</b>. <b>CẤM nhắn tin riêng</b> '
                '(Zalo cá nhân) với khách &mdash; Zalo cá nhân chỉ để GỌI ĐIỆN, còn '
                'nhắn tin thì lái khách lên nhóm, mọi thông tin phản hồi TRÊN NHÓM.</p>'
                '<p><b>Quy trình tạo nhóm:</b></p>'
                '<ul>'
                '<li>Thành viên tối thiểu: <b>bản thân + khách hàng + trưởng phòng</b>.</li>'
                '<li>Ngay sau khi tạo: <b>đổi ảnh đại diện = logo công ty</b> + <b>đổi '
                'tên nhóm theo quy tắc quy định</b>.</li>'
                '<li>Gửi lên nhóm theo thứ tự: <b>(1) 4 video VTV</b> (đầu tiên) &rarr; '
                '<b>(2) lời chào giới thiệu bản thân</b> &rarr; <b>(3) tổng hợp nhu cầu '
                'công năng khách</b> &rarr; <b>(4) tối thiểu 20 mẫu nhà</b>.</li>'
                '<li>Đủ các bước trên mới nhắn tin bình thường &mdash; luôn trên nhóm.</li>'
                '</ul>')
            + _key('Không nhắn tin riêng cá nhân. Đưa khách làm quen với việc làm việc '
                   'trên NHÓM ngay từ tin nhắn đầu tiên.')
            + _example(
                '<p>Vì sao cấm nhắn tin riêng? Nhắn riêng kéo theo nhiều hệ lụy:</p>'
                + _table(['Rủi ro', 'Vì sao xảy ra'],
                         [['<b>Ký hợp đồng về sau rất khó</b>',
                           'Khách chỉ biết/quan tâm mỗi người tư vấn cá nhân (bạn), không quan tâm ai khác trong nhóm.'],
                          ['<b>Khó chuyển giao thiết kế - thi công</b>',
                           'Khách quen làm việc cá nhân, chỉ biết người ban đầu; về sau không muốn làm việc với người khác/tập thể.'],
                          ['<b>Kế toán thu tiền khó</b>',
                           'Khách không biết phải làm việc với ai để thanh toán.']],
                         widths=['32%', '68%']))
            + _exercise(
                'Bạn vừa gọi điện tư vấn xong cho một khách. Khách nhắn tin Zalo cá '
                'nhân hỏi thêm về giá. Bạn nên làm gì?',
                ['Trả lời chi tiết ngay trên Zalo cá nhân cho nhanh.',
                 'Tạo nhóm Zalo (mình + khách + trưởng phòng), đổi ảnh/tên nhóm, gửi 4 video VTV + giới thiệu + nhu cầu + 20 mẫu nhà, rồi trao đổi trên nhóm.',
                 'Bảo khách gọi điện lại, không nhắn tin gì cả.',
                 'Chờ trưởng phòng nhắn cho khách trước.'],
                '<b>Đáp án B.</b> Sau khi gọi xong phải chốt báo giá + tạo nhóm ngay, '
                'không phản hồi ở Zalo cá nhân. Trả lời riêng (A) vi phạm quy định và '
                'gây khó cho việc ký hợp đồng, chuyển giao, thu tiền về sau.'))
        return _lesson('GIAI ĐOẠN 0', 'Quy tắc tạo nhóm (bắt buộc đầu tiên)',
                       'Chốt báo giá + tạo nhóm ngay &middot; cấm nhắn tin riêng.', inner)

    def _tdbg_b1(self):
        inner = (
            _theory(
                '<p>Đừng gửi kiểu &#8220;Em gửi anh/chị tham khảo nhé&#8221;. Trước khi '
                'bấm gửi, tự trả lời 3 câu:</p>'
                '<ul>'
                '<li><b>1. Đúng nhu cầu khách không?</b> (tài chính, phong cách, mục đích xây)</li>'
                '<li><b>2. Giải quyết vấn đề tài chính chưa?</b> (vượt ngân sách? phương '
                'án tối ưu? giảm chi phí? giải thích rõ vì sao ra số tiền?)</li>'
                '<li><b>3. Đúng mong muốn chưa?</b> (số tầng, số phòng, phong cách, mức '
                'hoàn thiện, thang máy, gara, sân &mdash; tất cả phải khớp)</li>'
                '</ul>')
            + _key('Nhân viên phải tự tin: "Nếu mình là khách, mình cũng thấy báo giá '
                   'này hợp lý". Đó mới là báo giá đạt yêu cầu.')
            + _example(
                _table(['Khách nói / muốn', 'Nếu gửi lệch', 'Kết quả'],
                       [['Tài chính khoảng 2,8 tỷ', 'Gửi báo giá 3,8 tỷ', '<span class="no">SAI</span>'],
                        ['Khách thích hiện đại', 'Báo giá theo mẫu tân cổ', '<span class="no">SAI</span>'],
                        ['Khách muốn xây để ở', 'Làm theo tiêu chuẩn đầu tư', '<span class="no">SAI</span>']],
                       widths=['36%', '40%', '24%']))
            + _exercise(
                'Khách nói tài chính khoảng 2,8 tỷ. Báo giá bạn tính ra là 3,8 tỷ. Bạn nên làm gì?',
                ['Cứ gửi 3,8 tỷ, báo cao để còn thương lượng giảm.',
                 'Gửi 3,8 tỷ kèm câu "anh/chị tham khảo nhé".',
                 'Cân đối lại phương án (diện tích/công năng) cho khớp tầm 2,8 tỷ rồi mới gửi.',
                 'Gửi luôn để khách thấy đẳng cấp.'],
                '<b>Đáp án C.</b> Báo giá lệch tầm tài chính là vô tác dụng &mdash; '
                'khách sẽ loại mình. Phải cân đối cho khớp ngân sách rồi mới gửi.'))
        return _lesson('BƯỚC 1', 'Kiểm tra chất lượng báo giá trước khi gửi',
                       'Tự trả lời 3 câu hỏi trước khi bấm gửi.', inner)

    def _tdbg_b2(self):
        inner = (
            _theory(
                '<p>Sai lầm lớn nhất: gửi báo giá xong rồi <b>im luôn</b>. Sau <b>1&ndash;2 '
                'ngày bắt buộc phải lấy phản hồi</b> &mdash; không phải để ép ký, mà để '
                '<b>biết khách đang nghĩ gì</b>. Ví dụ khai thác: đã xem báo giá chưa? '
                'thấy phần nào hợp lý? phần nào băn khoăn? mức đầu tư phù hợp? có hạng '
                'mục nào muốn điều chỉnh?</p>')
            + _key('Khách im lặng KHÔNG có nghĩa là hết quan tâm. Việc của nhân viên là '
                   'KHAI THÁC, không phải ĐOÁN.')
            + _example(
                '<p>Khách im lặng có thể vì:</p>'
                + _table(['Lý do khách im lặng'],
                         [['Báo giá cao hơn dự kiến'], ['Báo giá chưa đúng nhu cầu'],
                          ['Chưa hiểu cách tính'], ['Đang chờ đơn vị khác'],
                          ['Chưa thấy đủ niềm tin'], ['Chưa biết nên hỏi gì']]))
            + _exercise(
                'Bạn gửi báo giá đã 2 ngày, khách không phản hồi gì. Bạn nên làm gì?',
                ['Coi như khách hết quan tâm, chuyển sang khách khác.',
                 'Chờ thêm 1 tuần cho khách tự nhắn lại.',
                 'Chủ động gọi/nhắn để khai thác: khách đã xem chưa, phần nào băn khoăn, mức đầu tư có phù hợp không.',
                 'Nhắn "anh/chị ký chưa ạ?" để chốt nhanh.'],
                '<b>Đáp án C.</b> Im lặng là tín hiệu cần tìm hiểu. Mục tiêu cuộc gọi '
                'là hiểu suy nghĩ khách, không phải ép ký (D sai).'))
        return _lesson('BƯỚC 2', 'Sau 1&ndash;2 ngày bắt buộc lấy phản hồi',
                       'Gọi để hiểu khách nghĩ gì, không phải để ép ký.', inner)

    def _tdbg_b3(self):
        inner = (
            _theory(
                '<p>Gửi mẫu nhà là việc bắt buộc, nhưng <b>KHÔNG được ép khách chốt '
                'mẫu</b>. Mục tiêu: cho khách thêm ý tưởng, thấy nhiều lựa chọn, xác '
                'định sở thích.</p>')
            + _key('Khách KHÔNG mua mẫu nhà &mdash; khách mua giải pháp phù hợp với gia '
                   'đình mình.')
            + _example(
                '<p><b>KHÔNG nói:</b> &#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;</p>'
                '<p><b>NÊN nói:</b> &#8220;Em gửi thêm một số mẫu nhà có diện tích và '
                'mức đầu tư gần với nhu cầu của anh/chị để mình tham khảo. Nếu có chi '
                'tiết nào anh/chị thích, bên em sẽ điều chỉnh thiết kế theo đúng mong '
                'muốn của gia đình.&#8221;</p>')
            + _exercise(
                'Khi gửi mẫu nhà cho khách tham khảo, câu nào KHÔNG nên nói?',
                ['&#8220;Anh chị chọn giúp em một mẫu nhé.&#8221;',
                 '&#8220;Em gửi vài mẫu gần nhu cầu để mình tham khảo.&#8221;',
                 '&#8220;Thích chi tiết nào bên em điều chỉnh thiết kế theo.&#8221;',
                 '&#8220;Mấy mẫu này để anh chị có thêm ý tưởng ạ.&#8221;'],
                '<b>Đáp án A.</b> Ép khách chốt mẫu tạo áp lực. Khách mua giải pháp, '
                'không mua mẫu nhà.'))
        return _lesson('BƯỚC 3', 'Gửi mẫu nhà cho khách tham khảo',
                       'Cho khách thêm ý tưởng &middot; không ép chốt mẫu.', inner)

    def _tdbg_b4(self):
        inner = (
            _theory(
                '<p>Đặc biệt cuối năm, khách nào cũng muốn xây xong trước Tết. Khởi '
                'công muộn dễ dẫn tới: thi công gấp, ảnh hưởng tiến độ, khó bàn giao, '
                'khó hoàn thiện. Nhân viên chủ động nhắc khách về yếu tố thời gian.</p>')
            + _key('Mục tiêu KHÔNG phải gây áp lực vô lý, mà giúp khách hiểu rõ hệ quả '
                   'của việc chậm quyết định.')
            + _example(
                '<p><b>Câu mẫu:</b> &#8220;Nếu gia đình mình dự kiến ở nhà mới trước '
                'Tết thì mình nên triển khai sớm để đảm bảo tiến độ. Nếu để quá sát '
                'thời điểm cuối năm thì việc hoàn thiện sẽ rất áp lực.&#8221;</p>')
            + _exercise(
                'Khách còn chần chừ, trong khi đã là cuối năm. Bạn nên nói thế nào?',
                ['&#8220;Không ký nhanh là giá tăng gấp đôi đấy ạ.&#8221;',
                 '&#8220;Công ty sắp hết suất nhận công trình rồi.&#8221;',
                 '&#8220;Nếu gia đình muốn ở nhà mới trước Tết thì nên triển khai sớm để đảm bảo tiến độ, để sát cuối năm hoàn thiện sẽ rất áp lực.&#8221;',
                 '&#8220;Anh/chị phải khởi công ngay trong tuần này.&#8221;'],
                '<b>Đáp án C.</b> Giúp khách hiểu hệ quả của việc chậm, không dọa dẫm '
                'hay ép buộc vô lý (A, B, D đều là gây áp lực).'))
        return _lesson('BƯỚC 4', 'Tạo cảm giác cần quyết định về thời gian khởi công',
                       'Nhắc yếu tố thời gian &middot; không gây áp lực vô lý.', inner)

    def _tdbg_b5(self):
        inner = (
            _theory(
                '<p><b>Đây là bước quan trọng nhất.</b> Nếu khách chưa ký, chắc chắn '
                'còn vấn đề &mdash; nhân viên phải TÌM RA, không tự suy đoán. Khai thác '
                'đủ 6 nhóm câu hỏi.</p>')
            + _key('Nhóm 6 &mdash; Niềm tin ("Còn điều gì khiến anh/chị chưa yên tâm '
                   'khi lựa chọn bên em?") giúp phát hiện RÀO CẢN THẬT SỰ trước khi ký.')
            + _example(
                _table(['Nhóm', 'Câu hỏi cần khai thác'],
                       [['1. Báo giá', 'Có phù hợp không? Vượt tài chính không? Cần điều chỉnh không?'],
                        ['2. Thiết kế', 'Có thích không? Thay đổi gì? Thêm công năng không?'],
                        ['3. Mẫu nhà', 'Đúng phong cách chưa? Muốn tham khảo thêm không?'],
                        ['4. Gia đình', 'Đã thống nhất chưa? Ai quyết định? Trao đổi thêm với người thân không?'],
                        ['5. Khởi công', 'Dự kiến khi nào? Đang chờ việc gì? Vướng thủ tục không?'],
                        ['6. Niềm tin', 'Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?']],
                       widths=['20%', '80%']))
            + _exercise(
                'Khách đã ưng báo giá và thiết kế nhưng vẫn chưa ký. Câu hỏi nào giúp '
                'lộ ra rào cản thật sự nhất?',
                ['&#8220;Có vượt tài chính không ạ?&#8221; (nhóm Báo giá)',
                 '&#8220;Đã đúng phong cách chưa ạ?&#8221; (nhóm Mẫu nhà)',
                 '&#8220;Dự kiến khởi công khi nào ạ?&#8221; (nhóm Khởi công)',
                 '&#8220;Còn điều gì khiến anh/chị chưa yên tâm khi chọn bên em?&#8221; (nhóm Niềm tin)'],
                '<b>Đáp án D.</b> Câu hỏi Niềm tin buộc khách nói ra rào cản thật sự '
                'còn ẩn giấu &mdash; thứ đang chặn khách ký.'))
        return _lesson('BƯỚC 5', 'Khai thác toàn bộ khúc mắc',
                       'Bước quan trọng nhất &middot; 6 nhóm câu hỏi.', inner)

    def _tdbg_b6(self):
        inner = (
            _theory(
                '<p>Khi khách đã: <b>đồng ý báo giá + đồng ý phương án + không còn vướng '
                'mắc lớn</b> thì đừng nói chuyện chung chung nữa &mdash; chuyển sang '
                '<b>gửi hợp đồng để khách nghiên cứu</b>.</p>')
            + _example(
                '<p><b>Câu mẫu:</b> &#8220;Để gia đình mình có thời gian xem kỹ các '
                'điều khoản, bên em sẽ gửi trước hợp đồng để anh/chị đọc. Nếu có nội '
                'dung nào cần giải thích hoặc điều chỉnh, em sẽ trao đổi ngay để mình '
                'yên tâm trước khi ký.&#8221;</p>')
            + _exercise(
                'Khi nào là thời điểm ĐÚNG để chuyển sang gửi hợp đồng?',
                ['Ngay khi vừa gửi báo giá, để tạo áp lực chốt.',
                 'Khi khách đã đồng ý báo giá + phương án và không còn vướng mắc lớn.',
                 'Khi khách mới chỉ hỏi giá lần đầu.',
                 'Khi khách còn nhiều băn khoăn nhưng mình muốn thúc.'],
                '<b>Đáp án B.</b> Chỉ gửi hợp đồng khi đã hết khúc mắc lớn &mdash; gửi '
                'quá sớm khi khách còn băn khoăn sẽ phản tác dụng.'))
        return _lesson('BƯỚC 6', 'Khi không còn khúc mắc thì gửi hợp đồng',
                       'Đủ điều kiện thì chuyển bước, không nói chung chung.', inner)

    def _tdbg_b7(self):
        inner = (
            _theory(
                '<p>Sai lầm của nhiều nhân viên: gửi hợp đồng xong rồi <b>mất hút</b>. '
                'Điều đúng: <b>sau 1&ndash;2 ngày phải hỏi</b> &mdash; đã xem hợp đồng '
                'chưa? có điều khoản nào chưa rõ? có nội dung nào muốn trao đổi thêm?</p>')
            + _key('Nếu khách còn băn khoăn thì KHÔNG được bỏ qua &mdash; phải giải '
                   'quyết ngay.')
            + _exercise(
                'Bạn đã gửi hợp đồng cho khách 2 ngày, chưa thấy phản hồi. Bạn nên làm gì?',
                ['Chờ khách tự đọc xong rồi ký gửi lại.',
                 'Chủ động hỏi lại: đã xem hợp đồng chưa, điều khoản nào chưa rõ, có nội dung nào muốn trao đổi thêm.',
                 'Nhắn giục khách ký ngay cho kịp.',
                 'Coi như khách không quan tâm nữa.'],
                '<b>Đáp án B.</b> Gửi hợp đồng xong phải theo dõi, chủ động hỏi lại sau '
                '1&ndash;2 ngày &mdash; "mất hút" là sai lầm phổ biến khiến mất khách.'))
        return _lesson('BƯỚC 7', 'Theo dõi hợp đồng',
                       'Gửi hợp đồng xong phải chủ động hỏi lại sau 1&ndash;2 ngày.', inner)

    def _tdbg_b8(self):
        inner = (
            _theory(
                '<p>Khi khách đã: <b>đồng ý báo giá + thiết kế + hợp đồng</b>, bước tiếp '
                'theo là: đề nghị lên lịch <b>khảo sát thực tế</b> + thống nhất <b>lịch '
                'ký hợp đồng</b>. Trao đổi rõ quy trình ký kết và khoản <b>đặt cọc '
                '50.000.000 đồng</b> theo quy định công ty (nếu áp dụng) để khách chủ '
                'động sắp xếp.</p>')
            + _exercise(
                'Khách đã đồng ý báo giá, thiết kế và hợp đồng. Bước tiếp theo là gì?',
                ['Gửi thêm một bộ báo giá mới để khách so sánh.',
                 'Quay lại gửi mẫu nhà từ đầu.',
                 'Đề nghị lịch khảo sát thực tế + thống nhất lịch ký, trao đổi rõ quy trình ký kết và khoản đặt cọc.',
                 'Chờ khách tự đến công ty ký.'],
                '<b>Đáp án C.</b> Đã đồng ý cả 3 thì chốt lịch khảo sát + ký và làm rõ '
                'khoản đặt cọc 50 triệu (nếu áp dụng).'))
        return _lesson('BƯỚC 8', 'Hẹn khảo sát và ký hợp đồng',
                       'Chốt lịch khảo sát + ký &middot; làm rõ đặt cọc 50 triệu.', inner)

    def _tdbg_gold(self):
        inner = (
            _theory(
                '<p style="font-size:18px;color:#111827;font-weight:700;">Một nhân viên '
                'kinh doanh giỏi không phải là người gửi được nhiều báo giá, mà là '
                'người biết dẫn dắt khách hàng đi qua từng bước của hành trình ra quyết '
                'định.</p>'
                '<p>Nếu sau mỗi lần liên hệ, khách hàng tiến thêm một bước (phản hồi '
                'báo giá, giải quyết khúc mắc, xem hợp đồng, hẹn khảo sát...) thì khả '
                'năng ký hợp đồng sẽ tăng lên rất nhiều.</p>')
            + _key('Không bao giờ để khách &#8220;im lặng&#8221; quá lâu. Mỗi lần tương '
                   'tác đều phải có mục tiêu rõ ràng và đưa khách tiến gần hơn tới quyết '
                   'định ký hợp đồng.'))
        return _lesson('&#127942; NGUYÊN TẮC VÀNG', 'Dẫn dắt khách qua từng bước',
                       'Tổng kết tư duy cốt lõi của cả khóa.', inner)

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (bài thi chấm điểm) - bám sát file + tạo nhóm.
    #  Đáp án nhiễu đều hợp lý để NV phải phân vân. (đáp án, đúng?)
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
