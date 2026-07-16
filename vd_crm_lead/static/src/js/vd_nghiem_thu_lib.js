/** @odoo-module **/
/**
 * THƯ VIỆN tài liệu (Hướng A: nhúng Drive, bảo mật link).
 * Render 3 nút nổi trên form khách (giống THƯ VIỆN - Mẫu nhà): Video nghiệm thu,
 * Công năng 3D, Hợp đồng. Mỗi nút mở popup chứa iframe trỏ tới URL NỘI BỘ
 * /vd_drive_lib/embed?key=... (KHÔNG chứa link Google ở client). NV chỉ xem + tải,
 * không xóa được (quyền Drive = Người xem).
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

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
    get embedSrc() {
        return "/vd_drive_lib/embed?key=" + encodeURIComponent(this.props.libKey);
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
