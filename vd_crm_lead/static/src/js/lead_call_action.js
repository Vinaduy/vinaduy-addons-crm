/** @odoo-module **/
/**
 * Client action `vd_stringee_call` — triggered by crm.lead.action_call()
 * when NV has stringee_user_id (Web SDK ready).
 *
 * Flow:
 *   1. Lead form button click → server action_call → returns client action
 *   2. This handler invoked với params = {phone, lead_id, lead_name}
 *   3. Calls stringee.call(phone) — service trong vd_stringee/stringee_sdk.js
 *      → khởi tạo StringeeCall2 với mic của browser → bridge tới KH PSTN
 *   4. Recording đã được handle ở SDK level
 *
 * Fallback: nếu Web SDK lỗi → notification, không break form view.
 */
import { registry } from "@web/core/registry";

async function vdStringeeCallAction(env, action) {
    console.log("[VD-STRINGEE] vd_stringee_call action invoked:", action.params);
    const phone = action.params?.phone;
    const leadName = action.params?.lead_name || "";
    if (!phone) {
        console.warn("[VD-STRINGEE] No phone in params");
        env.services.notification.add("Khách hàng chưa có số điện thoại.", {
            type: "warning",
        });
        return false;
    }
    const stringee = env.services.stringee;
    if (!stringee) {
        console.error("[VD-STRINGEE] Service NOT registered");
        env.services.notification.add("Dịch vụ Stringee chưa sẵn sàng.", {
            type: "danger",
        });
        return false;
    }
    try {
        console.log("[VD-STRINGEE] Calling stringee.call(%s)...", phone);
        const result = await stringee.call(phone);
        console.log("[VD-STRINGEE] stringee.call() returned:", result);
        env.services.notification.add(
            `Đang gọi ${leadName} (${phone})`,
            { type: "info" },
        );
    } catch (e) {
        console.error("[VD-STRINGEE] stringee.call() threw:", e);
        env.services.notification.add(
            `Gọi thất bại: ${e.message || e}`,
            { type: "danger" },
        );
    }
    return false;
}

registry.category("actions").add("vd_stringee_call", vdStringeeCallAction);

/**
 * Client action `vd_stringee_hangup` — trigger từ nút "Cúp máy" trên lead form.
 * Per Stringee Web SDK doc step 6: call.hangup(callback).
 * Cần hangup BROWSER-SIDE để WebRTC peer được đóng đúng, không chỉ server REST.
 */
async function vdStringeeHangupAction(env, _action) {
    const stringee = env.services.stringee;
    if (stringee && stringee.hangup) {
        stringee.hangup();
        env.services.notification.add("Đã cúp máy", { type: "info" });
    }
    return false;
}
registry.category("actions").add("vd_stringee_hangup", vdStringeeHangupAction);
