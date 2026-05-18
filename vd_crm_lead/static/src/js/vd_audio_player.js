/** @odoo-module **/
/**
 * Compact audio player cho file ghi âm cuộc gọi.
 * UI: nút Play/Pause tròn + duration mm:ss.
 * Click play → audio bắt đầu phát inline (HTMLAudioElement ẩn).
 *
 * Usage in XML:
 *   <field name="recording_attachment_id" widget="vd_audio_player"/>
 */
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VdAudioPlayer extends Component {
    static template = "vd_crm_lead.AudioPlayer";
    static props = { ...standardFieldProps };

    setup() {
        this.audioRef = useRef("audio");
        this.state = useState({
            playing: false,
            duration: 0,   // tổng (giây), set sau khi loadedmetadata
            current: 0,    // thời điểm hiện tại (giây)
            loaded: false, // đã load metadata chưa
        });
        onMounted(() => {
            const a = this.audioRef.el;
            if (!a) return;
            this._onLoaded = () => {
                this.state.duration = Math.floor(a.duration || 0);
                this.state.loaded = true;
            };
            this._onTime = () => {
                this.state.current = Math.floor(a.currentTime || 0);
            };
            this._onEnded = () => {
                this.state.playing = false;
                this.state.current = 0;
            };
            this._onPlay = () => { this.state.playing = true; };
            this._onPause = () => { this.state.playing = false; };
            a.addEventListener("loadedmetadata", this._onLoaded);
            a.addEventListener("timeupdate", this._onTime);
            a.addEventListener("ended", this._onEnded);
            a.addEventListener("play", this._onPlay);
            a.addEventListener("pause", this._onPause);
        });
        onWillUnmount(() => {
            const a = this.audioRef.el;
            if (!a) return;
            a.removeEventListener("loadedmetadata", this._onLoaded);
            a.removeEventListener("timeupdate", this._onTime);
            a.removeEventListener("ended", this._onEnded);
            a.removeEventListener("play", this._onPlay);
            a.removeEventListener("pause", this._onPause);
            try { a.pause(); } catch (_) {}
        });
    }

    get attachmentId() {
        const v = this.props.record.data[this.props.name];
        if (!v) return null;
        if (Array.isArray(v)) return v[0];
        if (typeof v === "object") return v.id;
        return v;
    }

    get audioUrl() {
        const id = this.attachmentId;
        return id ? `/web/content/${id}?download=false` : null;
    }

    get downloadUrl() {
        const id = this.attachmentId;
        return id ? `/web/content/${id}?download=true` : null;
    }

    get displayTime() {
        // Khi đang play → hiện current; khi chưa play → hiện duration
        const t = this.state.playing ? this.state.current : this.state.duration;
        const m = Math.floor(t / 60);
        const s = t % 60;
        return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    }

    togglePlay(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const a = this.audioRef.el;
        if (!a) return;
        if (a.paused) {
            a.play().catch(() => {});
        } else {
            a.pause();
        }
    }
}

registry.category("fields").add("vd_audio_player", {
    component: VdAudioPlayer,
    supportedTypes: ["many2one"],
});
