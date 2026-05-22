/** @odoo-module **/
/**
 * HOVER trên "Thông tin tư vấn" → hiện inline panel khai thác ngay tại
 * vị trí của panel VẤN ĐỀ (bên phải form), KHÔNG cần popup overlay/click.
 * Click → pin mode (persistent, không auto-close).
 *
 * v2 — fix flicker:
 *  - HOVER_OPEN_DELAY 250ms: chỉ mở khi chuột thực sự stay trên button.
 *  - BỎ scroll listener (gây firing liên tục, position nhảy).
 *  - ResizeObserver thay cho resize event.
 *  - Position chỉ tính 1 lần khi mở; KHÔNG update giữa hover.
 *  - Cancel pending timer khi mouseleave để không trigger orphan.
 */

const HTML = document.documentElement;
const HOVER_CLS = "vd-intake-hover-active";
const PINNED_CLS = "vd-intake-pinned";
const HOVER_OPEN_DELAY = 250;   // ms — chống accidental hover
const CLOSE_DELAY = 200;        // ms — grace di chuột từ button → panel

let _openTimer = null;
let _closeTimer = null;
let _resizeObserver = null;

function _findRightPanel() {
    return document.querySelector(".o_vd_layout_right");
}
function _findOverlay() {
    return document.querySelector(".o_vd_intake_popup_overlay");
}

function _positionOverlay() {
    const right = _findRightPanel();
    const overlay = _findOverlay();
    if (!right || !overlay) return;
    const r = right.getBoundingClientRect();
    // Sanity check — nếu rect 0×0 (panel chưa render) thì bỏ qua
    if (r.width < 50 || r.height < 50) return;
    overlay.style.setProperty("--vd-hover-top",    Math.max(0, r.top) + "px");
    overlay.style.setProperty("--vd-hover-left",   Math.max(0, r.left) + "px");
    overlay.style.setProperty("--vd-hover-width",  r.width + "px");
    overlay.style.setProperty("--vd-hover-height",
        Math.max(r.height, window.innerHeight - r.top - 20) + "px");
}

function _setupObserver() {
    if (_resizeObserver) return;
    const right = _findRightPanel();
    if (!right || typeof ResizeObserver === "undefined") return;
    _resizeObserver = new ResizeObserver(() => _positionOverlay());
    _resizeObserver.observe(right);
}

function _teardownObserver() {
    if (_resizeObserver) {
        _resizeObserver.disconnect();
        _resizeObserver = null;
    }
}

function _open() {
    _cancelClose();
    _cancelOpen();
    _positionOverlay();
    HTML.classList.add(HOVER_CLS);
    _setupObserver();
}

function _close() {
    HTML.classList.remove(HOVER_CLS);
    if (!HTML.classList.contains(PINNED_CLS)) {
        _teardownObserver();
    }
}

function _scheduleOpen() {
    _cancelOpen();
    _openTimer = setTimeout(() => {
        _openTimer = null;
        _open();
    }, HOVER_OPEN_DELAY);
}

function _scheduleClose() {
    if (HTML.classList.contains(PINNED_CLS)) return;  // pinned: never auto-close
    _cancelClose();
    _closeTimer = setTimeout(() => {
        _closeTimer = null;
        _close();
    }, CLOSE_DELAY);
}

function _cancelOpen() {
    if (_openTimer) {
        clearTimeout(_openTimer);
        _openTimer = null;
    }
}
function _cancelClose() {
    if (_closeTimer) {
        clearTimeout(_closeTimer);
        _closeTimer = null;
    }
}

// ===== EVENTS =====
// Mouseenter button → schedule open (250ms delay).
document.addEventListener("mouseenter", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;

    if (target.closest(".o_vd_open_intake_btn_main")) {
        _scheduleOpen();
        return;
    }
    // Mouseenter panel (đang hover-open) → cancel close
    if (HTML.classList.contains(HOVER_CLS) && target.closest(".o_vd_intake_popup_panel")) {
        _cancelClose();
    }
}, true);

document.addEventListener("mouseleave", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;

    if (target.closest(".o_vd_open_intake_btn_main")) {
        _cancelOpen();    // cancel pending open nếu chưa kịp mở
        _scheduleClose(); // close nếu đã mở
        return;
    }
    if (HTML.classList.contains(HOVER_CLS) && target.closest(".o_vd_intake_popup_panel")) {
        _scheduleClose();
    }
}, true);

// Click button → PIN mode (persistent). Click X close → unpin.
document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;

    if (target.closest(".o_vd_popup_close_btn")) {
        HTML.classList.remove(PINNED_CLS);
        _close();
        _teardownObserver();
        return;
    }

    if (target.closest(".o_vd_open_intake_btn_main")) {
        _cancelOpen();
        _cancelClose();
        if (HTML.classList.contains(PINNED_CLS)) {
            HTML.classList.remove(PINNED_CLS);
            _close();
            _teardownObserver();
        } else {
            HTML.classList.add(PINNED_CLS);
            _open();
        }
    }
}, true);
