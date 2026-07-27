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
    { key: "cong_nang_3d", title: "THƯ VIỆN - Công năng", icon: "fa-th-large", cls: "o_vd_cn3d_lib_filter" },
    { key: "3d", title: "THƯ VIỆN - 3D", icon: "fa-cube", cls: "o_vd_3d_lib_filter" },
    { key: "hop_dong", title: "THƯ VIỆN - Hợp đồng", icon: "fa-file-text-o", cls: "o_vd_hd_lib_filter" },
];

// BỘ LỌC "Hạng mục" cho thư viện Video nghiệm thu — chip theo TỪ KHÓA trong tên
// video (1 video có thể khớp nhiều hạng mục). Chip chỉ hiện khi có ≥1 video khớp.
const NT_CATS = [
    { key: "mong", label: "Móng", kw: ["móng"] },
    { key: "coc", label: "Ép cọc", kw: ["cọc", "ép cọc"] },
    { key: "sat", label: "Sắt thép", kw: ["sắt", "thép"] },
    { key: "coppha", label: "Coppha", kw: ["coppha", "cốp pha", "cofa"] },
    { key: "cot", label: "Cột", kw: ["cột"] },
    { key: "tuong", label: "Tường - Gạch", kw: ["tường", "gạch", "xây"] },
    { key: "betong", label: "Bê tông", kw: ["bê tông", "betong"] },
    { key: "san", label: "Sàn", kw: ["sàn"] },
    { key: "bephot", label: "Bể phốt", kw: ["bể phốt", "bể phot"] },
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
        this.state = useState({
            loading: true, error: "", groups: [],
            fFloors: null, fFront: null,   // bộ lọc số tầng / mặt tiền (Công năng)
            fCat: null,                    // bộ lọc hạng mục (Video nghiệm thu)
            sel: {},                       // id video được tick chọn (tải hàng loạt)
        });
        this._alive = true;
        onWillUnmount(() => { this._alive = false; });
        this.load();
    }

    // ===== BỘ LỌC =====
    get isCnLib() { return this.props.libKey === "cong_nang_3d"; }
    get isNtLib() { return this.props.libKey === "nghiem_thu"; }
    get showFilters() { return this.isCnLib || this.isNtLib; }

    // --- Video nghiệm thu: lọc theo HẠNG MỤC (từ khóa trong tên) ---
    ntMatch(name, catKey) {
        const cat = NT_CATS.find((c) => c.key === catKey);
        if (!cat) return true;
        const n = (name || "").toLowerCase();
        return cat.kw.some((k) => n.includes(k));
    }
    get ntCatsList() {
        const files = this.allFiles;
        return NT_CATS.filter((c) => files.some((f) => this.ntMatch(f.name, c.key)));
    }
    setCat(v) { this.state.fCat = (this.state.fCat === v) ? null : v; }

    // --- CHỌN + TẢI HÀNG LOẠT (video nghiệm thu) ---
    get showBulk() { return this.isNtLib && this.displayedVideos.length > 0; }
    // Các video (có thumbnail) đang HIỂN THỊ theo bộ lọc hiện tại.
    get displayedVideos() {
        return this.displayGroups.flatMap(
            (g) => (g.files || []).filter((f) => this.hasThumb(f)));
    }
    isSelected(id) { return !!this.state.sel[id]; }
    toggleSel(id) {
        if (this.state.sel[id]) delete this.state.sel[id];
        else this.state.sel[id] = true;
    }
    get selCount() {
        return Object.keys(this.state.sel).filter((k) => this.state.sel[k]).length;
    }
    get allDisplayedSelected() {
        const vids = this.displayedVideos;
        return vids.length > 0 && vids.every((f) => this.state.sel[f.id]);
    }
    toggleSelectAll() {
        const vids = this.displayedVideos;
        if (this.allDisplayedSelected) {
            for (const f of vids) delete this.state.sel[f.id];
        } else {
            for (const f of vids) this.state.sel[f.id] = true;
        }
    }
    // Tải lần lượt các video đã chọn (giãn cách để trình duyệt không chặn loạt tải).
    downloadSelected() {
        const ids = Object.keys(this.state.sel).filter((k) => this.state.sel[k]);
        if (!ids.length) return;
        ids.forEach((id, i) => {
            setTimeout(() => {
                const a = document.createElement("a");
                a.href = this.dlUrl(id);
                a.download = "";
                document.body.appendChild(a);
                a.click();
                a.remove();
            }, i * 700);
        });
    }

    // Số tầng: token đầu "4,5T" / "2.5T" / "1T" → 4.5 / 2.5 / 1.
    parseFloors(name) {
        const m = (name || "").match(/(\d+(?:[.,]\d+)?)\s*T\b/i);
        return m ? parseFloat(m[1].replace(",", ".")) : null;
    }
    // Mặt tiền: số trước dấu "x" trong "5x13" / "10.4x11.5" → làm tròn xuống mét.
    parseFront(name) {
        const m = (name || "").match(/(\d+(?:[.,]\d+)?)\s*[xX]\s*\d/);
        return m ? Math.floor(parseFloat(m[1].replace(",", "."))) : null;
    }
    get floorsList() {
        const s = new Set();
        for (const f of this.allFiles) {
            const v = this.parseFloors(f.name);
            if (v !== null) s.add(v);
        }
        return [...s].sort((a, b) => a - b);
    }
    get frontList() {
        const s = new Set();
        for (const f of this.allFiles) {
            const v = this.parseFront(f.name);
            if (v !== null) s.add(v);
        }
        return [...s].sort((a, b) => a - b);
    }
    floorLabel(v) {
        return String(v).replace(".", ",") + " tầng";
    }
    setFloors(v) { this.state.fFloors = (this.state.fFloors === v) ? null : v; }
    setFront(v) { this.state.fFront = (this.state.fFront === v) ? null : v; }
    // Nhóm đã áp bộ lọc để render.
    get displayGroups() {
        if (this.isCnLib) {
            const ff = this.state.fFloors, fr = this.state.fFront;
            if (ff === null && fr === null) return this.state.groups;
            return (this.state.groups || []).map((g) => ({
                name: g.name,
                files: (g.files || []).filter((f) => {
                    if (ff !== null && this.parseFloors(f.name) !== ff) return false;
                    if (fr !== null && this.parseFront(f.name) !== fr) return false;
                    return true;
                }),
            }));
        }
        if (this.isNtLib && this.state.fCat) {
            return (this.state.groups || []).map((g) => ({
                name: g.name,
                files: (g.files || []).filter((f) => this.ntMatch(f.name, this.state.fCat)),
            }));
        }
        return this.state.groups;
    }
    get filteredEmpty() {
        const active = (this.isCnLib && (this.state.fFloors !== null || this.state.fFront !== null))
            || (this.isNtLib && !!this.state.fCat);
        return active && !this.displayGroups.some((g) => (g.files || []).length);
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

    // Tên hiển thị: bỏ đuôi file (.docx/.pdf/.xlsx…) cho gọn (user 2026-07-18).
    displayName(name) {
        return (name || "").replace(/\.[A-Za-z0-9]{2,5}$/, "");
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
