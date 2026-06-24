# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu hỏi thi cho khóa học
"D4 - Cân đối tài chính bằng cách GIẢM VẬT TƯ" (Cách 3).

Biến tài liệu gốc (cắt giảm 4 nhóm hạng mục: Thiết bị WC, Trần thạch cao, Cửa,
Sơn => bóc dự toán TRỪ TIỀN cho khách) thành 1 khóa trình bày dễ hiểu - dễ nhớ -
dễ áp dụng cho nhân viên MỚI, theo FORM chuẩn khóa học VINADUY: TIÊU ĐỀ LỚN có
hiệu ứng, ẢNH LỚN, khung công thức, tình huống, lời khuyên, chứng minh, sai lầm,
câu chốt thuộc lòng và ô "ÁP DỤNG NGAY".

Tái dùng helper khung từ seed_kh_tiem_nang + _chot từ seed_khong_tuoi để đồng
bộ giao diện. Tất cả helper riêng dùng prefix _d4v_ để KHÔNG trùng tên với các
file seed khác (xem reference-seed-method-name-collision).

Hiệu ứng toàn khóa: 1 khối <style> (class .vd-d4v) - keyframes vdShine (quét sáng
tiêu đề), vdRise (trồi lên khi hiện), vdPulse (nhịp mũi tên), hover zoom ảnh.
LƯU Ý: khối <style> được NỐI CHUỖI (không qua toán tử %) nên các ký tự % bên
trong (0%, 100%, scale) KHÔNG cần escape. Mọi helper dùng '...' % (...) thì ký tự
% literal (vd width:100%%) ĐÃ escape thành %% (xem reference-course-writing-format).

Idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models
from .seed_kh_tiem_nang import (
    _WRAP, _box, _formula, _apply, _situation, _advice, _proof, _mistake,
)
from .seed_khong_tuoi import _chot

_D4V_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.d4_giam_vat_tu_seed_version'
_IMG = '/vd_elearning/static/src/img/giamvattu/'

# ---------------------------------------------------------------------------
#  HIỆU ỨNG TOÀN KHÓA (nối chuỗi thuần - KHÔNG dùng % format -> % an toàn)
# ---------------------------------------------------------------------------
_STYLE = (
    '<style>'
    '.vd-d4v figure img{transition:transform .4s ease,box-shadow .4s ease;}'
    '.vd-d4v figure:hover img{transform:scale(1.035);'
    'box-shadow:0 20px 48px rgba(2,6,23,.34);}'
    '.vd-d4v .vd-card{animation:vdRise .7s ease both;}'
    '.vd-d4v .vd-hero{position:relative;overflow:hidden;}'
    '.vd-d4v .vd-hero::after{content:"";position:absolute;top:0;left:-65%;'
    'width:45%;height:100%;background:linear-gradient(120deg,'
    'rgba(255,255,255,0) 0%,rgba(255,255,255,.55) 50%,rgba(255,255,255,0) 100%);'
    'transform:skewX(-22deg);animation:vdShine 3.4s ease-in-out infinite;}'
    '.vd-d4v .vd-pulse{display:inline-block;animation:vdPulse 1.5s ease-in-out infinite;}'
    '@keyframes vdShine{0%{left:-65%}55%{left:135%}100%{left:135%}}'
    '@keyframes vdRise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}'
    '@keyframes vdPulse{0%,100%{transform:translateX(0)}50%{transform:translateX(7px)}}'
    '</style>'
)


def _hero(title_small, title_big, sub):
    """Tiêu đề SIÊU LỚN - ấn tượng (đỏ cam thương hiệu) + hiệu ứng quét sáng."""
    return (
        '<div class="vd-hero" style="background:linear-gradient(135deg,'
        '#f5523c 0%%,#d62f12 100%%);border-radius:22px;padding:40px 28px;'
        'margin:4px 0 28px;text-align:center;'
        'box-shadow:0 16px 40px rgba(214,47,18,.40);">'
        '<div style="color:#ffe6df;font-size:17px;font-weight:800;letter-spacing:4px;'
        'text-transform:uppercase;margin-bottom:10px;">%s</div>'
        '<div style="color:#ffffff;font-size:54px;font-weight:900;line-height:1.05;'
        'letter-spacing:1px;text-shadow:0 3px 10px rgba(0,0,0,.28);">%s</div>'
        '<div style="color:#fff4f0;font-size:17px;font-weight:600;margin-top:16px;'
        'max-width:760px;margin-left:auto;margin-right:auto;">%s</div></div>'
    ) % (title_small, title_big, sub)


def _solo(name, cap='', h=520):
    """1 ẢNH RẤT LỚN canh giữa (object-fit contain - không cắt mất nội dung)."""
    c = ''
    if cap:
        c = ('<figcaption style="font-size:14.5px;color:#475569;text-align:center;'
             'margin-top:12px;font-weight:700;">%s</figcaption>') % cap
    return (
        '<figure style="margin:20px auto;max-width:760px;">'
        '<img src="%s%s" style="width:100%%;max-height:%dpx;object-fit:contain;'
        'background:#f8fafc;border:1px solid #e2e8f0;border-radius:18px;padding:12px;'
        'box-shadow:0 12px 32px rgba(32,36,58,.22);"/>%s</figure>'
    ) % (_IMG, name, h, c)


def _gallery(*figs):
    return ('<div style="display:flex;flex-wrap:wrap;gap:18px;margin:20px 0;'
            'justify-content:center;">%s</div>') % ''.join(figs)


def _fig(name, cap='', h=440):
    """Ảnh LỚN trong gallery (xếp cạnh nhau)."""
    c = ''
    if cap:
        c = ('<figcaption style="font-size:13.5px;color:#475569;text-align:center;'
             'margin-top:9px;font-weight:700;">%s</figcaption>') % cap
    return (
        '<figure style="margin:0;flex:1 1 420px;min-width:300px;max-width:560px;">'
        '<img src="%s%s" style="width:100%%;height:%dpx;object-fit:contain;'
        'background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;padding:10px;'
        'box-shadow:0 10px 28px rgba(32,36,58,.20);"/>%s</figure>'
    ) % (_IMG, name, h, c)


def _card(c1, c2, icon, title, inner):
    """Thẻ hạng mục - đầu thẻ gradient màu, trồi lên khi hiện (vdRise)."""
    return (
        '<div class="vd-card" style="border:1px solid #e2e8f0;border-radius:18px;'
        'margin:24px 0;overflow:hidden;box-shadow:0 10px 30px rgba(2,6,23,.10);">'
        '<div style="background:linear-gradient(135deg,%s 0%%,%s 100%%);'
        'padding:16px 20px;color:#fff;font-size:22px;font-weight:900;'
        'letter-spacing:.5px;">%s %s</div>'
        '<div style="padding:18px 20px;">%s</div></div>'
    ) % (c1, c2, icon, title, inner)


class SlideChannelSeedD4GiamVatTu(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_d4_giam_vat_tu(self):
        ch = self.env.ref('vd_elearning.course_d4', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _D4V_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:30px 0;"/>'
        merged = sep.join(body for _title, body in self._vd_d4v_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-d4v" style="%s">%s</div>'
                                 % (_WRAP, merged)),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_d4v_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _D4V_VERSION)
        return True

    # ==================================================================
    #  NỘI DUNG BÀI HỌC (7 phần)
    # ==================================================================
    def _vd_d4v_pages(self):
        h2 = 'font-size:20px;font-weight:900;color:#1e293b;margin:20px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#b91c1c;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('Mở đầu', self._d4v_p1(h2, h3, lead)),
            ('Cách cắt giảm', self._d4v_p2(h2, h3, lead)),
            ('Thiết bị WC', self._d4v_p3(h2, h3, lead)),
            ('Trần thạch cao', self._d4v_p4(h2, h3, lead)),
            ('Cửa', self._d4v_p5(h2, h3, lead)),
            ('Sơn', self._d4v_p6(h2, h3, lead)),
            ('Kịch bản - Câu chốt', self._d4v_p7(h2, h3, lead)),
        ]

    # ------------------------------------------------------------------
    def _d4v_p1(self, h2, h3, lead):
        return (
            _hero('Cân đối tài chính &mdash; Nâng cao &middot; Cách 3',
                  'GIẢM VẬT TƯ',
                  'Khi ngân sách của khách CÓ HẠN &mdash; cắt bớt một số HẠNG MỤC '
                  'vật tư rồi BÓC DỰ TOÁN TRỪ TIỀN, để khách làm sau hoặc lấy chỗ '
                  'quen cho NỢ &mdash; chi phí về đúng tầm tiền mà nhà vẫn chắc.')

            + '<p style="' + lead + '">Trong tư vấn <b>xây nhà trọn gói</b>, nhiều '
            'khách rất thích nhưng <b>tài chính lại chưa đủ ngay</b>. Nhiệm vụ của '
            'nhân viên là <b>cân đối tài chính cho khách</b>: kéo chi phí về đúng '
            'tầm tiền. Một cách quan trọng là <b>GIẢM VẬT TƯ</b> &mdash; nhưng phải '
            'hiểu cho ĐÚNG bản chất.</p>'

            + _formula(
                'GIẢM VẬT TƯ ở đây = <span style="color:#16a34a;">CẮT BỚT HẠNG MỤC '
                'hoàn thiện / thiết bị</span> rồi <b>BÓC DỰ TOÁN TRỪ TIỀN</b> cho '
                'khách &mdash; <span style="color:#dc2626;">KHÔNG phải</span> hạ '
                'chất lượng vật tư kết cấu (móng, cột, dầm, mái).'
            )

            + '<h2 style="' + h2 + '">Phân biệt cho RÕ &mdash; tránh hiểu sai chết người</h2>'
            '<table><thead><tr>'
            '<th style="text-align:center;width:50%;color:#16a34a;">ĐÚNG &mdash; Giảm vật tư (cắt hạng mục)</th>'
            '<th style="text-align:center;color:#dc2626;">SAI &mdash; Giảm chất lượng vật tư</th>'
            '</tr></thead><tbody>'
            '<tr><td>Cắt bớt <b>thiết bị WC, trần thạch cao, cửa, sơn</b> (phần hoàn thiện)</td>'
            '<td>Đổi sang <b>xi măng, thép, gạch loại kém</b> để rẻ</td></tr>'
            '<tr><td>Khách <b>tự làm sau</b> hoặc lấy chỗ quen để <b>nợ / khất tiền</b></td>'
            '<td>Làm luôn nhưng bằng vật liệu dỏm</td></tr>'
            '<tr><td>Nhà vẫn <b>chắc, an toàn</b> &mdash; chỉ thiếu phần lắp sau</td>'
            '<td>Nhà <b>yếu, xuống cấp nhanh</b>, mất an toàn</td></tr>'
            '<tr><td>Vinaduy <b>bóc dự toán TRỪ TIỀN</b> minh bạch</td>'
            '<td>Giấu khách, sau phát sinh &mdash; mất uy tín</td></tr>'
            '</tbody></table>'

            + _advice(
                '<p style="margin-bottom:0;">Bốn nhóm hạng mục được phép cắt giảm để '
                'trừ tiền: <b>(1) Thiết bị WC &middot; (2) Trần thạch cao &middot; '
                '(3) Cửa &middot; (4) Sơn</b>. Đây đều là phần <b>hoàn thiện / lắp '
                'thêm</b> &mdash; cắt ra nhà vẫn ở được, khách bổ sung sau cũng dễ.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Khi khách kêu "chưa đủ tiền", phải nghĩ '
                'ngay tới <b>4 nhóm hạng mục cắt được</b> (WC, trần, cửa, sơn) &mdash; '
                '<span class="vd-pulse">&#10145;</span> đề xuất cắt và <b>trừ tiền</b>, '
                'TUYỆT ĐỐI không gợi ý hạ chất lượng vật tư kết cấu.</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">3 MỨC ĐỘ CẮT GIẢM &mdash; áp dụng cho MỌI hạng mục</h2>'
            '<p style="' + lead + '">Với bất kỳ hạng mục nào (WC, trần, cửa, sơn), '
            'luôn có <b>3 mức cắt giảm</b> để chọn theo nhu cầu và tài chính của khách. '
            'Học thuộc 3 mức này là dùng được cho cả 4 nhóm.</p>'

            + '<table><thead><tr><th style="width:60px;">Mức</th>'
            '<th>Cách làm</th><th>Dùng khi</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:22px;">&#9312;</td>'
            '<td><b style="color:#16a34a;">CẮT MỘT PHẦN</b><br/>Bỏ hạng mục ở '
            '<b>những phòng chưa dùng đến</b></td>'
            '<td>Khách vẫn muốn làm phần đang ở, chỉ tiết kiệm phần chưa cần.</td></tr>'
            '<tr><td style="text-align:center;font-size:22px;">&#9313;</td>'
            '<td><b style="color:#b45309;">CẮT TOÀN BỘ &mdash; LÀM SAU</b><br/>'
            'Bỏ hết hạng mục để <b>khách lắp / thi công sau</b> khi có điều kiện</td>'
            '<td>Khách muốn giảm mạnh, sẽ tự bổ sung khi có tiền.</td></tr>'
            '<tr><td style="text-align:center;font-size:22px;">&#9314;</td>'
            '<td><b style="color:#dc2626;">CẮT TOÀN BỘ &mdash; LẤY CHỖ QUEN</b><br/>'
            'Bỏ hết để khách lấy vật tư / thi công <b>chỗ người quen, cửa hàng gần '
            'nhà</b></td>'
            '<td>Khách cần <b>nợ được</b> hoặc <b>thanh toán dài hơn</b> qua mối quen.</td></tr>'
            '</tbody></table>'

            + _box('#0ea5e9', '#f0f9ff', '&#128221;', 'Quy trình BẮT BUỘC sau khi chốt cắt',
                   '<p style="margin-bottom:0;">Dù chọn mức nào, bước cuối luôn giống '
                   'nhau: <b>Vinaduy sẽ bóc dự toán và TRỪ những vật tư đó ra</b> để '
                   '<b>giảm chi phí cho khách</b> &mdash; rõ ràng, đúng số tiền của '
                   'phần đã cắt.</p>')

            + _proof(
                '<p style="margin-bottom:0;">Vì sao cách này hiệu quả? Phần cắt ra '
                '(WC, trần, cửa, sơn) <b>không ảnh hưởng kết cấu</b> &mdash; nhà vẫn '
                'xây xong chắc chắn. Khách <b>giảm được tiền ngay</b>, lại <b>chủ '
                'động</b> bổ sung sau theo túi tiền hoặc qua mối quen để khất nợ. '
                'Khách thấy mình được lo, không bị ép.</p>'
            )

            + _mistake(
                '<p style="margin-bottom:0;">Cắt hạng mục mà <b>quên bóc dự toán trừ '
                'tiền</b>, hoặc trừ không rõ ràng &mdash; khách nghĩ bị "ăn bớt". Phải '
                '<b>trừ đúng giá trị phần đã cắt</b> và nói rõ cho khách.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Thuộc lòng <b>3 mức cắt</b>: (1) cắt phần '
                'chưa dùng &middot; (2) cắt hết để làm sau &middot; (3) cắt hết để lấy '
                'chỗ quen cho nợ. Sau đó luôn <b>bóc dự toán trừ tiền</b>.</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p3(self, h2, h3, lead):
        return (
            _card('#0369a1', '#0ea5e9', '&#128701;&#65039;', 'HẠNG MỤC 1 &mdash; THIẾT BỊ WC',
                  '<p style="' + lead + '">Thiết bị WC gồm <b>bồn cầu, lavabo, vòi '
                  'sen, vòi rửa, sen tắm&hellip;</b> &mdash; là phần <b>lắp thêm</b>, '
                  'cắt ra rất dễ bổ sung sau.</p>'

                  + _solo('wc.jpg', 'Bộ thiết bị WC (bồn cầu, lavabo, vòi sen, sen '
                          'tắm) &mdash; phần hoàn thiện, cắt giảm để trừ tiền cho khách.',
                          h=520)

                  + '<ul style="margin:8px 0;">'
                  '<li><b>Cắt một phần:</b> giảm bớt thiết bị WC ở <b>những phòng chưa '
                  'sử dụng đến</b> để giảm chi phí.</li>'
                  '<li><b>Cắt toàn bộ &mdash; làm sau:</b> bỏ hết thiết bị WC để '
                  '<b>khách tự lắp đặt sau</b> khi có điều kiện.</li>'
                  '<li><b>Cắt toàn bộ &mdash; lấy chỗ quen:</b> để khách lấy vật tư '
                  '<b>chỗ người quen hoặc cửa hàng gần nhà</b>, nhờ đó <b>nợ được</b> '
                  'hoặc thanh toán trong thời gian lâu hơn.</li>'
                  '<li><b>Vinaduy bóc dự toán và TRỪ</b> thiết bị WC đã cắt để giảm chi '
                  'phí cho khách.</li></ul>')

            + _situation(
                '<p style="margin-bottom:0;">Khách xây nhà 4 phòng nhưng mới ở 2 '
                'phòng: mình tư vấn <b>chỉ lắp WC 2 phòng đang dùng</b>, hai phòng còn '
                'lại để trống, <b>trừ tiền thiết bị</b> ra. Khi nào dùng tới khách lắp '
                'sau cũng được.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Gặp khách thiếu tiền, hỏi ngay: '
                '"<b>Phòng nào chưa dùng tới mình để trống thiết bị WC nhé</b>, em '
                'trừ khoản đó ra cho anh, khi nào cần anh lắp sau cũng dễ."</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p4(self, h2, h3, lead):
        return (
            _card('#7c3aed', '#a855f7', '&#10024;', 'HẠNG MỤC 2 &mdash; TRẦN THẠCH CAO',
                  '<p style="' + lead + '">Trần thạch cao là phần <b>trang trí trần</b> '
                  '&mdash; đẹp nhưng <b>không bắt buộc</b>, cắt ra nhà vẫn hoàn thiện ở '
                  'được, làm sau rất dễ.</p>'

                  + _solo('tran_thach_cao.jpg', 'Trần thạch cao trang trí &mdash; hạng '
                          'mục hoàn thiện, có thể cắt giảm hoặc làm sau để trừ tiền.',
                          h=520)

                  + '<ul style="margin:8px 0;">'
                  '<li><b>Cắt một phần:</b> giảm bớt trần thạch cao ở <b>những phòng '
                  'chưa sử dụng đến</b>.</li>'
                  '<li><b>Cắt theo tầng (nhà cao tầng):</b> chỉ làm trần thạch cao '
                  '<b>phòng khách</b>, cắt toàn bộ trần thạch cao <b>các tầng trên</b> '
                  'để giảm chi phí.</li>'
                  '<li><b>Cắt toàn bộ &mdash; lấy chỗ quen:</b> để khách lấy vật tư '
                  'hoặc thi công <b>chỗ người quen / cửa hàng gần nhà</b> để <b>nợ '
                  'được</b> hoặc thanh toán lâu hơn.</li>'
                  '<li><b>Vinaduy bóc dự toán và TRỪ</b> phần trần thạch cao đã cắt.</li>'
                  '</ul>')

            + _advice(
                '<p style="margin-bottom:0;">Mẹo hay với nhà cao tầng: giữ trần thạch '
                'cao <b>phòng khách</b> (nơi tiếp khách, cần đẹp), <b>cắt các tầng '
                'trên</b> &mdash; khách vừa tiết kiệm nhiều, nhà vẫn sang ở khu vực '
                'quan trọng nhất.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Đề xuất với khách: "Mình <b>làm trần '
                'thạch cao phòng khách thôi</b> cho đẹp, các phòng trên để trần phẳng, '
                'em <b>trừ tiền</b> phần đó &mdash; sau này anh thích thì làm thêm dễ '
                'mà."</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p5(self, h2, h3, lead):
        return (
            _card('#475569', '#64748b', '&#128682;', 'HẠNG MỤC 3 &mdash; CỬA',
                  '<p style="' + lead + '">Cửa (cửa chính, cửa phòng, cửa sổ) là phần '
                  '<b>lắp sau cùng</b> &mdash; có thể cắt để khách thi công sau hoặc '
                  'làm chỗ quen cho khất nợ.</p>'

                  + _solo('cua.jpg', 'Hạng mục cửa &mdash; lắp ở giai đoạn cuối, có '
                          'thể cắt giảm để khách làm sau hoặc lấy chỗ quen.', h=500)

                  + '<ul style="margin:8px 0;">'
                  '<li><b>Cắt một phần:</b> cắt những phần cửa <b>chưa cần thiết phải '
                  'thi công luôn</b> để đối trừ, giảm tiền cho khách.</li>'
                  '<li><b>Cắt toàn bộ &mdash; làm sau:</b> bỏ hết phần cửa để '
                  '<b>khách thi công sau</b>.</li>'
                  '<li><b>Cắt toàn bộ &mdash; lấy chỗ quen:</b> để khách thi công '
                  '<b>chỗ người quen hoặc đơn vị gần nhà</b>, nhờ đó <b>khất lại chi '
                  'phí cửa</b> trong một khoảng thời gian.</li>'
                  '<li><b>Vinaduy bóc dự toán và TRỪ</b> phần cửa đã cắt để giảm chi '
                  'phí cho khách.</li></ul>')

            + _proof(
                '<p style="margin-bottom:0;">Cửa thường lắp ở <b>giai đoạn cuối</b> '
                'nên cắt ra <b>không ảnh hưởng tiến độ xây thô</b>. Khách hoàn toàn có '
                'thể tự lắp sau, hoặc đặt chỗ quen để <b>trả chậm</b> &mdash; đây là '
                'khoản dễ giãn tiền nhất cho khách.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Nói với khách: "Phần cửa mình <b>để lắp '
                'sau cũng được</b>, hoặc anh có chỗ quen làm cửa thì lấy bên đó cho '
                '<b>khất tiền</b>, em <b>trừ khoản cửa</b> ra trước cho nhẹ."</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p6(self, h2, h3, lead):
        return (
            _card('#15803d', '#22c55e', '&#127912;', 'HẠNG MỤC 4 &mdash; SƠN (TRONG &amp; NGOÀI)',
                  '<p style="' + lead + '">Toàn bộ phần sơn &mdash; gồm <b>sơn nội '
                  'thất (bên trong)</b> và <b>sơn ngoại thất (bên ngoài)</b> &mdash; '
                  'có thể cắt giảm, không thi công, để giảm chi phí cho khách.</p>'

                  + _gallery(
                      _fig('son.jpg', 'Sơn nội thất + ngoại thất &mdash; toàn bộ hạng '
                           'mục sơn có thể cắt để trừ tiền.', h=420),
                      _fig('nha_chua_son.jpg', 'Nhà bàn giao phần thô (chưa sơn) '
                           '&mdash; khách sơn sau khi có điều kiện.', h=420))

                  + '<ul style="margin:8px 0;">'
                  '<li><b>Cắt toàn bộ phần sơn:</b> cả <b>sơn trong nhà (nội thất)</b> '
                  'và <b>sơn ngoài nhà (ngoại thất)</b> đều cắt giảm, <b>không thi '
                  'công</b>, để giảm chi phí.</li>'
                  '<li>Khách <b>sơn sau</b> khi có điều kiện, hoặc thuê thợ quen để '
                  '<b>trả chậm</b>.</li>'
                  '<li><b>Vinaduy bóc dự toán và TRỪ</b> toàn bộ phần sơn để giảm chi '
                  'phí cho khách.</li></ul>')

            + _situation(
                '<p style="margin-bottom:0;">Khách cần dọn về ở gấp nhưng thiếu tiền: '
                'mình bàn giao nhà <b>phần thô hoàn thiện, chưa sơn</b>, <b>trừ toàn '
                'bộ tiền sơn</b> ra. Khách ở trước, để dành ít tháng rồi <b>sơn sau</b> '
                '&mdash; vừa nhẹ tiền vừa kịp về nhà mới.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Gợi ý: "Phần sơn trong và ngoài em '
                '<b>tách ra để sau</b>, anh ở ổn rồi sơn cũng được &mdash; em <b>trừ '
                'hẳn khoản sơn</b>, giờ anh nhẹ được một khoản lớn."</p>'
            )
        )

    # ------------------------------------------------------------------
    def _d4v_p7(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">KỊCH BẢN TƯ VẤN GIẢM VẬT TƯ (thuộc lòng)</h2>'
            '<p style="' + lead + '">Khi khách <b>thích nhưng chưa đủ tiền</b>, đây là '
            'cách dẫn dắt để khách yên tâm chốt:</p>'

            + _chot(
                '<b>Bước 1 &mdash; Trấn an &amp; giữ chất lượng:</b> "Bên em '
                '<b>không hạ chất lượng vật tư</b> đâu anh, kết cấu nhà vẫn chuẩn để '
                'bền và an toàn. Mình chỉ <b>cân đối lại vài hạng mục hoàn thiện</b> '
                'cho vừa tài chính của anh thôi."'
            )
            + _chot(
                '<b>Bước 2 &mdash; Đưa 4 nhóm cắt được:</b> "Có <b>4 phần</b> mình có '
                'thể tách ra để anh nhẹ tiền: <b>thiết bị WC, trần thạch cao, cửa và '
                'sơn</b>. Mấy phần này lắp sau rất dễ, không ảnh hưởng gì tới nhà cả."'
            )
            + _chot(
                '<b>Bước 3 &mdash; Mở đường nợ / làm sau:</b> "Anh có thể <b>tự làm '
                'sau</b> khi rảnh tiền, hoặc lấy <b>chỗ người quen, cửa hàng gần '
                'nhà</b> để <b>khất / trả chậm</b> được. Bên em <b>bóc dự toán trừ '
                'thẳng số tiền</b> mấy phần đó cho anh."'
            )
            + _chot(
                '<b>Bước 4 &mdash; Chốt mở:</b> "Để em <b>tính lại phương án đã trừ '
                'các hạng mục này</b> rồi gửi anh xem con số mới, anh em mình cân đối '
                'thêm cho hợp lý nhé."'
            )

            + '<h2 style="' + h2 + '">Vì sao kịch bản này hiệu quả</h2>'
            '<table><thead><tr><th style="width:36%;">Bước</th>'
            '<th>Khách cảm nhận được gì</th></tr></thead><tbody>'
            '<tr><td><b>1. Giữ chất lượng</b></td><td>Yên tâm nhà vẫn chắc, không bị làm ẩu.</td></tr>'
            '<tr><td><b>2. Đưa 4 nhóm cắt</b></td><td>Thấy có lối ra rõ ràng, dễ hiểu.</td></tr>'
            '<tr><td><b>3. Cho nợ / làm sau</b></td><td>Thấy được tạo điều kiện, chủ động về tiền.</td></tr>'
            '<tr><td><b>4. Chốt mở</b></td><td>Có lý do tiếp tục, mình được tính lại phương án.</td></tr>'
            '</tbody></table>'

            + _mistake(
                '<p style="margin-bottom:0;">Sai lầm chết người: để giữ phương án rẻ '
                'mà <b>hạ chất lượng vật tư kết cấu</b> (xi măng, thép, gạch dỏm). Nhà '
                'sẽ <b>yếu, nguy hiểm</b>, mất uy tín công ty. Đúng cách là <b>giữ vật '
                'tư chuẩn, chỉ cắt hạng mục hoàn thiện và trừ tiền</b>.</p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Kết luận phải nhớ</h2>'
            + _formula(
                'Khách chưa đủ tiền &rArr; <b>KHÔNG hạ chất lượng vật tư</b>, mà '
                '<b>CẮT 4 NHÓM HẠNG MỤC</b>: Thiết bị WC &#8226; Trần thạch cao '
                '&#8226; Cửa &#8226; Sơn &mdash; cho khách làm sau / lấy chỗ quen để '
                'nợ, rồi <b>BÓC DỰ TOÁN TRỪ TIỀN</b>.'
            )

            + _apply(
                '<p>Bảng tự kiểm trước mỗi lần báo giá cho khách "chưa đủ tiền" (Có/Không):</p>'
                '<ol>'
                '<li>Đã <b>giữ nguyên chất lượng vật tư kết cấu</b> chưa? (KHÔNG hạ cấp)</li>'
                '<li>Đã rà <b>4 nhóm hạng mục cắt được</b> (WC / trần / cửa / sơn) chưa?</li>'
                '<li>Đã chọn đúng <b>mức cắt</b> (phần chưa dùng / làm sau / lấy chỗ quen) chưa?</li>'
                '<li>Đã hứa <b>bóc dự toán TRỪ TIỀN</b> rõ ràng cho khách chưa?</li>'
                '<li>Đã mở đường <b>nợ / trả chậm</b> qua chỗ quen cho khách chưa?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Còn ô nào "Không" &rArr; đó là việc phải '
                'làm trước khi chốt giá với khách.</p>'
            )
        )

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (ép nhớ + vận dụng). (đáp án, đúng?)
    # ==================================================================
    def _vd_d4v_questions(self):
        T, F = True, False
        return [
            ('Trong khóa này, "GIẢM VẬT TƯ" để cân đối tài chính có nghĩa ĐÚNG là gì?',
             [('Cắt bớt một số HẠNG MỤC hoàn thiện/thiết bị rồi bóc dự toán TRỪ TIỀN cho khách', T),
              ('Đổi xi măng, thép, gạch sang loại kém hơn cho rẻ', F),
              ('Giảm số tầng của ngôi nhà', F),
              ('Báo giá cao hơn để khách tự rút lui', F)]),

            ('Vì sao TUYỆT ĐỐI không được hạ chất lượng vật tư kết cấu để giảm giá?',
             [('Nhà sẽ yếu, không an toàn, xuống cấp nhanh và làm mất uy tín công ty', T),
              ('Vì vật tư kém khó mua', F),
              ('Vì khách không thích màu vật tư kém', F),
              ('Thực ra hạ chất lượng là cách tốt nhất', F)]),

            ('Bốn (4) nhóm hạng mục được phép cắt giảm để trừ tiền là gì?',
             [('Thiết bị WC, Trần thạch cao, Cửa, Sơn', T),
              ('Móng, Cột, Dầm, Mái', F),
              ('Xi măng, Thép, Gạch, Cát', F),
              ('Phòng khách, Bếp, Nhà thờ, Phòng ngủ', F)]),

            ('Ba (3) mức độ cắt giảm áp dụng cho mọi hạng mục là gì?',
             [('Cắt phần chưa dùng đến; cắt toàn bộ để làm sau; cắt toàn bộ để lấy chỗ quen cho nợ', T),
              ('Cắt 10%, cắt 50%, cắt 100% ngẫu nhiên', F),
              ('Cắt móng, cắt cột, cắt mái', F),
              ('Giảm giá, tăng giá, giữ giá', F)]),

            ('Sau khi chốt cắt hạng mục, bước BẮT BUỘC cuối cùng Vinaduy phải làm là gì?',
             [('Bóc dự toán và TRỪ đúng giá trị những vật tư đã cắt để giảm chi phí cho khách', T),
              ('Giữ nguyên giá nhưng làm thêm cho khách', F),
              ('Tính thêm phụ phí quản lý', F),
              ('Không cần làm gì thêm', F)]),

            ('Với thiết bị WC, cách "cắt một phần" được thực hiện thế nào?',
             [('Giảm bớt thiết bị WC ở những phòng chưa sử dụng đến', T),
              ('Bỏ luôn cả bồn cầu phòng đang ở', F),
              ('Đổi sang bồn cầu loại kém', F),
              ('Lắp gấp đôi thiết bị cho đủ', F)]),

            ('Khi cắt toàn bộ thiết bị WC để khách "lấy chỗ quen", lợi ích cho khách là gì?',
             [('Khách nợ được hoặc thanh toán trong thời gian lâu hơn qua mối quen', T),
              ('Khách được tặng thêm thiết bị', F),
              ('Khách không phải lắp WC bao giờ', F),
              ('Khách được giảm thuế', F)]),

            ('Với nhà cao tầng, mẹo cắt trần thạch cao hợp lý là gì?',
             [('Chỉ làm trần thạch cao phòng khách, cắt toàn bộ trần các tầng trên', T),
              ('Làm trần thạch cao tất cả các phòng cho đều', F),
              ('Bỏ luôn trần phòng khách, giữ các tầng trên', F),
              ('Làm trần thạch cao gấp đôi ở tầng trên', F)]),

            ('Trần thạch cao thuộc loại hạng mục nào?',
             [('Phần hoàn thiện/trang trí, không bắt buộc, cắt ra nhà vẫn ở được', T),
              ('Phần kết cấu chịu lực bắt buộc', F),
              ('Phần móng của ngôi nhà', F),
              ('Phần không bao giờ được cắt', F)]),

            ('Vì sao hạng mục CỬA dễ cắt để khách làm sau?',
             [('Cửa thường lắp ở giai đoạn cuối nên cắt ra không ảnh hưởng tiến độ xây thô', T),
              ('Vì cửa không quan trọng với nhà', F),
              ('Vì cửa là phần chịu lực chính', F),
              ('Vì cửa luôn miễn phí', F)]),

            ('Cách cắt cửa "một phần" được mô tả thế nào?',
             [('Cắt những phần cửa chưa cần thiết phải thi công luôn để đối trừ, giảm tiền', T),
              ('Cắt toàn bộ cửa kể cả cửa chính', F),
              ('Đổi cửa sang loại kém', F),
              ('Bịt kín hết các ô cửa', F)]),

            ('Khi khách lấy cửa "chỗ người quen hoặc đơn vị gần nhà", lợi ích là gì?',
             [('Khách khất lại được chi phí cửa trong một khoảng thời gian', T),
              ('Cửa sẽ đẹp hơn hẳn', F),
              ('Vinaduy được thêm hoa hồng', F),
              ('Khách không cần lắp cửa nữa', F)]),

            ('Hạng mục SƠN khi cắt giảm bao gồm những phần nào?',
             [('Cả sơn nội thất (bên trong) và sơn ngoại thất (bên ngoài) đều cắt, không thi công', T),
              ('Chỉ cắt sơn bên trong, giữ sơn bên ngoài', F),
              ('Chỉ cắt sơn bên ngoài, giữ sơn bên trong', F),
              ('Đổi sang sơn loại rẻ tiền', F)]),

            ('Khi cắt toàn bộ sơn, nhà được bàn giao ở trạng thái nào?',
             [('Phần thô hoàn thiện chưa sơn; khách sơn sau khi có điều kiện', T),
              ('Nhà đã sơn hoàn chỉnh', F),
              ('Chỉ xong phần móng', F),
              ('Nhà bị bỏ dở không ở được', F)]),

            ('Câu nào sau đây là VÍ DỤ ĐÚNG của "giảm vật tư" (không phải giảm chất lượng)?',
             [('Để trống thiết bị WC các phòng chưa dùng và trừ tiền cho khách', T),
              ('Dùng thép nhỏ hơn quy cách để tiết kiệm', F),
              ('Trộn ít xi măng hơn vào bê tông', F),
              ('Dùng gạch nung non lửa cho rẻ', F)]),

            ('Trong kịch bản tư vấn, Bước 1 nhân viên cần làm gì trước tiên?',
             [('Trấn an khách rằng KHÔNG hạ chất lượng vật tư, kết cấu nhà vẫn chuẩn và an toàn', T),
              ('Báo ngay giá thấp nhất có thể', F),
              ('Yêu cầu khách đặt cọc gấp', F),
              ('Chê phương án của khách', F)]),

            ('Ở Bước 2 của kịch bản, nhân viên đưa ra cho khách điều gì?',
             [('4 nhóm hạng mục có thể tách ra để nhẹ tiền: thiết bị WC, trần thạch cao, cửa, sơn', T),
              ('Đề nghị vay ngân hàng', F),
              ('Danh sách vật tư giá rẻ kém chất lượng', F),
              ('Yêu cầu tăng ngân sách gấp đôi', F)]),

            ('Câu chốt mở (Bước 4) nên nói gì?',
             [('"Để em tính lại phương án đã trừ các hạng mục này rồi gửi anh xem con số mới, mình cân đối thêm"', T),
              ('"Giá này là cuối cùng, anh quyết luôn"', F),
              ('"Anh không chốt thì thôi em nghỉ"', F),
              ('"Anh tự tính lại rồi báo em"', F)]),

            ('Một khách muốn dọn về ở gấp nhưng thiếu tiền. Cách xử lý hợp lý nhất là gì?',
             [('Bàn giao nhà phần thô chưa sơn, trừ toàn bộ tiền sơn, khách ở trước rồi sơn sau', T),
              ('Giục khách vay nóng để sơn ngay', F),
              ('Dùng sơn dỏm cho rẻ rồi sơn luôn', F),
              ('Từ chối khách vì chưa đủ tiền', F)]),

            ('Đâu là nguyên tắc cốt lõi xuyên suốt khi "giảm vật tư" cân đối tài chính?',
             [('Giữ vật tư kết cấu chuẩn, chỉ cắt hạng mục hoàn thiện và bóc dự toán trừ tiền minh bạch', T),
              ('Cắt càng nhiều càng tốt kể cả kết cấu', F),
              ('Giấu khách phần đã cắt để giữ giá', F),
              ('Luôn báo giá cao nhất có thể', F)]),
        ]
