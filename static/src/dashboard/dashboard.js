/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

const STAGE_COLORS = {
    "Khách mới": "#0dcaf0",
    "Có tiềm năng": "#0d6efd",
    "Báo giá": "#fd7e14",
    "Tiềm năng đàm phán": "#6f42c1",
    "Tiềm năng hợp đồng": "#0a58ca",
    "Tiềm năng gấp": "#dc3545",
    "Chốt": "#198754",
    "Khách không có nhu cầu": "#343a40",
};

class VinaduyDashboard extends Component {
    static template = "vinaduy_crm.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true, error: null });

        this.charts = {};
        this.refTrend = useRef("trendChart");
        this.refStages = useRef("stagesChart");
        this.refUsers = useRef("usersChart");
        this.refSources = useRef("sourcesChart");
        this.refConvGauge = useRef("convGauge");
        this.refAbove = useRef("aboveChart");
        this.refBelow = useRef("belowChart");

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            try {
                const data = await this.orm.call("vinaduy.crm.dashboard", "get_dashboard_data", []);
                this.state.data = data;
            } catch (err) {
                this.state.error = err.message || "Không tải được dữ liệu";
            } finally {
                this.state.loading = false;
            }
        });

        onMounted(() => this.renderCharts());
        onWillUnmount(() => this.destroyCharts());
    }

    destroyCharts() {
        Object.values(this.charts).forEach((c) => c?.destroy?.());
        this.charts = {};
    }

    renderCharts() {
        if (!this.state.data || !window.Chart) return;
        this.destroyCharts();
        this.renderTrendChart();
        this.renderStagesChart();
        this.renderUsersChart();
        this.renderSourcesChart();
        this.renderConvGauge();
        this.renderAboveChart();
        this.renderBelowChart();
    }

    renderAboveChart() {
        if (!this.refAbove.el) return;
        const above = this.state.data.threshold_above;
        if (!above.length) return;
        this.charts.above = new Chart(this.refAbove.el, {
            type: "bar",
            data: {
                labels: above.map((u) => u.name),
                datasets: [
                    { label: "Tổng KH", data: above.map((u) => u.total), backgroundColor: "#52c41a", borderRadius: 4 },
                    { label: "Chốt", data: above.map((u) => u.won), backgroundColor: "#198754", borderRadius: 4 },
                ],
            },
            options: {
                indexAxis: "y", responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ctx) => {
                                const u = above[ctx.dataIndex];
                                return [` Conv: ${u.conv}%`, ` Đàm phán: ${u.damphan}`, ` HĐ: ${u.hopdong}`, `Click để xem chi tiết →`].join("\n");
                            },
                        },
                    },
                },
                scales: { x: { beginAtZero: true } },
                onClick: (evt, els) => {
                    if (!els.length) return;
                    const u = above[els[0].index];
                    this.openByUser(u.id, u.name);
                },
            },
        });
    }

    renderBelowChart() {
        if (!this.refBelow.el) return;
        const below = this.state.data.threshold_below.slice().sort((a, b) => b.overdue - a.overdue);
        if (!below.length) return;
        this.charts.below = new Chart(this.refBelow.el, {
            type: "bar",
            data: {
                labels: below.map((u) => u.name),
                datasets: [
                    { label: "Tổng KH", data: below.map((u) => u.total), backgroundColor: "#fd7e14", borderRadius: 4 },
                    { label: "Quá hạn", data: below.map((u) => u.overdue), backgroundColor: "#dc3545", borderRadius: 4 },
                ],
            },
            options: {
                indexAxis: "y", responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ctx) => {
                                const u = below[ctx.dataIndex];
                                return [` Chốt: ${u.won}`, ` Đàm phán: ${u.damphan}`, ` Conv: ${u.conv}%`, `Click để xem chi tiết →`].join("\n");
                            },
                        },
                    },
                },
                scales: { x: { beginAtZero: true } },
                onClick: (evt, els) => {
                    if (!els.length) return;
                    const u = below[els[0].index];
                    this.openByUser(u.id, u.name);
                },
            },
        });
    }

    renderTrendChart() {
        if (!this.refTrend.el) return;
        const trend = this.state.data.trend;
        this.charts.trend = new Chart(this.refTrend.el, {
            type: "bar",
            data: {
                labels: trend.map((m) => m.label),
                datasets: [
                    {
                        type: "bar",
                        label: "Tổng KH",
                        data: trend.map((m) => m.total),
                        backgroundColor: "#4096ff",
                        borderRadius: 4,
                        yAxisID: "y",
                        order: 2,
                    },
                    {
                        type: "line",
                        label: "Conv %",
                        data: trend.map((m) => m.conv),
                        borderColor: "#fd7e14",
                        backgroundColor: "#fd7e14",
                        borderWidth: 3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        tension: 0.3,
                        yAxisID: "y1",
                        order: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                if (ctx.dataset.type === "line") {
                                    return ` Conv: ${ctx.parsed.y}%`;
                                }
                                return ` Tổng: ${ctx.parsed.y} KH`;
                            },
                        },
                    },
                },
                scales: {
                    y: { type: "linear", position: "left", title: { display: true, text: "Số KH" }, beginAtZero: true },
                    y1: {
                        type: "linear",
                        position: "right",
                        title: { display: true, text: "Conv %" },
                        beginAtZero: true,
                        max: 100,
                        grid: { drawOnChartArea: false },
                    },
                },
            },
        });
    }

    renderStagesChart() {
        if (!this.refStages.el) return;
        const stages = this.state.data.stages;
        this.charts.stages = new Chart(this.refStages.el, {
            type: "doughnut",
            data: {
                labels: stages.map((s) => s.name),
                datasets: [
                    {
                        data: stages.map((s) => s.count),
                        backgroundColor: stages.map((s) => STAGE_COLORS[s.name] || "#6c757d"),
                        borderWidth: 2,
                        borderColor: "#fff",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 14, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.label}: ${ctx.parsed} KH`,
                        },
                    },
                },
                onClick: (evt, elements) => {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const stage = stages[idx];
                    this.openLeads([["stage_id", "=", stage.id]], stage.name);
                },
            },
        });
    }

    renderUsersChart() {
        if (!this.refUsers.el) return;
        const users = this.state.data.per_user.slice(0, 10);
        this.charts.users = new Chart(this.refUsers.el, {
            type: "bar",
            data: {
                labels: users.map((u) => u.name),
                datasets: [
                    {
                        label: "Tổng KH",
                        data: users.map((u) => u.total),
                        backgroundColor: users.map((u) => u.rating.color),
                        borderRadius: 4,
                    },
                    {
                        label: "Quá hạn",
                        data: users.map((u) => u.overdue),
                        backgroundColor: "#dc3545",
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ctx) => {
                                const u = users[ctx.dataIndex];
                                return [
                                    ` Chốt: ${u.won}`,
                                    ` Đàm phán: ${u.damphan}`,
                                    ` HĐ: ${u.hopdong}`,
                                    ` Conv: ${u.conv}%`,
                                    ` ${u.rating.label}`,
                                    `Click để xem chi tiết →`,
                                ].join("\n");
                            },
                        },
                    },
                },
                scales: { x: { beginAtZero: true } },
                onClick: (evt, elements) => {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const u = users[idx];
                    this.openByUser(u.id, u.name);
                },
            },
        });
    }

    renderSourcesChart() {
        if (!this.refSources.el) return;
        const sources = this.state.data.sources;
        const totalSources = sources.reduce((sum, s) => sum + s.count, 0) || 1;
        this.charts.sources = new Chart(this.refSources.el, {
            type: "pie",
            data: {
                labels: sources.map((s) => s.name),
                datasets: [
                    {
                        data: sources.map((s) => s.count),
                        backgroundColor: ["#1677ff", "#52c41a", "#fa8c16", "#722ed1"],
                        borderWidth: 2,
                        borderColor: "#fff",
                        hoverOffset: 12,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 14, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const pct = ((ctx.parsed / totalSources) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.parsed} KH (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    renderConvGauge() {
        if (!this.refConvGauge.el) return;
        const conv = this.state.data.kpi.conv_pct;
        const remaining = Math.max(0, 100 - conv);
        this.charts.convGauge = new Chart(this.refConvGauge.el, {
            type: "doughnut",
            data: {
                labels: ["Conv%", ""],
                datasets: [
                    {
                        data: [conv, remaining],
                        backgroundColor: [
                            conv >= 30 ? "#198754" : conv >= 10 ? "#fd7e14" : "#dc3545",
                            "#f0f2f5",
                        ],
                        borderWidth: 0,
                        circumference: 180,
                        rotation: 270,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "75%",
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                },
            },
            plugins: [
                {
                    id: "centerText",
                    afterDraw: (chart) => {
                        const { ctx, chartArea } = chart;
                        ctx.save();
                        ctx.font = "bold 26px Inter, sans-serif";
                        ctx.fillStyle = "#1f1f3a";
                        ctx.textAlign = "center";
                        ctx.fillText(`${conv}%`, (chartArea.left + chartArea.right) / 2, chartArea.bottom - 14);
                        ctx.font = "11px Inter, sans-serif";
                        ctx.fillStyle = "#6c757d";
                        ctx.fillText("CONV%", (chartArea.left + chartArea.right) / 2, chartArea.bottom + 6);
                        ctx.restore();
                    },
                },
            ],
        });
    }

    stageColor(name) {
        return STAGE_COLORS[name] || "#6c757d";
    }

    openLeads(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name || "Lead",
            res_model: "crm.lead",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domain,
            target: "new",
        });
    }

    openOverdue() {
        this.openLeads([["sla_overdue", "=", true], ["active", "=", true]], "🔴 KH quá hạn SLA");
    }

    openWon() {
        this.openLeads([["stage_id.is_won", "=", true]], "🎉 KH đã chốt");
    }

    openByUser(userId, userName) {
        this.openLeads([["user_id", "=", userId]], `Lead của ${userName}`);
    }
}

registry.category("actions").add("vinaduy_dashboard", VinaduyDashboard);
