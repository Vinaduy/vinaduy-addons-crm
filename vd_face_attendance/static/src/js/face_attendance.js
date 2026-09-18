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
            today: null, // {in_time, out_time, late_minutes, early_leave_minutes, worked_hours}
            hasOpen: false, // đã vào, chưa ra
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
            this.state.today = this.cfg.today;
            this.state.hasOpen = this.cfg.open;
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
        const apply = (pos) => {
            this._lastPos = pos.coords;
            const d = haversine(
                pos.coords.latitude, pos.coords.longitude,
                this.cfg.lat, this.cfg.lng);
            this.state.distance = Math.round(d);
            this.state.gpsOk = true;
            this.state.withinRadius = d <= this.cfg.radius;
        };
        // 1) Lấy NHANH 1 vị trí (wifi/mạng, không cần GPS chính xác) → hiện liền.
        navigator.geolocation.getCurrentPosition(
            apply, () => {},
            { enableHighAccuracy: false, maximumAge: 60000, timeout: 8000 });
        // 2) Theo dõi tiếp bằng độ chính xác cao để tinh chỉnh.
        this._geoWatch = navigator.geolocation.watchPosition(
            apply,
            () => { if (!this.state.gpsOk) { /* giữ trạng thái, chờ fix nhanh */ } },
            { enableHighAccuracy: true, maximumAge: 10000, timeout: 25000 });
    }

    async _detectFace() {
        const v = this.videoRef.el;
        if (!v || !this._faceapi) {
            return null;
        }
        return await this._faceapi
            .detectSingleFace(
                v, new this._faceapi.TinyFaceDetectorOptions({ inputSize: 320 }))
            .withFaceLandmarks()
            .withFaceDescriptor();
    }

    // Kiểm tra khuôn mặt phải TRỌN VẸN trong khung: không bị cắt ở mép (đủ cả
    // trán + cằm), không quá nhỏ/xa, không quá sát. Trả null nếu OK, hoặc câu
    // thông báo lỗi. (user spec 2026-09-18)
    _faceIssue(det) {
        const v = this.videoRef.el;
        const W = v.videoWidth || 640;
        const H = v.videoHeight || 480;
        const b = det.detection.box;
        const m = 0.05; // chừa 5% mép — mặt chạm mép coi như bị cắt
        if (b.x < W * m || b.y < H * m ||
            b.x + b.width > W * (1 - m) || b.y + b.height > H * (1 - m)) {
            return "Khuôn mặt bị cắt ở mép — đưa TRỌN khuôn mặt (cả trán và cằm) vào giữa khung.";
        }
        const fw = b.width / W;
        const fh = b.height / H;
        if (fw < 0.22 || fh < 0.28) {
            return "Khuôn mặt quá nhỏ/xa — hãy lại gần camera hơn.";
        }
        if (fw > 0.9 || fh > 0.95) {
            return "Khuôn mặt quá sát — hãy lùi ra một chút.";
        }
        // Chốt landmark trán (điểm lông mày) và cằm phải nằm trong khung.
        try {
            const pts = det.landmarks.positions;
            const chin = pts[8];          // cằm
            const browL = pts[19];        // lông mày (gần trán)
            const browR = pts[24];
            for (const p of [chin, browL, browR]) {
                if (p.x < W * 0.02 || p.x > W * 0.98 || p.y < H * 0.02 || p.y > H * 0.98) {
                    return "Chưa thấy đủ trán/cằm — đưa trọn khuôn mặt vào khung.";
                }
            }
        } catch (e) {
            /* landmark thiếu -> bỏ qua chốt phụ này */
        }
        return null;
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
            const det = await this._detectFace();
            if (!det) {
                this.state.faceMsg = "Không thấy khuôn mặt rõ — hãy nhìn thẳng vào camera.";
                return;
            }
            const issue = this._faceIssue(det);
            if (issue) {
                this.state.faceMsg = issue;
                this.notification.add(issue, { type: "warning" });
                return;
            }
            const desc = Array.from(det.descriptor);
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
        if (!this._lastPos || !this.state.gpsOk) {
            this.notification.add("Chưa lấy được vị trí GPS — hãy bật định vị rồi thử lại.", { type: "warning" });
            return;
        }
        // THÔNG BÁO khi vị trí quá xa (chặn ngay ở client, server cũng chặn lại).
        if (!this.state.withinRadius) {
            this.notification.add(
                `Không chấm công được: bạn đang cách văn phòng ${this.state.distance} m ` +
                `(chỉ chấm trong bán kính ${this.cfg.radius} m).`,
                { type: "danger", title: "Vị trí quá xa" });
            return;
        }
        this.state.busy = true;
        this.state.faceMsg = "Đang nhận diện…";
        try {
            const det = await this._detectFace();
            if (!det) {
                this.state.faceMsg = "Không thấy khuôn mặt — hãy nhìn thẳng vào camera.";
                return;
            }
            const issue = this._faceIssue(det);
            if (issue) {
                this.state.faceMsg = issue;
                this.notification.add(issue, { type: "warning" });
                return;
            }
            const desc = Array.from(det.descriptor);
            const dist = euclid(desc, this._descriptor);
            const score = Math.max(0, 1 - dist);
            if (dist > this.cfg.threshold) {
                this.state.faceMsg = "Khuôn mặt KHÔNG khớp với người đã đăng ký.";
                this.notification.add("Khuôn mặt không khớp — không chấm công được.", { type: "danger" });
                return;
            }
            const photo = this._snapshot();
            const method = kind === "in" ? "vd_check_in" : "vd_check_out";
            const res = await this.orm.call("vd.face.attendance", method, [
                this._lastPos.latitude, this._lastPos.longitude, score, photo,
            ]);
            const cfg = await this.orm.call(
                "vd.face.attendance", "vd_face_client_config", []);
            this.state.today = cfg.today;
            this.state.hasOpen = cfg.open;
            this.state.recent = cfg.recent || [];
            this.state.faceMsg = "";
            let msg;
            if (kind === "in") {
                msg = "✅ Chấm VÀO lúc " + (res.in_time || "");
                if (res.late_minutes) {
                    msg += ` (đi muộn ${res.late_minutes} phút)`;
                }
            } else {
                msg = "✅ Chấm RA lúc " + (res.out_time || "");
                if (res.early_leave_minutes) {
                    msg += ` (về sớm ${res.early_leave_minutes} phút)`;
                }
            }
            this.notification.add(msg, { type: "success" });
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
