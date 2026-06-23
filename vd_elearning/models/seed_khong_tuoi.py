# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa học
"Xử lý khách CHƯA hợp tuổi xây nhà (mượn tuổi)".

Gộp 4 tài liệu gốc (Khái niệm / Danh sách tuổi / Tư vấn chi tiết / Chốt theo
từng ý) thành 1 khóa, RÚT GỌN ~30% (bỏ ví dụ trùng lặp, gộp 2 phần tư vấn +
chốt vốn trùng nhau), viết lại cho nhân viên dễ học - dễ nhớ - dễ áp dụng.

Trình bày theo FORM chuẩn khóa học VINADUY: khung công thức, tình huống, lời
khuyên, chứng minh, sai lầm, ô "ÁP DỤNG NGAY". Tái dùng helper khung từ
seed_kh_tiem_nang để đồng bộ giao diện.

Idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)

_KDT_VERSION = 'v2'
_PARAM_KEY = 'vd_elearning.khong_tuoi_seed_version'


def _chot(inner):
    """Khung CÂU CHỐT NGUYÊN TẮC - vàng đậm, để nhân viên thuộc lòng câu nói."""
    return (
        '<div style="border:2px solid #16a34a;background:#f0fdf4;border-radius:12px;'
        'padding:14px 16px;margin:16px 0;">'
        '<div style="font-weight:900;color:#15803d;font-size:14px;margin-bottom:6px;'
        'text-transform:uppercase;letter-spacing:.3px;">&#128172; CÂU CHỐT - THUỘC LÒNG</div>'
        '<div style="font-size:16px;font-weight:700;color:#14532d;font-style:italic;">'
        '%s</div></div>'
    ) % inner


class SlideChannelSeedKhongTuoi(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_khong_tuoi(self):
        ch = self.env.ref('vd_elearning.course_khong_tuoi', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _KDT_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_kdt_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': '<div style="%s">%s</div>' % (_WRAP, merged),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_kdt_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _KDT_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (5 phần)
    # ==================================================================
    def _vd_kdt_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Bản chất mượn tuổi', self._kt_p1(h2, h3, lead)),
            ('2. Quy trình mượn tuổi', self._kt_p2(h2, h3, lead)),
            ('3. Tuổi thuận lễ + cách trả lời', self._kt_p3(h2, h3, lead)),
            ('4. 5 hướng tư vấn & chốt', self._kt_p4(h2, h3, lead)),
            ('5. Kết luận & câu chốt', self._kt_p5(h2, h3, lead)),
        ]

    def _kt_p1(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127891; Mục tiêu khóa học</h2>'
            '<p style="' + lead + '">Khách viện cớ <b>"không hợp tuổi"</b> để hoãn xây là '
            'tình huống cực kỳ phổ biến. Học xong khóa này, nhân viên <b>gỡ được nỗi lo '
            'tuổi của khách trong 1-2 câu</b> và kéo khách về đúng việc: thiết kế - giữ '
            'giá - tiến độ.</p>'

            '<h2 style="' + h2 + '">PHẦN 1 &mdash; Mượn tuổi là gì?</h2>'
            '<p>Mượn tuổi = nhờ một người <b>hợp tuổi</b> đứng đại diện trong <b>nghi lễ '
            'động thổ</b>. Mục đích thuần <b>tinh thần</b> (giải hạn, gia chủ yên tâm).</p>'
            + _formula(
                'Mượn tuổi CHỈ dùng trong <span style="color:#1d4ed8;">nghi lễ động thổ</span> '
                '&mdash; KHÔNG liên quan <span style="color:#dc2626;">pháp lý, giấy tờ đất, '
                'hợp đồng, kỹ thuật, chất lượng</span> công trình.'
            )

            + '<h2 style="' + h2 + '">Ai được mượn tuổi?</h2>'
            '<p>Thứ tự ưu tiên: <b>Bố đẻ &rarr; Anh/Em trai &rarr; Chú-bác-cậu-dượng '
            '&rarr; Bạn thân/đồng nghiệp tin tưởng</b>. Điều kiện: hợp tuổi trong năm xây, '
            'gia đình hòa thuận, sẵn lòng cho mượn.</p>'
            '<table><thead><tr><th>Hiểu đúng (nói với khách)</th></tr></thead><tbody>'
            '<tr><td>Không bắt buộc là đàn ông (thường ưu tiên nam).</td></tr>'
            '<tr><td>Không cần cùng hộ khẩu, không cần đến ở cùng.</td></tr>'
            '<tr><td>Phụ nữ vẫn đứng tuổi được; nhà toàn nữ thì mượn tuổi chồng/bố.</td></tr>'
            '</tbody></table>'

            + '<h2 style="' + h2 + '">Người được mượn tuổi có bị ảnh hưởng gì không?</h2>'
            '<table><thead><tr><th style="width:38%;">Lo lắng của khách</th><th>Sự thật phải trấn an</th></tr></thead><tbody>'
            '<tr><td>Ảnh hưởng pháp lý?</td><td><b style="color:#16a34a;">KHÔNG</b> &mdash; không liên quan quyền sở hữu đất, giấy tờ nhà, hợp đồng.</td></tr>'
            '<tr><td>Ảnh hưởng tài vận - sức khỏe?</td><td><b style="color:#16a34a;">KHÔNG</b> &mdash; chỉ "đứng vía" trong lễ vài phút, truyền thống xưa nay rất phổ biến.</td></tr>'
            '<tr><td>Phải chịu trách nhiệm sau lễ?</td><td><b style="color:#16a34a;">KHÔNG</b> &mdash; xong lễ là xong vai, không giám sát, không làm lễ suốt thi công.</td></tr>'
            '</tbody></table>'
            + _chot(
                '"Anh cứ yên tâm, người được mượn tuổi chỉ đứng vía trong lễ động thổ vài '
                'phút, hoàn toàn không vướng trách nhiệm hay pháp lý gì."'
            )
            + _proof(
                '<p style="margin-bottom:0;">Vì không mất thời gian, không ảnh hưởng vận '
                'mệnh, thậm chí không cần có mặt (chỉ cần ghi tên), nên <b>~90% trường hợp '
                'người thân cho mượn tuổi ngay khi hỏi</b>.</p>'
            )
            + _apply(
                '<p style="margin-bottom:0;">Tự đọc to 3 lần câu chốt trấn an ở trên. Cuộc '
                'gọi tới, nếu khách nói "không hợp tuổi" &rArr; bật ngay câu này thay vì im '
                'lặng hay né tránh.</p>'
            )
        )

    def _kt_p2(self, h2, h3, lead):
        rows = [
            ('1', 'Chọn người phù hợp', 'Tuổi đẹp trong năm, ưu tiên nam trong nhà; không có thì mượn người thân khác.'),
            ('2', 'Hỏi mượn tuổi', '"Bố/anh cho con mượn tuổi làm lễ động thổ, chỉ là nghi thức phong thủy, không liên quan giấy tờ." &mdash; thường đồng ý ngay.'),
            ('3', 'Đưa thông tin cho thầy', 'Năm sinh người mượn tuổi + địa chỉ nhà + ngày dự kiến động thổ. Thầy chọn giờ đẹp, bài khấn, hướng đặt cuốc.'),
            ('4', 'Lễ động thổ', 'Có mặt: xúc 3 nhát cuốc đầu. Vắng mặt: gia chủ làm lễ và đọc tên người mượn tuổi (rất nhiều nhà làm cách này).'),
            ('5', 'Sau lễ', 'Vai trò người mượn tuổi KẾT THÚC. Hợp đồng - hồ sơ - nghiệm thu đều do chính chủ nhà làm.'),
            ('6', 'Nếu xây sang năm sau', 'KHÔNG đổi người, KHÔNG làm lại lễ. Thi công bình thường.'),
        ]
        body = (
            '<h2 style="' + h2 + '">PHẦN 2 &mdash; Quy trình mượn tuổi (6 bước)</h2>'
            '<p style="' + lead + '">Nói gọn để khách thấy <b>đơn giản, làm 10-15 phút</b>, '
            'không có gì phức tạp.</p>'
            '<table><thead><tr><th style="width:48px;">Bước</th><th style="width:150px;">Việc</th>'
            '<th>Nội dung</th></tr></thead><tbody>'
        )
        for n, t, d in rows:
            body += ('<tr><td style="text-align:center;font-weight:800;color:#b45309;">'
                     + n + '</td><td><b>' + t + '</b></td><td>' + d + '</td></tr>')
        body += '</tbody></table>'
        body += _chot(
            '"Mượn tuổi là nghi lễ nhỏ 10-15 phút. Tất cả thủ tục pháp lý, bản vẽ, giấy '
            'phép vẫn do anh đứng tên như bình thường."'
        )
        body += _mistake(
            '<p style="margin-bottom:0;">Đừng để khách nghĩ mượn tuổi là rườm rà, kéo dài. '
            'Càng làm khách thấy phức tạp &rArr; khách càng <b>hoãn xây</b>.</p>'
        )
        return body

    def _kt_p3(self, h2, h3, lead):
        body = (
            '<h2 style="' + h2 + '">PHẦN 3 &mdash; Tuổi thuận lễ &amp; cách trả lời</h2>'
            '<p style="' + lead + '">Nhân viên <b>chỉ cần nhớ 5 tuổi mỗi năm</b> &mdash; '
            'còn lại đều có thể mượn tuổi.</p>'
            '<table><thead><tr><th style="text-align:center;">Năm 2025 - thuận lễ nhất</th>'
            '<th style="text-align:center;">Năm 2026 - thuận lễ nhất</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;">1965 (Ất Tỵ)</td><td style="text-align:center;">1964 (Giáp Thìn)</td></tr>'
            '<tr><td style="text-align:center;">1974 (Giáp Dần)</td><td style="text-align:center;">1971 (Tân Hợi)</td></tr>'
            '<tr><td style="text-align:center;">1980 (Canh Thân)</td><td style="text-align:center;">1979 (Kỷ Mùi)</td></tr>'
            '<tr><td style="text-align:center;">1986 (Bính Dần)</td><td style="text-align:center;">1985 (Ất Sửu)</td></tr>'
            '<tr><td style="text-align:center;">1992 (Nhâm Thân)</td><td style="text-align:center;">1991 (Tân Mùi)</td></tr>'
            '</tbody></table>'
            + _formula(
                'Tuổi <span style="color:#16a34a;">thuận lễ</span> &rArr; làm lễ bình thường. '
                'Tuổi <span style="color:#b45309;">chưa thuận</span> &rArr; <b>mượn tuổi</b> là xong. '
                'KHÔNG có "tuổi xấu tuyệt đối".'
            )

            + '<h2 style="' + h2 + '">3 tình huống khi khách gửi tuổi nhờ kiểm tra</h2>'
            '<table><thead><tr><th style="width:34%;">Tình huống</th><th>Nhân viên trả lời</th></tr></thead><tbody>'
            '<tr><td><b>Tuổi khách thuận lễ</b></td>'
            '<td>"Dạ tuổi anh năm nay thuận lễ, làm lễ động thổ được ạ. Giờ mình lo phần '
            'thiết kế - báo giá - giữ giá trước cho kịp kế hoạch."</td></tr>'
            '<tr><td><b>Tuổi chưa thuận lễ</b></td>'
            '<td>"Tuổi anh năm nay chưa phải nhóm thuận lễ nhất, nhưng đơn giản lắm ạ &mdash; '
            'mình mượn tuổi bố/anh trai là thầy làm được ngay. Giấy tờ - pháp lý vẫn tên anh."</td></tr>'
            '<tr><td><b>Khách hỏi tuổi nào xấu/đẹp</b></td>'
            '<td>"Phong thủy bây giờ không có tuổi xấu tuyệt đối. Chỉ có tuổi thuận lễ và '
            'tuổi cần mượn lễ &mdash; nhà nào không hợp năm cũng mượn tuổi người thân, rất '
            'đơn giản."</td></tr>'
            '</tbody></table>'
            + _advice(
                '<p style="margin-bottom:0;">Luôn xoáy vào <b>giải pháp (mượn tuổi)</b>, '
                'không sa vào tranh luận "đúng - sai", "hợp - không hợp". Kết mỗi câu bằng '
                'một hành động: "anh gửi em năm sinh, 10 giây em xem nhanh cho anh".</p>'
            )
        )
        return body

    def _kt_p4(self, h2, h3, lead):
        body = (
            '<h2 style="' + h2 + '">PHẦN 4 &mdash; 5 hướng tư vấn &amp; chốt</h2>'
            '<p style="' + lead + '">Tùy kiểu khách, chọn 1 trong 5 hướng. Mỗi hướng có '
            '<b>1 câu chốt phải thuộc lòng</b> và tình huống nên dùng.</p>'
            '<table><thead><tr><th style="width:120px;">Hướng</th>'
            '<th>Câu chốt nguyên tắc</th><th style="width:30%;">Khi nào dùng</th></tr></thead><tbody>'
            '<tr><td><b style="color:#2563eb;">1. Tâm lý</b></td>'
            '<td><i>"Tuổi chỉ là nghi lễ tinh thần, còn tiến độ và chi phí mới là thứ quyết định."</i></td>'
            '<td>Khách lo hợp/không hợp, sợ xui, "để anh xem thầy đã".</td></tr>'
            '<tr><td><b style="color:#16a34a;">2. Tài chính</b></td>'
            '<td><i>"Giữ giá bây giờ là lợi nhất, còn tuổi thì mình mượn tuổi là xong."</i></td>'
            '<td>Khách đòi "để năm sau", viện tuổi để hoãn, sợ chi phí.</td></tr>'
            '<tr><td><b style="color:#9333ea;">3. Kinh doanh</b></td>'
            '<td><i>"Anh đang làm ăn thì càng không nên đứng tuổi - để người thân đứng tuổi cho chuẩn."</i></td>'
            '<td>Khách là chủ kinh doanh, đang buôn bán/đầu tư, tin phong thủy.</td></tr>'
            '<tr><td><b style="color:#b45309;">4. Kế hoạch</b></td>'
            '<td><i>"Xem tuổi là một chuyện, chuẩn bị thiết kế - hồ sơ là chuyện quan trọng hơn nhiều."</i></td>'
            '<td>Khách "để xem ngày đã", chưa vội nhưng vẫn muốn tham khảo, sợ bị ép ký.</td></tr>'
            '<tr><td><b style="color:#dc2626;">5. Tiến độ</b></td>'
            '<td><i>"Ngày đẹp tháng nào cũng có, còn lịch thợ đẹp chỉ vài đợt - mình chốt sớm để giữ lịch thợ."</i></td>'
            '<td>Khách phân vân thời điểm, "chờ xem tuổi đã", sợ chậm tiến độ.</td></tr>'
            '</tbody></table>'

            + _formula(
                'Chờ "đúng tuổi" = <span style="color:#dc2626;">vật tư tăng 5-15%/năm</span>. '
                'Nhà 1,2 tỷ tăng 10% &rArr; <b>đội ~120 triệu</b>. Mượn tuổi = '
                '<span style="color:#16a34a;">miễn phí, 5-15 phút</span>.'
            )

            + _situation(
                '<p>Khách: <i>"Thầy bảo anh không hợp tuổi, để năm sau xây."</i></p>'
                '<p style="margin-bottom:0;"><b>NV giỏi</b> ghép 2 hướng: <i>"Không hợp thì '
                'mình mượn tuổi bố là xong anh ạ (Tâm lý). Quan trọng là giữ giá bây giờ, chứ '
                'chờ năm sau vật tư tăng có khi đội cả trăm triệu (Tài chính)."</i></p>'
            )
            + _proof(
                '<p style="margin-bottom:0;">Hơn <b>50% khách</b> bên mình mượn tuổi. Các tòa '
                'nhà ngân hàng, tập đoàn xây quanh năm, không ai chờ tuổi từng người &mdash; '
                'họ ưu tiên kế hoạch - tài chính - tiến độ. Qua năm xây vẫn bình thường, công '
                'trình lớn còn kéo dài 1,5-2 năm.</p>'
            )
            + _apply(
                '<p style="margin-bottom:0;">Học thuộc <b>5 câu chốt nguyên tắc</b>. Cuộc gọi '
                'tới có khách viện tuổi &rArr; xác định khách thuộc kiểu nào (lo tâm lý? tiếc '
                'tiền? kinh doanh?) rồi bật <b>đúng câu chốt</b> tương ứng.</p>'
            )
        )
        return body

    def _kt_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 5 &mdash; Kết luận &amp; bộ câu chốt</h2>'
            + _formula(
                'Tuổi đẹp &rArr; làm lễ. Tuổi chưa đẹp &rArr; <b>mượn tuổi</b>. '
                'Việc quyết định ngôi nhà là <span style="color:#1d4ed8;">thiết kế - vật tư '
                '- thi công - tiến độ - chi phí</span>, KHÔNG phải tuổi.'
            )
            + '<h2 style="' + h2 + '">&#128221; Bộ câu chốt cuối (PHẢI THUỘC)</h2>'
            '<table><thead><tr><th style="width:56px;">#</th><th>Câu chốt</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;">1</td><td>"Không hợp tuổi thì mượn tuổi, nhà nào cũng làm."</td></tr>'
            '<tr><td style="text-align:center;">2</td><td>"Tuổi hợp thì làm lễ bình thường, dễ lắm anh ạ."</td></tr>'
            '<tr><td style="text-align:center;">3</td><td>"Quan trọng là giữ giá trước khi vật tư tăng."</td></tr>'
            '<tr><td style="text-align:center;">4</td><td>"Ngày đẹp tháng nào cũng có, nhưng lịch thợ thì không đợi mình."</td></tr>'
            '<tr><td style="text-align:center;">5</td><td>"Xây nhà không có tuổi kiêng tuyệt đối, phong thủy hiện đại linh hoạt lắm."</td></tr>'
            '</tbody></table>'
            + _advice(
                '<p style="margin-bottom:0;">Ngôn ngữ đời thường, dễ dùng: "Tuổi đẹp thì làm '
                'lễ, tuổi chưa đẹp thì mượn tuổi." &middot; "Thầy chỉ cần tuổi để đọc bài '
                'khấn, còn thi công thì tuổi nào cũng xây được."</p>'
            )
            + _apply(
                '<p>Trước khi gọi khách đang viện tuổi, tự kiểm tra:</p>'
                '<ol>'
                '<li>Đã thuộc <b>câu trấn an</b> "mượn tuổi không ảnh hưởng pháp lý" chưa?</li>'
                '<li>Đã nhớ <b>5 tuổi thuận lễ</b> của năm chưa?</li>'
                '<li>Khách thuộc kiểu nào &rArr; chọn <b>câu chốt</b> nào (trong 5 hướng)?</li>'
                '<li>Đã có <b>câu kéo về hành động</b> (xin năm sinh / chốt thiết kế - giữ giá) chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Ô nào chưa &rArr; chuẩn bị ngay trước khi bấm gọi.</p>'
            )
            + '<p style="text-align:center;font-size:16px;margin-top:14px;">Gỡ xong nỗi lo '
            'tuổi &rArr; <b style="color:#16a34a;">kéo khách về Thiết kế &#10145; Giữ giá '
            '&#10145; Chốt tiến độ.</b></p>'
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM. (đáp án, đúng?)
    # ==================================================================
    def _vd_kdt_questions(self):
        T, F = True, False
        return [
            ('"Mượn tuổi xây nhà" về bản chất là gì?',
             [('Nhờ người hợp tuổi đứng đại diện trong nghi lễ động thổ', T),
              ('Nhờ người khác đứng tên sổ đỏ', F),
              ('Nhờ người khác ký hợp đồng xây dựng', F),
              ('Nhờ người khác giám sát thi công', F)]),

            ('Người được mượn tuổi có liên quan đến pháp lý / giấy tờ đất / hợp đồng không?',
             [('Không liên quan gì cả - chỉ tham gia nghi lễ', T),
              ('Có, phải cùng đứng tên sổ đỏ', F),
              ('Có, phải ký hợp đồng với công ty', F),
              ('Có, phải chịu trách nhiệm pháp lý ngôi nhà', F)]),

            ('Thứ tự ưu tiên người được mượn tuổi đúng nhất là?',
             [('Bố đẻ → anh/em trai → chú-bác-cậu-dượng → bạn thân tin tưởng', T),
              ('Bắt buộc phải là người cùng hộ khẩu', F),
              ('Bắt buộc phải là người đến ở cùng nhà', F),
              ('Chỉ được mượn tuổi người ngoài, không mượn người thân', F)]),

            ('Phụ nữ có đứng tuổi xây nhà được không?',
             [('Được - không phân biệt nam nữ; nhà toàn nữ thì mượn tuổi chồng/bố', T),
              ('Không, chỉ đàn ông mới được đứng tuổi', F),
              ('Không, phụ nữ xây nhà là xui', F),
              ('Chỉ được nếu trên 40 tuổi', F)]),

            ('Sau lễ động thổ, vai trò của người được mượn tuổi thế nào?',
             [('Kết thúc ngay - không giám sát, không làm lễ suốt thi công', T),
              ('Phải giám sát toàn bộ công trình', F),
              ('Phải làm lễ lại mỗi tháng', F),
              ('Phải đứng tên nghiệm thu', F)]),

            ('Câu trấn an đúng khi khách lo người thân bị ảnh hưởng khi cho mượn tuổi?',
             [('"Người mượn tuổi chỉ đứng vía trong lễ vài phút, không vướng trách nhiệm hay pháp lý gì"', T),
              ('"Cho mượn tuổi có thể ảnh hưởng sức khỏe người đó"', F),
              ('"Người đó phải chịu rủi ro thay gia chủ"', F),
              ('"Người đó sẽ liên đới nếu nhà có vấn đề"', F)]),

            ('Trong quy trình 6 bước, ở bước Lễ động thổ nếu người mượn tuổi VẮNG mặt thì sao?',
             [('Gia chủ vẫn làm lễ bình thường và đọc tên người được mượn tuổi', T),
              ('Phải hoãn lễ đến khi người đó có mặt', F),
              ('Phải đổi sang người mượn tuổi khác', F),
              ('Phải hủy kế hoạch xây', F)]),

            ('Nếu công trình xây kéo dài sang năm sau thì cần làm gì với việc mượn tuổi?',
             [('Không cần đổi người, không phải làm lại lễ - thi công bình thường', T),
              ('Phải mượn tuổi người mới mỗi năm', F),
              ('Phải làm lại lễ động thổ đầu năm', F),
              ('Phải dừng thi công chờ tuổi mới', F)]),

            ('Nhân viên cần nhớ bao nhiêu tuổi thuận lễ mỗi năm?',
             [('Chỉ cần nhớ 5 tuổi mỗi năm, còn lại đều có thể mượn tuổi', T),
              ('Phải nhớ toàn bộ 60 tuổi', F),
              ('Phải nhớ 12 con giáp đầy đủ', F),
              ('Không cần nhớ tuổi nào', F)]),

            ('Theo tài liệu, tuổi nào dưới đây THUẬN LỄ nhất năm 2025?',
             [('1980 (Canh Thân)', T),
              ('1964 (Giáp Thìn)', F),
              ('1971 (Tân Hợi)', F),
              ('1985 (Ất Sửu)', F)]),

            ('Khi khách gửi tuổi mà KHÔNG nằm trong nhóm thuận lễ, nên trả lời thế nào?',
             [('Hướng ngay sang giải pháp: mượn tuổi bố/anh trai là thầy làm được', T),
              ('Khuyên khách hoãn xây sang năm sau', F),
              ('Nói tuổi khách xấu, không nên xây', F),
              ('Từ chối tư vấn vì không hợp tuổi', F)]),

            ('Phong thủy hiện đại quan niệm thế nào về "tuổi xấu"?',
             [('Không có tuổi xấu tuyệt đối - chỉ có tuổi thuận lễ và tuổi cần mượn lễ', T),
              ('Có nhiều tuổi xấu tuyệt đối phải tránh', F),
              ('Tuổi xấu thì cấm xây nhà vĩnh viễn', F),
              ('Tuổi xấu phải chờ đủ 3 năm mới xây', F)]),

            ('Câu chốt theo hướng TÂM LÝ là câu nào?',
             [('"Tuổi chỉ là nghi lễ tinh thần, còn tiến độ và chi phí mới là thứ quyết định"', T),
              ('"Giữ giá bây giờ là lợi nhất"', F),
              ('"Anh đang làm ăn thì không nên đứng tuổi"', F),
              ('"Ngày đẹp tháng nào cũng có"', F)]),

            ('Câu chốt theo hướng TÀI CHÍNH là câu nào?',
             [('"Giữ giá bây giờ là lợi nhất, còn tuổi thì mình mượn tuổi là xong"', T),
              ('"Tuổi chỉ là nghi lễ tinh thần"', F),
              ('"Xem tuổi là một chuyện, chuẩn bị hồ sơ là chuyện khác"', F),
              ('"Anh đang làm ăn thì không nên đứng tuổi"', F)]),

            ('Với khách là CHỦ KINH DOANH, hướng tư vấn phù hợp nhất?',
             [('Khuyên để người thân (bố/anh trai) đứng tuổi để giữ vía làm ăn', T),
              ('Bắt khách tự đứng tuổi cho chắc', F),
              ('Khuyên hoãn xây đến khi nghỉ kinh doanh', F),
              ('Nói kinh doanh thì không được xây nhà', F)]),

            ('Khách nói "Để anh xem ngày đã" - nên dùng hướng chốt nào?',
             [('Hướng Kế hoạch: "Xem tuổi là một chuyện, chuẩn bị thiết kế - hồ sơ quan trọng hơn nhiều"', T),
              ('Im lặng chờ khách tự quyết', F),
              ('Ép khách ký ngay lập tức', F),
              ('Nói khách không cần xem ngày', F)]),

            ('Vì sao "chờ đúng tuổi" có thể khiến khách thiệt hại tiền?',
             [('Vật tư tăng 5-15%/năm - nhà 1,2 tỷ tăng 10% là đội ~120 triệu', T),
              ('Vì phải trả phí mượn tuổi rất cao', F),
              ('Vì thầy phong thủy tính tiền theo tuổi', F),
              ('Vì mượn tuổi tốn vài chục triệu', F)]),

            ('Xây nhà KÉO DÀI qua năm (1,5-2 năm) thì sao?',
             [('Hoàn toàn bình thường - công trình lớn còn kéo dài, thời gian không nói lên chất lượng', T),
              ('Là điềm xấu, phải phá đi xây lại', F),
              ('Bắt buộc phải xong trong 1 năm', F),
              ('Phải làm lại lễ động thổ', F)]),

            ('Câu chốt theo hướng TIẾN ĐỘ nhấn mạnh điều gì?',
             [('Ngày đẹp tháng nào cũng có, nhưng lịch thợ đẹp chỉ vài đợt - chốt sớm giữ lịch', T),
              ('Phải chờ đúng ngày đẹp mới được khởi công', F),
              ('Thợ lúc nào cũng rảnh, không cần giữ lịch', F),
              ('Tiến độ không quan trọng bằng tuổi', F)]),

            ('Thông điệp cốt lõi nhân viên phải nhớ của khóa học này?',
             [('Tuổi đẹp thì làm lễ, chưa đẹp thì mượn tuổi; quyết định ngôi nhà là thiết kế-vật tư-thi công-tiến độ-chi phí, không phải tuổi', T),
              ('Phải chờ đúng tuổi mới được xây nhà', F),
              ('Tuổi quyết định chất lượng và độ bền ngôi nhà', F),
              ('Khách không hợp tuổi thì nên để khách đi', F)]),
        ]
