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
    return document.querySelector(".o_vd_intake_popup_overlay");
}

// ===== PORTAL OVERLAY TO RIGHT PANEL (tab-switch style) =====
// Khi mở: di chuyển overlay vào .o_vd_layout_right để nó CHIẾM CHỖ panel VẤN ĐỀ
// (như chuyển tab). KHÔNG fixed positioning, KHÔNG zoom math — cùng zoom context
// với right panel nên dimensions tự khớp.
// Khi đóng: trả về vị trí gốc.
let _portalOriginalParent = null;
let _portalOriginalNext = null;

function _portalToRightPanel() {
    const overlay = _findOverlay();
    const right = _findRightPanel();
    if (!overlay || !right) return;
    if (overlay.parentElement === right) return; // đã portal
    _portalOriginalParent = overlay.parentElement;
    _portalOriginalNext = overlay.nextElementSibling;
    right.appendChild(overlay);
}

function _restoreFromRightPanel() {
    const overlay = _findOverlay();
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

// Overlay đã portal VÀO right panel → CSS dùng position:absolute; inset:0
// để fill panel. Không cần JS positioning nữa.
function _positionOverlay() { /* no-op — pure CSS */ }

function _setupObserver() { /* no-op — portal mode không cần observer */ }
function _teardownObserver() { /* no-op */ }

function _open() {
    _cancelClose();
    _cancelOpen();
    _portalToRightPanel();     // di overlay vào right panel — như chuyển tab
    HTML.classList.add(HOVER_CLS);
}

function _close() {
    HTML.classList.remove(HOVER_CLS);
    if (!HTML.classList.contains(PINNED_CLS)) {
        _restoreFromRightPanel();    // trả overlay về cây Odoo OWL gốc
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
