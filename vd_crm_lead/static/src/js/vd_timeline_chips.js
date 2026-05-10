/** @odoo-module **/
/**
 * Multi-select chip widget cho "Thời gian khởi công".
 * Stored value: Char field — comma-separated DISPLAY LABELS.
 * Vd: "Tháng 6/2026,Đầu 2027"
 *
 * Max 3 chips. Click chip = toggle.
 *
 * Dùng: <field name="vd_intake_timeline" widget="vd_timeline_chips"/>
 */

import { Component, useState } from "@odoo/owl";
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
        this.state = useState({});
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

    isSelected(label) {
        return this.selectedSet.has(label);
    }

    isMaxed() {
        return this.selectedSet.size >= MAX_PICK;
    }

    isDisabled(label) {
        return !this.isSelected(label) && this.isMaxed();
    }

    onChipClick(label) {
        const sel = this.selectedSet;
        if (sel.has(label)) {
            sel.delete(label);
        } else {
            if (sel.size >= MAX_PICK) {
                return;
            }
            sel.add(label);
        }
        // Sort selected theo thứ tự xuất hiện trong TIMELINE_OPTIONS để output ổn định
        const ordered = TIMELINE_OPTIONS.filter((o) => sel.has(o));
        this.props.record.update({ [this.props.name]: ordered.join(SEP) });
    }
}

export const vdTimelineChipsField = {
    component: VdTimelineChips,
    displayName: "Thời gian khởi công (chip multi-select)",
    supportedTypes: ["char"],
};

registry.category("fields").add("vd_timeline_chips", vdTimelineChipsField);
