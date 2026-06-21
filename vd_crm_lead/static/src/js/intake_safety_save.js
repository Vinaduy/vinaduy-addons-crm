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

let _saving = false;
let _focusTimer = null;

// Còn đang thao tác trong bảng / overlay dropdown? → KHÔNG lưu (sẽ reload cắt ngang).
function _stillEditing() {
    const ae = document.activeElement;
    return !!(ae && ae.closest && ae.closest(
        ".o_vd_steps_panel, .o-overlay-container, .o-autocomplete, " +
        ".o_vd_selection_hover_picker, .o_vd_m2o_hover_picker"
    ));
}

async function _safetySave(reason) {
    if (_saving) return;
    let rec = null;
    try { rec = window.__vdGetIntakeRecord && window.__vdGetIntakeRecord(); } catch (_e) {}
    if (!rec) return;
    // Chỉ lưu khi có thay đổi chưa lưu (Odoo 18: record.isDirty / .dirty).
    let dirty = true;
    try {
        if (typeof rec.isDirty === "boolean") dirty = rec.isDirty;
        else if (typeof rec.dirty === "boolean") dirty = rec.dirty;
    } catch (_e) {}
    if (!dirty) return;
    _saving = true;
    try {
        if (window.__vdFlushIntakeInputs) {
            await window.__vdFlushIntakeInputs("safety:" + reason);
        }
    } catch (_e) { /* ignore */ }
    try {
        await rec.save();
    } catch (e) {
        try { console.warn("[vd intake safety] save failed:", e); } catch (_) {}
    } finally {
        _saving = false;
    }
}

// Rời bảng (focus nhảy ra ngoài) → chờ 1 nhịp rồi kiểm tra, nếu thật sự ra ngoài → lưu.
document.addEventListener("focusout", (ev) => {
    const t = ev.target;
    if (!(t instanceof Element) || !t.closest(".o_vd_steps_panel")) return;
    if (_focusTimer) clearTimeout(_focusTimer);
    _focusTimer = setTimeout(() => {
        _focusTimer = null;
        if (!_stillEditing()) _safetySave("focusout");
    }, 220);
}, true);

// Ẩn tab / đóng trang → lưu best-effort.
document.addEventListener("visibilitychange", () => {
    if (document.hidden) _safetySave("hidden");
});
window.addEventListener("pagehide", () => _safetySave("pagehide"));
