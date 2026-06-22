# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa học
"Chuẩn hóa 30 giây đầu khi gọi điện tư vấn xây nhà trọn gói".

Biến tài liệu gốc (6 lỗi 30 giây đầu + kịch bản chuẩn + xử lý khách hỏi lại +
chấm điểm) thành 1 khóa trình bày dễ hiểu - dễ nhớ - dễ áp dụng theo FORM
chuẩn khóa học VINADUY: khung công thức, tình huống, lời khuyên, chứng minh,
sai lầm, câu chốt phải thuộc lòng, ô "ÁP DỤNG NGAY".

Tái dùng helper khung từ seed_kh_tiem_nang + _chot từ seed_khong_tuoi để
đồng bộ giao diện.

Idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_S30_VERSION = 'v3'
_PARAM_KEY = 'vd_elearning.s30_dau_seed_version'


class SlideChannelSeed30sDau(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_30s_dau(self):
        ch = self.env.ref('vd_elearning.course_30s_dau', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _S30_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_s30_pages())
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
        for text, answers in self._vd_s30_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _S30_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (6 phần)
    # ==================================================================
    def _vd_s30_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Vì sao 30 giây đầu quyết định', self._s30_p1(h2, h3, lead)),
            ('2. Giới thiệu đúng nguồn khách', self._s30_p2(h2, h3, lead)),
            ('3. Giọng nói: to, rõ, có lực', self._s30_p3(h2, h3, lead)),
            ('4. 3 câu đầu phải liền mạch', self._s30_p4(h2, h3, lead)),
            ('5. Tư vấn chứ không tra khảo', self._s30_p5(h2, h3, lead)),
            ('6. Kịch bản chuẩn - Xử lý - Chấm điểm', self._s30_p6(h2, h3, lead)),
        ]

    def _s30_p1(self, h2, h3, lead):
        return (
            '<p style="' + lead + '">Trong tư vấn <b>xây nhà trọn gói</b>, <b>30 giây '
            'đầu tiên</b> quyết định khách có tiếp tục nghe hay cúp máy. Một nhân viên '
            'có thể chưa tư vấn giỏi, chưa chốt giỏi, nhưng <b>bắt buộc</b> phải làm '
            'đúng 3 việc đầu tiên.</p>'

            '<table><thead><tr><th style="width:56px;">#</th>'
            '<th>3 việc BẮT BUỘC làm đúng trong 30 giây đầu</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>VIỆC 1:</b> Giới thiệu <b>đúng nguồn khách</b> (Facebook / TikTok / mặc định).</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>VIỆC 2:</b> Nói <b>đủ to, rõ, dứt khoát</b>.</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>VIỆC 3:</b> Tạo cảm giác <b>đáng tin</b>, không phải gọi để tra khảo thông tin.</td></tr>'
            '</tbody></table>'

            '<h2 style="' + h2 + '">&#127891; Mục tiêu bài học</h2>'
            '<p>Sau khi học xong, nhân viên <b>phải</b>:</p>'
            '<ul>'
            '<li>Giới thiệu đúng theo <b>thứ khách đang nhớ</b> (thương hiệu Vinaduy / Sếp Hinh).</li>'
            '<li>Nói câu đầu <b>to - rõ - có lực</b>, không lí nhí, không xin lỗi.</li>'
            '<li>Nói <b>3 câu đầu liền mạch</b>, không đứt quãng.</li>'
            '<li>Chuyển từ <b>hỏi cung sang tư vấn</b> để khách mở lòng.</li>'
            '<li>Tự <b>nghe lại ghi âm</b> để sửa lỗi của chính mình.</li>'
            '</ul>'

            + _mistake(
                '<p>Nếu làm sai 30 giây đầu, khách phản ứng ngay:</p>'
                '<ul>'
                '<li>"Em bên nào đấy?" &middot; "Cái gì vậy em?" &middot; "Anh không nghe rõ."</li>'
                '<li>"Em nói to lên." &middot; "Anh đang bận." &rArr; <b>Cúp máy ngay.</b></li>'
                '<li>Không nghe máy những lần sau &middot; Mất niềm tin vì thấy thiếu chuyên nghiệp.</li>'
                '</ul>'
                '<p style="margin-bottom:0;">Đây là lỗi <b>nghiêm trọng</b>: công ty đã '
                '<b>mất tiền marketing</b> để có khách, nhưng nhân viên làm hỏng khách '
                'ngay từ câu đầu tiên.</p>'
            )

            + _formula(
                '30 giây đầu đạt chuẩn = <span style="color:#1d4ed8;">Đúng nguồn khách</span> '
                '&#10133; <span style="color:#16a34a;">Giọng to - rõ - có lực</span> '
                '&#10133; <span style="color:#9333ea;">3 câu liền mạch</span> '
                '&#10133; <span style="color:#b45309;">Tư vấn, không tra khảo</span>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Mở lại <b>3 cuộc gọi gần nhất</b> của bạn. '
                'Tự chấm "Đạt / Chưa" cho từng việc: (1) giới thiệu đúng nguồn, (2) câu '
                'đầu có to-rõ không, (3) 3 câu đầu có liền mạch không. Việc nào "Chưa" '
                '&rArr; đó là lỗi phải sửa ngay ở cuộc gọi tiếp theo.</p>'
            )
        )

    def _s30_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">LỖI 1 &mdash; Không phân biệt nguồn khách khi giới thiệu</h2>'
            '<p style="' + lead + '">Khách từ kênh khác nhau <b>nhớ thương hiệu khác nhau</b>. '
            'Khách <b>Facebook</b> thường nhớ <b>Vinaduy</b>. Khách <b>TikTok</b> thường nhớ '
            '<b>Sếp Hinh</b>. Giới thiệu sai &rArr; khách không nhận ra, nghi ngờ, mất kết '
            'nối, dễ cúp máy.</p>'

            + _proof(
                '<p style="margin-bottom:0;">Khách <b>không có trách nhiệm</b> phải nhớ '
                'công ty mình là ai &mdash; nhân viên phải nói đúng theo thứ khách đang '
                'nhớ. Khách nhớ Sếp Hinh mà mình nói Vinaduy &rArr; "Vinaduy là bên nào?". '
                'Khách nhớ Vinaduy mà mình nói Sếp Hinh &rArr; "Sếp Hinh là ai?". Chỉ cần '
                '<b>3&ndash;5 giây nghi ngờ</b> là cuộc gọi đã mất nhịp &rArr; tỷ lệ cúp '
                'máy rất cao.</p>'
            )

            + '<h2 style="' + h2 + '">3 trường hợp - 3 câu giới thiệu</h2>'
            '<table><thead><tr><th style="width:130px;">Nguồn khách</th>'
            '<th>Câu giới thiệu BẮT BUỘC</th></tr></thead><tbody>'
            '<tr><td><b style="color:#1d4ed8;">Facebook</b></td>'
            '<td>"Em chào anh/chị, em là [Tên] bên xây nhà trọn gói <b>Vinaduy</b>. Bên em '
            'vừa nhận được thông tin anh/chị quan tâm dịch vụ xây nhà trọn gói ạ."</td></tr>'
            '<tr><td><b style="color:#be185d;">TikTok</b></td>'
            '<td>"Em chào anh/chị, em là [Tên] bên xây nhà trọn gói <b>của Sếp Hinh</b>. '
            'Bên em vừa nhận được thông tin anh/chị quan tâm mẫu nhà / xây nhà trọn gói '
            'trên TikTok ạ."</td></tr>'
            '<tr><td><b style="color:#6b7280;">Không rõ nguồn</b></td>'
            '<td>"Em chào anh/chị, em là [Tên] bên xây nhà trọn gói <b>Vinaduy</b>. Bên em '
            'vừa nhận được thông tin anh/chị quan tâm đến xây nhà trọn gói ạ." (mặc định Vinaduy)</td></tr>'
            '</tbody></table>'

            + _mistake(
                '<ul>'
                '<li>Khách <b>Facebook</b> mà nói "em bên <b>Sếp Hinh</b>" &rArr; khách '
                'có thể không biết Sếp Hinh là ai.</li>'
                '<li>Khách <b>TikTok</b> mà chỉ nói "em bên <b>Vinaduy</b>" &rArr; khách '
                'nhớ Sếp Hinh, chưa chắc nhớ Vinaduy.</li>'
                '</ul>'
            )

            + _advice(
                '<p style="margin-bottom:0;"><b>Trước khi bấm gọi</b>, nhìn vào hồ sơ '
                'khách để biết nguồn (Facebook hay TikTok), rồi chọn đúng câu giới thiệu. '
                'Không xác định được nguồn &rArr; dùng câu mặc định Vinaduy.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Viết sẵn <b>2 câu giới thiệu</b> (Facebook + '
                'TikTok) thay [Tên] bằng tên bạn, dán cạnh màn hình. Trong cuộc gọi tiếp '
                'theo, <b>kiểm tra nguồn khách trước</b> rồi mới chào.</p>'
            )
        )

    def _s30_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">LỖI 2 &amp; LỖI 5 &mdash; Câu đầu nhỏ, yếu, thiếu bản lĩnh</h2>'
            '<p style="' + lead + '">Nhiều nhân viên vừa nghe máy đã nói rất nhỏ: '
            '<i>"Alo&hellip; em chào anh ạ&hellip; em bên xây nhà&hellip;"</i>. Giọng nhỏ '
            'làm khách thấy nhân viên <b>thiếu tự tin, không chuyên nghiệp, không đáng tin, '
            'giống telesale làm phiền</b>.</p>'

            + _proof(
                '<p style="margin-bottom:0;">Trong ngành xây nhà, khách bỏ ra <b>vài trăm '
                'triệu đến vài tỷ đồng</b>. Họ <b>không thể tin</b> một người nói chuyện '
                'yếu, run, nhỏ, thiếu chắc chắn. Nói quá mềm, quá nhẹ &rArr; khách nghĩ '
                '"bạn này non", "bạn này không chắc", "gọi cho có".</p>'
            )

            + '<h2 style="' + h2 + '">Yêu cầu bắt buộc về câu đầu</h2>'
            '<table><thead><tr><th style="text-align:center;width:50%;color:#16a34a;">PHẢI (nói có lực)</th>'
            '<th style="text-align:center;color:#dc2626;">KHÔNG (nói yếu)</th></tr></thead><tbody>'
            '<tr><td>To hơn bình thường <b>20&ndash;30%</b></td><td>Lí nhí, nói nhỏ</td></tr>'
            '<tr><td>Rõ <b>từng chữ</b>, dứt khoát</td><td>Kéo dài, ngập ngừng</td></tr>'
            '<tr><td>Tâm thế "tôi là người tư vấn xây dựng, gọi để giúp khách"</td>'
            '<td>Tâm thế "em xin lỗi vì đã làm phiền anh"</td></tr>'
            '</tbody></table>'

            '<p>Nói có lực <b>không phải</b> là quát khách hay nói cứng nhắc. Câu đúng có '
            '<b>3 yếu tố</b>: rõ ràng &middot; tự tin &middot; có lý do gọi hợp lý.</p>'

            + _situation(
                '<p><b>Sai:</b> <i>"Dạ em chào anh ạ&hellip; em bên xây nhà trọn gói ạ&hellip; '
                'không biết anh có nhu cầu không ạ&hellip;"</i></p>'
                '<p style="margin-bottom:0;"><b>Đúng:</b> <i>"Em chào anh ạ, em là Huy bên '
                'xây nhà trọn gói của Sếp Hinh. Bên em vừa nhận được thông tin anh quan tâm '
                'mẫu nhà trên TikTok, nên em gọi nhanh để tư vấn đúng nhu cầu của anh ạ."</i></p>'
            )

            + _chot(
                '"Em chào anh ạ, em là Huy bên xây nhà trọn gói của Sếp Hinh."<br/>'
                '"Em chào anh ạ, em là Huy bên xây nhà trọn gói Vinaduy."'
            )

            + _apply(
                '<p style="margin-bottom:0;"><b>Luyện giọng 30 lần/ngày</b>: đọc to - dứt '
                'khoát - không ngập ngừng - không kéo dài 2 câu giới thiệu (TikTok + '
                'Facebook). Trước mỗi cuộc gọi, đọc to câu mở đầu 3 lần để lấy lực giọng.</p>'
            )
        )

    def _s30_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">LỖI 3 &mdash; 3 câu đầu rời rạc, đứt quãng, có khoảng trống</h2>'
            '<p style="' + lead + '">Cách nói đứt mạch khiến khách <b>phải chờ</b> khi chưa '
            'hiểu chuyện gì, rất dễ mất kiên nhẫn:</p>'

            + _mistake(
                '<p style="margin-bottom:0;"><i>"Alo ạ&hellip;"</i> (dừng) &mdash; '
                '<i>"Anh có phải anh Nam không ạ&hellip;"</i> (dừng) &mdash; '
                '<i>"Em bên xây nhà&hellip;"</i> (dừng) &mdash; '
                '<i>"Anh có nhu cầu xây nhà đúng không ạ&hellip;"</i>. Càng rời rạc, khách '
                'càng thấy mất chuyên nghiệp.</p>'
            )

            + '<h2 style="' + h2 + '">Công thức 3 câu đầu liền mạch</h2>'
            '<table><thead><tr><th style="width:90px;">Câu</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b style="color:#b45309;">Câu 1</b></td><td>Chào + giới thiệu <b>đúng thương hiệu</b>.</td></tr>'
            '<tr><td><b style="color:#b45309;">Câu 2</b></td><td>Nói <b>lý do gọi</b>.</td></tr>'
            '<tr><td><b style="color:#b45309;">Câu 3</b></td><td>Mở <b>câu hỏi nhẹ nhàng</b> để khách trả lời.</td></tr>'
            '</tbody></table>'

            + _formula(
                '3 câu đầu = <b>Chào + Giới thiệu đúng nguồn</b> &#8226; <b>Lý do gọi</b> '
                '&#8226; <b>Câu hỏi mở nhẹ nhàng</b> &mdash; nói LIỀN, không để khoảng trống.'
            )

            + _situation(
                '<p><b>TikTok:</b> <i>"Em chào anh Nam ạ, em là Huy bên xây nhà trọn gói '
                'của Sếp Hinh. Bên em vừa nhận được thông tin anh quan tâm mẫu nhà trên '
                'TikTok. Em gọi nhanh để hỏi anh đang dự kiến xây nhà ở khu vực nào để bên '
                'em tư vấn đúng hơn ạ?"</i></p>'
                '<p style="margin-bottom:0;"><b>Facebook:</b> <i>"Em chào chị ạ, em là Huy '
                'bên xây nhà trọn gói Vinaduy. Bên em vừa nhận được thông tin chị quan tâm '
                'xây nhà trọn gói trên Facebook. Em gọi nhanh để nắm nhu cầu ban đầu, chị '
                'đang dự kiến xây trong năm nay hay sang năm ạ?"</i></p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Nối liền 3 câu thành 1 hơi nói, kết bằng <b>1 '
                'câu hỏi mở</b> (khu vực xây / xây năm nay hay sang năm) để khách trả lời '
                'ngay &mdash; giữ được nhịp cuộc gọi.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Viết sẵn <b>đoạn 3 câu liền mạch</b> theo giọng '
                'của bạn cho cả 2 nguồn, đọc to đến khi nói trôi 1 hơi không vấp. Áp dụng '
                'ngay ở cuộc gọi tiếp theo.</p>'
            )
        )

    def _s30_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">LỖI NGHIÊM TRỌNG NHẤT &mdash; Gọi như đi lấy thông tin, không tạo kết nối</h2>'
            '<p style="' + lead + '">Nhiều nhân viên gọi điện như đang <b>hỏi cung</b>: '
            '"Anh xây ở đâu?", "Diện tích bao nhiêu?", "Bao giờ xây?", "Ngân sách bao '
            'nhiêu?", "Có bản vẽ chưa?". Khách thấy bị <b>khai thác thông tin</b>, không '
            'được tư vấn.</p>'

            + _proof(
                '<p style="margin-bottom:0;">Khách xây nhà đang có <b>nhiều lo lắng</b>: sợ '
                'phát sinh, sợ nhà thầu làm ẩu, sợ vật tư không đúng, sợ bị ép giá, chưa '
                'biết bắt đầu từ đâu, phải bàn với gia đình&hellip; Chỉ hỏi thông tin mà '
                '<b>không đồng cảm</b> &rArr; khách không mở lòng.</p>'
            )

            + _formula(
                'Tư duy đúng: Nhân viên <b>KHÔNG</b> gọi để lấy thông tin &mdash; gọi để '
                '<b>giúp khách hiểu rõ hơn</b> về việc xây nhà. Nói như <b>một người bạn '
                'có chuyên môn</b>, không phải người đang điều tra.'
            )

            + '<h2 style="' + h2 + '">Chuyển từ HỎI CUNG sang TƯ VẤN (gắn lý do vào câu hỏi)</h2>'
            '<table><thead><tr><th style="width:42%;color:#dc2626;">Hỏi cung (sai)</th>'
            '<th style="color:#16a34a;">Hỏi kèm lý do (tư vấn)</th></tr></thead><tbody>'
            '<tr><td>"Anh xây bao nhiêu mét?"</td>'
            '<td>"Để em tư vấn sát hơn, em hỏi nhanh diện tích đất khoảng bao nhiêu mét ạ? '
            'Vì diện tích ảnh hưởng trực tiếp đến chi phí phần thô và hoàn thiện."</td></tr>'
            '<tr><td>"Bao giờ anh xây?"</td>'
            '<td>"Anh dự kiến xây trong năm nay hay sang năm ạ? Vì xây trong năm nay thì '
            'bên em tư vấn kỹ hơn về tiến độ thiết kế, xin phép, chuẩn bị vật tư cho kịp."</td></tr>'
            '<tr><td>"Ngân sách bao nhiêu?"</td>'
            '<td>"Phần tài chính mình đã dự kiến khoảng nào chưa anh? Em hỏi để tư vấn '
            'phương án phù hợp, tránh đưa mẫu quá cao hoặc quá thấp so với nhu cầu."</td></tr>'
            '<tr><td>"Anh có bản vẽ chưa?"</td>'
            '<td>"Hiện mình đã có bản vẽ hay mới đang tham khảo mẫu thôi anh? Nếu chưa có '
            'thì bên em tư vấn từ công năng trước, rồi mới ra phương án chi phí cho sát."</td></tr>'
            '</tbody></table>'

            + '<h2 style="' + h2 + '">LỖI 4 &mdash; Không nghe lại ghi âm để tự sửa</h2>'
            '<p>Cảm nhận của nhân viên khi nói và cảm nhận của khách khi nghe là <b>hai '
            'việc khác nhau</b>. Không nghe lại ghi âm thì không bao giờ biết mình sai ở '
            'đâu. <b>Mỗi ngày nghe lại ít nhất 5 cuộc gọi</b>, tự chấm:</p>'
            '<ul>'
            '<li>Giới thiệu <b>đúng nguồn khách</b> chưa? Câu đầu <b>đủ to</b> chưa?</li>'
            '<li>Có bị <b>ngập ngừng</b> không? 3 câu đầu có <b>liền mạch</b> không?</li>'
            '<li>Khách có hỏi lại <b>"bên nào", "không nghe rõ"</b> không?</li>'
            '<li>Mình đang <b>tư vấn</b> hay đang <b>tra khảo</b> khách?</li>'
            '</ul>'

            + _advice(
                '<p style="margin-bottom:0;">Một cuộc gọi <b>đạt</b> khi khách KHÔNG phải '
                'hỏi lại: "Em bên nào?", "Em nói gì cơ?", "Anh không nghe rõ.", "Em tư vấn '
                'cái gì?". Nếu khách hỏi những câu này &rArr; tự hiểu 30 giây đầu đang có '
                'vấn đề.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Ngay hôm nay, <b>nghe lại 5 cuộc gọi</b> của '
                'chính mình và gắn lý do vào mọi câu hỏi (theo bảng trên). Với mỗi câu định '
                'hỏi khách, tự thêm vế <b>"em hỏi để tư vấn&hellip; vì&hellip;"</b>.</p>'
            )
        )

    def _s30_p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">KỊCH BẢN CHUẨN 30 GIÂY ĐẦU (thuộc lòng)</h2>'

            + _chot(
                '<b>Facebook:</b> "Em chào anh Nam ạ, em là Huy bên xây nhà trọn gói '
                'Vinaduy. Bên em vừa nhận được thông tin anh quan tâm dịch vụ xây nhà trọn '
                'gói trên Facebook. Em gọi nhanh để nắm nhu cầu ban đầu của anh, mình đang '
                'dự kiến xây ở khu vực nào ạ?"'
            )
            + _chot(
                '<b>TikTok:</b> "Em chào anh Nam ạ, em là Huy bên xây nhà trọn gói của Sếp '
                'Hinh. Bên em vừa nhận được thông tin anh quan tâm mẫu nhà trên TikTok. Em '
                'gọi nhanh để hỏi anh đang dự kiến xây nhà ở khu vực nào để bên em tư vấn '
                'đúng hơn ạ?"'
            )
            + _chot(
                '<b>Không rõ nguồn:</b> "Em chào anh Nam ạ, em là Huy bên xây nhà trọn gói '
                'Vinaduy. Bên em vừa nhận được thông tin anh quan tâm xây nhà trọn gói. Em '
                'gọi nhanh để nắm nhu cầu ban đầu, mình dự kiến xây trong năm nay hay sang '
                'năm ạ?"'
            )

            + '<h2 style="' + h2 + '">Xử lý khi khách hỏi lại (không lúng túng)</h2>'
            '<table><thead><tr><th style="width:34%;">Khách hỏi</th><th>Trả lời</th></tr></thead><tbody>'
            '<tr><td><b>"Em bên nào?"</b></td>'
            '<td>"Dạ em là Huy bên xây nhà trọn gói của Sếp Hinh ạ. Anh vừa quan tâm mẫu '
            'nhà bên em trên TikTok nên em gọi lại để tư vấn cho mình rõ hơn ạ." (FB thì '
            'đổi sang Vinaduy / Facebook)</td></tr>'
            '<tr><td><b>"Anh không nghe rõ."</b></td>'
            '<td>Nói TO hơn, chậm lại, rõ từng chữ: "Dạ em xin phép nói lại rõ hơn ạ. Em là '
            'Huy bên xây nhà trọn gói của Sếp Hinh. Bên em gọi lại vì anh vừa quan tâm mẫu '
            'nhà trên TikTok ạ."</td></tr>'
            '<tr><td><b>"Em tư vấn cái gì vậy?"</b></td>'
            '<td>"Dạ em tư vấn về xây nhà trọn gói ạ. Bên em hỗ trợ từ mẫu nhà, công năng, '
            'dự toán chi phí, vật tư, tiến độ thi công đến hoàn thiện nhà cho gia đình '
            'mình ạ."</td></tr>'
            '</tbody></table>'

            + '<h2 style="' + h2 + '">&#127919; Thang điểm chấm 1 cuộc gọi (100 điểm)</h2>'
            '<table><thead><tr><th>Tiêu chí</th><th style="width:90px;text-align:center;">Điểm</th></tr></thead><tbody>'
            '<tr><td>Giới thiệu đúng nguồn khách</td><td style="text-align:center;">20</td></tr>'
            '<tr><td>Câu đầu to, rõ, chắc</td><td style="text-align:center;">20</td></tr>'
            '<tr><td>Ba câu đầu liền mạch</td><td style="text-align:center;">20</td></tr>'
            '<tr><td>Không để khách hỏi lại "bên nào", "không nghe rõ"</td><td style="text-align:center;">15</td></tr>'
            '<tr><td>Giọng nói có lực, tự tin</td><td style="text-align:center;">15</td></tr>'
            '<tr><td>Cách hỏi có tư vấn, không tra khảo</td><td style="text-align:center;">10</td></tr>'
            '</tbody></table>'
            '<p style="text-align:center;">&lt; 70: <b style="color:#dc2626;">Không đạt</b> '
            '&middot; 70&ndash;84: Đạt tạm &middot; &#8805; 85: <b style="color:#16a34a;">Đạt '
            'chuẩn</b> &middot; &#8805; 95: làm mẫu cho nhân viên khác học.</p>'

            + '<h2 style="' + h2 + '">&#127942; Kết luận phải nhớ</h2>'
            + _formula(
                'Một khách để lại số điện thoại = công ty đã mất tiền, mất công kéo về. '
                'Trong xây nhà trọn gói, khách cần <b>SỰ TIN TƯỞNG trước khi cần báo giá</b>. '
                'Muốn khách tin: nói <b>rõ - chắc - đúng - có lực</b> như một người có '
                'chuyên môn thật sự.'
            )

            + _apply(
                '<p>Bảng tự chấm trước/sau mỗi cuộc gọi (Có/Không):</p>'
                '<ol>'
                '<li>Đã <b>kiểm tra nguồn khách</b> và chọn đúng câu giới thiệu chưa?</li>'
                '<li>Câu đầu có <b>to - rõ - dứt khoát</b> không?</li>'
                '<li>3 câu đầu có <b>liền mạch</b>, kết bằng câu hỏi mở không?</li>'
                '<li>Mọi câu hỏi đã <b>gắn lý do tư vấn</b> chưa (không tra khảo)?</li>'
                '<li>Đã <b>nghe lại ghi âm</b> để tự chấm chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; đó là việc phải sửa '
                'ngay ở cuộc gọi tiếp theo.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    #  Đáp án nhiễu được viết sát nội dung để tăng độ khó khi chọn.
    # ==================================================================
    def _vd_s30_questions(self):
        T, F = True, False
        return [
            ('30 giây đầu khi gọi điện tư vấn xây nhà quyết định điều gì?',
             [('Khách có tiếp tục nghe hay cúp máy', T),
              ('Giá hợp đồng cao hay thấp', F),
              ('Khách ở khu vực nào', F),
              ('Khách thích mẫu nhà mấy tầng', F)]),

            ('Ba việc BẮT BUỘC làm đúng trong 30 giây đầu là gì?',
             [('Giới thiệu đúng nguồn khách + nói đủ to rõ dứt khoát + tạo cảm giác đáng tin', T),
              ('Báo giá ngay + xin địa chỉ + hẹn gặp', F),
              ('Nói thật nhẹ nhàng + xin lỗi đã làm phiền + hỏi thật nhiều thông tin', F),
              ('Gửi nhiều mẫu nhà + chốt ký luôn + xin chuyển khoản', F)]),

            ('Khách đến từ Facebook thường nhớ thương hiệu nào, nên giới thiệu thế nào?',
             [('Nhớ Vinaduy - giới thiệu "bên xây nhà trọn gói Vinaduy"', T),
              ('Nhớ Sếp Hinh - giới thiệu "bên Sếp Hinh"', F),
              ('Không nhớ gì - không cần giới thiệu thương hiệu', F),
              ('Nhớ cả hai - đọc cả hai thương hiệu liền nhau', F)]),

            ('Khách đến từ TikTok thường nhớ thương hiệu nào, nên giới thiệu thế nào?',
             [('Nhớ Sếp Hinh - giới thiệu "bên xây nhà trọn gói của Sếp Hinh"', T),
              ('Nhớ Vinaduy - chỉ cần nói "bên Vinaduy"', F),
              ('Nhớ tên nhân viên - chỉ cần xưng tên', F),
              ('Không cần phân biệt nguồn, nói gì cũng được', F)]),

            ('Khi KHÔNG xác định được nguồn khách thì giới thiệu mặc định theo thương hiệu nào?',
             [('Vinaduy', T),
              ('Sếp Hinh', F),
              ('Đọc cả Vinaduy lẫn Sếp Hinh', F),
              ('Không giới thiệu thương hiệu, hỏi khách trước', F)]),

            ('Vì sao giới thiệu sai nguồn khách lại nguy hiểm?',
             [('Khách không nhận ra, nghi ngờ 3-5 giây, mất nhịp, dễ cúp máy', T),
              ('Vì khách sẽ đòi giảm giá', F),
              ('Vì làm lộ thông tin công ty', F),
              ('Không nguy hiểm gì, khách nào cũng hiểu', F)]),

            ('Yêu cầu về âm lượng của câu đầu tiên là gì?',
             [('To hơn bình thường 20-30%, rõ từng chữ, dứt khoát', T),
              ('Nói càng nhỏ càng lịch sự', F),
              ('Nói thật chậm và kéo dài từng chữ', F),
              ('To hết cỡ như quát để gây chú ý', F)]),

            ('Trong ngành xây nhà, vì sao giọng yếu/nhỏ lại làm mất khách?',
             [('Khách bỏ ra vài trăm triệu đến vài tỷ, không tin người nói yếu, run, thiếu chắc chắn', T),
              ('Vì khách bị điếc nên cần nói to', F),
              ('Vì tổng đài thu âm kém', F),
              ('Giọng yếu không ảnh hưởng gì đến niềm tin', F)]),

            ('Nói "có lực" được hiểu đúng là gì?',
             [('Rõ ràng, tự tin, có lý do gọi hợp lý - KHÔNG phải quát hay nói cứng nhắc', T),
              ('Quát to để khách phải nghe', F),
              ('Nói nhanh và liên tục không cho khách chen vào', F),
              ('Nói cứng nhắc, ra lệnh cho khách', F)]),

            ('Tâm thế đúng khi gọi cho khách là gì?',
             [('"Tôi là người tư vấn xây dựng, gọi để giúp khách hiểu đúng việc xây nhà"', T),
              ('"Em xin lỗi vì đã làm phiền anh"', F),
              ('"Mong anh thương tình mua giúp em"', F),
              ('"Anh phải nghe hết em mới được cúp"', F)]),

            ('Công thức 3 câu đầu liền mạch gồm những gì, theo đúng thứ tự?',
             [('Câu 1 chào + giới thiệu đúng thương hiệu; Câu 2 lý do gọi; Câu 3 câu hỏi mở nhẹ nhàng', T),
              ('Câu 1 báo giá; Câu 2 xin địa chỉ; Câu 3 hẹn gặp', F),
              ('Câu 1 hỏi tên; Câu 2 hỏi tuổi; Câu 3 hỏi ngân sách', F),
              ('Câu 1 xin lỗi; Câu 2 giới thiệu; Câu 3 cảm ơn', F)]),

            ('Vì sao 3 câu đầu đứt quãng, có khoảng trống lại làm hỏng cuộc gọi?',
             [('Khách phải chờ khi chưa hiểu chuyện gì nên mất kiên nhẫn, thấy mất chuyên nghiệp', T),
              ('Vì tốn thời gian của nhân viên', F),
              ('Vì hệ thống tính cước cao hơn', F),
              ('Không sao cả, miễn nói đủ ý là được', F)]),

            ('Câu thứ 3 trong 3 câu đầu nên là gì để giữ nhịp cuộc gọi?',
             [('Một câu hỏi mở nhẹ nhàng (khu vực xây / xây năm nay hay sang năm) để khách trả lời', T),
              ('Một câu báo giá cụ thể', F),
              ('Một lời xin lỗi vì làm phiền', F),
              ('Yêu cầu khách gửi bản vẽ ngay', F)]),

            ('Lỗi NGHIÊM TRỌNG NHẤT trong tài liệu là lỗi nào?',
             [('Gọi điện như đang lấy thông tin/hỏi cung, không tạo kết nối với khách', T),
              ('Gọi sai giờ hành chính', F),
              ('Gọi nhầm số khách', F),
              ('Quên chào khách', F)]),

            ('Thay vì hỏi cung "Anh xây bao nhiêu mét?", cách hỏi tư vấn đúng là gì?',
             [('Gắn lý do: "Để em tư vấn sát hơn, em hỏi diện tích đất bao nhiêu mét ạ? Vì nó ảnh hưởng chi phí phần thô và hoàn thiện"', T),
              ('Hỏi dồn liên tiếp nhiều câu cho nhanh', F),
              ('Không hỏi gì, báo giá luôn', F),
              ('Hỏi "Anh không trả lời thì em báo giá kiểu gì?"', F)]),

            ('Tư duy ĐÚNG về mục đích cuộc gọi là gì?',
             [('Gọi để giúp khách hiểu rõ hơn về việc xây nhà, nói như người bạn có chuyên môn', T),
              ('Gọi để lấy đủ thông tin rồi cúp', F),
              ('Gọi để điều tra xem khách có tiền không', F),
              ('Gọi để ép khách chốt ngay trong cuộc đầu', F)]),

            ('Vì sao khách xây nhà thường khó mở lòng nếu chỉ bị hỏi thông tin?',
             [('Khách đang có nhiều lo lắng (sợ phát sinh, sợ làm ẩu, sợ ép giá...) cần được đồng cảm', T),
              ('Vì khách lười nói', F),
              ('Vì khách không có nhu cầu thật', F),
              ('Vì khách không nghe rõ', F)]),

            ('Quy định bắt buộc về nghe lại ghi âm là gì?',
             [('Mỗi nhân viên nghe lại ít nhất 5 cuộc gọi/ngày để tự chấm và sửa lỗi', T),
              ('Chỉ nghe lại khi trưởng nhóm yêu cầu', F),
              ('Không cần nghe lại, tự cảm nhận là đủ', F),
              ('Nghe lại 1 cuộc/tuần là đủ', F)]),

            ('Một cuộc gọi 30 giây đầu được coi là ĐẠT khi nào?',
             [('Khi khách KHÔNG phải hỏi lại "em bên nào", "không nghe rõ", "em tư vấn cái gì"', T),
              ('Khi nhân viên nói được thật nhiều', F),
              ('Khi khách hỏi lại nhiều lần (chứng tỏ quan tâm)', F),
              ('Khi cuộc gọi kéo dài trên 10 phút', F)]),

            ('Khi khách nói "Anh không nghe rõ", nhân viên phải làm gì?',
             [('Trả lời ngay, nói TO hơn, chậm lại, rõ từng chữ và nhắc lại giới thiệu', T),
              ('Cúp máy gọi lại sau', F),
              ('Nói nhỏ hơn cho lịch sự', F),
              ('Im lặng chờ khách hỏi tiếp', F)]),
        ]
