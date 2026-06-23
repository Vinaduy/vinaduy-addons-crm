# -*- coding: utf-8 -*-
"""Seed noi dung + bai thi cho khoa "Don gia xay dung" (course_c1).

Gop 2 tai lieu cong ty: "Don gia.pdf" (bang gia chi tiet 3 mien) + "Tinh nham.pptx"
(he so tinh nham nhanh). Muc tieu: NV moi NHO duoc bang gia va TINH NHAM ra tong
chi phi ngay trong cuoc goi.

CACH TINH HE SO (user spec 2026-06-23): he so DUOC SUY RA tu bang gia, KHONG dung
so co san sai cua pptx:
    HE SO = Mong% + (So tang x 100%) + Mai%   (tat ca theo don gia)
Vi du: nha tren 70m2, 1 tang, mai bang, mong don = 30% + 100% + 20% = 1.50.

Bang HE SO chi viet MIEN BAC. Bang BAO GIA chi tiet co 3 tab (Bac/Trung/Nam).

Bai thi: 20 cau trac nghiem + 10 cau TINH TIEN (da tinh lai dung theo he so moi).

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import (_WRAP, _box, _formula, _apply, _situation,
                                _advice, _proof, _mistake)

_BG_VERSION = 'v3'
_PARAM_KEY = 'vd_elearning.banggia_seed_version'


def _tip(inner):
    """Khung MEO NHO (mau tim) - giup hoc thuoc nhanh."""
    return _box('#7c3aed', '#f5f3ff', '&#129504;', 'Mẹo nhớ nhanh', inner)


def _why(inner):
    """Khung VI SAO (mau xanh duong dam) - giai thich ly do dang sau con so."""
    return _box('#0369a1', '#e0f2fe', '&#10067;', 'Vì sao lại như vậy?', inner)


def _core(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">&#11088; ĐIỀU CẦN NHỚ</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


class SlideChannelSeedBangGia(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_bang_gia(self):
        ch = self.env.ref('vd_elearning.course_c1', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _BG_VERSION:
            return True

        # Khoa nay nang ve TINH TOAN: dat 80%, thi lai khong gioi han, 45 phut.
        ch.write({'name': 'Đơn giá xây dựng', 'vd_pass_percent': 80,
                  'vd_max_attempts': 0, 'vd_exam_minutes': 45})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        sep = '<hr style="border:0;border-top:2px dashed #e2e8f0;margin:28px 0;"/>'
        merged = sep.join(body for _t, body in self._vd_bg_pages())
        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': '<div style="%s">%s</div>' % (_WRAP, merged),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 30 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in (self._vd_bg_questions() + self._vd_bg_calc_questions()):
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _BG_VERSION)
        return True

    # ==================================================================
    #  NOI DUNG
    # ==================================================================
    def _vd_bg_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'
        return [
            ('1. Cong thuc than thanh', self._p1(h2, h3, lead)),
            ('2. Don gia theo m2', self._p2(h2, h3, lead)),
            ('3. He so tinh nham (Mien Bac)', self._p3(h2, h3, lead)),
            ('4. Bang bao gia 3 mien', self._p4(h2, h3, lead)),
            ('5. Cach tinh dien tich', self._p5(h2, h3, lead)),
            ('6. Phat sinh', self._p6(h2, h3, lead)),
            ('7. Vi du tinh mau', self._p7(h2, h3, lead)),
            ('8. Ket luan', self._p8(h2, h3, lead)),
        ]

    def _p1(self, h2, h3, lead):
        return (
            '<div style="background:linear-gradient(135deg,#b91c1c,#ea580c);color:#fff;'
            'padding:22px 24px;border-radius:16px;margin:4px 0 18px;">'
            '<div style="font-size:13px;letter-spacing:2px;opacity:.9;font-weight:700;">'
            'ĐƠN GIÁ XÂY DỰNG - VINADUY</div>'
            '<div style="font-size:25px;font-weight:900;margin-top:4px;">BẢNG GIÁ &amp; TÍNH NHẨM</div>'
            '<div style="font-size:15px;opacity:.95;margin-top:8px;">Học xong khóa này, bạn '
            '<b>tính nhẩm ra tổng tiền xây nhà NGAY trong cuộc gọi</b> &mdash; không cần mở file, '
            'không cần chờ báo giá. Quan trọng hơn: bạn <b>HIỂU vì sao</b> ra con số đó để giải '
            'thích cho khách thật tự tin.</div></div>'

            '<h2 style="' + h2 + '">&#128176; CHỈ CÓ 1 CÔNG THỨC PHẢI THUỘC</h2>'
            '<p style="' + lead + '">Mọi cách tính nhẩm của VINADUY đều quy về <b>một công thức '
            'duy nhất</b>. Thuộc công thức này là bạn tính được 90% trường hợp.</p>'

            + _formula(
                'TỔNG TIỀN = HỆ SỐ &times; DIỆN TÍCH (sàn tầng 1) &times; ĐƠN GIÁ'
            )
            + _tip(
                '<p style="margin:0;">Nhớ 3 chữ: <b style="color:#7c3aed;">HỆ &mdash; DIỆN &mdash; GIÁ</b> '
                '(Hệ số &rarr; Diện tích &rarr; Đơn giá). Đọc nhanh: '
                '<i>"Hệ nhân Diện nhân Giá"</i>.</p>'
                '<ul style="margin:8px 0 0;">'
                '<li><b>Hệ số</b>: tra bảng theo <b>Số tầng + Kiểu mái + Loại móng</b> '
                '(đã gộp sẵn móng - sàn - mái vào 1 con số).</li>'
                '<li><b>Diện tích</b>: lấy <b>diện tích sàn tầng 1</b> (m&sup2;), tức mặt bằng tầng trệt.</li>'
                '<li><b>Đơn giá</b>: tra bảng theo <b>diện tích</b> + <b>ô tô vào được hay không</b>.</li>'
                '</ul>'
            )

            + '<h2 style="' + h2 + '">&#129518; HỆ SỐ ĐƯỢC TÍNH RA THẾ NÀO?</h2>'
            '<p style="' + lead + '">Một ngôi nhà gồm 3 phần chi phí: <b>móng</b>, '
            '<b>các sàn (thân nhà)</b> và <b>mái</b>. Hệ số tính nhẩm chính là <b>tổng 3 phần đó</b>, '
            'mỗi phần tính theo % của đơn giá:</p>'

            + _formula(
                'HỆ SỐ = MÓNG% + (SỐ TẦNG &times; 100%) + MÁI%'
            )
            + _why(
                '<p style="margin:0 0 6px;">Lấy ví dụ chuẩn: <b>Miền Bắc, nhà trên 70m&sup2;, '
                '1 tầng, mái bằng, móng đơn</b>:</p>'
                '<ul style="margin:0;">'
                '<li>Móng đơn (Bắc, &gt;70m&sup2;) = <b>30%</b> &rarr; 0,30</li>'
                '<li>1 tầng sàn = <b>100%</b> &rarr; 1,00 (mỗi tầng cộng +1,0)</li>'
                '<li>Mái bằng = <b>20%</b> &rarr; 0,20</li>'
                '</ul>'
                '<p style="margin:8px 0 0;font-weight:800;color:#075985;">'
                '&rarr; Hệ số = 0,30 + 1,00 + 0,20 = <b>1,50</b></p>'
                '<p style="margin:6px 0 0;">Vì thế <b>PHẦN NGUYÊN của hệ số = số tầng</b> '
                '(1 tầng &rarr; 1.xx, 2 tầng &rarr; 2.xx), còn <b>PHẦN LẺ = móng + mái</b>.</p>'
            )
            + _core(
                'HỆ SỐ = <b>Móng% + (Số tầng &times; 100%) + Mái%</b>. '
                'Nhà &gt;70m&sup2;, 1 tầng, mái bằng, móng đơn = <b>1,50</b>.'
            )
        )

    def _p2(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127970; ĐƠN GIÁ XÂY THÔ THEO m&sup2; (đ/m&sup2;)</h2>'
            '<p style="' + lead + '">Đây là phần <b>ĐƠN GIÁ</b> trong công thức. Bảng này '
            '<b>giống nhau ở cả 3 miền</b> &mdash; chỉ phụ thuộc <b>diện tích sàn</b> và '
            '<b>ô tô có vào được hay không</b>.</p>'

            '<table><thead><tr><th style="width:34%;">Diện tích sàn</th>'
            '<th style="text-align:center;">Ô tô VÀO được</th>'
            '<th style="text-align:center;">Ô tô KHÔNG vào</th></tr></thead><tbody>'
            '<tr><td><b>&ge; 75 m&sup2;</b></td><td style="text-align:center;">6.400.000</td><td style="text-align:center;">6.700.000</td></tr>'
            '<tr><td><b>65 - 75 m&sup2;</b></td><td style="text-align:center;">6.600.000</td><td style="text-align:center;">6.900.000</td></tr>'
            '<tr><td><b>50 - 65 m&sup2;</b></td><td style="text-align:center;">6.800.000</td><td style="text-align:center;">7.000.000</td></tr>'
            '<tr><td><b>40 - 50 m&sup2;</b></td><td style="text-align:center;">7.000.000</td><td style="text-align:center;">7.500.000</td></tr>'
            '<tr><td><b>&lt; 40 m&sup2;</b></td><td style="text-align:center;">7.500.000</td><td style="text-align:center;">8.000.000</td></tr>'
            '</tbody></table>'
            '<p style="font-size:13px;color:#64748b;margin:4px 0 0;">Xây thô trọn gói: '
            '<b>5.000.000</b> đ/m&sup2; (nhà &ge;70m&sup2;) / <b>5.200.000</b> đ/m&sup2; (nhà &lt;70m&sup2;).</p>'

            + _why(
                '<ul style="margin:0;">'
                '<li><b>Nhà càng nhỏ, giá mỗi m&sup2; càng cao.</b> Chi phí cố định (huy động máy '
                'móc, đội thợ, lán trại, vận chuyển ban đầu) gần như <b>không đổi</b> dù nhà to hay '
                'nhỏ. Nhà to chia chi phí đó trên nhiều m&sup2; &rarr; rẻ/m&sup2;; nhà nhỏ gánh trên '
                'ít m&sup2; &rarr; đắt/m&sup2;.</li>'
                '<li><b>Ô tô không vào được thì đắt hơn (~+300k/m&sup2;).</b> Vật tư phải '
                '<b>trung chuyển thủ công</b> bằng xe nhỏ hoặc gánh bộ vào ngõ &rarr; tốn thêm công.</li>'
                '</ul>'
            )
            + _core(
                'Gốc <b>6,4 triệu/m&sup2;</b> (nhà &ge;75m&sup2;, ô tô vào). '
                'Nhỏ hơn = đắt hơn; ô tô không vào = đắt hơn ~300k.'
            )
        )

    def _p3(self, h2, h3, lead):
        def tbl(title, rows):
            r = ''
            for nm, vals in rows:
                r += ('<tr><td><b>%s</b></td>' % nm
                      + ''.join('<td style="text-align:center;">%s</td>' % v for v in vals)
                      + '</tr>')
            return (
                '<h3 style="' + h3 + '">' + title + '</h3>'
                '<table><thead><tr><th>Loại móng</th>'
                '<th style="text-align:center;">1T Mái bằng</th>'
                '<th style="text-align:center;">2T Mái bằng</th>'
                '<th style="text-align:center;">1T Mái Nhật<br/>(đổ trần)</th>'
                '<th style="text-align:center;">2T Mái Nhật<br/>(đổ trần)</th>'
                '<th style="text-align:center;">1T Mái Thái<br/>(đổ trần)</th>'
                '</tr></thead><tbody>' + r + '</tbody></table>'
            )
        return (
            '<h2 style="' + h2 + '">&#128207; BẢNG HỆ SỐ TÍNH NHẨM (MIỀN BẮC)</h2>'
            '<p style="' + lead + '">Bảng này suy ra từ công thức <b>Móng% + Số tầng&times;100% + Mái%</b> '
            '(đã cộng sẵn). Chỉ viết Miền Bắc &mdash; Trung/Nam chỉ khác phần % móng (xem bảng báo giá).</p>'

            + tbl('MIỀN BẮC (nhà trên 70m&sup2;)', [
                ('Móng đơn', ['1.50', '2.50', '1.78', '2.78', '1.85']),
                ('Móng băng', ['1.60', '2.60', '1.88', '2.88', '1.95']),
                ('Móng cọc', ['1.60', '2.60', '1.88', '2.88', '1.95']),
            ])

            + _why(
                '<p style="margin:0 0 6px;">Xem cách ra từng con số (móng đơn, đơn giá theo đơn giá):</p>'
                '<ul style="margin:0;">'
                '<li>1T mái bằng = 0,30 + 1,00 + 0,20 = <b>1,50</b></li>'
                '<li>2T mái bằng = 0,30 + 2,00 + 0,20 = <b>2,50</b></li>'
                '<li>1T mái Nhật đổ trần = 0,30 + 1,00 + 0,48 = <b>1,78</b></li>'
                '<li>1T mái Thái đổ trần = 0,30 + 1,00 + 0,55 = <b>1,85</b></li>'
                '</ul>'
                '<p style="margin:8px 0 0;">Móng băng/cọc (40%) thì cộng thêm 0,10 so với móng đơn '
                '(40% &minus; 30% = 10%).</p>'
            )
            + _tip(
                '<ul style="margin:0;">'
                '<li><b>Phần nguyên = số tầng.</b> Cứ thêm 1 tầng thì hệ số <b>+1,0</b>.</li>'
                '<li><b>Phần lẻ = móng + mái.</b> Móng đơn 0,30 &middot; móng băng/cọc 0,40. '
                'Mái bằng 0,20 &middot; Nhật đổ trần 0,48 &middot; Thái đổ trần 0,55.</li>'
                '</ul>'
            )
            + _mistake(
                '<p style="margin:0;"><b>Nhà dưới 70m&sup2;</b> thì phần móng <b>+5%</b> &rarr; '
                'hệ số <b>+0,05</b>. VD móng đơn 1T mái bằng: 1,50 &rarr; <b>1,55</b>.</p>'
            )
            + _core(
                'Móng đơn 1T mái bằng = <b>1,50</b>; mỗi tầng <b>+1,0</b>; '
                'móng băng/cọc <b>+0,10</b>; nhà &lt;70m&sup2; <b>+0,05</b>.'
            )
        )

    def _p4(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#128221; BẢNG BÁO GIÁ CHI TIẾT (3 MIỀN)</h2>'
            '<p style="' + lead + '">Bấm chọn miền để xem bảng % chi tiết. Mỗi hạng mục = '
            '<b>Diện tích &times; % &times; Đơn giá</b>. Phần <b>SÀN</b> và <b>MÁI</b> giống nhau '
            '3 miền; chỉ <b>MÓNG</b> khác nhau (Nam &gt; Trung &gt; Bắc).</p>'

            + self._vd_price_tabs()

            + _why(
                '<ul style="margin:0;">'
                '<li><b>Vì sao "có đổ trần" đắt hơn?</b> Đổ thêm 1 lớp sàn bê tông dưới mái '
                '&rarr; thêm thép, bê tông, cốp pha (Nhật 42% &rarr; 48%, Thái 45% &rarr; 55%).</li>'
                '<li><b>Vì sao móng cọc/băng &gt; móng đơn?</b> Phải khoan/ép cọc hoặc đổ dầm băng '
                'liên tục &rarr; nhiều vật tư và công hơn.</li>'
                '<li><b>Vì sao Nam &gt; Trung &gt; Bắc?</b> Giá nhân công, vật tư, vận chuyển '
                'tăng dần khi vào Nam.</li>'
                '</ul>'
            )
            + _proof(
                '<p style="margin:0;">Bảng tính nhẩm (phần 3) chính là bảng chi tiết này cộng gộp lại. '
                'Tính nhẩm để báo nhanh; bảng chi tiết để bóc tách khi khách hỏi sâu.</p>'
            )
        )

    def _vd_price_tabs(self):
        """Bang bao gia 3 mien voi 3 tab Bac/Trung/Nam (CSS radio, khong can JS).
        SAN va MAI giong nhau; chi MONG khac %."""
        mong = {
            'bac': [('Móng đơn', '30%', '35%'), ('Móng băng', '40%', '45%'),
                    ('Móng cọc', '40%', '45%')],
            'trung': [('Móng đơn', '35%', '40%'), ('Móng băng', '45%', '50%'),
                      ('Móng cọc', '45%', '50%')],
            'nam': [('Móng đơn (cốc)', '40%', '45%'), ('Móng băng', '50%', '55%'),
                    ('Móng cọc', '50%', '55%')],
        }
        notes = {
            'bac': 'Toàn tỉnh: Lai Châu, Sơn La, Điện Biên, Cao Bằng, Bắc Kạn tăng '
                   '300k/m&sup2;. Các huyện của tỉnh Hà Giang, Lạng Sơn tăng 300k.',
            'trung': 'Nhà tân cổ điển nhẹ tăng 400k/m&sup2;, tân cổ điển nặng tăng '
                     '800k/m&sup2; (gửi cấp trên duyệt).',
            'nam': 'Nhà tân cổ điển nhẹ tăng 400k/m&sup2;, tân cổ điển nặng tăng '
                   '800k/m&sup2; (gửi cấp trên duyệt).',
        }

        def san_mai():
            return (
                '<div style="font-weight:900;color:#b45309;margin:10px 0 4px;">SÀN (đ/m&sup2;)</div>'
                '<table><thead><tr><th>Diện tích sàn</th>'
                '<th style="text-align:center;">Ô tô vào</th>'
                '<th style="text-align:center;">Ô tô không vào</th></tr></thead><tbody>'
                '<tr><td><b>&ge; 75 m&sup2;</b></td><td style="text-align:center;">6.400.000</td><td style="text-align:center;">6.700.000</td></tr>'
                '<tr><td><b>65 - 75 m&sup2;</b></td><td style="text-align:center;">6.600.000</td><td style="text-align:center;">6.900.000</td></tr>'
                '<tr><td><b>50 - 65 m&sup2;</b></td><td style="text-align:center;">6.800.000</td><td style="text-align:center;">7.000.000</td></tr>'
                '<tr><td><b>40 - 50 m&sup2;</b></td><td style="text-align:center;">7.000.000</td><td style="text-align:center;">7.500.000</td></tr>'
                '<tr><td><b>&lt; 40 m&sup2;</b></td><td style="text-align:center;">7.500.000</td><td style="text-align:center;">8.000.000</td></tr>'
                '<tr><td><b>Xây thô trọn gói</b></td><td style="text-align:center;">5.000.000 (&ge;70m&sup2;)</td><td style="text-align:center;">5.200.000 (&lt;70m&sup2;)</td></tr>'
                '</tbody></table>'

                '<div style="font-weight:900;color:#b45309;margin:12px 0 4px;">MÁI (DT = diện tích sàn)</div>'
                '<table><thead><tr><th style="width:40%;">Loại mái</th><th>Công thức tính</th></tr></thead><tbody>'
                '<tr><td><b>Mái bằng</b></td><td>DT &times; 20% &times; Đơn giá</td></tr>'
                '<tr><td><b>Mái Nhật</b></td><td>Không đổ trần 42% &middot; <b>Có đổ trần 48%</b></td></tr>'
                '<tr><td><b>Mái Thái</b></td><td>Không đổ trần 45% &middot; <b>Có đổ trần 55%</b></td></tr>'
                '<tr><td><b>Thông tầng</b></td><td>DT &times; 40% &times; Đơn giá</td></tr>'
                '<tr><td><b>Mái trang trí</b></td><td>40% &rarr; 60% &middot; <b>Đổ trần 100%</b></td></tr>'
                '<tr><td><b>Mái tôn</b></td><td>1 mặt 13% &middot; 2 mặt 16% &middot; 3 mặt 20%</td></tr>'
                '</tbody></table>'
            )

        def panel(key):
            rows = ''
            for nm, a, b in mong[key]:
                rows += ('<tr><td><b>' + nm + '</b></td>'
                         '<td style="text-align:center;">DT &times; ' + a + ' &times; Đơn giá</td>'
                         '<td style="text-align:center;">DT &times; ' + b + ' &times; Đơn giá</td></tr>')
            return (
                '<div class="vd_pt_panel vd_pt_' + key + '">'
                '<div style="font-weight:900;color:#b45309;margin:10px 0 4px;">MÓNG</div>'
                '<table><thead><tr><th style="width:34%;">Loại móng</th>'
                '<th style="text-align:center;">Trên 70 m&sup2;</th>'
                '<th style="text-align:center;">Dưới 70 m&sup2;</th></tr></thead><tbody>'
                + rows + '</tbody></table>'
                '<p style="font-size:12.5px;color:#64748b;margin:4px 0 0;">Lưu ý: nhà dưới 70m&sup2; '
                'phần móng đã +5% (cột phải).</p>'
                + san_mai()
                + '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;'
                'padding:8px 12px;margin:10px 0 0;font-size:13px;color:#b91c1c;">'
                '&#128205; ' + notes[key] + '</div>'
                '</div>'
            )

        return (
            '<div class="vd_pt">'
            '<input class="vd_pt_radio" type="radio" name="vd_pt_region" id="vd_pt_bac" checked="checked"/>'
            '<input class="vd_pt_radio" type="radio" name="vd_pt_region" id="vd_pt_trung"/>'
            '<input class="vd_pt_radio" type="radio" name="vd_pt_region" id="vd_pt_nam"/>'
            '<div class="vd_pt_bar">'
            '<label class="vd_pt_tab" for="vd_pt_bac">MIỀN BẮC</label>'
            '<label class="vd_pt_tab" for="vd_pt_trung">MIỀN TRUNG</label>'
            '<label class="vd_pt_tab" for="vd_pt_nam">MIỀN NAM</label>'
            '</div>'
            + panel('bac') + panel('trung') + panel('nam')
            + '</div>'
        )

    def _p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#128208; DIỆN TÍCH NHÂN VỚI TỪNG HỆ SỐ (rất hay sai)</h2>'
            '<p style="' + lead + '">Khi tính nhẩm gộp, ta dùng chung <b>diện tích sàn tầng 1</b> cho '
            'nhanh. Nhưng khi <b>bóc tách chi tiết</b>, móng và mái dùng diện tích KHÁC nhau:</p>'

            '<table><thead><tr><th style="width:30%;">Hệ số</th><th>Diện tích để nhân</th></tr></thead><tbody>'
            '<tr><td><b>Hệ số MÓNG</b></td><td>= <b>diện tích sàn tầng 1</b>, '
            '<b>bao gồm cả bậc tam cấp và sảnh</b> (móng phải đỡ toàn bộ mặt bằng dưới cùng).</td></tr>'
            '<tr><td><b>Hệ số MÁI</b></td><td>= <b>diện tích bê tông mái của tầng 1</b> = '
            '<b>bằng diện tích sàn tầng 2</b> (nếu nhà 2 tầng). KHÔNG tính bậc tam cấp / sảnh ngoài '
            '(mái chỉ phủ phần thân nhà).</td></tr>'
            '<tr><td><b>Hệ số SÀN</b></td><td>Mỗi tầng = diện tích sàn của tầng đó '
            '(tầng trên tính cả ban công đua ra).</td></tr>'
            '</tbody></table>'

            + _why(
                '<p style="margin:0;"><b>Diện tích móng &gt; diện tích mái.</b> Vì móng đỡ cả phần '
                'tam cấp + sảnh ngoài trời, còn mái chỉ đổ bê tông phủ đúng phần thân nhà (bằng sàn '
                'tầng trên). Đó là lý do khi bóc tách, diện tích nhân hệ số mái lấy bằng '
                '<b>diện tích sàn tầng 2</b>, nhỏ hơn diện tích móng.</p>'
            )

            + '<h3 style="' + h3 + '">Tóm tắt cách đo diện tích</h3>'
            '<table><thead><tr><th style="width:28%;">Hạng mục</th><th>Cách tính</th></tr></thead><tbody>'
            '<tr><td><b>Diện tích MÓNG</b></td><td>Bằng diện tích sàn tầng 1 (gồm bậc tam cấp + sảnh).</td></tr>'
            '<tr><td><b>Sàn tầng 1</b></td><td>Tính cả bậc tam cấp.</td></tr>'
            '<tr><td><b>Sàn tầng trên</b></td><td>Tính cả ban công đua ra so với sàn tầng dưới.</td></tr>'
            '<tr><td><b>Mái bằng</b></td><td>Nếu có tum thì tính theo diện tích móng.</td></tr>'
            '<tr><td><b>Mái ngói</b> (Nhật/Thái)</td><td>Tính theo diện tích sàn dưới '
            '(hệ số đã gồm phần đua ra của mái).</td></tr>'
            '</tbody></table>'

            + _apply(
                '<p style="margin:0;">Khi hỏi khách, hỏi rõ: <i>"Mặt bằng tầng 1 dài rộng bao nhiêu '
                'mét ạ?"</i> rồi nhân dài &times; rộng. Tính nhẩm nhanh thì dùng luôn diện tích này; '
                'khi bóc tách chi tiết thì nhớ diện tích mái = sàn tầng trên.</p>'
            )
        )

    def _p6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#10071; CÁC KHOẢN PHÁT SINH (phải nói rõ với khách)</h2>'
            '<p style="' + lead + '">Nhiều khoản <b>KHÔNG nằm trong hợp đồng xây thô</b>. Báo trước '
            'để khách không bất ngờ &mdash; đây cũng là điểm khách hay so sánh giá.</p>'

            '<table><thead><tr><th style="width:42%;">Hạng mục</th><th>Chi phí ước tính</th></tr></thead><tbody>'
            '<tr><td><b>Nhà gác lửng</b></td><td>Tính nhẩm <b>bớt 30 - 50 triệu</b></td></tr>'
            '<tr><td><b>Nhà có tum</b></td><td>Phát sinh <b>120 - 150 triệu</b></td></tr>'
            '<tr><td><b>Ép cọc</b></td><td><b>70 - 150 triệu</b> (ngoài hợp đồng)</td></tr>'
            '<tr><td><b>Thi công nội thất</b></td><td><b>200 - 400 triệu</b> (ngoài hợp đồng)</td></tr>'
            '<tr><td><b>Cấp phép xây dựng</b></td><td><b>10 - 20 triệu</b> (ngoài hợp đồng)</td></tr>'
            '</tbody></table>'

            '<h3 style="' + h3 + '">BẢNG GIÁ PHÁT SINH THEO MẶT BẰNG (nhà 100m&sup2;)</h3>'
            '<table><thead><tr><th style="width:60%;">Tình trạng đường / đất</th><th>Phát sinh</th></tr></thead><tbody>'
            '<tr><td>Đường lớn - có chỗ tập kết</td><td><b>0 đ/m&sup2;</b></td></tr>'
            '<tr><td>Đường lớn - không chỗ tập kết</td><td>200.000 đ/m&sup2;</td></tr>'
            '<tr><td>Ngõ nhỏ - có chỗ tập kết</td><td>250.000 đ/m&sup2;</td></tr>'
            '<tr><td>Ngõ nhỏ - không chỗ tập kết</td><td>350.000 đ/m&sup2;</td></tr>'
            '<tr><td>Có chỗ để đất</td><td><b>0 đ/m&sup2;</b></td></tr>'
            '<tr><td>Không có chỗ để đất + đổ thải + mua đất</td><td>300.000 đ/m&sup2;</td></tr>'
            '<tr><td>Đất yếu - đào sâu - gia cố</td><td>250.000 đ/m&sup2;</td></tr>'
            '</tbody></table>'

            + _tip(
                '<p style="margin:0;">Nhớ nhóm "ngoài hợp đồng" bằng câu: '
                '<b style="color:#7c3aed;">"Cọc - Nội - Phép"</b> (Ép <b>Cọc</b> 70-150, '
                '<b>Nội</b> thất 200-400, Cấp <b>Phép</b> 10-20). '
                'Và <b>Tum +120-150</b>, <b>Lửng bớt 30-50</b>.</p>'
            )
            + _apply(
                '<p style="margin:0;">Khi báo giá, LUÔN nói thêm 1 câu: <i>"Báo giá này là phần xây thô - '
                'hoàn thiện ạ; còn ép cọc, nội thất, cấp phép là khoản riêng em sẽ bóc tách rõ cho anh/chị."</i> '
                '&rarr; khách tin tưởng, không bị hớ khi so giá.</p>'
            )
        )

    def _p7(self, h2, h3, lead):
        def vd(title, scen, steps, total):
            return (
                '<div style="border:1.5px solid #c7d2fe;background:#eef2ff;border-radius:12px;'
                'padding:14px 16px;margin:14px 0;">'
                '<div style="font-weight:900;color:#3730a3;margin-bottom:6px;">' + title + '</div>'
                '<div style="font-style:italic;color:#475569;margin-bottom:8px;">' + scen + '</div>'
                + steps +
                '<div style="margin-top:8px;font-size:17px;font-weight:900;color:#16a34a;">'
                '&rarr; TỔNG &asymp; ' + total + '</div></div>'
            )
        return (
            '<h2 style="' + h2 + '">&#129518; RẤT NHIỀU VÍ DỤ TÍNH MẪU (làm theo từng bước)</h2>'
            '<p style="' + lead + '">3 bước: <b>(1) tính Hệ số = Móng% + Số tầng + Mái% &rarr; '
            '(2) lấy Diện tích sàn tầng 1 &rarr; (3) tra Đơn giá</b>, rồi nhân 3 số.</p>'

            + vd('Ví dụ 1 &mdash; Nhà 1 tầng đơn giản, Miền Bắc',
                 'Miền Bắc, nhà 1 tầng mái bằng, móng đơn, sàn tầng 1 = 100m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,30 (móng đơn) + 1,00 (1 tầng) + 0,20 (mái bằng) = <b>1,50</b></li>'
                 '<li>100 m&sup2; (&ge;75, ô tô vào) &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>1,50 &times; 100 &times; 6.400.000</li></ul>',
                 '960.000.000 đ')

            + vd('Ví dụ 2 &mdash; Nhà phố 2 tầng, Miền Bắc',
                 'Miền Bắc, nhà 2 tầng mái bằng, móng băng, sàn tầng 1 = 80m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,40 (móng băng) + 2,00 (2 tầng) + 0,20 (mái bằng) = <b>2,60</b></li>'
                 '<li>80 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2,60 &times; 80 &times; 6.400.000</li></ul>',
                 '1.331.200.000 đ')

            + vd('Ví dụ 3 &mdash; Nhà 2 tầng mái Nhật, Miền Nam',
                 'Miền Nam, nhà 2 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,50 (móng cọc Nam) + 2,00 + 0,48 (Nhật đổ trần) = <b>2,98</b></li>'
                 '<li>100 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2,98 &times; 100 &times; 6.400.000</li></ul>',
                 '1.907.200.000 đ')

            + vd('Ví dụ 4 &mdash; Nhà to nhưng ô tô KHÔNG vào, Miền Bắc',
                 'Miền Bắc, nhà 2 tầng mái Nhật đổ trần, móng đơn, sàn tầng 1 = 90m&sup2;, ô tô KHÔNG vào.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,30 + 2,00 + 0,48 = <b>2,78</b></li>'
                 '<li>90 m&sup2; (&ge;75) nhưng ô tô không vào &rarr; đơn giá = <b>6.700.000</b></li>'
                 '<li>2,78 &times; 90 &times; 6.700.000</li></ul>',
                 '1.676.340.000 đ')

            + vd('Ví dụ 5 &mdash; Nhà 1 tầng mái Thái, Miền Trung',
                 'Miền Trung, nhà 1 tầng mái Thái đổ trần, móng đơn, sàn tầng 1 = 120m&sup2;, ô tô vào.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,35 (móng đơn Trung) + 1,00 + 0,55 (Thái đổ trần) = <b>1,90</b></li>'
                 '<li>120 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>1,90 &times; 120 &times; 6.400.000</li></ul>',
                 '1.459.200.000 đ')

            + vd('Ví dụ 6 &mdash; Nhà NHỎ dưới 70m&sup2; (móng +5%)',
                 'Miền Nam, nhà 1 tầng mái bằng, móng băng, sàn tầng 1 = 60m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Móng băng Nam dưới 70m&sup2; = 55% &rarr; Hệ số = 0,55 + 1,00 + 0,20 = <b>1,75</b></li>'
                 '<li>60 m&sup2; (50-65, ô tô vào) &rarr; đơn giá = <b>6.800.000</b></li>'
                 '<li>1,75 &times; 60 &times; 6.800.000</li></ul>',
                 '714.000.000 đ')

            + vd('Ví dụ 7 &mdash; Nhà 2 tầng to, Miền Trung',
                 'Miền Trung, nhà 2 tầng mái bằng, móng cọc, sàn tầng 1 = 150m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số = 0,45 (móng cọc Trung) + 2,00 + 0,20 = <b>2,65</b></li>'
                 '<li>150 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2,65 &times; 150 &times; 6.400.000</li></ul>',
                 '2.544.000.000 đ')

            + vd('Ví dụ 8 &mdash; Có thêm phát sinh ngõ nhỏ',
                 'Miền Bắc, nhà 2 tầng mái bằng, móng băng, sàn tầng 1 = 80m&sup2;, ô tô vào, '
                 'NGÕ NHỎ - không chỗ tập kết (350.000 đ/m&sup2;).',
                 '<ul style="margin:0;">'
                 '<li>Xây thô: 2,60 &times; 80 &times; 6.400.000 = <b>1.331.200.000</b></li>'
                 '<li>Phát sinh ngõ nhỏ: 80 &times; 350.000 = <b>28.000.000</b></li>'
                 '<li>Cộng lại: 1.331.200.000 + 28.000.000</li></ul>',
                 '1.359.200.000 đ')

            + _advice(
                '<p style="margin:0;">Khi gọi, vừa nói vừa bấm máy tính: <b>Hệ số &times; Diện tích</b> '
                'trước, rồi <b>&times; Đơn giá</b>. Báo cho khách con số <b>làm tròn</b> '
                '(vd "khoảng 1 tỷ 9") cho gọn và tự tin.</p>'
            )
        )

    def _p8(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127942; KẾT LUẬN PHẢI NHỚ</h2>'
            '<table><thead><tr><th style="width:34%;">Cần nhớ</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Công thức</b></td><td><b>Hệ số &times; Diện tích &times; Đơn giá</b> (Hệ - Diện - Giá)</td></tr>'
            '<tr><td><b>Hệ số</b></td><td><b>Móng% + (Số tầng &times; 100%) + Mái%</b>. Móng đơn 1T mái bằng = 1,50</td></tr>'
            '<tr><td><b>Đơn giá gốc</b></td><td><b>6,4 triệu/m&sup2;</b> (nhà &ge;75m&sup2;, ô tô vào); nhỏ hơn / ô tô không vào thì đắt hơn</td></tr>'
            '<tr><td><b>Móng %</b></td><td>Bắc: đơn 30, băng/cọc 40; Trung +5; Nam +10. Nhà &lt;70m&sup2; +5%</td></tr>'
            '<tr><td><b>Mái %</b></td><td>Bằng 20 &middot; Nhật ĐT 48 &middot; Thái ĐT 55 &middot; Tôn 13/16/20</td></tr>'
            '<tr><td><b>Diện tích</b></td><td>Móng = sàn tầng 1 (gồm tam cấp+sảnh); Mái = sàn tầng 2 (nhà 2 tầng)</td></tr>'
            '<tr><td><b>Ngoài hợp đồng</b></td><td>Cọc (70-150) &middot; Nội thất (200-400) &middot; Cấp phép (10-20); Tum +120-150; Lửng bớt 30-50</td></tr>'
            '</tbody></table>'

            + _core(
                'Thuộc <b>công thức hệ số</b> + <b>mốc đơn giá 6,4 triệu</b> + <b>% móng/mái</b> '
                'là bạn tính nhẩm được tổng tiền cho hầu hết khách ngay trong cuộc gọi.'
            )

            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Công thức hệ số gồm những gì? (Móng% + Số tầng + Mái%)</li>'
            '<li>Nhà &gt;70m&sup2;, 1 tầng, mái bằng, móng đơn = ? (1,50)</li>'
            '<li>Mỗi tầng cộng thêm bao nhiêu vào hệ số? (1,0)</li>'
            '<li>Đơn giá nhà &ge;75m&sup2; ô tô vào? (6,4 triệu)</li>'
            '<li>Nhà &lt;70m&sup2; thì hệ số xử lý sao? (+0,05)</li>'
            '<li>Diện tích nhân hệ số mái lấy theo đâu? (sàn tầng 2 / bê tông mái tầng 1)</li>'
            '<li>3 khoản ngoài hợp đồng? (Cọc - Nội - Phép)</li>'
            '</ol>'

            + _apply(
                '<p style="margin:0 0 6px;"><b>Bài tập áp dụng ngay:</b> lấy 1 khách bạn đang tư vấn, '
                'tự điền: Miền? Số tầng? Kiểu mái? Loại móng? Diện tích sàn tầng 1? Ô tô vào được không? '
                '&rarr; tính hệ số rồi bấm máy ra tổng tiền và đọc thử thành câu báo giá.</p>'
                '<p style="margin:0;">Làm trơn tru 3 khách là bạn đã thuộc bảng giá.</p>'
            )
        )

    # ==================================================================
    #  20 CAU TRAC NGHIEM (ly thuyet)
    # ==================================================================
    def _vd_bg_questions(self):
        T, F = True, False
        return [
            ('Công thức tính nhẩm tổng tiền xây nhà của VINADUY là gì?',
             [('Hệ số × Diện tích sàn tầng 1 × Đơn giá', T),
              ('Diện tích × Số tầng × 1 triệu', F),
              ('Đơn giá × Số phòng', F),
              ('Hệ số + Diện tích + Đơn giá', F)]),

            ('Hệ số được tính ra như thế nào?',
             [('Móng% + (Số tầng × 100%) + Mái%', T),
              ('Chỉ lấy phần móng', F),
              ('Số phòng ngủ + số tầng', F),
              ('Đơn giá chia số tầng', F)]),

            ('Nhà MIỀN BẮC trên 70m², 1 tầng, mái bằng, móng đơn thì hệ số bằng bao nhiêu?',
             [('1,50 (= 30% + 100% + 20%)', T),
              ('1,40', F),
              ('2,50', F),
              ('1,20', F)]),

            ('Mỗi khi tăng thêm 1 tầng thì hệ số thay đổi thế nào?',
             [('Cộng thêm 1,0 (vì mỗi tầng sàn = 100% đơn giá)', T),
              ('Cộng thêm 0,1', F),
              ('Giảm đi một nửa', F),
              ('Không đổi', F)]),

            ('Trong công thức, "Diện tích" (để tính nhẩm nhanh) lấy theo đâu?',
             [('Diện tích sàn tầng 1 (mặt bằng tầng trệt)', T),
              ('Diện tích cả khu đất kể cả sân vườn', F),
              ('Tổng diện tích tất cả các tầng cộng lại', F),
              ('Diện tích mái', F)]),

            ('Diện tích để nhân với hệ số MÓNG được tính thế nào?',
             [('Diện tích sàn tầng 1, GỒM cả bậc tam cấp và sảnh', T),
              ('Chỉ tính trong 4 bức tường', F),
              ('Bằng diện tích mái', F),
              ('Bằng nửa diện tích đất', F)]),

            ('Diện tích để nhân với hệ số MÁI được tính thế nào?',
             [('Bằng diện tích bê tông mái tầng 1 = sàn tầng 2 (nhà 2 tầng)', T),
              ('Bằng diện tích móng gồm tam cấp + sảnh', F),
              ('Bằng diện tích cả khu đất', F),
              ('Bằng tổng diện tích các tầng', F)]),

            ('Vì sao diện tích mái nhỏ hơn diện tích móng?',
             [('Vì mái chỉ phủ phần thân nhà, không gồm tam cấp/sảnh ngoài trời', T),
              ('Vì mái làm bằng vật liệu nhẹ', F),
              ('Vì mái luôn dốc', F),
              ('Thực ra mái lớn hơn móng', F)]),

            ('Đơn giá xây thô cho nhà ≥ 75m² và ô tô VÀO được là bao nhiêu?',
             [('6.400.000 đ/m²', T),
              ('5.000.000 đ/m²', F),
              ('7.500.000 đ/m²', F),
              ('8.000.000 đ/m²', F)]),

            ('Vì sao nhà càng nhỏ thì đơn giá mỗi m² càng cao?',
             [('Vì chi phí cố định chia trên ít m² nên đắt hơn mỗi m²', T),
              ('Vì nhà nhỏ dùng vật tư đắt tiền hơn', F),
              ('Vì nhà nhỏ xây lâu hơn nhà to', F),
              ('Không có lý do, do may rủi', F)]),

            ('Nhà ô tô KHÔNG vào được thì đơn giá thế nào và vì sao?',
             [('Cao hơn ~300k/m² vì phải trung chuyển vật tư thủ công', T),
              ('Thấp hơn vì đỡ tốn xăng', F),
              ('Bằng nhau', F),
              ('Được miễn phí vận chuyển', F)]),

            ('Theo bảng báo giá, móng ĐƠN Miền Bắc (trên 70m²) tính bao nhiêu %?',
             [('30% × Đơn giá', T),
              ('50% × Đơn giá', F),
              ('20% × Đơn giá', F),
              ('100% × Đơn giá', F)]),

            ('Móng băng Miền Nam (trên 70m²) tính bao nhiêu %?',
             [('50% × Đơn giá', T),
              ('30% × Đơn giá', F),
              ('20% × Đơn giá', F),
              ('100% × Đơn giá', F)]),

            ('So với Miền Bắc, % móng của Miền Trung và Miền Nam thế nào?',
             [('Trung cao hơn Bắc 5%, Nam cao hơn Bắc 10%', T),
              ('Cả 3 miền bằng nhau', F),
              ('Bắc cao nhất', F),
              ('Nam thấp nhất', F)]),

            ('Vì sao mái "có đổ trần" đắt hơn "không đổ trần"?',
             [('Vì đổ thêm 1 lớp sàn bê tông nên tốn thép, bê tông, cốp pha', T),
              ('Vì đổ trần dùng ngói đắt hơn', F),
              ('Vì phải thuê thợ giỏi hơn', F),
              ('Thực ra không đắt hơn', F)]),

            ('Mái NHẬT có đổ trần tính bao nhiêu %?',
             [('48% × Đơn giá', T),
              ('20% × Đơn giá', F),
              ('55% × Đơn giá', F),
              ('13% × Đơn giá', F)]),

            ('Mái THÁI có đổ trần tính bao nhiêu %?',
             [('55% × Đơn giá', T),
              ('42% × Đơn giá', F),
              ('20% × Đơn giá', F),
              ('30% × Đơn giá', F)]),

            ('Nhà dưới 70m² thì hệ số xử lý thế nào?',
             [('Phần móng +5% → hệ số +0,05', T),
              ('Giảm đi 0,05', F),
              ('Giữ nguyên', F),
              ('Nhân đôi hệ số', F)]),

            ('Chi phí ÉP CỌC khoảng bao nhiêu và có nằm trong hợp đồng không?',
             [('70 - 150 triệu, KHÔNG nằm trong hợp đồng', T),
              ('10 - 20 triệu, có trong hợp đồng', F),
              ('Miễn phí', F),
              ('500 triệu, có trong hợp đồng', F)]),

            ('Phát sinh mặt bằng "Ngõ nhỏ - không chỗ tập kết" (nhà 100m²) là bao nhiêu?',
             [('350.000 đ/m²', T),
              ('0 đ/m²', F),
              ('1.000.000 đ/m²', F),
              ('50.000 đ/m²', F)]),
        ]

    # ==================================================================
    #  10 CAU TINH TIEN — da tinh lai dung theo he so moi
    # ==================================================================
    def _vd_bg_calc_questions(self):
        T, F = True, False
        return [
            ('TÍNH TIỀN: Miền Bắc, nhà 1 tầng mái bằng, móng đơn, sàn tầng 1 = 100m², '
             'ô tô vào được. (Hệ số = 0,30+1,00+0,20 = 1,50)',
             [('960.000.000 đ', T),
              ('896.000.000 đ', F),
              ('640.000.000 đ', F),
              ('1.500.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 2 tầng mái bằng, móng băng, sàn tầng 1 = 80m², '
             'ô tô vào được. (Hệ số = 0,40+2,00+0,20 = 2,60)',
             [('1.331.200.000 đ', T),
              ('1.280.000.000 đ', F),
              ('1.536.000.000 đ', F),
              ('1.300.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 2 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m², '
             'ô tô vào được. (Hệ số = 0,50+2,00+0,48 = 2,98)',
             [('1.907.200.000 đ', T),
              ('1.843.200.000 đ', F),
              ('1.920.000.000 đ', F),
              ('1.800.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 1 tầng mái Thái đổ trần, móng đơn, sàn tầng 1 = 120m², '
             'ô tô vào được. (Hệ số = 0,35+1,00+0,55 = 1,90)',
             [('1.459.200.000 đ', T),
              ('1.367.040.000 đ', F),
              ('1.440.000.000 đ', F),
              ('1.500.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 2 tầng mái Nhật đổ trần, móng đơn, sàn tầng 1 = 90m², '
             'ô tô KHÔNG vào được. (Hệ số = 0,30+2,00+0,48 = 2,78; đơn giá 6.700.000)',
             [('1.676.340.000 đ', T),
              ('1.616.040.000 đ', F),
              ('1.728.000.000 đ', F),
              ('1.600.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 1 tầng mái bằng, móng băng, sàn tầng 1 = 72m², '
             'ô tô vào được. (Hệ số = 0,50+1,00+0,20 = 1,70; đơn giá 6.600.000)',
             [('807.840.000 đ', T),
              ('760.320.000 đ', F),
              ('792.000.000 đ', F),
              ('720.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 2 tầng mái bằng, móng cọc, sàn tầng 1 = 150m², '
             'ô tô vào được. (Hệ số = 0,45+2,00+0,20 = 2,65)',
             [('2.544.000.000 đ', T),
              ('2.448.000.000 đ', F),
              ('2.400.000.000 đ', F),
              ('2.650.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 1 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m², '
             'ô tô vào được. (Hệ số = 0,40+1,00+0,48 = 1,88)',
             [('1.203.200.000 đ', T),
              ('1.139.200.000 đ', F),
              ('1.280.000.000 đ', F),
              ('1.200.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 2 tầng mái Nhật đổ trần, móng băng, sàn tầng 1 = 85m², '
             'ô tô vào được. (Hệ số = 0,45+2,00+0,48 = 2,93)',
             [('1.593.920.000 đ', T),
              ('1.512.320.000 đ', F),
              ('1.600.000.000 đ', F),
              ('1.500.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 1 tầng mái Thái đổ trần, móng cọc, sàn tầng 1 = 110m², '
             'ô tô KHÔNG vào được. (Hệ số = 0,50+1,00+0,55 = 2,05; đơn giá 6.700.000)',
             [('1.510.850.000 đ', T),
              ('1.422.410.000 đ', F),
              ('1.500.000.000 đ', F),
              ('1.400.000.000 đ', F)]),
        ]
