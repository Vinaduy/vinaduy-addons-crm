/** @odoo-module **/
/**
 * Nút "← Quay lại" inject vào navbar (góc trên trái, cạnh CRM logo).
 * Click → window.history.back(). Ẩn khi không có lịch sử navigate (length <= 1).
 *
 * Dùng MutationObserver vì NavBar render lazy + có thể re-render khi
 * switch action.
 */

const BTN_ID = "vd_back_btn";

function makeButton() {
    const btn = document.createElement("button");
    btn.id = BTN_ID;
    btn.className = "vd_back_btn btn btn-sm";
    btn.title = "Quay lại trang trước (Alt+←)";
    btn.innerHTML = '<i class="fa fa-arrow-left"></i><span class="vd_back_lbl">Quay lại</span>';
    btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        if (window.history.length > 1) {
            window.history.back();
        }
    });
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
    // Ẩn nếu không có history (vào thẳng lead app, length = 1)
    if (window.history.length <= 1) {
        btn.style.display = "none";
    }
}

const observer = new MutationObserver(() => {
    const navbar = document.querySelector(".o_main_navbar");
    if (navbar) {
        injectInto(navbar);
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
