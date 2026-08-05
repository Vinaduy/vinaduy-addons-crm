/** @odoo-module **/
/**
 * vd_num_input — ô nhập số gọn cho form khai thác (intake).
 *
 *  - Chỉ nhận CHỮ SỐ (field Integer) hoặc số có 1 dấu thập phân (field Float).
 *  - TRỐNG khi giá trị = 0 (không hiện sẵn "0,0") → gõ là ăn ngay.
 *  - Dùng useInputField (hook chuẩn Odoo) cho hiển thị: KHÔNG reset input khi
 *    đang focus/gõ dở.
 *
 *  ===== FIX MẤT DỮ LIỆU — BẢN DỨT ĐIỂM 2026-08-05 =====
 *  File này giữ ĐƯỜNG LƯU DUY NHẤT của cả bảng THÔNG TIN TƯ VẤN
 *  (__vdCommitIntakeChange / __vdSaveIntakeNow). Xem khối chú thích ở giữa file:
 *  mọi lần lưu nay là `record.save({ reload: false })` — ghi DB nhưng KHÔNG đọc
 *  lại/dựng lại form, nên không còn bất kỳ đường nào nuốt dữ liệu đang nhập.
 *  QUY TẮC: KHÔNG widget nào được gọi record.save() (mặc định có reload) hay
 *  record.load() (vứt sạch thay đổi chưa lưu) trong khu intake.
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

// ===== LƯU KHÔNG RELOAD (2026-08-05) — chấm dứt hẳn bệnh nuốt dữ liệu =====
//
// GỐC BỆNH (10 lần sửa trước không dứt): mọi đường lưu đều gọi `record.save()`
// MẶC ĐỊNH = web_save + ĐỌC LẠI toàn bộ record từ DB (`_setData`) → dựng lại
// toàn bộ field component. Bất kỳ thứ gì đang dở (chữ trong ô chưa commit, chip
// vừa bấm đang chờ onchange, dropdown đang mở) đều bị thay thế bằng dữ liệu DB
// → "chọn 2-3 trường là mất sạch" + "bấm rất khó" (DOM bị thay dưới tay NV).
// Các bản vá cũ chỉ cố ĐOÁN lúc nào an toàn để reload (guard focus/1.5s) — đoán
// sai là mất; và guard đó KHÔNG bao giờ đúng vì bấm chip = focus rơi về <body>
// nên hệ thống tưởng "NV đã nghỉ tay" và reload ngay giữa lúc thao tác.
//
// CÁCH DỨT ĐIỂM: Odoo 18 hỗ trợ `record.save({ reload: false })` — vẫn web_save
// xuống DB nhưng KHÔNG đọc lại, chỉ merge _changes vào _values và bỏ cờ dirty.
// Màn hình giữ NGUYÊN 100% những gì NV đang thấy/đang gõ. Ngoài ra `save()` và
// `update()` cùng chạy trong `model.mutex` nên KHÔNG THỂ chen vào giữa 1 lần
// update/onchange → không còn race. Vì không còn gì để mất, bỏ luôn mọi guard
// "chỉ lưu khi nghỉ tay": lưu ngay sau mỗi thao tác (gom 400ms cho đỡ RPC).
const VD_SAVE_DEBOUNCE = 400;
// Lưu hỏng (thiếu trường bắt buộc...) → lùi lại, tránh spam thông báo đỏ.
const VD_SAVE_BACKOFF = 15000;
let _vdSaveTimer = null;
let _vdInflight = null;
let _vdSaveBlockedUntil = 0;

// Lưu NGAY (không debounce) — dùng khi rời bảng / đổi KH / ẩn tab.
// Nếu đang có 1 lượt lưu chạy dở → CHỜ nó xong rồi lưu tiếp (không bỏ qua, để
// thao tác cuối cùng chắc chắn xuống DB).
export async function vdSaveIntakeNow(record, reason) {
    if (!record) return false;
    if (_vdSaveTimer) { clearTimeout(_vdSaveTimer); _vdSaveTimer = null; }
    if (_vdInflight) { try { await _vdInflight; } catch (_e) {} }
    const run = async () => {
        try {
            await vdFlushIntakeInputs("save:" + (reason || "?"));
            // reload:false = KHÔNG đọc lại từ DB → không dựng lại form → không nuốt.
            const ok = await record.save({ reload: false });
            if (ok === false) {
                // Form đang thiếu/sai trường bắt buộc → Odoo đã báo. Lùi 15s.
                _vdSaveBlockedUntil = Date.now() + VD_SAVE_BACKOFF;
                vdlog("SAVE bị từ chối (trường không hợp lệ) —", reason);
            } else {
                vdlog("ĐÃ LƯU (không reload):", reason);
            }
            return ok !== false;
        } catch (e) {
            _vdSaveBlockedUntil = Date.now() + VD_SAVE_BACKOFF;
            vdlog("save err", e);
            return false;
        }
    };
    _vdInflight = run();
    try {
        return await _vdInflight;
    } finally {
        _vdInflight = null;
    }
}
window.__vdSaveIntakeNow = vdSaveIntakeNow;

export function vdScheduleIntakeSave(record, reason) {
    if (!record) return;
    if (Date.now() < _vdSaveBlockedUntil) return;
    if (_vdSaveTimer) clearTimeout(_vdSaveTimer);
    _vdSaveTimer = setTimeout(() => {
        _vdSaveTimer = null;
        vdSaveIntakeNow(record, reason);
    }, VD_SAVE_DEBOUNCE);
}
window.__vdScheduleIntakeSave = vdScheduleIntakeSave;

// ===== 1 ĐƯỜNG LƯU CHUNG cho MỌI chip/picker intake =====
// Mọi widget (chip, picker, dropdown, ô số) chỉ gọi hàm này sau khi đã
// record.update(). Không widget nào được tự gọi record.save() — save mặc định
// (có reload) là thứ gây mất dữ liệu.
// ===== ĐÁNH DẤU "NV CHỦ ĐỘNG TẮT TRƯỜNG NÀY" =====
// Bệnh: bấm tắt 1 lựa chọn → vài giây sau bấm trường khác thì nó HIỆN LẠI, vì
// onchange bên server (móng tự theo số tầng/đất, m² tầng tự theo diện tích, tiền
// tự theo tầm tài chính) cứ thấy trường trống là tự điền — không phân biệt "chưa
// nhập" với "vừa cố ý xoá". Ghi tên field vào vd_intake_manual_off để server
// biết mà chừa ra; chọn lại giá trị thì gỡ tên khỏi danh sách.
export async function vdMarkManualOff(record, fieldName, isOff) {
    try {
        if (!record || !record.fields || !record.fields.vd_intake_manual_off) return;
        const cur = String(record.data.vd_intake_manual_off || "")
            .split(",").map((s) => s.trim()).filter(Boolean);
        const has = cur.includes(fieldName);
        if (isOff === has) return;                       // không đổi gì
        const next = isOff ? cur.concat([fieldName]) : cur.filter((f) => f !== fieldName);
        await record.update({ vd_intake_manual_off: next.join(",") });
        vdlog(isOff ? "ĐÁNH DẤU tắt tay:" : "GỠ dấu tắt tay:", fieldName);
    } catch (e) { vdlog("manual-off err", e); }
}
window.__vdMarkManualOff = vdMarkManualOff;

export function vdCommitIntakeChange(record, reason) {
    if (!record) return;
    window.__vdIntake.lastType = Date.now();
    vdScheduleIntakeSave(record, reason);
}
window.__vdCommitIntakeChange = vdCommitIntakeChange;

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
        return this.props.record.update({ [this.props.name]: val })
            // Xoá trắng ô (=0) là CỐ Ý → cấm onchange tự điền lại từ diện tích;
            // gõ số trở lại thì gỡ dấu.
            .then(() => vdMarkManualOff(this.props.record, this.props.name, val === 0))
            .catch((e) => vdlog("update err", this.props.name, e));
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
            // Lưu ngầm luôn (không reload) → số đã gõ nằm trong DB kể cả khi NV
            // chưa rời ô, chưa bấm gì thêm, hay trình duyệt sập.
            vdScheduleIntakeSave(this.props.record, "vd_num typing");
        }, 400);
    }

    // Blur/Enter: commit chắc chắn + lưu ngầm (KHÔNG reload).
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
