/** @odoo-module **/
/**
 * Track con trỏ chuột trên mỗi .o_vd_problem_card → set CSS variable
 * `--vd-hover-x` = vị trí center X (clamped) cho popover chi tiết vấn đề
 * hiển thị NGAY DƯỚI con trỏ thay vì luôn full row width.
 *
 * Listener gắn 1 lần ở document; selector .closest() chỉ match khi
 * mouse thực sự nằm trong 1 problem card → ít overhead.
 */
document.addEventListener("mousemove", (ev) => {
    const card = ev.target && ev.target.closest && ev.target.closest(".o_vd_problem_card");
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const cardW = rect.width;
    if (!cardW) return;
    // Popover width = 50% card width (matching SCSS), capped 480px
    const popW = Math.min(cardW * 0.5, 480);
    const half = popW / 2;
    const margin = 6;
    const rawX = ev.clientX - rect.left;
    const clamped = Math.max(half + margin, Math.min(cardW - half - margin, rawX));
    card.style.setProperty("--vd-hover-x", clamped + "px");
    card.style.setProperty("--vd-hover-popw", popW + "px");
});
