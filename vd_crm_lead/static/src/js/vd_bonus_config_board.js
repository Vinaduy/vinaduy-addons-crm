/** @odoo-module **/
// Board CẤU HÌNH TIỀN THƯỞNG dạng THẺ (admin) — gộp Thưởng cá nhân + Thưởng phòng
// vào 1 màn. Chọn phòng ban (tab thẻ) → 2 khu thẻ: cá nhân (theo HĐ) + phòng.
// Tab "CHUNG" = mốc cá nhân áp cho mọi phòng chưa cấu hình riêng.
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

const NF = new Intl.NumberFormat("vi-VN");

export class VdBonusConfigBoard extends Component {
    static template = "vd_crm_lead.VdBonusConfigBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            teams: [],
            common: [],
            activeKey: "common",
            loading: true,
        });
        onWillStart(async () => { await this.load(); });
    }

    async load() {
        this.state.loading = true;
        const d = await this.orm.call("vd.bonus.team", "vd_bonus_config_data", []);
        this.state.teams = d.teams || [];
        this.state.common = d.common_personal || [];
        this.state.loading = false;
    }

    get activeTeam() {
        return this.state.teams.find((t) => t.key === this.state.activeKey) || null;
    }
    get isCommon() { return this.state.activeKey === "common"; }
    get personalList() {
        return this.isCommon ? this.state.common
            : (this.activeTeam ? this.activeTeam.personal : []);
    }
    get teamList() { return this.activeTeam ? this.activeTeam.team : []; }

    fmt(n) { return NF.format(Math.round(Number(n) || 0)); }
    setTab(key) { this.state.activeKey = key; }

    addPersonal() {
        const list = this.personalList;
        const nextNo = list.length
            ? Math.max(...list.map((i) => i.contract_no || 0)) + 1 : 1;
        list.push({ id: null, name: "", contract_no: nextNo, amount: 0, active: true, _new: true });
    }
    addTeam() {
        this.teamList.push({ id: null, name: "", amount: 0, contract_count: 1, people_count: 1, active: true, _new: true });
    }

    async saveItem(model, item) {
        const vals = model === "personal"
            ? {
                name: item.name,
                contract_no: Number(item.contract_no) || 1,
                amount: Number(item.amount) || 0,
                team: this.isCommon ? false : this.state.activeKey,
                active: item.active,
            }
            : {
                name: item.name,
                amount: Number(item.amount) || 0,
                contract_count: Number(item.contract_count) || 0,
                people_count: Number(item.people_count) || 0,
                team: this.state.activeKey,
                active: item.active,
            };
        try {
            const id = await this.orm.call(
                "vd.bonus.team", "vd_bonus_save", [model, vals, item.id || false]);
            item.id = id;
            item._new = false;
            this.notification.add("Đã lưu mốc thưởng.", { type: "success" });
        } catch (e) {
            this.notification.add("Lỗi lưu: " + (e.message || e), { type: "danger" });
        }
    }

    async deleteItem(model, item, list) {
        if (item.id) {
            try {
                await this.orm.call("vd.bonus.team", "vd_bonus_delete", [model, item.id]);
            } catch (e) {
                this.notification.add("Lỗi xoá: " + (e.message || e), { type: "danger" });
                return;
            }
        }
        const idx = list.indexOf(item);
        if (idx >= 0) list.splice(idx, 1);
    }
}

registry.category("actions").add("vd_bonus_config_board", VdBonusConfigBoard);
