/** @odoo-module **/
/**
 * HOVER trên "Thông tin tư vấn" → hiện inline panel khai thác ngay tại
 * vị trí của panel VẤN ĐỀ (bên phải form), KHÔNG cần popup overlay/click.
 * Mouse rời button + panel → ẩn, panel VẤN ĐỀ hiện lại.
 *
 * Cách triển khai:
 *  - Listen mouseenter trên .o_vd_open_intake_btn_main → add class
 *    .vd-intake-hover-active vào <html> + reposition .o_vd_intake_popup_overlay
 *    về rect của .o_vd_layout_right.
 *  - Mouseleave button → start 200ms close timer.
 *  - Mouseenter panel → cancel timer (cho phép user di chuột vào panel).
 *  - Mouseleave panel → start close timer.
 *  - Window resize/scroll → reposition.
 */

const HTML = document.documentElement;
const HOVER_CLS = "vd-intake-hover-active";
const PINNED_CLS = "vd-intake-pinned";
const CLOSE_DELAY = 200;

let _closeTimer = null;
let _scrollHandler = null;
let _resizeHandler = null;

function _findRightPanel() {
    return document.querySelector(".o_vd_layout_right");
}
function _findOverlay() {
    return document.querySelector(".o_vd_intake_popup_overlay");
}
function _findPanel() {
    return document.querySelector(".o_vd_intake_popup_panel");
}

function _positionOverlay() {
    const right = _findRightPanel();
    const overlay = _findOverlay();
    if (!right || !overlay) return;
    const r = right.getBoundingClientRect();
    overlay.style.setProperty("--vd-hover-top",    r.top + "px");
    overlay.style.setProperty("--vd-hover-left",   r.left + "px");
    overlay.style.setProperty("--vd-hover-width",  r.width + "px");
    overlay.style.setProperty("--vd-hover-height", Math.max(r.height, window.innerHeight - r.top - 16) + "px");
}

function _openHover() {
    if (_closeTimer) {
        clearTimeout(_closeTimer);
        _closeTimer = null;
    }
    HTML.classList.add(HOVER_CLS);
    _positionOverlay();
    if (!_scrollHandler) {
        _scrollHandler = _positionOverlay;
        _resizeHandler = _positionOverlay;
        window.addEventListener("scroll", _scrollHandler, true);
        window.addEventListener("resize", _resizeHandler);
    }
}

function _scheduleClose() {
    // Pinned mode (đã click button) → KHÔNG auto-close. Chỉ đóng khi click X.
    if (HTML.classList.contains(PINNED_CLS)) return;
    if (_closeTimer) clearTimeout(_closeTimer);
    _closeTimer = setTimeout(() => {
        HTML.classList.remove(HOVER_CLS);
        _closeTimer = null;
        _teardownListeners();
    }, CLOSE_DELAY);
}

function _teardownListeners() {
    if (_scrollHandler) {
        window.removeEventListener("scroll", _scrollHandler, true);
        window.removeEventListener("resize", _resizeHandler);
        _scrollHandler = null;
        _resizeHandler = null;
    }
}

function _cancelClose() {
    if (_closeTimer) {
        clearTimeout(_closeTimer);
        _closeTimer = null;
    }
}

document.addEventListener("mouseenter", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    // Hover lên button "Thông tin tư vấn" → mở
    if (target.closest(".o_vd_open_intake_btn_main")) {
        _openHover();
        return;
    }
    // Hover vào panel khi đang mở → cancel close timer
    if (HTML.classList.contains(HOVER_CLS) && target.closest(".o_vd_intake_popup_panel")) {
        _cancelClose();
    }
}, true);

document.addEventListener("mouseleave", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    if (target.closest(".o_vd_open_intake_btn_main")) {
        _scheduleClose();
        return;
    }
    if (HTML.classList.contains(HOVER_CLS) && target.closest(".o_vd_intake_popup_panel")) {
        _scheduleClose();
    }
}, true);

// User click nút "Thông tin tư vấn" → PIN inline mode (persistent, không auto-close).
// Server action vẫn fire (set vd_intake_open=True) để form fields bind data,
// nhưng popup render với inline positioning thay vì fixed overlay.
// Click lại button → unpin. Click X close → unpin + server đóng popup.
document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;

    // Click X close trong popup → unpin
    if (target.closest(".o_vd_popup_close_btn")) {
        HTML.classList.remove(PINNED_CLS);
        HTML.classList.remove(HOVER_CLS);
        if (_closeTimer) {
            clearTimeout(_closeTimer);
            _closeTimer = null;
        }
        _teardownListeners();
        return;
    }

    // Click button "Thông tin tư vấn" → toggle pinned mode
    if (target.closest(".o_vd_open_intake_btn_main")) {
        if (HTML.classList.contains(PINNED_CLS)) {
            HTML.classList.remove(PINNED_CLS);
            HTML.classList.remove(HOVER_CLS);
            _teardownListeners();
        } else {
            HTML.classList.add(PINNED_CLS);
            _openHover();
        }
    }
}, true);
