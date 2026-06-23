# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa học
"D1 - Cân đối tài chính bằng cách GIẢM DIỆN TÍCH".

Biến tài liệu gốc (3 cách giảm diện tích sàn + bảng công năng diện tích chuẩn +
các khoản phụ phí + kịch bản tư vấn) thành 1 khóa trình bày dễ hiểu - dễ nhớ -
dễ áp dụng cho nhân viên MỚI, theo FORM chuẩn khóa học VINADUY: tiêu đề lớn,
khung công thức, tình huống, lời khuyên, chứng minh, sai lầm, câu chốt thuộc
lòng và ô "ÁP DỤNG NGAY".

Tái dùng helper khung từ seed_kh_tiem_nang + _chot từ seed_khong_tuoi để đồng
bộ giao diện. Tất cả helper riêng dùng prefix _d1g_ để KHÔNG trùng tên với các
file seed khác (xem reference-seed-method-name-collision).

Idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_D1G_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.d1_giam_dien_tich_seed_version'


def _hero(title_small, title_big, sub):
    """Tiêu đề lớn - ấn tượng (đỏ cam thương hiệu) ở đầu khóa học."""
    return (
        '<div style="background:linear-gradient(135deg,#f5523c 0%%,#e8401f 100%%);'
        'border-radius:18px;padding:30px 26px;margin:4px 0 26px;text-align:center;'
        'box-shadow:0 10px 26px rgba(232,64,31,.30);">'
        '<div style="color:#ffe6df;font-size:15px;font-weight:800;letter-spacing:3px;'
        'text-transform:uppercase;margin-bottom:6px;">%s</div>'
        '<div style="color:#ffffff;font-size:40px;font-weight:900;line-height:1.1;'
        'letter-spacing:1px;text-shadow:0 2px 6px rgba(0,0,0,.18);">%s</div>'
        '<div style="color:#fff4f0;font-size:16px;font-weight:600;margin-top:12px;">'
        '%s</div></div>'
    ) % (title_small, title_big, sub)


class SlideChannelSeedD1GiamDienTich(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_d1_giam_dien_tich(self):
        ch = self.env.ref('vd_elearning.course_d1', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _D1G_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_d1g_pages())
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
        for text, answers in self._vd_d1g_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _D1G_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (6 phần)
    # ==================================================================
    def _vd_d1g_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#b91c1c;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('Mở đầu', self._d1g_p1(h2, h3, lead)),
            ('Cách 1 - Giảm diện tích sàn', self._d1g_p2(h2, h3, lead)),
            ('Cách 2 - Thu nhỏ hoặc bỏ Tum', self._d1g_p3(h2, h3, lead)),
            ('Cách 3 - Cắt sân sau làm sân phơi', self._d1g_p4(h2, h3, lead)),
            ('Bảng diện tích công năng chuẩn', self._d1g_p5(h2, h3, lead)),
            ('Kịch bản tư vấn - Câu chốt', self._d1g_p6(h2, h3, lead)),
        ]

    def _d1g_p1(self, h2, h3, lead):
        return (
            _hero('Cân đối tài chính &mdash; Nâng cao', 'GIẢM DIỆN TÍCH',
                  'Cách 2: Khi khách muốn chi phí thấp hơn ngân sách &mdash; '
                  'giảm diện tích sàn để giảm chi phí mà vẫn ĐỦ công năng')

            + '<p style="' + lead + '">Trong tư vấn <b>xây nhà trọn gói</b>, rất nhiều '
            'khách <b>thích diện tích lớn nhưng ngân sách lại có hạn</b>. Nếu cứ giữ '
            'nguyên diện tích khách muốn thì báo giá sẽ <b>vượt quá khả năng tài chính</b> '
            '&rArr; khách thấy đắt, do dự, dễ bỏ đi.</p>'

            '<p>Vậy nhiệm vụ của nhân viên là <b>cân đối tài chính cho khách</b>: kéo chi '
            'phí về đúng tầm tiền, nhưng nhà vẫn <b>đủ phòng để ở thoải mái</b>. Một trong '
            'những cách quan trọng nhất là <b>GIẢM DIỆN TÍCH SÀN</b> (vì chi phí xây nhà '
            'tính theo mét vuông sàn &mdash; giảm sàn là giảm tiền trực tiếp).</p>'

            + _formula(
                'Chi phí xây nhà = <span style="color:#dc2626;">Diện tích sàn</span> '
                '&#10005; Đơn giá. Muốn <b>giảm chi phí</b> mà <b>giữ đơn giá tốt</b> '
                '&rArr; phải <b>giảm diện tích sàn</b> một cách khéo léo.'
            )

            + '<h2 style="' + h2 + '">3 CÁCH GIẢM DIỆN TÍCH SÀN (phải thuộc)</h2>'
            '<table><thead><tr><th style="width:64px;">#</th>'
            '<th>Cách giảm</th><th>Bản chất</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:20px;">&#127968;</td>'
            '<td><b style="color:#b91c1c;">CÁCH 1</b><br/>Giảm diện tích sàn nhà</td>'
            '<td>Tăng diện tích <b>sân</b>, thu nhỏ phần <b>nhà</b> &rArr; ít mét sàn hơn.</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127970;</td>'
            '<td><b style="color:#b91c1c;">CÁCH 2</b><br/>Thu nhỏ hoặc bỏ Tum</td>'
            '<td>Thu Tum từ 25m&sup2; xuống 15m&sup2;/10m&sup2;, hoặc bỏ hẳn Tum.</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127787;</td>'
            '<td><b style="color:#b91c1c;">CÁCH 3</b><br/>Cắt bớt sân sau làm sân phơi</td>'
            '<td>Cắt một phần sàn ở phía sau thành sân phơi (không tính tiền như sàn).</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Giảm diện tích <b>không phải</b> là cắt phòng '
                'khách cần. Nguyên tắc là <b>giữ đủ công năng</b> (đủ phòng ngủ, bếp, thờ, '
                'WC) nhưng <b>bỏ bớt phần thừa</b> (sàn quá rộng, Tum quá to, sân sau dư). '
                'Khách vẫn ở thoải mái mà chi phí về đúng tầm tiền.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Học thuộc <b>3 cách giảm diện tích</b> theo '
                'thứ tự. Khi khách kêu "đắt quá" hoặc "vượt ngân sách", phải nghĩ ngay: '
                'mình giảm được ở đâu &mdash; sàn, Tum hay sân sau?</p>'
            )
        )

    def _d1g_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 1 &mdash; Giảm diện tích sàn nhà để giảm chi phí</h2>'
            '<p style="' + lead + '">Ý tưởng cốt lõi: <b>tăng diện tích sân, giảm diện tích '
            'nhà</b>. Phần đất khách không xây kín thành sàn mà để làm <b>sân trước, sân '
            'sau, vườn</b> &mdash; phần sân này <b>rẻ hơn rất nhiều</b> so với sàn nhà.</p>'

            '<table><thead><tr><th style="text-align:center;width:50%;color:#16a34a;">'
            'TĂNG diện tích SÂN</th>'
            '<th style="text-align:center;color:#dc2626;">GIẢM diện tích NHÀ</th></tr></thead><tbody>'
            '<tr><td>Sân trước, sân sau, vườn, lối đi</td><td>Phần sàn xây kín (khách, bếp, ngủ...)</td></tr>'
            '<tr><td>Chi phí <b>thấp</b> (lát nền, sân vườn)</td><td>Chi phí <b>cao</b> (kết cấu, mái, hoàn thiện)</td></tr>'
            '<tr><td>Tạo không gian thoáng, đẹp, sang</td><td>Mỗi mét sàn bớt đi = bớt tiền trực tiếp</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Một mét vuông <b>sàn nhà</b> phải gánh đủ: '
                'móng, cột, dầm, sàn, tường, mái, điện nước, hoàn thiện&hellip; nên rất '
                'đắt. Trong khi một mét vuông <b>sân</b> chủ yếu là nền và lát gạch &mdash; '
                'rẻ hơn nhiều lần. Vì vậy <b>chuyển bớt sàn thành sân</b> là cách giảm chi '
                'phí mạnh mà nhà vẫn đẹp, vẫn thoáng.</p>'
            )

            + _situation(
                '<p style="margin-bottom:0;">Khách có đất rộng nhưng muốn tiết kiệm: thay '
                'vì xây kín hết thành sàn, mình <b>để lại sân trước trồng cây, mở sân sau</b>, '
                'phần nhà thu gọn lại. Khách vừa <b>giảm được chi phí</b>, vừa có <b>sân '
                'vườn thoáng đẹp</b> &mdash; nghe còn sướng hơn là xây kín mít.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Khi khách than chi phí cao, đề xuất ngay: '
                '"Mình <b>để lại phần sân trước/sân sau</b> cho thoáng, phần nhà em thu gọn '
                'lại đủ công năng &mdash; vừa <b>giảm chi phí</b> vừa đẹp anh ạ."</p>'
            )
        )

    def _d1g_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 2 &mdash; Thu nhỏ hoặc bỏ Tum để giảm chi phí</h2>'
            '<p style="' + lead + '"><b>Tum</b> là phần xây thêm trên tầng mái cùng (che '
            'cầu thang, làm phòng thờ/giặt phơi/kho). Tum cũng <b>tính tiền như một phần '
            'sàn</b> &mdash; nên thu nhỏ hoặc bỏ Tum sẽ giảm chi phí ngay.</p>'

            '<table><thead><tr><th>Phương án</th><th>Cách làm</th><th>Tác dụng</th></tr></thead><tbody>'
            '<tr><td><b style="color:#b45309;">THU NHỎ TUM</b></td>'
            '<td>Từ <b>25m&sup2; xuống còn 15m&sup2;</b> hoặc <b>10m&sup2;</b></td>'
            '<td>Giảm 10&ndash;15m&sup2; sàn Tum &rArr; giảm chi phí mà vẫn còn Tum dùng.</td></tr>'
            '<tr><td><b style="color:#dc2626;">BỎ HẲN TUM</b></td>'
            '<td>Loại bỏ Tum, làm mái bằng phẳng</td>'
            '<td>Giảm mạnh nhất &rArr; dùng khi khách cần tiết kiệm tối đa.</td></tr>'
            '</tbody></table>'

            + _box('#dc2626', '#fef2f2', '&#9888;&#65039;', 'Lưu ý phụ phí BẮT BUỘC nhớ',
                   '<ul style="margin:0;">'
                   '<li><b>Tum dưới 20m&sup2;</b> vẫn <b>phải tính</b> và <b>cộng thêm '
                   '25&ndash;27 triệu</b> (phần Tum nhỏ vẫn tốn kết cấu, mái, cầu thang).</li>'
                   '<li>Nhà <b>2 mặt tiền</b>: cộng thêm <b>300.000đ/1m</b> (mặt tiền).</li>'
                   '<li>Nhà <b>3 mặt tiền</b>: cộng thêm <b>600.000đ/1m</b> (mặt tiền).</li>'
                   '</ul>')

            + _mistake(
                '<p style="margin-bottom:0;">Tưởng Tum nhỏ thì <b>miễn phí</b> hoặc không '
                'đáng kể. Sai! Tum <b>dưới 20m&sup2;</b> vẫn phải <b>cộng thêm 25&ndash;27 '
                'triệu</b>. Quên khoản này khi báo giá &rArr; báo thiếu, sau lại phải xin '
                'thêm tiền khách &rArr; mất uy tín.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Trước khi báo giá nhà có Tum, tự hỏi: (1) Tum '
                'bao nhiêu m&sup2;? (2) Có <b>dưới 20m&sup2; không &rArr; cộng 25&ndash;27tr</b>? '
                '(3) Nhà <b>mấy mặt tiền &rArr; cộng 300k/600k mỗi mét</b>? Cộng đủ rồi mới chốt giá.</p>'
            )
        )

    def _d1g_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 3 &mdash; Cắt bớt diện tích sân sau để làm sân phơi</h2>'
            '<p style="' + lead + '">Thay vì xây kín hết sàn tầng trên, mình <b>cắt một '
            'phần phía sau</b> (thường ở tầng trên cùng) để làm <b>sân phơi</b>. Phần này '
            'không tính tiền nặng như sàn xây kín &rArr; vừa giảm chi phí, vừa có chỗ '
            'phơi đồ thực dụng cho gia đình.</p>'

            + _proof(
                '<p style="margin-bottom:0;">Sân phơi chỉ cần <b>nền và lan can</b>, không '
                'cần tường bao, không cần hoàn thiện như phòng ở &rArr; chi phí thấp hơn '
                'sàn kín nhiều. Đổi một phần sàn dư thành sân phơi là <b>giảm chi phí mà '
                'tăng tiện ích</b> &mdash; nhà nào cũng cần chỗ phơi đồ.</p>'
            )

            + _situation(
                '<p style="margin-bottom:0;">Nhà khách có tầng trên rộng dư so với nhu cầu '
                'phòng. Mình tư vấn: "Phần phía sau tầng trên mình <b>để làm sân phơi</b> '
                'cho tiện giặt phơi, vừa <b>đỡ một khoản chi phí</b>, vừa thoáng nhà anh ạ." '
                '&rArr; Khách thấy hợp lý vì vừa tiết kiệm vừa có ích.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Cả 3 cách đều cùng một nguyên lý: <b>bỏ bớt '
                'phần sàn THỪA, giữ phần công năng CẦN</b>. Sân, Tum nhỏ, sân phơi đều rẻ '
                'hơn sàn ở kín &mdash; chuyển phần dư sang đó là cân đối được tài chính.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Ghi nhớ <b>3 cách giảm diện tích</b> như một '
                'bộ công cụ: gặp khách "vượt ngân sách" là lôi ra dùng &mdash; tăng sân/giảm '
                'nhà, thu/bỏ Tum, cắt sân sau làm sân phơi.</p>'
            )
        )

    def _d1g_p5(self, h2, h3, lead):
        # Bang cong nang chuan: dien tich thap nhat theo tung loai nha de tu van.
        def row(loai, cn, dt, goi):
            return ('<tr><td><b>%s</b></td><td>%s</td>'
                    '<td style="text-align:center;color:#b91c1c;font-weight:800;">%s</td>'
                    '<td>%s</td></tr>') % (loai, cn, dt, goi)
        bang = (
            '<table><thead><tr>'
            '<th style="width:120px;">Loại nhà</th><th>Công năng</th>'
            '<th style="width:96px;text-align:center;">DT thấp nhất</th>'
            '<th>Khoảng tư vấn</th></tr></thead><tbody>'
            + row('1 tầng mái bằng', '1 khách, 1 bếp, 1 thờ, 3 ngủ, 1 WC',
                  '80&ndash;120m&sup2;', '80-90, 90-100, 100-110')
            + row('1 tầng mái bằng', '1 khách, 1 bếp, 1 thờ, 4 ngủ, 2 WC',
                  '120&ndash;150m&sup2;', '120-130, 130-140, 140-150')
            + row('1 tầng mái ngói', '1 khách, 1 bếp, 1 thờ, 3 ngủ, 1 WC',
                  '100&ndash;140m&sup2;', '100-110, 110-120, 120-140')
            + row('1 tầng mái ngói', '1 khách, 1 bếp, 1 thờ, 4 ngủ, 2 WC',
                  '120&ndash;150m&sup2;', '120-130, 130-140, 140-150')
            + row('2 tầng mái bằng', 'T1: khách, bếp, 1 ngủ, 1 WC &middot; T2: 2 ngủ, 1 thờ, 1 WC',
                  '50&ndash;75m&sup2;', '50-60, 60-70, 70-75')
            + row('2 tầng mái bằng', 'T1: khách, bếp, 2 ngủ, 2 WC &middot; T2: 3 ngủ, 1 thờ, 2 WC',
                  '80&ndash;120m&sup2;', '80-100, 100-110, 110-120')
            + row('2 tầng mái ngói', 'T1: khách, bếp, 1 ngủ, 1 WC &middot; T2: 3 ngủ, 1 thờ, 1 WC',
                  '80&ndash;100m&sup2;', '80-90, 90-100')
            + row('2 tầng mái ngói', 'T1: khách, bếp, 2 ngủ, 2 WC &middot; T2: 3 ngủ, 1 thờ, 2 WC',
                  '90&ndash;120m&sup2;', '90-100, 100-110, 110-120')
            + '</tbody></table>'
        )
        return (
            '<h2 style="' + h2 + '">BẢNG DIỆN TÍCH CÔNG NĂNG CHUẨN (xương sống tư vấn)</h2>'
            '<p style="' + lead + '">Đây là <b>bảng công năng cơ bản</b> để tư vấn diện '
            'tích. Mỗi loại nhà có một <b>diện tích thấp nhất</b> để vẫn đủ ở &mdash; từ '
            'đó tùy <b>tầm tài chính của khách</b> mà chọn khoảng phù hợp, sao cho <b>báo '
            'giá không quá cao</b> mà khách vẫn thấy <b>vừa tâm tài chính</b>.</p>'

            + bang

            + _formula(
                'Quy tắc cộng/trừ phòng ngủ: <b>thêm 1 ngủ &rArr; +20m&sup2;</b>, '
                '<b>bớt 1 ngủ &rArr; &minus;20m&sup2;</b>. (Trung bình mỗi phòng ngủ '
                'gánh khoảng 20m&sup2; sàn.)'
            )

            + _situation(
                '<p style="margin-bottom:0;">Khách muốn nhà <b>1 tầng mái bằng, 3 ngủ</b> '
                'nhưng tài chính có hạn: mình tư vấn khoảng <b>80&ndash;90m&sup2;</b> (mức '
                'thấp nhất của loại này) để báo giá vừa tầm. Nếu khách muốn <b>bớt 1 ngủ</b> '
                '&rArr; trừ khoảng <b>20m&sup2;</b>, chi phí giảm thêm.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Không có con số cứng &mdash; luôn <b>nghe tầm '
                'tài chính của khách trước</b>, rồi chọn khoảng trong bảng cho khớp. Mục '
                'tiêu kép: <b>báo giá không quá cao</b> + khách thấy <b>vừa tâm tài chính</b>.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Học thuộc <b>diện tích thấp nhất</b> của từng '
                'loại nhà trong bảng và quy tắc <b>&plusmn;20m&sup2; mỗi phòng ngủ</b>. '
                'Khi khách hỏi, phải nói được ngay khoảng diện tích phù hợp với tầm tiền của họ.</p>'
            )
        )

    def _d1g_p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">KỊCH BẢN TƯ VẤN GIẢM DIỆN TÍCH (thuộc lòng)</h2>'
            '<p style="' + lead + '">Khi khách muốn <b>giữ nguyên diện tích lớn</b> nhưng '
            'ngân sách không đủ, đây là cách dẫn dắt để khách đồng ý điều chỉnh:</p>'

            + _chot(
                '<b>Bước 1 &mdash; Đặt vấn đề:</b> "Theo em, để làm được căn nhà với diện '
                'tích giữ nguyên như anh mong muốn, thì để lên được phương án chính xác '
                'nhất, anh vẫn sẽ phải <b>điều chỉnh một số hạng mục</b>, đồng thời mình có '
                'thể <b>tăng ngân sách lên thêm một chút</b> kèm phương án bên em hỗ trợ '
                'cân đối cho anh."'
            )
            + _chot(
                '<b>Bước 2 &mdash; Cảnh báo nếu ép giá thấp:</b> "Với tầm mức kinh phí như '
                'vậy, để thi công thì vật tư vật liệu sẽ phải <b>điều chỉnh giảm xuống rất '
                'thấp</b> &mdash; mà thấp như vậy tức là <b>vật tư loại kém</b>, kết cấu '
                'công trình <b>không đảm bảo an toàn</b>, bên em cũng ngần ngại trong việc '
                'giảm vật tư anh ạ."'
            )
            + _chot(
                '<b>Bước 3 &mdash; Hướng sang giảm diện tích:</b> "Em chia sẻ thật với anh '
                'là <b>công năng mình cần dùng không quá nhiều</b>, không nhất thiết phải '
                'làm đúng diện tích đó. Phần này bên em sẽ tính toán cho anh từ <b>diện '
                'tích thi công, đến chi phí, đến công năng sử dụng</b> &mdash; vẫn đáp ứng '
                'đủ nhu cầu nhà mình, đó mới là phương án anh ạ."'
            )
            + _chot(
                '<b>Bước 4 &mdash; Chốt mở:</b> "Để em <b>tính toán lại theo phương án '
                'này</b> rồi em gửi anh xem lại, và anh em mình cân đối thêm."'
            )

            + '<h2 style="' + h2 + '">Vì sao kịch bản này hiệu quả</h2>'
            '<table><thead><tr><th style="width:34%;">Bước</th><th>Khách cảm nhận được gì</th></tr></thead><tbody>'
            '<tr><td><b>1. Đặt vấn đề</b></td><td>Thấy mình được tôn trọng mong muốn, không bị ép.</td></tr>'
            '<tr><td><b>2. Cảnh báo vật tư kém</b></td><td>Hiểu vì sao KHÔNG nên ép giá thấp &mdash; sợ nhà yếu, không an toàn.</td></tr>'
            '<tr><td><b>3. Giảm diện tích</b></td><td>Thấy có lối ra: giảm phần thừa, giữ đủ công năng, chi phí về tầm.</td></tr>'
            '<tr><td><b>4. Chốt mở</b></td><td>Có lý do để tiếp tục làm việc, mình được tính lại phương án.</td></tr>'
            '</tbody></table>'

            + _mistake(
                '<p style="margin-bottom:0;">Sai lầm là <b>đồng ý giảm giá bằng cách giảm '
                'vật tư</b> để giữ diện tích lớn. Làm vậy nhà yếu, không an toàn, sau này '
                'phát sinh &mdash; mất uy tín công ty. Đúng cách là <b>giữ vật tư chuẩn, '
                'giảm diện tích thừa</b>.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Kết luận phải nhớ</h2>'
            + _formula(
                'Khách vượt ngân sách &rArr; <b>KHÔNG giảm vật tư</b> (nhà sẽ yếu), mà '
                '<b>GIẢM DIỆN TÍCH THỪA</b>: tăng sân/giảm nhà &#8226; thu hoặc bỏ Tum '
                '&#8226; cắt sân sau làm sân phơi &mdash; giữ đủ công năng, chi phí về '
                'đúng tầm tiền.'
            )

            + _apply(
                '<p>Bảng tự kiểm trước mỗi lần báo giá cho khách "thấy đắt" (Có/Không):</p>'
                '<ol>'
                '<li>Đã hỏi rõ <b>tầm tài chính</b> của khách chưa?</li>'
                '<li>Đã chọn <b>khoảng diện tích</b> trong bảng cho khớp tầm tiền chưa?</li>'
                '<li>Đã rà <b>3 cách giảm diện tích</b> (sàn / Tum / sân sau) chưa?</li>'
                '<li>Đã cộng đủ <b>phụ phí</b> (Tum dưới 20m&sup2; +25-27tr, 2/3 mặt tiền) chưa?</li>'
                '<li>Có đang <b>tránh giảm vật tư</b> để giữ nhà an toàn không?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; đó là việc phải làm '
                'lại trước khi chốt giá với khách.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    # ==================================================================
    def _vd_d1g_questions(self):
        T, F = True, False
        return [
            ('Mục tiêu của việc "giảm diện tích" khi cân đối tài chính cho khách là gì?',
             [('Giảm chi phí về đúng tầm tiền nhưng nhà vẫn đủ công năng để ở', T),
              ('Cắt bớt phòng ngủ khách cần để hợp đồng rẻ nhất', F),
              ('Giảm vật tư xuống loại kém cho rẻ', F),
              ('Tăng diện tích để báo giá cao hơn', F)]),

            ('Chi phí xây nhà được tính chủ yếu theo yếu tố nào?',
             [('Diện tích sàn nhân với đơn giá', T),
              ('Số lượng cửa sổ', F),
              ('Màu sơn khách chọn', F),
              ('Số người trong gia đình', F)]),

            ('Ba cách giảm diện tích sàn theo tài liệu là gì?',
             [('Giảm diện tích sàn nhà (tăng sân/giảm nhà), thu nhỏ hoặc bỏ Tum, cắt sân sau làm sân phơi', T),
              ('Giảm vật tư, đổi nhà thầu, giảm số tầng tùy ý', F),
              ('Bỏ phòng khách, bỏ bếp, bỏ nhà thờ', F),
              ('Tăng sàn, tăng Tum, mở rộng nhà', F)]),

            ('Cách 1 - "Giảm diện tích sàn nhà" được thực hiện bằng cách nào?',
             [('Tăng diện tích sân (trước/sau/vườn), thu gọn phần nhà xây kín', T),
              ('Xây kín toàn bộ đất thành sàn', F),
              ('Bỏ hết sân để làm nhà to nhất', F),
              ('Tăng số tầng lên cao', F)]),

            ('Vì sao chuyển bớt sàn nhà thành sân lại giảm được chi phí?',
             [('1m2 sàn phải gánh móng, cột, dầm, mái, hoàn thiện nên rất đắt; 1m2 sân chủ yếu là nền/lát nên rẻ hơn nhiều', T),
              ('Vì sân không cần xin phép xây dựng', F),
              ('Vì sân được miễn thuế', F),
              ('Vì sân không tính vào diện tích đất', F)]),

            ('Cách 2 - thu nhỏ Tum thường thu từ 25m2 xuống còn bao nhiêu?',
             [('Còn 15m2 hoặc 10m2', T),
              ('Còn 30m2', F),
              ('Còn 0m2 bắt buộc', F),
              ('Giữ nguyên 25m2', F)]),

            ('Tum có dưới 20m2 thì tính chi phí thế nào?',
             [('Vẫn phải tính và cộng thêm 25-27 triệu', T),
              ('Được miễn phí hoàn toàn', F),
              ('Chỉ tính một nửa giá', F),
              ('Không cần tính vì quá nhỏ', F)]),

            ('Nhà 2 mặt tiền và 3 mặt tiền cộng thêm phụ phí bao nhiêu mỗi mét?',
             [('2 mặt tiền +300.000đ/1m; 3 mặt tiền +600.000đ/1m', T),
              ('2 mặt tiền +600k/1m; 3 mặt tiền +300k/1m', F),
              ('Cả hai đều +100k/1m', F),
              ('Không cộng thêm gì', F)]),

            ('Cách 3 - cắt bớt sân sau dùng để làm gì?',
             [('Làm sân phơi', T),
              ('Làm thêm một phòng ngủ kín', F),
              ('Làm tầng hầm', F),
              ('Làm gara ô tô', F)]),

            ('Vì sao sân phơi rẻ hơn sàn ở kín?',
             [('Chỉ cần nền và lan can, không cần tường bao và hoàn thiện như phòng ở', T),
              ('Vì sân phơi không cần móng', F),
              ('Vì sân phơi do khách tự làm', F),
              ('Vì sân phơi không tính diện tích', F)]),

            ('Nguyên lý chung của cả 3 cách giảm diện tích là gì?',
             [('Bỏ bớt phần sàn THỪA, giữ phần công năng CẦN (đủ phòng để ở)', T),
              ('Cắt giảm mọi thứ kể cả phòng khách cần', F),
              ('Giữ nguyên diện tích, chỉ giảm vật tư', F),
              ('Tăng tối đa diện tích để nhà to', F)]),

            ('Nhà "1 tầng mái bằng - 3 ngủ 1 WC" có diện tích thấp nhất khoảng bao nhiêu?',
             [('80-120m2 (tư vấn 80-90, 90-100, 100-110)', T),
              ('50-75m2', F),
              ('120-150m2', F),
              ('200m2 trở lên', F)]),

            ('Nhà "1 tầng mái bằng - 4 ngủ 2 WC" có diện tích thấp nhất khoảng bao nhiêu?',
             [('120-150m2', T),
              ('60-80m2', F),
              ('80-100m2', F),
              ('40-60m2', F)]),

            ('Nhà "2 tầng mái bằng" với T1 khách-bếp-1 ngủ-1 WC, T2 2 ngủ-1 thờ-1 WC có diện tích thấp nhất khoảng?',
             [('50-75m2 (50-60, 60-70, 70-75)', T),
              ('120-150m2', F),
              ('100-140m2', F),
              ('30-45m2', F)]),

            ('Quy tắc cộng/trừ diện tích khi khách thêm hoặc bớt 1 phòng ngủ là gì?',
             [('Trung bình mỗi phòng ngủ cộng/trừ khoảng 20m2', T),
              ('Mỗi phòng ngủ cộng/trừ 50m2', F),
              ('Mỗi phòng ngủ cộng/trừ 5m2', F),
              ('Không thay đổi diện tích', F)]),

            ('Khi chọn khoảng diện tích để tư vấn, căn cứ quan trọng nhất là gì?',
             [('Tầm tài chính của khách - để báo giá không quá cao mà khách vẫn thấy vừa tâm tài chính', T),
              ('Diện tích lớn nhất có thể xây', F),
              ('Sở thích của nhân viên', F),
              ('Luôn lấy mức cao nhất trong bảng', F)]),

            ('Khi khách muốn giữ diện tích lớn nhưng ngân sách thấp, cách XỬ LÝ ĐÚNG là gì?',
             [('Giữ vật tư chuẩn và giảm diện tích thừa, không giảm vật tư', T),
              ('Giảm vật tư xuống loại kém để giữ diện tích lớn', F),
              ('Từ chối khách luôn', F),
              ('Báo giá thật cao cho khách tự rút lui', F)]),

            ('Vì sao KHÔNG nên giảm vật tư để hạ giá cho khách?',
             [('Vật tư loại kém làm kết cấu không đảm bảo an toàn, nhà yếu, dễ phát sinh, mất uy tín', T),
              ('Vì vật tư kém khó mua', F),
              ('Vì khách không thích màu vật tư kém', F),
              ('Thực ra giảm vật tư là cách tốt nhất', F)]),

            ('Trong kịch bản tư vấn, sau khi cảnh báo vật tư kém, nhân viên hướng khách sang đâu?',
             [('Hướng sang giảm diện tích thừa - vì công năng cần dùng không quá nhiều, vẫn đủ đáp ứng nhu cầu', T),
              ('Hướng sang đổi nhà thầu khác', F),
              ('Hướng sang vay thêm ngân hàng', F),
              ('Hướng sang bỏ luôn dự án', F)]),

            ('Câu chốt mở cuối kịch bản tư vấn nên nói gì?',
             [('"Để em tính toán lại theo phương án này rồi gửi anh xem lại và anh em mình cân đối thêm"', T),
              ('"Anh không chốt ngay thì em không làm nữa"', F),
              ('"Giá đó là cuối cùng, anh quyết luôn đi"', F),
              ('"Anh tự tính lại rồi báo em sau"', F)]),
        ]
