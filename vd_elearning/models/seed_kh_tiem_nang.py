# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa học
"Kỹ năng nhận diện khách hàng tiềm năng trong xây nhà trọn gói".

Thiết kế chuyên nghiệp: bảng so sánh, icon, khung công thức, tình huống,
lời khuyên, chứng minh, và ô "ÁP DỤNG NGAY" ép nhân viên thực hành.
Giữ ĐẦY ĐỦ nội dung gốc, chỉ viết THÊM (không cắt bớt).

Idempotent theo PHIÊN BẢN: lưu version vào ir.config_parameter. Nếu version
trùng -> bỏ qua (không ghi đè sửa tay của admin). Khi bump version -> xóa nội
dung tự sinh cũ và seed lại bản mới. HTML lưu ở slide.slide.vd_body
(sanitize=False) nên giữ nguyên bảng / style inline.
"""
from odoo import api, models

# Bump giá trị này mỗi khi muốn ghi đè lại toàn bộ nội dung tự sinh.
_KHTN_VERSION = 'v2-co-dau'
_PARAM_KEY = 'vd_elearning.khtn_seed_version'

# ------- Các khung (callout) dùng lại - style inline vì SCSS không phủ -------
_WRAP = (
    'font-size:15px;line-height:1.65;color:#2b2f44;'
    'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
)


def _box(border, bg, icon, title, inner):
    return (
        '<div style="border-left:6px solid %s;background:%s;border-radius:10px;'
        'padding:14px 16px;margin:16px 0;">'
        '<div style="font-weight:800;color:%s;margin-bottom:6px;font-size:14px;'
        'text-transform:uppercase;letter-spacing:.3px;">%s %s</div>'
        '<div>%s</div></div>'
    ) % (border, bg, border, icon, title, inner)


def _formula(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">CÔNG THỨC PHẢI THUỘC LÒNG</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _apply(inner):
    return (
        '<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;'
        'padding:16px 18px;margin:18px 0;">'
        '<div style="font-weight:900;color:#b91c1c;font-size:15px;margin-bottom:8px;">'
        '&#128308; BẮT BUỘC ÁP DỤNG NGAY (cuộc gọi tiếp theo)</div>'
        '<div>%s</div></div>'
    ) % inner


def _situation(inner):
    return _box('#2563eb', '#eff6ff', '&#127916;', 'Tình huống thực tế', inner)


def _advice(inner):
    return _box('#16a34a', '#f0fdf4', '&#128161;', 'Lời khuyên', inner)


def _proof(inner):
    return _box('#9333ea', '#faf5ff', '&#9989;', 'Chứng minh', inner)


def _mistake(inner):
    return _box('#ea580c', '#fff7ed', '&#9888;&#65039;', 'Sai lầm thường gặp', inner)


class SlideChannelSeedKHTN(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_kh_tiem_nang(self):
        ch = self.env.ref('vd_elearning.course_kh_tiem_nang', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _KHTN_VERSION:
            # Đã seed đúng phiên bản này -> giữ nguyên (tôn trọng sửa tay admin).
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        # Bump version -> xóa nội dung tự sinh cũ rồi seed lại bản mới.
        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        seq = 1
        for title, body in self._vd_khtn_pages():
            Slide.create({
                'channel_id': ch.id, 'name': title,
                'slide_category': 'article',
                'vd_body': '<div style="%s">%s</div>' % (_WRAP, body),
                'sequence': seq, 'is_published': True,
            })
            seq += 1

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_khtn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _KHTN_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC
    # ==================================================================
    def _vd_khtn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Bản chất & Mục tiêu', self._page1(h2, h3, lead)),
            ('2. Tiêu chí 1 - Thời gian khởi công', self._page2(h2, h3, lead)),
            ('3. Tiêu chí 2 - Tài chính + Mẫu nhà + Đất', self._page3(h2, h3, lead)),
            ('4. 4 câu hỏi vàng phải hỏi', self._page4(h2, h3, lead)),
            ('5. Phân loại khách A / B / C', self._page5(h2, h3, lead)),
            ('6. Cách chốt & Kết luận', self._page6(h2, h3, lead)),
        ]

    def _page1(self, h2, h3, lead):
        return (
            '<p style="' + lead + '">Trong ngành <b>xây nhà trọn gói</b>, khách có ký '
            'hợp đồng hay không gần như chỉ phụ thuộc vào <b>2 yếu tố cốt lõi</b>. Nắm '
            'được 2 yếu tố này, bạn thôi "đoán mò" và biết chính xác nên đầu tư thời '
            'gian vào ai.</p>'

            '<table><thead><tr><th style="width:56px;">#</th>'
            '<th>2 yếu tố cốt lõi quyết định khách có ký hợp đồng</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>YẾU TỐ 1:</b> Khách có <b>thời gian khởi công thật</b> hay không.</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>YẾU TỐ 2:</b> <b>Tài chính + Mẫu nhà + Diện tích đất</b> có khớp nhau hay không.</td></tr>'
            '</tbody></table>'

            '<h2 style="' + h2 + '">&#127891; Mục tiêu bài học</h2>'
            '<p>Sau khi học xong, nhân viên <b>phải</b>:</p>'
            '<ul>'
            '<li>Biết khách nào thực sự có khả năng <b>ký hợp đồng</b>.</li>'
            '<li>Biết khách nào chỉ đang <b>tham khảo</b>.</li>'
            '<li>Biết phải <b>hỏi gì</b> để xác định khách.</li>'
            '<li>Biết phải <b>tư vấn gì</b> để kéo khách ký sớm.</li>'
            '<li>Biết cách phát hiện khách tiềm năng dù khách <b>nói rất ít</b>.</li>'
            '</ul>'

            '<h2 style="' + h2 + '">PHẦN 1 &mdash; Bản chất khách hàng tiềm năng là gì</h2>'
            + _mistake(
                '<ul>'
                '<li>Khách nói nhiều &rArr; tưởng tiềm năng.</li>'
                '<li>Khách hỏi nhiều &rArr; tưởng tiềm năng.</li>'
                '<li>Khách xin nhiều mẫu &rArr; tưởng tiềm năng.</li>'
                '</ul>'
                '<p style="margin-bottom:0;"><b>Thực tế:</b> khách hàng tiềm năng '
                '<u>không</u> được xác định bằng việc khách nói nhiều hay ít.</p>'
            )
            + '<p>Khách hàng tiềm năng được xác định bằng <b>2 tiêu chí</b>:</p>'
            '<table><thead><tr><th style="width:90px;">Tiêu chí</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:800;color:#b91c1c;">SỐ 1</td>'
            '<td>Khách có <b>kế hoạch khởi công thực tế</b>.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#b91c1c;">SỐ 2</td>'
            '<td>Tài chính của khách <b>phù hợp với mẫu nhà mong muốn</b>.</td></tr>'
            '</tbody></table>'
            '<p style="text-align:center;font-size:16px;">Có đủ 2 yếu tố &rArr; '
            '<b style="color:#16a34a;">&#10145; Khách chính là khách hàng tiềm năng.</b></p>'

            + _apply(
                '<p>Mở lại 3 khách gần nhất bạn đang theo. Với từng khách tự chấm '
                '"Có / Chưa biết" cho 2 cột:</p>'
                '<ol><li>Khách có <b>thời gian khởi công</b> chưa?</li>'
                '<li>Tài chính có <b>khớp mẫu nhà</b> chưa?</li></ol>'
                '<p style="margin-bottom:0;">Khách nào cả 2 cột đều trống &rArr; bạn '
                'đang <b>tốn thời gian nhầm người</b>, cần xác minh lại ngay.</p>'
            )
        )

    def _page2(self, h2, h3, lead):
        def stars(n):
            return ('<span style="color:#f59e0b;font-size:17px;">' + ('&#9733;' * n)
                    + '</span><span style="color:#d1d5db;font-size:17px;">'
                    + ('&#9733;' * (5 - n)) + '</span>')
        return (
            '<h2 style="' + h2 + '">PHẦN 2 &mdash; Tiêu chí 1: Thời gian khởi công</h2>'
            '<h3 style="' + h3 + '">Tại sao đây là tiêu chí quan trọng nhất?</h3>'
            '<p>Bởi vì <b>người xây nhà thật luôn có kế hoạch</b>. Có thể là: tháng sau '
            'xây &middot; sau Tết xây &middot; 2 tháng nữa xây &middot; đợi hoàn tất thủ '
            'tục là xây&hellip; nhưng <b>luôn có thời gian dự kiến</b>.</p>'
            '<p>Ngược lại, người <b>chưa có nhu cầu thật</b> thường nói: "đang xem thôi", '
            '"chưa biết", "từ từ tính", "để tham khảo trước".</p>'

            + _proof(
                '<p style="margin-bottom:0;">Người sắp khởi công đã có ràng buộc thực tế '
                '(đất, tiền, gia đình, thời điểm đẹp) nên <b>họ buộc phải có mốc thời '
                'gian</b>. Còn người chỉ tham khảo thì không có áp lực nào &rArr; câu trả '
                'lời luôn mơ hồ. Vì vậy, <b>thời gian là phép thử thật-giả chính xác '
                'nhất</b>.</p>'
            )

            + '<h2 style="' + h2 + '">Cách nhận biết qua mốc thời gian</h2>'
            '<table><thead><tr><th>Nhóm khách</th><th>Khách nói thế nào</th>'
            '<th style="width:120px;text-align:center;">Mức độ</th><th>Hành động</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">Cực kỳ tiềm năng</b></td>'
            '<td>"Qua Tết anh xây", "Tháng 2 âm anh làm móng", "Cuối năm anh khởi công", '
            '"Đất xong rồi, giờ đang chuẩn bị".</td>'
            '<td style="text-align:center;">' + stars(5) + '</td>'
            '<td><b>Phải bám sát.</b></td></tr>'
            '<tr><td><b style="color:#d97706;">Tiềm năng trung bình</b></td>'
            '<td>"Chắc trong năm nay xây", "Đang chuẩn bị tài chính", "Đang hoàn thiện giấy tờ".</td>'
            '<td style="text-align:center;">' + stars(3) + '</td>'
            '<td>Cần theo dõi.</td></tr>'
            '<tr><td><b style="color:#6b7280;">Tham khảo</b></td>'
            '<td>"Chưa biết", "Đang tìm hiểu", "Hỏi trước thôi".</td>'
            '<td style="text-align:center;">' + stars(1) + '</td>'
            '<td>Không dành quá nhiều thời gian.</td></tr>'
            '</tbody></table>'

            + _situation(
                '<p>Khách nhắn tin: <i>"Em gửi anh vài mẫu nhà 2 tầng đi."</i></p>'
                '<p><b>NV yếu</b> gửi ngay 10 mẫu rồi&hellip; im. <b>NV giỏi</b> gửi mẫu '
                'kèm 1 câu: <i>"Dạ anh, để em chọn mẫu hợp nhất, anh dự kiến khoảng khi '
                'nào mình khởi công ạ?"</i></p>'
                '<p style="margin-bottom:0;">Chính câu hỏi thời gian mới <b>lọc ra</b> '
                'khách thật.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Đừng vội báo giá khi <b>chưa biết mốc thời '
                'gian</b>. Không có thời gian khởi công &rArr; mọi báo giá, mọi mẫu nhà '
                'đều chỉ để "tham khảo", rất dễ bị so sánh và mất khách.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Trong <b>3 cuộc gọi tiếp theo</b>, bắt buộc '
                'hỏi câu: <i>"Anh/chị dự kiến khoảng thời gian nào sẽ bắt đầu triển khai '
                'xây dựng ạ?"</i> &mdash; rồi ghi mốc thời gian vào hồ sơ khách. Không có '
                'mốc &rArr; xếp nhóm tham khảo (1&#9733;).</p>'
            )
        )

    def _page3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 3 &mdash; Tiêu chí 2: Tài chính + Mẫu nhà + Diện tích đất</h2>'
            '<p style="' + lead + '">Đây là tiêu chí <b>quyết định khách có ký được hay '
            'không</b>. Thời gian cho biết khách "có thật", còn bộ ba Tài chính - Mẫu - '
            'Đất cho biết khách "<b>khả thi</b>".</p>'

            '<h3 style="' + h3 + '">So sánh 2 ví dụ (cùng miếng đất 5x20)</h3>'
            '<table><thead><tr><th>Yếu tố</th>'
            '<th style="text-align:center;">Ví dụ 1</th>'
            '<th style="text-align:center;">Ví dụ 2</th></tr></thead><tbody>'
            '<tr><td><b>Diện tích đất</b></td><td style="text-align:center;">5 x 20</td>'
            '<td style="text-align:center;">5 x 20</td></tr>'
            '<tr><td><b>Mẫu nhà khách thích</b></td>'
            '<td style="text-align:center;">2 tầng hiện đại</td>'
            '<td style="text-align:center;">Tân cổ điển 3 tầng</td></tr>'
            '<tr><td><b>Tài chính</b></td>'
            '<td style="text-align:center;">1,4 tỷ</td>'
            '<td style="text-align:center;">1 tỷ</td></tr>'
            '<tr><td><b>Kết luận</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">&#9989; Hợp lý &rArr; rất tiềm năng</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">&#10060; Không khả thi &rArr; chưa tiềm năng</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Cùng 1 miếng đất nhưng mẫu nhà + tài chính '
                'khác nhau cho ra 2 kết quả ngược nhau. &rArr; Không phải khách cứ có tiền '
                'là ký được; <b>tiền phải khớp với mẫu nhà và diện tích</b>. Đây là lý do '
                'phải hỏi đủ cả 3 thông tin trước khi báo giá.</p>'
            )

            + _formula(
                'Khách tiềm năng = <span style="color:#1d4ed8;">Thời gian xây rõ ràng</span> '
                '&#10133; <span style="color:#16a34a;">Tài chính phù hợp</span> '
                '&#10133; <span style="color:#9333ea;">Mẫu nhà phù hợp</span> '
                '&#10133; <span style="color:#b45309;">Diện tích đất phù hợp</span>'
            )

            + _situation(
                '<p>Khách: <i>"Anh có 1 tỷ, muốn xây tân cổ điển 3 tầng trên đất 5x20."</i></p>'
                '<p><b>NV yếu</b> im lặng hoặc gật đại rồi báo giá &rArr; khách sốc giá, bỏ đi.</p>'
                '<p style="margin-bottom:0;"><b>NV giỏi</b> cân đối: <i>"Dạ với 1 tỷ trên '
                'đất 5x20, em gợi ý phương án 2 tầng hiện đại vừa đẹp vừa đủ ngân sách, còn '
                'tân cổ điển mình tính khi ngân sách thoải hơn ạ."</i> &mdash; giữ khách + '
                'kéo về vùng khả thi.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Khi tài chính chưa khớp mẫu, <b>đừng từ chối '
                'khách</b> &mdash; hãy <b>điều chỉnh mẫu / phương án</b> về vùng khả thi. Đây '
                'chính là cách biến khách Nhóm B thành khách ký được (xem Phần 5).</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Với mỗi khách đang theo, điền đủ <b>3 ô</b>: '
                'Diện tích đất &mdash; Mẫu nhà mong muốn &mdash; Tài chính dự trù. Thiếu ô '
                'nào &rArr; hỏi bổ sung ngay ở cuộc gọi sau. <b>Không báo giá khi còn ô '
                'trống.</b></p>'
            )
        )

    def _page4(self, h2, h3, lead):
        rows = [
            ('1', 'Anh/chị dự kiến khoảng thời gian nào sẽ bắt đầu triển khai xây dựng?',
             'Xác định <b>thời gian khởi công</b>.'),
            ('2', 'Anh/chị đang dự trù khoảng bao nhiêu kinh phí cho căn nhà?',
             'Xác định <b>khả năng tài chính</b>.'),
            ('3', 'Anh/chị thích mẫu nhà theo phong cách nào?',
             'Xác định <b>nhu cầu thực</b>.'),
            ('4', 'Diện tích đất hiện tại của mình là bao nhiêu mét vuông ạ?',
             'Kiểm tra <b>tính khả thi</b>.'),
        ]
        body = (
            '<h2 style="' + h2 + '">PHẦN 4 &mdash; 4 câu hỏi vàng phải hỏi</h2>'
            '<p style="' + lead + '">Chỉ cần hỏi xong <b>4 câu</b> này là bạn đủ dữ liệu '
            'để phân loại khách và biết bước tiếp theo. Học thuộc và hỏi <b>tự nhiên</b> '
            'trong hội thoại, không hỏi dồn dập như điều tra.</p>'
            '<table><thead><tr><th style="width:48px;">Câu</th><th>Câu hỏi vàng</th>'
            '<th style="width:42%;">Mục đích</th></tr></thead><tbody>'
        )
        for n, q, m in rows:
            body += ('<tr><td style="text-align:center;font-weight:800;color:#b45309;">'
                     + n + '</td><td><i>"' + q + '"</i></td><td>' + m + '</td></tr>')
        body += '</tbody></table>'
        body += _formula(
            '4 câu hỏi vàng = <b>Thời gian</b> &#8226; <b>Tài chính</b> &#8226; '
            '<b>Mẫu nhà</b> &#8226; <b>Diện tích đất</b>'
        )
        body += _situation(
            '<p>Khách kiệm lời, chỉ nhắn tin "báo giá đi em". Thay vì báo giá ngay, hỏi '
            'gọn 1 câu ghép: <i>"Dạ để báo giá chuẩn nhất, anh cho em xin diện tích đất và '
            'dự kiến khi nào khởi công ạ?"</i></p>'
            '<p style="margin-bottom:0;">2 thông tin này lọc ra ngay khách thật hay '
            'tham khảo.</p>'
        )
        body += _advice(
            '<p style="margin-bottom:0;">Dán 4 câu hỏi vàng cạnh màn hình. Sau mỗi cuộc '
            'gọi, kiểm tra đã thu được <b>đủ 4 thông tin</b> chưa. Thiếu câu nào &rArr; lần '
            'sau hỏi tiếp câu đó.</p>'
        )
        body += _apply(
            '<p style="margin-bottom:0;">Tự viết lại <b>4 câu hỏi vàng theo giọng của bạn</b> '
            '(cho tự nhiên) và đọc to 3 lần trước khi gọi khách tiếp theo. Bắt buộc hỏi đủ '
            '4 câu trong cuộc gọi đó.</p>'
        )
        return body

    def _page5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 5 &mdash; Phân loại khách hàng</h2>'
            '<p style="' + lead + '">Sau khi có 4 thông tin, xếp khách vào 1 trong 3 nhóm '
            'để biết <b>mục tiêu xử lý</b> rõ ràng.</p>'
            '<table><thead><tr><th style="width:120px;">Nhóm</th><th>Đặc điểm</th>'
            '<th style="width:96px;text-align:center;">Mức độ</th><th>Mục tiêu xử lý</th></tr></thead><tbody>'

            '<tr><td><b style="color:#16a34a;">NHÓM A</b><br/>Cực kỳ tiềm năng</td>'
            '<td>Có thời gian khởi công &middot; Có tài chính phù hợp &middot; Có mẫu nhà phù hợp.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;&#9733;&#9733;&#9733;&#9733;</td>'
            '<td>&#10145; Kéo về <b>khảo sát</b>.<br/>&#10145; <b>Ký giữ giá</b>.</td></tr>'

            '<tr><td><b style="color:#d97706;">NHÓM B</b><br/>Tiềm năng chưa chín</td>'
            '<td>Có thời gian xây, nhưng <b>tài chính chưa đủ</b> hoặc <b>chưa chọn được mẫu</b>.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;&#9733;&#9733;</td>'
            '<td>&#10145; Tư vấn <b>cân đối tài chính</b>.<br/>&#10145; <b>Điều chỉnh mẫu nhà</b>.<br/>'
            '&#10145; Hoàn thiện phương án.</td></tr>'

            '<tr><td><b style="color:#6b7280;">NHÓM C</b><br/>Tham khảo</td>'
            '<td>Chưa có thời gian xây &middot; Chưa có tài chính &middot; Chưa có nhu cầu rõ.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;</td>'
            '<td>&#10145; Giữ liên hệ.<br/>&#10145; Chăm sóc định kỳ.<br/>'
            '<b style="color:#dc2626;">Không dồn ký.</b></td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Phân nhóm giúp bạn <b>phân bổ thời gian đúng '
                'chỗ</b>: dồn lực vào Nhóm A (sắp ký), nuôi dưỡng Nhóm B (sửa phương án cho '
                'khả thi), và không "đốt" năng lượng vào Nhóm C. Đúng nhóm &rArr; tỷ lệ chốt '
                'tăng, thời gian không bị lãng phí.</p>'
            )

            + _mistake(
                '<p style="margin-bottom:0;">Dồn ký Nhóm C (chưa có thời gian, chưa có tiền) '
                '&rArr; khách sợ, mất thiện cảm, và bạn mất thời gian đáng lẽ dành cho Nhóm A.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Với Nhóm B, đừng bỏ &mdash; đây là "mỏ vàng" '
                'thường bị bỏ qua. Chỉ cần <b>cân đối tài chính / đổi mẫu cho khớp</b> là họ '
                'lên Nhóm A. Học kỹ các khóa "Cân đối tiền", "Chuyển đổi mẫu nhà" để xử lý '
                'Nhóm B.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Ngay hôm nay, gắn <b>nhãn A / B / C</b> cho tất '
                'cả khách bạn đang theo. Liệt kê rõ: Nhóm A gọi lịch khảo sát trước; Nhóm B '
                'ghi rõ "thiếu gì" (tiền hay mẫu) để xử lý.</p>'
            )
        )

    def _page6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 6 &mdash; Cách chốt khách tiềm năng</h2>'
            '<p style="' + lead + '">Khi khách đã có <b>đủ 3 điều kiện</b> (&#9989; thời '
            'gian xây &middot; &#9989; tài chính phù hợp &middot; &#9989; mẫu nhà phù hợp) '
            'thì <b>không tư vấn lan man nữa</b>. Chuyển ngay sang 3 bước chốt:</p>'

            '<table><thead><tr><th style="width:140px;">Bước chốt</th><th>Câu nói mẫu</th></tr></thead><tbody>'
            '<tr><td><b>&#128205; Khảo sát</b></td>'
            '<td><i>"Để phương án chính xác nhất, em xin lịch khảo sát thực tế giúp '
            'anh/chị."</i></td></tr>'
            '<tr><td><b>&#128176; Giữ giá</b></td>'
            '<td><i>"Hiện tại bên em đang áp dụng chính sách giữ giá 12 tháng, mình chốt '
            'sớm sẽ chủ động hơn rất nhiều khi triển khai."</i></td></tr>'
            '<tr><td><b>&#128396; Thiết kế sớm</b></td>'
            '<td><i>"Những khách chuẩn bị xây sau Tết thường triển khai thiết kế từ bây giờ '
            'để có thời gian chỉnh sửa công năng, tránh sát ngày thi công phải sửa nhiều '
            'lần."</i></td></tr>'
            '</tbody></table>'

            + _situation(
                '<p>Khách Nhóm A: "Qua Tết anh xây, anh có 1,4 tỷ, thích 2 tầng hiện đại, '
                'đất 5x20."</p>'
                '<p style="margin-bottom:0;">&rArr; Đủ điều kiện. Không gửi thêm mẫu để '
                '"suy nghĩ" nữa. Chốt lịch khảo sát + nêu chính sách giữ giá 12 tháng + đề '
                'xuất thiết kế sớm. <b>Càng kéo dài càng dễ mất vào tay đối thủ.</b></p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Kết luận nhân viên phải nhớ</h2>'
            + _formula(
                'Không phải khách nói nhiều / xin nhiều mẫu là tiềm năng.<br/>'
                'Khách tiềm năng thật = <b>(1) Thời gian khởi công tương đối rõ</b> '
                '&#10133; <b>(2) Tài chính phù hợp với mẫu nhà &amp; diện tích đất</b>.'
            )
            + '<p style="text-align:center;font-size:16px;">Có đủ 2 điều này &rArr; '
            '<b style="color:#16a34a;">Bám sát &#10145; Khảo sát &#10145; Giữ giá &#10145; '
            'Ký hợp đồng.</b></p>'
            '<p style="text-align:center;color:#475569;">Đó mới là khách hàng mang lại '
            '<b>doanh thu</b> cho công ty.</p>'

            + _apply(
                '<p>Bảng tự chấm trước khi rời mỗi khách (trả lời Có/Không):</p>'
                '<ol>'
                '<li>Đã biết <b>thời gian khởi công</b> chưa?</li>'
                '<li>Đã biết <b>tài chính</b> chưa?</li>'
                '<li>Đã biết <b>mẫu nhà + diện tích đất</b> chưa?</li>'
                '<li>Đã <b>xếp nhóm A/B/C</b> chưa?</li>'
                '<li>Nếu Nhóm A: đã <b>chốt khảo sát / nêu giữ giá</b> chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; đó chính là việc '
                'phải làm ở cuộc gọi tiếp theo.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    # ==================================================================
    def _vd_khtn_questions(self):
        T, F = True, False
        return [
            ('Trong xây nhà trọn gói, khách có ký hợp đồng hay không phụ thuộc chính vào mấy yếu tố cốt lõi?',
             [('2 yếu tố: thời gian khởi công và tài chính-mẫu-đất khớp nhau', T),
              ('1 yếu tố: khách nói nhiều hay ít', F),
              ('3 yếu tố: giá, khuyến mãi, quà tặng', F),
              ('Không yếu tố nào, hoàn toàn may rủi', F)]),

            ('Cách hiểu nào SAI về khách hàng tiềm năng?',
             [('Khách nói nhiều / xin nhiều mẫu nghĩa là tiềm năng', T),
              ('Khách có kế hoạch khởi công thực tế', F),
              ('Khách có tài chính phù hợp mẫu nhà', F),
              ('Khách có thời gian xây tương đối rõ', F)]),

            ('Hai tiêu chí xác định khách hàng tiềm năng là gì?',
             [('Có kế hoạch khởi công thực tế + tài chính phù hợp mẫu nhà', T),
              ('Nói nhiều + hỏi nhiều', F),
              ('Xin nhiều mẫu + trả giá giỏi', F),
              ('Ở gần công ty + quen biết', F)]),

            ('Tiêu chí nào được coi là QUAN TRỌNG NHẤT để lọc khách thật - giả?',
             [('Thời gian khởi công', T),
              ('Khách có thích nói chuyện không', F),
              ('Khách hỏi giá bao nhiêu lần', F),
              ('Số lượng mẫu khách xin', F)]),

            ('Câu nói nào thể hiện khách CHƯA có nhu cầu thật?',
             [('"Đang xem thôi, từ từ tính, để tham khảo trước"', T),
              ('"Qua Tết anh xây"', F),
              ('"Tháng 2 âm anh làm móng"', F),
              ('"Đất xong rồi, giờ đang chuẩn bị"', F)]),

            ('Khách nói "Qua Tết anh xây / Cuối năm anh khởi công / Đất xong rồi đang chuẩn bị" thuộc nhóm nào?',
             [('Khách cực kỳ tiềm năng (5 sao) - phải bám sát', T),
              ('Khách tham khảo (1 sao) - bỏ qua', F),
              ('Khách không có nhu cầu', F),
              ('Khách chỉ hỏi cho vui', F)]),

            ('Khách nói "Chắc trong năm nay xây, đang chuẩn bị tài chính, đang hoàn thiện giấy tờ" thuộc nhóm nào?',
             [('Tiềm năng trung bình (3 sao) - cần theo dõi', T),
              ('Cực kỳ tiềm năng (5 sao)', F),
              ('Tham khảo (1 sao)', F),
              ('Không tiềm năng', F)]),

            ('Với nhóm khách tham khảo (1 sao: "chưa biết, đang tìm hiểu, hỏi trước thôi"), nhân viên nên?',
             [('Không dành quá nhiều thời gian, giữ liên hệ chăm sóc định kỳ', T),
              ('Dồn hết sức ép ký ngay', F),
              ('Gọi liên tục mỗi ngày để ép', F),
              ('Báo giá thật thấp để ký gấp', F)]),

            ('Đất 5x20, khách thích nhà 2 tầng hiện đại, tài chính 1,4 tỷ. Đánh giá?',
             [('Hợp lý - đây là khách rất tiềm năng', T),
              ('Không khả thi', F),
              ('Không đủ tiền', F),
              ('Không xác định được', F)]),

            ('Đất 5x20, khách thích tân cổ điển 3 tầng, tài chính 1 tỷ. Đánh giá?',
             [('Không khả thi - chưa phải khách tiềm năng', T),
              ('Hợp lý - khách rất tiềm năng', F),
              ('Đủ tiền thoải mái', F),
              ('Chắc chắn ký được ngay', F)]),

            ('Công thức "Khách tiềm năng =" gồm đầy đủ những yếu tố nào?',
             [('Thời gian xây rõ ràng + Tài chính phù hợp + Mẫu nhà phù hợp + Diện tích đất phù hợp', T),
              ('Thời gian xây + số điện thoại', F),
              ('Tài chính + quà tặng', F),
              ('Mẫu nhà đẹp + giá rẻ', F)]),

            ('Mục đích của câu hỏi "Anh/chị dự kiến khoảng thời gian nào sẽ bắt đầu triển khai xây dựng?"',
             [('Xác định thời gian khởi công', T),
              ('Xác định tài chính', F),
              ('Xác định diện tích đất', F),
              ('Xác định phong cách mẫu nhà', F)]),

            ('Mục đích của câu hỏi "Anh/chị đang dự trù khoảng bao nhiêu kinh phí cho căn nhà?"',
             [('Xác định khả năng tài chính', T),
              ('Xác định thời gian khởi công', F),
              ('Xác định diện tích đất', F),
              ('Xác định mẫu nhà', F)]),

            ('Mục đích của câu hỏi "Diện tích đất hiện tại của mình là bao nhiêu mét vuông?"',
             [('Kiểm tra tính khả thi (mẫu + tài chính có khớp đất không)', T),
              ('Xác định thời gian khởi công', F),
              ('Xác định số tầng khách muốn', F),
              ('Để tính tiền hoa hồng', F)]),

            ('Khách NHÓM A (có thời gian + tài chính phù hợp + mẫu phù hợp) thì mục tiêu xử lý là?',
             [('Kéo về khảo sát và ký giữ giá', T),
              ('Giữ liên hệ, chăm sóc định kỳ', F),
              ('Chỉ gửi thêm mẫu rồi chờ', F),
              ('Không làm gì, đợi khách gọi lại', F)]),

            ('Khách NHÓM B (có thời gian xây nhưng tài chính chưa đủ hoặc chưa chọn mẫu) nên xử lý thế nào?',
             [('Tư vấn cân đối tài chính, điều chỉnh mẫu nhà, hoàn thiện phương án', T),
              ('Bỏ qua vì không đủ tiền', F),
              ('Ép ký ngay dù chưa khả thi', F),
              ('Báo giá cao hơn để lãi', F)]),

            ('Khách NHÓM C (chưa có thời gian, chưa có tài chính, chưa có nhu cầu rõ) thì?',
             [('Giữ liên hệ, chăm sóc định kỳ, KHÔNG dồn ký', T),
              ('Dồn ký càng sớm càng tốt', F),
              ('Gọi lịch khảo sát ngay', F),
              ('Ký giữ giá ngay lập tức', F)]),

            ('Khi khách đã đủ 3 điều kiện (thời gian, tài chính, mẫu nhà phù hợp), bước tiếp theo đúng nhất là?',
             [('Chuyển sang chốt: khảo sát - giữ giá - thiết kế sớm', T),
              ('Tiếp tục tư vấn lan man thêm nhiều mẫu', F),
              ('Cho khách tự suy nghĩ vô thời hạn', F),
              ('Gửi thêm bảng giá rồi im lặng', F)]),

            ('Câu nói "Hiện tại bên em đang áp dụng chính sách giữ giá 12 tháng, mình chốt sớm sẽ chủ động hơn" thuộc bước chốt nào?',
             [('Giữ giá', T),
              ('Khảo sát', F),
              ('Thiết kế sớm', F),
              ('Báo giá lại', F)]),

            ('Kết luận cốt lõi nhân viên phải nhớ là gì?',
             [('Khách tiềm năng thật phải có thời gian khởi công tương đối rõ VÀ tài chính phù hợp với mẫu nhà + diện tích đất', T),
              ('Khách nói càng nhiều càng tiềm năng', F),
              ('Khách xin càng nhiều mẫu càng dễ ký', F),
              ('Cứ báo giá thật thấp thì khách nào cũng ký', F)]),
        ]
