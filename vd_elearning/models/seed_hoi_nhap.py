# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau hoi thi cho khoa HOI NHAP nhan vien moi:
"Vinaduy va Hoi nhap".

Khoa dau tien trong lo trinh: gioi thieu cong ty, linh vuc xay nha tron goi,
tam nhin - su menh - gia tri, san pham dich vu, hanh trinh khach hang va vai
tro cua NV, co cau to chuc - van hoa - tac phong, lo trinh dao tao va cam ket.

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai. Tai
dung khung trinh bay tu seed_kh_tiem_nang de dong bo phong cach.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _situation, _advice, _proof, _mistake

_HN_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.hoinhap_seed_version'


# --- Khung rieng cho khoa hoi nhap (khong dung _formula/_apply mang giong sale) ---
def _core(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">&#11088; DIEU PHAI GHI NHO</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _action(inner):
    return (
        '<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;'
        'padding:16px 18px;margin:18px 0;">'
        '<div style="font-weight:900;color:#b91c1c;font-size:15px;margin-bottom:8px;">'
        '&#128308; VIEC CAN LAM NGAY</div>'
        '<div>%s</div></div>'
    ) % inner


class SlideChannelSeedHoiNhap(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_hoi_nhap(self):
        ch = self.env.ref('vd_elearning.course_hoi_nhap', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _HN_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_hn_pages())
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
        for text, answers in self._vd_hn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _HN_VERSION)
        return True

    # ==================================================================
    #  NOI DUNG BAI HOC
    # ==================================================================
    def _vd_hn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Chào mừng - Vinaduy là ai', self._page1(h2, h3, lead)),
            ('2. Tầm nhìn - Sứ mệnh - Giá trị cốt lõi', self._page2(h2, h3, lead)),
            ('3. Sản phẩm dịch vụ - Lợi thế', self._page3(h2, h3, lead)),
            ('4. Hành trình khách hàng - Vai trò của bạn', self._page4(h2, h3, lead)),
            ('5. Cơ cấu tổ chức - Văn hóa - Tác phong', self._page5(h2, h3, lead)),
            ('6. Lộ trình đào tạo - Cam kết hội nhập', self._page6(h2, h3, lead)),
        ]

    def _page1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#1e3a8a,#3730a3);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.85;font-weight:700;">'
            'CHÀO MỪNG BẠN GIA NHẬP</div>'
            '<div style="font-size:26px;font-weight:900;margin-top:4px;">VINADUY</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:6px;">Cùng nhau xây nên '
            'những tổ ấm vững bền cho mọi gia đình Việt.</div></div>'

            '<p style="' + lead + '">Chúc mừng bạn đã trở thành thành viên của <b>Vinaduy</b>. '
            'Khóa học này giúp bạn <b>hiểu công ty</b>, hiểu <b>công việc</b> của mình và '
            '<b>hòa nhập</b> nhanh nhất. Hãy đọc kỹ và làm bài thi cuối khóa.</p>'

            '<h2 style="' + h2 + '">&#127970; Vinaduy là ai?</h2>'
            '<p>Vinaduy là công ty hoạt động trong lĩnh vực <b>xây nhà trọn gói</b> &mdash; '
            'từ <b>thiết kế kiến trúc</b>, <b>thi công xây dựng</b> đến <b>hoàn thiện và bàn '
            'giao</b> căn nhà cho khách hàng theo hình thức "chìa khóa trao tay". Khách hàng '
            'của chúng ta là các <b>gia đình</b> đang chuẩn bị xây tổ ấm của họ.</p>'

            '<table><thead><tr><th style="width:200px;">Mảng hoạt động</th><th>Vinaduy làm gì</th></tr></thead><tbody>'
            '<tr><td><b>Thiết kế</b></td><td>Lên phương án kiến trúc, công năng, mẫu nhà phù hợp đất và ngân sách của khách.</td></tr>'
            '<tr><td><b>Thi công</b></td><td>Xây dựng phần thô, kết cấu, móng - cọc đúng kỹ thuật, an toàn.</td></tr>'
            '<tr><td><b>Hoàn thiện</b></td><td>Vật tư hoàn thiện, sơn, điện nước, bàn giao nhà hoàn chỉnh.</td></tr>'
            '<tr><td><b>Đồng hành</b></td><td>Tư vấn, khảo sát, cân đối tài chính, bảo hành sau bàn giao.</td></tr>'
            '</tbody></table>'

            + _core(
                'Bạn không chỉ "bán dịch vụ" &mdash; bạn đang giúp một gia đình '
                '<b>hiện thực hóa giấc mơ về ngôi nhà cả đời</b>. Đó là công việc rất ý nghĩa.'
            )
            + _action(
                '<p style="margin-bottom:0;">Tự giới thiệu lại trong đầu: <i>"Tôi là nhân '
                'viên Vinaduy &mdash; công ty xây nhà trọn gói: thiết kế, thi công, hoàn '
                'thiện."</i> Nói to 3 lần cho thật tự nhiên, vì bạn sẽ nói câu này với '
                'khách hàng rất nhiều lần.</p>'
            )
        )

    def _page2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 2 &mdash; Tầm nhìn, Sứ mệnh, Giá trị cốt lõi</h2>'
            '<table><thead><tr><th style="width:120px;">Yếu tố</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b style="color:#1d4ed8;">Tầm nhìn</b></td>'
            '<td>Trở thành công ty xây nhà trọn gói được các gia đình Việt <b>tin tưởng</b> '
            'và <b>giới thiệu</b> cho nhau.</td></tr>'
            '<tr><td><b style="color:#16a34a;">Sứ mệnh</b></td>'
            '<td>Mang đến những ngôi nhà <b>chất lượng thật</b> &mdash; <b>giá minh bạch</b> '
            '&mdash; <b>đúng tiến độ</b>, để mỗi khách hàng đều an tâm khi xây nhà.</td></tr>'
            '</tbody></table>'

            '<h2 style="' + h2 + '">&#127775; 5 giá trị cốt lõi</h2>'
            '<table><thead><tr><th style="width:56px;">#</th><th style="width:150px;">Giá trị</th>'
            '<th>Ý nghĩa khi làm việc</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:18px;">&#129309;</td><td><b>Uy tín</b></td>'
            '<td>Nói được làm được, đã hứa với khách là giữ lời.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#127959;&#65039;</td><td><b>Chất lượng</b></td>'
            '<td>Làm thật, không gian dối vật tư, đúng kỹ thuật.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#10084;&#65039;</td><td><b>Tận tâm</b></td>'
            '<td>Coi nhà của khách như nhà của mình, tư vấn vì lợi ích của khách.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#128202;</td><td><b>Minh bạch</b></td>'
            '<td>Báo giá rõ ràng, không phát sinh mập mờ, số liệu trung thực.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#128737;&#65039;</td><td><b>Trách nhiệm</b></td>'
            '<td>Theo khách đến cùng, sai thì sửa, bảo hành đầy đủ.</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Xây nhà là khoản chi <b>lớn nhất đời người</b> '
                'với đa số khách hàng. Họ chỉ xuống tiền khi <b>tin tưởng</b>. Vì vậy uy tín '
                'và minh bạch không phải khẩu hiệu &mdash; đó là thứ trực tiếp quyết định '
                'khách có ký hợp đồng với bạn hay không.</p>'
            )
            + _core(
                'Mọi lời tư vấn của bạn phải dựa trên 5 giá trị này. '
                '<b>Trung thực với khách = doanh thu bền vững.</b>'
            )
            + _action(
                '<p style="margin-bottom:0;">Học thuộc <b>5 giá trị cốt lõi</b>: Uy tín &middot; '
                'Chất lượng &middot; Tận tâm &middot; Minh bạch &middot; Trách nhiệm. Tự kiểm '
                'tra: lần tư vấn gần nhất của bạn (nếu có) đã thể hiện giá trị nào?</p>'
            )
        )

    def _page3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 3 &mdash; Sản phẩm, dịch vụ và lợi thế</h2>'
            '<p style="' + lead + '">Để tư vấn được, bạn phải nắm <b>các gói dịch vụ</b> và '
            '<b>điểm mạnh</b> của Vinaduy so với nơi khác.</p>'

            '<h3 style="' + h3 + '">Các gói dịch vụ chính</h3>'
            '<table><thead><tr><th style="width:190px;">Gói</th><th>Phù hợp với khách</th></tr></thead><tbody>'
            '<tr><td><b>Xây trọn gói (chìa khóa trao tay)</b></td>'
            '<td>Khách muốn giao toàn bộ, nhận nhà hoàn thiện, ít phải lo.</td></tr>'
            '<tr><td><b>Xây thô + nhân công hoàn thiện</b></td>'
            '<td>Khách muốn tự lo phần vật tư hoàn thiện để chủ động chi phí.</td></tr>'
            '<tr><td><b>Thiết kế kiến trúc</b></td>'
            '<td>Khách cần bản vẽ, phương án công năng trước khi xây.</td></tr>'
            '<tr><td><b>Cải tạo - sửa chữa</b></td>'
            '<td>Khách nâng tầng, sửa nhà cũ, cải tạo công năng.</td></tr>'
            '</tbody></table>'

            '<h3 style="' + h3 + '">3 lợi thế phải thuộc lòng</h3>'
            '<table><thead><tr><th style="width:56px;">#</th><th>Lợi thế</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:800;color:#b45309;">1</td>'
            '<td><b>Báo giá minh bạch</b> &mdash; rõ hạng mục, hạn chế phát sinh.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#b45309;">2</td>'
            '<td><b>Khảo sát thực tế</b> để ra phương án chuẩn theo đất và ngân sách.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#b45309;">3</td>'
            '<td><b>Cam kết chất lượng và bảo hành</b> &mdash; theo khách đến khi bàn giao và sau đó.</td></tr>'
            '</tbody></table>'

            + _situation(
                '<p>Khách hỏi: <i>"Công ty em có gì khác mấy chỗ kia?"</i></p>'
                '<p style="margin-bottom:0;"><b>NV giỏi</b> trả lời ngay 3 ý: <i>"Dạ bên em '
                '<b>báo giá minh bạch từng hạng mục</b>, <b>khảo sát thực tế</b> rồi mới ra '
                'phương án chuẩn, và <b>cam kết chất lượng - bảo hành</b> rõ ràng ạ."</i> '
                '&mdash; ngắn gọn, đúng trọng tâm, tạo niềm tin.</p>'
            )
            + _advice(
                '<p style="margin-bottom:0;">Đừng chê đối thủ. Chỉ cần nói rõ <b>mình làm gì '
                'tốt cho khách</b>. Khách tin vào người tư vấn chắc chắn, không tin người nói '
                'xấu nơi khác.</p>'
            )
            + _action(
                '<p style="margin-bottom:0;">Viết ra <b>3 lợi thế</b> bằng giọng của bạn và '
                'đọc to 3 lần. Đây là câu trả lời bạn sẽ dùng mỗi khi khách so sánh công ty.</p>'
            )
        )

    def _page4(self, h2, h3, lead):
        rows = [
            ('1', 'Tiếp nhận khách', 'Nhận data/lead khách quan tâm xây nhà trên phần mềm CRM.'),
            ('2', 'Gọi - Tư vấn', 'Gọi điện, hỏi nhu cầu, xác định thời gian - tài chính - mẫu nhà - đất.'),
            ('3', 'Khảo sát', 'Hẹn lịch khảo sát thực tế miếng đất để ra phương án chuẩn.'),
            ('4', 'Báo giá', 'Gửi báo giá minh bạch theo phương án đã chốt.'),
            ('5', 'Ký hợp đồng', 'Chốt điều kiện, ký hợp đồng, giữ giá.'),
            ('6', 'Thi công', 'Bộ phận kỹ thuật triển khai; NV theo sát, chăm sóc khách.'),
            ('7', 'Bàn giao - Bảo hành', 'Nghiệm thu, bàn giao nhà, bảo hành và xin khách giới thiệu.'),
        ]
        body = (
            '<h2 style="' + h2 + '">PHẦN 4 &mdash; Hành trình khách hàng và vai trò của bạn</h2>'
            '<p style="' + lead + '">Một khách hàng đi qua <b>7 bước</b> từ lúc quan tâm đến '
            'lúc nhận nhà. Bạn là người <b>đồng hành</b> ở mọi bước, đặc biệt là khâu tư vấn.</p>'
            '<table><thead><tr><th style="width:48px;">Bước</th><th style="width:160px;">Giai đoạn</th>'
            '<th>Việc diễn ra</th></tr></thead><tbody>'
        )
        for n, g, m in rows:
            body += ('<tr><td style="text-align:center;font-weight:800;color:#b45309;">' + n
                     + '</td><td><b>' + g + '</b></td><td>' + m + '</td></tr>')
        body += '</tbody></table>'
        body += _core(
            'Vai trò của bạn xuyên suốt: <b>Gọi &#10145; Tư vấn &#10145; Khảo sát &#10145; '
            'Chốt &#10145; Chăm sóc</b>. Khách có ký hay không phụ thuộc lớn vào bạn.'
        )
        body += _mistake(
            '<ul>'
            '<li>Nhận lead nhưng <b>không gọi</b> hoặc gọi trễ &rArr; mất khách vào tay đối thủ.</li>'
            '<li>Tư vấn qua loa, không hỏi đủ thông tin &rArr; báo giá sai, khách bỏ.</li>'
            '<li>Không cập nhật khách lên <b>phần mềm CRM</b> &rArr; quên chăm, sót việc.</li>'
            '</ul>'
        )
        body += _action(
            '<p style="margin-bottom:0;">Ghi nhớ <b>7 bước hành trình khách hàng</b> theo '
            'đúng thứ tự. Mỗi khách bạn nhận, xác định họ đang ở <b>bước nào</b> để biết việc '
            'cần làm tiếp theo.</p>'
        )
        return body

    def _page5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 5 &mdash; Cơ cấu tổ chức, văn hóa, tác phong</h2>'
            '<h3 style="' + h3 + '">Cơ cấu và lộ trình thăng tiến</h3>'
            '<p>Công ty tổ chức theo <b>phòng ban kinh doanh</b> (ví dụ HCM1, HCM2, HN) và '
            'lực lượng <b>cộng tác viên (CTV)</b>. Mỗi phòng có trưởng nhóm dẫn dắt.</p>'
            '<table><thead><tr><th>Cấp bậc</th><th>Vai trò</th></tr></thead><tbody>'
            '<tr><td><b>Cộng tác viên (CTV)</b></td><td>Tìm và giới thiệu khách hàng tiềm năng.</td></tr>'
            '<tr><td><b>Nhân viên kinh doanh</b></td><td>Gọi, tư vấn, khảo sát, chốt hợp đồng.</td></tr>'
            '<tr><td><b>Trưởng nhóm</b></td><td>Quản lý, kèm cặp nhân viên, chịu trách nhiệm doanh số phòng.</td></tr>'
            '<tr><td><b>Giám đốc</b></td><td>Điều hành chung, định hướng và phát triển công ty.</td></tr>'
            '</tbody></table>'
            '<p style="text-align:center;font-size:15px;">Lộ trình: '
            '<b style="color:#16a34a;">CTV &#10145; Nhân viên &#10145; Trưởng nhóm &#10145; '
            'Giám đốc</b> &mdash; thăng tiến bằng <b>kết quả và thái độ</b>.</p>'

            '<h3 style="' + h3 + '">Tác phong làm việc</h3>'
            '<table><thead><tr><th style="width:50%;text-align:center;">&#9989; NÊN</th>'
            '<th style="width:50%;text-align:center;">&#10060; KHÔNG NÊN</th></tr></thead><tbody>'
            '<tr><td>Đi làm đúng giờ, gọi khách đủ chỉ tiêu mỗi ngày.</td>'
            '<td>Đi trễ, bỏ bê cuộc gọi, để khách chờ.</td></tr>'
            '<tr><td>Cập nhật trung thực thông tin khách lên CRM.</td>'
            '<td>Khai man số liệu, báo cáo gian dối.</td></tr>'
            '<tr><td>Lịch sự, kiên nhẫn, giữ lời hứa với khách.</td>'
            '<td>Cáu gắt, hứa suông, nói xấu công ty/đồng nghiệp.</td></tr>'
            '<tr><td>Hỏi và học hỏi khi chưa biết.</td>'
            '<td>Giấu dốt, làm sai mà không báo.</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Hai thứ giúp bạn thăng tiến nhanh nhất ở Vinaduy: '
                '<b>kỷ luật cuộc gọi</b> (gọi đều, gọi đủ) và <b>trung thực số liệu</b>. '
                'Người làm thật luôn được ghi nhận.</p>'
            )
            + _action(
                '<p style="margin-bottom:0;">Nắm rõ bạn thuộc <b>phòng ban nào</b>, <b>ai là '
                'trưởng nhóm</b> của bạn. Ghi lại 3 quy tắc tác phong bạn cần giữ nhất.</p>'
            )
        )

    def _page6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 6 &mdash; Lộ trình đào tạo và cam kết hội nhập</h2>'
            '<p style="' + lead + '">Sau khóa hội nhập này, bạn sẽ học tiếp các khóa <b>kỹ '
            'năng và nghiệp vụ</b> theo lộ trình trên phần mềm để trở thành nhân viên giỏi.</p>'
            '<table><thead><tr><th style="width:56px;">Thứ tự</th><th>Khóa học tiếp theo (ví dụ)</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:800;color:#3730a3;">1</td>'
            '<td><b>Vinaduy và Hội nhập</b> (khóa bạn đang học).</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#3730a3;">2</td>'
            '<td>Kỹ năng nhận diện khách hàng tiềm năng.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#3730a3;">3</td>'
            '<td>Kiến thức xây dựng cơ bản: mẫu nhà, móng, vật tư, đơn giá.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#3730a3;">4</td>'
            '<td>Kỹ năng cân đối tài chính và xử lý từ chối.</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Nghề tư vấn xây nhà cần <b>kiến thức</b> (hiểu '
                'sản phẩm) và <b>kỹ năng</b> (biết tư vấn, biết chốt). Học đủ lộ trình giúp '
                'bạn tự tin trước khách và <b>tăng thu nhập</b> nhanh.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Cam kết hội nhập</h2>'
            '<table><thead><tr><th style="width:56px;">#</th><th>Tôi cam kết</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;">&#9989;</td><td>Hiểu và sống đúng <b>5 giá trị cốt lõi</b> của Vinaduy.</td></tr>'
            '<tr><td style="text-align:center;">&#9989;</td><td>Tư vấn <b>trung thực</b>, đặt lợi ích khách hàng lên trước.</td></tr>'
            '<tr><td style="text-align:center;">&#9989;</td><td>Giữ <b>kỷ luật cuộc gọi</b> và cập nhật CRM đầy đủ.</td></tr>'
            '<tr><td style="text-align:center;">&#9989;</td><td>Học hết <b>lộ trình đào tạo</b> để giỏi nghề.</td></tr>'
            '</tbody></table>'

            + _core(
                'Vinaduy phát triển nhờ <b>khách hàng tin tưởng</b>; khách tin nhờ <b>mỗi '
                'nhân viên làm thật, tư vấn thật</b>. Bạn chính là gương mặt của công ty '
                'trước khách hàng.'
            )

            + '<h2 style="' + h2 + '">&#128221; Kết luận phải nhớ</h2>'
            '<ul>'
            '<li>Vinaduy = công ty <b>xây nhà trọn gói</b>: thiết kế - thi công - hoàn thiện.</li>'
            '<li>5 giá trị: <b>Uy tín - Chất lượng - Tận tâm - Minh bạch - Trách nhiệm</b>.</li>'
            '<li>3 lợi thế: <b>báo giá minh bạch - khảo sát thực tế - cam kết bảo hành</b>.</li>'
            '<li>Hành trình khách hàng <b>7 bước</b>; bạn đồng hành ở mọi bước.</li>'
            '<li>Thăng tiến bằng <b>kết quả + thái độ</b>; làm thật được ghi nhận.</li>'
            '</ul>'

            + _action(
                '<p>Tự chấm trước khi kết thúc khóa (trả lời Có/Chưa):</p>'
                '<ol>'
                '<li>Nói được Vinaduy làm <b>lĩnh vực gì</b> chưa?</li>'
                '<li>Thuộc <b>5 giá trị cốt lõi</b> chưa?</li>'
                '<li>Thuộc <b>3 lợi thế</b> chưa?</li>'
                '<li>Nhớ <b>7 bước hành trình khách hàng</b> chưa?</li>'
                '<li>Biết mình thuộc <b>phòng nào, trưởng nhóm là ai</b> chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Chưa" &rArr; xem lại phần tương ứng '
                'rồi làm bài thi.</p>'
            )
        )

    # ==================================================================
    #  20 CAU HOI TRAC NGHIEM (dap an, dung?)
    # ==================================================================
    def _vd_hn_questions(self):
        T, F = True, False
        return [
            ('Vinaduy hoạt động chính trong lĩnh vực nào?',
             [('Xây nhà trọn gói: thiết kế - thi công - hoàn thiện', T),
              ('Bán điện thoại di động', F),
              ('Cho vay tài chính', F),
              ('Kinh doanh bất động sản nghỉ dưỡng', F)]),

            ('Hình thức bàn giao nhà của Vinaduy thường được gọi là gì?',
             [('Chìa khóa trao tay (nhận nhà hoàn thiện)', T),
              ('Bán nhà xây sẵn', F),
              ('Cho thuê nhà', F),
              ('Đấu giá nhà', F)]),

            ('Khách hàng chủ yếu của Vinaduy là ai?',
             [('Các gia đình đang chuẩn bị xây nhà', T),
              ('Các quỹ đầu tư nước ngoài', F),
              ('Người đi du lịch', F),
              ('Sinh viên thuê trọ', F)]),

            ('Sứ mệnh của Vinaduy nhấn mạnh điều gì?',
             [('Chất lượng thật - giá minh bạch - đúng tiến độ', T),
              ('Giá rẻ nhất thị trường bằng mọi cách', F),
              ('Xây càng nhanh càng tốt bất kể chất lượng', F),
              ('Chỉ nhận công trình lớn', F)]),

            ('5 giá trị cốt lõi của Vinaduy là gì?',
             [('Uy tín - Chất lượng - Tận tâm - Minh bạch - Trách nhiệm', T),
              ('Nhanh - Nhiều - Rẻ - Tốt - Đẹp', F),
              ('Doanh số - Hoa hồng - Thưởng - Phạt - Đua top', F),
              ('Quảng cáo - Khuyến mãi - Quà tặng - Giảm giá - Bốc thăm', F)]),

            ('Vì sao uy tín và minh bạch lại đặc biệt quan trọng khi tư vấn xây nhà?',
             [('Vì xây nhà là khoản chi lớn nhất đời người, khách chỉ xuống tiền khi tin tưởng', T),
              ('Vì luật bắt buộc phải nói nhiều', F),
              ('Vì để được nghỉ sớm', F),
              ('Vì không quan trọng, chỉ là khẩu hiệu', F)]),

            ('Gói dịch vụ nào phù hợp khách muốn giao toàn bộ và nhận nhà hoàn thiện?',
             [('Xây trọn gói (chìa khóa trao tay)', T),
              ('Chỉ thiết kế bản vẽ', F),
              ('Chỉ cải tạo sửa chữa', F),
              ('Chỉ tư vấn miễn phí', F)]),

            ('Gói "Xây thô + nhân công hoàn thiện" phù hợp với khách nào?',
             [('Khách muốn tự lo vật tư hoàn thiện để chủ động chi phí', T),
              ('Khách không có đất', F),
              ('Khách chỉ muốn thuê nhà', F),
              ('Khách muốn mua nhà xây sẵn', F)]),

            ('3 lợi thế phải thuộc lòng của Vinaduy là gì?',
             [('Báo giá minh bạch - Khảo sát thực tế - Cam kết chất lượng và bảo hành', T),
              ('Giá rẻ nhất - Quà nhiều nhất - Tặng xe', F),
              ('Làm nhanh nhất - Không cần hợp đồng - Không bảo hành', F),
              ('Nói xấu đối thủ - Hứa thật nhiều - Giảm giá sốc', F)]),

            ('Khi khách hỏi "Công ty em có gì khác chỗ khác?", cách trả lời đúng là?',
             [('Nêu ngắn gọn 3 lợi thế: báo giá minh bạch, khảo sát thực tế, cam kết bảo hành', T),
              ('Chê bai các công ty khác', F),
              ('Im lặng không trả lời', F),
              ('Hứa giảm giá thật sâu để khách ký ngay', F)]),

            ('Thái độ đúng với đối thủ cạnh tranh là gì?',
             [('Không chê đối thủ, chỉ nói rõ mình làm tốt gì cho khách', T),
              ('Nói xấu đối thủ càng nhiều càng tốt', F),
              ('Bịa thông tin xấu về nơi khác', F),
              ('Khuyên khách đừng tìm hiểu nơi nào khác', F)]),

            ('Hành trình khách hàng tại Vinaduy gồm mấy bước chính?',
             [('7 bước: tiếp nhận - tư vấn - khảo sát - báo giá - ký HĐ - thi công - bàn giao/bảo hành', T),
              ('2 bước: gọi và ký', F),
              ('Không có quy trình cố định', F),
              ('10 bước về thủ tục hành chính', F)]),

            ('Bước đầu tiên trong hành trình khách hàng là gì?',
             [('Tiếp nhận khách/lead trên phần mềm CRM', T),
              ('Bàn giao nhà', F),
              ('Thi công móng', F),
              ('Bảo hành', F)]),

            ('Sai lầm nào dễ làm mất khách vào tay đối thủ nhất?',
             [('Nhận lead nhưng không gọi hoặc gọi trễ', T),
              ('Gọi khách đúng giờ', F),
              ('Cập nhật CRM đầy đủ', F),
              ('Tư vấn trung thực', F)]),

            ('Vì sao phải cập nhật thông tin khách lên phần mềm CRM?',
             [('Để không quên chăm sóc, không sót việc và theo dõi đúng bước của khách', T),
              ('Để khoe với đồng nghiệp', F),
              ('Vì bắt buộc nhưng vô ích', F),
              ('Để tính tiền điện', F)]),

            ('Lộ trình thăng tiến tại Vinaduy theo thứ tự nào?',
             [('CTV - Nhân viên - Trưởng nhóm - Giám đốc', T),
              ('Giám đốc - Trưởng nhóm - Nhân viên - CTV', F),
              ('Chỉ có 1 cấp duy nhất', F),
              ('Thăng tiến ngẫu nhiên không theo kết quả', F)]),

            ('Trưởng nhóm có vai trò gì?',
             [('Quản lý, kèm cặp nhân viên và chịu trách nhiệm doanh số phòng', T),
              ('Chỉ ngồi chơi', F),
              ('Đi khảo sát thay tất cả nhân viên', F),
              ('Không liên quan đến nhân viên', F)]),

            ('Đâu là tác phong NÊN có của nhân viên Vinaduy?',
             [('Đi làm đúng giờ, gọi đủ chỉ tiêu, cập nhật CRM trung thực', T),
              ('Khai man số liệu để đẹp báo cáo', F),
              ('Hứa suông với khách', F),
              ('Giấu dốt, làm sai không báo', F)]),

            ('Hai yếu tố giúp nhân viên thăng tiến nhanh nhất theo bài học là gì?',
             [('Kỷ luật cuộc gọi và trung thực số liệu', T),
              ('Quen biết và nịnh sếp', F),
              ('Nói nhiều và hứa nhiều', F),
              ('May mắn và đợi chờ', F)]),

            ('Sau khóa "Vinaduy và Hội nhập", nhân viên nên làm gì tiếp theo?',
             [('Học tiếp các khóa kỹ năng và nghiệp vụ theo lộ trình đào tạo', T),
              ('Ngừng học, không cần học thêm', F),
              ('Tự ý bỏ quy trình công ty', F),
              ('Chỉ học khi bị ép', F)]),
        ]
