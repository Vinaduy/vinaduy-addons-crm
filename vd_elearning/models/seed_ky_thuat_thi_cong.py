# -*- coding: utf-8 -*-
"""Seed nội dung + 20 câu thi cho khóa "KỸ THUẬT THI CÔNG" (trong lộ trình CÂU
HỎI KHÓ).

Khóa dạy nhân viên kinh doanh cách XỬ LÝ các câu hỏi kỹ thuật khó khi tư vấn xây
nhà trọn gói (móng, vật tư, nứt tường, thấm, bê tông, trần, bảo hành, tường...).
Cốt lõi: khách hỏi kỹ thuật KHÔNG phải vì họ hiểu kỹ thuật, mà vì họ SỢ mất tiền
-> luôn theo CÔNG THỨC 5 BƯỚC: Đồng tình -> Nguyên nhân -> Quy trình công ty ->
Cam kết -> Kết thúc bằng sự yên tâm.

GIAO DIỆN kiểu Streamlit: menu trái chọn từng bài (micro-learning) + hộp màu +
hình mô phỏng SVG có công thức + quiz chấm đúng/sai tức thì (thuần CSS
input:checked, KHÔNG JS). vd_body sanitize=False + render markup() nên HTML/SVG
thô giữ nguyên.

Helper nối chuỗi (+) -> tránh bẫy %. MỌI class method dùng prefix RIÊNG _kttc_
để KHÔNG trùng tên với seed khác (xem reference-seed-method-name-collision).
Idempotent theo version lưu ở ir.config_parameter.
"""
from odoo import api, models

_KTTC_VERSION = 'v2-mong-3-tinh-huong'
_PARAM_KEY = 'vd_elearning.ky_thuat_thi_cong_seed_version'

_WRAP = 'font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'

_STYLE = (
    '<style>'
    '.vd-kttc{font-size:16px;line-height:1.7;color:#1f2937;'
    'width:96vw;max-width:1720px;position:relative;left:50%;transform:translateX(-50%);'
    'margin-top:-1.3cm;}'
    '.vd-kttc .vd-course{background:linear-gradient(180deg,#f3f8ff 0%,#f6fbff 100%);'
    'border-radius:18px;padding:16px;}'
    '.vd-kttc h3{font-size:19px;font-weight:800;color:#0f172a;margin:2px 0 12px;}'
    '.vd-kttc h4{font-size:16px;font-weight:800;color:#111827;margin:16px 0 6px;}'
    '.vd-kttc p{margin:0 0 10px;}'
    '.vd-kttc ul,.vd-kttc ol{margin:0 0 10px;padding-left:22px;}'
    '.vd-kttc li{margin:5px 0;}'
    '.vd-kttc b{color:#111827;}'
    '.vd-kttc table{border-collapse:collapse;width:100%;margin:8px 0 6px;font-size:15px;}'
    '.vd-kttc th,.vd-kttc td{border:1px solid #e5e7eb;padding:8px 11px;text-align:left;vertical-align:top;}'
    '.vd-kttc th{background:#f1f5f9;font-weight:800;color:#334155;}'
    '.vd-kttc .thok{background:#dcfce7;color:#15803d;}'
    '.vd-kttc .thno{background:#fee2e2;color:#b91c1c;}'
    '.vd-kttc .no{color:#b91c1c;font-weight:700;}'
    '.vd-kttc .yes{color:#15803d;font-weight:700;}'
    '.vd-kttc .navr,.vd-kttc .qopt{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}'
    '.vd-kttc .vc-layout{display:flex;gap:18px;align-items:flex-start;}'
    '.vd-kttc .vc-side{flex:0 0 300px;}'
    '.vd-kttc .vc-sidehead{font-size:12.5px;font-weight:800;letter-spacing:1px;'
    'color:#64748b;text-transform:uppercase;margin:4px 6px 10px;}'
    '.vd-kttc .vc-navbtn{display:flex;align-items:center;gap:8px;text-align:left;'
    'padding:10px 12px;margin:8px 0;border-radius:12px;'
    'background:#ffffff;color:#475569;font-weight:700;font-size:14px;cursor:pointer;'
    'border:2px solid #eef2f7;transition:all .15s;}'
    '.vd-kttc .vc-navbtn:hover{background:#eef5ff;border-color:#bfdbff;color:#1d4ed8;}'
    '.vd-kttc .vc-nbadge{flex:0 0 auto;display:inline-block;background:#e8f0ff;color:#1d4ed8;'
    'font-size:10.5px;font-weight:800;letter-spacing:1px;padding:3px 9px;border-radius:20px;'
    'white-space:nowrap;}'
    '.vd-kttc .vc-ntitle{flex:1 1 auto;font-weight:700;line-height:1.25;white-space:nowrap;}'
    '.vd-kttc .vc-content{flex:1;min-width:0;background:#ffffff;border:1px solid #eef2f7;'
    'border-radius:16px;padding:24px 26px;box-shadow:0 8px 28px rgba(2,6,23,.06);}'
    '.vd-kttc .vc-panel{display:none;}'
    '.vd-kttc .vc-tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:1px;'
    'color:#1d4ed8;background:#e8f0ff;padding:3px 10px;border-radius:20px;margin-bottom:8px;}'
    '.vd-kttc .box{border-left:5px solid;border-radius:0 8px 8px 0;padding:11px 15px;margin:9px 0;}'
    '.vd-kttc .b-err{background:#fef2f2;border-color:#dc2626;color:#991b1b;}'
    '.vd-kttc .b-warn{background:#fffbeb;border-color:#f59e0b;color:#92400e;}'
    '.vd-kttc .b-info{background:#eff6ff;border-color:#3b82f6;color:#1e40af;}'
    '.vd-kttc .b-ok{background:#f0fdf4;border-color:#16a34a;color:#166534;}'
    # công thức
    '.vd-kttc .fml{background:linear-gradient(135deg,#faf5ff,#eef2ff);border:2px solid #c4b5fd;'
    'border-radius:12px;padding:13px 16px;margin:10px 0;}'
    '.vd-kttc .fml .fh{font-weight:800;color:#6d28d9;font-size:12.5px;letter-spacing:.6px;margin-bottom:5px;}'
    '.vd-kttc .fml .fml-b{color:#4c1d95;font-weight:600;}'
    # câu mẫu (script)
    '.vd-kttc .say{background:#ecfeff;border:2px dashed #22d3ee;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#155e75;font-style:italic;}'
    '.vd-kttc .say .sh{font-style:normal;font-weight:800;color:#0e7490;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:4px;}'
    # sai lầm nhân viên
    '.vd-kttc .wrong{background:#fff1f2;border:2px solid #fda4af;border-radius:12px;'
    'padding:12px 16px;margin:10px 0;color:#9f1239;}'
    '.vd-kttc .wrong .wh{font-weight:800;color:#be123c;font-size:12.5px;'
    'letter-spacing:.6px;margin-bottom:5px;}'
    # hình mô phỏng SVG
    '.vd-kttc .fig{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;'
    'padding:14px 16px 10px;margin:12px 0;text-align:center;}'
    '.vd-kttc .fig svg{max-width:100%;height:auto;}'
    '.vd-kttc .fig .cap{font-size:13px;color:#64748b;margin-top:6px;font-weight:600;}'
    '.vd-kttc .fig .figh{font-size:12.5px;font-weight:800;letter-spacing:.6px;'
    'color:#0f172a;text-transform:uppercase;margin-bottom:8px;text-align:left;}'
    # thứ tự đánh số
    '.vd-kttc .vc-order{margin:12px 0;border:1px solid #bfdbff;border-radius:12px;overflow:hidden;}'
    '.vd-kttc .vc-ostep{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;'
    'border-bottom:1px dashed #dbeafe;background:#f7faff;}'
    '.vd-kttc .vc-ostep:last-child{border-bottom:none;}'
    '.vd-kttc .vc-onum{flex:0 0 34px;width:34px;height:34px;border-radius:50%;background:#1d4ed8;'
    'color:#fff;font-weight:800;text-align:center;line-height:34px;}'
    '.vd-kttc .vc-ot{font-weight:800;color:#1e3a8a;}'
    '.vd-kttc .vc-od{color:#1e40af;font-size:14.5px;}'
    # quiz
    '.vd-kttc .quiz{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin:18px 0 4px;}'
    '.vd-kttc .quiz .qq{font-weight:800;color:#0f172a;margin-bottom:4px;}'
    '.vd-kttc .quiz .qhint{font-size:13px;color:#64748b;margin-bottom:10px;}'
    '.vd-kttc .opts label{display:block;border:2px solid #e5e7eb;border-radius:10px;'
    'padding:11px 14px;margin:8px 0;cursor:pointer;background:#fff;transition:all .12s;}'
    '.vd-kttc .opts label:hover{border-color:#cbd5e1;background:#f8fafc;}'
    '.vd-kttc .qk{display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
    'border-radius:50%;background:#f1f5f9;font-weight:800;margin-right:9px;color:#334155;}'
    '.vd-kttc .fb{display:none;border-radius:8px;padding:11px 15px;margin-top:12px;font-weight:700;}'
    '.vd-kttc .fb-right{background:#dcfce7;color:#15803d;}'
    '.vd-kttc .fb-wrong{background:#fef9c3;color:#854d0e;}'
    '@media(max-width:820px){'
    '.vd-kttc .vc-layout{flex-direction:column;}'
    '.vd-kttc .vc-side{flex-basis:auto;width:100%;display:flex;flex-wrap:wrap;gap:6px;}'
    '.vd-kttc .vc-sidehead{width:100%;}'
    '.vd-kttc .vc-navbtn{margin:0;font-size:13.5px;padding:9px 12px;}}'
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


def _say(text):
    return ('<div class="say"><div class="sh">&#128172; CÂU MẪU NÓI VỚI KHÁCH</div>'
            + text + '</div>')


def _wrong(items):
    lis = ''.join('<li>' + x + '</li>' for x in items)
    return ('<div class="wrong"><div class="wh">&#10060; SAI LẦM NHÂN VIÊN HAY MẮC</div>'
            '<ul style="margin:0;">' + lis + '</ul></div>')


def _fig(head, svg, cap):
    return ('<div class="fig"><div class="figh">' + head + '</div>' + svg
            + '<div class="cap">' + cap + '</div></div>')


def _table(head, rows, widths=None):
    th = ''
    for i, h in enumerate(head):
        w = (' style="width:' + widths[i] + ';"') if (widths and i < len(widths) and widths[i]) else ''
        th += '<th' + w + '>' + h + '</th>'
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + c + '</td>' for c in r) + '</tr>'
    return '<table><tr>' + th + '</tr>' + body + '</table>'


def _nendont(nen, khong):
    nl = ''.join('<li>' + x + '</li>' for x in nen)
    kl = ''.join('<li>' + x + '</li>' for x in khong)
    return ('<table><tr><th style="width:50%;" class="thok">&#9989; NÊN</th>'
            '<th class="thno">&#10060; KHÔNG NÊN</th></tr>'
            '<tr><td><ul style="margin:0;">' + nl + '</ul></td>'
            '<td><ul style="margin:0;">' + kl + '</ul></td></tr></table>')


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
def _svg_mong_house(cx):
    """Ve khung NHA (than + mai) tai tam cx, day than o y=150."""
    x = cx - 66
    return ('<rect x="' + str(x) + '" y="98" width="132" height="52" fill="#e5e7eb" stroke="#94a3b8"/>'
            '<polygon points="' + str(cx - 78) + ',98 ' + str(cx) + ',62 ' + str(cx + 78) + ',98" '
            'fill="#cbd5e1" stroke="#94a3b8"/>'
            '<text x="' + str(cx) + '" y="130" font-size="13" fill="#334155" '
            'font-weight="800" text-anchor="middle">NHÀ</text>')


def _svg_mong_label(cx, th, ten):
    return ('<text x="' + str(cx) + '" y="272" font-size="11" fill="#c2410e" '
            'font-weight="800" text-anchor="middle">' + th + '</text>'
            '<text x="' + str(cx) + '" y="291" font-size="14" fill="#1d4ed8" '
            'font-weight="900" text-anchor="middle">' + ten + '</text>')


def _svg_mong():
    c1, c2, c3 = 140, 400, 655
    svg = ('<svg viewBox="0 0 800 305" width="800" role="img" '
           'aria-label="Ba tinh huong mong: coc, bang, don">')
    # nen dat (2 lop)
    svg += ('<rect x="0" y="175" width="800" height="52" fill="#fde68a"/>'
            '<rect x="0" y="227" width="800" height="55" fill="#86efac"/>'
            '<text x="10" y="197" font-size="11" fill="#92400e" font-weight="700">LỚP ĐẤT YẾU</text>'
            '<text x="10" y="250" font-size="11" fill="#166534" font-weight="700">LỚP ĐẤT TỐT (đất cứng)</text>')
    # duong ke chia 3 tinh huong
    svg += ('<line x1="268" y1="50" x2="268" y2="262" stroke="#cbd5e1" stroke-dasharray="3 4"/>'
            '<line x1="528" y1="50" x2="528" y2="262" stroke="#cbd5e1" stroke-dasharray="3 4"/>')
    # --- Tinh huong 1: MONG COC (coc xuyen dat yeu xuong dat tot) ---
    svg += _svg_mong_house(c1)
    svg += '<rect x="' + str(c1 - 56) + '" y="150" width="112" height="12" fill="#64748b"/>'
    for dx in (-44, -6, 32):
        svg += '<rect x="' + str(c1 + dx) + '" y="162" width="12" height="80" fill="#475569"/>'
    svg += ('<text x="' + str(c1) + '" y="252" font-size="10.5" fill="#1e3a8a" '
            'text-anchor="middle">cọc xuống tận đất tốt</text>')
    svg += _svg_mong_label(c1, 'TÌNH HUỐNG 1', 'MÓNG CỌC')
    # --- Tinh huong 2: MONG BANG (dai lien tua lop dat tren) ---
    svg += _svg_mong_house(c2)
    svg += ('<polygon points="' + str(c2 - 60) + ',150 ' + str(c2 + 60) + ',150 '
            + str(c2 + 72) + ',172 ' + str(c2 - 72) + ',172" fill="#64748b"/>')
    svg += ('<text x="' + str(c2) + '" y="200" font-size="10.5" fill="#92400e" '
            'text-anchor="middle">dải liền tựa đất trên</text>')
    svg += _svg_mong_label(c2, 'TÌNH HUỐNG 2', 'MÓNG BĂNG')
    # --- Tinh huong 3: MONG DON (dai de rieng le duoi tung cot) ---
    svg += _svg_mong_house(c3)
    for dx in (-52, -13, 26):
        svg += ('<rect x="' + str(c3 + dx) + '" y="150" width="6" height="14" fill="#475569"/>'
                '<rect x="' + str(c3 + dx - 8) + '" y="164" width="22" height="12" fill="#64748b"/>')
    svg += ('<text x="' + str(c3) + '" y="200" font-size="10.5" fill="#92400e" '
            'text-anchor="middle">đế đơn riêng dưới từng cột</text>')
    svg += _svg_mong_label(c3, 'TÌNH HUỐNG 3', 'MÓNG ĐƠN')
    return svg + '</svg>'


def _svg_nut():
    return (
        '<svg viewBox="0 0 560 260" width="560" role="img" aria-label="Nứt tường và lưới chống nứt">'
        # cot BT
        '<rect x="60" y="30" width="46" height="200" fill="#9ca3af" stroke="#6b7280"/>'
        '<text x="83" y="250" font-size="11" fill="#374151" font-weight="700" text-anchor="middle">CỘT BÊ TÔNG</text>'
        # gach
        '<rect x="106" y="30" width="180" height="200" fill="#fca5a5" stroke="#ef4444"/>'
        '<text x="196" y="250" font-size="11" fill="#b91c1c" font-weight="700" text-anchor="middle">TƯỜNG GẠCH</text>'
        # vet nut o tiep giap
        '<polyline points="106,40 112,70 104,105 114,145 106,190 112,225" '
        'fill="none" stroke="#7f1d1d" stroke-width="3" stroke-dasharray="2 3"/>'
        '<text x="150" y="24" font-size="12" fill="#7f1d1d" font-weight="800">&larr; nứt ở tiếp giáp gạch - cột</text>'
        # luoi chong nut (giai phap)
        '<rect x="330" y="30" width="46" height="200" fill="#9ca3af" stroke="#6b7280"/>'
        '<rect x="376" y="30" width="150" height="200" fill="#fca5a5" stroke="#ef4444"/>'
        # luoi
        '<g stroke="#16a34a" stroke-width="2">'
        '<line x1="352" y1="40" x2="352" y2="220"/><line x1="376" y1="40" x2="376" y2="220"/>'
        '<line x1="400" y1="40" x2="400" y2="220"/>'
        '<line x1="335" y1="60" x2="415" y2="60"/><line x1="335" y1="100" x2="415" y2="100"/>'
        '<line x1="335" y1="140" x2="415" y2="140"/><line x1="335" y1="180" x2="415" y2="180"/>'
        '</g>'
        '<text x="428" y="130" font-size="12" fill="#166534" font-weight="800">LƯỚI CHỐNG NỨT</text>'
        '<text x="428" y="150" font-size="11" fill="#166534">phủ tiếp giáp + ống điện/nước</text>'
        '</svg>')


def _svg_tham():
    return (
        '<svg viewBox="0 0 560 250" width="560" role="img" aria-label="Chống thấm và ngâm thử nước">'
        # cac lop san WC
        '<rect x="40" y="150" width="300" height="22" fill="#94a3b8"/>'
        '<text x="350" y="166" font-size="11" fill="#334155" font-weight="700">Sàn bê tông</text>'
        '<rect x="40" y="130" width="300" height="20" fill="#1e3a8a"/>'
        '<text x="350" y="146" font-size="11" fill="#1e3a8a" font-weight="700">Chống thấm Sika + màng PE</text>'
        '<rect x="40" y="112" width="300" height="18" fill="#cbd5e1"/>'
        '<text x="350" y="126" font-size="11" fill="#475569" font-weight="700">Lớp cán + gạch ốp lát</text>'
        # ngam nuoc 7 ngay
        '<rect x="40" y="70" width="300" height="42" fill="#7dd3fc" opacity="0.8"/>'
        '<text x="190" y="96" font-size="13" fill="#075985" font-weight="800" text-anchor="middle">NGÂM THỬ NƯỚC 7 NGÀY</text>'
        # dong ho
        '<circle cx="460" cy="120" r="46" fill="#e0f2fe" stroke="#0284c7" stroke-width="3"/>'
        '<line x1="460" y1="120" x2="460" y2="88" stroke="#0284c7" stroke-width="4"/>'
        '<line x1="460" y1="120" x2="486" y2="132" stroke="#0284c7" stroke-width="4"/>'
        '<text x="460" y="196" font-size="12" fill="#075985" font-weight="800" text-anchor="middle">Đạt mới ốp lát</text>'
        '<text x="460" y="214" font-size="11" fill="#b91c1c" font-weight="700" text-anchor="middle">Không đạt = KHÔNG bàn giao</text>'
        '</svg>')


def _svg_betong():
    return (
        '<svg viewBox="0 0 560 220" width="560" role="img" aria-label="Mẫu bê tông mác 350">'
        # mau lap phuong
        '<polygon points="70,120 130,120 130,180 70,180" fill="#cbd5e1" stroke="#64748b" stroke-width="2"/>'
        '<polygon points="70,120 90,100 150,100 130,120" fill="#e2e8f0" stroke="#64748b" stroke-width="2"/>'
        '<polygon points="130,120 150,100 150,160 130,180" fill="#94a3b8" stroke="#64748b" stroke-width="2"/>'
        '<text x="110" y="205" font-size="12" fill="#334155" font-weight="700" text-anchor="middle">Mẫu 15x15x15</text>'
        # mui ten nen
        '<line x1="230" y1="60" x2="230" y2="100" stroke="#dc2626" stroke-width="6"/>'
        '<polygon points="220,98 240,98 230,116" fill="#dc2626"/>'
        '<line x1="230" y1="176" x2="230" y2="136" stroke="#dc2626" stroke-width="6"/>'
        '<polygon points="220,138 240,138 230,120" fill="#dc2626"/>'
        '<rect x="200" y="116" width="60" height="24" fill="#94a3b8" stroke="#475569"/>'
        '<text x="230" y="205" font-size="12" fill="#334155" font-weight="700" text-anchor="middle">Nén kiểm tra cường độ</text>'
        # nhan mac 350
        '<rect x="330" y="90" width="200" height="70" rx="12" fill="#1d4ed8"/>'
        '<text x="430" y="122" font-size="22" fill="#fff" font-weight="900" text-anchor="middle">MÁC 350</text>'
        '<text x="430" y="146" font-size="12" fill="#dbeafe" text-anchor="middle">bê tông thương phẩm, có hóa đơn</text>'
        '</svg>')


def _svg_baohanh():
    return (
        '<svg viewBox="0 0 620 170" width="620" role="img" aria-label="Thời gian bảo hành">'
        # truc
        '<line x1="40" y1="110" x2="590" y2="110" stroke="#94a3b8" stroke-width="3"/>'
        '<text x="40" y="140" font-size="12" fill="#64748b" font-weight="700">0</text>'
        # 1 nam - dien
        '<line x1="150" y1="110" x2="150" y2="70" stroke="#f59e0b" stroke-width="3"/>'
        '<rect x="96" y="40" width="108" height="30" rx="8" fill="#fef3c7" stroke="#f59e0b"/>'
        '<text x="150" y="60" font-size="12" fill="#92400e" font-weight="800" text-anchor="middle">1 năm: điện</text>'
        '<text x="150" y="140" font-size="12" fill="#64748b" font-weight="700" text-anchor="middle">1</text>'
        # 2 nam - thiet bi
        '<line x1="310" y1="110" x2="310" y2="70" stroke="#0ea5e9" stroke-width="3"/>'
        '<rect x="228" y="40" width="164" height="30" rx="8" fill="#e0f2fe" stroke="#0ea5e9"/>'
        '<text x="310" y="60" font-size="12" fill="#075985" font-weight="800" text-anchor="middle">2 năm: TB vệ sinh/cửa/gạch</text>'
        '<text x="310" y="140" font-size="12" fill="#64748b" font-weight="700" text-anchor="middle">2</text>'
        # 5 nam - ket cau
        '<line x1="560" y1="110" x2="560" y2="70" stroke="#16a34a" stroke-width="4"/>'
        '<rect x="486" y="40" width="128" height="30" rx="8" fill="#dcfce7" stroke="#16a34a"/>'
        '<text x="550" y="60" font-size="12" fill="#166534" font-weight="800" text-anchor="middle">5 năm: KẾT CẤU</text>'
        '<text x="560" y="140" font-size="12" fill="#64748b" font-weight="700" text-anchor="middle">5</text>'
        '</svg>')


def _svg_tuong():
    return (
        '<svg viewBox="0 0 560 250" width="560" role="img" aria-label="Tường 200 và tường 100">'
        # khung tuong bao 200 (day)
        '<rect x="60" y="40" width="360" height="180" fill="none" stroke="#1d4ed8" stroke-width="18"/>'
        '<text x="240" y="30" font-size="13" fill="#1d4ed8" font-weight="800" text-anchor="middle">TƯỜNG BAO 200mm (tường 20)</text>'
        # tuong ngan 100 (mong)
        '<line x1="240" y1="49" x2="240" y2="211" stroke="#0ea5e9" stroke-width="9"/>'
        '<line x1="69" y1="140" x2="240" y2="140" stroke="#0ea5e9" stroke-width="9"/>'
        '<text x="330" y="150" font-size="12" fill="#075985" font-weight="800">tường ngăn 100mm</text>'
        '<text x="330" y="168" font-size="12" fill="#075985" font-weight="800">(tường 10)</text>'
        '<text x="150" y="100" font-size="12" fill="#334155">Phòng</text>'
        '<text x="150" y="185" font-size="12" fill="#334155">Phòng</text>'
        '<text x="300" y="100" font-size="12" fill="#334155">Phòng</text>'
        '</svg>')


def _svg_congthuc():
    steps = [('1', 'ĐỒNG TÌNH', '#f59e0b'), ('2', 'NGUYÊN NHÂN', '#3b82f6'),
             ('3', 'QUY TRÌNH CÔNG TY', '#8b5cf6'), ('4', 'CAM KẾT', '#0ea5e9'),
             ('5', 'YÊN TÂM', '#16a34a')]
    out = ('<svg viewBox="0 0 720 120" width="720" role="img" '
           'aria-label="Công thức 5 bước xử lý câu hỏi khó">')
    x = 20
    for i, (n, t, c) in enumerate(steps):
        out += ('<rect x="' + str(x) + '" y="35" width="112" height="50" rx="12" fill="' + c + '"/>'
                '<text x="' + str(x + 56) + '" y="58" font-size="15" fill="#fff" '
                'font-weight="900" text-anchor="middle">' + n + '</text>'
                '<text x="' + str(x + 56) + '" y="76" font-size="10.5" fill="#fff" '
                'font-weight="700" text-anchor="middle">' + t + '</text>')
        if i < len(steps) - 1:
            ax = x + 112
            out += ('<polygon points="' + str(ax + 2) + ',52 ' + str(ax + 18) + ',60 '
                    + str(ax + 2) + ',68" fill="#94a3b8"/>')
        x += 140
    return out + '</svg>'


class SlideChannelSeedKyThuatThiCong(models.Model):
    _inherit = 'slide.channel'

    @api.model
    def _vd_seed_ky_thuat_thi_cong(self):
        ch = self.env.ref('vd_elearning.course_ky_thuat_thi_cong',
                          raise_if_not_found=False)
        if not ch:
            ch = self.sudo().search([('name', 'ilike', 'Kỹ thuật thi công')], limit=1)
        if not ch:
            return False

        # Gan khoa vao LO TRINH "Cau hoi kho" (tao trong DB, khong co external id).
        path = self.env['vd.learning.path'].sudo().search(
            [('name', 'ilike', 'Câu hỏi khó'), ('zone', '=', 'sales')], limit=1)
        if path and ch.vd_path_id != path:
            ch.sudo().write({'vd_path_id': path.id})

        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _KTTC_VERSION:
            return True

        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        ch.slide_ids.filtered(lambda s: not s.is_category).unlink()

        Slide.create({
            'channel_id': ch.id, 'name': 'Nội dung khóa học',
            'slide_category': 'article',
            'vd_body': _STYLE + ('<div class="vd-kttc" style="%s">%s</div>'
                                 % (_WRAP, self._kttc_app())),
            'sequence': 1, 'is_published': True,
        })

        quiz = Slide.create({
            'channel_id': ch.id, 'name': 'Bài thi - 20 câu',
            'slide_category': 'quiz', 'sequence': 999, 'is_published': True,
        })
        qseq = 1
        for text, answers in self._kttc_questions():
            Question.create({
                'slide_id': quiz.id, 'question': text, 'sequence': qseq,
                'answer_ids': [
                    (0, 0, {'text_value': a, 'is_correct': c, 'sequence': i + 1})
                    for i, (a, c) in enumerate(answers)
                ],
            })
            qseq += 1

        ICP.set_param(_PARAM_KEY, _KTTC_VERSION)
        return True

    # ==================================================================
    #  APP (menu trái + panel phải)
    # ==================================================================
    def _kttc_app(self):
        lessons = self._kttc_lessons()
        radios = navbtns = panels = rules = ''
        for i, (icon, badge, title, body) in enumerate(lessons):
            rid = 'kttcL' + str(i)
            pid = 'kttcP' + str(i)
            radios += ('<input class="navr" type="radio" name="kttcnav" id="' + rid + '"'
                       + (' checked' if i == 0 else '') + '>')
            badge_html = ('<span class="vc-nbadge">' + badge + '</span>') if badge else ''
            navbtns += ('<label class="vc-navbtn" for="' + rid + '">' + badge_html
                        + '<span class="vc-ntitle">' + icon + ' ' + title + '</span></label>')
            panels += '<section class="vc-panel" id="' + pid + '">' + body + '</section>'
            rules += '#' + rid + ':checked ~ .vc-layout #' + pid + '{display:block}'
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + ']'
                      '{background:#1d4ed8;color:#fff;border-color:#1d4ed8}')
            rules += ('#' + rid + ':checked ~ .vc-layout label[for=' + rid + '] .vc-nbadge'
                      '{background:#ffffff;color:#1d4ed8}')
        hero = (
            '<div style="background:linear-gradient(120deg,#1d4ed8 0%,#2563eb 55%,#3b82f6 100%);'
            'border-radius:16px;padding:24px 26px;margin-bottom:14px;'
            'box-shadow:0 10px 30px rgba(29,78,216,.28);">'
            '<div style="color:#dbeafe;font-size:13px;font-weight:800;letter-spacing:2px;">'
            'CÂU HỎI KHÓ &mdash; KỸ THUẬT THI CÔNG</div>'
            '<div style="color:#fff;font-size:26px;font-weight:900;margin-top:6px;line-height:1.2;'
            'text-shadow:0 2px 8px rgba(0,0,0,.15);">'
            'Xử lý câu hỏi kỹ thuật khó khi tư vấn xây nhà trọn gói</div>'
            '<div style="color:#eff6ff;font-size:14.5px;margin-top:9px;">'
            '&#127959;&#65039; Khách hỏi kỹ thuật KHÔNG phải vì họ hiểu kỹ thuật &mdash; họ đang '
            'lo <b>&#8220;tôi có mất tiền oan không?&#8221;</b>. &#128073; Bấm từng mục ở MENU '
            'BÊN TRÁI để học lần lượt &mdash; mỗi bài có hình mô phỏng, công thức và trắc nghiệm chấm ngay.</div></div>')
        return ('<div class="vd-course">' + hero + radios + '<style>' + rules + '</style>'
                '<div class="vc-layout">'
                '<nav class="vc-side"><div class="vc-sidehead">&#128506;&#65039; Lộ trình học tập</div>'
                + navbtns + '</nav>'
                '<main class="vc-content">' + panels + '</main>'
                '</div></div>')

    def _kttc_tag(self, t):
        return '<div class="vc-tag">' + t + '</div>'

    def _kttc_lessons(self):
        return [
            ('&#129504;', 'MỞ ĐẦU', 'Tư duy + Công thức 5 bước', self._kttc_l_open()),
            ('&#127959;&#65039;', 'CHƯƠNG 1', 'Móng có đảm bảo không?', self._kttc_l_mong()),
            ('&#128230;', 'CHƯƠNG 2', 'Vật tư có bị kém không?', self._kttc_l_vattu()),
            ('&#129521;', 'CHƯƠNG 3', 'Vì sao nhà hay nứt tường?', self._kttc_l_nut()),
            ('&#128167;', 'CHƯƠNG 4', 'Nhà xây xong hay bị thấm?', self._kttc_l_tham()),
            ('&#127959;&#65039;', 'CH 5-6', 'Bê tông & Trần', self._kttc_l_betong_tran()),
            ('&#128736;&#65039;', 'CH 7-8', 'Bảo hành & Tường', self._kttc_l_baohanh_tuong()),
            ('&#127942;', 'TỔNG KẾT', '10 nguyên tắc vàng', self._kttc_l_gold()),
        ]

    # ------------------------------------------------------------------
    #  MỞ ĐẦU
    # ------------------------------------------------------------------
    def _kttc_l_open(self):
        return (
            self._kttc_tag('TƯ DUY NỀN TẢNG')
            + '<h3>Khách hỏi kỹ thuật KHÔNG phải vì họ hiểu kỹ thuật</h3>'
            + _box('info', '<b>Đây là điều mọi nhân viên phải nhớ.</b> Khoảng <b>90% khách</b> '
                   'hỏi kỹ thuật vì họ từng nghe người khác kể, từng xem TikTok / Facebook, '
                   'từng đọc báo, hoặc từng xây nhà bị lỗi &mdash; nên họ <b>SỢ mất tiền</b>.')
            + '<p>Nghĩa là: khách <b>không cần</b> bạn nói kỹ thuật quá sâu. Cái khách thật sự '
            'muốn biết là: <b>&#8220;Người này có đủ chuyên nghiệp để mình yên tâm giao hơn '
            '2 tỷ đồng hay không?&#8221;</b> Câu hỏi kỹ thuật thực chất là câu hỏi: '
            '<b>&#8220;Tôi có mất tiền oan không?&#8221;</b></p>'
            + _box('err', '<b>Vì vậy: KHÔNG tranh luận. KHÔNG phủ nhận khách. KHÔNG nói khách '
                   'sai.</b> Mục tiêu cuối cùng không phải là &#8220;thắng&#8221; cuộc tranh '
                   'luận, mà là giúp khách <b>TIN TƯỞNG</b> công ty có đủ năng lực, quy trình '
                   'và trách nhiệm.')
            + '<h4>&#128273; CÔNG THỨC 5 BƯỚC &mdash; xử lý MỌI câu hỏi khó</h4>'
            + _fig('Sơ đồ công thức 5 bước', _svg_congthuc(),
                   'Áp dụng đúng thứ tự cho mọi câu hỏi kỹ thuật khó của khách.')
            + _order([
                ('ĐỒNG TÌNH với khách', 'Ghi nhận nỗi lo của khách trước &mdash; không phản bác ngay.'),
                ('GIẢI THÍCH nguyên nhân', 'Nói rõ vì sao có hiện tượng đó, một cách dễ hiểu.'),
                ('ĐƯA quy trình công ty', 'Trình bày công ty kiểm soát điều đó bằng quy trình cụ thể nào.'),
                ('CAM KẾT', 'Khẳng định trách nhiệm, bảo hành, dừng thi công nếu cần...'),
                ('KẾT THÚC bằng sự YÊN TÂM', 'Chốt lại để khách cảm thấy an tâm giao công trình.'),
            ])
            + _fml('Mọi câu hỏi khó = <b>Đồng tình &rarr; Nguyên nhân &rarr; Quy trình công ty '
                   '&rarr; Cam kết &rarr; Yên tâm</b>. Biến một câu NGHI NGỜ thành một lợi thế để CHỐT hợp đồng.')
            + _wrong([
                'Nghe khách hỏi là <b>phản bác ngay</b>, cãi tay đôi để chứng minh mình đúng.',
                'Trả lời <b>theo cảm tính / suy đoán</b> (&#8220;chắc ổn&#8221;, &#8220;em nghĩ được&#8221;).',
                'Nói kỹ thuật quá sâu, quá dài &rarr; khách càng rối, càng nghi ngờ.',
                'Chê đơn vị khác thay vì nói về quy trình của công ty mình.'])
            + _quiz('kttc_open',
                    'Khách đặt một câu hỏi kỹ thuật khiến bạn thấy như đang bị nghi ngờ. Bước ĐẦU TIÊN đúng là gì?',
                    [('Phản bác ngay để chứng minh khách hiểu sai', False),
                     ('ĐỒNG TÌNH / ghi nhận nỗi lo của khách trước, rồi mới giải thích', True),
                     ('Nói thật nhiều thuật ngữ kỹ thuật cho khách nể', False),
                     ('Chê các công ty khác làm ẩu để mình nổi bật', False)],
                    'Luôn ĐỒNG TÌNH trước &mdash; đó là bước 1 của công thức 5 bước, tránh tranh luận với khách.'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 1 - MÓNG
    # ------------------------------------------------------------------
    def _kttc_l_mong(self):
        return (
            self._kttc_tag('CHƯƠNG 1 &mdash; MÓNG CÓ ĐẢM BẢO KHÔNG?')
            + '<h3>Móng: khách đang sợ lún, nứt, nghiêng &mdash; và sợ MẤT TIỀN</h3>'
            + '<p>Đây là câu hỏi xuất hiện rất nhiều. Khách lo nhà bị lún, nứt, nghiêng, sau '
            'này phải sửa. Thực chất khách đang hỏi: <b>&#8220;Tôi có mất tiền oan không?&#8221;</b></p>'
            + _box('ok', '<b>NGUYÊN TẮC CHUNG khi khách hỏi &#8220;móng như vậy có đảm bảo '
                   'không?&#8221;:</b> việc ĐẦU TIÊN là <b>KHẲNG ĐỊNH LÀ CÓ</b> &mdash; móng '
                   'trong báo giá đã đảm bảo kết cấu cho công trình. Sau đó mới xử lý theo '
                   'ĐÚNG loại móng ghi trong báo giá của khách. Có <b>3 tình huống</b>: móng '
                   'cọc, móng băng, móng đơn.')
            + _box('warn', '<b>Sợi chỉ đỏ xuyên suốt cả 3 tình huống:</b> nếu <b>đào đất móng '
                   'lên mà gặp đất yếu</b>, không thi công được theo báo giá thì bên em '
                   '<b>cho ÉP CỌC (chuyển móng cọc)</b> &mdash; tuyệt đối không cố làm trên '
                   'nền đất yếu. Câu này khiến khách rất yên tâm vì thấy công ty có trách nhiệm.')
            + _fig('3 tình huống móng: cọc / băng / đơn (mặt cắt)', _svg_mong(),
                   'Móng cọc xuống tận đất tốt; móng băng là dải liền; móng đơn là đế riêng dưới từng cột. '
                   'Cả 3: đào lên gặp đất yếu thì chuyển ép cọc.')
            + '<h4>&#128290; Tình huống 1 &mdash; Báo giá là MÓNG CỌC (phương án tốt nhất)</h4>'
            + _box('ok', 'Trả lời thật <b>CHẮC CHẮN</b>, khẳng định &mdash; không nói &#8220;chắc là ổn&#8221;.')
            + _say('&#8220;Anh chị hoàn toàn yên tâm. Hồ sơ bên em tư vấn cho mình là <b>móng '
                   'cọc</b> &mdash; phương án an toàn nhất hiện nay cho nhà dân dụng. Móng cọc '
                   'truyền toàn bộ tải trọng xuống lớp đất tốt phía dưới nên gần như không bị '
                   'ảnh hưởng bởi lớp đất yếu bên trên. Nhờ vậy sau này mình không phải lo '
                   'lún, nứt kết cấu hay sụt nền. Đây cũng là lý do rất nhiều công trình hiện '
                   'nay ưu tiên móng cọc.&#8221;')
            + '<h4>&#128290; Tình huống 2 &mdash; Báo giá là MÓNG BĂNG</h4>'
            + _box('ok', 'Vẫn <b>KHẲNG ĐỊNH đảm bảo kết cấu</b> trước, rồi nêu cam kết ép cọc '
                   'nếu đất yếu. KHÔNG nói lấp lửng &#8220;chắc là ổn&#8221;.')
            + _say('&#8220;Anh chị yên tâm, <b>móng băng bên em tính là đảm bảo kết cấu</b> cho '
                   'căn nhà của mình. Bên em <b>không bao giờ đánh đổi chất lượng</b>: khi đào '
                   'đất móng lên, nếu đội kỹ thuật thấy <b>nền đất yếu</b> hơn dự kiến thì bên '
                   'em sẽ <b>cho ép cọc (chuyển sang móng cọc)</b> luôn, chứ tuyệt đối không cố '
                   'làm móng băng trên nền đất yếu ạ.&#8221;')
            + '<h4>&#128290; Tình huống 3 &mdash; Báo giá là MÓNG ĐƠN</h4>'
            + _box('ok', 'Cũng <b>KHẲNG ĐỊNH đảm bảo</b>, giải thích theo số tầng, và giữ '
                   'nguyên cam kết ép cọc nếu đào lên gặp đất yếu.')
            + _table(['Trường hợp nhà', 'Cách khẳng định'],
                     [['<b>Nhà 1 tầng</b>', 'Làm móng đơn là <b>quá chắc chắn</b>, anh chị hoàn toàn yên tâm.'],
                      ['<b>Nhà 2 tầng</b>', '<b>Rất nhiều khách</b> bên em vẫn làm móng đơn và đảm bảo tốt.'],
                      ['<b>Đào lên gặp đất yếu, không thi công được</b>', 'Bên em <b>chuyển làm móng cọc (ép cọc)</b> &mdash; không cố làm móng đơn trên đất yếu.']],
                     widths=['40%', '60%'])
            + _say('&#8220;Báo giá của mình là móng đơn ạ. Nhà 1 tầng thì làm móng đơn là <b>quá '
                   'chắc chắn</b>; nhà 2 tầng thì <b>rất nhiều khách</b> bên em cũng làm móng '
                   'đơn và đảm bảo tốt. Trường hợp đào móng lên mà là <b>đất yếu, không thi '
                   'công móng đơn được</b> thì bên em sẽ <b>làm móng cọc</b> cho mình, nên anh '
                   'chị cứ yên tâm ạ.&#8221;')
            + _box('info', 'Khách rất thích câu <b>&#8220;đào lên đất yếu bên em sẽ ép cọc&#8221;</b> '
                   '&mdash; nó thể hiện công ty có trách nhiệm, không cố làm ẩu để tiết kiệm.')
            + _wrong([
                'Nghe khách hỏi là <b>ngập ngừng</b>, nói &#8220;chắc là ổn&#8221;, &#8220;em nghĩ được&#8221; thay vì KHẲNG ĐỊNH là CÓ.',
                'Với móng băng / móng đơn mà <b>quên cam kết ÉP CỌC</b> khi đào lên gặp đất yếu.',
                'Chê móng băng/móng đơn là &#8220;yếu&#8221; &mdash; làm khách hoang mang chính báo giá của họ.',
                'Khẳng định cứng &#8220;đất kiểu gì cũng làm được móng băng/đơn&#8221; (sai &mdash; đất yếu phải ép cọc).'])
            + _fml('Khách hỏi móng có đảm bảo &rarr; <b>KHẲNG ĐỊNH LÀ CÓ trước</b>. Cọc: an '
                   'toàn nhất. Băng: đảm bảo kết cấu. Đơn: 1 tầng quá chắc, 2 tầng nhiều khách '
                   'vẫn làm. Cả 3 &mdash; <b>đào lên gặp ĐẤT YẾU thì ÉP CỌC</b> (chuyển móng cọc).')
            + _quiz('kttc_mong',
                    'Báo giá của khách là MÓNG BĂNG (hoặc MÓNG ĐƠN). Khách hỏi "móng có đảm bảo không?". Trả lời ĐÚNG chuẩn là gì?',
                    [('Ngập ngừng "chắc là ổn ạ", để em hỏi lại kỹ thuật', False),
                     ('Khẳng định LÀ CÓ, đảm bảo kết cấu; nếu đào móng lên gặp đất yếu thì bên em cho ép cọc (chuyển móng cọc)', True),
                     ('Nói móng này hơi yếu, anh chị nên nâng cấp lên móng cọc cho chắc', False),
                     ('Đất kiểu gì cũng làm được móng băng/đơn nên anh chị đừng lo', False)],
                    'Luôn KHẲNG ĐỊNH là CÓ (đảm bảo kết cấu) trước; gặp đất yếu khi đào móng thì ép cọc &mdash; không cố làm trên đất yếu.'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 2 - VẬT TƯ
    # ------------------------------------------------------------------
    def _kttc_l_vattu(self):
        return (
            self._kttc_tag('CHƯƠNG 2 &mdash; VẬT TƯ CÓ BỊ KÉM KHÔNG?')
            + '<h3>Khách nói &#8220;công ty xây nhà toàn dùng vật tư kém&#8221;</h3>'
            + _box('err', '<b>KHÔNG phản bác ngay.</b> Phải ĐỒNG TÌNH trước rồi mới giải thích.')
            + _say('&#8220;Dạ đúng rồi anh. Thực tế trước đây có nhiều công trình xảy ra tình '
                   'trạng vật tư không đúng cam kết.&#8221;')
            + '<h4>Giải thích: xưa và nay khác nhau</h4>'
            + _table(['NGÀY XƯA', 'NGÀY NAY'],
                     [['Chủ nhà tự mua vật tư, tự thuê thợ, tự giám sát &mdash; muốn kiểm soát '
                       'phải tự biết kỹ thuật, định mức, thương hiệu, nghiệm thu (không phải ai cũng làm được).',
                       'Công ty xây trọn gói cạnh tranh nhau bằng <b>chất lượng, uy tín, thương '
                       'hiệu, bảo hành</b> &mdash; làm kém là tự mất khách.']],
                     widths=['50%', '50%'])
            + '<h4>Trả lời chuẩn: vật tư ghi RÕ thương hiệu trong hợp đồng</h4>'
            + _table(['Hạng mục', 'Thương hiệu (ví dụ, theo hợp đồng)'],
                     [['Sơn', '<b>Nippon</b>'],
                      ['Ống nước', '<b>Tiền Phong</b>'],
                      ['Dây điện', '<b>Trần Phú</b>'],
                      ['Thiết bị', 'Theo đúng danh mục hợp đồng']],
                     widths=['30%', '70%'])
            + _box('ok', '<b>Toàn bộ vật tư ghi rõ thương hiệu trong hợp đồng, không ghi chung '
                   'chung.</b> Khi vật tư về công trình sẽ được <b>nghiệm thu đầu vào</b>: nếu '
                   'sai thương hiệu / sai chủng loại / không đúng hợp đồng &mdash; khách có '
                   'quyền yêu cầu <b>dừng thi công, không cho sử dụng, đổi vật tư</b>.')
            + _say('&#8220;Điều quan trọng nhất là công ty luôn mong làm thật tốt công trình '
                   'của mình để sau này anh chị giới thiệu thêm khách. Nếu làm không tốt thì '
                   'chính công ty là đơn vị thiệt hại đầu tiên ạ.&#8221;')
            + _wrong([
                'Phản bác / cãi ngay &#8220;công ty em không bao giờ như thế&#8221; khi khách vừa nói.',
                'Nói vật tư <b>chung chung</b> (&#8220;sơn tốt&#8221;, &#8220;ống xịn&#8221;) mà không nêu THƯƠNG HIỆU cụ thể.',
                'Không nhắc tới <b>nghiệm thu đầu vào</b> và quyền của khách khi vật tư sai.'])
            + _fml('Vật tư = <b>ĐỒNG TÌNH</b> (xưa hay lỗi) &rarr; nay ghi RÕ THƯƠNG HIỆU trong '
                   'HĐ (Nippon / Tiền Phong / Trần Phú) &rarr; <b>NGHIỆM THU ĐẦU VÀO</b>, sai '
                   'là khách được dừng/đổi &rarr; làm kém công ty thiệt đầu tiên.')
            + _quiz('kttc_vattu',
                    'Khách nói: "Công ty xây nhà toàn dùng vật tư kém". Cách mở đầu ĐÚNG là?',
                    [('Phản bác ngay: "Công ty em không bao giờ như vậy đâu ạ"', False),
                     ('ĐỒNG TÌNH ("đúng là trước đây có tình trạng đó"), rồi giải thích vật tư ghi rõ thương hiệu + nghiệm thu đầu vào', True),
                     ('Im lặng cho qua rồi chuyển chủ đề', False),
                     ('Chê các công ty khác dùng vật tư kém hơn', False)],
                    'Đồng tình trước rồi giải thích: vật tư ghi rõ thương hiệu trong HĐ và được nghiệm thu đầu vào.'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 3 - NỨT TƯỜNG
    # ------------------------------------------------------------------
    def _kttc_l_nut(self):
        return (
            self._kttc_tag('CHƯƠNG 3 &mdash; VÌ SAO NHÀ HAY NỨT TƯỜNG?')
            + '<h3>Nứt tường: đồng tình trước, rồi đưa quy trình chống nứt</h3>'
            + _say('&#8220;Đúng rồi anh. Đây là lỗi mà rất nhiều công trình trên thị trường đang gặp phải.&#8221;')
            + '<h4>Nguyên nhân: nứt ở chỗ hai vật liệu giãn nở khác nhau</h4>'
            + _fig('Vị trí nứt &amp; lưới chống nứt', _svg_nut(),
                   'Nứt hay xuất hiện ở tiếp giáp gạch - bê tông; giải pháp là đóng lưới chống nứt phủ các vị trí đó.')
            + '<p>Nứt thường xuất hiện tại: tiếp giáp <b>gạch và cột bê tông</b>, tiếp giáp '
            '<b>dầm</b>, <b>hộp kỹ thuật</b>, đường <b>điện</b>, đường <b>nước</b> &mdash; nơi '
            'vật liệu giãn nở khác nhau.</p>'
            + '<h4>Quy trình công ty (bắt buộc nói)</h4>'
            + _order([
                ('Đóng lưới chống nứt', 'Toàn bộ vị trí tiếp giáp gạch và bê tông.'),
                ('Đóng lưới tại vị trí đi ống điện, ống nước', 'Trước khi tô.'),
                ('Đổ bê tông chân tường mái', 'Hạn chế nứt do co ngót và thời tiết.'),
                ('Thi công đúng kỹ thuật', 'Đúng tỷ lệ vữa và thời gian bảo dưỡng.'),
                ('Giám sát kỹ thuật kiểm tra thường xuyên', 'Phát hiện sai sót là yêu cầu thợ khắc phục ngay.'),
            ])
            + _box('ok', 'Chốt: <b>&#8220;Nhờ vậy công trình bên em hạn chế tối đa hiện tượng '
                   'nứt tường. Phần kết cấu cũng đã được thiết kế phù hợp nên anh chị yên tâm '
                   'dùng lâu dài.&#8221;</b>')
            + _wrong([
                'Khẳng định <b>&#8220;nhà em cam kết KHÔNG BAO GIỜ nứt&#8221;</b> &mdash; hứa quá khả năng.',
                'Phủ nhận khách (&#8220;làm gì có chuyện nứt&#8221;) thay vì đồng tình rồi đưa quy trình.',
                'Không kể được <b>lưới chống nứt</b> và các bước cụ thể &rarr; nghe chung chung, thiếu tin cậy.'])
            + _fml('Nứt tường = ĐỒNG TÌNH &rarr; nguyên nhân (tiếp giáp gạch - bê tông, ống '
                   'điện/nước) &rarr; quy trình: <b>ĐÓNG LƯỚI CHỐNG NỨT</b> + bê tông chân '
                   'tường mái + đúng vữa/bảo dưỡng + giám sát &rarr; hạn chế tối đa.')
            + _quiz('kttc_nut',
                    'Khách hỏi vì sao nhiều nhà bị nứt tường. Điểm cốt lõi trong quy trình chống nứt của công ty là gì?',
                    [('Cam kết chắc chắn nhà sẽ không bao giờ nứt', False),
                     ('Đóng LƯỚI CHỐNG NỨT tại tiếp giáp gạch - bê tông và vị trí ống điện/nước, cộng bê tông chân tường mái', True),
                     ('Xây tường thật dày để khỏi nứt', False),
                     ('Chỉ cần sơn chống nứt lên bề mặt là xong', False)],
                    'Cốt lõi: đóng lưới chống nứt ở tiếp giáp gạch - bê tông và ống điện/nước, đổ bê tông chân tường mái.'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 4 - THẤM
    # ------------------------------------------------------------------
    def _kttc_l_tham(self):
        return (
            self._kttc_tag('CHƯƠNG 4 &mdash; NHÀ XÂY XONG HAY BỊ THẤM?')
            + '<h3>Thấm: lỗi khách SỢ NHẤT &mdash; phải nói quy trình thật chi tiết</h3>'
            + _say('&#8220;Dạ đúng rồi anh. Thực tế rất nhiều khách hàng cũng phản ánh tình trạng này.&#8221;')
            + '<h4>Nguyên nhân thường gặp</h4>'
            + '<p>Không chống thấm, chống thấm sơ sài, <b>không thử nước</b>, thi công ẩu.</p>'
            + _fig('Các lớp chống thấm &amp; ngâm thử nước 7 ngày', _svg_tham(),
                   'Chống thấm Sika + màng PE, ngâm nước 7 ngày; không đạt thì KHÔNG ốp lát, KHÔNG bàn giao.')
            + '<h4>Quy trình công ty</h4>'
            + _table(['Chống thấm ở đâu', 'Bằng gì'],
                     [['Mái, WC, ban công, sân thượng', '<b>Chống thấm Sika</b> + sử dụng <b>màng PE</b>']],
                     widths=['50%', '50%'])
            + _order([
                ('Chống thấm đầy đủ các vị trí', 'Mái, WC, ban công, sân thượng &mdash; bằng Sika + màng PE.'),
                ('NGÂM THỬ NƯỚC 7 NGÀY', 'Sau khi chống thấm, ngâm nước liên tục 7 ngày để kiểm tra.'),
                ('Không đạt &rarr; KHÔNG ốp lát', 'Chưa đạt tuyệt đối không ốp lát, không bàn giao.'),
            ])
            + _box('info', '<b>Lý do công ty làm kỹ (câu cực thuyết phục):</b> nếu chống thấm '
                   'không tốt thì sau này <b>chính công ty phải chịu chi phí bảo hành</b> '
                   '&mdash; muốn sửa phải đục nền, tháo gạch, chống thấm lại, ốp lát lại: vừa '
                   'tốn thời gian, tốn chi phí, lại ảnh hưởng sinh hoạt của khách. Nên ngay từ '
                   'đầu bên em làm rất kỹ để tránh phát sinh về sau.')
            + _wrong([
                'Chỉ nói &#8220;bên em chống thấm kỹ lắm&#8221; mà <b>không kể quy trình</b> (Sika, màng PE, ngâm 7 ngày).',
                'Quên nhấn mạnh <b>ngâm thử nước 7 ngày</b> &mdash; đây là điểm khách tin nhất.',
                'Hứa &#8220;bảo đảm 100% không bao giờ thấm&#8221; thay vì nói quy trình + lý do làm kỹ.'])
            + _fml('Thấm = ĐỒNG TÌNH &rarr; nguyên nhân (không thử nước, thi công ẩu) &rarr; '
                   'quy trình: <b>Sika + màng PE</b>, <b>NGÂM NƯỚC 7 NGÀY</b>, không đạt KHÔNG '
                   'ốp lát/bàn giao &rarr; lý do: thấm thì công ty chịu chi phí bảo hành.')
            + _quiz('kttc_tham',
                    'Khách lo nhà xây xong bị thấm. Đâu là bước tạo niềm tin mạnh nhất trong quy trình chống thấm?',
                    [('Hứa bảo đảm 100% không bao giờ thấm', False),
                     ('NGÂM THỬ NƯỚC 7 NGÀY sau chống thấm; không đạt thì không ốp lát, không bàn giao', True),
                     ('Sơn thêm một lớp chống thấm cho chắc', False),
                     ('Chờ khách phản ánh thấm rồi mới xử lý bảo hành', False)],
                    'Điểm tin nhất: chống thấm Sika + màng PE rồi NGÂM NƯỚC 7 NGÀY; chưa đạt thì không ốp lát/bàn giao.'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 5 + 6 - BÊ TÔNG & TRẦN
    # ------------------------------------------------------------------
    def _kttc_l_betong_tran(self):
        return (
            self._kttc_tag('CHƯƠNG 5 - 6 &mdash; BÊ TÔNG & TRẦN')
            + '<h3>Bê tông có tốt không? Trần có trát không?</h3>'
            + '<h4>&#127959;&#65039; Chương 5 &mdash; Bê tông mác 350</h4>'
            + _fig('Bê tông thương phẩm mác 350', _svg_betong(),
                   'Lấy mẫu đúc kiểm tra cường độ; bê tông từ trạm trộn, có hóa đơn chứng từ.')
            + _say('&#8220;Bên em dùng <b>bê tông thương phẩm mác 350</b> &mdash; cấp độ rất '
                   'phổ biến và phù hợp cho nhà ở dân dụng, đáp ứng yêu cầu thiết kế kết cấu. '
                   'Khi đổ, bên em <b>lấy mẫu đúc để kiểm tra cường độ</b> theo quy định, sau '
                   'này cần kiểm định thì có mẫu đối chứng. Bê tông từ trạm trộn, có hóa đơn '
                   'chứng từ, kiểm soát chất lượng trước khi vào công trình. Anh chị hoàn toàn '
                   'yên tâm về chất lượng bê tông ạ.&#8221;')
            + _box('warn', '<b>LƯU Ý quan trọng:</b> chỉ khẳng định &#8220;mác 350 là loại '
                   '<b>cao dùng cho nhà ở dân dụng</b>&#8221; hoặc &#8220;<b>phù hợp nhà dân '
                   'dụng</b>&#8221;. <b>KHÔNG</b> nói đây là &#8220;mác cao nhất trong xây '
                   'dựng&#8221; &mdash; thực tế còn các cấp mác cao hơn dùng cho công trình đặc biệt.')
            + '<h4>&#127968; Chương 6 &mdash; Trần có trát không?</h4>'
            + _say('&#8220;Bên em <b>không trát trần bê tông</b>, thay vào đó thi công hệ '
                   '<b>trần thạch cao</b> hoàn thiện. Không trát trần giúp <b>giảm nguy cơ '
                   'bong tróc lớp vữa</b>, bề mặt phẳng hơn và dễ bố trí hệ thống điện, đèn, '
                   'điều hòa. Nếu anh chị chọn phương án không làm trần thạch cao thì phần '
                   'trần bê tông sẽ được xử lý hoàn thiện theo đúng thiết kế và phương án đã '
                   'thống nhất ạ.&#8221;')
            + _box('ok', 'Ý chính: <b>không trát trần = tránh bong tróc vữa</b>, phẳng đẹp hơn, '
                   'dễ đi điện/đèn/điều hòa; dùng <b>trần thạch cao</b> hoàn thiện.')
            + _wrong([
                'Nói bê tông mác 350 là <b>&#8220;mác cao nhất&#8221;</b> &rarr; khách rành sẽ bắt lỗi ngay.',
                'Quên nhắc <b>lấy mẫu đúc kiểm tra cường độ</b> và bê tông <b>có hóa đơn chứng từ</b>.',
                'Nói &#8220;trần không trát cho rẻ&#8221; &mdash; sai bản chất; lý do đúng là <b>tránh bong tróc vữa</b>, dễ đi kỹ thuật.'])
            + _fml('Bê tông = <b>mác 350</b> (cao/phù hợp nhà dân dụng, KHÔNG nói cao nhất) + '
                   'lấy mẫu đúc kiểm cường độ + có hóa đơn. Trần = <b>không trát</b>, dùng '
                   '<b>thạch cao</b> &rarr; tránh bong tróc vữa, dễ đi điện/đèn/điều hòa.')
            + _quiz('kttc_betong',
                    'Khi tư vấn về bê tông mác 350, câu nào TUYỆT ĐỐI không nên nói?',
                    [('Mác 350 phù hợp và là loại cao dùng cho nhà ở dân dụng', False),
                     ('Đây là mác CAO NHẤT trong xây dựng', True),
                     ('Bên em lấy mẫu đúc để kiểm tra cường độ theo quy định', False),
                     ('Bê tông từ trạm trộn, có hóa đơn chứng từ', False)],
                    'KHÔNG nói mác 350 là "cao nhất" &mdash; còn có mác cao hơn cho công trình đặc biệt; chỉ nói "cao/phù hợp nhà dân dụng".'))

    # ------------------------------------------------------------------
    #  CHƯƠNG 7 + 8 - BẢO HÀNH & TƯỜNG
    # ------------------------------------------------------------------
    def _kttc_l_baohanh_tuong(self):
        return (
            self._kttc_tag('CHƯƠNG 7 - 8 &mdash; BẢO HÀNH & TƯỜNG')
            + '<h3>Bảo hành bao lâu? Tường xây bao nhiêu?</h3>'
            + '<h4>&#128736;&#65039; Chương 7 &mdash; Bảo hành (trả lời RÕ RÀNG)</h4>'
            + _fig('Thời gian bảo hành theo hạng mục', _svg_baohanh(),
                   'Kết cấu 5 năm; thiết bị vệ sinh/cửa/gạch ốp lát 2 năm; thiết bị điện (bóng đèn) 1 năm.')
            + _table(['Hạng mục', 'Thời gian bảo hành'],
                     [['<b>Kết cấu</b>', '<b>05 năm</b>'],
                      ['Thiết bị vệ sinh, cửa, gạch ốp lát', '<b>02 năm</b>'],
                      ['Thiết bị điện (bóng đèn, bóng điện)', '<b>01 năm</b>']],
                     widths=['60%', '40%'])
            + _say('&#8220;Trong thời gian bảo hành, nếu có vấn đề anh chị chỉ cần báo trước '
                   'khoảng <b>1&ndash;2 ngày</b>, bên em sắp xếp kỹ thuật đến kiểm tra và xử lý '
                   'theo đúng cam kết bảo hành của hợp đồng ạ.&#8221;')
            + '<h4>&#129521; Chương 8 &mdash; Tường xây bao nhiêu?</h4>'
            + _fig('Tường bao 200mm &amp; tường ngăn 100mm', _svg_tuong(),
                   'Tường bao (bao quanh nhà) dày 200mm; tường ngăn phòng dày 100mm.')
            + _say('&#8220;Bên em thi công <b>tường bao 200mm</b> (thường gọi tường 20), các '
                   '<b>tường ngăn phòng 100mm</b> (tường 10). Đây là tiêu chuẩn công ty áp '
                   'dụng cho nhà ở dân dụng để đảm bảo <b>khả năng chịu lực, cách âm</b> và '
                   '<b>tối ưu diện tích sử dụng</b> ạ.&#8221;')
            + _box('ok', 'Nhớ nhanh: <b>tường BAO 200</b> (tường 20) &mdash; <b>tường NGĂN 100</b> (tường 10).')
            + _wrong([
                'Trả lời bảo hành <b>mơ hồ</b> (&#8220;bảo hành lâu dài&#8221;) thay vì nói rõ 5 / 2 / 1 năm theo hạng mục.',
                'Nhầm lẫn <b>tường bao</b> và <b>tường ngăn</b> (nói ngược 100 / 200).',
                'Không giải thích lý do dùng tường 200/100 (chịu lực, cách âm, tối ưu diện tích).'])
            + _fml('Bảo hành: <b>kết cấu 5 năm</b> / thiết bị vệ sinh - cửa - gạch <b>2 năm</b> '
                   '/ điện <b>1 năm</b>; báo trước 1&ndash;2 ngày. Tường: <b>bao 200</b> (tường '
                   '20), <b>ngăn 100</b> (tường 10) &rarr; chịu lực + cách âm + tối ưu diện tích.')
            + _quiz('kttc_bh',
                    'Khách hỏi bảo hành bao lâu. Trả lời nào ĐÚNG chuẩn công ty?',
                    [('Bảo hành trọn đời toàn bộ công trình', False),
                     ('Kết cấu 5 năm; thiết bị vệ sinh/cửa/gạch ốp lát 2 năm; thiết bị điện 1 năm', True),
                     ('Tất cả hạng mục đều bảo hành 5 năm như nhau', False),
                     ('Bảo hành lâu dài, cụ thể thì để em hỏi lại', False)],
                    'Đúng chuẩn: kết cấu 5 năm - thiết bị vệ sinh/cửa/gạch 2 năm - thiết bị điện 1 năm.'))

    # ------------------------------------------------------------------
    #  TỔNG KẾT - 10 NGUYÊN TẮC VÀNG
    # ------------------------------------------------------------------
    def _kttc_l_gold(self):
        return (
            self._kttc_tag('&#127942; TỔNG HỢP KIẾN THỨC')
            + '<h3>10 nguyên tắc vàng khi trả lời câu hỏi kỹ thuật</h3>'
            + '<ol>'
            '<li><b>Không tranh luận</b> với khách hàng.</li>'
            '<li>Luôn <b>đồng tình</b> trước khi giải thích.</li>'
            '<li>Không chê đơn vị khác &mdash; chỉ phân tích sự khác biệt trong <b>quy trình của công ty</b>.</li>'
            '<li>Không trả lời khi chưa biết; vượt chuyên môn thì <b>xin phép xác nhận với bộ phận kỹ thuật</b>.</li>'
            '<li>Không hứa những điều <b>ngoài hợp đồng</b> hoặc ngoài khả năng thực hiện.</li>'
            '<li>Luôn dựa trên <b>quy trình, tiêu chuẩn, cam kết</b> của công ty để trả lời.</li>'
            '<li>Biến mỗi câu hỏi thành <b>cơ hội chứng minh sự chuyên nghiệp</b> của doanh nghiệp.</li>'
            '<li>Kết thúc mỗi câu trả lời bằng việc <b>tạo sự yên tâm</b> cho khách.</li>'
            '<li><b>Ghi nhận câu hỏi mới</b> của khách để bổ sung vào kho dữ liệu đào tạo.</li>'
            '<li>Mục tiêu cuối cùng không phải &#8220;thắng&#8221; tranh luận, mà giúp khách '
            '<b>TIN TƯỞNG</b> công ty đủ năng lực, quy trình và trách nhiệm đồng hành.</li>'
            '</ol>'
            + '<h4>&#128221; Bảng công thức thuộc lòng (theo từng câu hỏi khó)</h4>'
            + _table(['Câu hỏi khó', 'Cốt lõi trả lời'],
                     [['<b>Công thức chung</b>', 'Đồng tình &rarr; Nguyên nhân &rarr; Quy trình công ty &rarr; Cam kết &rarr; Yên tâm.'],
                      ['<b>Móng có đảm bảo?</b>', 'Cọc: khẳng định chắc (an toàn nhất). Băng: tốt nếu đất cứng; gặp đất yếu &rarr; DỪNG thi công, chuyển móng cọc.'],
                      ['<b>Vật tư kém?</b>', 'Đồng tình (xưa hay lỗi) &rarr; nay ghi RÕ thương hiệu trong HĐ (Nippon/Tiền Phong/Trần Phú) + NGHIỆM THU ĐẦU VÀO.'],
                      ['<b>Nứt tường?</b>', 'Nguyên nhân tiếp giáp gạch - bê tông &rarr; ĐÓNG LƯỚI CHỐNG NỨT + bê tông chân tường mái + giám sát.'],
                      ['<b>Thấm?</b>', 'Sika + màng PE, NGÂM NƯỚC 7 NGÀY; không đạt không ốp lát/bàn giao; thấm thì công ty chịu chi phí bảo hành.'],
                      ['<b>Bê tông?</b>', 'Mác 350 (cao/phù hợp nhà dân dụng, KHÔNG nói cao nhất) + lấy mẫu đúc kiểm cường độ + có hóa đơn.'],
                      ['<b>Trần có trát?</b>', 'Không trát trần &rarr; dùng thạch cao; tránh bong tróc vữa, dễ đi điện/đèn/điều hòa.'],
                      ['<b>Bảo hành?</b>', 'Kết cấu 5 năm / thiết bị vệ sinh - cửa - gạch 2 năm / điện 1 năm; báo trước 1&ndash;2 ngày.'],
                      ['<b>Tường xây bao nhiêu?</b>', 'Tường bao 200 (tường 20), tường ngăn 100 (tường 10) &rarr; chịu lực + cách âm + tối ưu diện tích.']],
                     widths=['24%', '76%'])
            + _box('warn', 'Nguyên tắc bao trùm: <b>không &#8220;thắng&#8221; khách bằng tranh '
                   'luận</b> &mdash; thắng bằng cách khiến khách TIN. Mỗi câu hỏi khó là một '
                   'cơ hội chứng minh công ty chuyên nghiệp và có trách nhiệm.')
            + _quiz('kttc_gold',
                    'Đâu là MỤC TIÊU CUỐI CÙNG khi trả lời câu hỏi kỹ thuật của khách?',
                    [('Thắng khách trong cuộc tranh luận để chứng minh mình giỏi', False),
                     ('Giúp khách TIN TƯỞNG công ty đủ năng lực, quy trình và trách nhiệm &mdash; biến câu nghi ngờ thành lợi thế chốt hợp đồng', True),
                     ('Trả lời càng nhiều thuật ngữ kỹ thuật càng tốt', False),
                     ('Nói cho xong để chuyển sang chủ đề giá', False)],
                    'Mục tiêu là NIỀM TIN, không phải thắng tranh luận &mdash; biến câu hỏi khó thành lợi thế để chốt hợp đồng.'))

    # ==================================================================
    #  20 CÂU HỎI TRẮC NGHIỆM (bài THI chấm điểm)
    # ==================================================================
    def _kttc_questions(self):
        T, F = True, False
        return [
            ('Vì sao 90% khách hàng đặt câu hỏi kỹ thuật khi tư vấn xây nhà?',
             [('Vì họ SỢ mất tiền / mất tiền oan, không phải vì họ hiểu sâu kỹ thuật', T),
              ('Vì họ là kỹ sư xây dựng muốn kiểm tra', F),
              ('Vì họ muốn tự thi công công trình', F),
              ('Vì họ không quan tâm đến giá', F)]),

            ('Công thức 5 bước xử lý câu hỏi khó theo đúng thứ tự là gì?',
             [('Đồng tình → Giải thích nguyên nhân → Đưa quy trình công ty → Cam kết → Kết thúc bằng sự yên tâm', T),
              ('Phản bác → Chứng minh khách sai → Báo giá → Chốt', F),
              ('Nguyên nhân → Tranh luận → Cam kết → Đồng tình', F),
              ('Cam kết → Yên tâm → Nguyên nhân → Đồng tình', F)]),

            ('Bước ĐẦU TIÊN khi khách đặt một câu hỏi kỹ thuật gây nghi ngờ là gì?',
             [('Đồng tình / ghi nhận nỗi lo của khách trước', T),
              ('Phản bác ngay để bảo vệ công ty', F),
              ('Nói thật nhiều thuật ngữ kỹ thuật', F),
              ('Chuyển sang nói về giá cho nhanh', F)]),

            ('Báo giá là MÓNG CỌC, khách hỏi móng có đảm bảo không. Nên trả lời thế nào?',
             [('Khẳng định chắc chắn: móng cọc là phương án an toàn nhất, truyền tải xuống đất tốt nên hết lo lún nứt', T),
              ('Nói "chắc là ổn" cho khách yên tâm', F),
              ('Bảo để em hỏi lại kỹ thuật đã', F),
              ('Nói móng nào cũng như nhau', F)]),

            ('Báo giá là MÓNG BĂNG. Câu trả lời nào là SAI?',
             [('Móng băng lúc nào cũng tốt, không cần lo gì cả', T),
              ('Móng băng đảm bảo nếu nền đất cứng, đất liền thổ', F),
              ('Gặp đất yếu bên em sẽ dừng thi công, chuyển sang móng cọc', F),
              ('Bên em không đánh đổi chất lượng để tiết kiệm chi phí', F)]),

            ('Khi làm móng băng mà đào móng phát hiện nền đất yếu hơn dự kiến, công ty làm gì?',
             [('Lập tức dừng thi công, kiểm tra lại địa chất, cần thì chuyển sang móng cọc', T),
              ('Cứ làm tiếp móng băng cho tiết kiệm chi phí', F),
              ('Giấu khách và làm nhanh cho xong', F),
              ('Bỏ công trình không làm nữa', F)]),

            ('Khách nói "công ty xây nhà toàn dùng vật tư kém". Cách mở đầu ĐÚNG là?',
             [('Đồng tình ("trước đây đúng là có tình trạng đó") rồi mới giải thích', T),
              ('Phản bác ngay "công ty em không bao giờ như vậy"', F),
              ('Im lặng chuyển chủ đề', F),
              ('Chê các công ty khác dùng vật tư kém hơn', F)]),

            ('Điểm mấu chốt chứng minh vật tư đúng cam kết là gì?',
             [('Vật tư ghi RÕ thương hiệu trong hợp đồng + NGHIỆM THU ĐẦU VÀO, sai thì khách được dừng/đổi', T),
              ('Nói chung chung là "vật tư tốt, xịn"', F),
              ('Cho khách tự đi mua vật tư', F),
              ('Không cần ghi thương hiệu trong hợp đồng', F)]),

            ('Theo ví dụ trong khóa học, ống nước và dây điện dùng thương hiệu nào?',
             [('Ống nước Tiền Phong, dây điện Trần Phú', T),
              ('Ống nước Trần Phú, dây điện Nippon', F),
              ('Ống nước Nippon, dây điện Tiền Phong', F),
              ('Loại nào cũng được, không ghi cụ thể', F)]),

            ('Nứt tường thường xuất hiện ở đâu và giải pháp chính là gì?',
             [('Ở tiếp giáp gạch - bê tông và vị trí ống điện/nước; giải pháp: đóng LƯỚI CHỐNG NỨT', T),
              ('Ở giữa tường; giải pháp: xây tường thật dày', F),
              ('Ở nền nhà; giải pháp: lát thêm gạch', F),
              ('Không có cách nào phòng nứt', F)]),

            ('Ngoài đóng lưới chống nứt, bước nào giúp hạn chế nứt do co ngót và thời tiết?',
             [('Đổ bê tông chân tường mái', T),
              ('Sơn thật nhiều lớp lên tường', F),
              ('Không tô vữa lên tường', F),
              ('Xây tường bằng gạch không nung', F)]),

            ('Thấm là lỗi khách sợ nhất. Bước tạo niềm tin mạnh nhất trong quy trình chống thấm là?',
             [('Ngâm thử nước 7 ngày; không đạt thì KHÔNG ốp lát, KHÔNG bàn giao', T),
              ('Hứa bảo đảm 100% không bao giờ thấm', F),
              ('Sơn thêm một lớp chống thấm', F),
              ('Chờ khách phản ánh rồi mới xử lý', F)]),

            ('Công ty dùng vật liệu gì để chống thấm mái, WC, ban công, sân thượng?',
             [('Chống thấm Sika + sử dụng màng PE', T),
              ('Chỉ quét xi măng nguyên chất', F),
              ('Dán giấy dầu', F),
              ('Không cần vật liệu chống thấm chuyên dụng', F)]),

            ('Lý do thuyết phục vì sao công ty làm chống thấm rất kỹ ngay từ đầu?',
             [('Nếu thấm thì chính công ty phải chịu chi phí bảo hành: đục nền, tháo gạch, làm lại &mdash; rất tốn kém', T),
              ('Vì luật bắt buộc phải ngâm nước', F),
              ('Vì khách trả thêm tiền cho việc chống thấm', F),
              ('Vì để kéo dài thời gian thi công', F)]),

            ('Công ty dùng bê tông mác bao nhiêu cho nhà ở dân dụng?',
             [('Bê tông thương phẩm mác 350', T),
              ('Bê tông mác 100', F),
              ('Bê tông trộn tay không cần mác', F),
              ('Bê tông mác 600', F)]),

            ('Khi nói về bê tông mác 350, câu nào TUYỆT ĐỐI KHÔNG nên nói?',
             [('Đây là mác CAO NHẤT trong xây dựng', T),
              ('Mác 350 phù hợp, là loại cao dùng cho nhà ở dân dụng', F),
              ('Bên em lấy mẫu đúc kiểm tra cường độ theo quy định', F),
              ('Bê tông từ trạm trộn, có hóa đơn chứng từ', F)]),

            ('Vì sao công ty KHÔNG trát trần bê tông mà làm trần thạch cao?',
             [('Giảm nguy cơ bong tróc lớp vữa, bề mặt phẳng hơn, dễ bố trí điện/đèn/điều hòa', T),
              ('Vì thạch cao rẻ hơn nên làm cho tiết kiệm', F),
              ('Vì bê tông không thể trát được', F),
              ('Vì khách yêu cầu bắt buộc', F)]),

            ('Thời gian bảo hành đúng chuẩn công ty cho từng hạng mục là gì?',
             [('Kết cấu 5 năm; thiết bị vệ sinh/cửa/gạch ốp lát 2 năm; thiết bị điện 1 năm', T),
              ('Tất cả 5 năm như nhau', F),
              ('Kết cấu 1 năm; thiết bị 5 năm', F),
              ('Bảo hành trọn đời mọi hạng mục', F)]),

            ('Tường bao và tường ngăn phòng của công ty dày bao nhiêu?',
             [('Tường bao 200mm (tường 20); tường ngăn 100mm (tường 10)', T),
              ('Tường bao 100mm; tường ngăn 200mm', F),
              ('Tất cả tường đều 100mm', F),
              ('Tất cả tường đều 300mm', F)]),

            ('Mục tiêu cuối cùng khi trả lời câu hỏi kỹ thuật của khách là gì?',
             [('Giúp khách TIN TƯỞNG công ty đủ năng lực, quy trình, trách nhiệm &mdash; biến câu nghi ngờ thành lợi thế chốt hợp đồng', T),
              ('Thắng khách trong cuộc tranh luận', F),
              ('Khoe càng nhiều thuật ngữ kỹ thuật càng tốt', F),
              ('Trả lời cho xong để chuyển sang nói giá', F)]),
        ]
