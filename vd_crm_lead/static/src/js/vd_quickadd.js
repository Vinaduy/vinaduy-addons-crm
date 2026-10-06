/** @odoo-module **/
/**
 * THÊM KHÁCH HÀNG MỚI — popup OWL viết mới (user 2026-10-06).
 *
 * Luồng: gõ SĐT · Tên · Nguồn · Thông tin → "+" thêm vào danh sách dưới
 *   (hoặc 📤 nạp Excel → báo số trùng, chỉ hiện số KHÔNG trùng) → 💰 Chia số:
 *   chọn NV → tạo lead + chia theo danh sách. Cột Thông tin tự trỏ về trường
 *   khai thác (diện tích / số tầng T1·T2 / mẫu nhà / ngân sách) ở backend.
 *
 * Backend sạch, độc lập: crm.lead.vd_quickadd_meta / _parse_excel / _submit.
 */
import { Component, onWillStart, useState, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class VdQuickAddDialog extends Component {
    static template = "vd_crm_lead.QuickAddDialog";
    static components = { Dialog };
    static props = {
        onDone: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
        this.state = useState({
            loading: true,
            sources: [],
            nvs: [],
            rows: [],                       // {phone,name,source,info,excel}
            form: { phone: "", name: "", source: "quet", info: "" },
            picking: false,                 // đang chọn NV để chia
            selected: {},                   // {nvId: true}
            nvSearch: "",
            summary: "",                    // banner sau khi nạp Excel
            busy: false,
        });
        onWillStart(async () => {
            try {
                const meta = await this.orm.call("crm.lead", "vd_quickadd_meta", []);
                this.state.sources = meta.sources || [];
                this.state.nvs = meta.nvs || [];
                if (this.state.sources[0]) {
                    this.state.form.source = this.state.sources[0].key;
                }
            } catch (e) {
                this.notification.add("Không tải được dữ liệu popup.", { type: "danger" });
            }
            this.state.loading = false;
        });
    }

    // ---- Chỉ NV đang NHẬN số, lọc thêm theo ô tìm ----
    get nvList() {
        const q = (this.state.nvSearch || "").toLowerCase().trim();
        return this.state.nvs.filter(
            (n) => n.on && (!q || (n.name || "").toLowerCase().includes(q)));
    }
    get selectedCount() {
        return Object.values(this.state.selected).filter(Boolean).length;
    }
    sourceLabel(key) {
        const s = this.state.sources.find((x) => x.key === key);
        return s ? s.label : key;
    }

    // ---- Thêm 1 khách gõ tay vào danh sách ----
    addRow() {
        const f = this.state.form;
        const digits = (f.phone || "").replace(/\D/g, "");
        if (digits.length < 9) {
            this.notification.add("SĐT chưa hợp lệ.", { type: "warning" });
            return;
        }
        this.state.rows.push({
            phone: (f.phone || "").trim(),
            name: (f.name || "").trim(),
            source: f.source || "quet",
            info: (f.info || "").trim(),
            excel: false,
        });
        this.state.form = { phone: "", name: "", source: f.source, info: "" };
    }
    onFormKey(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addRow();
        }
    }
    removeRow(i) {
        this.state.rows.splice(i, 1);
    }

    // ---- Nạp Excel: báo trùng, chỉ nạp số KHÔNG trùng ----
    triggerFile() {
        if (this.fileInput.el) this.fileInput.el.click();
    }
    async onFile(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        this.state.busy = true;
        try {
            const b64 = await this._readB64(file);
            const r = await this.orm.call(
                "crm.lead", "vd_quickadd_parse_excel", [b64, file.name]);
            const rows = r.rows || [];
            for (const row of rows) this.state.rows.push(row);
            const parts = [`✅ Nạp ${rows.length} số mới`];
            if (r.dup) parts.push(`🔁 ${r.dup} số TRÙNG (đã bỏ)`);
            if (r.bad) parts.push(`⚠️ ${r.bad} số sai (đã bỏ)`);
            this.state.summary = parts.join(" · ");
            this.notification.add(this.state.summary, { type: rows.length ? "success" : "warning" });
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Đọc file lỗi.", { type: "danger" });
        } finally {
            this.state.busy = false;
            ev.target.value = "";
        }
    }
    _readB64(file) {
        return new Promise((resolve, reject) => {
            const fr = new FileReader();
            fr.onload = () => resolve(String(fr.result).split(",")[1] || "");
            fr.onerror = reject;
            fr.readAsDataURL(file);
        });
    }

    // ---- Chia số ----
    openPicker() {
        if (!this.state.rows.length) {
            this.notification.add("Chưa có khách nào trong danh sách.", { type: "warning" });
            return;
        }
        this.state.picking = true;
    }
    toggleNv(id) {
        this.state.selected[id] = !this.state.selected[id];
    }

    // forceAll=true → chia đều cho TẤT CẢ NV đang nhận số (bỏ qua ô chọn).
    async submit(forceAll) {
        if (this.state.busy) return;
        const ids = forceAll ? [] : Object.keys(this.state.selected)
            .filter((k) => this.state.selected[k]).map((k) => parseInt(k, 10));
        this.state.busy = true;
        try {
            const r = await this.orm.call(
                "crm.lead", "vd_quickadd_submit", [this.state.rows, ids]);
            const msg = `✅ Đã tạo & chia ${r.created} khách` +
                (r.detail ? ` → ${r.detail}` : "") +
                (r.dup ? ` · bỏ ${r.dup} trùng` : "");
            this.notification.add(msg, { type: "success" });
            if (this.props.onDone) this.props.onDone(r);
            this.props.close();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Chia số lỗi.", { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }
}
