# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "D3 - Chuyển đổi loại móng" (course_d3).

Cân đối tài chính bằng cách GIẢM KẾT CẤU MÓNG: chuyển sang loại móng / loại cọc
rẻ hơn KHI nền đất và tải trọng cho phép, để giảm chi phí mà vẫn AN TOÀN.

Đây là khóa liên quan KẾT CẤU nên nội dung được viết chắc về kỹ thuật xây dựng:
- Nêu rõ điều kiện áp dụng từng cách (loại nền đất + số tầng/tải trọng).
- Chỉnh lại vài chỗ tài liệu gốc ghi nhầm (trang 6 viết "nguyên lý móng băng"
  trong khi đang nói móng đơn -> sửa thành móng đơn).
- Bổ sung CẢNH BÁO an toàn: chỉ hạ cấp móng khi có KHẢO SÁT ĐỊA CHẤT + tính tải
  trọng + kỹ thuật/cấp trên duyệt; cọc tre/cừ tràm chỉ dùng nền đất LUÔN ngập
  nước (dưới mực nước ngầm) nếu không sẽ mục -> lún.

Tái dùng phong cách D2: hero lớn, ảnh so sánh LỚN, hiệu ứng động toàn khóa,
khung công thức/tình huống/chứng minh/cảnh báo/câu chốt + ô ÁP DỤNG NGAY.
Idempotent theo PHIÊN BẢN. Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_D3_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.d3_chuyen_doi_mong_seed_version'
_IMG = '/vd_elearning/static/src/img/chuyendoimong/'

_FX = (
    '<style>'
    '@keyframes vdD3Up{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}'
    '@keyframes vdD3Pop{0%{opacity:0;transform:scale(.6)}60%{transform:scale(1.12)}100%{opacity:1;transform:scale(1)}}'
    '@keyframes vdD3Shine{0%{transform:translateX(-130%) skewX(-18deg)}55%,100%{transform:translateX(340%) skewX(-18deg)}}'
    '.vd-d3-fx h2,.vd-d3-fx h3,.vd-d3-fx table,.vd-d3-fx figure,.vd-d3-fx ul,.vd-d3-fx ol,'
    '.vd-d3-fx > p,.vd-d3-fx > div{animation:vdD3Up .6s ease both}'
    '.vd-d3-fx figure img{transition:transform .35s ease,box-shadow .35s ease}'
    '.vd-d3-fx figure img:hover{transform:scale(1.03) translateY(-5px);box-shadow:0 16px 38px rgba(0,0,0,.28)}'
    '.vd-d3-badge{display:inline-block;animation:vdD3Pop .8s ease both}'
    '</style>'
)


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


def _hero(title_small, title_big, sub):
    return (
        '<div style="position:relative;overflow:hidden;'
        'background:linear-gradient(135deg,#f5523c 0%%,#e8401f 100%%);'
        'border-radius:18px;padding:32px 26px;margin:4px 0 26px;text-align:center;'
        'box-shadow:0 12px 30px rgba(232,64,31,.34);">'
        '<div style="position:absolute;top:0;bottom:0;left:0;width:42%%;'
        'background:linear-gradient(100deg,transparent,rgba(255,255,255,.45),transparent);'
        'animation:vdD3Shine 3.6s ease-in-out infinite;"></div>'
        '<div style="color:#ffe6df;font-size:15px;font-weight:800;letter-spacing:3px;'
        'text-transform:uppercase;margin-bottom:6px;position:relative;">%s</div>'
        '<div style="color:#fff;font-size:42px;font-weight:900;line-height:1.08;'
        'letter-spacing:1px;text-shadow:0 2px 6px rgba(0,0,0,.2);position:relative;">%s</div>'
        '<div style="color:#fff4f0;font-size:16px;font-weight:600;margin-top:12px;'
        'position:relative;">%s</div></div>'
    ) % (title_small, title_big, sub)


def _warn(inner):
    """Khung CẢNH BÁO AN TOÀN (đỏ) - bắt buộc khảo sát/duyệt trước khi hạ móng."""
    return _box('#dc2626', '#fef2f2', '&#9888;&#65039;', 'Cảnh báo an toàn kết cấu', inner)


class SlideChannelSeedD3(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_d3_chuyen_doi_mong(self):
        ch = self.env.ref('vd_elearning.course_d3', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _D3_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_d3_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': '%s<div class="vd-d3-fx" style="%s">%s</div>' % (_FX, _WRAP, merged),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_d3_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _D3_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG (6 phần)
    # ==================================================================
    def _vd_d3_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#b91c1c;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('Mở đầu', self._d3_p1(h2, h3, lead)),
            ('Hiểu 3 loại móng', self._d3_p2(h2, h3, lead)),
            ('Cách 1 - Móng cọc sang Móng băng', self._d3_p3(h2, h3, lead)),
            ('Cách 2 - Móng băng sang Móng đơn', self._d3_p4(h2, h3, lead)),
            ('Cách 3 - Móng cọc sang Móng đơn', self._d3_p5(h2, h3, lead)),
            ('Cách 4 - Cọc bê tông sang Cọc tre/Cừ tràm + Chốt', self._d3_p6(h2, h3, lead)),
        ]

    def _d3_p1(self, h2, h3, lead):
        return (
            _hero('Cân đối tài chính &mdash; Nâng cao', 'CHUYỂN ĐỔI LOẠI MÓNG',
                  'Cách 4: Giảm kết cấu móng để giảm chi phí &mdash; nhưng CHỈ khi nền đất '
                  'và tải trọng cho phép, và phải AN TOÀN')

            + '<p style="' + lead + '">Phần <b>móng</b> chiếm một khoản chi phí lớn. Khi khách '
            '<b>vượt ngân sách</b>, một cách cân đối là <b>chuyển sang loại móng rẻ hơn</b> '
            '(hoặc đổi loại cọc) &mdash; <b>nhưng chỉ khi nền đất và tải trọng công trình cho '
            'phép</b>. Móng là phần <b>quan trọng nhất</b> giữ cho nhà không lún, nứt, nghiêng, '
            'nên tuyệt đối không hạ cấp móng một cách tùy tiện.</p>'

            + _warn(
                '<p style="margin:0;">Hạ cấp móng SAI &rArr; nhà <b>lún, nứt, nghiêng</b>, sửa '
                'rất khó và rất tốn kém. Mọi đề xuất chuyển đổi móng <b>BẮT BUỘC</b> phải dựa '
                'trên: (1) <b>khảo sát địa chất / nền đất thực tế</b>, (2) <b>tính tải trọng '
                'theo số tầng</b>, (3) <b>kỹ thuật và cấp trên duyệt</b>. Nhân viên chỉ tư vấn '
                'hướng đi, KHÔNG tự quyết phương án kết cấu.</p>'
            )

            + _box('#2563eb', '#eff6ff', '&#9878;&#65039;', 'Nhắc lại nguyên tắc cân đối',
                   '<p style="margin:0;">Luôn <b>hỏi tầm tài chính của khách trước</b>, rồi cân '
                   'đối <b>diện tích, mẫu nhà, kết cấu móng</b> cho phù hợp túi tiền mà vẫn đủ '
                   'an toàn và công năng.</p>')

            + _formula(
                'Chi phí móng phụ thuộc <b>LOẠI MÓNG</b> và <b>LOẠI CỌC</b>. '
                'Móng cọc &gt; Móng băng &gt; Móng đơn về chi phí. '
                'Cọc bê tông &gt; Cọc tre / cừ tràm.'
            )

            + '<h2 style="' + h2 + '">4 CÁCH GIẢM KẾT CẤU MÓNG (phải thuộc)</h2>'
            '<table><thead><tr><th style="width:60px;">#</th><th>Chuyển đổi</th>'
            '<th style="width:150px;text-align:center;">Tiết kiệm</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">1</td>'
            '<td>Móng cọc &rarr; <b>Móng băng</b> (+ ép cọc tre nếu đất ẩm)</td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">30-40 triệu</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">2</td>'
            '<td>Móng băng &rarr; <b>Móng đơn</b> (đất cứng / + cọc tre nếu đất ẩm)</td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">3-5%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">3</td>'
            '<td>Móng cọc &rarr; <b>Móng đơn</b> (đất cứng)</td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">30-40 tr + 3-5%</td></tr>'
            '<tr><td style="text-align:center;font-weight:900;color:#b91c1c;">4</td>'
            '<td>Cọc bê tông &rarr; <b>Cọc tre / Cừ tràm</b></td>'
            '<td style="text-align:center;font-weight:900;color:#16a34a;">40-55 triệu</td></tr>'
            '</tbody></table>'

            + _apply(
                '<p style="margin-bottom:0;">Học thuộc <b>4 cách + điều kiện nền đất + giới hạn '
                'số tầng</b> của từng cách. Khi khách vượt ngân sách phần móng, phải biết đề '
                'xuất hướng phù hợp để chuyển cho kỹ thuật kiểm tra.</p>'
            )
        )

    def _d3_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">HIỂU 3 LOẠI MÓNG (nền tảng để tư vấn đúng)</h2>'
            '<p style="' + lead + '">Muốn tư vấn chuyển đổi móng cho đúng, phải hiểu bản chất '
            'và điều kiện dùng của từng loại móng:</p>'

            '<table><thead><tr><th style="width:120px;">Loại móng</th><th>Bản chất</th>'
            '<th>Dùng khi nào</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">Móng đơn</b></td>'
            '<td>Mỗi cột có một đế móng riêng (độc lập).</td>'
            '<td><b>Nền đất tốt, cứng, liền thổ</b> + tải nhẹ &mdash; nhà <b>1 tầng, 2 tầng nhỏ</b>. '
            'Rẻ nhất.</td></tr>'
            '<tr><td><b style="color:#2563eb;">Móng băng</b></td>'
            '<td>Dải móng bê tông chạy <b>liên tục</b> dưới hàng cột / tường.</td>'
            '<td>Nền đất <b>trung bình</b>, tải vừa &mdash; phổ biến cho nhà <b>tới 3 tầng</b>. '
            'Phân bố tải đều hơn móng đơn.</td></tr>'
            '<tr><td><b style="color:#b45309;">Móng cọc</b></td>'
            '<td>Đóng/ép cọc truyền tải xuống <b>lớp đất sâu chắc</b>.</td>'
            '<td>Nền đất <b>YẾU</b> hoặc tải <b>nặng / nhà cao tầng</b>. An toàn nhất nhưng '
            '<b>đắt nhất</b>.</td></tr>'
            '</tbody></table>'

            + _box('#16a34a', '#f0fdf4', '&#127795;', 'Cọc tre / cừ tràm là GIA CỐ NỀN (không phải móng)',
                   '<p style="margin:0;">Cọc tre, cừ tràm <b>đóng dày xuống nền đất yếu</b> để '
                   '<b>làm chặt đất và tăng sức chịu tải</b> cho móng nông (móng băng / móng '
                   'đơn) bên trên. Đây là cách <b>gia cố nền</b> rẻ tiền thay cho ép cọc bê '
                   'tông.</p>')

            + _warn(
                '<p style="margin:0;">Cọc tre / cừ tràm <b>chỉ dùng cho nền đất LUÔN ngập nước</b> '
                '(nằm dưới mực nước ngầm, đất ẩm ướt quanh năm). Khi luôn ngâm nước, cọc gỗ '
                '<b>không mục</b>, bền hàng chục năm. Nếu nền <b>khô theo mùa</b> &rArr; cọc '
                '<b>mục, mất tác dụng</b> &rArr; nền lún. Vì vậy đất khô / liền thổ thì dùng '
                '<b>móng đơn</b>, KHÔNG đóng cọc tre.</p>'
            )

            + _formula(
                'Chọn móng = NỀN ĐẤT &#10133; TẢI TRỌNG (số tầng). '
                'Đất tốt + nhà thấp tầng &rArr; được dùng móng nhẹ hơn &rArr; rẻ hơn.'
            )

            + _apply(
                '<p style="margin-bottom:0;">Trước khi nghĩ tới giảm móng, luôn hỏi/nắm '
                '<b>2 thông tin</b>: (1) nền đất khu vực ra sao (cứng/liền thổ hay ẩm ướt/ao '
                'hồ), (2) nhà mấy tầng. Hai cái này quyết định được phép chuyển đổi móng hay '
                'không.</p>'
            )
        )

    def _d3_p3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 1 &mdash; Móng cọc &rarr; MÓNG BĂNG '
            '<span class="vd-d3-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 30-40 triệu</span></h2>'

            '<p style="' + lead + '">Nếu nền đất không quá yếu và nhà <b>từ 3 tầng trở xuống</b>, '
            'có thể chuyển từ <b>móng cọc</b> (đắt) sang <b>móng băng</b>. Nếu nền hơi yếu / ẩm '
            'ướt thì <b>móng băng + ép cọc tre</b> để gia cố nền. Bỏ được phần ép cọc bê tông '
            '&rArr; <b>giảm 30-40 triệu</b> tiền ép cọc.</p>'

            + _figwide('c1_coc_bang.png',
                       'Móng cọc (trái) chuyển sang Móng băng (phải) - bỏ ép cọc bê tông, '
                       'giảm 30-40 triệu.', 360)

            + _proof(
                '<p style="margin:0;">Móng cọc tốn tiền vì phải <b>mua cọc bê tông + thuê máy '
                'ép (ca máy)</b>. Móng băng là dải bê tông chạy liên tục, <b>phân bố tải đều</b>, '
                'với nền đủ tốt và nhà &le; 3 tầng thì <b>đủ khả năng chịu lực</b> &mdash; nên '
                'bỏ được phần ép cọc, tiết kiệm 30-40 triệu.</p>'
            )

            + _box('#0369a1', '#e0f2fe', '&#9989;', 'Điều kiện áp dụng',
                   '<ul style="margin:0;">'
                   '<li>Nhà <b>từ 3 tầng trở xuống</b>.</li>'
                   '<li>Nền đất đủ tốt cho móng băng; nếu <b>đất ẩm ướt</b> thì thêm <b>ép cọc tre</b> gia cố.</li>'
                   '<li>Phải được <b>kỹ thuật xác nhận tải trọng</b> móng băng chịu được.</li>'
                   '</ul>')

            + _situation(
                '<p style="margin:0;">Khi tư vấn, <b>phân tích cho khách</b> về nguyên lý thi '
                'công móng băng và việc móng băng <b>thừa sức chịu tải</b> cho nhà &le; 3 tầng '
                'trên nền đất này &mdash; để khách yên tâm chuyển đổi móng, giảm chi phí mà vẫn '
                'an toàn.</p>'
            )

            + _chot(
                '"Với nền đất nhà mình và nhà 3 tầng trở xuống, bên em làm móng băng là đủ '
                'chịu lực an toàn rồi anh ạ, không cần ép cọc bê tông &mdash; mình tiết kiệm '
                'được khoảng 30-40 triệu tiền ép cọc. Em sẽ cho kỹ thuật kiểm tra nền để chốt '
                'phương án chính xác."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nhớ: cọc &rarr; băng = <b>giảm 30-40 triệu</b>, '
                'áp dụng <b>&le; 3 tầng</b>; đất ẩm thì <b>+ cọc tre</b>. Luôn kết bằng '
                '"để kỹ thuật kiểm tra nền".</p>'
            )
        )

    def _d3_p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 2 &mdash; Móng băng &rarr; MÓNG ĐƠN '
            '<span class="vd-d3-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 3-5%</span></h2>'

            '<p style="' + lead + '">Với <b>nhà 1 tầng hoặc 2 tầng nhỏ</b> trên <b>nền đất cứng, '
            'liền thổ</b>, có thể chuyển từ <b>móng băng</b> sang <b>móng đơn</b> &mdash; giảm '
            'khoảng <b>3-5%</b> chi phí (phần móng). Nếu nền <b>ẩm ướt</b> thì <b>móng đơn + ép '
            'cọc tre</b> gia cố (cộng thêm khoảng 10-15 triệu tiền cọc tre).</p>'

            + _figwide('c2_bang_don.png',
                       'Móng băng (trái) chuyển sang Móng đơn (phải) cho nhà 1-2 tầng nhỏ trên '
                       'nền đất cứng - giảm 3-5%.', 360)

            + '<table><thead><tr><th style="width:40%;">Trường hợp nền đất</th><th>Phương án</th>'
            '<th style="width:160px;">Tiết kiệm</th></tr></thead><tbody>'
            '<tr><td><b>Đất cứng, liền thổ</b></td><td>Móng băng &rarr; <b>Móng đơn</b></td>'
            '<td>Giảm <b>3-5%</b></td></tr>'
            '<tr><td><b>Đất ẩm ướt</b></td><td>Móng băng &rarr; <b>Móng đơn + ép cọc tre</b></td>'
            '<td>Giảm 3-5% loại móng, <b>+10-15 triệu</b> tiền cọc tre</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin:0;">Móng đơn ít bê tông và thép hơn móng băng (chỉ làm đế '
                'riêng dưới từng cột thay vì dải liên tục) nên <b>rẻ hơn</b>. Với <b>tải nhẹ</b> '
                '(1-2 tầng nhỏ) trên <b>nền đất tốt</b>, móng đơn <b>đủ chịu lực</b>.</p>'
            )

            + _warn(
                '<p style="margin:0;">Chỉ áp dụng cho <b>nhà 1 tầng và 2 tầng nhỏ</b> trên nền '
                '<b>đất tốt</b>. Đất yếu mà cố làm móng đơn &rArr; <b>lún lệch, nứt</b>. Đất ẩm '
                'ướt thì bắt buộc <b>gia cố cọc tre</b>. Mọi trường hợp phải có <b>kỹ thuật '
                'duyệt</b>.</p>'
            )

            + _chot(
                '"Nhà mình 1-2 tầng, nền đất ở đây cứng và liền thổ nên bên em làm móng đơn là '
                'an toàn và tiết kiệm hơn móng băng khoảng 3-5% anh ạ. Em cho kỹ thuật kiểm tra '
                'nền rồi chốt cho mình."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nhớ: băng &rarr; đơn = <b>giảm 3-5%</b>, chỉ '
                '<b>nhà 1-2 tầng nhỏ + đất cứng</b>; đất ẩm thì <b>+ cọc tre (10-15tr)</b>.</p>'
            )
        )

    def _d3_p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 3 &mdash; Móng cọc &rarr; MÓNG ĐƠN '
            '<span class="vd-d3-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 30-40 tr + 3-5%</span></h2>'

            '<p style="' + lead + '">Trường hợp khách đang dự kiến <b>móng cọc</b> nhưng nền '
            'thực tế là <b>đất cứng, liền thổ</b> và nhà <b>nhỏ (1 tầng, 2 tầng hệ nhỏ)</b>, có '
            'thể hạ thẳng xuống <b>móng đơn</b>: vừa bỏ tiền ép cọc (<b>30-40 triệu</b>), vừa '
            'giảm <b>3-5%</b> chi phí loại móng.</p>'

            + _figwide('c3_coc_don.png',
                       'Móng cọc (trái) chuyển sang Móng đơn (phải) khi nền đất cứng, nhà nhỏ - '
                       'giảm 30-40 triệu tiền ép cọc và 3-5%.', 360)

            + _warn(
                '<p style="margin:0;font-weight:700;color:#b91c1c;">QUAN TRỌNG: <b>Nhà 3 tầng '
                'KHÔNG được tư vấn hạ xuống móng đơn.</b> Móng đơn chỉ dùng cho nhà <b>1 tầng '
                'và 2 tầng hệ nhỏ</b> trên nền đất cứng. Tải của nhà 3 tầng quá lớn so với móng '
                'đơn &rArr; nguy cơ lún, nứt.</p>'
            )

            + _proof(
                '<p style="margin:0;">Đây là cách tiết kiệm <b>mạnh nhất</b> vì cắt được cả '
                '<b>phần ép cọc bê tông</b> (30-40 triệu) lẫn <b>hạ loại móng</b> (3-5%). Nhưng '
                'đúng người đúng việc: chỉ khi <b>nền đất thật sự tốt</b> và <b>nhà nhỏ</b>.</p>'
            )

            + _situation(
                '<p style="margin:0;">Phân tích cho khách về <b>nguyên lý thi công móng đơn</b> '
                'và việc móng đơn <b>đủ tải</b> cho nhà nhỏ trên nền đất cứng &mdash; để khách '
                'hiểu vì sao không cần ép cọc, yên tâm tiết kiệm.</p>'
            )

            + _chot(
                '"Nền đất nhà mình cứng, nhà lại 1-2 tầng nên không cần ép cọc đâu anh, bên em '
                'làm móng đơn là chắc chắn rồi &mdash; tiết kiệm cho mình 30-40 triệu tiền cọc '
                'và thêm 3-5% nữa. Em cho kỹ thuật khảo sát nền để chốt ạ."'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nhớ: cọc &rarr; đơn = <b>30-40tr + 3-5%</b>, chỉ '
                '<b>1-2 tầng nhỏ + đất cứng</b>; <b>nhà 3 tầng KHÔNG được</b>.</p>'
            )
        )

    def _d3_p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">CÁCH 4 &mdash; Ép cọc bê tông &rarr; CỌC TRE / CỪ TRÀM '
            '<span class="vd-d3-badge" style="background:#dcfce7;color:#15803d;border-radius:8px;'
            'padding:2px 10px;font-size:15px;">Giảm 40-55 triệu</span></h2>'

            '<p style="' + lead + '">Khi vẫn cần <b>gia cố nền đất yếu / ẩm ướt</b> nhưng tải '
            'không lớn, có thể thay <b>cọc bê tông đúc sẵn</b> bằng <b>cọc tre</b> (hoặc <b>cừ '
            'tràm</b>). Cọc tre rẻ hơn rất nhiều và <b>không tốn ca máy ép</b>.</p>'

            + _figwide('c4_coc_tre.png',
                       'Cọc bê tông (trái) chuyển sang Cọc tre / Cừ tràm (phải) cho nền đất yếu '
                       'ngập nước - rẻ hơn rất nhiều.', 480)

            + '<table><thead><tr><th>Khoản chi phí</th><th>Cọc bê tông</th><th>Cọc tre / cừ tràm</th></tr></thead><tbody>'
            '<tr><td><b>Tiền cọc</b></td><td>Cao</td><td>Cả công trình chỉ <b>10-15 triệu</b></td></tr>'
            '<tr><td><b>Ca máy ép</b></td><td>10-15 triệu</td><td><b>0đ</b> (đóng thủ công, không cần máy)</td></tr>'
            '<tr><td><b>Tổng tiết kiệm</b></td><td colspan="2"><b>~40-55 triệu</b> (30-40tr tiền cọc + 10-15tr ca ép)</td></tr>'
            '</tbody></table>'

            + _warn(
                '<p style="margin:0;">Cọc tre / cừ tràm <b>CHỈ dùng cho nền đất luôn ngập nước</b> '
                '(dưới mực nước ngầm). Đất khô theo mùa &rArr; cọc <b>mục</b> &rArr; lún. Và chỉ '
                'cho <b>tải nhẹ</b>. Phải để <b>kỹ thuật kiểm tra nền</b> trước khi chốt.</p>'
            )

            + _proof(
                '<p style="margin:0;">Cọc bê tông tốn cả <b>tiền cọc</b> lẫn <b>ca máy ép</b>. '
                'Cọc tre đóng thủ công, không cần máy, vật tư rẻ &mdash; tổng chi phí cọc tre '
                'cho một công trình chỉ khoảng <b>10-15 triệu</b>, rẻ hơn cọc bê tông tới '
                '<b>~40 triệu</b>.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; TỔNG KẾT 4 CÁCH (thuộc lòng)</h2>'
            '<table><thead><tr><th>Chuyển đổi</th><th>Điều kiện</th><th style="width:130px;">Tiết kiệm</th></tr></thead><tbody>'
            '<tr><td>1. Cọc &rarr; Băng</td><td>Nhà &le; 3 tầng; đất ẩm thì + cọc tre</td><td>30-40 tr</td></tr>'
            '<tr><td>2. Băng &rarr; Đơn</td><td>Nhà 1-2 tầng nhỏ; đất cứng (ẩm thì + cọc tre)</td><td>3-5%</td></tr>'
            '<tr><td>3. Cọc &rarr; Đơn</td><td>Nhà 1-2 tầng nhỏ, đất cứng; <b>3 tầng KHÔNG</b></td><td>30-40 tr + 3-5%</td></tr>'
            '<tr><td>4. Cọc BT &rarr; Cọc tre/cừ tràm</td><td>Đất yếu LUÔN ngập nước, tải nhẹ</td><td>40-55 tr</td></tr>'
            '</tbody></table>'

            + _formula(
                'Giảm móng = đúng <b>NỀN ĐẤT</b> + đúng <b>SỐ TẦNG</b> + có <b>KHẢO SÁT và '
                'KỸ THUẬT DUYỆT</b>. An toàn trước, tiết kiệm sau.'
            )

            + _apply(
                '<p>Bảng tự kiểm trước khi đề xuất giảm móng cho khách (Có/Không):</p>'
                '<ol>'
                '<li>Đã nắm <b>nền đất</b> (cứng/liền thổ hay ẩm ướt/ao hồ) chưa?</li>'
                '<li>Đã biết <b>nhà mấy tầng</b> chưa? (3 tầng thì KHÔNG hạ xuống móng đơn)</li>'
                '<li>Chọn đúng <b>cách chuyển đổi</b> theo nền đất + số tầng chưa?</li>'
                '<li>Nếu dùng <b>cọc tre/cừ tràm</b>: nền có <b>luôn ngập nước</b> không?</li>'
                '<li>Đã hẹn <b>kỹ thuật khảo sát nền + duyệt</b> trước khi chốt chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; chưa được chốt phương án '
                'móng với khách.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU TRẮC NGHIỆM
    # ==================================================================
    def _vd_d3_questions(self):
        T, F = True, False
        return [
            ('Vì sao tuyệt đối không được hạ cấp móng một cách tùy tiện?',
             [('Vì móng giữ nhà không lún/nứt/nghiêng; hạ sai gây hư hỏng nặng, sửa rất tốn', T),
              ('Vì hạ móng làm nhà xấu đi', F),
              ('Vì khách không thích móng nhỏ', F),
              ('Không sao cả, cứ hạ cho rẻ', F)]),

            ('Điều kiện BẮT BUỘC trước khi đề xuất chuyển đổi móng là gì?',
             [('Khảo sát địa chất/nền đất + tính tải trọng theo số tầng + kỹ thuật/cấp trên duyệt', T),
              ('Chỉ cần khách đồng ý là làm', F),
              ('Chỉ cần nhìn bằng mắt là đủ', F),
              ('Cứ chọn loại rẻ nhất cho nhanh', F)]),

            ('Về chi phí, thứ tự từ ĐẮT đến RẺ của 3 loại móng là gì?',
             [('Móng cọc > Móng băng > Móng đơn', T),
              ('Móng đơn > Móng băng > Móng cọc', F),
              ('Móng băng > Móng cọc > Móng đơn', F),
              ('Cả ba bằng nhau', F)]),

            ('Móng ĐƠN phù hợp dùng khi nào?',
             [('Nền đất tốt, cứng, liền thổ + tải nhẹ (nhà 1 tầng, 2 tầng nhỏ)', T),
              ('Nền đất yếu, ao hồ, nhà cao tầng', F),
              ('Mọi loại nền và mọi số tầng', F),
              ('Chỉ dùng cho nhà từ 4 tầng trở lên', F)]),

            ('Móng CỌC thường dùng khi nào?',
             [('Nền đất yếu hoặc tải nặng/nhà cao tầng - truyền tải xuống lớp đất sâu chắc', T),
              ('Nền đất rất cứng và nhà 1 tầng', F),
              ('Khi muốn tiết kiệm nhất', F),
              ('Chỉ khi khách yêu cầu cho đẹp', F)]),

            ('Cọc tre / cừ tràm có vai trò gì?',
             [('Gia cố nền đất yếu (làm chặt đất, tăng sức chịu tải) cho móng nông bên trên', T),
              ('Là một loại móng cọc bê tông', F),
              ('Dùng để trang trí mặt tiền', F),
              ('Thay thế cho cột nhà', F)]),

            ('Cọc tre / cừ tràm CHỈ được dùng cho loại nền nào?',
             [('Nền đất LUÔN ngập nước (dưới mực nước ngầm, ẩm ướt quanh năm)', T),
              ('Nền đất khô ráo, liền thổ', F),
              ('Mọi loại nền đều được', F),
              ('Nền đất cát khô', F)]),

            ('Vì sao cọc tre/cừ tràm không dùng cho nền đất khô theo mùa?',
             [('Vì khi khô cọc gỗ bị mục, mất tác dụng, dẫn đến nền lún', T),
              ('Vì cọc gỗ quá đắt', F),
              ('Vì khó vận chuyển', F),
              ('Vì làm bẩn công trình', F)]),

            ('Cách 1: chuyển từ móng cọc sang móng băng tiết kiệm khoảng bao nhiêu và áp dụng cho nhà mấy tầng?',
             [('Giảm 30-40 triệu tiền ép cọc; áp dụng nhà từ 3 tầng trở xuống', T),
              ('Giảm 50%; áp dụng mọi nhà', F),
              ('Giảm 3-5%; chỉ nhà 5 tầng', F),
              ('Không tiết kiệm gì', F)]),

            ('Khi chuyển móng cọc sang móng băng mà nền đất ẩm ướt thì làm thêm gì?',
             [('Ép cọc tre để gia cố nền', T),
              ('Đổ thêm bê tông mái', F),
              ('Bỏ luôn móng', F),
              ('Tăng số tầng', F)]),

            ('Cách 2: chuyển từ móng băng sang móng đơn (đất cứng) tiết kiệm khoảng bao nhiêu?',
             [('Khoảng 3-5% chi phí phần móng', T),
              ('Khoảng 30-40 triệu', F),
              ('Khoảng 50%', F),
              ('Không giảm', F)]),

            ('Cách 2 áp dụng cho nhà mấy tầng và nền đất nào?',
             [('Nhà 1 tầng và 2 tầng nhỏ, nền đất cứng/liền thổ', T),
              ('Nhà 4-5 tầng, nền đất yếu', F),
              ('Mọi nhà, mọi nền', F),
              ('Chỉ nhà trên ao hồ', F)]),

            ('Móng băng sang móng đơn khi nền đất ẩm ướt thì thêm chi phí gì?',
             [('Thêm khoảng 10-15 triệu tiền cọc tre để gia cố', T),
              ('Thêm 100 triệu tiền cọc bê tông', F),
              ('Không thêm gì', F),
              ('Thêm tiền mái', F)]),

            ('Cách 3: chuyển móng cọc thẳng sang móng đơn (đất cứng) tiết kiệm thế nào?',
             [('Bỏ 30-40 triệu tiền ép cọc và giảm thêm 3-5% loại móng', T),
              ('Chỉ giảm 3-5%', F),
              ('Chỉ giảm 30-40 triệu, không có %', F),
              ('Đắt hơn móng cọc', F)]),

            ('Quy định QUAN TRỌNG về nhà 3 tầng khi hạ xuống móng đơn là gì?',
             [('Nhà 3 tầng KHÔNG được tư vấn hạ xuống móng đơn', T),
              ('Nhà 3 tầng bắt buộc dùng móng đơn', F),
              ('Nhà 3 tầng nào cũng hạ móng đơn được', F),
              ('Không có quy định gì', F)]),

            ('Cách 4: thay cọc bê tông bằng cọc tre/cừ tràm tiết kiệm tổng khoảng bao nhiêu?',
             [('Khoảng 40-55 triệu (30-40tr tiền cọc + 10-15tr ca ép)', T),
              ('Khoảng 5 triệu', F),
              ('Khoảng 200 triệu', F),
              ('Không tiết kiệm', F)]),

            ('Vì sao ép cọc tre rẻ hơn nhiều so với cọc bê tông?',
             [('Cọc tre đóng thủ công không tốn ca máy ép, vật tư rẻ; cả công trình chỉ 10-15 triệu', T),
              ('Vì cọc tre to và nặng hơn', F),
              ('Vì cọc tre cần máy đặc biệt đắt tiền', F),
              ('Thực ra cọc tre đắt hơn', F)]),

            ('Nguyên tắc cốt lõi khi giảm kết cấu móng là gì?',
             [('Đúng nền đất + đúng số tầng + có khảo sát và kỹ thuật duyệt; an toàn trước, tiết kiệm sau', T),
              ('Cứ chọn loại rẻ nhất để khách chốt nhanh', F),
              ('Giảm móng càng nhiều càng tốt', F),
              ('Bỏ qua khảo sát cho nhanh', F)]),

            ('Hai thông tin phải nắm trước khi nghĩ tới giảm móng là gì?',
             [('Loại nền đất (cứng/liền thổ hay ẩm ướt/ao hồ) và số tầng của nhà', T),
              ('Màu sơn và kiểu cửa', F),
              ('Ngân sách nội thất và rèm', F),
              ('Hướng nhà và phong thủy', F)]),

            ('Vai trò của nhân viên kinh doanh trong việc chọn phương án móng là gì?',
             [('Tư vấn hướng đi và chuyển kỹ thuật khảo sát/duyệt, KHÔNG tự quyết kết cấu', T),
              ('Tự quyết loại móng và chốt luôn với khách', F),
              ('Tự ý ép cọc hay bỏ cọc theo ý mình', F),
              ('Quyết định tải trọng thay kỹ thuật', F)]),
        ]
