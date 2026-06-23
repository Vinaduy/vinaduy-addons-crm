# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "D2 - Chuyển đổi mẫu nhà" (course_d2).

Cân đối tài chính bằng cách CHUYỂN ĐỔI MẪU NHÀ sang kiểu rẻ hơn mà vẫn đẹp,
vẫn đủ công năng — để báo giá vừa tầm tài chính của khách. Biến file PPTX
"Chuyển đổi mẫu nhà" thành 1 khóa cho NV mới: tiêu đề lớn, ẢNH so sánh trước/
sau (lớn), khung công thức / tình huống / câu chốt, ô ÁP DỤNG NGAY, và HIỆU
ỨNG động toàn khóa (fade-up, ảnh phóng khi rê chuột, badge "giảm %" nảy).

Helper khung tái dùng từ seed_kh_tiem_nang + _chot từ seed_khong_tuoi.
Idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_D2_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.d2_chuyen_doi_seed_version'
_IMG = '/vd_elearning/static/src/img/chuyendoimaunha/'

# HIỆU ỨNG động cho toàn khóa (scope trong .vd-d2-fx). vd_body sanitize=False
# nên <style> được giữ nguyên.
_FX = (
    '<style>'
    '@keyframes vdD2Up{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}'
    '@keyframes vdD2Pop{0%{opacity:0;transform:scale(.6)}60%{transform:scale(1.12)}100%{opacity:1;transform:scale(1)}}'
    '@keyframes vdD2Shine{0%{transform:translateX(-130%) skewX(-18deg)}55%,100%{transform:translateX(340%) skewX(-18deg)}}'
    '.vd-d2-fx h2,.vd-d2-fx h3,.vd-d2-fx table,.vd-d2-fx figure,.vd-d2-fx ul,.vd-d2-fx ol,'
    '.vd-d2-fx > p,.vd-d2-fx > div{animation:vdD2Up .6s ease both}'
    '.vd-d2-fx figure img{transition:transform .35s ease,box-shadow .35s ease}'
    '.vd-d2-fx figure img:hover{transform:scale(1.04) translateY(-5px);box-shadow:0 16px 38px rgba(0,0,0,.28)}'
    '.vd-d2-badge{display:inline-block;animation:vdD2Pop .8s ease both}'
    '</style>'
)


def _fig(name, cap='', h=400):
    """Ảnh LỚN (contain - không cắt mất phần mái, vì khóa so sánh kiểu mái)."""
    c = ''
    if cap:
        c = ('<figcaption style="font-size:14px;color:#475569;text-align:center;'
             'margin-top:8px;font-weight:700;">%s</figcaption>') % cap
    return (
        '<figure style="margin:0;flex:1 1 420px;min-width:320px;max-width:680px;">'
        '<img src="%s%s" style="width:100%%;height:%dpx;object-fit:contain;'
        'background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:8px;'
        'box-shadow:0 8px 24px rgba(32,36,58,.18);"/>%s</figure>'
    ) % (_IMG, name, h, c)


def _figwide(name, cap='', h=460):
    c = ''
    if cap:
        c = ('<figcaption style="font-size:14px;color:#475569;text-align:center;'
             'margin-top:10px;font-weight:700;">%s</figcaption>') % cap
    return (
        '<figure style="margin:18px 0;">'
        '<img src="%s%s" style="width:100%%;max-height:%dpx;object-fit:contain;'
        'background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:10px;'
        'box-shadow:0 8px 24px rgba(32,36,58,.18);"/>%s</figure>'
    ) % (_IMG, name, h, c)


def _ba(before_img, before_cap, after_img, after_cap, percent):
    """Khối so sánh TRƯỚC -> SAU + badge 'giảm %' nảy ở giữa."""
    arrow = (
        '<div style="flex:0 0 auto;align-self:center;text-align:center;">'
        '<div class="vd-d2-badge" style="background:linear-gradient(135deg,#16a34a,#15803d);'
        'color:#fff;font-weight:900;font-size:18px;border-radius:14px;padding:10px 16px;'
        'box-shadow:0 8px 20px rgba(22,163,74,.4);white-space:nowrap;">%s</div>'
        '<div style="font-size:30px;color:#16a34a;font-weight:900;margin-top:4px;">&rarr;</div>'
        '</div>'
    ) % percent
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:16px;align-items:stretch;'
        'justify-content:center;margin:18px 0;">'
        + _fig(before_img, before_cap, 360) + arrow + _fig(after_img, after_cap, 360)
        + '</div>'
    )


def _gallery(*figs):
    return ('<div style="display:flex;flex-wrap:wrap;gap:16px;margin:18px 0;'
            'justify-content:center;">%s</div>') % ''.join(figs)


def _hero(title_small, title_big, sub):
    return (
        '<div style="position:relative;overflow:hidden;'
        'background:linear-gradient(135deg,#f5523c 0%%,#e8401f 100%%);'
        'border-radius:18px;padding:32px 26px;margin:4px 0 26px;text-align:center;'
        'box-shadow:0 12px 30px rgba(232,64,31,.34);">'
        '<div style="position:absolute;top:0;bottom:0;left:0;width:42%%;'
        'background:linear-gradient(100deg,transparent,rgba(255,255,255,.45),transparent);'
        'animation:vdD2Shine 3.6s ease-in-out infinite;"></div>'
        '<div style="color:#ffe6df;font-size:15px;font-weight:800;letter-spacing:3px;'
        'text-transform:uppercase;margin-bottom:6px;position:relative;">%s</div>'
        '<div style="color:#fff;font-size:42px;font-weight:900;line-height:1.08;'
        'letter-spacing:1px;text-shadow:0 2px 6px rgba(0,0,0,.2);position:relative;">%s</div>'
        '<div style="color:#fff4f0;font-size:16px;font-weight:600;margin-top:12px;'
        'position:relative;">%s</div></div>'
    ) % (title_small, title_big, sub)


class SlideChannelSeedD2(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_d2_chuyen_doi(self):
        ch = self.env.ref('vd_elearning.course_d2', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _D2_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_d2_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': '%s<div class="vd-d2-fx" style="%s">%s</div>' % (_FX, _WRAP, merged),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_d2_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _D2_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (6 phần)
    # ==================================================================
    def _vd_d2_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#b91c1c;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('Mở đầu', self._d2_p1(h2, h3, lead)),
            ('Cách 1 - Mái Nhật/Thái sang Vuông hiện đại', self._d2_p2(h2, h3, lead)),
            ('Cách 2 - Mái Thái sang Giả mái Thái', self._d2_p3(h2, h3, lead)),
            ('Cách 3 - Mái ngói sang Tôn giả ngói', self._d2_p4(h2, h3, lead)),
            ('Cách 4 - Bỏ mái bê tông', self._d2_p5(h2, h3, lead)),
            ('Cách 5 - Mái bằng sang lợp tôn + Chốt', self._d2_p6(h2, h3, lead)),
        ]

    def _d2_p1(self, h2, h3, lead):
        return (
            _hero('Cân đối tài chính &mdash; Nâng cao', 'CHUYỂN ĐỔI MẪU NHÀ',
                  'Cách 1: Khi tài chính khách có hạn &mdash; đổi sang mẫu nhà / kiểu mái '
                  'RẺ HƠN mà vẫn đẹp, vẫn đủ công năng để khách chốt')

            + '<p style="' + lead + '">Rất nhiều khách <b>thích mẫu nhà đẹp, mái Thái, mái '
            'Nhật</b> nhưng <b>tài chính lại có hạn</b>. Nếu cứ báo giá theo mẫu khách thích '
            'thì <b>vượt ngân sách</b> &rArr; khách phân vân, do dự rồi bỏ đi. Nhiệm vụ của '
            'nhân viên là <b>cân đối</b>: đưa ra mẫu nhà phù hợp túi tiền mà khách vẫn thấy '
            'đẹp, hợp lý &rArr; khách yên tâm chốt.</p>'

            + _box('#2563eb', '#eff6ff', '&#9878;&#65039;', 'Nguyên tắc gốc: cân đối DIỆN TÍCH - TÀI CHÍNH',
                   '<ul style="margin:0;">'
                   '<li>Khi tư vấn, <b>luôn hỏi tầm tài chính</b> của khách trước.</li>'
                   '<li>Từ tài chính &rArr; cân đối <b>diện tích</b> và <b>kiểu mẫu nhà</b> cho phù hợp.</li>'
                   '<li>Có thể tư vấn thêm <b>làm sân sau</b> để giảm diện tích sàn.</li>'
                   '</ul>')

            + _gallery(_fig('intro_can.png',
                            'Cân đối: một bên là TÀI CHÍNH của khách, một bên là MẪU NHÀ / '
                            'diện tích &mdash; phải cân cho khớp.', 300))

            + _formula(
                'Tài chính có hạn &rArr; <b>KHÔNG ép khách bỏ cuộc</b>, mà '
                '<span style="color:#dc2626;">CHUYỂN ĐỔI MẪU NHÀ</span> sang kiểu rẻ hơn: '
                'đổi kiểu mái, giả mái Thái, tôn giả ngói, bỏ mái bê tông, lợp tôn.'
            )

            + '<h2 style="' + h2 + '">5 CÁCH CHUYỂN ĐỔI MẪU NHÀ (phải thuộc)</h2>'
            '<table><thead><tr><th style="width:60px;">#</th><th>Chuyển đổi</th>'
            '<th style="width:110px;text-align:center;">Tiết kiệm</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">1</td>'
            '<td>Mái Nhật / Thái &rarr; <b>Vuông hiện đại</b></td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">~28%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">2</td>'
            '<td>Mái Thái thật &rarr; <b>Giả mái Thái</b></td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">20-25%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">3</td>'
            '<td>Mái ngói &rarr; <b>Tôn giả ngói</b></td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">~8%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">4</td>'
            '<td><b>Bỏ mái bê tông</b> (không đổ trần)</td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">8-10%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">5</td>'
            '<td>Mái bằng &rarr; <b>Lợp tôn + trần thạch cao</b></td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">tiết kiệm</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Mục tiêu khi tư vấn là cho khách <b>thấy phương '
                'án hợp lý để LỰA CHỌN</b>, thay vì để khách <b>phân vân</b> giữa "làm hay '
                'không làm". Người tư vấn giỏi là người giúp khách quyết định, không để khách '
                'tự rối.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Học thuộc <b>5 cách chuyển đổi + mức tiết kiệm</b>. '
                'Khi khách kêu "đắt quá / vượt ngân sách", phải bật ra ngay được 1-2 phương án '
                'chuyển đổi mẫu nhà phù hợp.</p>'
            )
        )

    def _d2_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 1 &mdash; Mái Nhật / Thái &rarr; Nhà VUÔNG HIỆN ĐẠI '
            '<span class="vd-d2-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm ~28%</span></h2>'

            '<p style="' + lead + '">Nhà <b>mái ngói đổ trần</b> (mái Nhật, mái Thái) rất đẹp '
            'nhưng <b>tốn chi phí</b>: phần mái dốc, đổ trần, lợp ngói đều đắt. Đổi sang nhà '
            '<b>vuông hiện đại</b> (mái bằng) thì <b>giảm khoảng 28%</b> chi phí mà vẫn đẹp, '
            'hiện đại, gọn gàng.</p>'

            + _ba('c1_maingoi.jpg', 'Nhà mái ngói đổ trần (mái Nhật/Thái) - đẹp nhưng tốn tiền',
                  'c1_vuong.jpg', 'Nhà vuông hiện đại (mái bằng) - rẻ hơn ~28%, vẫn đẹp',
                  'GIẢM ~28%')

            + _proof(
                '<p style="margin-bottom:0;">Mái Nhật / Thái phải làm <b>hệ kèo, mái dốc, đổ '
                'trần, lợp ngói</b> &mdash; nhiều hạng mục, nhiều vật tư, nhiều nhân công. Nhà '
                'vuông hiện đại chỉ <b>mái bằng phẳng</b> nên bớt được rất nhiều phần đó '
                '&rArr; rẻ hơn rõ rệt.</p>'
            )

            + _situation(
                '<p style="margin-bottom:0;">Khách thích mái Thái nhưng tài chính chưa đủ: tư '
                'vấn <b>làm nhà vuông hiện đại trước</b>, khi nào có điều kiện thì <b>làm thêm '
                'mái Thái / mái Nhật sau</b> đều được. Như vậy khách vào ở được ngay, đúng '
                'tầm tiền, sau này nâng cấp vẫn kịp.</p>'
            )

            + _chot(
                '"Trước mắt mình làm nhà vuông hiện đại cho đúng tầm tài chính, vừa đẹp vừa '
                'gọn anh ạ. Sau này có điều kiện, mình lợp thêm mái Thái / mái Nhật lên cũng '
                'được, không vướng gì cả."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Khi khách thích mái Thái mà ngân sách thiếu, đề '
                'xuất ngay phương án <b>vuông hiện đại trước - mái Thái sau</b>, kèm con số '
                '<b>giảm ~28%</b> để khách thấy rõ lợi ích.</p>'
            )
        )

    def _d2_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 2 &mdash; Mái Thái thật &rarr; GIẢ MÁI THÁI '
            '<span class="vd-d2-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 20-25%</span></h2>'

            '<p style="' + lead + '">Với <b>nhà ống</b>, thay vì làm <b>mái Thái thật</b> '
            '(tốn kém), ta làm <b>mặt tiền GIẢ mái Thái</b>: chỉ dựng phần mái Thái ở mặt '
            'tiền cho đẹp, phần sau để mái bằng. Nhìn từ ngoài vẫn ra dáng mái Thái mà chi '
            'phí giảm <b>20-25%</b>.</p>'

            + _ba('c2_maithai.jpg', 'Nhà ống mái Thái thật (lợp ngói toàn bộ) - tốn kém',
                  'c2_gia.jpg', 'Nhà ống GIẢ mái Thái (chỉ mặt tiền) - giảm 20-25%',
                  'GIẢM 20-25%')

            + _box('#16a34a', '#f0fdf4', '&#128176;', 'Chi phí mặt tiền giả mái Thái',
                   '<p style="margin-bottom:0;">Chỉ từ <b>30.000.000đ &ndash; 40.000.000đ</b> '
                   '&mdash; <b>giảm đi rất nhiều</b> so với thi công mái Thái thật cho cả căn.</p>')

            + '<h2 style="' + h2 + '">Ưu điểm để thuyết phục khách chọn giả mái Thái</h2>'
            '<table><thead><tr><th>Ưu điểm</th><th>Diễn giải</th></tr></thead><tbody>'
            '<tr><td><b>Chi phí giảm</b></td><td>Giảm khoảng <b>20-25%</b> so với mái Thái thật.</td></tr>'
            '<tr><td><b>Tiết kiệm</b></td><td>Phù hợp tài chính, không phải vay thêm.</td></tr>'
            '<tr><td><b>Đẹp</b></td><td>Nhìn mặt tiền vẫn ra dáng mái Thái sang trọng.</td></tr>'
            '<tr><td><b>Ít phát sinh</b></td><td>Không bị phát sinh nhiều so với tài chính khách.</td></tr>'
            '</tbody></table>'

            + _mistake(
                '<p style="margin-bottom:0;">Đừng để khách <b>tự phân vân</b> giữa "mái Thái '
                'thật" và "giả mái Thái". Phải <b>tư vấn rõ ưu điểm</b> của giả mái Thái để '
                'khách <b>lựa chọn</b>, chứ không bỏ mặc khách tự cân nhắc rồi rối.</p>'
            )

            + _chot(
                '"Mặt tiền giả mái Thái chỉ khoảng 30-40 triệu thôi anh, nhìn vẫn ra dáng mái '
                'Thái mà tiết kiệm 20-25%, lại ít phát sinh. Em thấy phương án này hợp tài '
                'chính của mình nhất."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nhớ con số <b>30-40 triệu</b> cho mặt tiền giả '
                'mái Thái và mức <b>giảm 20-25%</b>. Tư vấn theo hướng ƯU ĐIỂM để khách chọn '
                'ngay, không phân vân.</p>'
            )
        )

    def _d2_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 3 &mdash; Mái ngói &rarr; MÁI TÔN GIẢ NGÓI '
            '<span class="vd-d2-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm ~8%</span></h2>'

            '<p style="' + lead + '">Thay vì lợp <b>mái ngói</b>, ta lợp <b>mái tôn giả ngói</b> '
            '(tấm tôn dập sóng giống viên ngói). Nhìn xa <b>gần như không phân biệt được</b> '
            'với ngói thật, mà chi phí <b>giảm khoảng 8%</b>, thi công nhanh hơn.</p>'

            + _ba('c3_ngoi.jpg', 'Mái ngói thật - đẹp nhưng nặng, lâu, tốn hơn',
                  'c3_ton.jpg', 'Mái tôn giả ngói - nhẹ, nhanh, rẻ hơn ~8%',
                  'GIẢM ~8%')

            + '<h2 style="' + h2 + '">Ưu điểm nổi bật của tôn giả ngói</h2>'
            '<table><thead><tr><th>Tiêu chí</th><th>Tôn giả ngói</th></tr></thead><tbody>'
            '<tr><td><b>Chi phí</b></td><td>Hợp lý, <b>rẻ hơn ~8%</b> so với mái ngói.</td></tr>'
            '<tr><td><b>Độ bền</b></td><td>Bền, chắc chắn.</td></tr>'
            '<tr><td><b>Thi công</b></td><td><b>Nhanh</b>, không bị phát sinh nhiều chi phí.</td></tr>'
            '<tr><td><b>Thẩm mỹ</b></td><td>Đẹp <b>không khác gì mái ngói</b>, nhìn xa không phân biệt được.</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Khách hay sợ "tôn thì xấu". Nhưng tôn <b>giả '
                'ngói</b> được dập sóng và phủ màu y như ngói &mdash; đứng dưới đất nhìn lên '
                '<b>không thể phân biệt</b> với ngói thật. Cái khách được là: <b>rẻ hơn, nhẹ '
                'hơn, nhanh hơn</b>.</p>'
            )

            + _chot(
                '"Tôn giả ngói nhìn xa y như ngói thật anh ạ, mà thi công nhanh, bền, rẻ hơn '
                'khoảng 8% lại ít phát sinh. Em tư vấn mình dùng tôn giả ngói cho hợp lý."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Tập nói <b>truyền cảm, chắc chắn</b> về tôn giả '
                'ngói (đẹp - bền - nhanh - rẻ ~8%) để khách <b>chọn luôn</b>, tránh để khách '
                'phân vân "ngói hay tôn".</p>'
            )
        )

    def _d2_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 4 &mdash; BỎ PHẦN MÁI BÊ TÔNG (không đổ trần) '
            '<span class="vd-d2-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 8-10%</span></h2>'

            '<p style="' + lead + '">Thay vì <b>đổ trần bê tông</b> rồi mới lợp mái, ta '
            '<b>bỏ phần mái bê tông</b>: xây tường xong lợp mái ngói (hoặc mái tôn) rồi '
            '<b>bắn trần thạch cao</b> để trang trí và che trần. Giảm <b>8-10%</b> chi phí.</p>'

            + _figwide('c4_bomai.jpg',
                       'Mặt cắt: xây tường xong lợp mái + trần thạch cao bên dưới, '
                       'KHÔNG đổ trần bê tông - tiết kiệm 8-10%.', 420)

            + '<h2 style="' + h2 + '">Hai phương án bỏ mái bê tông</h2>'
            '<table><thead><tr><th style="width:50%;">Phương án</th><th>Cách làm</th></tr></thead><tbody>'
            '<tr><td><b>Lợp mái ngói + trần thạch cao</b></td>'
            '<td>Xây tường xong &rarr; lợp mái ngói &rarr; bắn trần thạch cao <b>trang trí và che trần</b>.</td></tr>'
            '<tr><td><b>Lợp mái tôn + trần thạch cao</b></td>'
            '<td>Xây tường xong &rarr; lợp mái tôn &rarr; bắn trần thạch cao <b>chống nóng</b>.</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Tư vấn phải <b>chân thật</b> và giúp khách <b>dễ '
                'hình dung</b>: không đổ trần bê tông thì tiết kiệm 8-10%, vẫn có trần thạch '
                'cao đẹp và chống nóng. Cho khách thấy rõ <b>ưu điểm</b> để chọn luôn, không '
                'phân vân.</p>'
            )

            + _chot(
                '"Phần này mình không cần đổ trần bê tông đâu anh. Lợp mái xong bắn trần thạch '
                'cao là vừa đẹp, vừa chống nóng, lại tiết kiệm được 8-10% chi phí cho mình."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nhớ: bỏ mái bê tông = <b>lợp mái + trần thạch '
                'cao</b>, giảm <b>8-10%</b>. Giải thích chân thật, dễ hiểu để khách quyết định.</p>'
            )
        )

    def _d2_p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 5 &mdash; Mái bằng &rarr; LỢP TÔN + TRẦN THẠCH CAO</h2>'

            '<p style="' + lead + '">Nếu <b>tài chính khách không đủ</b> để đổ mái bê tông, '
            'tư vấn khách <b>đổi từ bê tông mái sang lợp tôn</b> + trần thạch cao. Vừa che '
            'mưa nắng, vừa chống nóng, mà chi phí nhẹ hơn nhiều.</p>'

            + _ba('c5_maibang.jpg', 'Nhà mái bằng (đổ bê tông mái) - tốn hơn',
                  'c5_ton.jpg', 'Đổi sang lợp tôn phần mái + trần thạch - nhẹ chi phí',
                  'TIẾT KIỆM')

            + _box('#2563eb', '#eff6ff', '&#128161;', 'Khi nào dùng cách 5?',
                   '<p style="margin-bottom:0;">Khi <b>tài chính của khách không đủ</b> để làm '
                   'mái bê tông. Giải pháp: <b>mái tôn + trần thạch cao</b> &mdash; đủ công '
                   'năng che chắn, chống nóng, chi phí nhẹ.</p>')

            + '<h2 style="' + h2 + '">&#127942; TỔNG KẾT 5 CÁCH (phải thuộc lòng)</h2>'
            '<table><thead><tr><th>Cách chuyển đổi</th><th style="width:120px;text-align:center;">Tiết kiệm</th></tr></thead><tbody>'
            '<tr><td>1. Mái Nhật/Thái &rarr; Vuông hiện đại</td><td style="text-align:center;font-weight:900;color:#16a34a;">~28%</td></tr>'
            '<tr><td>2. Mái Thái thật &rarr; Giả mái Thái</td><td style="text-align:center;font-weight:900;color:#16a34a;">20-25%</td></tr>'
            '<tr><td>3. Mái ngói &rarr; Tôn giả ngói</td><td style="text-align:center;font-weight:900;color:#16a34a;">~8%</td></tr>'
            '<tr><td>4. Bỏ mái bê tông (không đổ trần)</td><td style="text-align:center;font-weight:900;color:#16a34a;">8-10%</td></tr>'
            '<tr><td>5. Mái bằng &rarr; Lợp tôn + trần thạch</td><td style="text-align:center;font-weight:900;color:#16a34a;">tiết kiệm</td></tr>'
            '</tbody></table>'

            + _formula(
                'Khách thích mẫu đẹp mà tài chính có hạn &rArr; <b>KHÔNG để khách bỏ đi</b>: '
                'CHUYỂN ĐỔI sang mẫu rẻ hơn vẫn đẹp, đưa <b>con số tiết kiệm</b> + <b>ưu điểm</b> '
                'rõ ràng để khách CHỌN, không phân vân.'
            )

            + _apply(
                '<p>Bảng tự kiểm khi khách kêu mẫu nhà "đắt / vượt ngân sách" (Có/Không):</p>'
                '<ol>'
                '<li>Đã hỏi rõ <b>tầm tài chính</b> của khách chưa?</li>'
                '<li>Đã chọn được <b>cách chuyển đổi mẫu nhà</b> phù hợp (1 trong 5) chưa?</li>'
                '<li>Đã đưa <b>con số tiết kiệm</b> cụ thể (28% / 20-25% / 8% / 8-10%) chưa?</li>'
                '<li>Đã nêu <b>ưu điểm</b> để khách thấy hợp lý mà CHỌN chưa?</li>'
                '<li>Có đang giúp khách <b>quyết định</b> thay vì để khách phân vân không?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; quay lại làm cho đủ '
                'trước khi báo giá.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM
    # ==================================================================
    def _vd_d2_questions(self):
        T, F = True, False
        return [
            ('Mục đích của việc "chuyển đổi mẫu nhà" khi cân đối tài chính là gì?',
             [('Đổi sang mẫu nhà rẻ hơn nhưng vẫn đẹp, đủ công năng để khách chốt được', T),
              ('Ép khách làm đúng mẫu đắt nhất', F),
              ('Bỏ qua khách không đủ tiền', F),
              ('Giảm chất lượng vật tư để rẻ', F)]),

            ('Trước khi tư vấn cân đối mẫu nhà, việc đầu tiên phải làm là gì?',
             [('Hỏi tầm tài chính của khách', T),
              ('Báo giá mẫu đắt nhất trước', F),
              ('Bắt khách chọn mái Thái', F),
              ('Yêu cầu khách đặt cọc ngay', F)]),

            ('Có mấy cách chuyển đổi mẫu nhà để cân đối tài chính trong khóa này?',
             [('5 cách', T), ('2 cách', F), ('3 cách', F), ('8 cách', F)]),

            ('Cách 1: chuyển từ nhà mái Nhật/Thái sang kiểu nào và giảm bao nhiêu?',
             [('Sang nhà vuông hiện đại (mái bằng), giảm khoảng 28%', T),
              ('Sang nhà mái ngói, giảm 50%', F),
              ('Sang nhà giả mái Thái, giảm 8%', F),
              ('Sang nhà cấp 4, giảm 28%', F)]),

            ('Vì sao nhà mái Nhật/Thái đắt hơn nhà vuông hiện đại?',
             [('Phải làm hệ kèo, mái dốc, đổ trần, lợp ngói - nhiều hạng mục, vật tư, nhân công', T),
              ('Vì dùng gạch đắt hơn', F),
              ('Vì diện tích lớn gấp đôi', F),
              ('Vì phải xin phép xây dựng riêng', F)]),

            ('Khi khách thích mái Thái nhưng chưa đủ tiền, cách tư vấn đúng là gì?',
             [('Làm nhà vuông hiện đại trước, khi có điều kiện làm thêm mái Thái/Nhật sau', T),
              ('Bắt khách vay tiền làm mái Thái ngay', F),
              ('Từ chối khách', F),
              ('Làm mái Thái nhưng giảm vật tư cho rẻ', F)]),

            ('Cách 2: nhà ống mái Thái thật nên chuyển sang gì và giảm bao nhiêu?',
             [('Giả mái Thái (chỉ làm mặt tiền), giảm 20-25%', T),
              ('Mái ngói thật, giảm 28%', F),
              ('Mái tôn lạnh, giảm 50%', F),
              ('Bỏ mái hoàn toàn, giảm 40%', F)]),

            ('Chi phí làm mặt tiền giả mái Thái khoảng bao nhiêu?',
             [('Chỉ từ 30.000.000đ đến 40.000.000đ', T),
              ('Từ 100 đến 150 triệu', F),
              ('Từ 5 đến 10 triệu', F),
              ('Bằng đúng mái Thái thật', F)]),

            ('"Giả mái Thái" nghĩa là làm như thế nào?',
             [('Chỉ dựng phần mái Thái ở mặt tiền cho đẹp, phần sau để mái bằng', T),
              ('Làm mái Thái bằng nhựa giả', F),
              ('Vẽ hình mái Thái lên tường', F),
              ('Làm mái Thái nhưng nhỏ lại một nửa', F)]),

            ('Cách 3: chuyển từ mái ngói sang loại mái nào và giảm bao nhiêu?',
             [('Mái tôn giả ngói, giảm khoảng 8%', T),
              ('Mái bê tông, giảm 28%', F),
              ('Mái kính, giảm 20%', F),
              ('Mái lá, giảm 30%', F)]),

            ('Ưu điểm thẩm mỹ của tôn giả ngói là gì?',
             [('Đẹp không khác gì mái ngói, nhìn xa không phân biệt được', T),
              ('Đẹp hơn hẳn nhưng đắt hơn', F),
              ('Xấu hơn nhưng rẻ', F),
              ('Trong suốt cho sáng nhà', F)]),

            ('Các ưu điểm của tôn giả ngói gồm những gì?',
             [('Chi phí hợp lý, bền, thi công nhanh, ít phát sinh, đẹp như ngói', T),
              ('Chỉ rẻ nhưng nhanh hỏng', F),
              ('Chỉ đẹp nhưng rất đắt', F),
              ('Nặng hơn ngói, lâu hơn', F)]),

            ('Cách 4: "bỏ phần mái bê tông" được làm như thế nào?',
             [('Xây tường xong lợp mái ngói/tôn rồi bắn trần thạch cao, không đổ trần bê tông', T),
              ('Bỏ luôn mái, để trống nóc nhà', F),
              ('Đổ trần bê tông dày hơn', F),
              ('Lợp 2 lớp mái ngói', F)]),

            ('Bỏ phần mái bê tông (không đổ trần) giảm được bao nhiêu chi phí?',
             [('Khoảng 8-10%', T), ('Khoảng 28%', F), ('Khoảng 50%', F), ('Không giảm gì', F)]),

            ('Lợp mái tôn rồi bắn trần thạch cao có tác dụng gì?',
             [('Chống nóng', T),
              ('Tăng tải trọng cho móng', F),
              ('Làm nhà tối hơn', F),
              ('Thay thế cho tường', F)]),

            ('Cách 5: khi tài chính khách KHÔNG đủ làm mái bê tông thì tư vấn gì?',
             [('Đổi từ bê tông mái sang lợp tôn + trần thạch cao', T),
              ('Bắt khách vay ngân hàng', F),
              ('Bỏ luôn tầng trên', F),
              ('Làm mái bê tông mỏng hơn cho rẻ', F)]),

            ('Cách chuyển đổi mẫu nhà nào tiết kiệm NHIỀU nhất?',
             [('Mái Nhật/Thái sang vuông hiện đại (~28%)', T),
              ('Mái ngói sang tôn giả ngói (~8%)', F),
              ('Bỏ mái bê tông (8-10%)', F),
              ('Giả mái Thái (20-25%)', F)]),

            ('Thái độ tư vấn đúng để khách quyết định nhanh là gì?',
             [('Đưa phương án hợp lý + ưu điểm rõ để khách LỰA CHỌN, không để khách phân vân', T),
              ('Liệt kê thật nhiều phương án rồi để khách tự nghĩ', F),
              ('Chỉ nói giá, không nói ưu điểm', F),
              ('Ép khách chọn ngay không giải thích', F)]),

            ('Nguyên tắc gốc khi khách thích mẫu đẹp mà tài chính có hạn là gì?',
             [('Không để khách bỏ đi - chuyển đổi sang mẫu rẻ hơn vẫn đẹp, kèm số tiết kiệm và ưu điểm', T),
              ('Giảm vật tư để giữ nguyên mẫu đắt', F),
              ('Báo giá thật cao cho khách tự rút', F),
              ('Khuyên khách đừng xây nữa', F)]),

            ('Ngoài đổi kiểu mái, có thể tư vấn thêm cách nào để cân đối diện tích/tài chính?',
             [('Tư vấn thiết kế làm sân sau để giảm diện tích sàn', T),
              ('Tăng số tầng lên cho hoành tráng', F),
              ('Mở rộng diện tích nhà tối đa', F),
              ('Đổ thêm nhiều trần bê tông', F)]),
        ]
