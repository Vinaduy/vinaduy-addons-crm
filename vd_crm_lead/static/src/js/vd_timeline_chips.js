/** @odoo-module **/
/**
 * Multi-select chip widget cho "Thời gian khởi công" — DROPDOWN style.
 * Stored value: Char field — comma-separated DISPLAY LABELS.
 * Vd: "Tháng 6/2026,Đầu 2027"
 *
 * Mặc định: Hiển thị bar gọn (chỉ chips đã chọn). Click bar → mở danh sách.
 * Max 3 chips. Click chip = toggle.
 *
 * Dùng: <field name="vd_intake_timeline" widget="vd_timeline_chips"/>
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MAX_PICK = 3;
const SEP = ",";

// Danh sách thời gian ĐỘNG theo ngày hiện tại (tự cuộn mỗi tháng):
//  - Ẩn tháng hiện tại + tháng kế (tháng kế = "Càng sớm càng tốt").
//  - Tháng cụ thể bắt đầu từ hiện tại + 2, kéo dài 12 tháng.
// VD tháng 6/2026 -> ẩn T1..T7/2026, hiện T8/2026 .. T7/2027.
function buildTimelineOptions() {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1; // 1..12
    const out = ["Chưa xác định", "Càng sớm càng tốt"];
    let mm = m + 2;
    let yy = y;
    for (let i = 0; i < 12; i++) {
        while (mm > 12) { mm -= 12; yy += 1; }
        out.push("Tháng " + mm + "/" + yy);
        mm += 1;
    }
    return out;
}

export class VdTimelineChips extends Component {
    static template = "vd_crm_lead.VdTimelineChips";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ open: false });
        this.rootRef = useRef("root");
        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };
        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick, true));
    }

    get options() {
        return buildTimelineOptions();
    }

    selectedArray() {
        const raw = this.props.record.data[this.props.name] || "";
        return raw.split(SEP).map((s) => s.trim()).filter((s) => s.length > 0);
    }

    get selectedSet() {
        return new Set(this.selectedArray());
    }

    get selectedOrdered() {
        // Giữ nguyên thứ tự đã lưu — kể cả nhãn cũ không còn trong danh sách động.
        return this.selectedArray();
    }

    isSelected(label) {
        return this.selectedSet.has(label);
    }

    isMaxed() {
        return this.selectedSet.size >= MAX_PICK;
    }

    /** "Chưa xác định" mutex với mọi chip khác:
     *  - Đã chọn "Chưa xác định" → các chip khác disable
     *  - Đã chọn chip khác → "Chưa xác định" disable */
    isDisabled(label) {
        const sel = this.selectedSet;
        if (this.isSelected(label)) return false;
        if (label === "Chưa xác định" && sel.size > 0) return true;
        if (label !== "Chưa xác định" && sel.has("Chưa xác định")) return true;
        return this.isMaxed();
    }

    toggleOpen(ev) {
        ev.stopPropagation();
        this.state.open = !this.state.open;
    }

    onMouseEnter() {
        if (this._closeTimer) { clearTimeout(this._closeTimer); this._closeTimer = null; }
        this.state.open = true;
    }

    onMouseLeave() {
        if (this._closeTimer) clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(async () => {
            this.state.open = false;
            try { if (window.__vdFlushIntakeInputs) await window.__vdFlushIntakeInputs("timeline"); } catch (_e) {}
            try { await this.props.record.save(); } catch (_e) {}
        }, 150);
    }

    onChipClick(label, ev) {
        ev.stopPropagation();
        let arr = this.selectedArray();
        if (arr.includes(label)) {
            arr = arr.filter((x) => x !== label);
        } else {
            if (arr.length >= MAX_PICK) {
                return;
            }
            arr.push(label);
        }
        this.props.record.update({ [this.props.name]: arr.join(SEP) });
        try { if (window.__vdScheduleIntakeSave) window.__vdScheduleIntakeSave(this.props.record, "timeline"); } catch (_) {}
    }

    onRemoveSelected(label, ev) {
        ev.stopPropagation();
        const arr = this.selectedArray().filter((x) => x !== label);
        this.props.record.update({ [this.props.name]: arr.join(SEP) });
        try { if (window.__vdScheduleIntakeSave) window.__vdScheduleIntakeSave(this.props.record, "timeline rm"); } catch (_) {}
    }
}

export const vdTimelineChipsField = {
    component: VdTimelineChips,
    displayName: "Thời gian khởi công (chip multi-select dropdown)",
    supportedTypes: ["char"],
};

registry.category("fields").add("vd_timeline_chips", vdTimelineChipsField);
