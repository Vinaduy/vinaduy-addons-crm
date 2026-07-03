/** @odoo-module **/
/**
 * vd_media_field — widget tải ảnh/video cho Chiến dịch Spam Zalo (trang cấu hình).
 *
 *  - Tải HÀNG LOẠT: chọn nhiều file cùng lúc, mỗi file 1 thanh tiến trình riêng.
 *  - Tải xong TỰ HIỆN ngay (không cần reload trang), phát video trực tiếp <video controls>.
 *  - Xoá từng file (nút X).
 *
 *  Cơ chế: upload qua controller /vd_broadcast/upload (multipart, có progress qua
 *  XHR) → tạo ir.attachment gắn m2m → RPC vd_media_list/unlink để đồng bộ.
 *
 *  Gắn: <field name="attachment_ids" widget="vd_media_field"/>
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class VdMediaField extends Component {
    static template = "vd_crm_lead.VdMediaField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        // items: [{id,name,kind,url,src}], uploads: [{key,name,progress,error}]
        this.state = useState({ items: [], uploads: [], loading: true });
        this._uploadKey = 0;
        onWillStart(async () => {
            await this._reload();
        });
    }

    get campaignId() {
        return this.props.record.resId;
    }
    get isSaved() {
        return !!this.campaignId;
    }

    async _reload() {
        if (!this.isSaved) {
            this.state.items = [];
            this.state.loading = false;
            return;
        }
        try {
            const list = await this.orm.call(
                "vd.broadcast.campaign", "vd_media_list", [this.campaignId]);
            this.state.items = list || [];
        } catch (_e) {
            this.state.items = [];
        }
        this.state.loading = false;
    }

    // Chọn file (1 hoặc nhiều) → tải song song, mỗi file 1 progress.
    onFilesSelected(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";  // cho phép chọn lại cùng file
        if (!this.isSaved) {
            this.notification.add(
                "Vui lòng LƯU chiến dịch trước khi tải ảnh/video.", { type: "warning" });
            return;
        }
        for (const file of files) {
            this._uploadOne(file);
        }
    }

    _uploadOne(file) {
        const key = ++this._uploadKey;
        this.state.uploads.push({ key, name: file.name, progress: 0, error: false });
        const up = () => this.state.uploads.find((u) => u.key === key);

        const fd = new FormData();
        fd.append("campaign_id", this.campaignId);
        fd.append("ufile", file);
        fd.append("csrf_token", odoo.csrf_token);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/vd_broadcast/upload", true);
        xhr.upload.onprogress = (e) => {
            const u = up();
            if (u && e.lengthComputable) {
                u.progress = Math.round((e.loaded / e.total) * 100);
            }
        };
        xhr.onload = async () => {
            const u = up();
            let ok = false;
            try {
                const res = JSON.parse(xhr.responseText || "{}");
                if (xhr.status === 200 && res.attachments) {
                    ok = true;
                    // Thêm ngay vào danh sách (tự hiện, phát được luôn).
                    for (const a of res.attachments) {
                        this.state.items.push(a);
                    }
                } else if (res.error) {
                    this.notification.add(res.error, { type: "danger" });
                }
            } catch (_e) { /* parse fail */ }
            // Bỏ entry progress khỏi danh sách đang tải.
            this.state.uploads = this.state.uploads.filter((x) => x.key !== key);
            if (!ok) {
                this.notification.add("Tải lên thất bại: " + file.name, { type: "danger" });
            }
        };
        xhr.onerror = () => {
            this.state.uploads = this.state.uploads.filter((x) => x.key !== key);
            this.notification.add("Lỗi mạng khi tải: " + file.name, { type: "danger" });
        };
        xhr.send(fd);
    }

    async removeItem(item) {
        if (!this.isSaved) return;
        try {
            const list = await this.orm.call(
                "vd.broadcast.campaign", "vd_media_unlink",
                [this.campaignId, item.id]);
            this.state.items = list || [];
        } catch (_e) {
            this.notification.add("Xoá thất bại.", { type: "danger" });
        }
    }
}

export const vdMediaField = {
    component: VdMediaField,
    displayName: "Tải ảnh/video (progress + xem trực tiếp)",
    supportedTypes: ["many2many"],
};

registry.category("fields").add("vd_media_field", vdMediaField);
