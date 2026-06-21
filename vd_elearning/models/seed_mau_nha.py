# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau thi cho khoa "Mau nha" (course_a1).

Doi tuong: nhan vien sale TRAI NGANH, chua biet gi ve xay dung. Khoa giup NV moi
HIEU va PHAN BIET cac mau nha (vuong hien dai, mai Nhat, mai Thai, mau khac) va
cac hang muc dac biet (tum, san thuong, tang lung, thong tang). Bam theo file
PowerPoint "Mau Nha.pptx" cua cong ty; anh dat trong static/src/img/maunha.

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _advice, _proof, _mistake

_MN_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.maunha_seed_version'
_IMG = '/vd_elearning/static/src/img/maunha/'


def _core(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">&#11088; ĐIỀU CẦN NHỚ</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _note(inner):
    return _box('#0ea5e9', '#ecfeff', '&#128161;', 'Hiểu cho dễ', inner)


def _fig(name, cap=''):
    c = ''
    if cap:
        c = ('<figcaption style="font-size:12.5px;color:#64748b;text-align:center;'
             'margin-top:5px;font-weight:600;">%s</figcaption>') % cap
    return (
        '<figure style="margin:0;flex:1 1 230px;min-width:190px;max-width:330px;">'
        '<img src="%s%s" style="width:100%%;height:190px;object-fit:cover;border-radius:12px;'
        'box-shadow:0 4px 14px rgba(32,36,58,.18);"/>%s</figure>'
    ) % (_IMG, name, c)


def _gallery(*figs):
    return ('<div style="display:flex;flex-wrap:wrap;gap:12px;margin:14px 0;">%s</div>'
            % ''.join(figs))


class SlideChannelSeedMauNha(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_mau_nha(self):
        ch = self.env.ref('vd_elearning.course_a1', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _MN_VERSION:
            return True

        # Khoa kien thuc: dat 80%, thi lai khong gioi han (NV trai nganh).
        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_mn_pages())
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
        for text, answers in self._vd_mn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _MN_VERSION)
        return True

    # ==================================================================
    def _vd_mn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Mau nha la gi', self._p1(h2, h3, lead)),
            ('2. Nha vuong hien dai', self._p2(h2, h3, lead)),
            ('3. Nha mai Nhat', self._p3(h2, h3, lead)),
            ('4. Nha mai Thai', self._p4(h2, h3, lead)),
            ('5. So sanh mai Nhat - mai Thai', self._p5(h2, h3, lead)),
            ('6. Cac mau nha khac', self._p6(h2, h3, lead)),
            ('7. Tum - San thuong - Tang lung - Thong tang', self._p7(h2, h3, lead)),
            ('8. Ket luan - Nhan biet nhanh', self._p8(h2, h3, lead)),
        ]

    def _p1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#1e3a8a,#3730a3);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.85;font-weight:700;">'
            'KIẾN THỨC CƠ BẢN VỀ XÂY DỰNG</div>'
            '<div style="font-size:25px;font-weight:900;margin-top:4px;">PHÂN BIỆT CÁC MẪU NHÀ</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Dành cho nhân viên mới '
            '(kể cả trái ngành) &mdash; chỉ cần đọc xong là phân biệt được các kiểu nhà '
            'khách hay nhắc tới.</div></div>'

            '<h2 style="' + h2 + '">&#127968; "Mẫu nhà" là gì?</h2>'
            '<p style="' + lead + '"><b>Mẫu nhà</b> là <b>kiểu dáng và phong cách kiến trúc '
            'tổng thể</b> của căn nhà &mdash; nhìn bên ngoài thấy nhà <b>hình khối ra sao</b>, '
            '<b>kiểu mái thế nào</b>, <b>phong cách hiện đại hay cổ điển</b>. Mỗi mẫu nhà hợp '
            'với một loại đất, một mức chi phí và một sở thích khác nhau.</p>'

            + _note(
                '<p style="margin-bottom:0;">Khi khách nói <i>"anh thích nhà <b>mái Thái</b>"</i>, '
                '<i>"cho anh xem <b>nhà vuông hiện đại</b>"</i> hay <i>"nhà <b>mái Nhật</b> đẹp '
                'không em?"</i> &mdash; đó chính là khách đang nói về <b>MẪU NHÀ</b>. Bạn phải '
                '<b>nhận ra ngay</b> khách muốn kiểu gì để tư vấn cho đúng.</p>'
            )

            + '<h2 style="' + h2 + '">Khóa này gồm những gì?</h2>'
            '<table><thead><tr><th style="width:230px;">Nhóm</th><th>Gồm</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">3 mẫu nhà CHỦ ĐẠO</b><br/>(hay gặp nhất)</td>'
            '<td>Nhà vuông hiện đại &middot; Nhà mái Nhật &middot; Nhà mái Thái</td></tr>'
            '<tr><td><b style="color:#9333ea;">Mẫu nhà khác</b><br/>(tham khảo, cao cấp)</td>'
            '<td>Indochine &middot; Tân cổ điển &middot; Mái Pháp</td></tr>'
            '<tr><td><b style="color:#b45309;">Hạng mục đặc biệt</b></td>'
            '<td>Tum &middot; Sân thượng &middot; Tầng lửng &middot; Thông tầng</td></tr>'
            '</tbody></table>'

            + _core(
                'Mẫu nhà = <b>kiểu dáng + kiểu mái + phong cách</b> của ngôi nhà. '
                'Nhớ trước <b>3 mẫu chủ đạo</b>: Vuông hiện đại &middot; Mái Nhật &middot; Mái Thái.'
            )
        )

    def _p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MẪU 1 &mdash; NHÀ VUÔNG HIỆN ĐẠI</h2>'
            '<p style="' + lead + '">Là kiểu nhà <b>hình khối vuông vức</b>, <b>mái bằng '
            '(mái phẳng)</b>, đường nét đơn giản, hiện đại. Đây là mẫu <b>thông dụng nhất</b> '
            'hiện nay.</p>'
            + _gallery(_fig('image15.jpg'), _fig('image32.jpg'), _fig('image22.jpg'),
                       _fig('image31.jpg'), _fig('image34.jpg'))
            + '<table><thead><tr><th style="width:200px;">Đặc điểm</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Kiểu mái</b></td><td>Mái bằng (phẳng), khối vuông hiện đại.</td></tr>'
            '<tr><td><b>Phù hợp</b></td><td><b>Nhà phố</b> (mặt tiền hẹp, đất hình ống).</td></tr>'
            '<tr><td><b>Chi phí</b></td><td><b style="color:#16a34a;">RẺ NHẤT</b> trong các mẫu.</td></tr>'
            '<tr><td><b>Mức độ phổ biến</b></td><td><b style="color:#16a34a;">Được sử dụng NHIỀU NHẤT</b> trên thị trường.</td></tr>'
            '</tbody></table>'
            + _core(
                'Nhà vuông hiện đại = <b>mái bằng &middot; hợp nhà phố &middot; RẺ NHẤT &middot; '
                'PHỔ BIẾN NHẤT</b>.'
            )
        )

    def _p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MẪU 2 &mdash; NHÀ MÁI NHẬT</h2>'
            '<p style="' + lead + '">Là kiểu nhà có <b>mái ngói</b> theo phong cách Nhật: '
            '<b>hệ mái lùn, thấp</b>, trải rộng và êm mắt.</p>'
            + _gallery(_fig('image24.jpg'), _fig('image23.jpg'),
                       _fig('image33.png'), _fig('image20.png'))
            + '<table><thead><tr><th style="width:200px;">Đặc điểm</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Kiểu mái</b></td><td>Hệ mái <b>lùn, thấp</b>; <b>KHÔNG có góc chữ A</b>; '
            '<b>dễ khoe được phần ngói</b>.</td></tr>'
            '<tr><td><b>Phù hợp</b></td><td><b>Đất rộng &mdash; nhà vườn</b>.</td></tr>'
            '<tr><td><b>Chi phí</b></td><td><b>Cao hơn</b> nhà vuông hiện đại (nhưng <b>rẻ hơn mái Thái</b>).</td></tr>'
            '</tbody></table>'
            + _note(
                '<p style="margin-bottom:0;"><b>"Góc chữ A"</b> là phần mái dốc nhọn nhô cao '
                'lên giống hình chữ A khi nhìn từ phía trước. <b>Mái Nhật KHÔNG có góc chữ A</b> '
                'nên trông thấp và trải rộng.</p>'
            )
            + _core('Mái Nhật = <b>mái lùn thấp &middot; không có góc chữ A &middot; khoe ngói &middot; hợp đất rộng / nhà vườn</b>.')
        )

    def _p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MẪU 3 &mdash; NHÀ MÁI THÁI</h2>'
            '<p style="' + lead + '">Là kiểu nhà mái ngói phong cách Thái: <b>hệ mái cao</b>, '
            'dốc nhọn, sang trọng.</p>'
            + _gallery(_fig('image47.jpg'), _fig('image46.jpg'))
            + '<table><thead><tr><th style="width:200px;">Đặc điểm</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Kiểu mái</b></td><td>Hệ mái <b>cao</b>; <b>CÓ xây góc chữ A</b>; '
            'đứng phía trước <b>không nhìn rõ phần ngói</b>.</td></tr>'
            '<tr><td><b>Phù hợp</b></td><td><b>Đất rộng &mdash; nhà vườn</b>.</td></tr>'
            '<tr><td><b>Chi phí</b></td><td><b style="color:#dc2626;">ĐẮT HƠN mái Nhật</b> (vì mái cao, nhiều vật tư hơn).</td></tr>'
            '</tbody></table>'
            + _core('Mái Thái = <b>mái cao &middot; CÓ góc chữ A &middot; đứng trước không thấy ngói &middot; ĐẮT HƠN mái Nhật</b>.')
        )

    def _p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">SO SÁNH NHANH: MÁI NHẬT vs MÁI THÁI</h2>'
            '<p style="' + lead + '">Hai mẫu này hay bị nhầm. Đây là bảng phân biệt bạn '
            '<b>phải thuộc</b>.</p>'
            '<table><thead><tr><th style="width:34%;">Tiêu chí</th>'
            '<th style="text-align:center;">MÁI NHẬT</th>'
            '<th style="text-align:center;">MÁI THÁI</th></tr></thead><tbody>'
            '<tr><td><b>Độ cao mái</b></td>'
            '<td style="text-align:center;">Mái <b>lùn, thấp</b></td>'
            '<td style="text-align:center;">Mái <b>cao</b></td></tr>'
            '<tr><td><b>Góc chữ A</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">KHÔNG có</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">CÓ</td></tr>'
            '<tr><td><b>Nhìn từ phía trước</b></td>'
            '<td style="text-align:center;">Dễ <b>khoe phần ngói</b></td>'
            '<td style="text-align:center;"><b>Không nhìn rõ</b> phần ngói</td></tr>'
            '<tr><td><b>Chi phí</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">Rẻ hơn</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">Đắt hơn</td></tr>'
            '</tbody></table>'
            + _gallery(_fig('image29.jpg', 'Đối chiếu hình dáng mái'),
                       _fig('image25.png', 'Phân biệt mái Nhật và mái Thái'))
            + _advice(
                '<p style="margin-bottom:0;"><b>Mẹo phân biệt nhanh:</b> nhìn vào đỉnh mái phía '
                'trước &mdash; thấy <b>góc nhọn cao hình chữ A</b> thì là <b>MÁI THÁI</b>; '
                'thấy mái <b>thấp, lùn, lộ rõ hàng ngói</b> thì là <b>MÁI NHẬT</b>.</p>'
            )
            + _core('Khác nhau cốt lõi: <b>góc chữ A</b> (Thái CÓ, Nhật KHÔNG) và <b>chi phí</b> (Thái đắt hơn).')
        )

    def _p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">MẪU NHÀ KHÁC (tham khảo &mdash; cao cấp)</h2>'
            '<p style="' + lead + '">Ngoài 3 mẫu chủ đạo, còn vài mẫu <b>cao cấp, đặc thù</b>, '
            'ít phổ biến hơn nhưng khách đôi khi sẽ hỏi.</p>'
            '<table><thead><tr><th style="width:160px;">Mẫu</th><th>Đặc điểm chung</th></tr></thead><tbody>'
            '<tr><td><b>Indochine</b><br/>(Đông Dương)</td>'
            '<td>Phong cách giao thoa <b>Á &mdash; Âu</b>, hoài cổ, sang trọng, hay dùng gạch bông, '
            'hoa văn xưa.</td></tr>'
            '<tr><td><b>Tân cổ điển</b></td>'
            '<td>Sang trọng, có <b>phào chỉ</b>, đối xứng, bề thế nhưng nhẹ nhàng hơn cổ điển thuần.</td></tr>'
            '<tr><td><b>Nhà mái Pháp</b></td>'
            '<td>Biệt thự kiểu Pháp, <b>mái dốc nhiều lớp</b>, cầu kỳ, đẳng cấp, chi phí cao.</td></tr>'
            '</tbody></table>'
            + _gallery(_fig('image49.jpg'), _fig('image44.jpg'), _fig('image36.jpg'),
                       _fig('image43.jpg'), _fig('image40.jpg'), _fig('image35.jpg'))
            + _note(
                '<p style="margin-bottom:0;">Đây là nhóm <b>cao cấp</b>, chi phí lớn và cần đội '
                'thiết kế chuyên sâu. Bạn chỉ cần <b>nhận ra tên gọi</b> để khi khách hỏi thì '
                'biết và chuyển tiếp tư vấn, không cần thuộc chi tiết.</p>'
            )
        )

    def _p7(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁC HẠNG MỤC ĐẶC BIỆT</h2>'
            '<p style="' + lead + '">Đây là các phần khách hay hỏi thêm khi xây nhà. Hiểu để '
            'tư vấn và biết phần nào làm <b>tăng chi phí</b>.</p>'

            '<h3 style="' + h3 + '">1) TUM và SÂN THƯỢNG</h3>'
            + _gallery(_fig('image42.jpg', 'Tum và sân thượng'), _fig('image41.jpg'))
            + '<table><thead><tr><th style="width:160px;">Hạng mục</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Tum</b></td><td>Diện tích <b>15 &mdash; 25 m&sup2;</b>; là <b>mái che khu '
            'cầu thang</b> trên cùng; <b>có thể kết hợp làm phòng thờ</b>.</td></tr>'
            '<tr><td><b>Sân thượng</b></td><td><b>Sân trước:</b> nơi ăn BBQ, uống cafe, trồng cây&hellip; '
            '&nbsp;&middot;&nbsp; <b>Sân sau:</b> để máy giặt, phơi quần áo. Có thể có <b>mái trang trí</b> '
            'hoặc không.</td></tr>'
            '</tbody></table>'
            + _mistake(
                '<p style="margin-bottom:0;">Sân thượng <b>có mái trang trí</b> thì <b>chi phí thi '
                'công CAO HƠN</b> so với sân thượng không mái. Đừng quên nói rõ điểm này khi báo giá.</p>'
            )

            + '<h3 style="' + h3 + '">2) TẦNG LỬNG và THÔNG TẦNG</h3>'
            + _gallery(_fig('image45.jpg', 'Tầng lửng - Thông tầng'))
            + '<table><thead><tr><th style="width:160px;">Hạng mục</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Tầng lửng</b></td><td>Tầng phụ xen giữa, chiều cao khoảng <b>3 m</b>.</td></tr>'
            '<tr><td><b>Thông tầng</b></td><td>Khoảng không thông 2 tầng, thường bố trí ở <b>phòng khách</b>; '
            'chiều cao khoảng <b>6 m</b>; chiếm <b>30 &mdash; 50% diện tích sàn</b>.</td></tr>'
            '</tbody></table>'
            + _core(
                'Tum <b>15-25 m&sup2;</b> (che cầu thang, có thể làm phòng thờ) &middot; '
                'Tầng lửng <b>~3 m</b> &middot; Thông tầng <b>~6 m, 30-50% sàn</b> &middot; '
                'mái trang trí = <b>tốn thêm chi phí</b>.'
            )
        )

    def _p8(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127942; KẾT LUẬN &mdash; NHẬN BIẾT NHANH</h2>'
            '<table><thead><tr><th>Mẫu nhà</th><th>Mái</th><th>Hợp với</th>'
            '<th style="text-align:center;">Chi phí</th></tr></thead><tbody>'
            '<tr><td><b>Vuông hiện đại</b></td><td>Mái bằng</td><td>Nhà phố</td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">Rẻ nhất</td></tr>'
            '<tr><td><b>Mái Nhật</b></td><td>Mái thấp, không góc chữ A</td><td>Đất rộng, nhà vườn</td>'
            '<td style="text-align:center;font-weight:800;">Trung bình</td></tr>'
            '<tr><td><b>Mái Thái</b></td><td>Mái cao, có góc chữ A</td><td>Đất rộng, nhà vườn</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">Đắt nhất (trong 3 mẫu)</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p><b>Kịch bản tư vấn ngắn:</b></p>'
                '<ul>'
                '<li>Khách <b>đất hẹp / nhà phố, muốn tiết kiệm</b> &rarr; gợi ý <b>nhà vuông hiện đại</b>.</li>'
                '<li>Khách <b>đất rộng, thích mái ngói</b>, ngân sách vừa &rarr; <b>mái Nhật</b>.</li>'
                '<li>Khách <b>đất rộng, thích bề thế</b>, ngân sách cao hơn &rarr; <b>mái Thái</b>.</li>'
                '</ul>'
                '<p style="margin-bottom:0;">Luôn hỏi <b>diện tích đất</b> và <b>ngân sách</b> trước khi gợi ý mẫu.</p>'
            )

            + _core(
                'Thuộc 3 mẫu chủ đạo và cách phân biệt <b>mái Nhật (thấp, không góc A, rẻ hơn)</b> '
                'với <b>mái Thái (cao, có góc A, đắt hơn)</b> là bạn đã tư vấn được mẫu nhà cơ bản.'
            )

            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Mẫu nào <b>rẻ nhất</b> và <b>phổ biến nhất</b>? (vuông hiện đại)</li>'
            '<li>Mái nào <b>có góc chữ A</b>, mái nào <b>không</b>? (Thái có, Nhật không)</li>'
            '<li>Mái nào <b>đắt hơn</b>? (mái Thái)</li>'
            '<li>Tum dùng làm gì? Diện tích bao nhiêu? (che cầu thang / có thể phòng thờ &mdash; 15-25 m&sup2;)</li>'
            '<li>Thông tầng cao bao nhiêu, chiếm bao nhiêu % sàn? (~6 m, 30-50%)</li>'
            '</ol>'
        )

    # ==================================================================
    #  20 CAU HOI (dap an, dung?)
    # ==================================================================
    def _vd_mn_questions(self):
        T, F = True, False
        return [
            ('"Mẫu nhà" là gì?',
             [('Kiểu dáng và phong cách kiến trúc tổng thể của căn nhà', T),
              ('Tên chủ nhà', F),
              ('Số tiền xây nhà', F),
              ('Diện tích miếng đất', F)]),

            ('Ba mẫu nhà CHỦ ĐẠO (hay gặp nhất) là gì?',
             [('Nhà vuông hiện đại, nhà mái Nhật, nhà mái Thái', T),
              ('Indochine, Tân cổ điển, Mái Pháp', F),
              ('Nhà cấp 4, chung cư, nhà trọ', F),
              ('Tum, sân thượng, tầng lửng', F)]),

            ('Mẫu nhà nào có chi phí RẺ NHẤT?',
             [('Nhà vuông hiện đại', T),
              ('Nhà mái Thái', F),
              ('Nhà mái Pháp', F),
              ('Nhà Indochine', F)]),

            ('Mẫu nhà nào được sử dụng NHIỀU NHẤT (phổ biến nhất)?',
             [('Nhà vuông hiện đại', T),
              ('Nhà mái Thái', F),
              ('Nhà Tân cổ điển', F),
              ('Nhà mái Pháp', F)]),

            ('Mẫu nhà nào phù hợp nhất với NHÀ PHỐ (đất hẹp, hình ống)?',
             [('Nhà vuông hiện đại', T),
              ('Nhà mái Thái', F),
              ('Nhà mái Nhật', F),
              ('Nhà mái Pháp', F)]),

            ('Nhà vuông hiện đại dùng kiểu mái gì?',
             [('Mái bằng (mái phẳng)', T),
              ('Mái cao có góc chữ A', F),
              ('Mái dốc nhiều lớp kiểu Pháp', F),
              ('Không có mái', F)]),

            ('Đặc điểm của mái NHẬT là gì?',
             [('Hệ mái lùn, thấp, KHÔNG có góc chữ A, dễ khoe phần ngói', T),
              ('Hệ mái cao, có góc chữ A', F),
              ('Mái bằng phẳng hoàn toàn', F),
              ('Mái dốc nhiều lớp cầu kỳ', F)]),

            ('Đặc điểm của mái THÁI là gì?',
             [('Hệ mái cao, CÓ xây góc chữ A, đứng trước không nhìn rõ ngói', T),
              ('Hệ mái lùn thấp, không có góc chữ A', F),
              ('Mái bằng phẳng', F),
              ('Không có ngói', F)]),

            ('Mái nào KHÔNG có góc chữ A?',
             [('Mái Nhật', T),
              ('Mái Thái', F),
              ('Mái Pháp', F),
              ('Cả hai đều có', F)]),

            ('Mái nào CÓ góc chữ A?',
             [('Mái Thái', T),
              ('Mái Nhật', F),
              ('Mái bằng', F),
              ('Không mái nào có', F)]),

            ('Đứng phía trước KHÔNG nhìn rõ phần ngói là mái nào?',
             [('Mái Thái', T),
              ('Mái Nhật', F),
              ('Mái bằng', F),
              ('Mái nào cũng thấy rõ ngói', F)]),

            ('Tầng lửng có chiều cao khoảng bao nhiêu?',
             [('Khoảng 3 m', T),
              ('Khoảng 6 m', F),
              ('Khoảng 10 m', F),
              ('Khoảng 1 m', F)]),

            ('So sánh chi phí giữa mái Nhật và mái Thái?',
             [('Mái Nhật rẻ hơn, mái Thái đắt hơn', T),
              ('Mái Thái rẻ hơn mái Nhật', F),
              ('Hai mái giá bằng nhau', F),
              ('Mái Nhật đắt gấp đôi mái Thái', F)]),

            ('Nhà mái Nhật và mái Thái phù hợp với loại đất nào?',
             [('Đất rộng, nhà vườn', T),
              ('Đất hẹp trong hẻm nhỏ', F),
              ('Chỉ làm được trên đất dưới 30 m2', F),
              ('Không cần đất', F)]),

            ('Các mẫu nhà khác (tham khảo, cao cấp) gồm những gì?',
             [('Indochine, Tân cổ điển, Nhà mái Pháp', T),
              ('Vuông hiện đại, mái Nhật, mái Thái', F),
              ('Nhà trọ, chung cư, nhà cấp 4', F),
              ('Tum, sân thượng, tầng lửng', F)]),

            ('Tum dùng để làm gì?',
             [('Là mái che khu cầu thang trên cùng, có thể kết hợp làm phòng thờ', T),
              ('Là tầng hầm để xe', F),
              ('Là sân trước để uống cafe', F),
              ('Là phòng ngủ chính', F)]),

            ('Diện tích của Tum khoảng bao nhiêu?',
             [('Khoảng 15 - 25 m2', T),
              ('Khoảng 100 m2', F),
              ('Khoảng 1 - 2 m2', F),
              ('Khoảng 60 - 80 m2', F)]),

            ('Có thể bố trí phòng thờ trên tum được không?',
             [('Có thể kết hợp làm phòng thờ', T),
              ('Tuyệt đối không được', F),
              ('Chỉ làm nhà kho thôi', F),
              ('Tum không liên quan phòng thờ', F)]),

            ('Sân thượng CÓ mái trang trí thì chi phí thế nào?',
             [('Chi phí thi công CAO HƠN sân thượng không mái', T),
              ('Rẻ hơn sân thượng không mái', F),
              ('Không ảnh hưởng chi phí', F),
              ('Được miễn phí', F)]),

            ('Thông tầng thường chiếm khoảng bao nhiêu phần trăm diện tích sàn?',
             [('Khoảng 30 - 50% diện tích sàn', T),
              ('Khoảng 90 - 100% diện tích sàn', F),
              ('Khoảng 5% diện tích sàn', F),
              ('Không chiếm diện tích nào', F)]),
        ]
