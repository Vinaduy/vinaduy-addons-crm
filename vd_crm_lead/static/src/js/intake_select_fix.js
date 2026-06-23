/** @odoo-module **/
/**
 * Đơn giản — KHÔNG wrap, chỉ:
 * 1. Ẩn <option value=""> khỏi listbox của Selection field trong popup
 *    (placeholder option không xuất hiện trong dropdown khi user mở).
 * 2. Đính <datalist> 24 tháng cho ô "Thời gian dự kiến".
 *
 * Defensive: bỏ qua mọi element không phải HTMLSelectElement / HTMLInputElement.
 */

const SCOPE = ".o_vd_intake_compact, .o_vd_hero_card";
const TIMELINE_INPUT = ".o_vd_hero_time input[type='text']";

function patchSelect(sel) {
    // Defensive: chỉ xử lý native <select>
    if (!sel || sel.tagName !== "SELECT" || !sel.options) return;
    for (const opt of sel.options) {
        const val = opt.getAttribute("value");
        // Odoo 18 dùng value="false" (stringify từ JS) làm placeholder option.
        // Cũng cover các trường hợp value="" hoặc không có value.
        if (val === "false" || val === "" || val === null) {
            if (!opt.hidden) opt.hidden = true;
            if (opt.style.display !== "none") opt.style.display = "none";
        }
    }
}

function patchAllSelects() {
    try {
        document.querySelectorAll(`${SCOPE} select`).forEach(patchSelect);
    } catch (e) {
        // Không crash UI nếu có element bất thường
        console.warn("[VD intake] patchAllSelects skipped:", e);
    }
}

// ----- Dims input fade: gắn class .vd-dim-empty khi Float = 0 -----
function fadeZeroDims() {
    try {
        document.querySelectorAll(".o_vd_dims_row .o_field_widget input").forEach((input) => {
            if (!input || input.tagName !== "INPUT") return;
            const v = parseFloat(input.value || "0");
            const isEmpty = !v || v === 0 || isNaN(v);
            input.classList.toggle("vd-dim-empty", isEmpty);
        });
    } catch (e) {
        console.warn("[VD intake] fadeZeroDims skipped:", e);
    }
}

// ----- Month picker datalist -----
let _monthDl = null;
function buildMonthDatalist() {
    if (_monthDl && document.body.contains(_monthDl)) return _monthDl;
    const dl = document.createElement("datalist");
    dl.id = "vd-month-options";
    const today = new Date();
    for (let i = 0; i < 24; i++) {
        const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
        const opt = document.createElement("option");
        opt.value = `Tháng ${d.getMonth() + 1}/${d.getFullYear()}`;
        dl.appendChild(opt);
    }
    ["Càng sớm càng tốt", "Trong năm nay", "Năm sau", "Chưa xác định"].forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v;
        dl.appendChild(opt);
    });
    document.body.appendChild(dl);
    _monthDl = dl;
    return dl;
}

function attachMonthPicker() {
    try {
        document.querySelectorAll(TIMELINE_INPUT).forEach((input) => {
            if (!input || input.tagName !== "INPUT") return;
            if (input.dataset.vdMonthAttached) return;
            input.dataset.vdMonthAttached = "1";
            const dl = buildMonthDatalist();
            input.setAttribute("list", dl.id);
            input.setAttribute("autocomplete", "off");
        });
    } catch (e) {
        console.warn("[VD intake] attachMonthPicker skipped:", e);
    }
}

// ----- Clear (×) button cho mọi input trong popup -----
const CLEAR_SKIP_SELECTORS = [
    ".o_vd_select_dd",       // custom dropdown — đã có clear
    ".o-autocomplete",       // Many2one — Odoo tự có clear
    ".o_vd_popup_banner",    // banner đang gọi — phone readonly
    ".o_vd_dim_total",       // total diện tích — readonly
    ".o_vd_estimate_panel",  // panel estimate — readonly
    ".o_vd_floors_oneline",  // hàng số tầng — input diện tích Tầng 1/2/3... bỏ X (user request)
    ".o_vd_area_row",        // Dài / Rộng đất + nhà — bỏ X cho UX gọn
];

function shouldSkipClear(input) {
    if (!input) return true;
    // CHỈ áp dụng cho <input>, KHÔNG dùng cho <textarea> (textarea có resize
    // handle ở góc, button × làm overlap + lỗi visual ellipse)
    if (input.tagName !== "INPUT") return true;
    if (input.type === "checkbox" || input.type === "radio" || input.type === "button" || input.type === "submit") return true;
    if (input.readOnly || input.disabled) return true;
    if (input.dataset.vdClearAttached === "1") return true;
    for (const sel of CLEAR_SKIP_SELECTORS) {
        if (input.closest(sel)) return true;
    }
    return false;
}

// V2: Tạo X button SIBLING của input (không phải absolute trong wrapper)
// → wrap input trong span flex → button × ngay bên phải input → KHÔNG có
// CSS positioning conflict, KHÔNG bị Odoo CSS override.
function attachClearButton(input) {
    if (shouldSkipClear(input)) return;
    input.dataset.vdClearAttached = "1";

    const fieldWidget = input.closest(".o_field_widget") || input.parentElement;
    if (!fieldWidget) return;

    // Xóa mọi X button cũ (từ các build trước hoặc re-render cũ)
    fieldWidget.querySelectorAll(".o_vd_clear_btn, .vd-x-clear").forEach((b) => b.remove());

    // Tạo X button — DỰNG QUA TEXT ĐƠN GIẢN (không phải <button>) để tránh
    // Bootstrap .btn / Odoo button styles
    const x = document.createElement("span");
    x.className = "vd-x-clear";
    x.textContent = "×";
    x.title = "Xoá nội dung";
    x.setAttribute("role", "button");
    x.setAttribute("aria-label", "Xoá");

    // Inline styles VỚI !important — bypass cả SCSS .o_vd_pf > .o_field_widget > *
    // (rule này set width:100% !important cho mọi direct child của field_widget,
    // sẽ stretch X full width nếu không dùng !important).
    const styles = {
        position: "absolute",
        right: "8px",
        top: "50%",
        transform: "translateY(-50%)",
        width: "20px",
        "min-width": "20px",
        "max-width": "20px",
        height: "20px",
        "min-height": "20px",
        "max-height": "20px",
        "line-height": "18px",
        "text-align": "center",
        "font-size": "16px",
        "font-weight": "bold",
        color: "#868e96",
        background: "transparent",
        border: "1px solid #ced4da",
        "border-radius": "50%",
        cursor: "pointer",
        "z-index": "10",
        display: "none",
        padding: "0",
        margin: "0",
        "box-sizing": "border-box",
        "user-select": "none",
        "pointer-events": "auto",
        flex: "0 0 20px",
    };
    Object.entries(styles).forEach(([k, v]) => x.style.setProperty(k, v, "important"));

    // Ensure parent là position relative (cho absolute child)
    if (getComputedStyle(fieldWidget).position === "static") {
        fieldWidget.style.position = "relative";
    }

    const update = () => {
        const v = input.value;
        const hasVal = v && v !== "0" && v !== "0.00" && v !== "0.0";
        x.style.setProperty("display", hasVal ? "inline-block" : "none", "important");
    };

    x.addEventListener("mousedown", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const proto = Object.getOwnPropertyDescriptor(
            input.tagName === "TEXTAREA"
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype,
            "value"
        );
        if (proto && proto.set) proto.set.call(input, "");
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.focus();
        update();
    });

    x.addEventListener("mouseenter", () => {
        x.style.setProperty("background", "#fa5252", "important");
        x.style.setProperty("color", "#fff", "important");
        x.style.setProperty("border-color", "#fa5252", "important");
    });
    x.addEventListener("mouseleave", () => {
        x.style.setProperty("background", "transparent", "important");
        x.style.setProperty("color", "#868e96", "important");
        x.style.setProperty("border-color", "#ced4da", "important");
    });

    fieldWidget.appendChild(x);

    input.addEventListener("input", update);
    input.addEventListener("change", update);
    update();
}

function attachClearAll() {
    try {
        // Xóa hẳn các button cũ với class .o_vd_clear_btn (legacy bị stretch)
        document.querySelectorAll(".o_vd_clear_btn").forEach((b) => b.remove());
        // CHỈ <input> trong popup. Textarea bị skip vì gây bug visual ellipse.
        document.querySelectorAll(".o_vd_intake_compact input").forEach(attachClearButton);
    } catch (e) {
        console.warn("[VD intake] attachClearAll skipped:", e);
    }
}

// ----- Focus-clear cho Float/Monetary input có value = 0 -----
// Khi user click vào input đang hiển thị "0.00" / "0" → tự xoá visual để
// placeholder hiện ra + user gõ thẳng giá trị mới (KHÔNG cần Backspace).
// Khi blur mà input rỗng → khôi phục "0" để Odoo không lưu null bất ngờ.
function attachZeroFocusClear(input) {
    if (!input || input.dataset.vdZeroFocus === "1") return;
    if (input.type === "checkbox" || input.type === "radio" || input.readOnly) return;
    input.dataset.vdZeroFocus = "1";

    const isZeroValue = (v) => {
        if (v === undefined || v === null || v === "") return true;
        const f = parseFloat(String(v).replace(/[,\s]/g, ""));
        return f === 0 || isNaN(f);
    };

    const setNativeValue = (el, val) => {
        const proto = Object.getOwnPropertyDescriptor(
            el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
            "value"
        );
        if (proto && proto.set) proto.set.call(el, val);
    };

    input.addEventListener("focus", () => {
        if (isZeroValue(input.value)) {
            // Clear hiển thị để placeholder hiện + user gõ trực tiếp
            setNativeValue(input, "");
        } else {
            // Đã có giá trị thật → select all để gõ replace nhanh
            requestAnimationFrame(() => {
                try { input.select(); } catch (e) {}
            });
        }
    });

    input.addEventListener("blur", () => {
        // GIỮ TRỐNG khi value = 0 — không restore "0" để placeholder hiện ra.
        // Odoo internal value đã là 0 sẵn, display trống không ảnh hưởng data.
        if (isZeroValue(input.value)) {
            setNativeValue(input, "");
        }
    });
}

function attachZeroFocusAll() {
    try {
        // Áp dụng cho Float/Monetary inputs trong popup:
        // - Hero ngân sách (monetary)
        // - Dim length / width (Float)
        // - Số tầng (Float)
        const selectors = [
            ".o_vd_hero_budget input",
            ".o_vd_dim_input input",
            // .o_vd_num_input do widget vd_num_input tự quản (blank-when-zero) →
            // KHÔNG để legacy setNativeValue đè lên OWL gây desync/mất chữ.
            ".o_vd_area_dim input:not(.o_vd_num_input)",   // Dài/Rộng (đất + nhà)
            ".o_vd_area_input input:not(.o_vd_num_input)", // Diện tích đất + nhà
            ".o_vd_tech_field input[type=number]",
            ".o_vd_tech_field input[type=text]",
        ];
        document.querySelectorAll(selectors.join(", ")).forEach(attachZeroFocusClear);
    } catch (e) {
        console.warn("[VD intake] attachZeroFocusAll skipped:", e);
    }
}

// ----- Clear hiển thị "0.00" / "0" / "0.0" m² ngay khi Odoo render lại -----
// Khi field Float/Monetary có value = 0, Odoo display "0.00". User muốn TRỐNG
// (placeholder hiện ra). Function này chạy mỗi schedule (sau re-render) để
// xoá display 0 nếu input không focus.
function clearZeroDisplays() {
    try {
        const isZero = (v) => {
            if (v === undefined || v === null || v === "") return true;
            const f = parseFloat(String(v).replace(/[,\s]/g, ""));
            return f === 0 || isNaN(f);
        };
        const setNativeValue = (el, val) => {
            const proto = Object.getOwnPropertyDescriptor(
                el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
                "value"
            );
            if (proto && proto.set) proto.set.call(el, val);
        };

        // Inputs cần clear: ngân sách, dims, số tầng (writable)
        const writableSelectors = [
            ".o_vd_hero_budget input:not([readonly])",
            ".o_vd_dim_input input:not([readonly])",
            // Bỏ qua .o_vd_num_input (widget tự quản blank-when-zero).
            ".o_vd_area_dim input:not([readonly]):not(.o_vd_num_input)",
            ".o_vd_area_input input:not([readonly]):not(.o_vd_num_input)",
            ".o_vd_tech_field input:not([readonly])",
        ];
        document.querySelectorAll(writableSelectors.join(", ")).forEach((input) => {
            if (input.type === "checkbox" || input.type === "radio") return;
            if (document.activeElement === input) return;
            if (isZero(input.value)) {
                setNativeValue(input, "");
            }
        });

        // KHÔNG clear .o_vd_dim_total readonly span vì sẽ phá Owl reactivity:
        // - JS set textContent="" → Owl nghĩ vDOM đã render, không update khi
        //   compute ra giá trị mới (vd 60) → user thấy ô diện tích trống mãi
        // Để Odoo native render value (kể cả "0.0") thì compute reactive sẽ
        // tự update khi length/width thay đổi.
    } catch (e) {
        console.warn("[VD intake] clearZeroDisplays skipped:", e);
    }
}

// ----- Readable hint cho Ngân sách: "2,000,000,000 ₫" → "≈ 2 tỷ đồng" -----
function formatVndReadable(num) {
    if (!num || isNaN(num) || num <= 0) return "";
    const ty = Math.floor(num / 1_000_000_000);
    const trieu = Math.floor((num % 1_000_000_000) / 1_000_000);
    const nghin = Math.floor((num % 1_000_000) / 1_000);
    const dong = Math.floor(num % 1_000);
    const parts = [];
    if (ty > 0) parts.push(`${ty} tỷ`);
    if (trieu > 0) parts.push(`${trieu} triệu`);
    if (nghin > 0) parts.push(`${nghin} nghìn`);
    if (dong > 0) parts.push(`${dong} đồng`);
    return parts.join(" ") || "";
}

function attachReadableHint(input) {
    if (!input || input.dataset.vdReadable === "1") return;
    input.dataset.vdReadable = "1";

    // Ưu tiên append vào row .o_vd_budget_manual (ngay sau input ngân sách dự kiến).
    // Fallback: hero_card hoặc pf row.
    const manualRow = input.closest(".o_vd_budget_manual");
    const target = manualRow || input.closest(".o_vd_hero_card") || input.closest(".o_vd_pf");
    if (!target) return;

    let hint = target.querySelector(":scope > .o_vd_readable_hint");
    if (!hint) {
        hint = document.createElement("div");
        hint.className = "o_vd_readable_hint";
        target.appendChild(hint);
    }

    const update = () => {
        // Parse số: bỏ dấu phẩy, khoảng trắng, ký hiệu tiền tệ
        const raw = (input.value || "").replace(/[,\s₫\$đ]/g, "");
        const num = parseFloat(raw);
        if (!num || isNaN(num) || num <= 0) {
            hint.style.display = "none";
            hint.textContent = "";
            return;
        }
        const readable = formatVndReadable(num);
        hint.style.display = "block";
        hint.textContent = readable ? `≈ ${readable}` : "";
    };

    input.addEventListener("input", update);
    input.addEventListener("change", update);
    input.addEventListener("blur", update);
    update();
}

function attachReadableHintAll() {
    try {
        // Bỏ readable hint theo yêu cầu user — XOÁ existing hints + KHÔNG attach mới
        document.querySelectorAll(".o_vd_readable_hint").forEach((el) => el.remove());
    } catch (e) {
        console.warn("[VD intake] attachReadableHintAll skipped:", e);
    }
}

// ----- Live thousand separator: gõ tới đâu chèn dấu phẩy tới đó -----
function attachLiveSeparator(input) {
    if (!input || input.dataset.vdLiveSep === "1") return;
    input.dataset.vdLiveSep = "1";

    const formatLive = (val) => {
        const s = String(val || "");
        // Tách phần thập phân (nếu có) — dùng dấu chấm cuối cùng
        const lastDot = s.lastIndexOf(".");
        let intPart, decPart;
        if (lastDot >= 0) {
            intPart = s.slice(0, lastDot).replace(/[^\d]/g, "");
            decPart = s.slice(lastDot + 1).replace(/[^\d]/g, "");
        } else {
            intPart = s.replace(/[^\d]/g, "");
            decPart = "";
        }
        if (!intPart && !decPart && lastDot < 0) return "";
        // Format phần nguyên với dấu phẩy ngàn
        const intFmt = intPart ? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
        return lastDot >= 0 ? `${intFmt}.${decPart}` : intFmt;
    };

    input.addEventListener("input", (e) => {
        const oldVal = input.value;
        const oldCaret = input.selectionStart || 0;
        // Đếm số digit (và dấu chấm thập phân) trước caret để khôi phục vị trí
        const digitsBefore = oldVal.slice(0, oldCaret).replace(/[^\d.]/g, "").length;

        const newVal = formatLive(oldVal);
        if (newVal === oldVal) return;
        input.value = newVal;

        // Restore caret: đặt sau ký tự thứ N digits-or-dot từ trái
        let count = 0;
        let newCaret = newVal.length;
        for (let i = 0; i < newVal.length; i++) {
            if (count >= digitsBefore) {
                newCaret = i;
                break;
            }
            if (/[\d.]/.test(newVal[i])) count++;
        }
        try {
            input.setSelectionRange(newCaret, newCaret);
        } catch (_) {}
    });
}

function attachLiveSeparatorAll() {
    try {
        // Áp dụng cho TẤT CẢ input của ngân sách + monetary trong popup intake
        document.querySelectorAll(
            ".o_vd_hero_budget input, .o_vd_budget_manual input"
        ).forEach(attachLiveSeparator);
    } catch (e) {
        console.warn("[VD intake] attachLiveSeparatorAll skipped:", e);
    }
}

// ----- Bootstrap (debounced) -----
// TRAILING DEBOUNCE 150ms thay vì requestAnimationFrame: 1 lần form reload đẻ ra
// HÀNG CHỤC mutation/frame → rAF chạy mỗi frame = giật main-thread (khó click,
// mất con trỏ, nút chậm). Debounce gộp cả cụm mutation về 1-2 lần chạy → mượt.
let _schedTimer = null;
function schedule() {
    if (_schedTimer) clearTimeout(_schedTimer);
    _schedTimer = setTimeout(() => {
        _schedTimer = null;
        patchAllSelects();
        attachMonthPicker();
        fadeZeroDims();
        attachClearAll();
        attachZeroFocusAll();
        attachReadableHintAll();        // chỉ XOÁ hint cũ, không tạo mới
        attachLiveSeparatorAll();        // gõ tới đâu phân cách số tới đó
        clearZeroDisplays();
        attachAutoSaveBlur();            // blur Float/Char inputs → auto-save form
        syncIntakeLockedClass();         // sync class .vd-intake-locked theo state
    }, 150);
}

// ===== AUTO-SAVE on blur cho Float/Char inputs trong steps panel =====
// Để auto-lock trigger ngay khi user blur khỏi ô cuối (Tầng N m², Diện tích...)
// thay vì phải bấm cloud icon Save thủ công.
//
// QUAN TRỌNG — KHÔNG áp dụng cho ô Many2one (.o-autocomplete: Tỉnh/Huyện):
// ô số/chữ commit value NGAY khi blur, nhưng Many2one commit BẤT ĐỒNG BỘ.
// Nếu auto-save (debounce 350ms) bấm Lùu đúng lúc user vừa chọn ô m2o kế tiếp
// → form reload khi giá trị m2o trước đó CHƯA kịp commit → mất giá trị.
// Bug thực tế: chọn Tỉnh xong chọn Huyện → Tỉnh bị xoá trắng. Loại m2o khỏi
// auto-save-blur; Tỉnh/Huyện vẫn được lưu khi user bấm CHỐT hoặc blur ô khác.
async function _autoSaveFormSafe() {
    try {
        // NẾU NV vẫn đang focus 1 ô trong khu nhập (steps panel / overlay
        // dropdown) → KHOAN save. Save kéo theo reload form → xoá chữ đang gõ ở
        // ô kế. Chỉ save khi user đã rời hẳn khu intake. (Fix mất dữ liệu.)
        const ae = document.activeElement;
        if (ae && ae.closest && ae.closest(
            ".o_vd_steps_panel, .o_vd_intake_compact, .o-overlay-container, " +
            ".o_vd_selection_hover_picker, .o-autocomplete"
        )) {
            return;
        }
        // Vừa gõ số < 1.5s → khoan (giá trị có thể chưa ổn định).
        const g = window.__vdIntake;
        if (g && Date.now() - (g.lastType || 0) < 1500) {
            return;
        }
        // Ép mọi ô số commit giá trị in-flight TRƯỚC khi save → không mất dữ liệu.
        try { if (window.__vdFlushIntakeInputs) await window.__vdFlushIntakeInputs("blur autosave"); } catch (_) {}
        // Tìm cloud icon Save (Odoo 18 form view); click nếu form dirty.
        const btn = document.querySelector(
            ".o_form_view.o_form_dirty button.o_form_button_save, " +
            ".o_form_view button.o_form_button_save:not([disabled])"
        );
        if (btn && btn.offsetParent !== null) {
            btn.click();
        }
    } catch (e) {
        // im lặng — không phá UI
    }
}
let _autoSaveDebounce = null;
function attachAutoSaveBlur() {
    try {
        document.querySelectorAll(
            ".o_vd_steps_panel input, .o_vd_steps_panel textarea"
        ).forEach((el) => {
            if (el.dataset.vdAutoSaveBlur === "1") return;
            el.dataset.vdAutoSaveBlur = "1";
            el.addEventListener("blur", () => {
                if (_autoSaveDebounce) clearTimeout(_autoSaveDebounce);
                _autoSaveDebounce = setTimeout(_autoSaveFormSafe, 350);
            });
        });
    } catch (e) {}
}

// ===== Sync class 'vd-intake-locked' lên .o_vd_steps_panel =====
// Odoo 18: field Boolean invisible="1" KHÔNG render <input> DOM nên không
// thể đọc value trực tiếp. Dùng marker element o_vd_steps_lock_marker:
//   - View XML có <span class="o_vd_steps_lock_marker"
//                       invisible="not vd_intake_locked"/>
//   - Khi locked=True  → element render vào DOM
//   - Khi locked=False → invisible="True" → Odoo remove element khỏi DOM
//   - JS chỉ cần check existence để biết lock state
function syncIntakeLockedClass() {
    try {
        document.querySelectorAll('.o_vd_steps_panel').forEach((panel) => {
            const isLocked = !!panel.querySelector('.o_vd_steps_lock_marker');
            panel.classList.toggle('vd-intake-locked', isLocked);
            // Set HTML5 `inert` attribute trên từng step row (KHÔNG set lên
            // .o_vd_hero_head để giữ button Cúp máy/Copy/Mở khoá dùng được).
            // `inert` block CẢ click LẪN keystroke — user spec 2026-05-29: dù
            // input đã focus sẵn, lock xong vẫn không gõ được. Khác overlay
            // (chỉ block pointer, không block keyboard sau khi focus).
            panel.querySelectorAll('.o_vd_step, .o_vd_intake_consult_script_wrap').forEach((row) => {
                if (isLocked) row.setAttribute('inert', '');
                else row.removeAttribute('inert');
            });
        });
    } catch (e) {}
}

// ===== Nút +Tầng / +Tum / +Lửng chạy CLIENT-SIDE (không gọi server action) =====
// Server action type="object" = round-trip + reload toàn form mỗi lần bấm → rất
// chậm trên server thiếu RAM. Thay bằng record.update tại client: nhẹ, tức thì,
// và vẫn chạy onchange backend (_onchange_floors_select tự điền diện tích tầng).
// Nếu không lấy được record → KHÔNG chặn, để server action chạy như cũ (fallback).
const FLOOR_BTN_NAMES = ["action_add_floor", "action_toggle_tum", "action_toggle_lung"];
async function _handleFloorBtn(rec, name) {
    try {
        if (window.__vdFlushIntakeInputs) await window.__vdFlushIntakeInputs("floor btn:" + name);
        if (name === "action_add_floor") {
            const cur = parseInt(rec.data.vd_intake_floors_count || 1, 10) || 1;
            if (cur >= 7) return;
            const next = cur + 1;
            await rec.update({ vd_intake_floors_count: next, vd_intake_floors_select: String(next) });
        } else if (name === "action_toggle_tum") {
            await rec.update({ vd_intake_has_tum: !rec.data.vd_intake_has_tum });
        } else if (name === "action_toggle_lung") {
            await rec.update({ vd_intake_has_lung: !rec.data.vd_intake_has_lung });
        }
        // LƯU NGAY (flush đã chạy ở trên) — dòng tầng/tum/lửng vừa thêm phải bền
        // ngay, KHÔNG để mất khi user chuyển sang thao tác khác. Trước đây dùng
        // scheduleSave (hoãn 900ms + guard) nên thường bị bỏ qua → thay đổi chỉ
        // nằm in-memory, gặp reload là mất dòng vừa thêm.
        try { await rec.save(); } catch (e) { console.warn("[VD floor btn] save lỗi:", e); }
    } catch (err) {
        console.warn("[VD floor btn] lỗi, sẽ không chặn lần sau:", err);
    }
}

function start() {
    schedule();
    new MutationObserver(schedule).observe(document.body, {
        childList: true,
        subtree: true,
    });

    // Bắt click nút +Tầng/+Tum/+Lửng ở capture phase → chặn server action, chạy
    // client-side cho nhẹ + nhanh. (Nút Xoá tầng giữ server action vì logic dồn
    // tầng phức tạp.)
    document.addEventListener(
        "click",
        (e) => {
            const btn = e.target.closest && e.target.closest("button[name]");
            if (!btn) return;
            const name = btn.getAttribute("name");
            if (!FLOOR_BTN_NAMES.includes(name)) return;
            if (!btn.closest(".o_vd_steps_panel")) return;
            const rec = window.__vdGetIntakeRecord && window.__vdGetIntakeRecord();
            if (!rec) return;   // fallback: để server action chạy
            e.preventDefault();
            e.stopPropagation();
            _handleFloorBtn(rec, name);
        },
        true
    );
    // Update fade state khi user gõ vào dim input
    document.addEventListener(
        "input",
        (e) => {
            const t = e.target;
            if (t && t.tagName === "INPUT" && t.closest(".o_vd_dims_row")) {
                const v = parseFloat(t.value || "0");
                t.classList.toggle("vd-dim-empty", !v || v === 0 || isNaN(v));
            }
        },
        true
    );

    // ===== Copy Zalo button — click → direct clipboard write (no modal) =====
    // User spec 2026-05-29 (round 4): hover panel hiện preview, click copy ngay.
    // Phải bind capture-phase để chặn Odoo's default button handler.
    document.addEventListener(
        "click",
        async (e) => {
            const btn = e.target.closest(".o_vd_copy_zalo_btn");
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();
            const wrap = btn.closest(".o_vd_copy_zalo_wrap");
            const txtEl = wrap && wrap.querySelector(".o_vd_copy_zalo_text");
            // innerText ưu tiên vì giữ \n từ white-space:pre-wrap render
            const text = txtEl ? (txtEl.innerText || txtEl.textContent || "") : "";
            if (!text.trim()) return;
            try {
                await navigator.clipboard.writeText(text);
                const orig = btn.innerHTML;
                btn.innerHTML = '<i class="fa fa-check"></i><span>Đã copy</span>';
                btn.classList.add("o_vd_copy_zalo_btn_done");
                setTimeout(() => {
                    btn.innerHTML = orig;
                    btn.classList.remove("o_vd_copy_zalo_btn_done");
                }, 1500);
            } catch (err) {
                // Fallback: legacy execCommand (HTTPS không cần — nhưng phòng hờ)
                try {
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    ta.style.position = "fixed";
                    ta.style.opacity = "0";
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                    btn.innerHTML = '<i class="fa fa-check"></i><span>Đã copy</span>';
                    btn.classList.add("o_vd_copy_zalo_btn_done");
                    setTimeout(() => {
                        btn.innerHTML = '<i class="fa fa-clipboard"></i><span>Copy</span>';
                        btn.classList.remove("o_vd_copy_zalo_btn_done");
                    }, 1500);
                } catch (e2) {
                    console.error("Copy failed:", err, e2);
                }
            }
        },
        true
    );
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
} else {
    start();
}
