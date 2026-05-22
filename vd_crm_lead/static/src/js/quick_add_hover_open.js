/** @odoo-module **/
/**
 * Hover-to-open cho các cột Selection trong wizard "Thêm KH mới".
 *
 * Đáng lẽ NV phải click 1 lần để cell vào edit mode (widget render +
 * auto-open via vd_selection_dropdown). User muốn chỉ cần di chuột vào
 * cell là dropdown bung ra — không click.
 *
 * Cách: lắng nghe `mouseenter` trên TD cells của các field selection
 * trong list của model vd.lead.quick.add.wizard.line. Sau 80ms delay
 * (tránh hover lướt vô tình), simulate click trên cell để chuyển sang
 * edit mode. Widget mount → auto-open.
 */

const HOVER_TARGET_FIELDS = new Set([
    "source",
    "i_house_type",
    "i_foundation_type",
    "i_floors_select",
    "i_dimensions",
    "i_land_type",
    "i_car_access_select",
]);

const HOVER_DELAY_MS = 80;

let _pendingTd = null;
let _pendingTimer = null;

function _clearPending() {
    if (_pendingTimer) {
        clearTimeout(_pendingTimer);
        _pendingTimer = null;
    }
    _pendingTd = null;
}

function _isWizardLineCell(td) {
    if (!td || td.tagName !== "TD") return false;
    const name = td.getAttribute("name") || td.dataset?.name;
    if (!HOVER_TARGET_FIELDS.has(name)) return false;
    // Kiểm tra cell thuộc table của wizard line model
    const table = td.closest(".o_list_table, .o_list_renderer");
    if (!table) return false;
    // Cell đang ở edit mode rồi (đã có widget root bên trong) → bỏ qua
    if (td.querySelector(".o_vd_select_dd")) return false;
    return true;
}

document.addEventListener(
    "mouseenter",
    (ev) => {
        const target = ev.target;
        if (!(target instanceof Element)) return;
        const td = target.closest("td");
        if (!_isWizardLineCell(td)) return;

        _clearPending();
        _pendingTd = td;
        _pendingTimer = setTimeout(() => {
            if (_pendingTd === td && document.contains(td)) {
                // Simulate click để Odoo cell vào edit mode → vd_selection_dropdown
                // mount → setup() detect list ancestor → auto-open.
                td.click();
            }
            _pendingTimer = null;
            _pendingTd = null;
        }, HOVER_DELAY_MS);
    },
    true,
);

document.addEventListener(
    "mouseleave",
    (ev) => {
        const td = ev.target instanceof Element ? ev.target.closest("td") : null;
        if (_pendingTd && td === _pendingTd) {
            _clearPending();
        }
    },
    true,
);
