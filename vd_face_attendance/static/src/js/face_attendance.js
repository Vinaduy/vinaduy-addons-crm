/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";

// Tải face-api.js 1 lần (từ CDN cấu hình được). Trả về window.faceapi.
let _faceApiPromise = null;
function loadFaceApi(libUrl) {
    if (window.faceapi) {
        return Promise.resolve(window.faceapi);
    }
    if (_faceApiPromise) {
        return _faceApiPromise;
    }
    _faceApiPromise = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = libUrl;
        s.async = true;
        s.onload = () =>
            window.faceapi
                ? resolve(window.faceapi)
                : reject(new Error("Thư viện nhận diện tải lỗi."));
        s.onerror = () =>
            reject(new Error("Không tải được thư viện nhận diện (kiểm tra mạng)."));
        document.head.appendChild(s);
    });
    return _faceApiPromise;
}

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const toR = (d) => (d * Math.PI) / 180;
    const dLat = toR(lat2 - lat1);
    const dLon = toR(lon2 - lon1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toR(lat1)) * Math.cos(toR(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
}

function euclid(a, b) {
    let s = 0;
    for (let i = 0; i < a.length; i++) {
        const d = a[i] - b[i];
        s += d * d;
    }
    return Math.sqrt(s);
}

export class VdFaceCheckin extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.state = useState({
            phase: "loading", // loading | ready | error
            msg: "Đang khởi tạo…",
            enrolled: false,
            userName: "",
            gpsOk: false,
            distance: null,
            withinRadius: false,
            radius: 50,
            faceMsg: "",
            busy: false,
            open: null,
            recent: [],
            camOk: false,
            // Đăng ký: nhập tên + giới tính; mã số tự cấp.
            enrollName: "",
            enrollGender: "male",
            reg: null, // hồ sơ đã đăng ký {code, name, gender, photo}
        });
        this.cfg = null;
        this._descriptor = null;
        this._faceapi = null;
        this._stream = null;
        this._geoWatch = null;
        this._lastPos = null;

        onMounted(() => this._init());
        onWillUnmount(() => this._cleanup());
    }

    async _init() {
        try {
            this.cfg = await this.orm.call(
                "vd.face.attendance", "vd_face_client_config", []);
            this.state.enrolled = this.cfg.enrolled;
            this.state.userName = this.cfg.user_name;
            this.state.radius = this.cfg.radius;
            this.state.open = this.cfg.open_attendance;
            this.state.recent = this.cfg.recent || [];
            this._descriptor = this.cfg.descriptor;
            this.state.enrollName = (this.cfg.employee && this.cfg.employee.name) || this.cfg.user_name || "";
            if (this.cfg.employee) {
                this.state.reg = { ...this.cfg.employee, photo: null };
            }

            await this._startCamera();
            this._startGps();

            this.state.msg = "Đang tải mô hình nhận diện…";
            const faceapi = await loadFaceApi(this.cfg.lib_url);
            const url = this.cfg.model_url;
            await faceapi.nets.tinyFaceDetector.loadFromUri(url);
            await faceapi.nets.faceLandmark68Net.loadFromUri(url);
            await faceapi.nets.faceRecognitionNet.loadFromUri(url);
            this._faceapi = faceapi;

            this.state.phase = "ready";
            this.state.msg = "";
        } catch (e) {
            this.state.phase = "error";
            this.state.msg = e.message || "Lỗi khởi tạo.";
        }
    }

    async _startCamera() {
        try {
            this._stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" },
                audio: false,
            });
            const v = this.videoRef.el;
            if (v) {
                v.srcObject = this._stream;
                await v.play().catch(() => {});
            }
            this.state.camOk = true;
        } catch (e) {
            throw new Error("Không mở được camera. Hãy cho phép quyền camera rồi tải lại trang.");
        }
    }

    _startGps() {
        if (!navigator.geolocation) {
            this.state.faceMsg = "Thiết bị không hỗ trợ định vị GPS.";
            return;
        }
        this._geoWatch = navigator.geolocation.watchPosition(
            (pos) => {
                this._lastPos = pos.coords;
                const d = haversine(
                    pos.coords.latitude, pos.coords.longitude,
                    this.cfg.lat, this.cfg.lng);
                this.state.distance = Math.round(d);
                this.state.gpsOk = true;
                this.state.withinRadius = d <= this.cfg.radius;
            },
            () => {
                this.state.gpsOk = false;
            },
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 }
        );
    }

    async _captureDescriptor() {
        const v = this.videoRef.el;
        if (!v || !this._faceapi) {
            return null;
        }
        const det = await this._faceapi
            .detectSingleFace(
                v, new this._faceapi.TinyFaceDetectorOptions({ inputSize: 320 }))
            .withFaceLandmarks()
            .withFaceDescriptor();
        return det ? Array.from(det.descriptor) : null;
    }

    _snapshot() {
        const v = this.videoRef.el;
        const c = this.canvasRef.el;
        if (!v || !c || !v.videoWidth) {
            return null;
        }
        const w = 320;
        const h = Math.round(w * (v.videoHeight / v.videoWidth));
        c.width = w;
        c.height = h;
        c.getContext("2d").drawImage(v, 0, 0, w, h);
        return c.toDataURL("image/jpeg", 0.8);
    }

    async enroll() {
        if (this.state.busy || this.state.phase !== "ready") {
            return;
        }
        const name = (this.state.enrollName || "").trim();
        if (!name) {
            this.notification.add("Hãy nhập TÊN nhân viên trước khi đăng ký.", { type: "warning" });
            return;
        }
        this.state.busy = true;
        this.state.faceMsg = "Đang lấy mẫu khuôn mặt…";
        try {
            const desc = await this._captureDescriptor();
            if (!desc) {
                this.state.faceMsg = "Không thấy khuôn mặt rõ — hãy nhìn thẳng vào camera.";
                return;
            }
            const photo = this._snapshot();
            const res = await this.orm.call("vd.face.attendance", "vd_enroll_face", [
                name, this.state.enrollGender, desc, photo,
            ]);
            this._descriptor = desc;
            this.state.enrolled = true;
            this.state.reg = {
                code: res.code, name: res.name, gender: res.gender, photo: res.photo || photo,
            };
            this.state.faceMsg = "";
            this.notification.add(
                "Đăng ký thành công — Mã số: " + res.code, { type: "success" });
        } catch (e) {
            this.notification.add(this._errMsg(e), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    async _doAttendance(kind) {
        if (this.state.busy || this.state.phase !== "ready") {
            return;
        }
        if (!this.state.enrolled) {
            this.notification.add("Bạn chưa đăng ký khuôn mặt.", { type: "warning" });
            return;
        }
        if (!this._lastPos) {
            this.notification.add("Chưa lấy được vị trí GPS — hãy bật định vị.", { type: "warning" });
            return;
        }
        this.state.busy = true;
        this.state.faceMsg = "Đang nhận diện…";
        try {
            const desc = await this._captureDescriptor();
            if (!desc) {
                this.state.faceMsg = "Không thấy khuôn mặt — hãy nhìn thẳng vào camera.";
                return;
            }
            const dist = euclid(desc, this._descriptor);
            const score = Math.max(0, 1 - dist);
            if (dist > this.cfg.threshold) {
                this.state.faceMsg = "Khuôn mặt KHÔNG khớp với người đã đăng ký.";
                this.notification.add("Khuôn mặt không khớp — không chấm công được.", { type: "danger" });
                return;
            }
            const photo = this._snapshot();
            const method = kind === "in" ? "vd_check_in" : "vd_check_out";
            await this.orm.call("vd.face.attendance", method, [
                this._lastPos.latitude, this._lastPos.longitude, score, photo,
            ]);
            const cfg = await this.orm.call(
                "vd.face.attendance", "vd_face_client_config", []);
            this.state.open = cfg.open_attendance;
            this.state.recent = cfg.recent || [];
            this.state.faceMsg = "";
            this.notification.add(
                kind === "in" ? "✅ Chấm VÀO thành công." : "✅ Chấm RA thành công.",
                { type: "success" });
        } catch (e) {
            const msg = this._errMsg(e);
            this.notification.add(msg, { type: "danger" });
            this.state.faceMsg = msg;
        } finally {
            this.state.busy = false;
        }
    }

    checkIn() {
        return this._doAttendance("in");
    }
    checkOut() {
        return this._doAttendance("out");
    }

    _errMsg(e) {
        return (e && e.data && e.data.message) || (e && e.message) || "Có lỗi xảy ra.";
    }

    _cleanup() {
        if (this._geoWatch != null && navigator.geolocation) {
            navigator.geolocation.clearWatch(this._geoWatch);
        }
        if (this._stream) {
            this._stream.getTracks().forEach((t) => t.stop());
        }
    }
}
VdFaceCheckin.template = "vd_face_attendance.Checkin";

registry.category("actions").add("vd_face_attendance_checkin", VdFaceCheckin);
