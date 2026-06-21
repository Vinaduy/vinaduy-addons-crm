# -*- coding: utf-8 -*-
"""Seed noi dung khoa GIOI THIEU CONG TY cho nhan vien moi ngay dau:
"Vinaduy va Hoi nhap".

Phong cach: GIOI THIEU cho NV moi (chua biet gi ve cong ty va nganh xay nha
tron goi) hieu duoc cong ty lam gi, co nhung phong ban nao, tru so o dau, quy
mo va muc tieu. KHONG phai khoa tu van khach hang.

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai.
Bai thi nhe (10 cau de) chi de xac nhan NV da doc; dat 80%, thi lai khong gioi han.
"""
from odoo import api, models

from .seed_kh_tiem_nang import _WRAP, _box, _advice, _proof

_HN_VERSION = 'v2-intro'
_PARAM_KEY = 'vd_elearning.hoinhap_seed_version'


# --- Khung rieng cho khoa gioi thieu (giong tone "chao mung", co dau day du) ---
def _core(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">&#11088; ĐIỀU CẦN GHI NHỚ</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _note(inner):
    # Khung "BAN CO BIET" - giai thich khai niem cho NV moi chua biet gi.
    return _box('#0ea5e9', '#ecfeff', '&#128161;', 'Bạn có biết', inner)


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

        # Khoa gioi thieu: thi nhe nhang (de qua) - dat 80%, thi lai khong gioi han.
        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

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
            'channel_id': ch.id, 'name': 'Bài thi - 10 câu',
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
    #  NOI DUNG GIOI THIEU
    # ==================================================================
    def _vd_hn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Chao mung - Vinaduy lam gi', self._page1(h2, h3, lead)),
            ('2. Quy mo - Thanh tich - Muc tieu', self._page2(h2, h3, lead)),
            ('3. Cac phong ban trong cong ty', self._page3(h2, h3, lead)),
            ('4. Tru so va chi nhanh', self._page4(h2, h3, lead)),
            ('5. Mot ngoi nha ra doi the nao', self._page5(h2, h3, lead)),
            ('6. Van hoa - Ngay dau cua ban', self._page6(h2, h3, lead)),
        ]

    def _page1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#1e3a8a,#3730a3);color:#fff;'
            'padding:24px 26px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.85;font-weight:700;">'
            'CHÀO MỪNG BẠN ĐẾN VỚI</div>'
            '<div style="font-size:28px;font-weight:900;margin-top:4px;">CÔNG TY VINADUY</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Hôm nay là ngày đầu tiên '
            'của bạn. Khóa học ngắn này sẽ giúp bạn hiểu Vinaduy là công ty gì, làm về lĩnh '
            'vực nào, có những phòng ban nào và đang hướng tới điều gì.</div></div>'

            '<h2 style="' + h2 + '">&#127970; Vinaduy là công ty gì?</h2>'
            '<p style="' + lead + '">Vinaduy là <b>công ty xây dựng</b>, chuyên về '
            '<b>thiết kế nhà</b> và <b>xây nhà trọn gói</b> cho các gia đình. Nói đơn giản: '
            '<b>Vinaduy giúp khách hàng xây nên ngôi nhà của họ, từ lúc còn là bản vẽ cho '
            'đến khi thành căn nhà hoàn chỉnh để dọn vào ở.</b></p>'

            + _note(
                '<p><b>"Xây nhà trọn gói" nghĩa là gì?</b></p>'
                '<p>Là khách hàng <b>giao trọn</b> cho công ty lo từ đầu đến cuối: '
                '<b>thiết kế bản vẽ &rarr; xin phép xây dựng &rarr; thi công phần thô '
                '(móng, khung, tường) &rarr; hoàn thiện (sơn, điện, nước, ốp lát) &rarr; '
                'bàn giao nhà</b>. Khách chỉ việc nhận nhà và dọn vào ở &mdash; quen gọi là '
                '"chìa khóa trao tay".</p>'
                '<p style="margin-bottom:0;">Ngược lại, nếu khách tự thuê thợ làm từng khâu '
                'thì rất vất vả và dễ phát sinh. Vinaduy lo <b>trọn gói</b> để khách nhàn và '
                'yên tâm.</p>'
            )

            + _note(
                '<p style="margin-bottom:0;"><b>"Thiết kế nhà" là gì?</b> Là bước <b>vẽ ra '
                'ngôi nhà trên giấy (bản vẽ)</b> trước khi xây: hình dáng mặt tiền, số tầng, '
                'bố trí các phòng (công năng), kết cấu chịu lực. Có bản vẽ tốt thì xây mới '
                'đẹp, đúng ý và tiết kiệm.</p>'
            )

            + _core(
                'Vinaduy = công ty <b>thiết kế và xây nhà trọn gói</b>. '
                'Chúng ta lo cho khách <b>cả ngôi nhà</b>: từ bản vẽ đến lúc bàn giao chìa khóa.'
            )
        )

    def _page2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 2 &mdash; Quy mô, thành tích và mục tiêu</h2>'
            '<p style="' + lead + '">Để bạn tự hào về nơi mình làm việc, hãy biết Vinaduy '
            'đang ở đâu và đang hướng tới điều gì.</p>'

            '<h3 style="' + h3 + '">Quy mô hiện tại</h3>'
            '<table><thead><tr><th style="width:60%;">Chỉ số</th><th>Hiện tại</th></tr></thead><tbody>'
            '<tr><td>Số công trình bàn giao mỗi năm</td>'
            '<td><b style="color:#16a34a;">Khoảng 200 công trình / năm</b></td></tr>'
            '<tr><td>Giá trị trung bình mỗi công trình</td>'
            '<td><b style="color:#16a34a;">Khoảng 1 tỷ đồng / công trình</b></td></tr>'
            '<tr><td>Quy mô doanh thu ước tính</td>'
            '<td><b style="color:#16a34a;">Khoảng 200 tỷ đồng / năm</b></td></tr>'
            '</tbody></table>'
            '<p>Mỗi năm có <b>khoảng 200 gia đình</b> tin tưởng giao ngôi nhà của họ cho '
            'Vinaduy &mdash; đó là con số thể hiện <b>uy tín</b> của công ty.</p>'

            '<h2 style="' + h2 + '">&#127919; Mục tiêu và khát vọng của Vinaduy</h2>'
            '<table><thead><tr><th style="width:56px;">#</th><th>Vinaduy hướng tới</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:18px;">&#127942;</td>'
            '<td>Trở thành công ty <b>TỐT NHẤT</b> và <b>ĐI ĐẦU</b> trong lĩnh vực xây nhà trọn gói.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#127759;</td>'
            '<td><b>Mỗi tỉnh thành đều có chi nhánh</b> Vinaduy.</td></tr>'
            '<tr><td style="text-align:center;font-size:18px;">&#127970;</td>'
            '<td>Thi công <b>hàng nghìn công trình mỗi năm</b>.</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Từ <b>khoảng 200 công trình/năm</b> tiến tới '
                '<b>hàng nghìn công trình/năm</b> và <b>có mặt ở mọi tỉnh thành</b> &mdash; '
                'đây là chặng đường lớn, và <b>mỗi nhân viên mới như bạn chính là một phần '
                'của hành trình đó</b>.</p>'
            )

            + _core(
                'Hiện tại: ~200 công trình/năm (~1 tỷ/công trình). '
                'Mục tiêu: <b>đi đầu ngành xây nhà trọn gói &middot; mỗi tỉnh thành có chi '
                'nhánh &middot; hàng nghìn công trình/năm</b>.'
            )
        )

    def _page3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 3 &mdash; Các phòng ban trong công ty</h2>'
            '<p style="' + lead + '">Một ngôi nhà hoàn thành là nhờ <b>nhiều phòng ban phối '
            'hợp</b>. Dưới đây là các bộ phận chính của Vinaduy và việc của từng bộ phận.</p>'

            '<table><thead><tr><th style="width:210px;">Phòng ban</th><th>Nhiệm vụ chính</th></tr></thead><tbody>'
            '<tr><td><b style="color:#1d4ed8;">Phòng Kinh doanh</b><br/>(các nhóm HCM1, HCM2, HN&hellip;)</td>'
            '<td>Tư vấn khách hàng, giới thiệu dịch vụ, khảo sát nhu cầu và <b>chốt hợp đồng</b> xây nhà.</td></tr>'
            '<tr><td><b style="color:#9333ea;">Phòng Thiết kế</b></td>'
            '<td>Vẽ <b>bản vẽ kiến trúc</b> (mặt tiền, công năng) và <b>kết cấu</b> cho ngôi nhà của khách.</td></tr>'
            '<tr><td><b style="color:#b45309;">Phòng Thi công và Kỹ thuật</b></td>'
            '<td>Đội ngũ <b>kỹ sư và thợ xây</b> trực tiếp thi công ngoài công trường, '
            '<b>giám sát kỹ thuật</b>, bảo đảm chất lượng và tiến độ.</td></tr>'
            '<tr><td><b style="color:#0f766e;">Phòng Hỗ trợ và Hành chính</b></td>'
            '<td>Kế toán, nhân sự, hành chính &mdash; hỗ trợ toàn công ty vận hành trơn tru.</td></tr>'
            '<tr><td><b style="color:#6b7280;">Cộng tác viên (CTV)</b></td>'
            '<td>Lực lượng <b>giới thiệu khách hàng</b> tiềm năng cho công ty.</td></tr>'
            '</tbody></table>'

            + _note(
                '<p style="margin-bottom:0;">Mỗi phòng ban là <b>một mắt xích</b>: Kinh doanh '
                'tìm và chốt khách &rarr; Thiết kế vẽ nhà &rarr; Thi công và Kỹ thuật xây '
                'dựng &rarr; các phòng hỗ trợ lo phần còn lại. Tất cả cùng tạo nên <b>một '
                'ngôi nhà hoàn chỉnh</b> cho khách.</p>'
            )

            + _core(
                'Ba phòng ban "làm nên ngôi nhà": <b>Kinh doanh &middot; Thiết kế &middot; '
                'Thi công và Kỹ thuật</b>.'
            )
        )

    def _page4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 4 &mdash; Trụ sở và chi nhánh</h2>'
            '<p style="' + lead + '">Vinaduy hoạt động ở các thành phố lớn và đang mở rộng '
            'ra toàn quốc.</p>'

            '<table><thead><tr><th style="width:200px;">Cơ sở</th><th>Vai trò</th></tr></thead><tbody>'
            '<tr><td><b>Trụ sở chính &mdash; TP. Hồ Chí Minh</b></td>'
            '<td>Trung tâm điều hành, có các nhóm kinh doanh (HCM1, HCM2&hellip;), thiết kế, thi công.</td></tr>'
            '<tr><td><b>Chi nhánh &mdash; Hà Nội</b></td>'
            '<td>Phục vụ khách hàng khu vực phía Bắc.</td></tr>'
            '<tr><td><b>Định hướng mở rộng</b></td>'
            '<td><b>Mỗi tỉnh thành đều có chi nhánh Vinaduy</b> trong tương lai gần.</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Ngày đầu, bạn nên biết rõ <b>mình làm ở cơ sở '
                'nào</b>, thuộc <b>phòng/nhóm nào</b> và <b>ai là người quản lý trực tiếp</b> '
                'của mình để tiện trao đổi công việc.</p>'
            )

            + _core(
                'Trụ sở chính ở <b>TP. Hồ Chí Minh</b>, chi nhánh tại <b>Hà Nội</b>; '
                'mục tiêu <b>mỗi tỉnh thành đều có chi nhánh</b>.'
            )
        )

    def _page5(self, h2, h3, lead):
        rows = [
            ('1', 'Khách liên hệ', 'Khách quan tâm xây nhà để lại thông tin / gọi đến công ty.'),
            ('2', 'Kinh doanh tư vấn', 'Nhân viên kinh doanh tư vấn nhu cầu, mẫu nhà, ngân sách.'),
            ('3', 'Khảo sát', 'Khảo sát thực tế miếng đất của khách.'),
            ('4', 'Thiết kế', 'Phòng thiết kế vẽ bản vẽ kiến trúc và công năng.'),
            ('5', 'Báo giá và ký hợp đồng', 'Thống nhất phương án, báo giá rõ ràng, ký hợp đồng.'),
            ('6', 'Thi công', 'Phòng Thi công và Kỹ thuật xây phần thô, kết cấu.'),
            ('7', 'Hoàn thiện', 'Sơn, điện nước, ốp lát&hellip; hoàn chỉnh ngôi nhà.'),
            ('8', 'Bàn giao và bảo hành', 'Nghiệm thu, bàn giao chìa khóa, bảo hành cho khách.'),
        ]
        body = (
            '<h2 style="' + h2 + '">PHẦN 5 &mdash; Một ngôi nhà Vinaduy ra đời như thế nào?</h2>'
            '<p style="' + lead + '">Để bạn hình dung cách công ty vận hành, đây là hành '
            'trình một ngôi nhà từ lúc khách liên hệ đến khi nhận nhà.</p>'
            '<table><thead><tr><th style="width:48px;">Bước</th><th style="width:200px;">Giai đoạn</th>'
            '<th>Diễn ra điều gì</th></tr></thead><tbody>'
        )
        for n, g, m in rows:
            body += ('<tr><td style="text-align:center;font-weight:800;color:#b45309;">' + n
                     + '</td><td><b>' + g + '</b></td><td>' + m + '</td></tr>')
        body += '</tbody></table>'
        body += _note(
            '<p style="margin-bottom:0;">Bạn sẽ thấy <b>cả ba phòng ban chính</b> cùng xuất '
            'hiện trong hành trình này: Kinh doanh (bước 1-5), Thiết kế (bước 4), Thi công '
            'và Kỹ thuật (bước 6-8). Đó là lý do các phòng phải <b>phối hợp nhịp nhàng</b>.</p>'
        )
        body += _core(
            'Một ngôi nhà = <b>Tư vấn &rarr; Khảo sát &rarr; Thiết kế &rarr; Ký hợp đồng '
            '&rarr; Thi công &rarr; Hoàn thiện &rarr; Bàn giao</b>.'
        )
        return body

    def _page6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHẦN 6 &mdash; Văn hóa và ngày đầu của bạn</h2>'
            '<p style="' + lead + '">Vinaduy đề cao tinh thần <b>tận tâm &middot; trung thực '
            '&middot; chuyên nghiệp</b>. Coi ngôi nhà của khách như nhà của mình &mdash; đó '
            'là điều làm nên uy tín của công ty.</p>'

            '<h3 style="' + h3 + '">Ngày đầu tiên, bạn nên:</h3>'
            '<ul>'
            '<li>Làm quen với <b>đồng nghiệp</b> và <b>người quản lý trực tiếp</b>.</li>'
            '<li>Ghi nhớ <b>công ty làm gì</b> và <b>các phòng ban</b> để biết khi cần thì hỏi ai.</li>'
            '<li><b>Mạnh dạn hỏi</b> khi chưa rõ &mdash; không ai trách người mới chịu khó học hỏi.</li>'
            '<li>Làm quen với <b>phần mềm và công cụ</b> công ty đang dùng.</li>'
            '</ul>'

            + _advice(
                '<p style="margin-bottom:0;">Đừng lo nếu hôm nay bạn chưa nhớ hết. Quan trọng '
                'nhất là <b>tinh thần ham học hỏi</b> và <b>thái độ tích cực</b>. Mọi kỹ năng '
                'chuyên môn sẽ được đào tạo dần ở các khóa học tiếp theo.</p>'
            )

            + '<h2 style="' + h2 + '">&#128221; Tóm tắt cần nhớ</h2>'
            '<ul>'
            '<li>Vinaduy là công ty <b>thiết kế và xây nhà trọn gói</b> (lo trọn từ bản vẽ đến bàn giao).</li>'
            '<li>Hiện làm <b>~200 công trình/năm</b>, mỗi công trình <b>~1 tỷ đồng</b>.</li>'
            '<li>Mục tiêu: <b>đi đầu ngành &middot; mỗi tỉnh thành có chi nhánh &middot; hàng nghìn công trình/năm</b>.</li>'
            '<li>Phòng ban chính: <b>Kinh doanh &middot; Thiết kế &middot; Thi công và Kỹ thuật</b> (cùng các bộ phận hỗ trợ).</li>'
            '<li>Trụ sở chính tại <b>TP. Hồ Chí Minh</b>, chi nhánh <b>Hà Nội</b>.</li>'
            '</ul>'

            + _core(
                'Chào mừng bạn đến với Vinaduy! Hãy tự hào vì bạn đang góp phần '
                '<b>xây nên những tổ ấm</b> cho hàng trăm gia đình mỗi năm.'
            )
        )

    # ==================================================================
    #  10 CAU HOI NHE (xac nhan da doc). (dap an, dung?)
    # ==================================================================
    def _vd_hn_questions(self):
        T, F = True, False
        return [
            ('Vinaduy là công ty hoạt động trong lĩnh vực nào?',
             [('Thiết kế và xây nhà trọn gói cho các gia đình', T),
              ('Bán điện thoại di động', F),
              ('Kinh doanh quán ăn', F),
              ('Du lịch lữ hành', F)]),

            ('"Xây nhà trọn gói" nghĩa là gì?',
             [('Công ty lo trọn từ thiết kế, thi công đến hoàn thiện và bàn giao nhà', T),
              ('Khách tự thuê thợ làm từng khâu', F),
              ('Chỉ bán vật liệu xây dựng', F),
              ('Chỉ cho thuê nhà', F)]),

            ('"Thiết kế nhà" là bước làm gì?',
             [('Vẽ ra ngôi nhà trên bản vẽ (kiến trúc, công năng, kết cấu) trước khi xây', T),
              ('Đổ móng nhà', F),
              ('Sơn tường nhà', F),
              ('Dọn nhà cho khách', F)]),

            ('Hiện tại mỗi năm Vinaduy bàn giao khoảng bao nhiêu công trình?',
             [('Khoảng 200 công trình / năm', T),
              ('Khoảng 5 công trình / năm', F),
              ('Khoảng 10.000 công trình / năm', F),
              ('Không xây công trình nào', F)]),

            ('Giá trị trung bình mỗi công trình của Vinaduy khoảng bao nhiêu?',
             [('Khoảng 1 tỷ đồng / công trình', T),
              ('Khoảng 10 triệu đồng / công trình', F),
              ('Khoảng 100 tỷ đồng / công trình', F),
              ('Miễn phí cho khách', F)]),

            ('Mục tiêu lớn của Vinaduy là gì?',
             [('Trở thành công ty tốt nhất, đi đầu trong lĩnh vực xây nhà trọn gói', T),
              ('Chỉ làm cho vui, không cần phát triển', F),
              ('Chuyển sang bán cà phê', F),
              ('Giảm dần số công trình mỗi năm', F)]),

            ('Về mạng lưới, Vinaduy đặt mục tiêu gì?',
             [('Mỗi tỉnh thành đều có chi nhánh và thi công hàng nghìn công trình mỗi năm', T),
              ('Chỉ ở duy nhất một quận', F),
              ('Không mở thêm chi nhánh nào', F),
              ('Chỉ hoạt động ở nước ngoài', F)]),

            ('Ba phòng ban chính trực tiếp làm nên một ngôi nhà là gì?',
             [('Kinh doanh, Thiết kế, Thi công và Kỹ thuật', T),
              ('Bếp, Lễ tân, Bảo vệ', F),
              ('Marketing, Quay phim, Giao hàng', F),
              ('Không có phòng ban nào', F)]),

            ('Phòng Thi công và Kỹ thuật làm việc gì?',
             [('Kỹ sư và thợ trực tiếp xây dựng và giám sát kỹ thuật ngoài công trường', T),
              ('Vẽ bản vẽ kiến trúc', F),
              ('Gọi điện tư vấn khách', F),
              ('Tính lương nhân viên', F)]),

            ('Trụ sở chính của Vinaduy đặt ở đâu?',
             [('TP. Hồ Chí Minh (có chi nhánh tại Hà Nội)', T),
              ('Ở nước ngoài', F),
              ('Không có trụ sở', F),
              ('Chỉ có ở Hà Nội', F)]),
        ]
