/** @odoo-module **/
/**
 * Excel TSV paste cho wizard "Thêm KH mới".
 *
 * Khi user copy nhiều dòng từ Excel (TSV: tab giữa cột, newline giữa dòng) rồi
 * paste vào 1 ô trong list → tự fill các ô tiếp theo (theo cột hiện tại + bên
 * phải) và các dòng tiếp theo (tạo dòng mới nếu thiếu).
 *
 * Chỉ áp dụng cho model `vd.lead.quick.add.wizard.line`.
 */
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

const WIZARD_LINE_MODEL = "vd.lead.quick.add.wizard.line";

/** Parse TSV text → matrix [[r1c1, r1c2, ...], [r2c1, ...], ...] */
function parseTsv(text) {
    const lines = text.split(/\r?\n/);
    // Bỏ dòng trống cuối (Excel thường thêm newline cuối)
    while (lines.length && lines[lines.length - 1] === "") lines.pop();
    return lines.map((l) => l.split("\t"));
}

/** Convert string value to field-typed value (best effort). */
function coerceValue(rawStr, field) {
    if (!field) return rawStr;
    const s = (rawStr || "").trim();
    switch (field.type) {
        case "char":
        case "text":
        case "html":
            return s;
        case "integer":
            return parseInt(s, 10) || 0;
        case "float":
        case "monetary":
            return parseFloat(s.replace(/[, ]/g, "")) || 0;
        case "boolean":
            return ["1", "true", "x", "yes", "có"].includes(s.toLowerCase());
        case "date":
        case "datetime":
            return s; // để Odoo parse, có thể fail
        case "selection": {
            // Match by key hoặc by label (case-insensitive)
            const opts = field.selection || [];
            const lower = s.toLowerCase();
            const hit = opts.find(
                ([k, lbl]) =>
                    String(k).toLowerCase() === lower ||
                    String(lbl).toLowerCase() === lower,
            );
            return hit ? hit[0] : false;
        }
        default:
            // many2one / many2many: bỏ qua (không đủ context để resolve)
            return undefined;
    }
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        if (this.props?.list?.resModel === WIZARD_LINE_MODEL) {
            useEffect(
                () => {
                    const el = this.tableRef?.el || this.rootRef?.el;
                    if (!el) return;
                    const handler = (ev) => this._vdTsvPaste(ev);
                    el.addEventListener("paste", handler, true);
                    return () => el.removeEventListener("paste", handler, true);
                },
                () => [this.tableRef?.el, this.rootRef?.el],
            );
        }
    },

    async _vdTsvPaste(ev) {
        const clip = ev.clipboardData || window.clipboardData;
        if (!clip) return;
        const text = clip.getData("text/plain") || "";
        if (!text) return;
        // Chỉ kích hoạt nếu TSV thực sự (có tab hoặc nhiều dòng)
        const hasTab = text.includes("\t");
        const hasMultiLine = /\r?\n/.test(text.trimEnd());
        if (!hasTab && !hasMultiLine) return;

        const matrix = parseTsv(text);
        if (!matrix.length) return;

        // Xác định ô đang focus
        const td = ev.target.closest("td");
        const tr = ev.target.closest("tr");
        if (!td || !tr) return;
        const startFieldName = td.getAttribute("name") || td.dataset?.name;
        if (!startFieldName) return;

        // Danh sách field cột (theo thứ tự hiển thị)
        const columns = (this.state?.columns || this.props?.archInfo?.columns || [])
            .filter((c) => c.type === "field");
        const startColIdx = columns.findIndex((c) => c.name === startFieldName);
        if (startColIdx < 0) return;

        // Vị trí dòng đang focus trong list.records
        const list = this.props.list;
        const rowId = tr.dataset?.id || tr.getAttribute("data-id");
        let startRowIdx = list.records.findIndex((r) => r.id === rowId);
        if (startRowIdx < 0) {
            // Fallback: dùng index trong DOM
            const trList = Array.from(tr.parentElement.children).filter(
                (c) => c.tagName === "TR" && c.dataset?.id,
            );
            startRowIdx = trList.indexOf(tr);
            if (startRowIdx < 0) return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        const activeFields = list.activeFields || {};
        // Apply matrix
        for (let r = 0; r < matrix.length; r++) {
            const targetIdx = startRowIdx + r;
            let record = list.records[targetIdx];
            if (!record) {
                await list.addNewRecord?.({ position: "bottom" })
                    ?? list.addNew?.({ position: "bottom" });
                record = list.records[list.records.length - 1];
                if (!record) continue;
            }
            const update = {};
            for (let c = 0; c < matrix[r].length; c++) {
                const colIdx = startColIdx + c;
                const col = columns[colIdx];
                if (!col) continue;
                const fieldInfo =
                    activeFields[col.name]?.field || list.fields?.[col.name];
                const val = coerceValue(matrix[r][c], fieldInfo);
                if (val === undefined) continue;
                update[col.name] = val;
            }
            if (Object.keys(update).length) {
                try {
                    await record.update(update);
                } catch (e) {
                    // Lỗi 1 ô không nên hủy toàn bộ paste
                    console.warn("TSV paste: update failed", e);
                }
            }
        }
    },
});
