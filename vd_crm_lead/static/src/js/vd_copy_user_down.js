/** @odoo-module **/
/**
 * Nút "Sao chép giá trị cột này XUỐNG các dòng dưới" cho wizard Thêm KH mới.
 * Client-side: KHÔNG cần lưu — copy thẳng vào các dòng đã nhập (có tên) ngay.
 * Dùng cho cột Nhân viên (user_id) + cột Nguồn (source) qua option {'field': ...}.
 * User spec 2026-06-10.
 */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

class VdCopyDown extends Component {
    static template = "vd_crm_lead.CopyDown";
    static props = {
        ...standardFieldProps,
        copyField: { type: String, optional: true },
        batchN: { type: Number, optional: true },
    };

    setup() {
        this.notification = useService("notification");
    }

    get _field() {
        return this.props.copyField || "user_id";
    }
    get batchN() {
        return this.props.batchN || 5;
    }
    get hasValue() {
        return !!this.props.record.data[this._field];
    }

    async onCopyDown() {
        const rec = this.props.record;
        const f = this._field;
        const val = rec.data[f];
        if (!val) return;
        const list = rec.model.root.data.line_ids;
        const records = (list && list.records) || [];
        const myIdx = records.findIndex((r) => r.id === rec.id);
        if (myIdx < 0) return;
        let count = 0;
        for (let i = myIdx + 1; i < records.length; i++) {
            const r = records[i];
            if (r.data && r.data.name) {
                try {
                    await r.update({ [f]: val });
                    count++;
                } catch (e) {
                    console.warn("copy down failed", e);
                }
            }
        }
        this.notification.add(
            count
                ? `Đã sao chép xuống ${count} khách bên dưới.`
                : "Chưa có khách (đã nhập tên) ở các dòng dưới để sao chép.",
            { type: count ? "success" : "warning" },
        );
    }

    // Gán giá trị (NV) cho ĐÚNG batchN khách: dòng này + (batchN-1) dòng dưới
    // có nhập tên. user spec 2026-06-25 ("1 NV cho 5 khách").
    async onCopyDownN() {
        const rec = this.props.record;
        const f = this._field;
        const val = rec.data[f];
        if (!val) return;
        const list = rec.model.root.data.line_ids;
        const records = (list && list.records) || [];
        const myIdx = records.findIndex((r) => r.id === rec.id);
        if (myIdx < 0) return;
        let filled = 1; // dòng hiện tại đã có NV
        for (let i = myIdx + 1; i < records.length && filled < this.batchN; i++) {
            const r = records[i];
            if (r.data && r.data.name) {
                try {
                    await r.update({ [f]: val });
                    filled++;
                } catch (e) {
                    console.warn("copy down N failed", e);
                }
            }
        }
        this.notification.add(
            `Đã gán NV này cho ${filled} khách (dòng này + ${filled - 1} dưới).`,
            { type: "success" },
        );
    }
}

registry.category("fields").add("vd_copy_down", {
    component: VdCopyDown,
    extractProps: ({ options }) => ({
        copyField: (options && options.field) || "user_id",
        batchN: (options && options.batch) || 5,
    }),
    supportedOptions: [
        { label: "Field to copy", name: "field", type: "string" },
        { label: "Batch size", name: "batch", type: "number" },
    ],
});
