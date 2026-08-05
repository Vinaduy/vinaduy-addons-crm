/** @odoo-module **/
/**
 * intake_safety_save — LƯỚI AN TOÀN chống mất dữ liệu bảng THÔNG TIN TƯ VẤN.
 *
 * Bệnh: các ô intake chỉ `record.update` (in-memory) + LƯU DỒN debounce 900ms.
 * Nếu NV rời bảng / đổi khách / ẩn tab TRƯỚC khi timer chạy → thay đổi chưa kịp
 * vào DB → MẤT.
 *
 * Cách chữa: nghe sự kiện "rời bảng" → flush ô số đang gõ + record.save() NGAY.
 *   - focusout khỏi .o_vd_steps_panel (và focus mới KHÔNG còn trong bảng / overlay
 *     dropdown đang chọn) → lưu.
 *   - tab ẩn (visibilitychange) / đóng trang (pagehide) → lưu best-effort.
 * Chỉ lưu khi record DIRTY (tránh reload thừa). Có cờ chặn lưu chồng.
 *
 * Dùng record + helper do vd_num_input.js expose:
 *   window.__vdGetIntakeRecord(), window.__vdFlushIntakeInputs()
 */

let _focusTimer = null;

// 2026-08-05: lưu ở đây TRƯỚC ĐÂY là `rec.save()` mặc định = save + ĐỌC LẠI
// record từ DB (reload) → dựng lại toàn bộ form. Vì bấm 1 chip làm focus rơi về
// <body>, hàm "còn đang thao tác?" luôn trả false → CỨ bấm chip sau khi gõ số là
// form reload ngay giữa lúc thao tác → nuốt sạch. Nay dùng chung đường lưu
// KHÔNG RELOAD (__vdSaveIntakeNow → record.save({reload:false})).
async function _safetySave(reason) {
    let rec = null;
    try { rec = window.__vdGetIntakeRecord && window.__vdGetIntakeRecord(); } catch (_e) {}
    if (!rec) return;
    let dirty = true;
    try {
        if (typeof rec.dirty === "boolean") dirty = rec.dirty;
    } catch (_e) {}
    if (!dirty) return;
    try {
        if (window.__vdSaveIntakeNow) await window.__vdSaveIntakeNow(rec, reason);
    } catch (e) {
        try { console.warn("[vd intake safety] save failed:", e); } catch (_) {}
    }
}

// Rời ô nhập → lưu ngầm (không reload nên chạy lúc nào cũng an toàn).
document.addEventListener("focusout", (ev) => {
    const t = ev.target;
    if (!(t instanceof Element) || !t.closest(".o_vd_steps_panel")) return;
    if (_focusTimer) clearTimeout(_focusTimer);
    _focusTimer = setTimeout(() => {
        _focusTimer = null;
        _safetySave("focusout");
    }, 300);
}, true);

// Ẩn tab / đóng trang → lưu best-effort.
document.addEventListener("visibilitychange", () => {
    if (document.hidden) _safetySave("hidden");
});
window.addEventListener("pagehide", () => _safetySave("pagehide"));
