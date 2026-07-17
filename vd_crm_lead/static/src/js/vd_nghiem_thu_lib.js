/** @odoo-module **/
/**
 * THƯ VIỆN tài liệu (Hướng A+: Google Drive API).
 * 3 nút nổi (Video nghiệm thu / Công năng 3D / Hợp đồng). Popup dựng LƯỚI file từ
 * Drive (controller /vd_drive_lib/list). Thumbnail + tải đều qua proxy SAME-ORIGIN
 * (/vd_drive_lib/thumb, /vd_drive_lib/dl) → tải sạch, ẩn Google, không đơ trang.
 * NV chỉ xem/tải, không xóa (folder Drive quyền Người xem).
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";

const VD_LIBS = [
    { key: "nghiem_thu", title: "THƯ VIỆN - Video nghiệm thu", icon: "fa-film", cls: "o_vd_nt_lib_filter" },
    { key: "cong_nang_3d", title: "THƯ VIỆN - Công năng 3D", icon: "fa-cube", cls: "o_vd_cn3d_lib_filter" },
    { key: "hop_dong", title: "THƯ VIỆN - Hợp đồng", icon: "fa-file-text-o", cls: "o_vd_hd_lib_filter" },
];

export class VdDriveLibDialog extends Component {
    static template = "vd_crm_lead.DriveLibDialog";
    static components = { Dialog };
    static props = {
        libKey: String,
        libTitle: String,
        close: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({ loading: true, error: "", groups: [], tab: 0 });
        this._alive = true;
        onWillUnmount(() => { this._alive = false; });
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        try {
            const resp = await fetch(
                "/vd_drive_lib/list?key=" + encodeURIComponent(this.props.libKey),
                { credentials: "same-origin" }
            );
            const data = await resp.json();
            if (!this._alive) return;
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.groups = data.groups || [];
                this.state.tab = 0;
            }
        } catch (e) {
            if (!this._alive) return;
            console.warn("[vd_drive_lib] load lỗi:", e);
            this.state.error = "Không tải được danh sách tài liệu.";
        }
        if (this._alive) this.state.loading = false;
    }

    get curGroup() {
        return this.state.groups[this.state.tab] || null;
    }
    get curCount() {
        return this.curGroup ? this.curGroup.files.length : 0;
    }
    thumb(id) {
        return ("/vd_drive_lib/thumb?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }
    dlUrl(id) {
        return ("/vd_drive_lib/dl?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }

    // Tải TẤT CẢ file trong tab hiện tại — bấm tuần tự, giãn nhịp để trình duyệt
    // không chặn. Link same-origin nên thuộc tính download hoạt động.
    downloadAll() {
        const files = (this.curGroup && this.curGroup.files) || [];
        if (!files.length) return;
        files.forEach((f, i) => {
            setTimeout(() => {
                const a = document.createElement("a");
                a.href = this.dlUrl(f.id);
                a.download = f.name || "";
                document.body.appendChild(a);
                a.click();
                a.remove();
            }, i * 700);
        });
    }
}

// Nút nổi (field widget trên boolean stage_is_won) — render cả 3 nút.
export class VdDriveLibsButton extends Component {
    static template = "vd_crm_lead.DriveLibsButton";
    static props = { ...standardFieldProps };
    setup() {
        this.dialog = useService("dialog");
        this.libs = VD_LIBS;
    }
    get hidden() {
        return !!this.props.record.data.stage_is_won;
    }
    open(lib) {
        this.dialog.add(VdDriveLibDialog, { libKey: lib.key, libTitle: lib.title });
    }
}

registry.category("fields").add("vd_drive_libs_btn", {
    component: VdDriveLibsButton,
    supportedTypes: ["boolean"],
});
