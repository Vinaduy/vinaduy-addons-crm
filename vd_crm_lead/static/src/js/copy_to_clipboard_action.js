/** @odoo-module **/
/**
 * Client action `vd_copy_to_clipboard` — opens a preview dialog with the text
 * and a Copy button. Copy click → writes to clipboard.
 *
 * Why dialog instead of immediate clipboard write?
 * - navigator.clipboard.writeText() có thể bị browser block nếu user-gesture
 *   không rõ ràng (vd: server action chain). Hiện popup + nút Copy trong popup
 *   = fresh user click → clipboard luôn cho phép.
 * - User cần XEM trước khi copy để biết đang gửi gì.
 */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class VdCopyPreviewDialog extends Component {
    static template = "vd_crm_lead.CopyPreviewDialog";
    static components = { Dialog };
    static props = {
        text: String,
        message: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.notification = useService("notification");
    }

    async onCopy() {
        const text = this.props.text || "";
        let ok = false;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                ok = true;
            }
        } catch (_e) {
            ok = false;
        }
        if (!ok) {
            // Fallback: select textarea + execCommand
            const ta = document.getElementById("vd_copy_preview_ta");
            if (ta) {
                ta.select();
                try {
                    ok = document.execCommand("copy");
                } catch (_e) { /* noop */ }
            }
        }
        if (ok) {
            this.notification.add(
                this.props.message || "Đã copy vào clipboard. Dán vào Zalo!",
                { type: "success" },
            );
            this.props.close();
        } else {
            this.notification.add(
                "Trình duyệt không cho copy tự động. Bôi đen text + Ctrl+C / Cmd+C để copy thủ công.",
                { type: "warning", sticky: true },
            );
        }
    }

    onCancel() {
        this.props.close();
    }
}

async function vdCopyToClipboard(env, action) {
    const text = action.params?.text || "";
    if (!text) {
        env.services.notification.add("Không có nội dung để copy", { type: "warning" });
        return false;
    }
    env.services.dialog.add(VdCopyPreviewDialog, {
        text: text,
        message: action.params?.message || "",
    });
    return false;  // Không navigate
}

registry.category("actions").add("vd_copy_to_clipboard", vdCopyToClipboard);
