/** @odoo-module **/
/**
 * vd_num_input — ô nhập số gọn cho form khai thác (intake).
 *
 *  - Chỉ nhận CHỮ SỐ (field Integer) hoặc số có 1 dấu thập phân (field Float).
 *  - TRỐNG khi giá trị = 0 (không hiện sẵn "0,0") → gõ là ăn ngay.
 *  - Dùng useInputField (hook chuẩn Odoo) cho hiển thị: KHÔNG reset input khi
 *    đang focus/gõ dở.
 *
 *  ===== FIX MẤT DỮ LIỆU + GIẬT LAG (2026-06-16, vòng 2) =====
 *  Bệnh gốc: form intake gọi `record.save()` (→ RELOAD toàn form) sau MỖI thao
 *  tác (chọn picker, gõ số, +Tầng...). Reload liên tục gây:
 *    1. Mất giá trị đang gõ (reload đọc lại giá trị cũ).
 *    2. Re-render input → mất con trỏ / khó click vào ô để gõ.
 *    3. Server bận reload → nút +Tầng/+Tum/Xoá tầng (server action) phản hồi chậm.
 *  Thêm 1 race: flush (commit giá trị đang gõ) KHÔNG await trước save → save chạy
 *  trước khi giá trị kịp vào record.
 *
 *  Cách sửa DỨT ĐIỂM:
 *   A. DỒN mọi save về 1 hàm `vdScheduleIntakeSave` debounce 900ms, CHỈ thật save
 *      khi user đã NGHỈ tay (không focus trong khu nhập, không gõ < 1.5s). Chọn
 *      picker / gõ số chỉ `record.update` (cập nhật in-memory, UI đổi ngay) — KHÔNG
 *      reload giữa chừng nữa → hết mất dữ liệu, hết mất con trỏ, nút bấm nhẹ hơn.
 *   B. Flush ĐỒNG BỘ + AWAIT: `window.__vdFlushIntakeInputs()` ép mọi ô số commit
 *      giá trị đang gõ (đọc thẳng từ DOM) vào record TRƯỚC khi save.
 *
 * Gắn: <field name="..." widget="vd_num_input"/>  — backend KHÔNG đổi.
 */
import { Component, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";

// ===== Logging có thể bật/tắt — để bật khi cần soi mất dữ liệu =====
const VD_NUM_LOG = true;
function vdlog(...args) {
    if (!VD_NUM_LOG) return;
    try { console.log("%c[VD num]", "color:#2563eb;font-weight:bold", ...args); } catch (_) {}
}

// ===== Trạng thái chung khu intake =====
window.__vdIntake = window.__vdIntake || { lastType: 0 };

// Tập các instance đang sống → cho flush đồng bộ trước mỗi save.
const _vdLiveInputs = new Set();

/**
 * Ép MỌI ô số intake commit giá trị đang gõ (đọc thẳng từ DOM) vào record.
 * AWAIT-able: trả về Promise resolve khi mọi record.update xong → gọi
 * `await window.__vdFlushIntakeInputs()` TRƯỚC record.save() là chắc chắn không
 * mất giá trị in-flight.
 */
export async function vdFlushIntakeInputs(reason) {
    const proms = [];
    for (const comp of _vdLiveInputs) {
        try { const p = comp._commitNow(true); if (p) proms.push(p); } catch (e) { vdlog("flush err", e); }
    }
    if (proms.length) {
        vdlog("FLUSH", proms.length, "ô (lý do:", reason || "?", ")");
        try { await Promise.all(proms); } catch (e) { vdlog("flush await err", e); }
    }
    return proms.length;
}
window.__vdFlushIntakeInputs = vdFlushIntakeInputs;

// Lấy record intake đang mở (chia sẻ chung) từ bất kỳ ô số nào còn sống.
// Dùng cho handler client-side của nút +Tầng/+Tum/+Lửng (khỏi gọi server action
// → khỏi reload → bấm NHẸ và NHANH).
export function vdGetIntakeRecord() {
    for (const c of _vdLiveInputs) {
        if (c && c.props && c.props.record) return c.props.record;
    }
    return null;
}
window.__vdGetIntakeRecord = vdGetIntakeRecord;

// Có nên cho save (→ reload) chạy bây giờ không?
//  - Còn focus trong khu nhập / overlay dropdown → KHÔNG (sẽ reload giữa lúc nhập).
//  - User vừa gõ < 1.5s → KHÔNG (giá trị có thể chưa ổn định).
export function vdCanAutosaveIntake() {
    const since = Date.now() - (window.__vdIntake.lastType || 0);
    if (since < 1500) {
        vdlog("save HOÃN: vừa gõ", since, "ms trước");
        return false;
    }
    const ae = document.activeElement;
    if (ae && ae.closest && ae.closest(
        ".o_vd_steps_panel, .o_vd_intake_compact, .o-overlay-container, " +
        ".o_vd_selection_hover_picker, .o-autocomplete"
    )) {
        vdlog("save HOÃN: focus còn trong khu nhập/overlay");
        return false;
    }
    return true;
}

// ===== SAVE DỒN: 1 timer chung cho toàn intake (debounce 900ms, idle) =====
// Mọi nơi muốn lưu form intake → gọi vdScheduleIntakeSave thay vì record.save()
// trực tiếp. Nhờ vậy chọn/gõ liên tục KHÔNG reload từng phát; chỉ save 1 lần khi
// user nghỉ tay → UI mượt, không mất con trỏ, không mất dữ liệu.
let _vdSaveTimer = null;
export function vdScheduleIntakeSave(record, reason) {
    if (!record) return;
    if (_vdSaveTimer) clearTimeout(_vdSaveTimer);
    _vdSaveTimer = setTimeout(async () => {
        _vdSaveTimer = null;
        if (!vdCanAutosaveIntake()) {
            // Vẫn đang thao tác → khoan. Dữ liệu đã nằm trong record (in-memory),
            // lần thao tác kế hoặc blur-ra-ngoài sẽ save. Không reload cắt ngang.
            return;
        }
        await vdFlushIntakeInputs("scheduled save:" + (reason || "?"));
        try {
            await record.save();
            vdlog("SAVED (", reason, ")");
        } catch (e) { vdlog("save err", e); }
    }, 900);
}
window.__vdScheduleIntakeSave = vdScheduleIntakeSave;

export class VdNumInput extends Component {
    static template = "vd_crm_lead.VdNumInput";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.inputRef = useRef("input");
        this._commitTimer = null;
        // Hook chuẩn Odoo: tự set value từ record CHỈ khi input không dirty/không
        // focus, tự commit (record.update) lúc change. Tránh ghi đè chữ đang gõ.
        useInputField({
            getValue: () => {
                const v = this.props.record.data[this.props.name];
                return v ? String(v) : "";
            },
            refName: "input",
            parse: (value) => this._parse(value),
        });
        _vdLiveInputs.add(this);
        onWillUnmount(() => {
            _vdLiveInputs.delete(this);
            if (this._commitTimer) clearTimeout(this._commitTimer);
        });
    }

    get isInteger() {
        return this.props.record.fields[this.props.name].type === "integer";
    }

    _parse(value) {
        const s = (value || "").replace(/,/g, ".").replace(/[^0-9.]/g, "");
        if (!s) {
            return 0;
        }
        const v = this.isInteger ? parseInt(s, 10) : parseFloat(s);
        return isNaN(v) ? 0 : v;
    }

    // Commit giá trị đang hiển thị (DOM) vào record nếu khác giá trị hiện tại.
    // Trả về Promise (record.update) nếu có thay đổi, ngược lại null.
    _commitNow(sync) {
        const el = this.inputRef.el;
        if (!el) return null;
        if (this._commitTimer) { clearTimeout(this._commitTimer); this._commitTimer = null; }
        const val = this._parse(el.value);
        const curNum = this.props.record.data[this.props.name] || 0;
        if (val === curNum) return null;
        vdlog((sync ? "commit(flush)" : "commit"), this.props.name, ":", curNum, "->", val);
        return this.props.record.update({ [this.props.name]: val }).catch((e) => vdlog("update err", this.props.name, e));
    }

    // Lọc ký tự ngay khi gõ + commit sớm vào record (debounce) → không chờ blur.
    onInput(ev) {
        let s = ev.target.value || "";
        if (this.isInteger) {
            s = s.replace(/[^0-9]/g, "");
        } else {
            s = s.replace(/,/g, ".").replace(/[^0-9.]/g, "");
            const i = s.indexOf(".");
            if (i !== -1) {
                s = s.slice(0, i + 1) + s.slice(i + 1).replace(/\./g, "");
            }
        }
        if (ev.target.value !== s) {
            ev.target.value = s;
        }
        // Đánh dấu "đang gõ" để save không reload cắt ngang.
        window.__vdIntake.lastType = Date.now();
        // Commit sớm vào record (debounce 300ms) — KHÔNG đợi blur. Nhờ vậy nếu
        // có save xảy ra, record đã có giá trị mới → không mất. KHÔNG save ở đây.
        if (this._commitTimer) clearTimeout(this._commitTimer);
        this._commitTimer = setTimeout(() => {
            this._commitTimer = null;
            this._commitNow(false);
        }, 300);
    }

    // Blur/Enter: commit chắc chắn + lên lịch SAVE DỒN (idle, guarded).
    onChange() {
        this._commitNow(true);
        vdScheduleIntakeSave(this.props.record, "vd_num change");
    }
}

export const vdNumInput = {
    component: VdNumInput,
    displayName: "Ô nhập số (autosave)",
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder }),
};

registry.category("fields").add("vd_num_input", vdNumInput);
