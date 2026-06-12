/** @odoo-module **/
/**
 * Hộp thư hội thoại Facebook — giao diện kiểu PANCAKE (3 cột):
 *   TRÁI  : danh sách hội thoại (avatar, tên, tin cuối, giờ, badge chưa đọc)
 *   GIỮA  : khung chat bong bóng (khách = trái/xám, page = phải/xanh) + ô soạn tin
 *   PHẢI  : thông tin khách (tên, PSID, page, KH/CRM, trạng thái)
 *
 * Dữ liệu lấy thẳng qua ORM (vd.fb.conversation / vd.fb.message). Tự poll mỗi
 * 7s để tin nhắn webhook mới hiện live — tiện quay video Facebook App Review.
 */
import { Component, onMounted, onWillStart, onWillUnmount, onPatched, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

const CONV_FIELDS = [
    "customer_name", "snippet", "last_message_at", "last_inbound_at",
    "unread", "state", "platform", "page_id", "psid", "lead_id", "user_id",
];
const MSG_FIELDS = ["direction", "body", "sent_at", "attachment_url", "attachment_type", "send_error"];
const POLL_MS = 7000;

export class VdFbChat extends Component {
    static template = "vd_crm_lead.FbChat";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.streamRef = useRef("stream");
        this._needScroll = false;

        this.state = useState({
            loading: true,
            pages: [],
            pageFilter: null,        // id page đang lọc | null = tất cả
            conversations: [],
            activeId: null,
            messages: [],
            replyText: "",
            sending: false,
            isAdmin: false,
        });

        onWillStart(async () => {
            this.state.isAdmin = await user.hasGroup("vd_crm_lead.vd_crm_group_admin");
            this.state.pages = await this.orm.searchRead("vd.fb.page", [], ["name", "platform"]);
            await this.loadConversations();
            this.state.loading = false;
        });

        onMounted(() => {
            this._poll = browser.setInterval(() => this.poll(), POLL_MS);
        });
        onWillUnmount(() => {
            if (this._poll) browser.clearInterval(this._poll);
        });
        onPatched(() => {
            if (this._needScroll && this.streamRef.el) {
                this.streamRef.el.scrollTop = this.streamRef.el.scrollHeight;
                this._needScroll = false;
            }
        });
    }

    // ---------- Tải dữ liệu ----------
    get convDomain() {
        return this.state.pageFilter ? [["page_id", "=", this.state.pageFilter]] : [];
    }

    async loadConversations() {
        this.state.conversations = await this.orm.searchRead(
            "vd.fb.conversation", this.convDomain, CONV_FIELDS,
            { order: "last_message_at desc, id desc", limit: 200 },
        );
        // giữ lựa chọn cũ nếu còn, nếu không chọn hội thoại đầu
        if (!this.state.conversations.some((c) => c.id === this.state.activeId)) {
            this.state.activeId = this.state.conversations.length
                ? this.state.conversations[0].id : null;
            if (this.state.activeId) await this.loadMessages();
            else this.state.messages = [];
        }
    }

    async loadMessages() {
        if (!this.state.activeId) {
            this.state.messages = [];
            return;
        }
        this.state.messages = await this.orm.searchRead(
            "vd.fb.message", [["conversation_id", "=", this.state.activeId]], MSG_FIELDS,
            { order: "sent_at asc, id asc", limit: 500 },
        );
        this._needScroll = true;
    }

    async poll() {
        if (this.state.sending) return;
        const prevCount = this.state.messages.length;
        await this.loadConversations();
        if (this.state.activeId) {
            await this.loadMessages();
            if (this.state.messages.length > prevCount) this._needScroll = true;
        }
    }

    // ---------- Tương tác ----------
    get activeConv() {
        return this.state.conversations.find((c) => c.id === this.state.activeId) || null;
    }

    async selectConv(id) {
        if (this.state.activeId === id) return;
        this.state.activeId = id;
        await this.loadMessages();
        const conv = this.activeConv;
        if (conv && conv.unread) {
            await this.orm.call("vd.fb.conversation", "action_mark_read", [[id]]);
            conv.unread = 0;
        }
    }

    async setPageFilter(val) {
        this.state.pageFilter = val ? parseInt(val, 10) : null;
        this.state.activeId = null;
        await this.loadConversations();
    }

    onKeydown(ev) {
        // Enter gửi, Shift+Enter xuống dòng
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendReply();
        }
    }

    async sendReply() {
        const text = (this.state.replyText || "").trim();
        if (!text || !this.state.activeId || this.state.sending) return;
        this.state.sending = true;
        try {
            const res = await this.orm.call("vd.fb.conversation", "post_reply", [
                [this.state.activeId], text,
            ]);
            this.state.replyText = "";
            await this.loadMessages();
            await this.loadConversations();
            if (res && typeof res === "object" && res.error) {
                this.notification.add("Gửi thất bại: " + res.error, { type: "warning" });
            }
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || "Lỗi gửi tin", { type: "danger" });
        } finally {
            this.state.sending = false;
        }
    }

    async markDone() {
        if (!this.state.activeId) return;
        await this.orm.call("vd.fb.conversation", "action_mark_done", [[this.state.activeId]]);
        await this.loadConversations();
    }

    async simulateInbound() {
        if (!this.state.activeId) return;
        await this.orm.call("vd.fb.conversation", "action_simulate_inbound", [[this.state.activeId]]);
        await this.loadMessages();
        await this.loadConversations();
    }

    openLead() {
        const conv = this.activeConv;
        if (!conv || !conv.lead_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: conv.lead_id[0],
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ---------- Helpers hiển thị ----------
    initial(name) {
        const s = (name || "?").trim();
        return s ? s[0].toUpperCase() : "?";
    }

    fmtTime(dt) {
        // dt dạng "YYYY-MM-DD HH:MM:SS" (UTC từ ORM) → "HH:MM"
        if (!dt) return "";
        const s = String(dt);
        const m = s.match(/(\d{2}):(\d{2})/);
        return m ? `${m[1]}:${m[2]}` : "";
    }

    convName(c) {
        return c.customer_name || c.psid || "Khách";
    }
}

registry.category("actions").add("vd_crm_lead.fb_chat", VdFbChat);
