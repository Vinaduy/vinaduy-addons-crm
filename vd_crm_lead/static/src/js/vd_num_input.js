/** @odoo-module **/
/**
 * vd_num_input — ô nhập số gọn cho form khai thác (intake).
 *
 *  - Chỉ nhận CHỮ SỐ (field Integer) hoặc số có 1 dấu thập phân (field Float).
 *  - TRỐNG khi giá trị = 0 (không hiện sẵn "0,0") → gõ là ăn ngay.
 *  - Dùng useInputField (hook chuẩn Odoo) cho hiển thị: KHÔNG reset input khi
 *    đang focus/gõ dở.
 *
 *  ===== FIX MẤT DỮ LIỆU (2026-06-16) =====
 *  Bug: gõ số vào ô A, bấm sang ô B (hoặc chọn Mẫu nhà / Móng) → ô A bị xoá.
 *  Nguyên nhân: useInputField CHỈ commit value vào record lúc `change`/blur.
 *  Trong khi đó picker (vd_selection_hover_picker) + autosave gọi
 *  `record.save()` NGAY → form reload từ DB. Nếu giá trị vừa gõ CHƯA kịp commit
 *  (đang "in-flight"), reload đọc lại giá trị CŨ (0) → ô trống = mất dữ liệu.
 *
 *  Cách sửa DỨT ĐIỂM:
 *   1. Commit value vào record NGAY khi gõ (debounce 250ms) — không chờ blur.
 *   2. Expose flush ĐỒNG BỘ: window.__vdFlushIntakeInputs() ép mọi ô commit
 *      pending NGAY. Mọi nơi gọi record.save() PHẢI flush trước → không còn
 *      giá trị in-flight nào bị reload nuốt mất.
 *   3. Autosave (record.save) chỉ chạy khi KHÔNG còn focus trong khu intake/
 *      overlay VÀ user đã ngừng gõ ≥ 1.5s (chống reload giữa lúc đang nhập).
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
 * Ép MỌI ô số intake commit giá trị đang gõ vào record NGAY (đồng bộ).
 * Gọi hàm này TRƯỚC mỗi record.save() để không reload nuốt giá trị in-flight.
 */
export function vdFlushIntakeInputs(reason) {
    let n = 0;
    for (const comp of _vdLiveInputs) {
        try { if (comp._commitNow(true)) n++; } catch (e) { vdlog("flush err", e); }
    }
    if (n) vdlog("FLUSH", n, "ô (lý do:", reason || "?", ")");
    return n;
}
window.__vdFlushIntakeInputs = vdFlushIntakeInputs;

// Có nên cho autosave (record.save → reload) chạy không?
//  - Còn focus trong khu nhập / overlay dropdown → KHÔNG (sẽ reload giữa lúc nhập).
//  - User vừa gõ < 1.5s → KHÔNG (giá trị có thể chưa ổn định).
export function vdCanAutosaveIntake() {
    const since = Date.now() - (window.__vdIntake.lastType || 0);
    if (since < 1500) {
        vdlog("autosave HOÃN: vừa gõ", since, "ms trước");
        return false;
    }
    const ae = document.activeElement;
    if (ae && ae.closest && ae.closest(
        ".o_vd_steps_panel, .o_vd_intake_compact, .o-overlay-container, " +
        ".o_vd_selection_hover_picker, .o-autocomplete"
    )) {
        vdlog("autosave HOÃN: focus còn trong khu nhập/overlay");
        return false;
    }
    return true;
}

// Debounce CHUNG cho autosave — chỉ thật lưu khi NV đã rời hẳn khu nhập.
let _vdNumSaveTimer = null;

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

    // Commit giá trị đang hiển thị vào record NGAY (nếu khác giá trị hiện tại).
    // Trả về true nếu có thay đổi đã commit. `sync` chỉ để log rõ nguồn gọi.
    _commitNow(sync) {
        const el = this.inputRef.el;
        if (!el) return false;
        if (this._commitTimer) { clearTimeout(this._commitTimer); this._commitTimer = null; }
        const val = this._parse(el.value);
        const cur = this.props.record.data[this.props.name];
        const curNum = cur || 0;
        if (val === curNum) return false;
        vdlog((sync ? "commit(flush)" : "commit"), this.props.name, ":", curNum, "->", val);
        this.props.record.update({ [this.props.name]: val }).catch((e) => vdlog("update err", this.props.name, e));
        return true;
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
        // Đánh dấu "đang gõ" để autosave không reload cắt ngang.
        window.__vdIntake.lastType = Date.now();
        // Commit sớm vào record (debounce 250ms) — KHÔNG đợi blur. Nhờ vậy nếu
        // có save()/reload xảy ra, record đã có giá trị mới → không mất.
        if (this._commitTimer) clearTimeout(this._commitTimer);
        this._commitTimer = setTimeout(() => {
            this._commitTimer = null;
            this._commitNow(false);
        }, 250);
    }

    // useInputField đã commit value vào record lúc change. Ở đây flush chắc chắn
    // + lên lịch autosave (có guard chống reload giữa lúc nhập).
    onChange() {
        this._commitNow(true);
        const record = this.props.record;
        if (_vdNumSaveTimer) {
            clearTimeout(_vdNumSaveTimer);
        }
        _vdNumSaveTimer = setTimeout(() => {
            _vdNumSaveTimer = null;
            if (!vdCanAutosaveIntake()) {
                return;     // vẫn đang nhập / chưa rời khu intake → khoan lưu
            }
            vdFlushIntakeInputs("vd_num autosave");
            vdlog("autosave -> record.save()");
            record.save().catch((e) => vdlog("save err", e));
        }, 600);
    }
}

export const vdNumInput = {
    component: VdNumInput,
    displayName: "Ô nhập số (autosave)",
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs }) => ({ placeholder: attrs.placeholder }),
};

registry.category("fields").add("vd_num_input", vdNumInput);
