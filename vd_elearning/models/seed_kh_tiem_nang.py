# -*- coding: utf-8 -*-
"""Seed noi dung + 20 cau hoi thi cho khoa hoc
"Ky nang nhan dien khach hang tiem nang trong xay nha tron goi".

Thiet ke chuyen nghiep: bang so sanh, icon, khung cong thuc, tinh huong,
loi khuyen, chung minh, va o "AP DUNG NGAY" ep nhan vien thuc hanh.
Giu DAY DU noi dung goc, chi viet THEM (khong cat bot).

Idempotent: neu khoa da co noi dung article thi BO QUA (tranh ghi de sua tay
cua admin + tranh nhan ban khi nang cap lai). HTML luu o slide.slide.vd_body
(sanitize=False) nen giu nguyen bang/style inline.
"""
from odoo import api, models

# ------- Cac khung (callout) dung lai - style inline vi SCSS khong phu -------
_WRAP = (
    'font-size:15px;line-height:1.65;color:#2b2f44;'
    'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
)


def _box(border, bg, icon, title, inner):
    return (
        '<div style="border-left:6px solid %s;background:%s;border-radius:10px;'
        'padding:14px 16px;margin:16px 0;">'
        '<div style="font-weight:800;color:%s;margin-bottom:6px;font-size:14px;'
        'text-transform:uppercase;letter-spacing:.3px;">%s %s</div>'
        '<div>%s</div></div>'
    ) % (border, bg, border, icon, title, inner)


def _formula(inner):
    return (
        '<div style="border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
        'padding:18px 20px;margin:18px 0;text-align:center;">'
        '<div style="font-weight:900;color:#92600a;font-size:15px;margin-bottom:10px;'
        'text-transform:uppercase;letter-spacing:.5px;">CONG THUC PHAI THUOC LONG</div>'
        '<div style="font-size:17px;font-weight:800;color:#3a2c05;">%s</div></div>'
    ) % inner


def _apply(inner):
    return (
        '<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;'
        'padding:16px 18px;margin:18px 0;">'
        '<div style="font-weight:900;color:#b91c1c;font-size:15px;margin-bottom:8px;">'
        'BAT BUOC AP DUNG NGAY (cuoc goi tiep theo)</div>'
        '<div>%s</div></div>'
    ) % inner


def _situation(inner):
    return _box('#2563eb', '#eff6ff', '&#127916;', 'Tinh huong thuc te', inner)


def _advice(inner):
    return _box('#16a34a', '#f0fdf4', '&#128161;', 'Loi khuyen', inner)


def _proof(inner):
    return _box('#9333ea', '#faf5ff', '&#9989;', 'Chung minh', inner)


def _mistake(inner):
    return _box('#ea580c', '#fff7ed', '&#9888;&#65039;', 'Sai lam thuong gap', inner)


class SlideChannelSeedKHTN(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_kh_tiem_nang(self):
        ch = self.env.ref('vd_elearning.course_kh_tiem_nang', raise_if_not_found=False)
        if not ch:
            return False
        # Idempotent: da co bai hoc -> giu nguyen (ton trong sua tay admin).
        if ch.slide_ids.filtered(lambda s: not s.is_category):
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        pages = self._vd_khtn_pages()
        seq = 1
        for title, body in pages:
            Slide.create({
                'channel_id': ch.id, 'name': title,
                'slide_category': 'article',
                'vd_body': '<div style="%s">%s</div>' % (_WRAP, body),
                'sequence': seq, 'is_published': True,
            })
            seq += 1

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bai thi - 20 cau',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._vd_khtn_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1
        return True

    # ==================================================================
    #  NOI DUNG BAI HOC
    # ==================================================================
    def _vd_khtn_pages(self):
        h2 = 'font-size:19px;font-weight:900;color:#1e293b;margin:18px 0 8px;'
        h3 = 'font-size:16px;font-weight:800;color:#3730a3;margin:14px 0 6px;'
        lead = 'font-size:16px;color:#475569;margin:0 0 12px;'

        # Xay tung trang bang ghep chuoi truc tiep (an toan voi ky tu % / &).
        return [
            ('1. Ban chat & Muc tieu', self._page1(h2, h3, lead)),
            ('2. Tieu chi 1 - Thoi gian khoi cong', self._page2(h2, h3, lead)),
            ('3. Tieu chi 2 - Tai chinh + Mau nha + Dat', self._page3(h2, h3, lead)),
            ('4. 4 cau hoi vang phai hoi', self._page4(h2, h3, lead)),
            ('5. Phan loai khach A / B / C', self._page5(h2, h3, lead)),
            ('6. Cach chot & Ket luan', self._page6(h2, h3, lead)),
        ]

    def _page1(self, h2, h3, lead):
        return (
            '<p style="' + lead + '">Trong nganh <b>xay nha tron goi</b>, khach co ky '
            'hop dong hay khong gan nhu chi phu thuoc vao <b>2 yeu to cot loi</b>. Nam '
            'duoc 2 yeu to nay, ban thoi "doan mo" va biet chinh xac nen dau tu thoi '
            'gian vao ai.</p>'

            '<table><thead><tr><th style="width:56px;">#</th>'
            '<th>2 yeu to cot loi quyet dinh khach co ky hop dong</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>YEU TO 1:</b> Khach co <b>thoi gian khoi cong that</b> hay khong.</td></tr>'
            '<tr><td style="text-align:center;font-size:20px;">&#127919;</td>'
            '<td><b>YEU TO 2:</b> <b>Tai chinh + Mau nha + Dien tich dat</b> co khop nhau hay khong.</td></tr>'
            '</tbody></table>'

            '<h2 style="' + h2 + '">&#127891; Muc tieu bai hoc</h2>'
            '<p>Sau khi hoc xong, nhan vien <b>phai</b>:</p>'
            '<ul>'
            '<li>Biet khach nao thuc su co kha nang <b>ky hop dong</b>.</li>'
            '<li>Biet khach nao chi dang <b>tham khao</b>.</li>'
            '<li>Biet phai <b>hoi gi</b> de xac dinh khach.</li>'
            '<li>Biet phai <b>tu van gi</b> de keo khach ky som.</li>'
            '<li>Biet cach phat hien khach tiem nang du khach <b>noi rat it</b>.</li>'
            '</ul>'

            '<h2 style="' + h2 + '">PHAN 1 &mdash; Ban chat khach hang tiem nang la gi</h2>'
            + _mistake(
                '<ul>'
                '<li>Khach noi nhieu &rArr; tuong tiem nang.</li>'
                '<li>Khach hoi nhieu &rArr; tuong tiem nang.</li>'
                '<li>Khach xin nhieu mau &rArr; tuong tiem nang.</li>'
                '</ul>'
                '<p style="margin-bottom:0;"><b>Thuc te:</b> khach hang tiem nang '
                '<u>khong</u> duoc xac dinh bang viec khach noi nhieu hay it.</p>'
            )
            + '<p>Khach hang tiem nang duoc xac dinh bang <b>2 tieu chi</b>:</p>'
            '<table><thead><tr><th style="width:90px;">Tieu chi</th><th>Noi dung</th></tr></thead><tbody>'
            '<tr><td style="text-align:center;font-weight:800;color:#b91c1c;">SO 1</td>'
            '<td>Khach co <b>ke hoach khoi cong thuc te</b>.</td></tr>'
            '<tr><td style="text-align:center;font-weight:800;color:#b91c1c;">SO 2</td>'
            '<td>Tai chinh cua khach <b>phu hop voi mau nha mong muon</b>.</td></tr>'
            '</tbody></table>'
            '<p style="text-align:center;font-size:16px;">Co du 2 yeu to &rArr; '
            '<b style="color:#16a34a;">&#10145; Khach chinh la khach hang tiem nang.</b></p>'

            + _apply(
                '<p>Mo lai 3 khach gan nhat ban dang theo. Voi tung khach tu cham '
                '"Co / Chua biet" cho 2 cot:</p>'
                '<ol><li>Khach co <b>thoi gian khoi cong</b> chua?</li>'
                '<li>Tai chinh co <b>khop mau nha</b> chua?</li></ol>'
                '<p style="margin-bottom:0;">Khach nao ca 2 cot deu trong &rArr; ban '
                'dang <b>ton thoi gian nham nguoi</b>, can xac minh lai ngay.</p>'
            )
        )

    def _page2(self, h2, h3, lead):
        stars = lambda n: ('<span style="color:#f59e0b;font-size:17px;">' + ('&#9733;' * n)
                           + '</span><span style="color:#d1d5db;font-size:17px;">'
                           + ('&#9733;' * (5 - n)) + '</span>')
        return (
            '<h2 style="' + h2 + '">PHAN 2 &mdash; Tieu chi 1: Thoi gian khoi cong</h2>'
            '<h3 style="' + h3 + '">Tai sao day la tieu chi quan trong nhat?</h3>'
            '<p>Boi vi <b>nguoi xay nha that luon co ke hoach</b>. Co the la: thang sau '
            'xay &middot; sau Tet xay &middot; 2 thang nua xay &middot; doi hoan tat thu '
            'tuc la xay&hellip; nhung <b>luon co thoi gian du kien</b>.</p>'
            '<p>Nguoc lai, nguoi <b>chua co nhu cau that</b> thuong noi: "dang xem thoi", '
            '"chua biet", "tu tu tinh", "de tham khao truoc".</p>'

            + _proof(
                '<p style="margin-bottom:0;">Nguoi sap khoi cong da co rang buoc thuc te '
                '(dat, tien, gia dinh, thoi diem dep) nen <b>ho buoc phai co moc thoi '
                'gian</b>. Con nguoi chi tham khao thi khong co ap luc nao &rArr; cau tra '
                'loi luon mo ho. Vi vay, <b>thoi gian la phep thu that-gia chinh xac '
                'nhat</b>.</p>'
            )

            + '<h2 style="' + h2 + '">Cach nhan biet qua moc thoi gian</h2>'
            '<table><thead><tr><th>Nhom khach</th><th>Khach noi the nao</th>'
            '<th style="width:120px;text-align:center;">Muc do</th><th>Hanh dong</th></tr></thead><tbody>'
            '<tr><td><b style="color:#16a34a;">Cuc ky tiem nang</b></td>'
            '<td>"Qua Tet anh xay", "Thang 2 am anh lam mong", "Cuoi nam anh khoi cong", '
            '"Dat xong roi, gio dang chuan bi".</td>'
            '<td style="text-align:center;">' + stars(5) + '</td>'
            '<td><b>Phai bam sat.</b></td></tr>'
            '<tr><td><b style="color:#d97706;">Tiem nang trung binh</b></td>'
            '<td>"Chac trong nam nay xay", "Dang chuan bi tai chinh", "Dang hoan thien giay to".</td>'
            '<td style="text-align:center;">' + stars(3) + '</td>'
            '<td>Can theo doi.</td></tr>'
            '<tr><td><b style="color:#6b7280;">Tham khao</b></td>'
            '<td>"Chua biet", "Dang tim hieu", "Hoi truoc thoi".</td>'
            '<td style="text-align:center;">' + stars(1) + '</td>'
            '<td>Khong danh qua nhieu thoi gian.</td></tr>'
            '</tbody></table>'

            + _situation(
                '<p>Khach nhan tin: <i>"Em gui anh vai mau nha 2 tang di."</i></p>'
                '<p><b>NV yeu</b> gui ngay 10 mau roi&hellip; im. <b>NV gioi</b> gui mau '
                'kem 1 cau: <i>"Da anh, de em chon mau hop nhat, anh du kien khoang khi '
                'nao minh khoi cong a?"</i></p>'
                '<p style="margin-bottom:0;">Chinh cau hoi thoi gian moi <b>loc ra</b> '
                'khach that.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Dung voi bao gia khi <b>chua biet moc thoi '
                'gian</b>. Khong co thoi gian khoi cong &rArr; moi bao gia, moi mau nha '
                'deu chi de "tham khao", rat de bi so sanh va mat khach.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Trong <b>3 cuoc goi tiep theo</b>, bat buoc '
                'hoi cau: <i>"Anh/chi du kien khoang thoi gian nao se bat dau trien khai '
                'xay dung a?"</i> &mdash; roi ghi moc thoi gian vao ho so khach. Khong co '
                'moc &rArr; xep nhom tham khao (1&#9733;).</p>'
            )
        )

    def _page3(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHAN 3 &mdash; Tieu chi 2: Tai chinh + Mau nha + Dien tich dat</h2>'
            '<p style="' + lead + '">Day la tieu chi <b>quyet dinh khach co ky duoc hay '
            'khong</b>. Thoi gian cho biet khach "co that", con bo ba Tai chinh - Mau - '
            'Dat cho biet khach "<b>kha thi</b>".</p>'

            '<h3 style="' + h3 + '">So sanh 2 vi du (cung mieng dat 5x20)</h3>'
            '<table><thead><tr><th>Yeu to</th>'
            '<th style="text-align:center;">Vi du 1</th>'
            '<th style="text-align:center;">Vi du 2</th></tr></thead><tbody>'
            '<tr><td><b>Dien tich dat</b></td><td style="text-align:center;">5 x 20</td>'
            '<td style="text-align:center;">5 x 20</td></tr>'
            '<tr><td><b>Mau nha khach thich</b></td>'
            '<td style="text-align:center;">2 tang hien dai</td>'
            '<td style="text-align:center;">Tan co dien 3 tang</td></tr>'
            '<tr><td><b>Tai chinh</b></td>'
            '<td style="text-align:center;">1,4 ty</td>'
            '<td style="text-align:center;">1 ty</td></tr>'
            '<tr><td><b>Ket luan</b></td>'
            '<td style="text-align:center;color:#16a34a;font-weight:800;">&#9989; Hop ly &rArr; rat tiem nang</td>'
            '<td style="text-align:center;color:#dc2626;font-weight:800;">&#10060; Khong kha thi &rArr; chua tiem nang</td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Cung 1 mieng dat nhung mau nha + tai chinh '
                'khac nhau cho ra 2 ket qua nguoc nhau. &rArr; Khong phai khach cu co tien '
                'la ky duoc; <b>tien phai khop voi mau nha va dien tich</b>. Day la ly do '
                'phai hoi du ca 3 thong tin truoc khi bao gia.</p>'
            )

            + _formula(
                'Khach tiem nang = <span style="color:#1d4ed8;">Thoi gian xay ro rang</span> '
                '&#10133; <span style="color:#16a34a;">Tai chinh phu hop</span> '
                '&#10133; <span style="color:#9333ea;">Mau nha phu hop</span> '
                '&#10133; <span style="color:#b45309;">Dien tich dat phu hop</span>'
            )

            + _situation(
                '<p>Khach: <i>"Anh co 1 ty, muon xay tan co dien 3 tang tren dat 5x20."</i></p>'
                '<p><b>NV yeu</b> im lang hoac gat dai roi bao gia &rArr; khach soc gia, bo di.</p>'
                '<p style="margin-bottom:0;"><b>NV gioi</b> can doi: <i>"Da voi 1 ty tren '
                'dat 5x20, em goi y phuong an 2 tang hien dai vua dep vua du ngan sach, con '
                'tan co dien minh tinh khi ngan sach thoai hon a."</i> &mdash; giu khach + '
                'keo ve vung kha thi.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Khi tai chinh chua khop mau, <b>dung tu choi '
                'khach</b> &mdash; hay <b>dieu chinh mau/phuong an</b> ve vung kha thi. Day '
                'chinh la cach bien khach Nhom B thanh khach ky duoc (xem Phan 5).</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Voi moi khach dang theo, dien du <b>3 o</b>: '
                'Dien tich dat &mdash; Mau nha mong muon &mdash; Tai chinh du tru. Thieu o '
                'nao &rArr; hoi bo sung ngay o cuoc goi sau. <b>Khong bao gia khi con o '
                'trong.</b></p>'
            )
        )

    def _page4(self, h2, h3, lead):
        rows = [
            ('1', 'Anh/chi du kien khoang thoi gian nao se bat dau trien khai xay dung?',
             'Xac dinh <b>thoi gian khoi cong</b>.'),
            ('2', 'Anh/chi dang du tru khoang bao nhieu kinh phi cho can nha?',
             'Xac dinh <b>kha nang tai chinh</b>.'),
            ('3', 'Anh/chi thich mau nha theo phong cach nao?',
             'Xac dinh <b>nhu cau thuc</b>.'),
            ('4', 'Dien tich dat hien tai cua minh la bao nhieu met vuong a?',
             'Kiem tra <b>tinh kha thi</b>.'),
        ]
        body = (
            '<h2 style="' + h2 + '">PHAN 4 &mdash; 4 cau hoi vang phai hoi</h2>'
            '<p style="' + lead + '">Chi can hoi xong <b>4 cau</b> nay la ban du du lieu '
            'de phan loai khach va biet buoc tiep theo. Hoc thuoc va hoi <b>tu nhien</b> '
            'trong hoi thoai, khong hoi don dap nhu dieu tra.</p>'
            '<table><thead><tr><th style="width:48px;">Cau</th><th>Cau hoi vang</th>'
            '<th style="width:42%;">Muc dich</th></tr></thead><tbody>'
        )
        for n, q, m in rows:
            body += ('<tr><td style="text-align:center;font-weight:800;color:#b45309;">'
                     + n + '</td><td><i>"' + q + '"</i></td><td>' + m + '</td></tr>')
        body += '</tbody></table>'
        body += _formula(
            '4 cau hoi vang = <b>Thoi gian</b> &#8226; <b>Tai chinh</b> &#8226; '
            '<b>Mau nha</b> &#8226; <b>Dien tich dat</b>'
        )
        body += _situation(
            '<p>Khach kiem loi, chi nhan tin "bao gia di em". Thay vi bao gia ngay, hoi '
            'gon 1 cau ghep: <i>"Da de bao gia chuan nhat, anh cho em xin dien tich dat va '
            'du kien khi nao khoi cong a?"</i></p>'
            '<p style="margin-bottom:0;">2 thong tin nay loc ra ngay khach that hay '
            'tham khao.</p>'
        )
        body += _advice(
            '<p style="margin-bottom:0;">Dan 4 cau hoi vang canh man hinh. Sau moi cuoc '
            'goi, kiem tra da thu duoc <b>du 4 thong tin</b> chua. Thieu cau nao &rArr; lan '
            'sau hoi tiep cau do.</p>'
        )
        body += _apply(
            '<p style="margin-bottom:0;">Tu viet lai <b>4 cau hoi vang theo giong cua ban</b> '
            '(cho tu nhien) va doc to 3 lan truoc khi goi khach tiep theo. Bat buoc hoi du '
            '4 cau trong cuoc goi do.</p>'
        )
        return body

    def _page5(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHAN 5 &mdash; Phan loai khach hang</h2>'
            '<p style="' + lead + '">Sau khi co 4 thong tin, xep khach vao 1 trong 3 nhom '
            'de biet <b>muc tieu xu ly</b> ro rang.</p>'
            '<table><thead><tr><th style="width:120px;">Nhom</th><th>Dac diem</th>'
            '<th style="width:96px;text-align:center;">Muc do</th><th>Muc tieu xu ly</th></tr></thead><tbody>'

            '<tr><td><b style="color:#16a34a;">NHOM A</b><br/>Cuc ky tiem nang</td>'
            '<td>Co thoi gian khoi cong &middot; Co tai chinh phu hop &middot; Co mau nha phu hop.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;&#9733;&#9733;&#9733;&#9733;</td>'
            '<td>&#10145; Keo ve <b>khao sat</b>.<br/>&#10145; <b>Ky giu gia</b>.</td></tr>'

            '<tr><td><b style="color:#d97706;">NHOM B</b><br/>Tiem nang chua chin</td>'
            '<td>Co thoi gian xay, nhung <b>tai chinh chua du</b> hoac <b>chua chon duoc mau</b>.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;&#9733;&#9733;</td>'
            '<td>&#10145; Tu van <b>can doi tai chinh</b>.<br/>&#10145; <b>Dieu chinh mau nha</b>.<br/>'
            '&#10145; Hoan thien phuong an.</td></tr>'

            '<tr><td><b style="color:#6b7280;">NHOM C</b><br/>Tham khao</td>'
            '<td>Chua co thoi gian xay &middot; Chua co tai chinh &middot; Chua co nhu cau ro.</td>'
            '<td style="text-align:center;color:#f59e0b;">&#9733;</td>'
            '<td>&#10145; Giu lien he.<br/>&#10145; Cham soc dinh ky.<br/>'
            '<b style="color:#dc2626;">Khong don ky.</b></td></tr>'
            '</tbody></table>'

            + _proof(
                '<p style="margin-bottom:0;">Phan nhom giup ban <b>phan bo thoi gian dung '
                'cho</b>: don luc vao Nhom A (sap ky), nuoi duong Nhom B (sua phuong an cho '
                'kha thi), va khong "dot" nang luong vao Nhom C. Dung nhom &rArr; ty le chot '
                'tang, thoi gian khong bi lang phi.</p>'
            )

            + _mistake(
                '<p style="margin-bottom:0;">Don ky Nhom C (chua co thoi gian, chua co tien) '
                '&rArr; khach so, mat thien cam, va ban mat thoi gian dang le danh cho Nhom A.</p>'
            )

            + _advice(
                '<p style="margin-bottom:0;">Voi Nhom B, dung bo &mdash; day la "mo vang" '
                'thuong bi bo qua. Chi can <b>can doi tai chinh / doi mau cho khop</b> la ho '
                'len Nhom A. Hoc ky cac khoa "Can doi tien", "Chuyen doi mau nha" de xu ly '
                'Nhom B.</p>'
            )

            + _apply(
                '<p style="margin-bottom:0;">Ngay hom nay, gan <b>nhan A / B / C</b> cho tat '
                'ca khach ban dang theo. Liet ke ro: Nhom A goi lich khao sat truoc; Nhom B '
                'ghi ro "thieu gi" (tien hay mau) de xu ly.</p>'
            )
        )

    def _page6(self, h2, h3, lead):
        return (
            '<h2 style="' + h2 + '">PHAN 6 &mdash; Cach chot khach tiem nang</h2>'
            '<p style="' + lead + '">Khi khach da co <b>du 3 dieu kien</b> (&#9989; thoi '
            'gian xay &middot; &#9989; tai chinh phu hop &middot; &#9989; mau nha phu hop) '
            'thi <b>khong tu van lan man nua</b>. Chuyen ngay sang 3 buoc chot:</p>'

            '<table><thead><tr><th style="width:140px;">Buoc chot</th><th>Cau noi mau</th></tr></thead><tbody>'
            '<tr><td><b>&#128205; Khao sat</b></td>'
            '<td><i>"De phuong an chinh xac nhat, em xin lich khao sat thuc te giup '
            'anh/chi."</i></td></tr>'
            '<tr><td><b>&#128176; Giu gia</b></td>'
            '<td><i>"Hien tai ben em dang ap dung chinh sach giu gia 12 thang, minh chot '
            'som se chu dong hon rat nhieu khi trien khai."</i></td></tr>'
            '<tr><td><b>&#128396; Thiet ke som</b></td>'
            '<td><i>"Nhung khach chuan bi xay sau Tet thuong trien khai thiet ke tu bay gio '
            'de co thoi gian chinh sua cong nang, tranh sat ngay thi cong phai sua nhieu '
            'lan."</i></td></tr>'
            '</tbody></table>'

            + _situation(
                '<p>Khach Nhom A: "Qua Tet anh xay, anh co 1,4 ty, thich 2 tang hien dai, '
                'dat 5x20."</p>'
                '<p style="margin-bottom:0;">&rArr; Du dieu kien. Khong gui them mau de '
                '"suy nghi" nua. Chot lich khao sat + neu chinh sach giu gia 12 thang + de '
                'xuat thiet ke som. <b>Cang keo dai cang de mat vao tay doi thu.</b></p>'
            )

            + '<h2 style="' + h2 + '">&#127942; Ket luan nhan vien phai nho</h2>'
            + _formula(
                'Khong phai khach noi nhieu / xin nhieu mau la tiem nang.<br/>'
                'Khach tiem nang that = <b>(1) Thoi gian khoi cong tuong doi ro</b> '
                '&#10133; <b>(2) Tai chinh phu hop voi mau nha &amp; dien tich dat</b>.'
            )
            + '<p style="text-align:center;font-size:16px;">Co du 2 dieu nay &rArr; '
            '<b style="color:#16a34a;">Bam sat &#10145; Khao sat &#10145; Giu gia &#10145; '
            'Ky hop dong.</b></p>'
            '<p style="text-align:center;color:#475569;">Do moi la khach hang mang lai '
            '<b>doanh thu</b> cho cong ty.</p>'

            + _apply(
                '<p>Bang tu cham truoc khi roi moi khach (tra loi Co/Khong):</p>'
                '<ol>'
                '<li>Da biet <b>thoi gian khoi cong</b> chua?</li>'
                '<li>Da biet <b>tai chinh</b> chua?</li>'
                '<li>Da biet <b>mau nha + dien tich dat</b> chua?</li>'
                '<li>Da <b>xep nhom A/B/C</b> chua?</li>'
                '<li>Neu Nhom A: da <b>chot khao sat / neu giu gia</b> chua?</li>'
                '</ol>'
                '<p style="margin-bottom:0;">Con o nao "Khong" &rArr; do chinh la viec '
                'phai lam o cuoc goi tiep theo.</p>'
            )
        )

    # ==================================================================
    #  20 CAU HOI TRAC NGHIEM (ep nho + van dung). (dap an, dung?)
    # ==================================================================
    def _vd_khtn_questions(self):
        T, F = True, False
        return [
            ('Trong xay nha tron goi, khach co ky hop dong hay khong phu thuoc chinh vao may yeu to cot loi?',
             [('2 yeu to: thoi gian khoi cong va tai chinh-mau-dat khop nhau', T),
              ('1 yeu to: khach noi nhieu hay it', F),
              ('3 yeu to: gia, khuyen mai, qua tang', F),
              ('Khong yeu to nao, hoan toan may rui', F)]),

            ('Cach hieu nao SAI ve khach hang tiem nang?',
             [('Khach noi nhieu / xin nhieu mau nghia la tiem nang', T),
              ('Khach co ke hoach khoi cong thuc te', F),
              ('Khach co tai chinh phu hop mau nha', F),
              ('Khach co thoi gian xay tuong doi ro', F)]),

            ('Hai tieu chi xac dinh khach hang tiem nang la gi?',
             [('Co ke hoach khoi cong thuc te + tai chinh phu hop mau nha', T),
              ('Noi nhieu + hoi nhieu', F),
              ('Xin nhieu mau + tra gia gioi', F),
              ('O gan cong ty + quen biet', F)]),

            ('Tieu chi nao duoc coi la QUAN TRONG NHAT de loc khach that - gia?',
             [('Thoi gian khoi cong', T),
              ('Khach co thich noi chuyen khong', F),
              ('Khach hoi gia bao nhieu lan', F),
              ('So luong mau khach xin', F)]),

            ('Cau noi nao the hien khach CHUA co nhu cau that?',
             [('"Dang xem thoi, tu tu tinh, de tham khao truoc"', T),
              ('"Qua Tet anh xay"', F),
              ('"Thang 2 am anh lam mong"', F),
              ('"Dat xong roi, gio dang chuan bi"', F)]),

            ('Khach noi "Qua Tet anh xay / Cuoi nam anh khoi cong / Dat xong roi dang chuan bi" thuoc nhom nao?',
             [('Khach cuc ky tiem nang (5 sao) - phai bam sat', T),
              ('Khach tham khao (1 sao) - bo qua', F),
              ('Khach khong co nhu cau', F),
              ('Khach chi hoi cho vui', F)]),

            ('Khach noi "Chac trong nam nay xay, dang chuan bi tai chinh, dang hoan thien giay to" thuoc nhom nao?',
             [('Tiem nang trung binh (3 sao) - can theo doi', T),
              ('Cuc ky tiem nang (5 sao)', F),
              ('Tham khao (1 sao)', F),
              ('Khong tiem nang', F)]),

            ('Voi nhom khach tham khao (1 sao: "chua biet, dang tim hieu, hoi truoc thoi"), nhan vien nen?',
             [('Khong danh qua nhieu thoi gian, giu lien he cham soc dinh ky', T),
              ('Don het suc ep ky ngay', F),
              ('Goi lien tuc moi ngay de ep', F),
              ('Bao gia that thap de ky gap', F)]),

            ('Dat 5x20, khach thich nha 2 tang hien dai, tai chinh 1,4 ty. Danh gia?',
             [('Hop ly - day la khach rat tiem nang', T),
              ('Khong kha thi', F),
              ('Khong du tien', F),
              ('Khong xac dinh duoc', F)]),

            ('Dat 5x20, khach thich tan co dien 3 tang, tai chinh 1 ty. Danh gia?',
             [('Khong kha thi - chua phai khach tiem nang', T),
              ('Hop ly - khach rat tiem nang', F),
              ('Du tien thoai mai', F),
              ('Chac chan ky duoc ngay', F)]),

            ('Cong thuc "Khach tiem nang =" gom day du nhung yeu to nao?',
             [('Thoi gian xay ro rang + Tai chinh phu hop + Mau nha phu hop + Dien tich dat phu hop', T),
              ('Thoi gian xay + so dien thoai', F),
              ('Tai chinh + qua tang', F),
              ('Mau nha dep + gia re', F)]),

            ('Muc dich cua cau hoi "Anh/chi du kien khoang thoi gian nao se bat dau trien khai xay dung?"',
             [('Xac dinh thoi gian khoi cong', T),
              ('Xac dinh tai chinh', F),
              ('Xac dinh dien tich dat', F),
              ('Xac dinh phong cach mau nha', F)]),

            ('Muc dich cua cau hoi "Anh/chi dang du tru khoang bao nhieu kinh phi cho can nha?"',
             [('Xac dinh kha nang tai chinh', T),
              ('Xac dinh thoi gian khoi cong', F),
              ('Xac dinh dien tich dat', F),
              ('Xac dinh mau nha', F)]),

            ('Muc dich cua cau hoi "Dien tich dat hien tai cua minh la bao nhieu met vuong?"',
             [('Kiem tra tinh kha thi (mau + tai chinh co khop dat khong)', T),
              ('Xac dinh thoi gian khoi cong', F),
              ('Xac dinh so tang khach muon', F),
              ('De tinh tien hoa hong', F)]),

            ('Khach NHOM A (co thoi gian + tai chinh phu hop + mau phu hop) thi muc tieu xu ly la?',
             [('Keo ve khao sat va ky giu gia', T),
              ('Giu lien he, cham soc dinh ky', F),
              ('Chi gui them mau roi cho', F),
              ('Khong lam gi, doi khach goi lai', F)]),

            ('Khach NHOM B (co thoi gian xay nhung tai chinh chua du hoac chua chon mau) nen xu ly the nao?',
             [('Tu van can doi tai chinh, dieu chinh mau nha, hoan thien phuong an', T),
              ('Bo qua vi khong du tien', F),
              ('Ep ky ngay du chua kha thi', F),
              ('Bao gia cao hon de lai', F)]),

            ('Khach NHOM C (chua co thoi gian, chua co tai chinh, chua co nhu cau ro) thi?',
             [('Giu lien he, cham soc dinh ky, KHONG don ky', T),
              ('Don ky cang som cang tot', F),
              ('Goi lich khao sat ngay', F),
              ('Ky giu gia ngay lap tuc', F)]),

            ('Khi khach da du 3 dieu kien (thoi gian, tai chinh, mau nha phu hop), buoc tiep theo dung nhat la?',
             [('Chuyen sang chot: khao sat - giu gia - thiet ke som', T),
              ('Tiep tuc tu van lan man them nhieu mau', F),
              ('Cho khach tu suy nghi vo thoi han', F),
              ('Gui them bang gia roi im lang', F)]),

            ('Cau noi "Hien tai ben em dang ap dung chinh sach giu gia 12 thang, minh chot som se chu dong hon" thuoc buoc chot nao?',
             [('Giu gia', T),
              ('Khao sat', F),
              ('Thiet ke som', F),
              ('Bao gia lai', F)]),

            ('Ket luan cot loi nhan vien phai nho la gi?',
             [('Khach tiem nang that phai co thoi gian khoi cong tuong doi ro VA tai chinh phu hop voi mau nha + dien tich dat', T),
              ('Khach noi cang nhieu cang tiem nang', F),
              ('Khach xin cang nhieu mau cang de ky', F),
              ('Cu bao gia that thap thi khach nao cung ky', F)]),
        ]
