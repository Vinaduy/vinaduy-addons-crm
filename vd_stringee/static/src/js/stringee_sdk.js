/** @odoo-module **/
/**
 * Stringee Web SDK service.
 *
 * - Lazy-loads the SDK from cdn.stringee.com on first use.
 * - Connects with a short-lived user JWT fetched from /stringee/user_token.
 * - Falls back to REST callout (server-side) when the user has no stringee_user_id.
 *
 * Refs:
 *   https://developer.stringee.com/docs/getting-started/getting-started-stringee-web-sdk
 */
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const SDK_URL = "https://cdn.stringee.com/sdk/web/latest/stringee-web-sdk.min.js";

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

export const stringeeService = {
    dependencies: ["notification"],
    async start(env, { notification }) {
        const state = {
            connected: false,
            userId: "",
            client: null,
            currentCall: null,
            hasUser: null,  // null=unknown, true=has stringee_user_id, false=fallback REST
        };

        async function ensureConnected() {
            if (state.connected && state.client) {
                return state.client;
            }
            const { token, user_id } = await rpc("/stringee/user_token", {});
            if (!token) {
                state.hasUser = false;
                return null;
            }
            state.hasUser = true;
            await loadStringeeSDK();
            state.userId = user_id;
            state.client = new window.StringeeClient();
            return new Promise((resolve, reject) => {
                let settled = false;
                state.client.on("authen", (res) => {
                    if (settled) return;
                    settled = true;
                    if (res && res.r === 0) {
                        state.connected = true;
                        resolve(state.client);
                    } else {
                        reject(new Error(`Stringee authen failed: ${res && res.message}`));
                    }
                });
                state.client.on("disconnect", () => { state.connected = false; });
                state.client.connect(token);
            });
        }

        async function call(targetNumber) {
            if (!targetNumber) {
                throw new Error("Thiếu số gọi");
            }
            let client;
            try {
                client = await ensureConnected();
            } catch (e) {
                notification.add(e.message, { type: "danger" });
                client = null;
            }
            if (!client) {
                // Fallback: server-side REST callout (no Web SDK).
                const res = await rpc("/stringee/click_to_call", { callee: targetNumber });
                notification.add(
                    res.error
                        ? `Lỗi: ${res.error}`
                        : `Đã gửi yêu cầu gọi ${targetNumber} (REST callout)`,
                    { type: res.error ? "danger" : "info" },
                );
                return res;
            }
            const call2 = new window.StringeeCall2(client, state.userId, targetNumber, false);
            call2.on("addremotestream", (stream) => {
                ensureAudioElement().srcObject = stream;
            });
            call2.on("signalingstate", (s) => {
                if (s && (s.code === 5 || s.code === 6)) {
                    state.currentCall = null;
                }
            });
            call2.on("error", (e) => {
                notification.add(`Stringee error: ${JSON.stringify(e)}`, { type: "danger" });
            });
            call2.makeCall((res) => {
                if (res && res.r !== 0) {
                    notification.add(`Gọi thất bại: ${res.message}`, { type: "danger" });
                }
            });
            state.currentCall = call2;
            return call2;
        }

        function hangup() {
            if (state.currentCall) {
                try {
                    state.currentCall.hangup();
                } catch (e) {
                    // Ignore
                }
                state.currentCall = null;
            }
        }

        return { state, call, hangup, ensureConnected };
    },
};

registry.category("services").add("stringee", stringeeService);
