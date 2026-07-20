# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "MẪU NHÀ" (course_a1).

Đối tượng: nhân viên sale (kể cả TRÁI NGÀNH), chưa biết gì về xây dựng. Khóa
giúp NV mới HIỂU và PHÂN BIỆT các mẫu nhà (vuông hiện đại, mái Nhật, mái Thái,
mẫu khác) và các hạng mục đặc biệt (tum, sân thượng, tầng lửng, thông tầng).

GIAO DIỆN kiểu Streamlit (giống khóa "Kỹ thuật thi công"): menu trái chọn từng
bài + hộp màu + HÌNH MÔ PHỎNG SVG tự vẽ + ẢNH THỰC TẾ có sẵn + công thức chốt +
quiz chấm đúng/sai tức thì (thuần CSS input:checked, KHÔNG JS).

Helper nối chuỗi (+) -> tránh bẫy %. MỌI class method dùng prefix RIÊNG _mnh_
để KHÔNG trùng tên với seed khác (xem reference-seed-method-name-collision).
Idempotent theo VERSION (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, models

_MN_VERSION = 'v4-svg-streamlit'
_PARAM_KEY = 'vd_elearning.maunha_seed_version'
_IMG = '/vd_elearning/static/src/img/maunha/'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-mnh{font-size:16px;line-height:1.7;color:#1f2937;'
    'width:96vw;max-width:1720px;position:relative;left:50%;transform:translateX(-50%);'
    'margin-top:-1.3cm;}'
    '.vd-mnh .vd-course{background:linear-gradient(180deg,#eef2ff 0%,#f5f8ff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-mnh h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-mnh h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-mnh p{margin:0 0 10px;}'
    '.vd-mnh ul,.vd-mnh ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-mnh li{margin:5px 0;}'
    '.vd-mnh b{color:#111827;}'
    '.vd-mnh table{border-collapse:collapse;width:100%;margin:8px 0 6px;font-size:15px;}'
    '.vd-mnh th,.vd-mnh td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-mnh th{background:#eef2ff;font-weight:800;color:#3730a3;}'
    '.vd-mnh .tc{text-align:center;}'
    '.vd-mnh .cheap{color:#16a34a;font-weight:800;}'
    '.vd-mnh .mid{color:#d97706;font-weight:800;}'
    '.vd-mnh .exp{color:#dc2626;font-weight:800;}'
    '.vd-mnh .navr,.vd-mnh .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-mnh .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-mnh .vc-side{flex:0 0 300px;}'
    '.vd-mnh .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-mnh .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-mnh .vc-navbtn:hover{background:#eef2ff;border-color:#c7d2fe;color:#4338ca;}'
    '.vd-mnh .vc-nbadge{flex:0 0 auto;display:inline-block;background:#e0e7ff;color:#4338ca;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-mnh .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;white-space:nowrap;}'
    '.vd-mnh .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-mnh .vc-panel{display:none;}'
    '.vd-mnh .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#4338ca;background:#e0e7ff;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-mnh .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:9px 0;}'
    '.vd-mnh .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-mnh .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-mnh .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-mnh .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    '.vd-mnh .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:10px 0;}'
    '.vd-mnh .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-mnh .fml .fml-b{color:#4c1d95;font-weight:600;}'
    '.vd-mnh .core{border:2px dashed #b8860b;background:#fff8e1;border-radius:14px;'
    'padding:15px 18px;margin:14px 0;text-align:center;}'
    '.vd-mnh .core .ch{font-weight:900;color:#92600a;font-size:12.5px;letter-spacing:.6px;'
    'text-transform:uppercase;margin-bottom:7px;}'
    '.vd-mnh .core .cb{font-size:16px;font-weight:800;color:#3a2c05;}'
    '.vd-mnh .wrong{background:#fff1f2;border:2px solid #fda4af;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#9f1239;}'
    '.vd-mnh .wrong .wh{font-weight:800;color:#be123c;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-mnh .fig{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;'
    'padding:14px 16px 10px;margin:12px 0;text-align:center;}'
    '.vd-mnh .fig svg{max-width:100%;height:auto;}'
    '.vd-mnh .fig .cap{font-size:13px;color:#64748b;margin-top:6px;font-weight:600;}'
    '.vd-mnh .fig .figh{font-size:12.5px;font-weight:800;letter-spacing:.6px;'
    'color:#0f172a;text-transform:uppercase;margin-bottom:8px;text-align:left;}'
    # gallery anh thuc te
    '.vd-mnh .phwrap{margin:12px 0;}'
    '.vd-mnh .phhead{font-size:12.5px;font-weight:800;letter-spacing:.6px;color:#0f172a;'
    'text-transform:uppercase;margin-bottom:8px;}'
    '.vd-mnh .phrow{display:flex;flex-wrap:wrap;gap:12px;}'
    '.vd-mnh .phrow figure{margin:0;flex:1 1 230px;min-width:190px;max-width:360px;}'
    '.vd-mnh .phrow img{width:100%;height:210px;object-fit:cover;border-radius:12px;'
    'box-shadow:0 6px 18px rgba(2,6,23,.18);}'
    '.vd-mnh .phrow figcaption{font-size:12px;color:#64748b;text-align:center;'
    'margin-top:5px;font-weight:600;}'
    '.vd-mnh .vc-order{margin:12px 0;border:1px solid #c7d2fe;border-radius:12px;overflow:hidden;}'
    '.vd-mnh .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #e0e7ff;background:#f7f8ff;}'
    '.vd-mnh .vc-ostep:last-child{border-bottom:none;}'
    '.vd-mnh .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#4338ca;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-mnh .vc-ot{font-weight:800;color:#3730a3;}'
    '.vd-mnh .vc-od{color:#4338ca;font-size:14.5px;}'
    '.vd-mnh .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
    '.vd-mnh .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-mnh .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-mnh .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-mnh .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-mnh .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-mnh .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-mnh .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-mnh .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-mnh .vc-layout{flex-direction:column;}'
    '.vd-mnh .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-mnh .vc-sidehead{width:100%;}'
    '.vd-mnh .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
    '</style>'
)


# ---------------------------------------------------------------------------
#  HELPER
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
#  SVG MÔ PHỎNG
# ---------------------------------------------------------------------------
def _svg_ngoi(cx, y0, w, rows):
    """Vai duong ke ngoi tren mai (trang tri)."""
    out = '<g stroke="#7c2d12" stroke-width="1.5" opacity="0.6">'
    for i in range(rows):
        yy = y0 + 8 + i * 9
        out += '<line x1="' + str(cx - w) + '" y1="' + str(yy) + '" x2="' + str(cx + w) + '" y2="' + str(yy) + '"/>'
    return out + '</g>'


def _svg_3mau():
    svg = ('<svg viewBox="0 0 720 260" width="720" role="img" '
           'aria-label="3 mau nha chu dao">')
    svg += '<line x1="20" y1="214" x2="700" y2="214" stroke="#a1824a" stroke-width="2"/>'
    # 1) Vuong hien dai
    svg += ('<rect x="65" y="118" width="130" height="96" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
            '<rect x="58" y="102" width="144" height="16" fill="#94a3b8"/>'
            '<rect x="85" y="140" width="34" height="34" fill="#c7d2fe"/>'
            '<rect x="140" y="140" width="34" height="34" fill="#c7d2fe"/>'
            '<text x="130" y="236" font-size="13" fill="#1d4ed8" font-weight="900" text-anchor="middle">VUÔNG HIỆN ĐẠI</text>'
            '<text x="130" y="252" font-size="11" fill="#64748b" text-anchor="middle">mái bằng &middot; rẻ nhất</text>')
    # 2) Mai Nhat (mai thap, trai rong)
    svg += ('<rect x="300" y="130" width="130" height="84" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
            '<polygon points="262,130 365,88 468,130" fill="#c2410e" stroke="#7c2d12" stroke-width="2"/>'
            + _svg_ngoi(365, 92, 84, 3) +
            '<text x="365" y="236" font-size="13" fill="#1d4ed8" font-weight="900" text-anchor="middle">MÁI NHẬT</text>'
            '<text x="365" y="252" font-size="11" fill="#64748b" text-anchor="middle">mái thấp &middot; lộ ngói &middot; KHÔNG góc A</text>')
    # 3) Mai Thai (mai cao, goc chu A)
    svg += ('<rect x="545" y="130" width="110" height="84" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
            '<polygon points="527,130 600,52 673,130" fill="#b91c1c" stroke="#7c1010" stroke-width="2"/>'
            '<text x="600" y="104" font-size="20" fill="#fff" font-weight="900" text-anchor="middle">A</text>'
            '<text x="600" y="236" font-size="13" fill="#1d4ed8" font-weight="900" text-anchor="middle">MÁI THÁI</text>'
            '<text x="600" y="252" font-size="11" fill="#64748b" text-anchor="middle">mái cao &middot; CÓ góc chữ A &middot; đắt hơn</text>')
    return svg + '</svg>'


def _svg_vuong():
    return (
        '<svg viewBox="0 0 440 260" width="440" role="img" aria-label="Nha vuong hien dai mai bang">'
        '<line x1="20" y1="220" x2="420" y2="220" stroke="#a1824a" stroke-width="2"/>'
        '<rect x="120" y="70" width="200" height="150" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        '<rect x="110" y="54" width="220" height="18" fill="#94a3b8"/>'
        '<text x="220" y="47" font-size="12" fill="#475569" font-weight="700" text-anchor="middle">Mái bằng (phẳng)</text>'
        # cua kinh lon hien dai
        '<rect x="145" y="95" width="70" height="50" fill="#bfdbfe" stroke="#93c5fd"/>'
        '<rect x="235" y="95" width="55" height="50" fill="#bfdbfe" stroke="#93c5fd"/>'
        '<rect x="185" y="160" width="70" height="60" fill="#93c5fd" stroke="#60a5fa"/>'
        '<text x="220" y="245" font-size="12" fill="#16a34a" font-weight="800" text-anchor="middle">Khối vuông vức, đường nét đơn giản &mdash; hợp NHÀ PHỐ</text>'
        '</svg>')


def _svg_mai_nhat():
    return (
        '<svg viewBox="0 0 480 280" width="480" role="img" aria-label="Nha mai Nhat">'
        '<line x1="20" y1="238" x2="460" y2="238" stroke="#a1824a" stroke-width="2"/>'
        '<rect x="150" y="150" width="180" height="88" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        # mai thap trai rong (do doc thoai)
        '<polygon points="110,150 240,96 370,150" fill="#c2410e" stroke="#7c2d12" stroke-width="2"/>'
        + _svg_ngoi(240, 100, 130, 4) +
        '<rect x="190" y="175" width="45" height="63" fill="#93c5fd"/>'
        '<rect x="250" y="185" width="55" height="35" fill="#bfdbfe"/>'
        # annotate
        '<text x="240" y="86" font-size="12" fill="#166534" font-weight="800" text-anchor="middle">Mái LÙN, THẤP, trải rộng</text>'
        '<text x="392" y="120" font-size="11.5" fill="#7c2d12" font-weight="700">lộ rõ hàng ngói</text>'
        '<text x="240" y="266" font-size="12" fill="#1d4ed8" font-weight="800" text-anchor="middle">KHÔNG có góc chữ A &mdash; hợp đất rộng / nhà vườn</text>'
        '</svg>')


def _svg_mai_thai():
    return (
        '<svg viewBox="0 0 480 290" width="480" role="img" aria-label="Nha mai Thai">'
        '<line x1="20" y1="248" x2="460" y2="248" stroke="#a1824a" stroke-width="2"/>'
        '<rect x="160" y="170" width="160" height="78" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        # mai cao doc nhon = goc chu A
        '<polygon points="130,170 240,64 350,170" fill="#b91c1c" stroke="#7c1010" stroke-width="2"/>'
        # marker goc chu A
        '<text x="240" y="132" font-size="30" fill="#fff" font-weight="900" text-anchor="middle">A</text>'
        '<path d="M205 160 L240 96 L275 160" fill="none" stroke="#fca5a5" stroke-width="2" stroke-dasharray="3 3"/>'
        '<rect x="200" y="192" width="48" height="56" fill="#93c5fd"/>'
        '<rect x="262" y="200" width="45" height="30" fill="#bfdbfe"/>'
        '<text x="240" y="54" font-size="12" fill="#b91c1c" font-weight="800" text-anchor="middle">Mái CAO, dốc nhọn</text>'
        '<text x="360" y="150" font-size="11.5" fill="#7c1010" font-weight="700">có GÓC CHỮ A</text>'
        '<text x="240" y="276" font-size="12" fill="#1d4ed8" font-weight="800" text-anchor="middle">Đứng trước KHÔNG thấy ngói &mdash; đắt hơn mái Nhật</text>'
        '</svg>')


def _svg_compare_roof():
    return (
        '<svg viewBox="0 0 560 260" width="560" role="img" aria-label="So sanh mai Nhat va mai Thai">'
        '<line x1="20" y1="220" x2="540" y2="220" stroke="#a1824a" stroke-width="2"/>'
        # NHAT (trai) - mai thap
        '<rect x="70" y="150" width="150" height="70" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        '<polygon points="42,150 145,112 248,150" fill="#c2410e" stroke="#7c2d12" stroke-width="2"/>'
        '<text x="145" y="104" font-size="13" fill="#166534" font-weight="900" text-anchor="middle">MÁI NHẬT</text>'
        '<text x="145" y="242" font-size="12" fill="#16a34a" font-weight="800" text-anchor="middle">&#9989; thấp &middot; KHÔNG góc A &middot; rẻ hơn</text>'
        # THAI (phai) - mai cao
        '<rect x="330" y="150" width="150" height="70" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
        '<polygon points="302,150 405,60 508,150" fill="#b91c1c" stroke="#7c1010" stroke-width="2"/>'
        '<text x="405" y="116" font-size="22" fill="#fff" font-weight="900" text-anchor="middle">A</text>'
        '<text x="405" y="50" font-size="13" fill="#b91c1c" font-weight="900" text-anchor="middle">MÁI THÁI</text>'
        '<text x="405" y="242" font-size="12" fill="#dc2626" font-weight="800" text-anchor="middle">&#10060; cao &middot; CÓ góc A &middot; đắt hơn</text>'
        # duong ke so sanh do cao
        '<line x1="260" y1="112" x2="290" y2="112" stroke="#64748b" stroke-dasharray="3 3"/>'
        '<line x1="260" y1="60" x2="302" y2="60" stroke="#64748b" stroke-dasharray="3 3"/>'
        '<line x1="275" y1="60" x2="275" y2="112" stroke="#4338ca" stroke-width="2"/>'
        '<polygon points="271,66 279,66 275,58" fill="#4338ca"/>'
        '<polygon points="271,106 279,106 275,114" fill="#4338ca"/>'
        '<text x="278" y="92" font-size="10.5" fill="#4338ca" font-weight="700">chênh</text>'
        '</svg>')


def _svg_caocap():
    svg = ('<svg viewBox="0 0 600 200" width="600" role="img" aria-label="Mau nha cao cap">')
    svg += '<line x1="20" y1="164" x2="580" y2="164" stroke="#a1824a" stroke-width="2"/>'
    # Indochine - vom cua + cot
    svg += ('<rect x="50" y="70" width="120" height="94" fill="#fef3c7" stroke="#b45309" stroke-width="2"/>'
            '<path d="M70 100 a20 20 0 0 1 40 0" fill="none" stroke="#b45309" stroke-width="3"/>'
            '<path d="M120 100 a20 20 0 0 1 40 0" fill="none" stroke="#b45309" stroke-width="3"/>'
            '<line x1="90" y1="100" x2="90" y2="164" stroke="#b45309" stroke-width="3"/>'
            '<line x1="140" y1="100" x2="140" y2="164" stroke="#b45309" stroke-width="3"/>'
            '<text x="110" y="186" font-size="12" fill="#92400e" font-weight="800" text-anchor="middle">INDOCHINE</text>')
    # Tan co dien - doi xung, phao chi
    svg += ('<rect x="240" y="66" width="120" height="98" fill="#f8fafc" stroke="#94a3b8" stroke-width="2"/>'
            '<rect x="234" y="56" width="132" height="12" fill="#cbd5e1"/>'
            '<line x1="300" y1="68" x2="300" y2="164" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4 3"/>'
            '<rect x="258" y="86" width="30" height="46" fill="#e2e8f0" stroke="#94a3b8"/>'
            '<rect x="312" y="86" width="30" height="46" fill="#e2e8f0" stroke="#94a3b8"/>'
            '<text x="300" y="186" font-size="12" fill="#475569" font-weight="800" text-anchor="middle">TÂN CỔ ĐIỂN</text>')
    # Mai Phap - mansard nhieu lop
    svg += ('<rect x="430" y="96" width="120" height="68" fill="#eef2f7" stroke="#94a3b8" stroke-width="2"/>'
            '<polygon points="430,96 452,66 528,66 550,96" fill="#475569" stroke="#334155" stroke-width="2"/>'
            '<polygon points="452,66 478,44 502,44 528,66" fill="#64748b" stroke="#334155" stroke-width="2"/>'
            '<text x="490" y="186" font-size="12" fill="#334155" font-weight="800" text-anchor="middle">MÁI PHÁP</text>')
    return svg + '</svg>'


def _svg_hangmuc():
    svg = ('<svg viewBox="0 0 600 380" width="600" role="img" aria-label="Tum san thuong tang lung thong tang">')
    # dat
    svg += ('<rect x="0" y="340" width="600" height="40" fill="#d9c9a3"/>'
            '<line x1="0" y1="340" x2="600" y2="340" stroke="#a1824a" stroke-width="2"/>')
    # tuong ngoai
    svg += '<rect x="80" y="120" width="400" height="220" fill="#f8fafc" stroke="#475569" stroke-width="3"/>'
    # san mai (deck) tren cung
    svg += '<rect x="74" y="112" width="412" height="10" fill="#94a3b8"/>'
    # san giua 2 tang - chi ben PHAI (ben trai la thong tang)
    svg += '<rect x="250" y="228" width="230" height="9" fill="#94a3b8"/>'
    # TUM tren mai (che cau thang)
    svg += ('<rect x="250" y="66" width="120" height="46" fill="#e2e8f0" stroke="#475569" stroke-width="2"/>'
            '<polygon points="244,66 310,44 376,66" fill="#c2410e" stroke="#7c2d12" stroke-width="2"/>'
            '<text x="310" y="94" font-size="12" fill="#334155" font-weight="800" text-anchor="middle">TUM</text>')
    # cau thang duoi tum
    svg += '<g stroke="#94a3b8" stroke-width="3" fill="none">'
    for i in range(5):
        yy = 132 + i * 18
        svg += '<path d="M300 ' + str(yy) + ' h26 v18"/>'
    svg += '</g>'
    # SAN THUONG (trai, tren deck) - lan can
    svg += '<g stroke="#64748b" stroke-width="2">'
    for x in range(96, 236, 22):
        svg += '<line x1="' + str(x) + '" y1="96" x2="' + str(x) + '" y2="112"/>'
    svg += '<line x1="90" y1="96" x2="236" y2="96"/></g>'
    svg += '<text x="163" y="90" font-size="11.5" fill="#0f172a" font-weight="800" text-anchor="middle">SÂN THƯỢNG</text>'
    # TANG LUNG (mot phan san ben phai)
    svg += ('<rect x="250" y="292" width="130" height="8" fill="#a3a3a3"/>'
            '<text x="315" y="286" font-size="11" fill="#334155" font-weight="800" text-anchor="middle">TẦNG LỬNG (~3m)</text>')
    # THONG TANG (trai - khoang thong 2 tang tai phong khach)
    svg += ('<line x1="165" y1="132" x2="165" y2="334" stroke="#4338ca" stroke-width="2"/>'
            '<polygon points="161,138 169,138 165,128" fill="#4338ca"/>'
            '<polygon points="161,328 169,328 165,338" fill="#4338ca"/>'
            '<text x="165" y="210" font-size="12" fill="#4338ca" font-weight="900" text-anchor="middle" transform="rotate(-90 165 210)">THÔNG TẦNG ~6m</text>'
            '<text x="120" y="360" font-size="11" fill="#4338ca" font-weight="700">phòng khách thông 2 tầng (30-50% sàn)</text>')
    # nhan tang
    svg += ('<text x="470" y="300" font-size="11" fill="#475569" font-weight="700" text-anchor="end">Tầng trệt</text>'
            '<text x="470" y="200" font-size="11" fill="#475569" font-weight="700" text-anchor="end">Tầng 2</text>')
    return svg + '</svg>'


def _svg_decide():
    svg = ('<svg viewBox="0 0 640 260" width="640" role="img" aria-label="So do tu van chon mau nha">')
    # hop hoi
    svg += ('<rect x="230" y="20" width="180" height="46" rx="10" fill="#4338ca"/>'
            '<text x="320" y="40" font-size="12.5" fill="#fff" font-weight="800" text-anchor="middle">Hỏi: ĐẤT gì?</text>'
            '<text x="320" y="57" font-size="12.5" fill="#fff" font-weight="800" text-anchor="middle">NGÂN SÁCH bao nhiêu?</text>')
    # 3 nhanh
    branches = [(90, '#16a34a', 'Đất hẹp / nhà phố', 'tiết kiệm', 'VUÔNG HIỆN ĐẠI'),
                (320, '#d97706', 'Đất rộng, ngân sách vừa', 'thích ngói', 'MÁI NHẬT'),
                (550, '#dc2626', 'Đất rộng, ngân sách cao', 'thích bề thế', 'MÁI THÁI')]
    for x, c, cond, cond2, out in branches:
        svg += ('<line x1="320" y1="66" x2="' + str(x) + '" y2="120" stroke="#94a3b8" stroke-width="2"/>')
        svg += ('<rect x="' + str(x - 85) + '" y="120" width="170" height="46" rx="8" fill="#eef2ff" stroke="' + c + '" stroke-width="2"/>'
                '<text x="' + str(x) + '" y="139" font-size="11.5" fill="#334155" font-weight="700" text-anchor="middle">' + cond + '</text>'
                '<text x="' + str(x) + '" y="156" font-size="11" fill="#64748b" text-anchor="middle">' + cond2 + '</text>')
        svg += ('<line x1="' + str(x) + '" y1="166" x2="' + str(x) + '" y2="196" stroke="#94a3b8" stroke-width="2"/>'
                '<polygon points="' + str(x - 5) + ',192 ' + str(x + 5) + ',192 ' + str(x) + ',202" fill="#94a3b8"/>')
        svg += ('<rect x="' + str(x - 85) + '" y="204" width="170" height="40" rx="8" fill="' + c + '"/>'
                '<text x="' + str(x) + '" y="229" font-size="13" fill="#fff" font-weight="900" text-anchor="middle">' + out + '</text>')
    return svg + '</svg>'


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

        ch.write({'vd_pass_percent': 80, 'vd_max_attempts': 0, 'vd_exam_minutes': 0})

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-mnh" style="%s">%s</div>'
                                 % (_WRAP, self._mnh_app())),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._mnh_questions():
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
    def _mnh_app(self):
        lessons = self._mnh_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'mnhL' + str(i)
            pid = 'mnhP' + str(i)
            radios += ('<input class="navr" type="radio" name="mnhnav" id="' + rid + '"'
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
            'PHÂN BIỆT CÁC MẪU NHÀ &mdash; nhận ra ngay khách muốn kiểu gì</div>'
            '<div style="color:#eef2ff;font-size:14.5px;margin-top:9px;">'
            '&#127968; Chỉ cần đọc xong là phân biệt được các kiểu nhà khách hay nhắc tới. '
            '&#128073; Bấm từng mục ở MENU BÊN TRÁI &mdash; mỗi bài có hình mô phỏng, ảnh thực tế, '
            'công thức và trắc nghiệm chấm ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _mnh_tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    def _mnh_lessons(self):
        return [
            ('&#129504;', 'MỞ ĐẦU', 'Mẫu nhà là gì? 3 mẫu chủ đạo', self._mnh_l_intro()),
            ('&#127970;', 'MẪU 1', 'Nhà vuông hiện đại', self._mnh_l_vuong()),
            ('&#127962;', 'MẪU 2', 'Nhà mái Nhật', self._mnh_l_nhat()),
            ('&#127964;', 'MẪU 3', 'Nhà mái Thái', self._mnh_l_thai()),
            ('&#128202;', 'SO SÁNH', 'Mái Nhật vs Mái Thái', self._mnh_l_compare()),
            ('&#127983;', 'CAO CẤP', 'Các mẫu nhà khác', self._mnh_l_khac()),
            ('&#128736;&#65039;', 'HẠNG MỤC', 'Tum, sân thượng, lửng, thông tầng', self._mnh_l_hangmuc()),
            ('&#127942;', 'TỔNG KẾT', 'Nhận biết nhanh + kịch bản tư vấn', self._mnh_l_gold()),
        ]

    # ------------------------------------------------------------------
    def _mnh_l_intro(self):
        return (
            self._mnh_tag('KIẾN THỨC NỀN TẢNG')
            + '<h3>&#8220;Mẫu nhà&#8221; là gì và vì sao phải nhận ra ngay?</h3>'
            + '<p><b>Mẫu nhà</b> là <b>kiểu dáng và phong cách kiến trúc tổng thể</b> của căn '
            'nhà &mdash; nhìn bên ngoài thấy nhà <b>hình khối ra sao</b>, <b>kiểu mái thế '
            'nào</b>, <b>hiện đại hay cổ điển</b>. Mỗi mẫu hợp với một loại đất, một mức chi '
            'phí và một sở thích khác nhau.</p>'
            + _fig('3 mẫu nhà chủ đạo &mdash; nhìn là biết', _svg_3mau(),
                   'Vuông hiện đại (mái bằng) &middot; Mái Nhật (mái thấp, lộ ngói) &middot; Mái Thái (mái cao, góc chữ A).')
            + _box('info', 'Khi khách nói <i>&#8220;anh thích nhà <b>mái Thái</b>&#8221;</i>, '
                   '<i>&#8220;cho xem <b>nhà vuông hiện đại</b>&#8221;</i> hay <i>&#8220;nhà '
                   '<b>mái Nhật</b> đẹp không em?&#8221;</i> &mdash; đó chính là khách đang nói '
                   'về <b>MẪU NHÀ</b>. Bạn phải <b>nhận ra ngay</b> khách muốn kiểu gì để tư vấn đúng.')
            + '<h4>&#128209; Toàn khóa gồm gì?</h4>'
            + _table(['Nhóm', 'Gồm'],
                     [['<b class="cheap">3 mẫu CHỦ ĐẠO</b> (hay gặp nhất)',
                       'Nhà vuông hiện đại &middot; Nhà mái Nhật &middot; Nhà mái Thái'],
                      ['<b style="color:#9333ea;">Mẫu khác</b> (cao cấp, tham khảo)',
                       'Indochine &middot; Tân cổ điển &middot; Mái Pháp'],
                      ['<b style="color:#b45309;">Hạng mục đặc biệt</b>',
                       'Tum &middot; Sân thượng &middot; Tầng lửng &middot; Thông tầng']],
                     widths=['34%', '66%'])
            + _core('Mẫu nhà = <b>kiểu dáng + kiểu mái + phong cách</b>. Nhớ trước <b>3 mẫu chủ '
                    'đạo</b>: Vuông hiện đại &middot; Mái Nhật &middot; Mái Thái.')
            + _fml('Muốn tư vấn đúng: hỏi <b>diện tích ĐẤT</b> + <b>NGÂN SÁCH</b> + <b>sở '
                   'thích mái</b> &rarr; gợi ý đúng 1 trong 3 mẫu chủ đạo.')
            + _quiz('mnh_intro',
                    'Khi khách nói "cho anh xem nhà mái Thái", khách đang nói về điều gì?',
                    [('Về MẪU NHÀ (kiểu dáng + kiểu mái + phong cách) &mdash; cần nhận ra ngay để tư vấn đúng', True),
                     ('Về số tiền xây nhà', False),
                     ('Về diện tích miếng đất', False),
                     ('Về tên của chủ nhà', False)],
                    'Mái Thái/vuông/mái Nhật đều là cách khách gọi MẪU NHÀ &mdash; nhận ra ngay để tư vấn đúng.'))

    # ------------------------------------------------------------------
    def _mnh_l_vuong(self):
        return (
            self._mnh_tag('MẪU 1 &mdash; NHÀ VUÔNG HIỆN ĐẠI')
            + '<h3>Nhà vuông hiện đại: mái bằng, khối vuông &mdash; rẻ &amp; phổ biến nhất</h3>'
            + '<p>Là kiểu nhà <b>hình khối vuông vức</b>, <b>mái bằng (mái phẳng)</b>, đường '
            'nét đơn giản, hiện đại. Đây là mẫu <b>thông dụng nhất</b> hiện nay.</p>'
            + _fig('Nhà vuông hiện đại &mdash; mái bằng', _svg_vuong(),
                   'Khối vuông vức, mái phẳng, cửa kính lớn, đường nét tối giản.')
            + _photos('Hình thực tế', [('image15.jpg', ''), ('image32.jpg', ''), ('image22.jpg', ''),
                                       ('image31.jpg', ''), ('image34.jpg', '')])
            + _table(['Đặc điểm', 'Nội dung'],
                     [['<b>Kiểu mái</b>', 'Mái bằng (phẳng), khối vuông hiện đại'],
                      ['<b>Phù hợp</b>', '<b>Nhà phố</b> (mặt tiền hẹp, đất hình ống)'],
                      ['<b>Chi phí</b>', '<span class="cheap">RẺ NHẤT</span> trong các mẫu (ít vật tư mái)'],
                      ['<b>Phổ biến</b>', '<span class="cheap">Dùng NHIỀU NHẤT</span> trên thị trường']],
                     widths=['26%', '74%'])
            + _box('info', '<b>Vì sao rẻ nhất?</b> Mái bằng không tốn hệ khung kèo + ngói như '
                   'mái Nhật/Thái &mdash; ít vật tư, thi công nhanh hơn.')
            + _wrong(['Gọi nhà vuông hiện đại là &#8220;nhà cấp 4&#8221; hay &#8220;nhà không '
                      'có mái&#8221; &mdash; nó có mái BẰNG (phẳng), là mẫu hiện đại phổ biến nhất.'])
            + _core('Nhà vuông hiện đại = <b>mái bằng &middot; hợp nhà phố &middot; RẺ NHẤT &middot; PHỔ BIẾN NHẤT</b>.')
            + _fml('VUÔNG HIỆN ĐẠI &rarr; <b>mái bằng</b> + <b>nhà phố</b> + <b>rẻ nhất</b> + <b>phổ biến nhất</b>.')
            + _quiz('mnh_vuong',
                    'Khách có đất nhà phố mặt tiền hẹp, muốn tiết kiệm chi phí. Gợi ý mẫu nào?',
                    [('Nhà vuông hiện đại &mdash; mái bằng, hợp nhà phố, rẻ nhất', True),
                     ('Nhà mái Thái cho sang', False),
                     ('Nhà mái Pháp cao cấp', False),
                     ('Nhà Indochine', False)],
                    'Đất hẹp nhà phố + tiết kiệm → nhà vuông hiện đại (mái bằng, rẻ nhất, phổ biến nhất).'))

    # ------------------------------------------------------------------
    def _mnh_l_nhat(self):
        return (
            self._mnh_tag('MẪU 2 &mdash; NHÀ MÁI NHẬT')
            + '<h3>Nhà mái Nhật: mái ngói LÙN, THẤP, trải rộng &mdash; KHÔNG góc chữ A</h3>'
            + '<p>Là kiểu nhà có <b>mái ngói</b> phong cách Nhật: <b>hệ mái lùn, thấp</b>, trải '
            'rộng và êm mắt.</p>'
            + _fig('Nhà mái Nhật &mdash; mái thấp, lộ ngói', _svg_mai_nhat(),
                   'Mái lùn thấp, dốc thoải trải rộng, đứng trước nhìn rõ hàng ngói; không có góc chữ A.')
            + _photos('Hình thực tế', [('image24.jpg', ''), ('image23.jpg', ''),
                                       ('image33.png', ''), ('image20.png', '')])
            + _table(['Đặc điểm', 'Nội dung'],
                     [['<b>Kiểu mái</b>', 'Hệ mái <b>lùn, thấp</b>; <b>KHÔNG có góc chữ A</b>; <b>dễ khoe được phần ngói</b>'],
                      ['<b>Phù hợp</b>', '<b>Đất rộng &mdash; nhà vườn</b>'],
                      ['<b>Chi phí</b>', '<span class="mid">Cao hơn nhà vuông</span> (nhưng <b>rẻ hơn mái Thái</b>)']],
                     widths=['26%', '74%'])
            + _box('info', '<b>&#8220;Góc chữ A&#8221; là gì?</b> Là phần mái dốc nhọn nhô cao '
                   'lên giống chữ A khi nhìn từ phía trước. <b>Mái Nhật KHÔNG có góc chữ A</b> '
                   'nên trông thấp và trải rộng.')
            + _wrong(['Nhầm mái Nhật với mái Thái vì đều là mái ngói &mdash; khác nhau ở CHỖ: '
                      'mái Nhật <b>thấp, KHÔNG góc A, lộ ngói</b>.'])
            + _core('Mái Nhật = <b>mái lùn thấp &middot; KHÔNG góc chữ A &middot; khoe ngói &middot; hợp đất rộng / nhà vườn</b>.')
            + _fml('MÁI NHẬT &rarr; <b>thấp</b> + <b>KHÔNG góc A</b> + <b>lộ ngói</b> + <b>rẻ hơn Thái</b>.')
            + _quiz('mnh_nhat',
                    'Đặc điểm nào ĐÚNG với mái Nhật?',
                    [('Mái lùn thấp, KHÔNG có góc chữ A, đứng trước nhìn rõ hàng ngói', True),
                     ('Mái cao dốc nhọn, có góc chữ A', False),
                     ('Mái bằng phẳng hoàn toàn', False),
                     ('Mái dốc nhiều lớp kiểu Pháp', False)],
                    'Mái Nhật = thấp, không góc chữ A, lộ rõ ngói.'))

    # ------------------------------------------------------------------
    def _mnh_l_thai(self):
        return (
            self._mnh_tag('MẪU 3 &mdash; NHÀ MÁI THÁI')
            + '<h3>Nhà mái Thái: mái ngói CAO, dốc nhọn &mdash; CÓ góc chữ A</h3>'
            + '<p>Là kiểu nhà mái ngói phong cách Thái: <b>hệ mái cao</b>, dốc nhọn, sang trọng.</p>'
            + _fig('Nhà mái Thái &mdash; mái cao, góc chữ A', _svg_mai_thai(),
                   'Mái cao dốc nhọn tạo góc chữ A; đứng phía trước không nhìn rõ phần ngói.')
            + _photos('Hình thực tế', [('image47.jpg', ''), ('image46.jpg', '')])
            + _table(['Đặc điểm', 'Nội dung'],
                     [['<b>Kiểu mái</b>', 'Hệ mái <b>cao</b>; <b>CÓ xây góc chữ A</b>; đứng phía trước <b>không nhìn rõ phần ngói</b>'],
                      ['<b>Phù hợp</b>', '<b>Đất rộng &mdash; nhà vườn</b>'],
                      ['<b>Chi phí</b>', '<span class="exp">ĐẮT HƠN mái Nhật</span> (mái cao, nhiều vật tư hơn)']],
                     widths=['26%', '74%'])
            + _box('info', '<b>Vì sao đắt hơn mái Nhật?</b> Mái cao và dốc nhọn nên tốn nhiều '
                   'khung kèo, ngói và nhân công hơn.')
            + _wrong(['Nói mái Thái &#8220;rẻ hơn hoặc bằng mái Nhật&#8221; &mdash; sai, mái '
                      'Thái luôn <b>đắt hơn</b> vì mái cao hơn.'])
            + _core('Mái Thái = <b>mái cao &middot; CÓ góc chữ A &middot; đứng trước không thấy ngói &middot; ĐẮT HƠN mái Nhật</b>.')
            + _fml('MÁI THÁI &rarr; <b>cao</b> + <b>CÓ góc A</b> + <b>không thấy ngói</b> + <b>đắt hơn Nhật</b>.')
            + _quiz('mnh_thai',
                    'Dấu hiệu NHẬN RA mái Thái khi nhìn từ phía trước là gì?',
                    [('Mái cao dốc nhọn tạo GÓC CHỮ A, không nhìn rõ phần ngói', True),
                     ('Mái thấp trải rộng, lộ rõ ngói', False),
                     ('Mái bằng phẳng', False),
                     ('Không có mái', False)],
                    'Mái Thái = mái cao, CÓ góc chữ A; đứng trước không thấy ngói.'))

    # ------------------------------------------------------------------
    def _mnh_l_compare(self):
        return (
            self._mnh_tag('SO SÁNH &mdash; MÁI NHẬT vs MÁI THÁI')
            + '<h3>Hai mẫu hay bị nhầm &mdash; phân biệt bằng GÓC CHỮ A</h3>'
            + _fig('Mái Nhật (thấp) vs Mái Thái (cao, góc A)', _svg_compare_roof(),
                   'Nhìn đỉnh mái: cao nhọn hình chữ A → mái Thái; thấp lùn lộ ngói → mái Nhật.')
            + _photos('Hình đối chiếu', [('image29.jpg', 'Đối chiếu hình dáng mái'),
                                         ('image25.png', 'Phân biệt mái Nhật và mái Thái')])
            + _table(['Tiêu chí', 'MÁI NHẬT', 'MÁI THÁI'],
                     [['<b>Độ cao mái</b>', 'Mái <b>lùn, thấp</b>', 'Mái <b>cao</b>'],
                      ['<b>Góc chữ A</b>', '<span class="cheap">KHÔNG có</span>', '<span class="exp">CÓ</span>'],
                      ['<b>Nhìn từ trước</b>', 'Dễ <b>khoe phần ngói</b>', '<b>Không nhìn rõ</b> ngói'],
                      ['<b>Chi phí</b>', '<span class="cheap">Rẻ hơn</span>', '<span class="exp">Đắt hơn</span>']],
                     widths=['26%', '37%', '37%'])
            + _box('ok', '<b>Mẹo phân biệt nhanh:</b> nhìn vào đỉnh mái phía trước &mdash; thấy '
                   '<b>góc nhọn cao hình chữ A</b> thì là <b>MÁI THÁI</b>; thấy mái <b>thấp, '
                   'lùn, lộ rõ hàng ngói</b> thì là <b>MÁI NHẬT</b>.')
            + _wrong(['Chỉ nhìn &#8220;có ngói&#8221; rồi đoán bừa &mdash; cả hai đều ngói. '
                      'Phải nhìn <b>GÓC CHỮ A</b> và <b>độ cao mái</b>.'])
            + _core('Khác nhau cốt lõi: <b>góc chữ A</b> (Thái CÓ, Nhật KHÔNG) và <b>chi phí</b> (Thái đắt hơn).')
            + _fml('NHẬT = thấp, KHÔNG góc A, rẻ hơn. THÁI = cao, CÓ góc A, đắt hơn. '
                   'Nhìn đỉnh mái là ra.')
            + _quiz('mnh_cmp',
                    'Điểm khác biệt CỐT LÕI giúp phân biệt mái Nhật và mái Thái là gì?',
                    [('Góc chữ A: mái Thái CÓ, mái Nhật KHÔNG (và mái Thái cao hơn, đắt hơn)', True),
                     ('Màu ngói khác nhau', False),
                     ('Mái Nhật có ngói, mái Thái không có ngói', False),
                     ('Hai mái hoàn toàn giống nhau', False)],
                    'Cốt lõi: góc chữ A (Thái có, Nhật không); mái Thái cao và đắt hơn.'))

    # ------------------------------------------------------------------
    def _mnh_l_khac(self):
        return (
            self._mnh_tag('CAO CẤP &mdash; CÁC MẪU NHÀ KHÁC')
            + '<h3>Mẫu cao cấp: chỉ cần NHẬN RA TÊN để chuyển tiếp tư vấn</h3>'
            + '<p>Ngoài 3 mẫu chủ đạo, còn vài mẫu <b>cao cấp, đặc thù</b>, ít phổ biến hơn '
            'nhưng khách đôi khi sẽ hỏi.</p>'
            + _fig('3 mẫu cao cấp &mdash; nhận diện phong cách', _svg_caocap(),
                   'Indochine (giao thoa Á-Âu, vòm/cột) • Tân cổ điển (đối xứng, phào chỉ) • Mái Pháp (mái dốc nhiều lớp).')
            + _photos('Hình thực tế', [('image49.jpg', ''), ('image44.jpg', ''), ('image36.jpg', ''),
                                       ('image43.jpg', ''), ('image40.jpg', ''), ('image35.jpg', '')])
            + _table(['Mẫu', 'Đặc điểm chung'],
                     [['<b>Indochine</b> (Đông Dương)', 'Giao thoa <b>Á &mdash; Âu</b>, hoài cổ, sang trọng, hay dùng gạch bông, hoa văn xưa'],
                      ['<b>Tân cổ điển</b>', 'Sang trọng, có <b>phào chỉ</b>, đối xứng, bề thế nhưng nhẹ nhàng hơn cổ điển thuần'],
                      ['<b>Nhà mái Pháp</b>', 'Biệt thự kiểu Pháp, <b>mái dốc nhiều lớp</b>, cầu kỳ, đẳng cấp, chi phí cao']],
                     widths=['26%', '74%'])
            + _box('info', 'Đây là nhóm <b>cao cấp</b>, chi phí lớn và cần đội thiết kế chuyên '
                   'sâu. Bạn chỉ cần <b>nhận ra tên gọi</b> để khi khách hỏi thì biết và chuyển '
                   'tiếp tư vấn, không cần thuộc chi tiết.')
            + _core('Mẫu cao cấp = <b>Indochine &middot; Tân cổ điển &middot; Mái Pháp</b> &mdash; nhớ TÊN để nhận ra, chuyển đội thiết kế.')
            + _quiz('mnh_khac',
                    'Nhóm mẫu nhà cao cấp (tham khảo) gồm những gì?',
                    [('Indochine, Tân cổ điển, Nhà mái Pháp', True),
                     ('Vuông hiện đại, mái Nhật, mái Thái', False),
                     ('Nhà trọ, chung cư, nhà cấp 4', False),
                     ('Tum, sân thượng, tầng lửng', False)],
                    'Nhóm cao cấp: Indochine, Tân cổ điển, Mái Pháp — chỉ cần nhận ra tên.'))

    # ------------------------------------------------------------------
    def _mnh_l_hangmuc(self):
        return (
            self._mnh_tag('HẠNG MỤC ĐẶC BIỆT')
            + '<h3>Tum &middot; Sân thượng &middot; Tầng lửng &middot; Thông tầng</h3>'
            + '<p>Đây là các phần khách hay hỏi thêm khi xây nhà. Hiểu để tư vấn và biết phần '
            'nào làm <b>tăng chi phí</b>.</p>'
            + _fig('Mặt cắt nhà &mdash; vị trí 4 hạng mục', _svg_hangmuc(),
                   'Tum che cầu thang trên cùng; sân thượng cạnh tum; tầng lửng là tầng phụ ~3m; thông tầng là khoảng thông 2 tầng ~6m.')
            + '<h4>1) TUM và SÂN THƯỢNG</h4>'
            + _photos('Hình thực tế', [('image42.jpg', 'Tum và sân thượng'), ('image41.jpg', '')])
            + _table(['Hạng mục', 'Nội dung'],
                     [['<b>Tum</b>', 'Diện tích <b>15 &mdash; 25 m&#178;</b>; là <b>mái che khu cầu thang</b> trên cùng; <b>có thể kết hợp làm phòng thờ</b>'],
                      ['<b>Sân thượng</b>', '<b>Sân trước:</b> ăn BBQ, uống cafe, trồng cây&hellip; &middot; <b>Sân sau:</b> để máy giặt, phơi đồ. Có thể có <b>mái trang trí</b> hoặc không']],
                     widths=['22%', '78%'])
            + _box('warn', 'Sân thượng <b>có mái trang trí</b> thì <b>chi phí thi công CAO '
                   'HƠN</b> so với sân thượng không mái. Đừng quên nói rõ khi báo giá.')
            + '<h4>2) TẦNG LỬNG và THÔNG TẦNG</h4>'
            + _photos('Hình thực tế', [('image45.jpg', 'Tầng lửng - Thông tầng')])
            + _table(['Hạng mục', 'Nội dung'],
                     [['<b>Tầng lửng</b>', 'Tầng phụ xen giữa, chiều cao khoảng <b>3 m</b>'],
                      ['<b>Thông tầng</b>', 'Khoảng không thông 2 tầng, thường ở <b>phòng khách</b>; chiều cao khoảng <b>6 m</b>; chiếm <b>30 &mdash; 50% diện tích sàn</b>']],
                     widths=['22%', '78%'])
            + _wrong(['Nhầm <b>tầng lửng</b> (tầng phụ ~3m) với <b>thông tầng</b> (khoảng thông '
                      '2 tầng ~6m) &mdash; hai thứ ngược nhau: lửng THÊM sàn, thông tầng BỎ TRỐNG sàn.'])
            + _core('Tum <b>15-25 m&#178;</b> (che cầu thang, có thể phòng thờ) &middot; Tầng lửng '
                    '<b>~3m</b> &middot; Thông tầng <b>~6m, 30-50% sàn</b> &middot; mái trang trí = <b>tốn thêm</b>.')
            + _fml('TUM 15-25m&#178; &middot; TẦNG LỬNG ~3m (thêm sàn) &middot; THÔNG TẦNG ~6m, 30-50% sàn (bỏ trống). '
                   'Sân thượng có mái = đắt hơn.')
            + _quiz('mnh_hm',
                    'Thông tầng khác tầng lửng ở điểm nào?',
                    [('Thông tầng là khoảng THÔNG 2 tầng (~6m, bỏ trống sàn); tầng lửng là tầng phụ THÊM vào (~3m)', True),
                     ('Hai cái giống hệt nhau', False),
                     ('Thông tầng cao 3m, tầng lửng cao 6m', False),
                     ('Cả hai đều nằm trên mái nhà', False)],
                    'Tầng lửng = thêm sàn (~3m); thông tầng = bỏ trống, thông 2 tầng (~6m, 30-50% sàn).'))

    # ------------------------------------------------------------------
    def _mnh_l_gold(self):
        return (
            self._mnh_tag('&#127942; TỔNG HỢP KIẾN THỨC')
            + '<h3>Nhận biết nhanh + kịch bản tư vấn mẫu nhà</h3>'
            + _fig('Sơ đồ tư vấn chọn mẫu nhà', _svg_decide(),
                   'Hỏi đất + ngân sách → đất hẹp/tiết kiệm: vuông hiện đại; đất rộng vừa tiền: mái Nhật; đất rộng nhiều tiền: mái Thái.')
            + _table(['Mẫu nhà', 'Mái', 'Hợp với', 'Chi phí'],
                     [['<b>Vuông hiện đại</b>', 'Mái bằng', 'Nhà phố', '<span class="cheap">Rẻ nhất</span>'],
                      ['<b>Mái Nhật</b>', 'Mái thấp, KHÔNG góc A', 'Đất rộng, nhà vườn', '<span class="mid">Trung bình</span>'],
                      ['<b>Mái Thái</b>', 'Mái cao, CÓ góc A', 'Đất rộng, nhà vườn', '<span class="exp">Đắt nhất (trong 3)</span>']],
                     widths=['24%', '30%', '26%', '20%'])
            + '<h4>&#127919; Kịch bản tư vấn ngắn</h4>'
            + _order([
                ('Khách đất hẹp / nhà phố, muốn tiết kiệm', 'Gợi ý NHÀ VUÔNG HIỆN ĐẠI (mái bằng, rẻ nhất).'),
                ('Khách đất rộng, thích mái ngói, ngân sách vừa', 'Gợi ý MÁI NHẬT (thấp, không góc A, giá vừa).'),
                ('Khách đất rộng, thích bề thế, ngân sách cao hơn', 'Gợi ý MÁI THÁI (cao, góc A, sang hơn).'),
            ])
            + _box('ok', 'Luôn hỏi <b>diện tích đất</b> và <b>ngân sách</b> TRƯỚC khi gợi ý mẫu '
                   '&mdash; tránh gợi ý mẫu quá đắt hoặc không hợp đất của khách.')
            + '<h4>&#128221; Bảng ghi nhớ tổng hợp</h4>'
            + _table(['Chủ đề', 'Điều phải thuộc'],
                     [['<b>Vuông hiện đại</b>', 'Mái bằng, hợp nhà phố, rẻ nhất, phổ biến nhất.'],
                      ['<b>Mái Nhật</b>', 'Mái thấp, KHÔNG góc chữ A, lộ ngói, đất rộng, giá trung bình.'],
                      ['<b>Mái Thái</b>', 'Mái cao, CÓ góc chữ A, không thấy ngói, đất rộng, đắt hơn Nhật.'],
                      ['<b>Mẫu cao cấp</b>', 'Indochine, Tân cổ điển, Mái Pháp &mdash; nhớ tên, chuyển đội thiết kế.'],
                      ['<b>Tum</b>', '15-25 m&#178;, che cầu thang, có thể làm phòng thờ.'],
                      ['<b>Tầng lửng / Thông tầng</b>', 'Lửng ~3m (thêm sàn); thông tầng ~6m, 30-50% sàn (bỏ trống).']],
                     widths=['26%', '74%'])
            + _core('Thuộc 3 mẫu chủ đạo + phân biệt <b>mái Nhật (thấp, không góc A, rẻ hơn)</b> '
                    'với <b>mái Thái (cao, có góc A, đắt hơn)</b> là tư vấn được mẫu nhà cơ bản.')
            + _fml('Hỏi <b>ĐẤT + NGÂN SÁCH</b> &rarr; đất hẹp = vuông hiện đại; đất rộng vừa tiền '
                   '= mái Nhật; đất rộng nhiều tiền = mái Thái.')
            + _quiz('mnh_gold',
                    'Khách đất vườn rộng, ngân sách cao, thích nhà bề thế sang trọng. Gợi ý mẫu nào?',
                    [('Mái Thái (mái cao, góc chữ A, sang trọng, đắt hơn) &mdash; hợp đất rộng, ngân sách cao', True),
                     ('Nhà vuông hiện đại cho rẻ', False),
                     ('Bắt buộc mái Nhật', False),
                     ('Nhà cấp 4', False)],
                    'Đất rộng + ngân sách cao + thích bề thế → mái Thái (cao, góc A, sang hơn).'))

    # ==================================================================
    #  20 CÂU HỎI
    # ==================================================================
    def _mnh_questions(self):
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
