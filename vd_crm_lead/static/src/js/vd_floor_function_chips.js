/** @odoo-module **/
/**
 * Multi-select chip widget cho "Công năng từng tầng" — UX hệt vd_timeline_chips
 * nhưng cho many2many → vd.floor.function.tag.
 *
 * Bar gọn: hiển thị chips đã chọn (hoặc placeholder) + caret. Click bar → mở
 * panel hiện TẤT CẢ tag (filter theo fit_floors khớp floor code) → click chip
 * để toggle add/remove.
 *
 * Floor code được parse từ field name:
 *   vd_intake_floor_1_function_ids → 'f1'
 *   vd_intake_floor_tum_function_ids → 'tum'
 *
 * Dùng: <field name="vd_intake_floor_1_function_ids" widget="vd_floor_function_chips"/>
 */

import { Component, useState, useRef, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";

export class VdFloorFunctionChips extends Component {
    static template = "vd_crm_lead.VdFloorFunctionChips";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false, allTags: [] });
        this.rootRef = useRef("root");

        const m = this.props.name.match(/floor_(\d+|tum)_function/);
        this.floorCode = m ? (m[1] === "tum" ? "tum" : `f${m[1]}`) : null;

        const { saveRecord, removeRecord } = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            true
        );
        this.saveRecord = saveRecord;
        this.removeRecord = removeRecord;

        this._onDocClick = (ev) => {
            if (this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };

        onWillStart(async () => {
            const tags = await this.orm.searchRead(
                "vd.floor.function.tag",
                [],
                ["id", "name", "icon", "fit_floors", "color"],
                { order: "sequence, id" }
            );
            this.state.allTags = tags.filter((t) => {
                const fit = (t.fit_floors || "all").trim();
                if (fit === "all") return true;
                return fit.split(",").map((s) => s.trim()).includes(this.floorCode);
            });
        });

        onMounted(() => document.addEventListener("click", this._onDocClick, true));
        onWillUnmount(() => document.removeEventListener("click", this._onDocClick, true));
    }

    get x2manyValue() {
        return this.props.record.data[this.props.name];
    }

    get selectedIds() {
        return new Set((this.x2manyValue?.records || []).map((r) => r.resId));
    }

    get selectedTags() {
        const sel = this.selectedIds;
        return this.state.allTags.filter((t) => sel.has(t.id));
    }

    isSelected(id) {
        return this.selectedIds.has(id);
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

    async onChipClick(tag, ev) {
        ev.stopPropagation();
        const sel = this.selectedIds;
        if (sel.has(tag.id)) {
            const rec = this.x2manyValue.records.find((r) => r.resId === tag.id);
            if (rec) await this.removeRecord(rec);
        } else {
            await this.saveRecord([tag.id]);
        }
    }

    async onRemoveSelected(tag, ev) {
        ev.stopPropagation();
        const rec = this.x2manyValue.records.find((r) => r.resId === tag.id);
        if (rec) await this.removeRecord(rec);
    }
}

export const vdFloorFunctionChipsField = {
    component: VdFloorFunctionChips,
    displayName: "Công năng tầng (chip multi-select)",
    supportedTypes: ["many2many"],
    relatedFields: () => [{ name: "name", type: "char" }],
};

registry.category("fields").add("vd_floor_function_chips", vdFloorFunctionChipsField);
