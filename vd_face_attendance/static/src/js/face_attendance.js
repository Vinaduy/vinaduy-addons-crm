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
            gpsOk: false,
            gpsErr: "",
            distance: null,
            withinRadius: false,
            radius: 50,
            workStart: "08:00",
            workEnd: "17:30",
            faceMsg: "",
            faceLive: "none", // none | bad | ok  (trạng thái quét trực tiếp)
            faceHint: "Đưa khuôn mặt vào khung",
            busy: false,
            recent: [],
            camOk: false,
            facesCount: 0,
            showEnroll: false, // mở form đăng ký khuôn mặt mới
            // KIOSK: kết quả nhận diện gần nhất để hiện TO tên + mã.
            result: null, // {ok, name, code, line, kind}
            // Đăng ký: nhập tên + giới tính; mã số tự cấp.
            enrollName: "",
            enrollGender: "male",
        });
        this.cfg = null;
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
                "vd.face.attendance", "vd_kiosk_config", []);
            this.state.radius = this.cfg.radius;
            this.state.workStart = this.cfg.work_start_label || "08:00";
            this.state.workEnd = this.cfg.work_end_label || "17:30";
            this.state.recent = this.cfg.recent || [];
            this.state.facesCount = this.cfg.faces_count || 0;

            await this._startCamera();
            this._startGps();

            this.state.msg = "Đang tải mô hình nhận diện…";
            const faceapi = await loadFaceApi(this.cfg.lib_url);
            const url = this.cfg.model_url;
            // Tải 3 model SONG SONG cho nhanh (thay vì chờ tuần tự).
            await Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(url),
                faceapi.nets.faceLandmark68Net.loadFromUri(url),
                faceapi.nets.faceRecognitionNet.loadFromUri(url),
            ]);
            this._faceapi = faceapi;
            // WARM-UP: chạy 1 lần trên canvas trắng để khởi tạo WebGL trước → lần
            // nhận diện thật KHÔNG bị khựng ~1-2s (nguyên nhân "quét lâu").
            try {
                const c = document.createElement("canvas");
                c.width = 224; c.height = 224;
                await faceapi.detectSingleFace(
                    c, new faceapi.TinyFaceDetectorOptions({ inputSize: 224 }));
            } catch (e) { /* bỏ qua */ }

            this.state.phase = "ready";
            this.state.msg = "";
            // Quét LIÊN TỤC nhẹ → phản hồi tức thì + đăng ký/chấm dùng lại kết quả
            // mới nhất (gần như không phải chờ).
            this._startDetectLoop();
        } catch (e) {
            this.state.phase = "error";
            this.state.msg = e.message || "Lỗi khởi tạo.";
        }
    }

    async _startCamera() {
        const attach = async (stream) => {
            this._stream = stream;
            const v = this.videoRef.el;
            if (v) {
                v.muted = true;
                v.setAttribute("playsinline", "");
                v.srcObject = stream;
                // Đợi metadata rồi mới play → tránh khung ĐEN do play sớm.
                await new Promise((res) => {
                    if (v.readyState >= 1) return res();
                    v.onloadedmetadata = () => res();
                    setTimeout(res, 1500);
                });
                for (let i = 0; i < 3; i++) {
                    try { await v.play(); break; } catch (e) { await new Promise(r => setTimeout(r, 250)); }
                }
            }
            this.state.camOk = true;
        };
        try {
            await attach(await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false,
            }));
        } catch (e1) {
            // Một số máy không nhận facingMode → thử camera bất kỳ.
            try {
                await attach(await navigator.mediaDevices.getUserMedia({ video: true, audio: false }));
            } catch (e2) {
                throw new Error("Không mở được camera. Hãy cho phép quyền camera rồi tải lại trang.");
            }
        }
    }

    // ===== QUÉT LIÊN TỤC (nhẹ) — cập nhật trạng thái + giữ kết quả mới nhất =====
    _startDetectLoop() {
        const tick = async () => {
            if (this._stopped) return;
            const v = this.videoRef.el;
            if (this._faceapi && v && v.readyState >= 2 && !this._detecting) {
                this._detecting = true;
                try {
                    const det = await this._detectFace();
                    this._lastDet = det ? { det, t: Date.now() } : null;
                    this._updateFaceLive(det);
                } catch (e) { /* bỏ qua 1 nhịp */ } finally {
                    this._detecting = false;
                }
            }
            this._loopTimer = setTimeout(tick, 300);
        };
        tick();
    }

    _updateFaceLive(det) {
        if (this.state.busy) return;
        if (!det) {
            this.state.faceLive = "none";
            this.state.faceHint = "Đưa khuôn mặt vào giữa khung";
            return;
        }
        const issue = this._faceIssue(det);
        if (issue) {
            this.state.faceLive = "bad";
            this.state.faceHint = issue;
        } else {
            this.state.faceLive = "ok";
            this.state.faceHint = "Khuôn mặt tốt ✓ — bấm nút bên phải";
            // GHI NHẬN khung TỐT gần nhất → khi bấm đăng ký/chấm dùng luôn khung
            // này, KHÔNG kiểm lại (tránh 'báo tốt mà không cho'). 2026-09-18.
            this._lastGoodDet = { det, t: Date.now() };
        }
    }

    // Lấy detection để đăng ký/chấm:
    // - Nếu vừa có khung ĐÃ XÁC NHẬN TỐT (< 2.5s) → dùng luôn, ok=true.
    // - Nếu không → chụp 1 khung mới rồi kiểm tra.
    async _getGoodDet() {
        if (this._lastGoodDet && Date.now() - this._lastGoodDet.t < 2500) {
            return { det: this._lastGoodDet.det, ok: true, issue: null };
        }
        const det = await this._detectFace();
        if (!det) {
            return { det: null, ok: false, issue: null };
        }
        const issue = this._faceIssue(det);
        return { det, ok: !issue, issue };
    }

    _gpsError(err) {
        let m = "Không lấy được vị trí GPS.";
        if (err && err.code === 1) {
            m = "Quyền vị trí đang bị CHẶN. Hãy cho phép định vị cho trang này (biểu tượng ổ khoá trên thanh địa chỉ) rồi bấm 'Lấy lại vị trí'.";
        } else if (err && err.code === 2) {
            m = "Máy không xác định được vị trí. Hãy BẬT định vị (Location) của thiết bị — hoặc dùng ĐIỆN THOẠI (chính xác hơn máy tính) rồi bấm 'Lấy lại vị trí'.";
        } else if (err && err.code === 3) {
            m = "Quá thời gian lấy GPS. Bấm 'Lấy lại vị trí' để thử lại (ra chỗ thoáng, gần cửa sổ nếu ở trong nhà).";
        }
        if (!this.state.gpsOk) {
            this.state.gpsErr = m;
        }
    }

    _startGps() {
        if (typeof window !== "undefined" && window.isSecureContext === false) {
            this.state.gpsErr = "Trang không chạy HTTPS nên trình duyệt chặn định vị. Hãy mở qua https://…";
            return;
        }
        if (!navigator.geolocation) {
            this.state.gpsErr = "Trình duyệt không hỗ trợ định vị GPS.";
            return;
        }
        this.state.gpsErr = "";
        const apply = (pos) => {
            this._lastPos = pos.coords;
            const d = haversine(
                pos.coords.latitude, pos.coords.longitude,
                this.cfg.lat, this.cfg.lng);
            this.state.distance = Math.round(d);
            this.state.gpsOk = true;
            this.state.gpsErr = "";
            this.state.withinRadius = d <= this.cfg.radius;
        };
        // 1) Lấy NHANH 1 vị trí (wifi/mạng) → hiện liền; lỗi thì báo rõ.
        navigator.geolocation.getCurrentPosition(
            apply, (e) => this._gpsError(e),
            { enableHighAccuracy: false, maximumAge: 60000, timeout: 15000 });
        // 2) Theo dõi tiếp bằng độ chính xác cao để tinh chỉnh.
        this._geoWatch = navigator.geolocation.watchPosition(
            apply, (e) => this._gpsError(e),
            { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 });
    }

    retryGps() {
        if (this._geoWatch != null && navigator.geolocation) {
            navigator.geolocation.clearWatch(this._geoWatch);
            this._geoWatch = null;
        }
        this.state.gpsOk = false;
        this.state.gpsErr = "Đang lấy lại vị trí…";
        this._startGps();
    }

    async _detectFace() {
        const v = this.videoRef.el;
        if (!v || !this._faceapi) {
            return null;
        }
        return await this._faceapi
            .detectSingleFace(
                v, new this._faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.4 }))
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
            const g = await this._getGoodDet();
            if (!g.det) {
                this.state.faceMsg = "Không thấy khuôn mặt rõ — hãy nhìn thẳng vào camera.";
                return;
            }
            if (!g.ok) {
                this.state.faceMsg = g.issue;
                this.notification.add(g.issue, { type: "warning" });
                return;
            }
            const desc = Array.from(g.det.descriptor);
            const photo = this._snapshot();
            const res = await this.orm.call("vd.face.attendance", "vd_kiosk_enroll", [
                name, this.state.enrollGender, desc, photo,
            ]);
            this.state.faceMsg = "";
            this.state.facesCount += 1;
            this.state.showEnroll = false;
            this.state.enrollName = "";
            this.state.result = { ok: true, name: res.name, code: res.code,
                line: "Đăng ký thành công" };
            this.notification.add(
                `Đăng ký thành công: ${res.name} — Mã ${res.code}`, { type: "success" });
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
        if (!this._lastPos || !this.state.gpsOk) {
            this.notification.add("Chưa lấy được vị trí GPS — hãy bật định vị rồi thử lại.", { type: "warning" });
            return;
        }
        this.state.busy = true;
        this.state.faceMsg = "Đang nhận diện…";
        this.state.result = null;
        try {
            const g = await this._getGoodDet();
            if (!g.det) {
                this.state.faceMsg = "Không thấy khuôn mặt — hãy nhìn thẳng vào camera.";
                return;
            }
            if (!g.ok) {
                this.state.faceMsg = g.issue;
                this.notification.add(g.issue, { type: "warning" });
                return;
            }
            const desc = Array.from(g.det.descriptor);
            const photo = this._snapshot();
            // KIOSK: gửi descriptor → SERVER nhận diện ai + chấm cho đúng người.
            const res = await this.orm.call("vd.face.attendance", "vd_kiosk_check", [
                desc, this._lastPos.latitude, this._lastPos.longitude, kind, 0, photo,
            ]);
            this.state.faceMsg = "";
            const emp = res.employee || {};
            if (!res.ok) {
                // Sai / không nhận ra / quá xa → hiện tên (nếu nhận ra) + lý do.
                this.state.result = {
                    ok: false, name: emp.name || "", code: emp.code || "",
                    line: res.error || "Không chấm công được.",
                };
                this.notification.add(res.error || "Không chấm công được.",
                    { type: "danger", title: emp.name ? `${emp.name} (${emp.code})` : "Không nhận diện được" });
                return;
            }
            if (res.recent) {
                this.state.recent = res.recent;
            }
            let line;
            if (kind === "in") {
                line = "✅ Chấm VÀO lúc " + (res.in_time || "");
                if (res.late_minutes) line += ` (đi muộn ${res.late_minutes} phút)`;
            } else {
                line = "✅ Chấm RA lúc " + (res.out_time || "");
                if (res.early_leave_minutes) line += ` (về sớm ${res.early_leave_minutes} phút)`;
            }
            this.state.result = { ok: true, name: emp.name, code: emp.code, line, kind };
            this.notification.add(`${emp.name} (${emp.code}) — ${line}`, { type: "success" });
        } catch (e) {
            const msg = this._errMsg(e);
            this.notification.add(msg, { type: "danger" });
            this.state.faceMsg = msg;
        } finally {
            this.state.busy = false;
        }
    }

    toggleEnroll() {
        this.state.showEnroll = !this.state.showEnroll;
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
        this._stopped = true;
        if (this._loopTimer) {
            clearTimeout(this._loopTimer);
            this._loopTimer = null;
        }
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
