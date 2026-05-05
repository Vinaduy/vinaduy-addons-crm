/** @odoo-module **/
/**
 * Color statusbar buttons of crm.lead based on stage name.
 * Each stage gets a distinct color when it's the current one.
 */
import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { onMounted, onPatched } from "@odoo/owl";

const STAGE_COLORS = {
    "Khách chưa gán": "#6c757d",       // xám
    "Khách mới": "#0dcaf0",            // xanh lam nhạt
    "Có tiềm năng": "#0d6efd",         // xanh dương
    "Báo giá": "#fd7e14",              // cam
    "Tiềm năng đàm phán": "#6f42c1",   // tím
    "Tiềm năng hợp đồng": "#0a58ca",   // xanh đậm
    "Tiềm năng gấp": "#dc3545",        // ĐỎ
    "Chốt": "#198754",                 // XANH LÁ
};

// Add "Khách không có nhu cầu" stage to the color map
STAGE_COLORS["Khách không có nhu cầu"] = "#343a40";  // xám đen

function applyVinaduyStageColors(rootEl) {
    if (!rootEl) return;
    // Xóa empty .o_statusbar_buttons div để statusbar slide sát trái
    rootEl.querySelectorAll(".o_form_statusbar .o_statusbar_buttons").forEach((el) => {
        if (!el.textContent.trim() && !el.querySelector("button:not([style*='display: none'])")) {
            el.style.display = "none";
            el.style.width = "0";
            el.style.flex = "0 0 0";
        }
    });
    // Force statusbar status to start from left
    rootEl.querySelectorAll(".o_form_statusbar .o_statusbar_status").forEach((el) => {
        el.style.marginLeft = "0";
        el.style.marginRight = "auto";
    });
    const buttons = rootEl.querySelectorAll(".o_statusbar_status .o_arrow_button");
    buttons.forEach((btn) => {
        const text = (btn.textContent || "").trim();
        const color = STAGE_COLORS[text];
        if (color && btn.classList.contains("o_arrow_button_current")) {
            btn.style.backgroundColor = color;
            btn.style.borderColor = color;
            btn.style.color = "#ffffff";
            btn.style.backgroundImage = "none";
        } else if (color) {
            btn.style.backgroundColor = "";
            btn.style.borderColor = "";
            btn.style.color = "";
            btn.style.backgroundImage = "";
        }
    });
}

function applyKanbanColumnColors() {
    document.querySelectorAll(".o_kanban_renderer .o_kanban_group").forEach((col) => {
        const titleEl = col.querySelector(".o_column_title, .o_kanban_header_title");
        if (!titleEl) return;
        // Get stage name (without count badge)
        const existingBadge = titleEl.querySelector(".vd-count-badge");
        if (existingBadge) existingBadge.remove();
        const text = (titleEl.textContent || "").trim().split("\n")[0].trim().replace(/\s*\(\d+\)\s*$/, "");
        let matchedColor = null;
        for (const [stage, color] of Object.entries(STAGE_COLORS)) {
            if (text === stage || text.startsWith(stage)) {
                matchedColor = color;
                break;
            }
        }
        // Tô màu - background NHẠT + chữ đậm dễ đọc
        if (matchedColor) {
            titleEl.style.background = matchedColor + "22"; // alpha ~13% (rất nhạt)
            titleEl.style.color = matchedColor;             // chữ đậm full màu
            titleEl.style.fontWeight = "700";
            titleEl.style.padding = "8px 14px";
            titleEl.style.borderRadius = "8px";
            titleEl.style.borderLeft = `4px solid ${matchedColor}`;
            titleEl.style.borderTop = "none";
            titleEl.style.display = "flex";
            titleEl.style.alignItems = "center";
            titleEl.style.gap = "6px";
            titleEl.style.boxShadow = "none";
        }
        // Đếm số lead trong cột → format "(10)" nhỏ gọn bên cạnh tên
        const cardCount = col.querySelectorAll(".o_kanban_record").length;
        const countSpan = document.createElement("span");
        countSpan.className = "vd-count-badge";
        countSpan.style.fontWeight = "normal";
        countSpan.style.marginLeft = "6px";
        countSpan.textContent = `(${cardCount})`;
        titleEl.appendChild(countSpan);

        // Tô màu thanh progressbar theo stage color
        if (matchedColor) {
            col.querySelectorAll(".o_kanban_counter_progress .progress-bar").forEach((bar) => {
                bar.style.backgroundColor = matchedColor;
                bar.style.borderColor = matchedColor;
            });
        }
    });
}

// Throttled observer - tránh infinite loop khi modify DOM
let kanbanObserver = null;
let pendingTimer = null;
let isApplying = false;

function scheduleApply() {
    if (isApplying || pendingTimer) return;
    pendingTimer = setTimeout(() => {
        pendingTimer = null;
        isApplying = true;
        try {
            applyKanbanColumnColors();
        } finally {
            isApplying = false;
        }
    }, 500);
}

function ensureKanbanObserver() {
    if (kanbanObserver) return;
    kanbanObserver = new MutationObserver((mutations) => {
        // Bỏ qua changes do chính mình tạo (vd-count-badge)
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.classList && node.classList.contains("vd-count-badge")) {
                    return;
                }
            }
        }
        scheduleApply();
    });
    kanbanObserver.observe(document.body, { childList: true, subtree: true });
    setTimeout(applyKanbanColumnColors, 500);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureKanbanObserver);
} else {
    ensureKanbanObserver();
}

patch(StatusBarField.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            const root = document.querySelector(".o_form_view");
            applyVinaduyStageColors(root);
        });
        onPatched(() => {
            const root = document.querySelector(".o_form_view");
            applyVinaduyStageColors(root);
        });
    },
});
