/** @odoo-module **/
/**
 * HOVER 2 nút "Lịch sử cuộc gọi" (panel Thông tin tư vấn + panel Vấn đề) →
 * bung panel chứa 2 bảng (TRÊN = sau báo giá, DƯỚI = trước báo giá).
 *
 * Vì sao portal ra <body> thay vì CSS :hover thuần:
 *  - Nút ở panel Vấn đề nằm trong .o_vd_pq_call_report (overflow-x:auto) →
 *    dropdown absolute sẽ bị CẮT. Portal ra body thoát clip.
 *  - Form bị zoom 0.7; panel ở body render full-size (zoom=1) → dễ đọc.
 *    getBoundingClientRect() trả toạ độ màn hình thật nên position:fixed khớp.
 *
 * Hover-only: KHÔNG click, KHÔNG ghim. Rời chuột → đóng (grace để di vào panel).
 */

const OPEN_DELAY = 160;   // ms — chống accidental hover
const CLOSE_DELAY = 220;  // ms — grace di chuột từ nút → panel
const VIS_CLS = "vd-callhist-open";
const MARGIN = 8;

let _openTimer = null;
let _closeTimer = null;
let _panel = null;          // panel đang mở (đã portal ra body)
let _origParent = null;     // parent gốc để trả về
let _origNext = null;       // sibling gốc để insertBefore

function _cancelOpen() {
    if (_openTimer) { clearTimeout(_openTimer); _openTimer = null; }
}
function _cancelClose() {
    if (_closeTimer) { clearTimeout(_closeTimer); _closeTimer = null; }
}

function _close() {
    if (!_panel) return;
    _panel.classList.remove(VIS_CLS);
    _panel.style.left = "";
    _panel.style.top = "";
    try {
        if (_origNext && _origNext.parentElement === _origParent) {
            _origParent.insertBefore(_panel, _origNext);
        } else if (_origParent) {
            _origParent.appendChild(_panel);
        }
    } catch (_e) { /* parent có thể đã unmount khi đổi form — bỏ qua */ }
    _panel = _origParent = _origNext = null;
}

function _position(panel, trigger) {
    const r = trigger.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;
    const pw = Math.min(panel.offsetWidth || 680, vw - 2 * MARGIN);
    const ph = panel.offsetHeight || 320;

    // X: căn mép trái nút; nếu tràn phải thì đẩy sang trái cho vừa.
    let left = r.left;
    if (left + pw > vw - MARGIN) left = Math.max(MARGIN, vw - MARGIN - pw);

    // Y: dưới nút; nếu không đủ chỗ dưới mà phía trên đủ → mở lên trên.
    let top = r.bottom + 6;
    if (top + ph > vh - MARGIN && (r.top - 6 - ph) > MARGIN) {
        top = r.top - 6 - ph;
    }

    panel.style.left = Math.round(left) + "px";
    panel.style.top = Math.round(top) + "px";
}

function _open(trigger) {
    const wrap = trigger.closest(".o_vd_callhist_wrap");
    const panel = wrap && wrap.querySelector(".o_vd_callhist_panel");
    if (!panel) return;
    if (_panel === panel) { _cancelClose(); return; }
    if (_panel) _close();           // đóng panel khác đang mở

    _origParent = panel.parentElement;
    _origNext = panel.nextElementSibling;
    _panel = panel;
    document.body.appendChild(panel);
    panel.classList.add(VIS_CLS);   // CSS: position:fixed + display:block
    _position(panel, trigger);
}

// Mouseenter nút → schedule open; mouseenter panel → cancel close.
document.addEventListener("mouseenter", (ev) => {
    const t = ev.target;
    if (!(t instanceof Element)) return;
    const trig = t.closest(".o_vd_callhist_trigger");
    if (trig) {
        _cancelClose();
        _cancelOpen();
        _openTimer = setTimeout(() => { _openTimer = null; _open(trig); }, OPEN_DELAY);
        return;
    }
    if (_panel && t.closest(".o_vd_callhist_panel") === _panel) {
        _cancelClose();
    }
}, true);

// Mouseleave nút hoặc panel → schedule close.
document.addEventListener("mouseleave", (ev) => {
    const t = ev.target;
    if (!(t instanceof Element)) return;
    const leftTrig = !!t.closest(".o_vd_callhist_trigger");
    const leftPanel = _panel && t.closest(".o_vd_callhist_panel") === _panel;
    if (leftTrig || leftPanel) {
        _cancelOpen();
        _cancelClose();
        _closeTimer = setTimeout(() => { _closeTimer = null; _close(); }, CLOSE_DELAY);
    }
}, true);
