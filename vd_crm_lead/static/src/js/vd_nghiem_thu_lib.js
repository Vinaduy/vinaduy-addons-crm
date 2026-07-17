/** @odoo-module **/
/**
 * THƯ VIỆN tài liệu (Hướng A+: Google Drive API) — hiện PHẲNG toàn bộ file.
 * 3 nút nổi. Popup hiện lưới TẤT CẢ file trong kho (đệ quy mọi thư mục con, quét
 * song song + cache ở server). Video có ảnh xem trước; tài liệu (pdf/word) dùng
 * icon. Mỗi file 1 thẻ: tên + nút Tải cùng 1 dòng. Tải/thumb qua proxy same-origin.
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
        this.state = useState({ loading: true, error: "", groups: [] });
        this._alive = true;
        onWillUnmount(() => { this._alive = false; });
        this.load();
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const resp = await fetch(
                "/vd_drive_lib/list?key=" + encodeURIComponent(this.props.libKey),
                { credentials: "same-origin" });
            const data = await resp.json();
            if (!this._alive) return;
            if (data.error) {
                this.state.error = data.error;
                this.state.groups = [];
            } else {
                this.state.groups = data.groups || [];
            }
        } catch (e) {
            if (!this._alive) return;
            console.warn("[vd_drive_lib] load lỗi:", e);
            this.state.error = "Không tải được danh sách tài liệu.";
        }
        if (this._alive) this.state.loading = false;
    }

    get allFiles() {
        return (this.state.groups || []).flatMap((g) => g.files || []);
    }
    // File cần xem trước (video/ảnh) -> thẻ có thumbnail; còn lại là tài liệu.
    openUrl(id) {
        return "https://drive.google.com/file/d/" + id + "/view";
    }
    openFile(id) {
        window.open(this.openUrl(id), "_blank", "noopener");
    }

    // Loại tài liệu Google có thể "Tạo bản sao" để điền (Word/Excel/PowerPoint/GDoc).
    docKind(f) {
        const m = f.mime || "";
        if (m.includes("presentation")) return "presentation";
        if (m.includes("spreadsheet") || m.includes("excel")) return "spreadsheets";
        if (m.includes("wordprocessing") || m.includes("vnd.google-apps.document")) return "document";
        return null;
    }
    canCopy(f) {
        return !!this.docKind(f);
    }
    // URL "Tạo bản sao": ÉP qua màn đăng nhập/chọn tài khoản Google rồi tới lệnh
    // /copy (bản sao vào Drive cá nhân của NV -> mỗi NV 1 bản, không đụng bản gốc).
    copyUrl(f) {
        const kind = this.docKind(f);
        if (!kind) return "";
        const target = "https://docs.google.com/" + kind + "/d/" + f.id + "/copy";
        return "https://accounts.google.com/AccountChooser?continue="
            + encodeURIComponent(target);
    }

    hasThumb(f) {
        const m = f.mime || "";
        return m.startsWith("video/") || m.startsWith("image/");
    }
    fileIcon(f) {
        const m = f.mime || "";
        if (m.startsWith("video/")) return "fa-file-video-o";
        if (m.startsWith("image/")) return "fa-file-image-o";
        if (m.includes("pdf")) return "fa-file-pdf-o";
        if (m.includes("word") || m.includes("document")) return "fa-file-word-o";
        if (m.includes("sheet") || m.includes("excel")) return "fa-file-excel-o";
        if (m.includes("presentation") || m.includes("powerpoint")) return "fa-file-powerpoint-o";
        return "fa-file-o";
    }
    thumb(id) {
        return ("/vd_drive_lib/thumb?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }
    dlUrl(id) {
        return ("/vd_drive_lib/dl?key=" + encodeURIComponent(this.props.libKey)
            + "&id=" + encodeURIComponent(id));
    }

    downloadAll() {
        const files = this.allFiles;
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
        this._open = false;
    }
    get hidden() {
        return !!this.props.record.data.stage_is_won;
    }
    open(lib) {
        if (this._open) return;   // chống mở nhiều popup
        this._open = true;
        this.dialog.add(VdDriveLibDialog,
            { libKey: lib.key, libTitle: lib.title },
            { onClose: () => { this._open = false; } });
    }
}

registry.category("fields").add("vd_drive_libs_btn", {
    component: VdDriveLibsButton,
    supportedTypes: ["boolean"],
});
