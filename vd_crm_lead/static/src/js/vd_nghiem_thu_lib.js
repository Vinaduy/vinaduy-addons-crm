/** @odoo-module **/
/**
 * THƯ VIỆN tài liệu (Hướng A+: Google Drive API) — DUYỆT theo thư mục.
 * 3 nút nổi. Popup duyệt từng thư mục (breadcrumb): bấm folder để vào, bấm Tải ở
 * từng file. Mỗi lần chỉ gọi 1 API (nhanh, không treo server). Thumbnail + tải đều
 * qua proxy SAME-ORIGIN (/vd_drive_lib/thumb, /dl) → sạch, ẩn Google, không đơ.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillUnmount } from "@odoo/owl";

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
        // stack = breadcrumb các thư mục con đã vào [{id,name}]; rỗng = gốc.
        this.state = useState({
            loading: true, error: "", folders: [], files: [], stack: [],
        });
        this._alive = true;
        onWillUnmount(() => { this._alive = false; });
        // Mở dialog HIỆN NGAY (spinner), tải nền — KHÔNG chặn mount (tránh treo).
        this.load(null);
    }

    async load(folderId) {
        this.state.loading = true;
        this.state.error = "";
        try {
            const url = "/vd_drive_lib/list?key=" + encodeURIComponent(this.props.libKey)
                + (folderId ? "&folder=" + encodeURIComponent(folderId) : "");
            const resp = await fetch(url, { credentials: "same-origin" });
            const data = await resp.json();
            if (!this._alive) return;
            if (data.error) {
                this.state.error = data.error;
                this.state.folders = [];
                this.state.files = [];
            } else {
                this.state.folders = data.folders || [];
                this.state.files = data.files || [];
            }
        } catch (e) {
            if (!this._alive) return;
            console.warn("[vd_drive_lib] load lỗi:", e);
            this.state.error = "Không tải được danh sách tài liệu.";
        }
        if (this._alive) this.state.loading = false;
    }

    // Điều hướng thư mục
    openFolder(f) {
        this.state.stack.push({ id: f.id, name: f.name });
        this.load(f.id);
    }
    goRoot() {
        this.state.stack = [];
        this.load(null);
    }
    goCrumb(i) {
        const c = this.state.stack[i];
        this.state.stack = this.state.stack.slice(0, i + 1);
        this.load(c.id);
    }

    thumb(id) {
        return ("/vd_drive_lib/thumb?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }
    dlUrl(id) {
        return ("/vd_drive_lib/dl?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }

    // Tải TẤT CẢ file trong thư mục hiện tại (giãn nhịp; link same-origin nên
    // thuộc tính download hoạt động).
    downloadAll() {
        const files = this.state.files || [];
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
