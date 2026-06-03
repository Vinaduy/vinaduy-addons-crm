/** @odoo-module **/
/**
 * Popup thông báo cuộc gọi — NỔI BẬT, căn giữa trên cùng màn hình.
 *
 * Thay cho toast nhỏ ở góc: mọi thông báo liên quan cuộc gọi đi (không có số
 * cùng mạng / cấm gọi ngoại mạng / số chết / khách bận / không nghe...) hiện
 * ở đây cho NV thấy rõ. Nguồn dữ liệu: reactive state của `stringee` service.
 *
 * - danger: giữ tới khi NV bấm đóng.
 * - warning/info/success: tự tắt sau vài giây (cấu hình trong showCallAlert).
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const ICON = {
    danger: "fa-exclamation-triangle",
    warning: "fa-exclamation-circle",
    info: "fa-info-circle",
    success: "fa-check-circle",
};

export class VdCallAlert extends Component {
    static template = "vd_stringee.CallAlert";
    static props = {};

    setup() {
        this.stringee = useService("stringee");
        this.s = useState(this.stringee.state);
    }

    get iconClass() {
        return ICON[this.s.alertLevel] || ICON.info;
    }

    onClose() {
        this.stringee.hideCallAlert();
    }
}

registry.category("main_components").add("vd_stringee.CallAlert", {
    Component: VdCallAlert,
});
