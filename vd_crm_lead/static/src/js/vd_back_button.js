/** @odoo-module **/
/**
 * Nút "← Quay lại" inject vào navbar (góc trên trái, cạnh CRM logo).
 *
 * Click → Ưu tiên click vào breadcrumb item PHÍA TRƯỚC current (Odoo SPA
 * không reliable với history.back() vì internal renders push lung tung
 * lên history stack). Fallback: history.back() nếu không có breadcrumb.
 */

const BTN_ID = "vd_back_btn";

function _goBack(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    // STRATEGY 1: click breadcrumb item NGAY TRƯỚC current.
    // Odoo 18 breadcrumb structure: ol.breadcrumb > li.breadcrumb-item *
    //   .breadcrumb-item (clickable links) ... .breadcrumb-item.active (current)
    // Hoặc Odoo 18 mới: .o_breadcrumb .o_breadcrumb_item button/a clickable +
    //   last child là current (không clickable).
    const breadcrumbLinks = document.querySelectorAll(
        ".o_breadcrumb .o_breadcrumb_item a, " +
        ".o_breadcrumb .o_breadcrumb_item button:not([disabled]), " +
        ".breadcrumb .breadcrumb-item a, " +
        ".breadcrumb .breadcrumb-item:not(.active) a"
    );
    if (breadcrumbLinks.length > 0) {
        // Click cái CUỐI cùng trong list clickable (tức là item ngay trước current)
        const target = breadcrumbLinks[breadcrumbLinks.length - 1];
        target.click();
        return;
    }
    // STRATEGY 2: history.back() fallback
    if (window.history.length > 1) {
        window.history.back();
    }
}

function makeButton() {
    const btn = document.createElement("button");
    btn.id = BTN_ID;
    btn.className = "vd_back_btn btn btn-sm";
    btn.title = "Quay lại trang trước";
    btn.innerHTML = '<i class="fa fa-arrow-left"></i><span class="vd_back_lbl">Quay lại</span>';
    btn.addEventListener("click", _goBack);
    return btn;
}

function injectInto(navbar) {
    if (!navbar || navbar.querySelector(`#${BTN_ID}`)) return;
    // Đặt SAU apps menu icon, TRƯỚC brand "CRM"
    const brand = navbar.querySelector(".o_menu_brand, .o_main_navbar_title");
    const appsMenu = navbar.querySelector(".o_navbar_apps_menu");
    const btn = makeButton();
    if (brand) {
        brand.parentNode.insertBefore(btn, brand);
    } else if (appsMenu && appsMenu.nextSibling) {
        appsMenu.parentNode.insertBefore(btn, appsMenu.nextSibling);
    } else {
        navbar.prepend(btn);
    }
    syncVisibility(btn);
}

function syncVisibility(btn) {
    // Hiện nếu có breadcrumb item trước current HOẶC history.length > 1
    const hasBreadcrumb = !!document.querySelector(
        ".o_breadcrumb .o_breadcrumb_item a, " +
        ".o_breadcrumb .o_breadcrumb_item button:not([disabled]), " +
        ".breadcrumb .breadcrumb-item:not(.active) a"
    );
    const hasHistory = window.history.length > 1;
    btn.style.display = (hasBreadcrumb || hasHistory) ? "" : "none";
}

const observer = new MutationObserver(() => {
    const navbar = document.querySelector(".o_main_navbar");
    if (navbar) {
        injectInto(navbar);
        const btn = navbar.querySelector(`#${BTN_ID}`);
        if (btn) syncVisibility(btn);
    }
});

if (document.readyState !== "loading") {
    observer.observe(document.body, { childList: true, subtree: true });
    const navbar = document.querySelector(".o_main_navbar");
    if (navbar) injectInto(navbar);
} else {
    document.addEventListener("DOMContentLoaded", () => {
        observer.observe(document.body, { childList: true, subtree: true });
        const navbar = document.querySelector(".o_main_navbar");
        if (navbar) injectInto(navbar);
    });
}
