/** @odoo-module **/
/**
 * THƯ VIỆN - Mẫu nhà thiết kế.
 * Nút nổi trên form khách hàng (giống THƯ VIỆN câu hỏi khó) → mở popup:
 *  - Tab NHÓM (Nhà cấp 4 / 2 / 3 / 4 tầng) + tab con KIỂU (Vuông hiện đại,
 *    Mái Nhật/Thái/Pháp, Tân cổ điển) → lưới ảnh.
 *  - NV: bấm 1 ảnh để chọn (bôi đen), Copy 1 ảnh (dán Zalo), hoặc Tải nhiều ảnh đã chọn.
 *  - Admin/quản lý: tải ảnh hàng loạt lên album đang xem + xoá ảnh đã chọn.
 *
 * LƯU Ý kỹ thuật: clipboard CHỈ giữ 1 ảnh/lần → "copy nhiều ảnh dán 1 lượt" vào
 * Zalo là KHÔNG thể. Nhiều ảnh → Tải về rồi kéo/đính kèm vào Zalo.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, useState } from "@odoo/owl";

function readAsBase64(file) {
    return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => {
            const s = String(r.result || "");
            const i = s.indexOf(",");
            resolve(i >= 0 ? s.slice(i + 1) : s);
        };
        r.onerror = reject;
        r.readAsDataURL(file);
    });
}

export class VdHouseLibDialog extends Component {
    static template = "vd_crm_lead.HouseLibDialog";
    static components = { Dialog };
    static props = { close: { type: Function, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            isAdmin: false,
            categories: [],
            cat: null,
            style: null,
            images: [],
            selected: {},
            uploading: false,
        });
        onWillStart(async () => {
            const d = await this.orm.call("vd.house.design", "vd_house_tabs", []);
            this.state.isAdmin = !!(d && d.is_admin);
            this.state.categories = (d && d.categories) || [];
            const c0 = this.state.categories[0];
            if (c0) {
                this.state.cat = c0.key;
                this.state.style = (c0.styles[0] || {}).key || null;
                await this.loadImages();
            }
            this.state.loading = false;
        });
    }

    get curCat() {
        return this.state.categories.find((c) => c.key === this.state.cat) || null;
    }
    get selCount() {
        return Object.keys(this.state.selected).length;
    }
    imgUrl(id) {
        return `/web/image/vd.house.design/${id}/image/240x240`;
    }

    async selectCat(ck) {
        this.state.cat = ck;
        const c = this.curCat;
        this.state.style = (c && c.styles[0] && c.styles[0].key) || null;
        await this.loadImages();
    }
    async selectStyle(sk) {
        this.state.style = sk;
        await this.loadImages();
    }
    async loadImages() {
        this.state.selected = {};
        if (!this.state.cat || !this.state.style) {
            this.state.images = [];
            return;
        }
        this.state.images = await this.orm.call(
            "vd.house.design", "vd_house_list", [this.state.cat, this.state.style]);
    }
    async reloadTabsKeepPos() {
        const d = await this.orm.call("vd.house.design", "vd_house_tabs", []);
        this.state.categories = (d && d.categories) || [];
        await this.loadImages();
    }

    toggleSel(id) {
        const s = { ...this.state.selected };
        if (s[id]) { delete s[id]; } else { s[id] = true; }
        this.state.selected = s;
    }
    isSel(id) {
        return !!this.state.selected[id];
    }

    async copyOne(id) {
        try {
            const resp = await fetch(`/web/image/vd.house.design/${id}/image`);
            const blob = await resp.blob();
            // Chuyển sang PNG bằng canvas để clipboard nhận (Zalo dán được).
            const bmp = await createImageBitmap(blob);
            const cv = document.createElement("canvas");
            cv.width = bmp.width; cv.height = bmp.height;
            cv.getContext("2d").drawImage(bmp, 0, 0);
            const png = await new Promise((r) => cv.toBlob(r, "image/png"));
            await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
            this.notification.add("Đã copy ảnh — dán (Ctrl+V) vào Zalo để gửi.", { type: "success" });
        } catch (e) {
            console.warn("Copy ảnh lỗi:", e);
            this.notification.add("Trình duyệt chặn copy ảnh. Hãy dùng nút Tải về.", { type: "warning" });
        }
    }

    downloadSelected() {
        const ids = Object.keys(this.state.selected);
        if (!ids.length) {
            this.notification.add("Chưa chọn ảnh nào (bấm vào ảnh để chọn).", { type: "warning" });
            return;
        }
        ids.forEach((id, i) => {
            setTimeout(() => {
                const a = document.createElement("a");
                a.href = `/web/content/vd.house.design/${id}/image?download=true&filename=mau_nha_${id}.jpg`;
                a.download = `mau_nha_${id}.jpg`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }, i * 250);
        });
        this.notification.add(`Đang tải ${ids.length} ảnh — kéo/đính kèm vào Zalo để gửi.`, { type: "success" });
    }

    async onPickFiles(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";
        if (!files.length) return;
        this.state.uploading = true;
        try {
            // Tải theo lô 6 ảnh để tránh request quá lớn.
            let done = 0;
            for (let i = 0; i < files.length; i += 6) {
                const chunk = files.slice(i, i + 6);
                const payload = [];
                for (const f of chunk) {
                    payload.push({ name: f.name, data: await readAsBase64(f) });
                }
                done += await this.orm.call("vd.house.design", "vd_house_upload",
                    [this.state.cat, this.state.style, payload]);
            }
            this.notification.add(`Đã tải lên ${done} ảnh.`, { type: "success" });
            await this.reloadTabsKeepPos();
        } catch (e) {
            console.warn("Tải ảnh lên lỗi:", e);
            this.notification.add("Tải ảnh lên lỗi.", { type: "danger" });
        } finally {
            this.state.uploading = false;
        }
    }

    async removeSelected() {
        const ids = Object.keys(this.state.selected).map(Number);
        if (!ids.length) return;
        try {
            await this.orm.call("vd.house.design", "vd_house_delete", [ids]);
            await this.reloadTabsKeepPos();
            this.notification.add(`Đã xoá ${ids.length} ảnh.`, { type: "success" });
        } catch (e) {
            console.warn("Xoá ảnh lỗi:", e);
        }
    }
}

// Nút nổi trên form khách hàng (field widget trên boolean stage_is_won).
export class VdHouseLibButton extends Component {
    static template = "vd_crm_lead.HouseLibButton";
    static props = { ...standardFieldProps };
    setup() {
        this.dialog = useService("dialog");
    }
    get hidden() {
        return !!this.props.record.data.stage_is_won;
    }
    open() {
        this.dialog.add(VdHouseLibDialog, {});
    }
}

registry.category("fields").add("vd_house_lib_btn", {
    component: VdHouseLibButton,
    supportedTypes: ["boolean"],
});
