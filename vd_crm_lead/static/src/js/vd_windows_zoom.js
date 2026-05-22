/** @odoo-module **/
/**
 * Trên Windows, set zoom mặc định 67% cho toàn bộ webclient (giống Ctrl+-)
 * để khớp với compact density của Mac retina. User vẫn override được qua
 * Ctrl+/- bình thường.
 *
 * Detect OS qua navigator.userAgentData (modern) hoặc fallback userAgent.
 */

function isWindows() {
    const ua =
        navigator.userAgentData?.platform ||
        navigator.userAgent ||
        navigator.platform ||
        "";
    return /Win(dows|32|64)/i.test(ua);
}

if (isWindows()) {
    document.documentElement.classList.add("vd-os-windows");
    // Áp CSS zoom đồng thời bằng class — nếu CSS chưa load (rare), set inline
    // làm fallback để không bị "loé" full size 1 nhịp.
    try {
        document.documentElement.style.zoom = "0.67";
    } catch (e) {
        /* noop */
    }
}
