# -*- coding: utf-8 -*-
"""Seed noi dung + bai thi cho khoa "Don gia xay dung" (course_c1).

Gop 2 tai lieu cong ty: "Don gia.pdf" (bang gia chi tiet 3 mien) + "Tinh nham.pptx"
(he so tinh nham nhanh). Muc tieu: NV moi NHO duoc bang gia va TINH NHAM ra tong
chi phi ngay trong cuoc goi. Co GIAI THICH VI SAO (tai sao tinh nham nhu vay, tai
sao bang gia nhu vay) + RAT NHIEU vi du de hieu.

Bai thi: 20 cau trac nghiem (ly thuyet bang gia) + 10 cau TINH TIEN (cho thong so
-> NV bam may tinh ra tong tien -> chon dap an so tien dung -> tu cham).

Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lai.
"""
from odoo import api, models

from .seed_kh_tiem_nang import (_WRAP, _box, _formula, _apply, _situation,
                                _advice, _proof, _mistake)

_BG_VERSION = 'v2'
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
            ('3. He so tinh nham 3 mien', self._p3(h2, h3, lead)),
            ('4. Bang gia chi tiet', self._p4(h2, h3, lead)),
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
                '<li><b>Hệ số</b>: tra bảng theo <b>Miền + Số tầng + Kiểu mái + Loại móng</b> '
                '(đã gộp sẵn móng - sàn - mái vào 1 con số).</li>'
                '<li><b>Diện tích</b>: lấy <b>diện tích sàn tầng 1</b> (m&sup2;), tức mặt bằng tầng trệt.</li>'
                '<li><b>Đơn giá</b>: tra bảng theo <b>diện tích</b> + <b>ô tô vào được hay không</b>.</li>'
                '</ul>'
            )

            + '<h2 style="' + h2 + '">&#129518; VÌ SAO CHỈ CẦN 1 CON SỐ "HỆ SỐ"?</h2>'
            '<p style="' + lead + '">Một ngôi nhà gồm 3 phần chi phí chính: <b>móng</b>, '
            '<b>các sàn (thân nhà)</b> và <b>mái</b>. Bảng chi tiết tính riêng từng phần rồi cộng '
            'lại. "Hệ số tính nhẩm" chỉ là <b>tổng 3 phần đó gộp sẵn</b> thành 1 số, để bạn không '
            'phải cộng lại khi đang gọi.</p>'

            + _why(
                '<p style="margin:0 0 6px;">Hệ số được dựng từ 3 mảnh, mỗi mảnh là <b>% của đơn giá</b>:</p>'
                '<ul style="margin:0;">'
                '<li><b>Mỗi tầng sàn &asymp; 1,0</b> (tức 100% đơn giá cho mỗi sàn). '
                'Vì thế <b>PHẦN NGUYÊN của hệ số = số tầng</b>: nhà 1 tầng bắt đầu bằng <b>1.xx</b>, '
                'nhà 2 tầng <b>2.xx</b>, cứ thêm 1 tầng thì hệ số <b>+1,0</b>.</li>'
                '<li><b>Móng + Mái</b> nằm ở <b>PHẦN LẺ</b> (.xx). Móng to (cọc, băng) và mái dốc '
                '(Nhật, Thái, đổ trần) thì phần lẻ lớn; móng đơn + mái bằng thì phần lẻ nhỏ.</li>'
                '</ul>'
                '<p style="margin:8px 0 0;">Ví dụ đọc ngược con số <b>2.50</b> (Bắc, móng băng, 2 tầng '
                'mái bằng): số <b>2</b> = 2 tầng sàn; phần lẻ <b>.50</b> = móng băng + mái bằng cộng lại. '
                'Hiểu vậy là bạn nhìn con số biết ngay nhà mấy tầng, móng - mái loại gì.</p>'
            )
            + _core(
                'TỔNG = <b>HỆ SỐ &times; DIỆN TÍCH &times; ĐƠN GIÁ</b>. '
                'Hệ số = Móng + (số tầng &times; 1,0) + Mái &mdash; công ty đã gộp sẵn vào bảng.'
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
                '<li><b>Ô tô không vào được thì đắt hơn (~+300k/m&sup2;).</b> Vật tư (cát, đá, gạch, '
                'xi măng, thép) phải <b>trung chuyển thủ công</b> bằng xe nhỏ hoặc gánh bộ vào ngõ '
                '&rarr; tốn thêm công và thời gian.</li>'
                '</ul>'
            )
            + _tip(
                '<p style="margin:0;">Mốc gốc cần thuộc: nhà to (&ge;75m&sup2;), ô tô vào được = '
                '<b>6,4 triệu/m&sup2;</b>. Từ đó:</p>'
                '<ul style="margin:8px 0 0;">'
                '<li>Nhà <b>nhỏ dần</b> mỗi bậc &rarr; <b>tăng ~200k</b> (6,4 &rarr; 6,6 &rarr; 6,8 &rarr; 7,0 &rarr; 7,5).</li>'
                '<li><b>Ô tô không vào</b> &rarr; <b>+300k</b> so với ô tô vào (ở các nhà to).</li>'
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
            '<h2 style="' + h2 + '">&#128207; BẢNG HỆ SỐ TÍNH NHẨM (3 MIỀN)</h2>'
            '<p style="' + lead + '">Đây là phần <b>HỆ SỐ</b> trong công thức &mdash; tra theo '
            '<b>Miền &rarr; Loại móng &rarr; Số tầng &amp; kiểu mái</b>. Hệ số đã '
            '<b>gộp sẵn móng + sàn các tầng + mái</b> vào 1 con số.</p>'

            + tbl('MIỀN BẮC', [
                ('Móng cốc', ['1.40', '2.40', '1.68', '2.68', '1.31']),
                ('Móng băng', ['1.50', '2.50', '1.78', '2.78', '1.41']),
                ('Móng cọc', ['1.50', '2.50', '1.78', '2.78', '1.41']),
            ])
            + tbl('MIỀN TRUNG', [
                ('Móng cốc', ['1.45', '2.45', '1.73', '2.73', '1.78']),
                ('Móng băng', ['1.55', '2.55', '1.78', '2.78', '1.88']),
                ('Móng cọc', ['1.55', '2.55', '1.78', '2.78', '1.88']),
            ])
            + tbl('MIỀN NAM', [
                ('Móng cốc', ['1.50', '2.50', '1.78', '2.78', '1.83']),
                ('Móng băng', ['1.60', '2.60', '1.88', '2.88', '1.93']),
                ('Móng cọc', ['1.60', '2.60', '1.88', '2.88', '1.93']),
            ])

            + _why(
                '<ul style="margin:0;">'
                '<li><b>Vì sao phần nguyên = số tầng?</b> Mỗi tầng sàn tốn ~100% đơn giá &rarr; '
                'mỗi tầng cộng +1,0. Nhìn cột "1T" toàn 1.xx, cột "2T" toàn 2.xx, hơn kém nhau '
                'đúng 1,0.</li>'
                '<li><b>Vì sao phần lẻ khác nhau?</b> Phần lẻ = móng + mái. Móng cọc/băng nhiều bê '
                'tông &amp; thép hơn móng đơn; mái Nhật/Thái/đổ trần nhiều vật tư hơn mái bằng &rarr; '
                'phần lẻ lớn hơn.</li>'
                '<li><b>Vì sao Nam &gt; Trung &gt; Bắc?</b> Giá nhân công, vật tư và vận chuyển tăng '
                'dần khi vào Nam. Cùng một ngôi nhà, hệ số miền Nam nhỉnh hơn miền Bắc một chút.</li>'
                '</ul>'
            )
            + _tip(
                '<ul style="margin:0;">'
                '<li><b>Phần nguyên = số tầng.</b> Nhà 1 tầng hệ số <b>1.xx</b>, nhà 2 tầng <b>2.xx</b>. '
                'Cứ thêm 1 tầng thì hệ số <b>+1,0</b>.</li>'
                '<li><b>Phần lẻ = móng + mái.</b> Mái bằng phần lẻ nhỏ (~.40-.60), mái Nhật/Thái lớn hơn.</li>'
                '<li><b>Đắt dần theo miền: NAM &gt; TRUNG &gt; BẮC.</b></li>'
                '</ul>'
            )
            + _mistake(
                '<p style="margin:0;"><b>Diện tích &lt; 70 m&sup2;</b> thì <b>cộng thêm ~0,05</b> vào hệ số '
                '(vì móng nhà nhỏ cộng thêm 5%). VD móng cốc Bắc 2T mái bằng 2.40 &rarr; nhà &lt;70m&sup2; '
                'lấy <b>2.45</b>. Đừng quên khi khách xây nhà nhỏ.</p>'
            )
            + _core(
                'Phần nguyên = <b>số tầng</b>; phần lẻ = <b>móng + mái</b>. '
                'Đắt dần: <b>Nam &gt; Trung &gt; Bắc</b>. Nhà &lt;70m&sup2; cộng ~0,05 hệ số.'
            )
        )

    def _p4(self, h2, h3, lead):
        def mong_tbl(title, rows):
            r = ''
            for nm, a, b in rows:
                r += ('<tr><td><b>%s</b></td>'
                      '<td style="text-align:center;">%s</td>'
                      '<td style="text-align:center;">%s</td></tr>' % (nm, a, b))
            return (
                '<h3 style="' + h3 + '">' + title + '</h3>'
                '<table><thead><tr><th style="width:34%;">Loại móng</th>'
                '<th style="text-align:center;">Trên 70 m&sup2;</th>'
                '<th style="text-align:center;">Dưới 70 m&sup2;</th>'
                '</tr></thead><tbody>' + r + '</tbody></table>'
            )
        return (
            '<h2 style="' + h2 + '">&#128221; BẢNG GIÁ CHI TIẾT (cách bóc tách)</h2>'
            '<p style="' + lead + '">Khi cần giải thích cho khách <b>vì sao ra con số đó</b>, dùng '
            'bảng % chi tiết: mỗi hạng mục = <b>Diện tích &times; % &times; Đơn giá</b>, rồi cộng lại. '
            'Đây chính là "bản gốc" mà hệ số tính nhẩm được rút ra.</p>'

            '<h3 style="' + h3 + '">PHẦN MÓNG (% theo diện tích sàn)</h3>'
            + mong_tbl('Miền Bắc', [
                ('Móng đơn / cốc', '30%', '35%'),
                ('Móng băng', '40%', '45%'),
                ('Móng cọc', '40%', '45%'),
            ])
            + mong_tbl('Miền Trung', [
                ('Móng đơn / cốc', '35%', '40%'),
                ('Móng băng', '45%', '50%'),
                ('Móng cọc', '45%', '50%'),
            ])
            + mong_tbl('Miền Nam', [
                ('Móng đơn / cốc', '40%', '45%'),
                ('Móng băng', '50%', '55%'),
                ('Móng cọc', '50%', '55%'),
            ])
            + '<p style="font-size:13px;color:#64748b;margin:4px 0 0;">Cột "Dưới 70m&sup2;" đã '
            'cộng sẵn +5% so với "Trên 70m&sup2;" (nhà nhỏ móng tốn hơn).</p>'

            '<h3 style="' + h3 + '">PHẦN MÁI (% theo diện tích)</h3>'
            '<table><thead><tr><th style="width:42%;">Loại mái</th><th>Hệ số % &times; Đơn giá</th></tr></thead><tbody>'
            '<tr><td><b>Mái bằng</b></td><td>20%</td></tr>'
            '<tr><td><b>Mái Nhật</b></td><td>Không đổ trần 42% &middot; <b>Có đổ trần 48%</b></td></tr>'
            '<tr><td><b>Mái Thái</b></td><td>Không đổ trần 45% &middot; <b>Có đổ trần 55%</b></td></tr>'
            '<tr><td><b>Thông tầng</b></td><td>40%</td></tr>'
            '<tr><td><b>Mái trang trí</b></td><td>40% &rarr; 60% &middot; <b>Đổ trần 100%</b></td></tr>'
            '<tr><td><b>Mái tôn</b></td><td>1 mặt 13% &middot; 2 mặt 16% &middot; 3 mặt 20%</td></tr>'
            '</tbody></table>'

            + _why(
                '<ul style="margin:0;">'
                '<li><b>Vì sao có đổ trần đắt hơn?</b> "Đổ trần" là đổ thêm 1 lớp sàn bê tông dưới '
                'mái &rarr; thêm thép, bê tông, cốp pha &rarr; % cao hơn (Nhật 42% &rarr; 48%, '
                'Thái 45% &rarr; 55%).</li>'
                '<li><b>Vì sao mái Thái &gt; mái Nhật?</b> Mái Thái dốc hơn, nhiều diện tích lợp và '
                'kết cấu đỡ mái hơn.</li>'
                '<li><b>Vì sao móng cọc/băng &gt; móng đơn?</b> Phải khoan/ép cọc hoặc đổ dầm băng '
                'liên tục &rarr; nhiều vật tư và công hơn móng đơn từng điểm.</li>'
                '</ul>'
            )
            + _tip(
                '<p style="margin:0;">Mái: <b>Bằng 20 &mdash; Nhật 42/48 &mdash; Thái 45/55 &mdash; '
                'Tôn 13/16/20</b>. Mái Thái luôn đắt hơn mái Nhật; có đổ trần luôn đắt hơn không đổ trần.</p>'
            )
            + _proof(
                '<p style="margin:0;">Bảng tính nhẩm (phần 3) và bảng chi tiết (phần 4) cho ra <b>kết quả '
                'gần như nhau</b>. Tính nhẩm để báo nhanh; bảng chi tiết để bóc tách khi khách hỏi sâu.</p>'
            )
            + _mistake(
                '<p style="margin:0;">Nhà <b>tân cổ điển</b> cộng thêm: nhẹ <b>+400k/m&sup2;</b>, '
                'nặng <b>+800k/m&sup2;</b> &mdash; phải <b>gửi cấp trên duyệt</b> trước khi báo. '
                'Một số tỉnh miền núi (Lai Châu, Sơn La, Điện Biên, Cao Bằng, Bắc Kạn; các huyện '
                'Hà Giang, Lạng Sơn) <b>+300k/m&sup2;</b>.</p>'
            )
        )

    def _p5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#128208; CÁCH TÍNH DIỆN TÍCH (rất hay sai)</h2>'
            '<p style="' + lead + '">Công thức dùng <b>diện tích sàn tầng 1</b>. Tính sai diện tích '
            'là sai cả tổng tiền, nên phải nắm chắc 3 phần: móng - sàn - mái.</p>'

            '<table><thead><tr><th style="width:28%;">Hạng mục</th><th>Cách tính</th></tr></thead><tbody>'
            '<tr><td><b>Diện tích MÓNG</b></td><td>Bằng <b>diện tích sàn tầng 1</b>.</td></tr>'
            '<tr><td><b>Diện tích SÀN tầng 1</b></td><td>Phải tính <b>cả bậc tam cấp</b> (bậc thềm trước nhà).</td></tr>'
            '<tr><td><b>Diện tích SÀN tầng trên</b></td><td>Tính cả phần <b>ban công đua ra</b> so với sàn tầng dưới.</td></tr>'
            '<tr><td><b>Mái BẰNG</b></td><td>Nếu <b>có tum</b> thì tính theo <b>diện tích móng</b>.</td></tr>'
            '<tr><td><b>Mái NGÓI</b> (Nhật/Thái)</td><td>Tính theo <b>diện tích sàn dưới</b> '
            '(hệ số đã bao gồm phần đua ra của mái).</td></tr>'
            '</tbody></table>'

            + _why(
                '<p style="margin:0;">Lấy <b>sàn tầng 1</b> làm gốc vì móng đỡ đúng mặt bằng tầng 1, '
                'và các tầng trên thường lặp lại mặt bằng đó &rarr; chỉ cần 1 con số diện tích là '
                'tính được cả nhà (số tầng đã nằm trong hệ số). Ban công và bậc tam cấp vẫn tốn vật '
                'tư nên phải cộng vào.</p>'
            )
            + _apply(
                '<p style="margin:0;">Khi hỏi khách diện tích, hỏi rõ: <i>"Mặt bằng tầng 1 nhà mình '
                'dài rộng bao nhiêu mét ạ?"</i> rồi nhân dài &times; rộng. Đừng quên cộng bậc tam cấp '
                'và ban công các tầng trên khi chốt số.</p>'
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

            + _why(
                '<p style="margin:0;">Phát sinh đều xoay quanh <b>vận chuyển vật tư</b> và <b>xử lý '
                'đất/thải</b>: ngõ nhỏ, không chỗ tập kết, đất yếu... đều khiến đội thi công tốn thêm '
                'công và máy. Đó là lý do tính theo <b>đ/m&sup2;</b> chứ không phải một con số cố định.</p>'
            )
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
            '<p style="' + lead + '">Cứ làm đúng 3 bước: <b>(1) tra Hệ số &rarr; (2) lấy Diện tích '
            'sàn tầng 1 &rarr; (3) tra Đơn giá</b>, rồi nhân 3 số lại.</p>'

            + vd('Ví dụ 1 &mdash; Nhà 1 tầng đơn giản, Miền Bắc',
                 'Miền Bắc, nhà 1 tầng mái bằng, móng cốc, sàn tầng 1 = 100m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Bắc, móng cốc, 1T mái bằng) = <b>1.40</b></li>'
                 '<li>100 m&sup2; (&ge;75, ô tô vào) &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>1.40 &times; 100 &times; 6.400.000</li></ul>',
                 '896.000.000 đ')

            + vd('Ví dụ 2 &mdash; Nhà phố 2 tầng, Miền Bắc',
                 'Miền Bắc, nhà 2 tầng mái bằng, móng băng, sàn tầng 1 = 80m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Bắc, móng băng, 2T mái bằng) = <b>2.50</b></li>'
                 '<li>80 m&sup2; (&ge;75, ô tô vào) &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2.50 &times; 80 &times; 6.400.000</li></ul>',
                 '1.280.000.000 đ')

            + vd('Ví dụ 3 &mdash; Nhà vườn 2 tầng mái Nhật, Miền Nam',
                 'Miền Nam, nhà 2 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Nam, móng cọc, 2T mái Nhật) = <b>2.88</b></li>'
                 '<li>100 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2.88 &times; 100 &times; 6.400.000</li></ul>',
                 '1.843.200.000 đ')

            + vd('Ví dụ 4 &mdash; Nhà to nhưng ô tô KHÔNG vào, Miền Bắc',
                 'Miền Bắc, nhà 2 tầng mái Nhật đổ trần, móng cốc, sàn tầng 1 = 90m&sup2;, ô tô KHÔNG vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Bắc, móng cốc, 2T mái Nhật) = <b>2.68</b></li>'
                 '<li>90 m&sup2; (&ge;75) nhưng ô tô không vào &rarr; đơn giá = <b>6.700.000</b></li>'
                 '<li>2.68 &times; 90 &times; 6.700.000</li></ul>',
                 '1.616.040.000 đ')

            + vd('Ví dụ 5 &mdash; Nhà 1 tầng mái Thái, Miền Trung',
                 'Miền Trung, nhà 1 tầng mái Thái đổ trần, móng cốc, sàn tầng 1 = 120m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Trung, móng cốc, 1T mái Thái) = <b>1.78</b></li>'
                 '<li>120 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>1.78 &times; 120 &times; 6.400.000</li></ul>',
                 '1.367.040.000 đ')

            + vd('Ví dụ 6 &mdash; Nhà NHỎ dưới 70m&sup2; (nhớ +0,05 hệ số)',
                 'Miền Nam, nhà 1 tầng mái bằng, móng băng, sàn tầng 1 = 60m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số gốc (Nam, móng băng, 1T mái bằng) = 1.60; nhà &lt;70m&sup2; &rarr; '
                 '<b>1.60 + 0.05 = 1.65</b></li>'
                 '<li>60 m&sup2; (khoảng 50-65, ô tô vào) &rarr; đơn giá = <b>6.800.000</b></li>'
                 '<li>1.65 &times; 60 &times; 6.800.000</li></ul>',
                 '673.200.000 đ')

            + vd('Ví dụ 7 &mdash; Nhà 2 tầng to, Miền Trung',
                 'Miền Trung, nhà 2 tầng mái bằng, móng cọc, sàn tầng 1 = 150m&sup2;, ô tô vào được.',
                 '<ul style="margin:0;">'
                 '<li>Hệ số (Trung, móng cọc, 2T mái bằng) = <b>2.55</b></li>'
                 '<li>150 m&sup2; &rarr; đơn giá = <b>6.400.000</b></li>'
                 '<li>2.55 &times; 150 &times; 6.400.000</li></ul>',
                 '2.448.000.000 đ')

            + vd('Ví dụ 8 &mdash; Có thêm phát sinh ngõ nhỏ',
                 'Miền Bắc, nhà 2 tầng mái bằng, móng băng, sàn tầng 1 = 80m&sup2;, ô tô vào được, '
                 'nhưng NGÕ NHỎ - không chỗ tập kết (350.000 đ/m&sup2;).',
                 '<ul style="margin:0;">'
                 '<li>Xây thô: 2.50 &times; 80 &times; 6.400.000 = <b>1.280.000.000</b></li>'
                 '<li>Phát sinh ngõ nhỏ: 80 &times; 350.000 = <b>28.000.000</b></li>'
                 '<li>Cộng lại: 1.280.000.000 + 28.000.000</li></ul>',
                 '1.308.000.000 đ')

            + _advice(
                '<p style="margin:0;">Khi gọi, vừa nói chuyện vừa bấm máy tính: <b>Hệ số &times; Diện tích</b> '
                'trước (ra một số tròn), rồi <b>&times; Đơn giá</b>. Báo cho khách con số <b>làm tròn</b> '
                '(vd "khoảng 1 tỷ 8") để nghe gọn và tự tin.</p>'
            )
        )

    def _p8(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">&#127942; KẾT LUẬN PHẢI NHỚ</h2>'
            '<table><thead><tr><th style="width:34%;">Cần nhớ</th><th>Nội dung</th></tr></thead><tbody>'
            '<tr><td><b>Công thức</b></td><td><b>Hệ số &times; Diện tích &times; Đơn giá</b> (Hệ - Diện - Giá)</td></tr>'
            '<tr><td><b>Hệ số được dựng từ</b></td><td>Móng + (số tầng &times; 1,0) + Mái &mdash; gộp sẵn trong bảng</td></tr>'
            '<tr><td><b>Đơn giá gốc</b></td><td><b>6,4 triệu/m&sup2;</b> (nhà &ge;75m&sup2;, ô tô vào); nhỏ hơn / ô tô không vào thì đắt hơn</td></tr>'
            '<tr><td><b>Hệ số</b></td><td>Phần nguyên = số tầng; Nam &gt; Trung &gt; Bắc; nhà &lt;70m&sup2; +0,05</td></tr>'
            '<tr><td><b>Diện tích</b></td><td>Lấy sàn tầng 1; cộng cả bậc tam cấp + ban công đua ra</td></tr>'
            '<tr><td><b>Ngoài hợp đồng</b></td><td>Cọc (70-150) &middot; Nội thất (200-400) &middot; Cấp phép (10-20); Tum +120-150; Lửng bớt 30-50</td></tr>'
            '</tbody></table>'

            + _core(
                'Thuộc <b>1 công thức</b> + <b>mốc đơn giá 6,4 triệu</b> + <b>bảng hệ số</b> '
                'là bạn tính nhẩm được tổng tiền cho hầu hết khách ngay trong cuộc gọi.'
            )

            + '<h2 style="' + h2 + '">&#128221; Tự kiểm tra trước khi thi</h2>'
            '<ol>'
            '<li>Đọc lại công thức 3 chữ. (Hệ - Diện - Giá)</li>'
            '<li>Hệ số được dựng từ những phần nào? (Móng + số tầng + Mái)</li>'
            '<li>Đơn giá nhà &ge;75m&sup2; ô tô vào là bao nhiêu? (6,4 triệu)</li>'
            '<li>Ô tô không vào thì cộng thêm bao nhiêu? (~300k)</li>'
            '<li>Nhà 2 tầng hệ số bắt đầu bằng số mấy? (2.xx)</li>'
            '<li>Miền nào đắt nhất? (Miền Nam)</li>'
            '<li>Nhà &lt;70m&sup2; thì hệ số xử lý sao? (+0,05)</li>'
            '<li>3 khoản ngoài hợp đồng? (Cọc - Nội - Phép)</li>'
            '</ol>'

            + _apply(
                '<p style="margin:0 0 6px;"><b>Bài tập áp dụng ngay:</b> lấy 1 khách bạn đang tư vấn, '
                'tự điền: Miền? Số tầng? Kiểu mái? Loại móng? Diện tích sàn tầng 1? Ô tô vào được không? '
                '&rarr; bấm máy tính ra tổng tiền và đọc thử thành câu báo giá.</p>'
                '<p style="margin:0;">Làm được trơn tru 3 khách là bạn đã thuộc bảng giá.</p>'
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

            ('Trong công thức, "Diện tích" lấy theo đâu?',
             [('Diện tích sàn tầng 1 (mặt bằng tầng trệt)', T),
              ('Diện tích cả khu đất kể cả sân vườn', F),
              ('Tổng diện tích tất cả các tầng cộng lại', F),
              ('Diện tích mái', F)]),

            ('Hệ số tính nhẩm được gộp từ những phần chi phí nào?',
             [('Móng + các sàn (mỗi tầng ~1,0) + Mái', T),
              ('Chỉ phần móng', F),
              ('Số phòng ngủ + số tầng', F),
              ('Tiền nhân công một ngày', F)]),

            ('Vì sao PHẦN NGUYÊN của hệ số bằng số tầng?',
             [('Vì mỗi tầng sàn tốn khoảng 100% đơn giá nên cộng +1,0 mỗi tầng', T),
              ('Vì quy định nhà nước', F),
              ('Vì số tầng bằng số phòng', F),
              ('Đó chỉ là con số ngẫu nhiên', F)]),

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

            ('Đơn giá cho nhà diện tích < 40m², ô tô KHÔNG vào được?',
             [('8.000.000 đ/m²', T),
              ('6.400.000 đ/m²', F),
              ('5.200.000 đ/m²', F),
              ('7.000.000 đ/m²', F)]),

            ('Mỗi khi tăng thêm 1 tầng thì hệ số tính nhẩm thay đổi thế nào?',
             [('Cộng thêm khoảng 1,0', T),
              ('Cộng thêm 0,1', F),
              ('Giảm đi một nửa', F),
              ('Không đổi', F)]),

            ('Thứ tự đắt dần giữa 3 miền (cùng điều kiện) là?',
             [('Nam > Trung > Bắc', T),
              ('Bắc > Trung > Nam', F),
              ('Trung > Nam > Bắc', F),
              ('Ba miền giá bằng nhau', F)]),

            ('Nhà có diện tích sàn < 70m² thì hệ số tính nhẩm xử lý thế nào?',
             [('Cộng thêm khoảng 0,05 vào hệ số (móng nhà nhỏ +5%)', T),
              ('Giảm đi 0,05', F),
              ('Giữ nguyên', F),
              ('Nhân đôi hệ số', F)]),

            ('Theo bảng giá chi tiết, móng ĐƠN (cốc) Miền Bắc (trên 70m²) tính bao nhiêu %?',
             [('30% × Đơn giá', T),
              ('50% × Đơn giá', F),
              ('20% × Đơn giá', F),
              ('100% × Đơn giá', F)]),

            ('Móng băng Miền Nam (trên 70m²) tính bao nhiêu %?',
             [('50% × Đơn giá', T),
              ('30% × Đơn giá', F),
              ('20% × Đơn giá', F),
              ('100% × Đơn giá', F)]),

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

            ('Mái tôn 1 mặt / 2 mặt / 3 mặt tính lần lượt bao nhiêu %?',
             [('13% / 16% / 20%', T),
              ('20% / 40% / 60%', F),
              ('10% / 20% / 30%', F),
              ('42% / 48% / 55%', F)]),

            ('Diện tích sàn tầng 1 phải tính thêm phần nào?',
             [('Cả bậc tam cấp (và ban công đua ra ở tầng trên)', T),
              ('Chỉ tính trong 4 bức tường', F),
              ('Trừ đi phần cầu thang', F),
              ('Cộng cả sân vườn', F)]),

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
    #  10 CAU TINH TIEN — NV bam may tinh ra tong tien, chon so dung
    # ==================================================================
    def _vd_bg_calc_questions(self):
        T, F = True, False
        return [
            ('TÍNH TIỀN: Miền Bắc, nhà 1 tầng mái bằng, móng cốc, diện tích sàn tầng 1 = 100m², '
             'ô tô vào được. Tổng tiền tạm tính? (Gợi ý: hệ số 1.40)',
             [('896.000.000 đ', T),
              ('640.000.000 đ', F),
              ('1.344.000.000 đ', F),
              ('1.536.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 2 tầng mái bằng, móng băng, diện tích sàn tầng 1 = 80m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 2.50)',
             [('1.280.000.000 đ', T),
              ('768.000.000 đ', F),
              ('1.600.000.000 đ', F),
              ('1.340.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 2 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 2.88)',
             [('1.843.200.000 đ', T),
              ('1.203.200.000 đ', F),
              ('1.920.000.000 đ', F),
              ('1.728.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 1 tầng mái Thái đổ trần, móng cốc, sàn tầng 1 = 120m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 1.78)',
             [('1.367.040.000 đ', T),
              ('1.328.640.000 đ', F),
              ('1.440.000.000 đ', F),
              ('1.536.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 2 tầng mái Nhật đổ trần, móng cốc, sàn tầng 1 = 90m², '
             'ô tô KHÔNG vào được. Tổng tiền tạm tính? (hệ số 2.68, đơn giá 6.700.000)',
             [('1.616.040.000 đ', T),
              ('1.543.680.000 đ', F),
              ('1.728.000.000 đ', F),
              ('1.500.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 1 tầng mái bằng, móng băng, sàn tầng 1 = 72m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 1.60, đơn giá 6.600.000)',
             [('760.320.000 đ', T),
              ('737.280.000 đ', F),
              ('691.200.000 đ', F),
              ('792.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 2 tầng mái bằng, móng cọc, sàn tầng 1 = 150m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 2.55)',
             [('2.448.000.000 đ', T),
              ('1.468.800.000 đ', F),
              ('2.400.000.000 đ', F),
              ('2.550.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Bắc, nhà 1 tầng mái Nhật đổ trần, móng cọc, sàn tầng 1 = 100m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 1.78)',
             [('1.139.200.000 đ', T),
              ('1.075.200.000 đ', F),
              ('1.712.000.000 đ', F),
              ('1.000.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Trung, nhà 2 tầng mái Nhật đổ trần, móng băng, sàn tầng 1 = 85m², '
             'ô tô vào được. Tổng tiền tạm tính? (hệ số 2.78)',
             [('1.512.320.000 đ', T),
              ('968.320.000 đ', F),
              ('1.600.000.000 đ', F),
              ('1.452.000.000 đ', F)]),

            ('TÍNH TIỀN: Miền Nam, nhà 1 tầng mái Thái đổ trần, móng cọc, sàn tầng 1 = 110m², '
             'ô tô KHÔNG vào được. Tổng tiền tạm tính? (hệ số 1.93, đơn giá 6.700.000)',
             [('1.422.410.000 đ', T),
              ('1.358.720.000 đ', F),
              ('1.500.000.000 đ', F),
              ('1.272.810.000 đ', F)]),
        ]
