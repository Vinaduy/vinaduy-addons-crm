# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "MÓNG" (course_a2).

Đối tượng: nhân viên sale (kể cả TRÁI NGÀNH). Khóa giúp hiểu và phân biệt: đất
thi công (liền thổ / yếu), 3 loại móng (đơn / băng / cọc), cọc bê tông đúc sẵn,
2 phương pháp ép (ép tải / ép neo), các loại cọc ít dùng.

GIAO DIỆN kiểu Streamlit (giống khóa "Kỹ thuật thi công"): menu trái chọn từng
bài + hộp màu + HÌNH MÔ PHỎNG SVG tự vẽ + công thức chốt + quiz chấm đúng/sai
tức thì (thuần CSS input:checked, KHÔNG JS). vd_body sanitize=False + render
markup() nên HTML/SVG thô giữ nguyên.

Helper nối chuỗi (+) -> tránh bẫy %. MỌI class method dùng prefix RIÊNG _mng_
để KHÔNG trùng tên với seed khác (xem reference-seed-method-name-collision).
Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models

_MO_VERSION = 'v5-svg-photos'
_PARAM_KEY = 'vd_elearning.mong_seed_version'
_IMG = '/vd_elearning/static/src/img/mong/'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-mong{font-size:16px;line-height:1.7;color:#1f2937;'
    'width:96vw;max-width:1720px;position:relative;left:50%;transform:translateX(-50%);'
    'margin-top:-1.3cm;}'
    '.vd-mong .vd-course{background:linear-gradient(180deg,#eef2ff 0%,#f5f8ff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-mong h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-mong h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-mong p{margin:0 0 10px;}'
    '.vd-mong ul,.vd-mong ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-mong li{margin:5px 0;}'
    '.vd-mong b{color:#111827;}'
    '.vd-mong table{border-collapse:collapse;width:100%;margin:8px 0 6px;font-size:15px;}'
    '.vd-mong th,.vd-mong td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-mong th{background:#eef2ff;font-weight:800;color:#3730a3;}'
    '.vd-mong .thok{background:#dcfce7;color:#15803d;}'
    '.vd-mong .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-mong .tc{text-align:center;}'
    '.vd-mong .cheap{color:#16a34a;font-weight:800;}'
    '.vd-mong .mid{color:#d97706;font-weight:800;}'
    '.vd-mong .exp{color:#dc2626;font-weight:800;}'
    '.vd-mong .navr,.vd-mong .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-mong .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-mong .vc-side{flex:0 0 300px;}'
    '.vd-mong .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-mong .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-mong .vc-navbtn:hover{background:#eef2ff;border-color:#c7d2fe;color:#4338ca;}'
    '.vd-mong .vc-nbadge{flex:0 0 auto;display:inline-block;background:#e0e7ff;color:#4338ca;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-mong .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;white-space:nowrap;}'
    '.vd-mong .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-mong .vc-panel{display:none;}'
    '.vd-mong .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#4338ca;background:#e0e7ff;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-mong .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:9px 0;}'
    '.vd-mong .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-mong .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-mong .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-mong .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # cong thuc
    '.vd-mong .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:10px 0;}'
    '.vd-mong .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-mong .fml .fml-b{color:#4c1d95;font-weight:600;}'
    # dieu can nho (chot)
    '.vd-mong .core{border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
    'padding:15px 18px;margin:14px 0;text-align:center;}'
    '.vd-mong .core .ch{font-weight:900;color:#92600a;font-size:12.5px;letter-spacing:.6px;'
    'text-transform:uppercase;margin-bottom:7px;}'
    '.vd-mong .core .cb{font-size:16px;font-weight:800;color:#3a2c05;}'
    # sai lam nhan vien
    '.vd-mong .wrong{background:#fff1f2;border:2px solid #fda4af;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#9f1239;}'
    '.vd-mong .wrong .wh{font-weight:800;color:#be123c;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:5px;}'
    # hinh mo phong SVG
    '.vd-mong .fig{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;'
    'padding:14px 16px 10px;margin:12px 0;text-align:center;}'
    '.vd-mong .fig svg{max-width:100%;height:auto;}'
    '.vd-mong .fig .cap{font-size:13px;color:#64748b;margin-top:6px;font-weight:600;}'
    '.vd-mong .fig .figh{font-size:12.5px;font-weight:800;letter-spacing:.6px;'
    'color:#0f172a;text-transform:uppercase;margin-bottom:8px;text-align:left;}'
    # gallery anh thuc te
    '.vd-mong .phwrap{margin:12px 0;}'
    '.vd-mong .phhead{font-size:12.5px;font-weight:800;letter-spacing:.6px;color:#0f172a;'
    'text-transform:uppercase;margin-bottom:8px;}'
    '.vd-mong .phrow{display:flex;flex-wrap:wrap;gap:12px;}'
    '.vd-mong .phrow figure{margin:0;flex:1 1 230px;min-width:190px;max-width:360px;}'
    '.vd-mong .phrow img{width:100%;height:210px;object-fit:cover;border-radius:12px;'
    'box-shadow:0 6px 18px rgba(2,6,23,.18);}'
    '.vd-mong .phrow figcaption{font-size:12px;color:#64748b;text-align:center;'
    'margin-top:5px;font-weight:600;}'
    # thu tu danh so
    '.vd-mong .vc-order{margin:12px 0;border:1px solid #c7d2fe;border-radius:12px;overflow:hidden;}'
    '.vd-mong .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #e0e7ff;background:#f7f8ff;}'
    '.vd-mong .vc-ostep:last-child{border-bottom:none;}'
    '.vd-mong .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#4338ca;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-mong .vc-ot{font-weight:800;color:#3730a3;}'
    '.vd-mong .vc-od{color:#4338ca;font-size:14.5px;}'
    # quiz
    '.vd-mong .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
    '.vd-mong .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-mong .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-mong .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-mong .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-mong .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-mong .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-mong .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-mong .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-mong .vc-layout{flex-direction:column;}'
    '.vd-mong .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-mong .vc-sidehead{width:100%;}'
    '.vd-mong .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
    '</style>'
)


# ---------------------------------------------------------------------------
#  HELPER (nối chuỗi -> không lo bẫy %)
# ---------------------------------------------------------------------------
def _box(kind, text):
    cls = {'err': 'b-err', 'warn': 'b-warn', 'info': 'b-info', 'ok': 'b-ok'}[kind]
    icon = {'err': '&#128680;', 'warn': '&#9888;&#65039;', 'info': '&#128161;', 'ok': '&#9989;'}[kind]
    return '<div class="box ' + cls + '">' + icon + ' ' + text + '</div>'


def _fml(text):
    return ('<div class="fml"><div class="fh">&#128208; CÔNG THỨC THUỘC LÒNG</div>'
            '<div class="fml-b">' + text + '</div></div>')


def _core(text):
    return ('<div class="core"><div class="ch">&#11088; ĐIỀU CẦN NHỚ</div>'
            '<div class="cb">' + text + '</div></div>')


def _wrong(items):
    lis = ''.join('<li>' + x + '</li>' for x in items)
    return ('<div class="wrong"><div class="wh">&#10060; SAI LẦM NHÂN VIÊN HAY MẮC</div>'
            '<ul style="margin:0;">' + lis + '</ul></div>')


def _fig(head, svg, cap):
    return ('<div class="fig"><div class="figh">' + head + '</div>' + svg
            + '<div class="cap">' + cap + '</div></div>')


def _photos(head, items):
    """Gallery ANH THUC TE. items = list (ten_file, chu_thich)."""
    figs = ''
    for name, cap in items:
        c = ('<figcaption>' + cap + '</figcaption>') if cap else ''
        figs += '<figure><img src="' + _IMG + name + '"/>' + c + '</figure>'
    return ('<div class="phwrap"><div class="phhead">&#128247; ' + head + '</div>'
            '<div class="phrow">' + figs + '</div></div>')


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _order(steps):
    out = '<div class="vc-order">'
    for i, (t, d) in enumerate(steps):
        out += ('<div class="vc-ostep"><div class="vc-onum">' + str(i + 1) + '</div>'
                '<div><div class="vc-ot">' + t + '</div>'
                + ('<div class="vc-od">' + d + '</div>' if d else '') + '</div></div>')
    return out + '</div>'


def _quiz(qid, question, options, explain):
    letters = ['A', 'B', 'C', 'D', 'E']
    inputs = ''
    labels = ''
    correct = 0
    wrong = []
    for i, (text, ok) in enumerate(options):
        oid = qid + '_' + str(i)
        inputs += '<input class="qopt" type="radio" name="' + qid + '" id="' + oid + '">'
        labels += ('<label for="' + oid + '"><span class="qk">' + letters[i]
                   + '</span>' + text + '</label>')
        if ok:
            correct = i
        else:
            wrong.append(i)
    cid = qid + '_' + str(correct)
    css = '#' + cid + ':checked ~ .fb-right{display:block}'
    if wrong:
        css += ','.join('#' + qid + '_' + str(w) + ':checked ~ .fb-wrong' for w in wrong) + '{display:block}'
    css += ('#' + cid + ':checked ~ .opts label[for=' + cid + ']'
            '{background:#dcfce7;border-color:#16a34a;color:#15803d}')
    for w in wrong:
        wid = qid + '_' + str(w)
        css += ('#' + wid + ':checked ~ .opts label[for=' + wid + ']'
                '{background:#fee2e2;border-color:#dc2626;color:#b91c1c}')
        css += ('#' + wid + ':checked ~ .opts label[for=' + cid + ']'
                '{background:#dcfce7;border-color:#16a34a;color:#15803d}')
    return ('<div class="quiz"><div class="qq">&#128221; Trắc nghiệm nhanh</div>'
            '<div class="qhint">' + question + ' &mdash; bấm chọn một đáp án:</div>'
            + inputs + '<div class="opts">' + labels + '</div>'
            '<div class="fb fb-right">&#127881; Chính xác! ' + explain + '</div>'
            '<div class="fb fb-wrong">&#9888;&#65039; Chưa đúng &mdash; ô tô XANH là '
            'đáp án đúng. ' + explain + '</div>'
            '<style>' + css + '</style></div>')


# ---------------------------------------------------------------------------
#  SVG MÔ PHỎNG (self-contained, viewBox, responsive)
# ---------------------------------------------------------------------------
def _house(cx):
    """Khung NHA (than + mai), day than o y=150 (mat dat cho cac mat cat mong)."""
    x = cx - 92
    return ('<rect x="' + str(x) + '" y="92" width="184" height="58" fill="#eef2f7" stroke="#94a3b8"/>'
            '<polygon points="' + str(cx - 106) + ',92 ' + str(cx) + ',54 ' + str(cx + 106) + ',92" '
            'fill="#cbd5e1" stroke="#94a3b8"/>'
            '<rect x="' + str(cx - 14) + '" y="112" width="28" height="38" fill="#c7d2fe"/>'
            '<text x="' + str(cx) + '" y="86" font-size="12" fill="#334155" '
            'font-weight="800" text-anchor="middle">NHÀ</text>')


def _svg_intro():
    return (
        '<svg viewBox="0 0 560 300" width="560" role="img" aria-label="Mong do va truyen tai trong xuong nen dat">'
        '<rect x="0" y="196" width="560" height="104" fill="#d9c9a3"/>'
        '<line x1="0" y1="196" x2="560" y2="196" stroke="#a1824a" stroke-width="2"/>'
        '<text x="465" y="222" font-size="12" fill="#7c5a1e" font-weight="700">NỀN ĐẤT</text>'
        # nha
        '<rect x="185" y="96" width="190" height="100" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        '<polygon points="170,96 280,44 390,96" fill="#cbd5e1" stroke="#94a3b8" stroke-width="2"/>'
        '<rect x="215" y="120" width="34" height="40" fill="#c7d2fe"/>'
        '<rect x="311" y="120" width="34" height="40" fill="#c7d2fe"/>'
        '<text x="280" y="112" font-size="16" fill="#334155" font-weight="900" text-anchor="middle">NGÔI NHÀ</text>'
        # mong (chim duoi dat)
        '<polygon points="210,196 350,196 335,258 225,258" fill="#64748b"/>'
        '<text x="280" y="234" font-size="13" fill="#fff" font-weight="800" text-anchor="middle">MÓNG</text>'
        # mui ten tai trong
        '<g stroke="#dc2626" stroke-width="5">'
        '<line x1="250" y1="150" x2="250" y2="250"/><line x1="310" y1="150" x2="310" y2="250"/></g>'
        '<polygon points="240,248 260,248 250,268" fill="#dc2626"/>'
        '<polygon points="300,248 320,248 310,268" fill="#dc2626"/>'
        '<text x="398" y="150" font-size="12" fill="#b91c1c" font-weight="700">Tải trọng cả</text>'
        '<text x="398" y="167" font-size="12" fill="#b91c1c" font-weight="700">ngôi nhà</text>'
        '<text x="360" y="278" font-size="12" fill="#7c5a1e" font-weight="700">truyền xuống nền đất</text>'
        '</svg>')


def _svg_dat():
    return (
        '<svg viewBox="0 0 580 250" width="580" role="img" aria-label="Dat lien tho va dat yeu">'
        # DAT LIEN THO
        '<rect x="20" y="50" width="250" height="170" fill="#c9a86a"/>'
        '<g fill="#a9863f">'
        '<circle cx="70" cy="95" r="4"/><circle cx="150" cy="120" r="4"/><circle cx="220" cy="90" r="4"/>'
        '<circle cx="110" cy="170" r="4"/><circle cx="200" cy="160" r="4"/><circle cx="60" cy="150" r="4"/></g>'
        '<text x="145" y="42" font-size="14" fill="#166534" font-weight="900" text-anchor="middle">&#9989; ĐẤT LIỀN THỔ</text>'
        '<text x="145" y="205" font-size="12" fill="#5c4718" font-weight="700" text-anchor="middle">cứng tự nhiên, chịu lực tốt</text>'
        # DAT YEU
        '<rect x="310" y="50" width="250" height="170" fill="#bda66a"/>'
        # ao/nuoc + bun
        '<rect x="310" y="50" width="250" height="46" fill="#7dd3fc" opacity="0.75"/>'
        '<path d="M310 96 Q360 86 410 96 T510 96 T560 96 L560 130 L310 130 Z" fill="#8a7b52"/>'
        '<g stroke="#38bdf8" stroke-width="2" fill="none">'
        '<path d="M330 70 q12 -6 24 0 t24 0 t24 0"/><path d="M430 78 q12 -6 24 0 t24 0 t24 0"/></g>'
        '<text x="435" y="42" font-size="14" fill="#b91c1c" font-weight="900" text-anchor="middle">&#9888;&#65039; ĐẤT YẾU</text>'
        '<text x="435" y="205" font-size="12" fill="#5c4718" font-weight="700" text-anchor="middle">ao hồ, san lấp, có bùn nước</text>'
        '</svg>')


def _svg_mong_don():
    svg = ('<svg viewBox="0 0 620 300" width="620" role="img" aria-label="Mong don - 3 bo phan">')
    svg += ('<rect x="0" y="150" width="620" height="150" fill="#d9c9a3"/>'
            '<line x1="0" y1="150" x2="620" y2="150" stroke="#a1824a" stroke-width="2"/>'
            '<text x="12" y="290" font-size="11" fill="#7c5a1e" font-weight="700">Đất cứng, liền thổ</text>')
    svg += _house(310)
    # dam mong (khoa cac de) - ngay duoi mat dat
    svg += '<rect x="120" y="156" width="380" height="14" fill="#334155"/>'
    # 3 de tach roi + doan cot
    for cx in (170, 310, 450):
        svg += '<rect x="' + str(cx - 10) + '" y="170" width="20" height="42" fill="#475569"/>'
        svg += '<rect x="' + str(cx - 40) + '" y="212" width="80" height="24" fill="#64748b"/>'
    # nhan
    svg += ('<text x="310" y="150" font-size="0"> </text>'
            '<text x="512" y="166" font-size="11" fill="#0f172a" font-weight="800">DẦM MÓNG</text>'
            '<text x="512" y="182" font-size="10.5" fill="#475569">khóa các đế</text>'
            '<text x="170" y="256" font-size="11" fill="#0f172a" font-weight="800" text-anchor="middle">ĐẾ MÓNG</text>'
            '<text x="170" y="272" font-size="10.5" fill="#dc2626" font-weight="700" text-anchor="middle">tách rời</text>'
            '<text x="380" y="205" font-size="11" fill="#0f172a" font-weight="800">ĐOẠN CỘT</text>')
    return svg + '</svg>'


def _svg_mong_bang():
    svg = ('<svg viewBox="0 0 620 300" width="620" role="img" aria-label="Mong bang - de chay dai lien mach">')
    svg += ('<rect x="0" y="150" width="620" height="150" fill="#d9c9a3"/>'
            '<line x1="0" y1="150" x2="620" y2="150" stroke="#a1824a" stroke-width="2"/>'
            '<text x="12" y="290" font-size="11" fill="#7c5a1e" font-weight="700">Đất cứng, liền thổ</text>')
    svg += _house(310)
    # dam mong lien
    svg += '<rect x="110" y="156" width="400" height="14" fill="#334155"/>'
    # doan cot
    for cx in (170, 310, 450):
        svg += '<rect x="' + str(cx - 10) + '" y="170" width="20" height="40" fill="#475569"/>'
    # de chay dai lien mach (1 dai)
    svg += '<polygon points="118,210 502,210 516,236 104,236" fill="#64748b"/>'
    svg += ('<text x="522" y="166" font-size="11" fill="#0f172a" font-weight="800">DẦM MÓNG</text>'
            '<text x="522" y="182" font-size="10.5" fill="#475569">liền với đế</text>'
            '<text x="310" y="256" font-size="11" fill="#0f172a" font-weight="800" text-anchor="middle">ĐẾ MÓNG</text>'
            '<text x="310" y="272" font-size="10.5" fill="#16a34a" font-weight="700" text-anchor="middle">chạy dài liền mạch</text>')
    return svg + '</svg>'


def _svg_mong_coc():
    svg = ('<svg viewBox="0 0 620 320" width="620" role="img" aria-label="Mong coc - coc + dai + dam">')
    # 2 lop dat
    svg += ('<rect x="0" y="150" width="620" height="80" fill="#fde68a"/>'
            '<rect x="0" y="230" width="620" height="90" fill="#86efac"/>'
            '<line x1="0" y1="150" x2="620" y2="150" stroke="#a1824a" stroke-width="2"/>'
            '<text x="12" y="172" font-size="11" fill="#92400e" font-weight="700">ĐẤT YẾU (ao hồ, san lấp)</text>'
            '<text x="12" y="252" font-size="11" fill="#166534" font-weight="700">ĐẤT TỐT (lớp chịu lực)</text>')
    svg += _house(310)
    # dam mong
    svg += '<rect x="150" y="156" width="320" height="14" fill="#334155"/>'
    # 2 dai mong roi + coc xuong dat tot
    for cx in (215, 405):
        svg += '<rect x="' + str(cx - 34) + '" y="170" width="68" height="20" fill="#64748b"/>'
        svg += '<rect x="' + str(cx - 24) + '" y="190" width="12" height="72" fill="#475569"/>'
        svg += '<rect x="' + str(cx + 12) + '" y="190" width="12" height="72" fill="#475569"/>'
    svg += ('<text x="480" y="166" font-size="11" fill="#0f172a" font-weight="800">DẦM MÓNG</text>'
            '<text x="215" y="150" font-size="0"> </text>'
            '<text x="405" y="210" font-size="11" fill="#0f172a" font-weight="800" text-anchor="middle">ĐÀI MÓNG</text>'
            '<text x="405" y="150" font-size="0"> </text>'
            '<text x="300" y="300" font-size="11" fill="#1e3a8a" font-weight="800" text-anchor="middle">CỌC BÊ TÔNG ép xuống tận đất tốt (chi phí phát sinh)</text>')
    return svg + '</svg>'


def _svg_compare():
    svg = ('<svg viewBox="0 0 640 300" width="640" role="img" aria-label="Truc do phuc tap va chi phi 3 loai mong">')
    svg += ('<line x1="40" y1="262" x2="600" y2="262" stroke="#94a3b8" stroke-width="2"/>')
    bars = [(70, 210, '#16a34a', 'MÓNG ĐƠN', '1 tầng', 'Rẻ nhất'),
            (270, 160, '#d97706', 'MÓNG BĂNG', '2-3 tầng', 'Trung bình'),
            (470, 100, '#dc2626', 'MÓNG CỌC', '2-5 tầng', 'Đắt hơn')]
    for x, top, c, name, tang, cost in bars:
        h = 262 - top
        svg += ('<rect x="' + str(x) + '" y="' + str(top) + '" width="110" height="' + str(h) + '" '
                'rx="8" fill="' + c + '" opacity="0.9"/>')
        svg += ('<text x="' + str(x + 55) + '" y="' + str(top - 8) + '" font-size="13" fill="' + c + '" '
                'font-weight="900" text-anchor="middle">' + name + '</text>')
        svg += ('<text x="' + str(x + 55) + '" y="' + str(top + 26) + '" font-size="12" fill="#fff" '
                'font-weight="800" text-anchor="middle">' + tang + '</text>')
        svg += ('<text x="' + str(x + 55) + '" y="' + str(top + 46) + '" font-size="11.5" fill="#fff" '
                'text-anchor="middle">' + cost + '</text>')
    # mui ten cheo di len
    svg += ('<line x1="60" y1="250" x2="592" y2="80" stroke="#4338ca" stroke-width="3" stroke-dasharray="6 5"/>'
            '<polygon points="592,80 576,84 586,96" fill="#4338ca"/>'
            '<text x="150" y="52" font-size="12.5" fill="#4338ca" font-weight="800">Đất càng yếu / nhà càng cao '
            '&rarr; móng càng phức tạp &rarr; càng ĐẮT</text>')
    return svg + '</svg>'


def _svg_coc_betong():
    return (
        '<svg viewBox="0 0 580 240" width="580" role="img" aria-label="Coc be tong duc san">'
        # coc nam ngang + mui coc
        '<rect x="60" y="80" width="360" height="44" fill="#94a3b8" stroke="#475569" stroke-width="2"/>'
        '<polygon points="420,80 470,102 420,124" fill="#64748b" stroke="#475569" stroke-width="2"/>'
        # thep trong coc
        '<g stroke="#e2e8f0" stroke-width="2">'
        '<line x1="70" y1="92" x2="410" y2="92"/><line x1="70" y1="112" x2="410" y2="112"/></g>'
        # dim chieu dai
        '<line x1="60" y1="150" x2="470" y2="150" stroke="#1d4ed8" stroke-width="2"/>'
        '<line x1="60" y1="144" x2="60" y2="156" stroke="#1d4ed8" stroke-width="2"/>'
        '<line x1="470" y1="144" x2="470" y2="156" stroke="#1d4ed8" stroke-width="2"/>'
        '<text x="265" y="170" font-size="13" fill="#1d4ed8" font-weight="800" text-anchor="middle">Dài 5 - 6 m mỗi đoạn</text>'
        # mat cat vuong
        '<rect x="60" y="185" width="46" height="46" fill="#94a3b8" stroke="#475569" stroke-width="2"/>'
        '<text x="200" y="205" font-size="13" fill="#0f172a" font-weight="800">Tiết diện: 20x20 cm và 25x25 cm</text>'
        '<text x="200" y="225" font-size="12" fill="#475569">Giá: Miền Bắc ~200k/m &middot; Miền Nam ~270k/m (1 mét dài)</text>'
        '</svg>')


def _svg_ep_tai_neo():
    svg = ('<svg viewBox="0 0 680 300" width="680" role="img" aria-label="Ep tai va ep neo">')
    svg += ('<rect x="0" y="200" width="680" height="100" fill="#d9c9a3"/>'
            '<line x1="0" y1="200" x2="680" y2="200" stroke="#a1824a" stroke-width="2"/>'
            '<line x1="340" y1="30" x2="340" y2="285" stroke="#cbd5e1" stroke-dasharray="3 4"/>')
    # --- EP TAI (trai) ---
    # doi trong xep chong
    for i, y in enumerate((60, 82, 104)):
        svg += '<rect x="115" y="' + str(y) + '" width="130" height="18" fill="#6b7280" stroke="#374151"/>'
    svg += '<text x="180" y="52" font-size="11" fill="#374151" font-weight="800" text-anchor="middle">ĐỐI TRỌNG (tải)</text>'
    # coc
    svg += '<rect x="172" y="122" width="16" height="140" fill="#475569"/>'
    # mui ten de xuong
    svg += ('<line x1="180" y1="126" x2="180" y2="150" stroke="#dc2626" stroke-width="5"/>'
            '<polygon points="172,148 188,148 180,164" fill="#dc2626"/>')
    svg += ('<text x="180" y="288" font-size="14" fill="#1d4ed8" font-weight="900" text-anchor="middle">ÉP TẢI</text>'
            '<text x="300" y="150" font-size="11.5" fill="#166534" font-weight="800">60-120 tấn</text>'
            '<text x="300" y="170" font-size="11" fill="#475569">hẻm &ge; 2,5m</text>'
            '<text x="300" y="188" font-size="11" fill="#475569">~30 triệu/ca</text>'
            '<text x="300" y="230" font-size="11" fill="#dc2626" font-weight="700">rung đất,</text>'
            '<text x="300" y="246" font-size="11" fill="#dc2626" font-weight="700">dễ nứt nhà bên</text>')
    # --- EP NEO (phai) ---
    # khung + neo khoan cheo 2 ben
    svg += '<rect x="440" y="96" width="150" height="14" fill="#6b7280" stroke="#374151"/>'
    svg += ('<line x1="455" y1="110" x2="430" y2="262" stroke="#334155" stroke-width="7"/>'
            '<line x1="575" y1="110" x2="600" y2="262" stroke="#334155" stroke-width="7"/>')
    svg += '<text x="515" y="88" font-size="11" fill="#374151" font-weight="800" text-anchor="middle">NEO KHOAN GIỮ</text>'
    # coc giua
    svg += '<rect x="507" y="112" width="16" height="150" fill="#475569"/>'
    svg += ('<line x1="515" y1="116" x2="515" y2="150" stroke="#dc2626" stroke-width="5"/>'
            '<polygon points="507,148 523,148 515,164" fill="#dc2626"/>')
    svg += ('<text x="515" y="288" font-size="14" fill="#1d4ed8" font-weight="900" text-anchor="middle">ÉP NEO</text>'
            '<text x="628" y="150" font-size="11.5" fill="#334155" font-weight="800">40 tấn</text>'
            '<text x="628" y="170" font-size="11" fill="#475569">hẻm &lt; 1,5m</text>'
            '<text x="628" y="188" font-size="11" fill="#475569">~15 triệu/ca</text>'
            '<text x="628" y="230" font-size="11" fill="#16a34a" font-weight="700">không ảnh</text>'
            '<text x="628" y="246" font-size="11" fill="#16a34a" font-weight="700">hưởng hàng xóm</text>')
    return svg + '</svg>'


class SlideChannelSeedMong(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_mong(self):
        ch = self.env.ref('vd_elearning.course_a2', raise_if_not_found=False)
        if not ch:
            return False

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _MO_VERSION:
            return True

        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-mong" style="%s">%s</div>'
                                 % (_WRAP, self._mng_app())),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._mng_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _MO_VERSION)
        return True

    # ==================================================================
    #  APP (menu trái + panel phải)
    # ==================================================================
    def _mng_app(self):
        lessons = self._mng_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'mngL' + str(i)
            pid = 'mngP' + str(i)
            radios += ('<input class="navr" type="radio" name="mngnav" id="' + rid + '"'
                       + (' checked' if i == 0 else '') + '>')
            badge_html = ('<span class="vc-nbadge">' + badge + '</span>') if badge else ''
            navbtns += ('<label class="vc-navbtn" for="' + rid + '">' + badge_html
                        + '<span class="vc-ntitle">' + icon + ' ' + title + '</span></label>')
            panels += '<section class="vc-panel" id="' + pid + '">' + body + '</section>'
            rules += '#' + rid + ':checked ~ .vc-layout #' + pid + '{display:block}'
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + ']'
                      '{background:#4338ca;color:#fff;border-color:#4338ca}')
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + '] .vc-nbadge'
                      '{background:#ffffff;color:#4338ca}')
        hero = (
            '<div style="background:linear-gradient(120deg,#1e3a8a 0%,#4338ca 55%,#6d28d9 100%);'
            'border-radius:16px;padding:24px 26px;margin-bottom:14px;'
            'box-shadow:0 10px 30px rgba(67,56,202,.28);">'
            '<div style="color:#dbeafe;font-size:13px;font-weight:800;letter-spacing:2px;">'
            'KIẾN THỨC XÂY DỰNG &mdash; DÀNH CHO SALE (KỂ CẢ TRÁI NGÀNH)</div>'
            '<div style="color:#fff;font-size:26px;font-weight:900;margin-top:6px;line-height:1.2;'
            'text-shadow:0 2px 8px rgba(0,0,0,.15);">'
            'MÓNG NHÀ &mdash; hiểu để tư vấn đúng và giải thích được chi phí</div>'
            '<div style="color:#eef2ff;font-size:14.5px;margin-top:9px;">'
            '&#127959;&#65039; <b>Đất nào &rarr; móng đó &rarr; chi phí đó.</b> &#128073; Bấm từng mục ở '
            'MENU BÊN TRÁI để học lần lượt &mdash; mỗi bài có hình mô phỏng, công thức và trắc nghiệm chấm ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _mng_tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    def _mng_lessons(self):
        return [
            ('&#129504;', 'MỞ ĐẦU', 'Móng là gì? Vì sao sale phải biết', self._mng_l_intro()),
            ('&#127957;&#65039;', 'BÀI 1', 'Đất thi công: liền thổ vs yếu', self._mng_l_dat()),
            ('&#129513;', 'BÀI 2', 'Móng đơn (3 bộ phận)', self._mng_l_don()),
            ('&#12310;&#12311;', 'BÀI 3', 'Móng băng (2 bộ phận)', self._mng_l_bang()),
            ('&#128204;', 'BÀI 4', 'Móng cọc (đất yếu)', self._mng_l_coc()),
            ('&#128202;', 'BÀI 5', 'So sánh nhanh 3 loại móng', self._mng_l_compare()),
            ('&#128295;', 'BÀI 6', 'Cọc bê tông + Ép tải vs Ép neo', self._mng_l_epcoc()),
            ('&#127942;', 'TỔNG KẾT', 'Cọc ít dùng + Nhận biết nhanh', self._mng_l_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỞ ĐẦU
    # ------------------------------------------------------------------
    def _mng_l_intro(self):
        return (
            self._mng_tag('KIẾN THỨC NỀN TẢNG')
            + '<h3>&#8220;Móng&#8221; là gì và vì sao SALE bắt buộc phải hiểu?</h3>'
            + '<p><b>Móng</b> là <b>phần nằm dưới cùng của ngôi nhà, chìm dưới mặt đất</b>, có '
            'nhiệm vụ <b>đỡ toàn bộ sức nặng của căn nhà và truyền xuống nền đất</b>. Móng yếu '
            'thì nhà nứt, lún, nghiêng &mdash; nên đây là phần <b>quan trọng nhất</b> quyết '
            'định nhà bền hay không.</p>'
            + _fig('Móng đỡ và truyền tải trọng xuống nền đất', _svg_intro(),
                   'Toàn bộ sức nặng của ngôi nhà dồn xuống móng, móng truyền tiếp xuống nền đất.')
            + _box('info', '<b>Vì sao sale phải biết về móng?</b> Vì <b>loại ĐẤT</b> của khách '
                   'quyết định <b>loại MÓNG</b>, mà loại móng ảnh hưởng trực tiếp đến <b>CHI '
                   'PHÍ</b>. Hiểu móng, bạn mới giải thích được vì sao báo giá cao/thấp và tư '
                   'vấn đúng &mdash; khách sẽ tin bạn là người chuyên nghiệp.')
            + '<h4>&#128209; Toàn khóa gồm gì?</h4>'
            + _table(['Phần', 'Nội dung'],
                     [['<b>Đất thi công</b>', 'Đất liền thổ &middot; Đất yếu'],
                      ['<b>3 loại móng</b>', 'Móng đơn &middot; Móng băng &middot; Móng cọc'],
                      ['<b>Ép cọc bê tông</b>', 'Cọc đúc sẵn &middot; Ép tải &middot; Ép neo'],
                      ['<b>Cọc ít dùng</b>', 'Cọc tre / cừ tràm &middot; Cọc khoan nhồi']],
                     widths=['28%', '72%'])
            + _core('Móng = phần dưới cùng đỡ cả ngôi nhà. <b>Đất nào &rarr; móng đó &rarr; chi phí đó.</b>')
            + _fml('Muốn tư vấn đúng: hỏi <b>ĐẤT gì</b> (thổ cư lâu năm hay san lấp/phân lô) + '
                   '<b>nhà MẤY TẦNG</b> &rarr; suy ra loại móng &rarr; giải thích được chi phí.')
            + _quiz('mng_intro',
                    'Vì sao nhân viên SALE cần hiểu về móng?',
                    [('Vì loại ĐẤT quyết định loại MÓNG, mà loại móng ảnh hưởng trực tiếp đến CHI PHÍ báo giá', True),
                     ('Vì sale phải tự đi thi công móng cho khách', False),
                     ('Vì để thay kỹ sư thiết kế kết cấu', False),
                     ('Không cần biết, cứ báo giá đại là được', False)],
                    'Hiểu móng để giải thích chi phí và tư vấn đúng: đất nào → móng đó → chi phí đó.'))

    # ------------------------------------------------------------------
    #  BÀI 1 - ĐẤT
    # ------------------------------------------------------------------
    def _mng_l_dat(self):
        return (
            self._mng_tag('BÀI 1 &mdash; ĐẤT THI CÔNG')
            + '<h3>Trước khi chọn móng, phải biết ĐẤT của khách là loại nào</h3>'
            + '<p>Đất là yếu tố <b>quyết định đầu tiên</b>. Có <b>2 loại đất</b> cần phân biệt: '
            '<b>đất liền thổ</b> (cứng) và <b>đất yếu</b> (ao hồ, san lấp).</p>'
            + _fig('Đất liền thổ vs Đất yếu', _svg_dat(),
                   'Đất liền thổ cứng tự nhiên, chịu lực tốt; đất yếu có bùn nước, không đỡ nổi nhà nếu không ép cọc.')
            + _photos('Hình thực tế', [('image24.jpg', 'Đất liền thổ (cứng tự nhiên)'),
                                       ('image16.jpg', 'Đất yếu (ao hồ, san lấp)')])
            + _table(['Tiêu chí', 'ĐẤT LIỀN THỔ', 'ĐẤT YẾU'],
                     [['<b>Bản chất</b>', 'Đất <b>cứng tự nhiên</b>, chưa đào bới san lấp',
                       'Đất <b>ao hồ, san lấp</b>, có bùn, ẩm'],
                      ['<b>Ví dụ</b>', 'Đất thổ cư cứng lâu năm',
                       'Đất phân lô khu đô thị san từ ruộng ao, đất ven sông'],
                      ['<b>Móng phù hợp</b>', '<span class="cheap">Móng đơn / Móng băng</span>',
                       '<span class="exp">Móng cọc (bắt buộc)</span>']],
                     widths=['24%', '38%', '38%'])
            + _box('warn', '<b>Phân tích:</b> đất yếu có lớp bùn/nước, gần như <b>không chịu '
                   'lực</b>. Nếu đặt móng nông (đơn/băng) lên đất yếu, nhà sẽ <b>lún và '
                   'nghiêng</b>. Bắt buộc phải <b>ép cọc</b> xuyên qua lớp yếu, cắm xuống lớp '
                   'đất tốt bên dưới để &#8220;gánh&#8221; nhà.')
            + _box('ok', '<b>Mẹo hỏi khách:</b> &#8220;Đất nhà mình là đất thổ cư cứng lâu năm '
                   'hay đất mới san lấp / phân lô ạ?&#8221; &mdash; câu này đủ để biết hướng '
                   'móng và chi phí.')
            + _wrong([
                'Không hỏi đất, mặc định báo giá móng rẻ (đơn/băng) cho khách đất yếu &rarr; sai kết cấu, phát sinh lớn về sau.',
                'Nhầm &#8220;đất phân lô khu đô thị&#8221; là đất cứng (thực ra thường san lấp &rarr; đất yếu).'])
            + _core('Đất <b>liền thổ</b> (cứng) &rarr; móng đơn/băng. Đất <b>yếu</b> (ao hồ, san lấp) &rarr; <b>phải dùng móng cọc</b>.')
            + _fml('Đất YẾU = có bùn/nước, không chịu lực &rarr; <b>ÉP CỌC</b> xuống lớp đất tốt. '
                   'Đất CỨNG (liền thổ) &rarr; móng nông (đơn/băng) là đủ.')
            + _quiz('mng_dat',
                    'Đất yếu (ao hồ, san lấp) thì BẮT BUỘC dùng loại móng nào?',
                    [('Móng cọc &mdash; ép cọc xuyên lớp yếu xuống lớp đất tốt', True),
                     ('Móng đơn cho rẻ', False),
                     ('Móng băng là đủ', False),
                     ('Móng đơn hoặc băng đều được', False)],
                    'Đất yếu không chịu lực → phải ép cọc (móng cọc) xuống lớp đất tốt.'))

    # ------------------------------------------------------------------
    #  BÀI 2 - MÓNG ĐƠN
    # ------------------------------------------------------------------
    def _mng_l_don(self):
        return (
            self._mng_tag('BÀI 2 &mdash; MÓNG ĐƠN (móng cốc)')
            + '<h3>Móng đơn: 3 bộ phận, các đế TÁCH RỜI &mdash; rẻ nhất</h3>'
            + _fig('Mặt cắt móng đơn &mdash; 3 bộ phận', _svg_mong_don(),
                   'Các đế móng tách rời từng cục, nối lên dầm móng bằng đoạn cột; dầm móng khóa các đế lại.')
            + _photos('Hình thực tế móng đơn', [('image30.jpg', ''), ('image25.jpg', ''),
                                                ('image26.jpg', ''), ('image15.jpg', '')])
            + '<h4>Gồm 3 bộ phận</h4>'
            + _order([
                ('ĐẾ MÓNG', 'Các đế móng KHÔNG liên kết với nhau &mdash; tách rời từng cục (đặt dưới mỗi cột).'),
                ('ĐOẠN CỘT', 'Nối đế móng với dầm móng bằng một đoạn cột.'),
                ('DẦM MÓNG', 'Khóa các đế móng lại với nhau cho ổn định.'),
            ])
            + _table(['Thông tin', 'Chi tiết'],
                     [['<b>Áp dụng</b>', 'Đất <b>cứng, liền thổ</b>'],
                      ['<b>Chi phí</b>', '<span class="cheap">RẺ NHẤT</span> trong 3 loại móng (ít bê tông, đế nhỏ tách rời)'],
                      ['<b>Sử dụng</b>', 'Nhà <b>1 tầng</b> (2 tầng nếu tài chính thấp)']],
                     widths=['26%', '74%'])
            + _box('info', '<b>Vì sao rẻ nhất?</b> Đế tách rời, kích thước nhỏ, tốn ít bê tông '
                   'và thép hơn hẳn móng băng (đế chạy dài) hay móng cọc (thêm tiền cọc).')
            + _wrong([
                'Nhầm móng đơn có <b>2 bộ phận</b> (đó là móng băng) &mdash; móng đơn có <b>3</b>.',
                'Tư vấn móng đơn cho nhà cao tầng / đất yếu &mdash; sai, móng đơn chỉ hợp nhà thấp trên đất cứng.'])
            + _core('Móng đơn = <b>3 bộ phận</b> &middot; đế <b>tách rời</b> &middot; đất cứng &middot; <b>rẻ nhất</b> &middot; nhà 1 tầng.')
            + _fml('MÓNG ĐƠN &rarr; nhớ số <b>3</b> (3 bộ phận) + <b>tách rời</b> + <b>rẻ nhất</b> + <b>1 tầng</b>.')
            + _quiz('mng_don',
                    'Đặc điểm ĐẾ MÓNG của móng ĐƠN và số bộ phận là gì?',
                    [('3 bộ phận; các đế móng tách rời, không liên kết với nhau', True),
                     ('2 bộ phận; đế móng chạy dài liền mạch', False),
                     ('3 bộ phận; đế móng nằm trên cọc bê tông', False),
                     ('1 bộ phận duy nhất', False)],
                    'Móng đơn = 3 bộ phận (đế, đoạn cột, dầm); đế tách rời từng cục.'))

    # ------------------------------------------------------------------
    #  BÀI 3 - MÓNG BĂNG
    # ------------------------------------------------------------------
    def _mng_l_bang(self):
        return (
            self._mng_tag('BÀI 3 &mdash; MÓNG BĂNG')
            + '<h3>Móng băng: 2 bộ phận, đế CHẠY DÀI LIỀN MẠCH &mdash; trung bình</h3>'
            + _fig('Mặt cắt móng băng &mdash; 2 bộ phận', _svg_mong_bang(),
                   'Đế móng chạy dài liền mạch (không tách rời), dầm móng liền với đế.')
            + _photos('Hình thực tế móng băng', [('image20.jpg', ''), ('image17.jpg', ''),
                                                 ('image18.jpg', ''), ('image23.jpg', '')])
            + '<h4>Gồm 2 bộ phận</h4>'
            + _order([
                ('ĐẾ MÓNG', 'Đế móng CHẠY DÀI, LIỀN MẠCH (không tách rời từng cục như móng đơn).'),
                ('DẦM MÓNG', 'Liền với đế móng.'),
            ])
            + _table(['Thông tin', 'Chi tiết'],
                     [['<b>Áp dụng</b>', 'Đất <b>cứng, liền thổ</b>'],
                      ['<b>Chi phí</b>', '<span class="mid">TRUNG BÌNH</span> (đế chạy dài nên tốn hơn móng đơn)'],
                      ['<b>Sử dụng</b>', 'Nhà <b>2 - 3 tầng</b>']],
                     widths=['26%', '74%'])
            + _box('info', '<b>Phân biệt nhanh với móng đơn:</b> móng đơn có đế <b>tách rời '
                   'từng cục</b> (3 bộ phận), còn móng băng có đế <b>chạy dài liền mạch</b> '
                   '(2 bộ phận). Đế liền mạch giúp phân bố lực đều hơn &rarr; đỡ được nhà cao '
                   'tầng hơn móng đơn.')
            + _wrong([
                'Nhầm móng băng <b>3 bộ phận</b> &mdash; móng băng chỉ có <b>2</b> (đế + dầm).',
                'Nhầm đế móng băng là &#8220;tách rời&#8221; &mdash; đế móng băng <b>chạy dài liền mạch</b>.'])
            + _core('Móng băng = <b>2 bộ phận</b> &middot; đế <b>chạy dài liền mạch</b> &middot; đất cứng &middot; <b>trung bình</b> &middot; nhà 2-3 tầng.')
            + _fml('MÓNG BĂNG &rarr; nhớ số <b>2</b> (2 bộ phận) + <b>liền mạch</b> + <b>trung bình</b> + <b>2-3 tầng</b>.')
            + _quiz('mng_bang',
                    'Móng BĂNG khác móng ĐƠN ở điểm cốt lõi nào?',
                    [('Móng băng 2 bộ phận, đế chạy dài liền mạch; móng đơn 3 bộ phận, đế tách rời', True),
                     ('Móng băng dùng cho đất yếu, móng đơn cho đất cứng', False),
                     ('Móng băng có cọc bê tông, móng đơn thì không', False),
                     ('Hai loại giống hệt nhau', False)],
                    'Móng băng = 2 bộ phận, đế liền mạch; móng đơn = 3 bộ phận, đế tách rời.'))

    # ------------------------------------------------------------------
    #  BÀI 4 - MÓNG CỌC
    # ------------------------------------------------------------------
    def _mng_l_coc(self):
        return (
            self._mng_tag('BÀI 4 &mdash; MÓNG CỌC')
            + '<h3>Móng cọc: dùng cho ĐẤT YẾU &mdash; ép cọc xuống lớp đất tốt</h3>'
            + '<p>Khi đất yếu (ao hồ, san lấp) thì phải <b>ép cọc xuống sâu</b> tới lớp đất '
            'cứng để giữ nhà. Phía trên cọc là phần móng.</p>'
            + _fig('Mặt cắt móng cọc &mdash; cọc + đài + dầm', _svg_mong_coc(),
                   'Cọc bê tông xuyên lớp đất yếu, cắm xuống lớp đất tốt; đài móng đặt trên đầu cọc, dầm móng liền đài.')
            + _photos('Hình thực tế móng cọc', [('image27.jpg', ''), ('image29.jpg', ''),
                                                ('image28.png', '')])
            + '<h4>Các bộ phận</h4>'
            + _order([
                ('CỌC BÊ TÔNG', 'Ép sâu xuống đất tới lớp chịu lực &mdash; là CHI PHÍ PHÁT SINH thêm của móng cọc.'),
                ('ĐÀI MÓNG', 'Đế móng thu về thành đài móng, đặt trên đầu cọc; các đài KHÔNG liền nhau.'),
                ('DẦM MÓNG', 'Liền với đài móng.'),
            ])
            + _table(['Thông tin', 'Chi tiết'],
                     [['<b>Áp dụng</b>', 'Đất <b>yếu, ao hồ san lấp</b>'],
                      ['<b>Chi phí</b>', 'Phần đài + dầm <b>bằng móng băng</b>, nhưng <span class="exp">ĐẮT HƠN</span> vì phát sinh <b>tiền cọc bê tông</b>'],
                      ['<b>Sử dụng</b>', 'Nhà <b>2 - 5 tầng</b>']],
                     widths=['26%', '74%'])
            + _box('warn', '<b>Điểm khách hay thắc mắc:</b> &#8220;sao báo giá đắt hơn?&#8221; '
                   '&mdash; vì đất yếu bắt buộc ép cọc, phát sinh <b>tiền cọc bê tông</b> so '
                   'với nhà làm móng băng/đơn trên đất cứng. Giải thích rõ để khách hiểu là '
                   'tiền đó mua sự AN TOÀN, chống lún nghiêng.')
            + _wrong([
                'Nói móng cọc &#8220;đắt vô lý&#8221; mà không giải thích được <b>tiền cọc bê tông</b> là khoản phát sinh.',
                'Tư vấn móng đơn/băng cho đất yếu để &#8220;giá rẻ&#8221; &mdash; nhà sẽ lún, hậu quả nặng.'])
            + _core('Móng cọc = <b>đất yếu</b> &middot; có <b>cọc bê tông</b> ép xuống + đài móng + dầm &middot; <b>đắt hơn</b> (tiền cọc) &middot; nhà 2-5 tầng.')
            + _fml('MÓNG CỌC &rarr; <b>ĐẤT YẾU</b> + <b>CỌC</b> (đài + dầm như móng băng) + <b>đắt hơn vì tiền cọc</b> + <b>2-5 tầng</b>.')
            + _quiz('mng_coc',
                    'Vì sao móng CỌC đắt hơn móng băng dù phần đài và dầm tương đương?',
                    [('Vì phát sinh thêm TIỀN CỌC bê tông ép xuống đất', True),
                     ('Vì dùng nhiều dầm móng hơn', False),
                     ('Vì đế móng chạy dài hơn', False),
                     ('Vì bắt buộc phải xây thêm 1 tầng', False)],
                    'Móng cọc đắt hơn vì phát sinh tiền cọc bê tông; phần đài + dầm tương đương móng băng.'))

    # ------------------------------------------------------------------
    #  BÀI 5 - SO SÁNH
    # ------------------------------------------------------------------
    def _mng_l_compare(self):
        return (
            self._mng_tag('BÀI 5 &mdash; SO SÁNH NHANH')
            + '<h3>3 loại móng trên một trục: đất càng yếu / nhà càng cao &rarr; càng đắt</h3>'
            + _fig('Trục độ phức tạp &amp; chi phí 3 loại móng', _svg_compare(),
                   'Móng đơn (rẻ, 1 tầng) → Móng băng (2-3 tầng) → Móng cọc (đất yếu, đắt nhất).')
            + _table(['Tiêu chí', 'Móng đơn', 'Móng băng', 'Móng cọc'],
                     [['<b>Số bộ phận</b>', '3', '2', 'Cọc + đài + dầm'],
                      ['<b>Đế móng</b>', 'Tách rời', 'Chạy dài liền mạch', 'Thu về đài móng (rời)'],
                      ['<b>Loại đất</b>', 'Cứng, liền thổ', 'Cứng, liền thổ', '<span class="exp">Yếu, ao hồ</span>'],
                      ['<b>Chi phí</b>', '<span class="cheap">Rẻ nhất</span>', '<span class="mid">Trung bình</span>', '<span class="exp">Đắt hơn (có cọc)</span>'],
                      ['<b>Số tầng</b>', '1 tầng', '2 - 3 tầng', '2 - 5 tầng']],
                     widths=['22%', '26%', '26%', '26%'])
            + _box('info', 'Nhớ theo trục: <b>đất càng yếu / nhà càng cao tầng &rarr; móng '
                   'càng phức tạp &rarr; càng đắt</b>. Móng đơn (1 tầng, rẻ) &rarr; móng băng '
                   '(2-3 tầng) &rarr; móng cọc (đất yếu, 2-5 tầng, đắt nhất).')
            + _core('Móng đơn <b>(3, tách rời, rẻ)</b> &rarr; móng băng <b>(2, liền mạch, TB)</b> &rarr; móng cọc <b>(cọc, đất yếu, đắt)</b>.')
            + _fml('Số bộ phận: đơn <b>3</b> &middot; băng <b>2</b> &middot; cọc <b>cọc+đài+dầm</b>. '
                   'Chi phí: đơn &lt; băng &lt; cọc. Đất yếu &rarr; luôn là móng cọc.')
            + _quiz('mng_cmp',
                    'Sắp xếp chi phí 3 loại móng từ rẻ đến đắt cho ĐÚNG?',
                    [('Móng đơn (rẻ nhất) &lt; Móng băng (trung bình) &lt; Móng cọc (đắt hơn, có cọc)', True),
                     ('Móng cọc &lt; Móng băng &lt; Móng đơn', False),
                     ('Móng băng &lt; Móng đơn &lt; Móng cọc', False),
                     ('Ba loại bằng giá nhau', False)],
                    'Rẻ → đắt: móng đơn < móng băng < móng cọc (móng cọc thêm tiền cọc).'))

    # ------------------------------------------------------------------
    #  BÀI 6 - CỌC BÊ TÔNG + ÉP TẢI / ÉP NEO
    # ------------------------------------------------------------------
    def _mng_l_epcoc(self):
        return (
            self._mng_tag('BÀI 6 &mdash; ÉP CỌC BÊ TÔNG')
            + '<h3>Cọc bê tông đúc sẵn &amp; 2 phương pháp ép: ÉP TẢI vs ÉP NEO</h3>'
            + '<h4>&#128295; Cọc bê tông đúc sẵn</h4>'
            + _fig('Cọc bê tông đúc sẵn &mdash; kích thước &amp; đơn giá', _svg_coc_betong(),
                   'Tiết diện 20x20 hoặc 25x25 cm, mỗi đoạn dài 5-6 m; giá theo mét dài.')
            + _photos('Hình thực tế cọc bê tông', [('image33.jpg', ''), ('image36.jpg', '')])
            + _table(['Thông tin', 'Chi tiết'],
                     [['<b>Tiết diện</b>', '<b>20x20 cm</b> và <b>25x25 cm</b>'],
                      ['<b>Chiều dài</b>', '<b>5 - 6 m</b> mỗi đoạn'],
                      ['<b>Đơn giá Miền Bắc</b>', 'Khoảng <b>200k / 1 m dài</b>'],
                      ['<b>Đơn giá Miền Nam</b>', 'Khoảng <b>270k / 1 m dài</b>']],
                     widths=['32%', '68%'])
            + '<h4>&#9878;&#65039; 2 phương pháp ép cọc</h4>'
            + _fig('Ép tải vs Ép neo', _svg_ep_tai_neo(),
                   'Ép tải dùng đối trọng đè (tải lớn nhưng rung đất); ép neo dùng neo khoan giữ (tải nhỏ, hợp hẻm nhỏ).')
            + _photos('Hình thực tế', [('image34.jpg', 'Ép tải (đối trọng)'),
                                       ('image39.jpg', 'Ép neo (neo khoan)')])
            + _table(['Tiêu chí', 'ÉP TẢI', 'ÉP NEO'],
                     [['<b>Cách làm</b>', 'Dùng máy có <b>đối trọng (tải)</b> đè cọc xuống', 'Dùng <b>neo khoan dẫn hướng</b> giữ khung rồi đóng cọc'],
                      ['<b>Tải trọng ép</b>', '<span class="cheap">60 - 120 tấn</span>', '<b>40 tấn</b>'],
                      ['<b>Ngõ hẻm</b>', 'Từ <b>2,5 m trở lên</b>', 'Dưới <b>1,5 m</b> (hẻm nhỏ vẫn làm được)'],
                      ['<b>Nhược điểm</b>', '<span class="exp">Rung đất, dễ nứt nhà bên cạnh</span>', '<span class="exp">Ép được tải trọng thấp</span>'],
                      ['<b>Ưu điểm</b>', 'Tải trọng lớn, chắc', '<b>Không ảnh hưởng nhà hàng xóm</b>'],
                      ['<b>Chi phí 1 ca ép</b>', 'Khoảng <b>30 triệu</b>', 'Khoảng <b>15 triệu</b>']],
                     widths=['24%', '38%', '38%'])
            + _box('warn', '<b>RẤT DỄ NHẦM SỐ LIỆU &mdash; nhớ theo cặp đối lập:</b> '
                   '<b>Ép TẢI</b> = tải LỚN (60-120 tấn), hẻm RỘNG (2,5m+), giá CAO (~30tr), '
                   'nhưng RUNG đất. <b>Ép NEO</b> = tải THẤP (40 tấn), hẻm NHỎ (dưới 1,5m), '
                   'giá THẤP (~15tr), KHÔNG ảnh hưởng hàng xóm.')
            + _wrong([
                'Đảo số: nói ép tải ~15tr / ép neo ~30tr (ngược &mdash; ép tải ~30tr, ép neo ~15tr).',
                'Nói ép neo dùng cho hẻm rộng &mdash; sai, ép neo là để hẻm NHỎ (dưới 1,5m).',
                'Quên cảnh báo ép tải <b>rung đất</b> có thể nứt nhà hàng xóm &rarr; tư vấn thiếu.'])
            + _core('Ép TẢI: 60-120 tấn &middot; hẻm &ge;2,5m &middot; ~30tr &middot; RUNG đất. '
                    'Ép NEO: 40 tấn &middot; hẻm &lt;1,5m &middot; ~15tr &middot; không ảnh hưởng hàng xóm.')
            + _fml('Cọc: <b>20x20 / 25x25 cm</b>, dài <b>5-6m</b>, giá <b>MB 200k / MN 270k</b> mỗi mét. '
                   'Ép TẢI (lớn, rộng, đắt, rung) &harr; Ép NEO (nhỏ, hẻm nhỏ, rẻ, êm).')
            + _quiz('mng_ep',
                    'Ngõ hẻm nhỏ dưới 1,5m, nhà sát vách hàng xóm sợ nứt &mdash; nên dùng phương pháp ép nào?',
                    [('Ép NEO &mdash; hợp hẻm nhỏ, không ảnh hưởng nhà hàng xóm (tải ~40 tấn, ~15tr)', True),
                     ('Ép TẢI &mdash; vì tải trọng lớn 60-120 tấn', False),
                     ('Ép nào cũng như nhau', False),
                     ('Không ép được, phải chuyển móng băng', False)],
                    'Hẻm nhỏ + sợ nứt nhà bên → Ép NEO (êm, không rung, hợp hẻm dưới 1,5m).'))

    # ------------------------------------------------------------------
    #  TỔNG KẾT
    # ------------------------------------------------------------------
    def _mng_l_gold(self):
        return (
            self._mng_tag('&#127942; TỔNG HỢP KIẾN THỨC')
            + '<h3>Cọc ít dùng (tham khảo) + Nhận biết nhanh khi tư vấn</h3>'
            + '<h4>Loại cọc ít sử dụng</h4>'
            + _table(['Loại cọc', 'Đặc điểm'],
                     [['<b>Cọc tre</b> (Miền Bắc) / <b>cọc cừ tràm</b> (Miền Nam)',
                       'Cọc tự nhiên, dài khoảng <b>2 m</b>, đơn giá <b>~500k / 1 m&#178; trọn gói</b>. '
                       'Yêu cầu nền đất phải <b>ẩm, nhiều nước</b> &mdash; đất khô lâu thì cọc sẽ <b>mục</b>.'],
                      ['<b>Cọc khoan nhồi</b> (cả nước)', 'Đơn giá <b>~700 - 800k / 1 m dài trọn gói</b>.']],
                     widths=['40%', '60%'])
            + _photos('Hình thực tế cọc ít dùng', [('image42.jpg', ''), ('image37.jpg', ''),
                                                   ('image40.jpg', ''), ('image44.jpg', '')])
            + _box('info', '<b>Miền Tây là miền sông nước</b> &rarr; nền đất rất yếu nên <b>gần '
                   'như 100% phải ép cọc</b>.')
            + _photos('Miền Tây sông nước', [('image45.jpg', 'Nền đất yếu, hầu hết phải ép cọc')])
            + '<h4>&#127919; NHẬN BIẾT NHANH &mdash; KỊCH BẢN TƯ VẤN</h4>'
            + _order([
                ('Hỏi ĐẤT', 'Đất thổ cư cứng lâu năm (liền thổ) hay đất san lấp / phân lô (yếu)?'),
                ('Đất CỨNG &rarr; móng nông', 'Nhà 1 tầng &rarr; móng đơn (rẻ nhất); nhà 2-3 tầng &rarr; móng băng.'),
                ('Đất YẾU &rarr; móng cọc', 'Ép cọc bê tông (2-5 tầng), giải thích đắt hơn vì tiền cọc.'),
                ('Chọn cách ép', 'Hẻm rộng (&ge;2,5m) &rarr; ép tải; hẻm nhỏ (&lt;1,5m) / sợ nứt nhà bên &rarr; ép neo.'),
            ])
            + '<h4>&#128221; Bảng ghi nhớ tổng hợp</h4>'
            + _table(['Chủ đề', 'Điều phải thuộc'],
                     [['<b>Đất</b>', 'Liền thổ (cứng) &rarr; móng đơn/băng. Yếu (ao hồ, san lấp) &rarr; móng cọc.'],
                      ['<b>Móng đơn</b>', '3 bộ phận, đế tách rời, rẻ nhất, nhà 1 tầng.'],
                      ['<b>Móng băng</b>', '2 bộ phận, đế chạy dài liền mạch, trung bình, nhà 2-3 tầng.'],
                      ['<b>Móng cọc</b>', 'Cọc + đài + dầm, đất yếu, đắt hơn (tiền cọc), nhà 2-5 tầng.'],
                      ['<b>Cọc bê tông</b>', 'Tiết diện 20x20 / 25x25 cm, dài 5-6m, giá MB 200k / MN 270k mỗi mét.'],
                      ['<b>Ép tải</b>', '60-120 tấn, hẻm &ge;2,5m, ~30tr, RUNG đất.'],
                      ['<b>Ép neo</b>', '40 tấn, hẻm &lt;1,5m, ~15tr, không ảnh hưởng hàng xóm.']],
                     widths=['24%', '76%'])
            + _core('1) Xem ĐẤT: liền thổ hay yếu. 2) Cứng &rarr; móng đơn (1 tầng) / băng (2-3 tầng). '
                    '3) Yếu &rarr; móng cọc (đắt hơn). 4) Ép: hẻm rộng &rarr; ép tải, hẻm nhỏ &rarr; ép neo.')
            + _fml('Luôn hỏi <b>ĐẤT gì + nhà MẤY TẦNG</b> &rarr; ra loại móng &rarr; ra chi phí '
                   '&rarr; giải thích cho khách. Đất yếu = móng cọc; hẻm nhỏ = ép neo.')
            + _quiz('mng_gold',
                    'Khách có đất mới san lấp (đất yếu), nhà trong ngõ hẻm rộng 3m, xây 3 tầng. Tư vấn đúng là gì?',
                    [('Móng cọc (đất yếu); ép TẢI vì hẻm rộng ≥2,5m; giải thích đắt hơn do tiền cọc', True),
                     ('Móng băng cho rẻ vì hẻm rộng', False),
                     ('Móng đơn vì chỉ 3 tầng', False),
                     ('Móng cọc nhưng ép NEO vì cho chắc', False)],
                    'Đất yếu → móng cọc; hẻm rộng ≥2,5m → ép tải; đắt hơn vì tiền cọc bê tông.'))

    # ==================================================================
    #  20 CÂU HỎI (đáp án gây PHÂN VÂN - trao số liệu giữa các loại)
    # ==================================================================
    def _mng_questions(self):
        T, F = True, False
        return [
            ('Đất liền thổ là loại đất nào?',
             [('Đất cứng tự nhiên, chưa qua đào bới san lấp, không có bùn nước', T),
              ('Đất ao hồ được san lấp, còn lớp bùn ẩm', F),
              ('Đất phân lô khu đô thị san từ ruộng', F),
              ('Đất ven sông nhiều nước', F)]),

            ('Đâu KHÔNG phải là đất yếu?',
             [('Đất cứng tự nhiên lâu năm chưa san lấp', T),
              ('Đất ao hồ san lấp', F),
              ('Đất phân lô khu đô thị san từ ruộng ao', F),
              ('Đất ven sông', F)]),

            ('Đất yếu (ao hồ, san lấp) thì BẮT BUỘC dùng loại móng nào?',
             [('Móng cọc', T),
              ('Móng đơn', F),
              ('Móng băng', F),
              ('Móng đơn hoặc móng băng đều được', F)]),

            ('Móng ĐƠN có bao nhiêu bộ phận?',
             [('3 bộ phận (đế móng, đoạn cột, dầm móng)', T),
              ('2 bộ phận (đế móng, dầm móng)', F),
              ('4 bộ phận', F),
              ('1 bộ phận duy nhất', F)]),

            ('Móng BĂNG có bao nhiêu bộ phận?',
             [('2 bộ phận (đế móng, dầm móng)', T),
              ('3 bộ phận (đế móng, đoạn cột, dầm móng)', F),
              ('4 bộ phận', F),
              ('1 bộ phận', F)]),

            ('Đặc điểm ĐẾ MÓNG của móng ĐƠN là gì?',
             [('Các đế móng KHÔNG liên kết với nhau (tách rời)', T),
              ('Đế móng chạy dài, liền mạch', F),
              ('Đế móng thu về thành đài móng', F),
              ('Không có đế móng', F)]),

            ('Đặc điểm ĐẾ MÓNG của móng BĂNG là gì?',
             [('Đế móng chạy dài, liền mạch', T),
              ('Các đế móng tách rời từng cục', F),
              ('Đế móng nằm trên cọc bê tông', F),
              ('Không có đế móng, chỉ có cọc', F)]),

            ('Trong 3 loại móng, loại nào chi phí RẺ NHẤT?',
             [('Móng đơn', T),
              ('Móng băng', F),
              ('Móng cọc', F),
              ('Ba loại bằng giá nhau', F)]),

            ('Chi phí của móng BĂNG được xếp ở mức nào?',
             [('Trung bình', T),
              ('Rẻ nhất', F),
              ('Đắt nhất', F),
              ('Miễn phí', F)]),

            ('Móng ĐƠN thường dùng cho nhà mấy tầng?',
             [('Nhà 1 tầng (2 tầng nếu tài chính thấp)', T),
              ('Nhà 2 - 3 tầng', F),
              ('Nhà 2 - 5 tầng', F),
              ('Nhà trên 5 tầng', F)]),

            ('Móng BĂNG thường dùng cho nhà mấy tầng?',
             [('Nhà 2 - 3 tầng', T),
              ('Nhà 1 tầng', F),
              ('Nhà 2 - 5 tầng', F),
              ('Nhà trên 10 tầng', F)]),

            ('Móng CỌC thường dùng cho nhà mấy tầng?',
             [('Nhà 2 - 5 tầng', T),
              ('Nhà 1 tầng', F),
              ('Nhà 2 - 3 tầng', F),
              ('Chỉ nhà cấp 4', F)]),

            ('Vì sao móng CỌC đắt hơn móng băng dù phần đài và dầm tương đương?',
             [('Vì phát sinh thêm tiền cọc bê tông ép xuống đất', T),
              ('Vì dùng nhiều dầm móng hơn', F),
              ('Vì đế móng chạy dài hơn', F),
              ('Vì phải xây thêm 1 tầng', F)]),

            ('Cọc bê tông đúc sẵn có kích thước nào?',
             [('20x20 cm và 25x25 cm', T),
              ('25x25 cm và 30x30 cm', F),
              ('20x20 cm và 30x30 cm', F),
              ('15x15 cm và 20x20 cm', F)]),

            ('Cọc bê tông đúc sẵn có chiều dài khoảng bao nhiêu mỗi đoạn?',
             [('5 - 6 m', T),
              ('2 m', F),
              ('10 - 12 m', F),
              ('3 - 4 m', F)]),

            ('Đơn giá cọc bê tông đúc sẵn theo vùng là bao nhiêu?',
             [('Miền Bắc ~200k/m, Miền Nam ~270k/m', T),
              ('Miền Bắc ~270k/m, Miền Nam ~200k/m', F),
              ('Cả hai miền ~500k/m', F),
              ('Miền Bắc ~200k/m, Miền Nam ~200k/m', F)]),

            ('Phương pháp ÉP TẢI ép được tải trọng bao nhiêu?',
             [('Khoảng 60 - 120 tấn', T),
              ('Khoảng 40 tấn', F),
              ('Khoảng 15 - 30 tấn', F),
              ('Khoảng 200 tấn', F)]),

            ('Phương pháp ÉP NEO phù hợp với điều kiện nào?',
             [('Ngõ hẻm nhỏ dưới 1,5 m, không ảnh hưởng nhà hàng xóm', T),
              ('Ngõ hẻm rộng từ 2,5 m trở lên, làm rung đất', F),
              ('Chỉ dùng cho đất cứng liền thổ', F),
              ('Ép được tải trọng 60 - 120 tấn', F)]),

            ('Nhược điểm của ÉP TẢI là gì?',
             [('Làm rung đất, dễ gây nứt nhà bên cạnh', T),
              ('Ép được tải trọng quá thấp', F),
              ('Không làm được ở hẻm rộng', F),
              ('Giá quá rẻ nên kém chất lượng', F)]),

            ('So sánh chi phí 1 ca ép: ép tải và ép neo?',
             [('Ép tải ~30 triệu, ép neo ~15 triệu', T),
              ('Ép tải ~15 triệu, ép neo ~30 triệu', F),
              ('Cả hai ~30 triệu', F),
              ('Cả hai ~15 triệu', F)]),
        ]
