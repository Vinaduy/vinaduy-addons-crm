/** @odoo-module **/
/**
 * INTAKE CLOSE GUARD — hiển thị modal cảnh báo khi NV đóng form lead chưa CHỐT.
 *
 * Trigger: FormController.beforeLeave (Odoo 18) — gọi khi user navigate đi đâu
 * khác (back, switch lead, breadcrumb, X close). Trả về Promise<boolean>:
 *   - true  → cho phép leave
 *   - false → block, ở lại form
 *
 * Modal có 3 nút:
 *   ✓ CHỐT THÔNG TIN  → gọi action_save_intake_done (validate đủ 11 trường rồi lock)
 *   🗑 Huỷ bỏ (wipe)   → gọi action_vd_wipe_intake_data → cho leave
 *   ← Quay lại        → ở lại form, không leave
 */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, xml, useState } from "@odoo/owl";

class VdIntakeCloseDialog extends Component {
    static components = { Dialog };
    static props = {
        leadName: { type: String, optional: true },
        onChot: Function,
        onWipe: Function,
        onBack: Function,
        close: Function,  // injected by dialog service
    };
    static template = xml/* xml */`
        <Dialog title="'⚠ Bạn chưa CHỐT THÔNG TIN'" size="'md'" footer="false">
            <div class="o_vd_intake_close_guard">
                <div class="o_vd_icg_msg">
                    <p><b t-esc="props.leadName"/></p>
                    <p>Bạn đã nhập thông tin tư vấn nhưng <b>chưa bấm CHỐT THÔNG TIN</b>.</p>
                    <p class="text-danger">
                        Nếu chọn <b>Huỷ bỏ</b>, toàn bộ dữ liệu khai thác sẽ bị xoá ngay.
                        Sau 15 phút im lặng, dữ liệu cũng tự xoá.
                    </p>
                    <p>Bạn muốn làm gì?</p>
                </div>
                <div class="o_vd_icg_actions">
                    <button type="button" class="btn btn-success" t-on-click="onChot" t-att-disabled="state.busy">
                        <i class="fa fa-lock me-1"/> CHỐT THÔNG TIN
                    </button>
                    <button type="button" class="btn btn-outline-danger" t-on-click="onWipe" t-att-disabled="state.busy">
                        <i class="fa fa-trash me-1"/> Huỷ bỏ (xoá dữ liệu)
                    </button>
                    <button type="button" class="btn btn-secondary" t-on-click="onBack" t-att-disabled="state.busy">
                        <i class="fa fa-arrow-left me-1"/> Quay lại
                    </button>
                </div>
            </div>
        </Dialog>
    `;

    setup() {
        this.state = useState({ busy: false });
    }

    async _safe(action) {
        if (this.state.busy) return;
        this.state.busy = true;
        try {
            await action();
        } finally {
            this.state.busy = false;
            this.props.close();
        }
    }

    onChot() { this._safe(this.props.onChot); }
    onWipe() { this._safe(this.props.onWipe); }
    onBack() {
        this.props.onBack();
        this.props.close();
    }
}

// Các field intake để check xem record có data không (subset đại diện)
const VD_INTAKE_SIGNAL_FIELDS = [
    "vd_intake_province_id",
    "vd_intake_timeline",
    "vd_intake_total_m2",
    "vd_intake_house_type",
    "vd_intake_foundation_type",
    "vd_intake_land_type",
    "vd_intake_soil_dump",
    "vd_intake_car_access_select",
    "vd_intake_budget_range",
    "vd_intake_dimensions",
    "vd_intake_floor_1_m2",
];

function _hasAnyIntakeData(data) {
    for (const f of VD_INTAKE_SIGNAL_FIELDS) {
        const v = data && data[f];
        if (!v) continue;
        if (Array.isArray(v)) {
            if (v.length > 0) return true;
        } else if (typeof v === "object") {
            if (v.id || v.resId) return true;
        } else if (typeof v === "number") {
            if (v > 0) return true;
        } else {
            return true;
        }
    }
    return false;
}

patch(FormController.prototype, {
    async beforeLeave() {
        const blocked = await this._vdIntakeGuardCheck();
        if (blocked === false) return false;
        return super.beforeLeave(...arguments);
    },

    /**
     * @returns {Promise<boolean>} false = block leave, true/undefined = allow
     */
    async _vdIntakeGuardCheck() {
        const record = this.model && this.model.root;
        if (!record) return true;
        if (record.resModel !== "crm.lead") return true;
        const d = record.data || {};
        if (d.vd_intake_locked) return true;
        if (!_hasAnyIntakeData(d)) return true;

        const dialogService = this.env.services.dialog;
        const orm = this.env.services.orm;
        const resId = record.resId;
        if (!resId || !dialogService || !orm) return true;

        const leadName = d.name || d.partner_name || d.contact_name || "Khách hàng";
        return await new Promise((resolve) => {
            let resolved = false;
            const safeResolve = (v) => { if (!resolved) { resolved = true; resolve(v); } };
            dialogService.add(VdIntakeCloseDialog, {
                leadName: leadName,
                onChot: async () => {
                    try {
                        await orm.call("crm.lead", "action_save_intake_done", [[resId]]);
                        safeResolve(true);
                    } catch (e) {
                        console.error("[vd_intake_close_guard] CHỐT failed:", e);
                        safeResolve(false);
                    }
                },
                onWipe: async () => {
                    try {
                        await orm.call("crm.lead", "action_vd_wipe_intake_data", [[resId]]);
                        try { await record.load(); } catch (_) {}
                        safeResolve(true);
                    } catch (e) {
                        console.error("[vd_intake_close_guard] WIPE failed:", e);
                        safeResolve(true);
                    }
                },
                onBack: () => safeResolve(false),
            }, {
                onClose: () => safeResolve(false),
            });
        });
    },
});
