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
const ON_LEAD_CLS = "vd-on-lead-form";
const HOVER_OPEN_DELAY = 250;   // ms — chống accidental hover
const CLOSE_DELAY = 200;        // ms — grace di chuột từ button → panel

// ===== DETECT LEAD FORM (add .vd-on-lead-form vào <html>) =====
// CSS zoom 0.7 chỉ apply khi class này active → form khác không bị zoom theo.
function _detectLeadForm() {
    const hasLeadForm = !!document.querySelector(".o_form_view .o_vd_layout_grid");
    HTML.classList.toggle(ON_LEAD_CLS, hasLeadForm);
}
// Run on initial load + watch DOM changes (debounced)
let _detectTimer = null;
function _scheduleDetect() {
    if (_detectTimer) return;
    _detectTimer = setTimeout(() => {
        _detectTimer = null;
        _detectLeadForm();
    }, 100);
}
const _mainObserver = new MutationObserver(_scheduleDetect);
_mainObserver.observe(document.documentElement, { childList: true, subtree: true });
_detectLeadForm();

// Read CSS zoom factor (cần để hover position bù lại scale).
function _getZoomFactor() {
    const sheet = document.querySelector(".o_form_view .o_form_sheet");
    if (!sheet) return 1;
    const z = parseFloat(getComputedStyle(sheet).zoom || "1");
    return isNaN(z) || z <= 0 ? 1 : z;
}

let _openTimer = null;
let _closeTimer = null;
let _resizeObserver = null;

function _findRightPanel() {
    // Scope vào form view đang visible để không match nhầm wizard/khác.
    const form = document.querySelector(".o_form_view");
    return form ? form.querySelector(".o_vd_layout_right") : null;
}
function _findOverlay() {
    // Ưu tiên tìm overlay đã portal lên body trước (nếu đang open).
    const portaled = document.body.querySelector(":scope > .o_vd_intake_popup_overlay");
    if (portaled) return portaled;
    return document.querySelector(".o_vd_intake_popup_overlay");
}

// ===== PORTAL OVERLAY TO <body> =====
// Khi mở: di chuyển overlay ra body để ESCAPE zoom 0.7 context của form sheet.
// Khi đóng: trả về vị trí gốc để Odoo OWL không bị lệch render tree.
let _portalOriginalParent = null;
let _portalOriginalNext = null;

function _portalToBody() {
    const overlay = _findOverlay();
    if (!overlay) return;
    if (overlay.parentElement === document.body) return; // đã portal
    _portalOriginalParent = overlay.parentElement;
    _portalOriginalNext = overlay.nextElementSibling;
    document.body.appendChild(overlay);
}

function _restoreFromBody() {
    const overlay = document.body.querySelector(":scope > .o_vd_intake_popup_overlay");
    if (!overlay || !_portalOriginalParent) {
        _portalOriginalParent = null;
        _portalOriginalNext = null;
        return;
    }
    try {
        if (_portalOriginalNext && _portalOriginalNext.parentElement === _portalOriginalParent) {
            _portalOriginalParent.insertBefore(overlay, _portalOriginalNext);
        } else {
            _portalOriginalParent.appendChild(overlay);
        }
    } catch (_e) { /* parent có thể đã unmount; bỏ qua */ }
    _portalOriginalParent = null;
    _portalOriginalNext = null;
}

function _positionOverlay() {
    const right = _findRightPanel();
    const overlay = _findOverlay();
    if (!right || !overlay) return;
    const r = right.getBoundingClientRect();
    if (r.width < 50 || r.height < 50) return;
    // Overlay đã portal ra <body> → KHÔNG còn trong zoom context.
    // Set rect viewport coords trực tiếp, không cần chia zoom.
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
    _portalToBody();           // escape form's zoom 0.7 context
    _positionOverlay();
    HTML.classList.add(HOVER_CLS);
    _setupObserver();
}

function _close() {
    HTML.classList.remove(HOVER_CLS);
    if (!HTML.classList.contains(PINNED_CLS)) {
        _teardownObserver();
        _restoreFromBody();    // trả overlay về cây Odoo OWL
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
