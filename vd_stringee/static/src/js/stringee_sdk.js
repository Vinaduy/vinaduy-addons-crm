/** @odoo-module **/
/**
 * Stringee Web SDK service — aligned with official getting-started doc.
 *
 *   https://developer.stringee.com/docs/getting-started/getting-started-stringee-web-sdk
 *
 * Flow:
 *   1. Lazy-load SDK from cdn.stringee.com on first use.
 *   2. Fetch short-lived user JWT from /stringee/user_token (empty if user
 *      has no stringee_user_id → fallback to REST callout via /stringee/click_to_call).
 *   3. StringeeClient.connect(token); listen for `connect` / `authen` /
 *      `requestnewtoken` / `incomingcall` / `disconnect`.
 *   4. Outbound: StringeeCall2 with full event chain (addremotestream,
 *      signalingstate, mediastate, info, otherdevice, error).
 *   5. Recording: configured server-side via /stringee/answer SCCO record
 *      action — Stringee fetches it when the call is bridged to PSTN.
 *
 * Stringee signaling state codes (per SDK docs):
 *   0 CALLING, 1 RINGING, 2 ANSWERED, 3 BUSY, 4 ENDED, 5 ENDED-from-server, 6 BUSY-from-server
 */
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const SDK_URL = "https://cdn.stringee.com/sdk/web/latest/stringee-web-sdk.min.js";

/**
 * Normalize VN phone number to international format WITHOUT `+` prefix.
 * Stringee Web SDK với phone format local (vd "0348886375") sẽ classify
 * thành internal user ID → reject. Format international (vd "84348886375")
 * → Stringee detect là PSTN → đúng route.
 *
 * Tương ứng với Python `_to_stringee_number` ở vd_stringee/models/stringee_call.py
 */
function normalizeVnPhone(num, defaultCountry = "84") {
    if (!num) return "";
    const digits = String(num).replace(/\D/g, "");
    if (!digits) return "";
    if (digits.startsWith(defaultCountry)) return digits;
    if (digits.startsWith("0")) return defaultCountry + digits.slice(1);
    return defaultCountry + digits;
}

// Per-number debounce window — chặn accidental double-click trong 3s
const DEBOUNCE_MS = 3_000;

// Stringee Web SDK signalingstate codes (per official docs):
// 0=CALLING, 1=RINGING, 2=ANSWERED, 3=BUSY, 4=ENDED, 5=REJECTED, 6=ERROR
const SIGNALING_LABEL = {
    0: 'CALLING', 1: 'RINGING', 2: 'ANSWERED',
    3: 'BUSY', 4: 'ENDED', 5: 'REJECTED', 6: 'ERROR',
};
// Codes terminal — call no longer active → hangup + clear state
const TERMINAL_SIGNALING_CODES = new Set([3, 4, 5, 6]);

let _sdkPromise = null;
function loadStringeeSDK() {
    if (_sdkPromise) {
        return _sdkPromise;
    }
    _sdkPromise = new Promise((resolve, reject) => {
        if (window.StringeeClient) {
            return resolve(window.StringeeClient);
        }
        const script = document.createElement("script");
        script.src = SDK_URL;
        script.async = true;
        script.onload = () => resolve(window.StringeeClient);
        script.onerror = () => reject(new Error("Không tải được Stringee Web SDK"));
        document.head.appendChild(script);
    });
    return _sdkPromise;
}

function ensureAudioElement() {
    let audio = document.getElementById("vd_stringee_remote_audio");
    if (!audio) {
        audio = document.createElement("audio");
        audio.id = "vd_stringee_remote_audio";
        audio.autoplay = true;
        document.body.appendChild(audio);
    }
    return audio;
}

async function fetchToken() {
    const res = await rpc("/stringee/user_token", {});
    return {
        token: res?.token || "",
        userId: res?.user_id || "",
        fromNumber: res?.from_number || "",
    };
}

export const stringeeService = {
    dependencies: ["notification"],
    async start(env, { notification }) {
        const state = {
            connected: false,
            userId: "",
            fromNumber: "",  // Hotline đã mua trên Stringee — dùng làm fromNumber
                             // trong StringeeCall2 cho App-to-Phone outbound.
            client: null,
            currentCall: null,
            hasUser: null,   // null=unknown, true=có user JWT, false=fallback REST
            inFlight: null,  // promise call() đang chạy — chặn duplicate
            lastCallAt: 0,
            lastCallTo: "",
        };

        // ===================================================================
        // Setup events theo doc: connect, authen, requestnewtoken,
        // incomingcall, disconnect.
        // ===================================================================
        function attachClientEvents(client) {
            client.on("connect", () => {
                console.log("[VD-STRINGEE] client.connect — socket OK, waiting authen");
            });

            client.on("disconnect", () => {
                console.warn("[VD-STRINGEE] client.disconnect");
                state.connected = false;
            });

            // SDK báo token sắp/đã hết hạn → fetch token mới + reconnect.
            client.on("requestnewtoken", async () => {
                try {
                    const { token } = await fetchToken();
                    if (token) {
                        client.connect(token);
                    }
                } catch (e) {
                    notification.add(
                        `Stringee: không refresh được token (${e.message})`,
                        { type: "warning" },
                    );
                }
            });

            // Inbound call (SDK v1) — auto-answer + bind audio, hoặc notify nếu đang busy.
            client.on("incomingcall", (incomingCall) => {
                console.log("[VD-STRINGEE] *** incomingcall (v1) RECEIVED ***", {
                    callId: incomingCall?.callId,
                    fromNumber: incomingCall?.fromNumber,
                    toNumber: incomingCall?.toNumber,
                    fromAlias: incomingCall?.fromAlias,
                    customDataFromYourServer: incomingCall?.customDataFromYourServer,
                });
                if (state.currentCall) {
                    console.warn("[VD-STRINGEE] Busy, reject incomingcall");
                    try { incomingCall.reject(() => {}); } catch (_e) { /* noop */ }
                    return;
                }
                attachCallEvents(incomingCall);
                state.currentCall = incomingCall;
                try {
                    incomingCall.answer((res) => {
                        console.log("[VD-STRINGEE] incomingcall.answer callback:", res);
                    });
                } catch (e) {
                    console.error("[VD-STRINGEE] incomingcall.answer throw:", e);
                    notification.add(
                        `Stringee: trả lời cuộc gọi đến lỗi (${e.message})`,
                        { type: "danger" },
                    );
                    state.currentCall = null;
                }
            });

            // Inbound call (SDK v2 / StringeeCall2)
            client.on("incomingcall2", (incomingCall) => {
                console.log("[VD-STRINGEE] *** incomingcall2 (v2) RECEIVED ***", {
                    callId: incomingCall?.callId,
                    fromNumber: incomingCall?.fromNumber,
                    toNumber: incomingCall?.toNumber,
                    fromAlias: incomingCall?.fromAlias,
                    customDataFromYourServer: incomingCall?.customDataFromYourServer,
                });
                if (state.currentCall) {
                    console.warn("[VD-STRINGEE] Busy, reject incomingcall2");
                    try { incomingCall.reject(() => {}); } catch (_e) { /* noop */ }
                    return;
                }
                attachCallEvents(incomingCall);
                state.currentCall = incomingCall;
                try {
                    if (typeof incomingCall.initAnswer === "function") {
                        incomingCall.initAnswer((initRes) => {
                            console.log("[VD-STRINGEE] incomingcall2.initAnswer res:", initRes);
                            incomingCall.answer((res) => {
                                console.log("[VD-STRINGEE] incomingcall2.answer res:", res);
                            });
                        });
                    } else {
                        incomingCall.answer((res) => {
                            console.log("[VD-STRINGEE] incomingcall2.answer (no initAnswer) res:", res);
                        });
                    }
                } catch (e) {
                    console.error("[VD-STRINGEE] incomingcall2 answer throw:", e);
                    notification.add(
                        `Stringee v2: trả lời cuộc gọi đến lỗi (${e.message})`,
                        { type: "danger" },
                    );
                    state.currentCall = null;
                }
            });
        }

        // ===================================================================
        // Setup events trên call instance theo doc — full chain để debug + UX.
        // ===================================================================
        function attachCallEvents(call) {
            // Failsafe: nếu Stringee silent fail (CALL_NOT_ALLOWED, network drop),
            // không event terminal nào fire → hangup + clear sau 90s.
            const failsafe = setTimeout(() => {
                if (state.currentCall === call) {
                    console.warn("[VD-STRINGEE] FAILSAFE 45s timeout → hangup + cleanup");
                    safeHangup(call);
                    cleanupState();
                }
            }, 45_000);

            // Per Stringee doc step 6: call.hangup(callback) để đóng WebRTC peer
            // sạch sẽ (KHÔNG chỉ clear state JS — cần báo Stringee server end call).
            const safeHangup = (c) => {
                try {
                    if (c && typeof c.hangup === 'function') {
                        c.hangup((res) => {
                            console.log("[VD-STRINGEE] call.hangup res:", res);
                        });
                    }
                } catch (e) {
                    console.warn("[VD-STRINGEE] safeHangup throw:", e?.message || e);
                }
            };

            // Cleanup state: cho phép call mới ngay sau đó không bị debounce.
            const cleanupState = () => {
                clearTimeout(failsafe);
                state.currentCall = null;
                state.lastCallTo = "";
                state.lastCallAt = 0;
                state.inFlight = null;
            };

            call.on("addremotestream", (stream) => {
                console.log("[VD-STRINGEE] addremotestream — KH bắt máy, bind audio");
                ensureAudioElement().srcObject = stream;
            });

            call.on("addlocalstream", (_stream) => {
                console.log("[VD-STRINGEE] addlocalstream — mic OK");
            });

            // ===== signalingstate — theo dõi state máy của call =====
            // Per Stringee Web SDK doc: state codes 0-6
            // CALLING/RINGING/ANSWERED = active, không hangup
            // BUSY/ENDED/REJECTED/ERROR = terminal → hangup + cleanup
            call.on("signalingstate", (s) => {
                const code = s && s.code;
                const label = SIGNALING_LABEL[code] || `UNKNOWN(${code})`;
                console.log("[VD-STRINGEE] signalingstate:", label, s);
                if (code === 3) {
                    notification.add("KH bận máy", { type: "warning" });
                } else if (code === 4) {
                    notification.add("Cuộc gọi đã kết thúc", { type: "info" });
                } else if (code === 5) {
                    notification.add("KH từ chối cuộc gọi", { type: "warning" });
                } else if (code === 6) {
                    notification.add(
                        `Cuộc gọi lỗi: ${s?.reason || s?.message || 'unknown'}`,
                        { type: "danger" },
                    );
                }
                if (TERMINAL_SIGNALING_CODES.has(code)) {
                    safeHangup(call);  // explicit hangup per Step 6 docs
                    cleanupState();
                }
            });

            call.on("mediastate", (m) => {
                console.log("[VD-STRINGEE] mediastate:", m);
            });

            call.on("info", (info) => {
                console.log("[VD-STRINGEE] info (DTMF/custom):", info);
            });

            call.on("otherdevice", (data) => {
                console.log("[VD-STRINGEE] otherdevice:", data);
                if (data && (data.type === "CALL_STATE" || data.type === "ANSWERED")) {
                    notification.add("Cuộc gọi đã được xử lý ở thiết bị khác", { type: "info" });
                    safeHangup(call);
                    cleanupState();
                }
            });

            // ===== error event — bất kỳ lỗi nào → hangup + notify =====
            call.on("error", (e) => {
                console.error("[VD-STRINGEE] call.error:", e);
                notification.add(
                    `Stringee error: ${e?.message || JSON.stringify(e)}`,
                    { type: "danger", sticky: true },
                );
                safeHangup(call);
                cleanupState();
            });
        }

        // ===================================================================
        // Kết nối client (idempotent). Trả về null nếu user không có
        // stringee_user_id → caller dùng REST fallback.
        // ===================================================================
        async function ensureConnected() {
            if (state.connected && state.client) {
                console.log("[VD-STRINGEE] ensureConnected: already connected");
                return state.client;
            }
            console.log("[VD-STRINGEE] ensureConnected: fetching token...");
            const { token, userId, fromNumber } = await fetchToken();
            console.log("[VD-STRINGEE] fetchToken result:", {
                hasToken: !!token, tokenLen: token?.length,
                userId, fromNumber,
            });
            if (!token) {
                state.hasUser = false;
                return null;
            }
            state.hasUser = true;
            await loadStringeeSDK();
            console.log("[VD-STRINGEE] SDK loaded, version:",
                window.StringeeUtil?.version || "unknown");
            state.userId = userId;
            state.fromNumber = fromNumber;
            state.client = new window.StringeeClient();
            attachClientEvents(state.client);

            return new Promise((resolve, reject) => {
                let settled = false;
                state.client.on("authen", (res) => {
                    console.log("[VD-STRINGEE] authen event:", res);
                    // Ping server để có evidence trong log: browser đã authen
                    try {
                        rpc("/stringee/heartbeat", {
                            ok: res?.r === 0,
                            r_code: res?.r,
                            message: res?.message || "",
                            userId: userId,
                        }).catch(() => {});
                    } catch (_e) { /* noop */ }
                    if (settled) return;
                    settled = true;
                    if (res && res.r === 0) {
                        state.connected = true;
                        console.log("[VD-STRINGEE] ✓ AUTHENTICATED as", userId);
                        resolve(state.client);
                    } else {
                        reject(new Error(`Stringee authen failed: ${res && res.message}`));
                    }
                });
                console.log("[VD-STRINGEE] calling client.connect(token)...");
                state.client.connect(token);
            });
        }

        // ===================================================================
        // AUTO-CONNECT at startup — browser cần online với Stringee để nhận
        // incomingcall2 từ SCCO `connect to=internal` (REST callout flow).
        // Fire-and-forget; nếu user không có stringee_user_id thì silent skip.
        // ===================================================================
        console.log("[VD-STRINGEE] Service start — initiating auto-connect...");
        ensureConnected()
            .then((c) => console.log("[VD-STRINGEE] Auto-connect OK, client:", !!c))
            .catch((e) => console.warn("[VD-STRINGEE] Auto-connect failed:", e?.message || e));

        // ===================================================================
        // Outbound call — qua Web SDK nếu có user, ngược lại fallback REST.
        // ===================================================================
        async function call(targetNumberRaw) {
            console.log("[VD-STRINGEE] call() invoked with:", targetNumberRaw,
                        " | currentCall:", !!state.currentCall,
                        " | inFlight:", !!state.inFlight,
                        " | lastCallTo:", state.lastCallTo,
                        " | lastCallAt:", state.lastCallAt,
                        " | ageMs:", state.lastCallAt ? Date.now() - state.lastCallAt : 'N/A');
            if (!targetNumberRaw) {
                console.warn("[VD-STRINGEE] call() — missing number");
                throw new Error("Thiếu số gọi");
            }
            const targetNumber = normalizeVnPhone(targetNumberRaw);
            console.log("[VD-STRINGEE] normalized:", targetNumberRaw, "→", targetNumber);
            if (!targetNumber) {
                throw new Error(`Số không hợp lệ: ${targetNumberRaw}`);
            }
            // (1) Đang có call() in-flight → return promise đó
            if (state.inFlight) {
                return state.inFlight;
            }
            // (2) Đang có call active Web SDK → check stuck state
            if (state.currentCall) {
                // Nếu lastCallAt > 60s = stuck state (call thực chỉ chạy max 30s).
                // Force-cleanup + cho phép call mới.
                const ageMs = state.lastCallAt ? (Date.now() - state.lastCallAt) : Infinity;
                if (ageMs > 35_000) {
                    console.warn("[VD-STRINGEE] currentCall STUCK %ds → force reset", Math.floor(ageMs/1000));
                    try { state.currentCall.hangup(() => {}); } catch (_e) {}
                    state.currentCall = null;
                    state.lastCallTo = "";
                    state.lastCallAt = 0;
                } else {
                    notification.add(
                        "Đang có cuộc gọi diễn ra. Cúp máy trước khi gọi tiếp.",
                        { type: "warning" },
                    );
                    return state.currentCall;
                }
            }
            // (3) Per-number debounce 3s
            const now = Date.now();
            if (state.lastCallTo === targetNumber && (now - state.lastCallAt) < DEBOUNCE_MS) {
                return null;
            }

            state.inFlight = (async () => {
                let client;
                try {
                    client = await ensureConnected();
                } catch (e) {
                    notification.add(e.message, { type: "danger" });
                    client = null;
                }

                // Không có user → REST fallback (server-side dedup 30s)
                if (!client) {
                    const res = await rpc("/stringee/click_to_call", { callee: targetNumber });
                    notification.add(
                        res.error
                            ? `Lỗi: ${res.error}`
                            : `Đã gửi yêu cầu gọi ${targetNumber}`,
                        { type: res.error ? "danger" : "info" },
                    );
                    return res;
                }

                // Web SDK App-to-Phone — per Stringee docs (StringeeCall v1):
                //   new StringeeCall(client, fromNumber, toNumber, isVideoCall)
                //   fromNumber = số hotline đã mua trên Stringee (84xxx)
                //   toNumber   = phone number của KH (PSTN)
                // Đổi sang v1 theo yêu cầu đối tác: call thường dùng StringeeCall
                // thay vì StringeeCall2 (StringeeCall2 cho video / advanced).
                if (!state.fromNumber) {
                    notification.add(
                        "Chưa cấu hình hotline Stringee (vd_stringee.from_number).",
                        { type: "danger" },
                    );
                    return null;
                }
                const call2 = new window.StringeeCall(
                    client, state.fromNumber, targetNumber, false,
                );
                try {
                    call2.custom = JSON.stringify({
                        source: "vd_crm_lead",
                        odoo_user_id: state.userId,
                        callee: targetNumber,
                    });
                } catch (_e) { /* SDK chưa support custom → bỏ qua */ }

                attachCallEvents(call2);
                state.currentCall = call2;

                call2.makeCall((res) => {
                    if (res && res.r !== 0) {
                        notification.add(
                            `Gọi thất bại: ${res.message}`,
                            { type: "danger" },
                        );
                        // Clear hoàn toàn — cho retry ngay không bị debounce
                        state.currentCall = null;
                        state.lastCallTo = "";
                        state.lastCallAt = 0;
                    }
                });
                return call2;
            })();

            try {
                const result = await state.inFlight;
                state.lastCallAt = Date.now();
                state.lastCallTo = targetNumber;
                return result;
            } finally {
                state.inFlight = null;
            }
        }

        function hangup() {
            // Per Stringee Web SDK getting-started Step 6:
            // call.hangup(callback) — graceful hangup.
            // Cleanup state fully để cho phép call mới ngay sau đó không bị debounce.
            const cur = state.currentCall;
            if (cur) {
                try {
                    cur.hangup((res) => {
                        console.log("[VD-STRINGEE] hangup res:", res);
                    });
                } catch (e) {
                    console.warn("[VD-STRINGEE] hangup throw:", e);
                }
            }
            state.currentCall = null;
            state.lastCallTo = "";
            state.lastCallAt = 0;
            state.inFlight = null;
        }

        return { state, call, hangup, ensureConnected };
    },
};

registry.category("services").add("stringee", stringeeService);
