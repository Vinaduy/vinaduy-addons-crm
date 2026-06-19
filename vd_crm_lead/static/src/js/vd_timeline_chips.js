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

const TIMELINE_OPTIONS = [
    "Chưa xác định",
    "Càng sớm càng tốt",
    "Tháng 5/2026",
    "Tháng 6/2026",
    "Tháng 7/2026",
    "Tháng 8/2026",
    "Tháng 9/2026",
    "Tháng 10/2026",
    "Tháng 11/2026",
    "Tháng 12/2026",
    "Đầu 2027",
    "Giữa 2027",
    "Cuối 2027",
];

const MAX_PICK = 3;
const SEP = ",";

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
        return TIMELINE_OPTIONS;
    }

    get selectedSet() {
        const raw = this.props.record.data[this.props.name] || "";
        return new Set(
            raw.split(SEP).map((s) => s.trim()).filter((s) => s.length > 0)
        );
    }

    get selectedOrdered() {
        const sel = this.selectedSet;
        return TIMELINE_OPTIONS.filter((o) => sel.has(o));
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
        this._closeTimer = setTimeout(() => { this.state.open = false; }, 150);
    }

    onChipClick(label, ev) {
        ev.stopPropagation();
        const sel = this.selectedSet;
        if (sel.has(label)) {
            sel.delete(label);
        } else {
            if (sel.size >= MAX_PICK) {
                return;
            }
            sel.add(label);
        }
        const ordered = TIMELINE_OPTIONS.filter((o) => sel.has(o));
        this.props.record.update({ [this.props.name]: ordered.join(SEP) });
        // SAVE DỒN (idle) — không reload từng phát.
        try { if (window.__vdScheduleIntakeSave) window.__vdScheduleIntakeSave(this.props.record, "timeline"); } catch (_) {}
    }

    onRemoveSelected(label, ev) {
        ev.stopPropagation();
        const sel = this.selectedSet;
        sel.delete(label);
        const ordered = TIMELINE_OPTIONS.filter((o) => sel.has(o));
        this.props.record.update({ [this.props.name]: ordered.join(SEP) });
        try { if (window.__vdScheduleIntakeSave) window.__vdScheduleIntakeSave(this.props.record, "timeline rm"); } catch (_) {}
    }
}

export const vdTimelineChipsField = {
    component: VdTimelineChips,
    displayName: "Thời gian khởi công (chip multi-select dropdown)",
    supportedTypes: ["char"],
};

registry.category("fields").add("vd_timeline_chips", vdTimelineChipsField);
