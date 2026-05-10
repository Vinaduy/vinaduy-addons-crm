/** @odoo-module **/
/**
 * Toggle class .o_vd_sheet_expanded trên .o_form_sheet khi phiếu khai thác
 * mở (.o_vd_intake_full xuất hiện). CSS dùng class này để widen sheet và
 * apply grid 2-cột (form + bubble bên trong sheet).
 *
 * Tránh dùng :has() (không tin cậy 100%). JS đáng tin trên mọi browser.
 */

const SHEET_SEL = ".o_form_sheet";
const FULL_SEL = ".o_vd_intake_full";
const SIDEBAR_SEL = ".o_vd_intake_sidebar";
const EXPANDED_CLS = "o_vd_sheet_expanded";

function syncOne(sheet) {
    const hasFull = !!sheet.querySelector(FULL_SEL);
    sheet.classList.toggle(EXPANDED_CLS, hasFull);

    // Defensive: clear any inline positioning từ build trước
    const sidebar = sheet.querySelector(SIDEBAR_SEL);
    if (sidebar) {
        sidebar.style.position = "";
        sidebar.style.left = "";
        sidebar.style.top = "";
        sidebar.style.right = "";
        sidebar.style.width = "";
        sidebar.style.maxWidth = "";
        sidebar.style.maxHeight = "";
        sidebar.style.overflowY = "";
        sidebar.style.zIndex = "";
        sidebar.style.marginTop = "";
    }
}

function syncAll() {
    try {
        document.querySelectorAll(SHEET_SEL).forEach(syncOne);
    } catch (e) {
        // Defensive — không bao giờ throw để tránh trắng màn
    }
}

let rafToken = null;
function schedule() {
    if (rafToken) return;
    rafToken = window.requestAnimationFrame(function () {
        rafToken = null;
        syncAll();
    });
}

if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(schedule);
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener("DOMContentLoaded", function () {
            observer.observe(document.body, { childList: true, subtree: true });
            schedule();
        });
    }
}

if (document.readyState !== "loading") {
    schedule();
} else {
    document.addEventListener("DOMContentLoaded", schedule);
}

// ============= FLASH effect WOW khi value compute thay đổi =============
// 3 LOẠI hiệu ứng tùy element:
// • AMOUNT (.vd-flash-amount) — số tiền: scale 1.55x + đổi màu + glow + bounce
// • RIPPLE (.vd-ripple-burst) — banner cảnh báo: vòng tròn loang + shake nếu critical
// • GENERAL (.vd-flash-update) — sections/badges: flash vàng + scale + glow

// Selectors cho hiệu ứng AMOUNT (mạnh nhất — số tiền)
const FLASH_AMOUNT_TARGETS = [
    ".o_vd_bubble_amount",                            // Số ước tính trong bubble
    ".o_vd_summary_estimate .o_vd_sum_est_value",     // Ước tính trong summary
    ".o_vd_summary_hero .o_vd_sum_hero_value",        // Hero card values
];

// Selectors cho hiệu ứng RIPPLE (banner cảnh báo)
const FLASH_RIPPLE_TARGETS = [
    ".o_vd_consult_bubble .o_vd_bubble_section > b:first-child",  // Banner heading
    ".o_vd_consult_bubble .o_vd_bubble_section > p:first-child > b:first-child",
    ".o_vd_sum_budget_badge",                         // Badge trạng thái ngân sách
    ".o_vd_sum_time_badge",                           // Badge trạng thái thời gian
];

// Selectors cho hiệu ứng GENERAL (background flash)
const FLASH_GENERAL_TARGETS = [
    ".o_vd_consult_bubble .o_vd_bubble_section",      // Toàn bộ section
    ".o_vd_summary_estimate",                         // Row ước tính trong summary
];

function applyFlash(el, className, durationMs) {
    if (!el) return;
    el.classList.remove(className);
    void el.offsetWidth; // force reflow để restart animation
    el.classList.add(className);
    setTimeout(() => el.classList.remove(className), durationMs);
}

function flashAmount(el) {
    applyFlash(el, "vd-flash-amount", 1450);
}
function flashRipple(el) {
    applyFlash(el, "vd-ripple-burst", 1250);
    // Thêm shake nếu là banner critical (đỏ - màu c92a2a)
    const style = el.getAttribute("style") || "";
    if (style.includes("c92a2a") || el.classList.contains("o_vd_badge_over")) {
        applyFlash(el, "vd-shake-alert", 650);
    }
}
function flashGeneral(el) {
    applyFlash(el, "vd-flash-update", 1150);
}

const flashCache = new WeakMap();
function watchSet(selectors, flashFn) {
    selectors.forEach((sel) => {
        document.querySelectorAll(sel).forEach((el) => {
            const currentText = el.textContent.trim();
            const lastText = flashCache.get(el);
            if (lastText !== undefined && lastText !== currentText && currentText !== "") {
                flashFn(el);
            }
            flashCache.set(el, currentText);
        });
    });
}

function watchFlashTargets() {
    try {
        watchSet(FLASH_AMOUNT_TARGETS, flashAmount);
        watchSet(FLASH_RIPPLE_TARGETS, flashRipple);
        watchSet(FLASH_GENERAL_TARGETS, flashGeneral);
    } catch (e) {}
}

// Trigger watch sau mỗi DOM mutation (Owl re-render)
let flashRaf = null;
function scheduleFlashCheck() {
    if (flashRaf) return;
    flashRaf = window.requestAnimationFrame(() => {
        flashRaf = null;
        watchFlashTargets();
    });
}

if (typeof MutationObserver !== "undefined") {
    const flashObs = new MutationObserver(scheduleFlashCheck);
    if (document.body) {
        flashObs.observe(document.body, { childList: true, subtree: true, characterData: true });
    } else {
        document.addEventListener("DOMContentLoaded", () => {
            flashObs.observe(document.body, { childList: true, subtree: true, characterData: true });
        });
    }
}
