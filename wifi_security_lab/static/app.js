/**
 * Wi-Fi Security Lab - Client Application Logic
 *
 * Demonstrates:
 * 1. Consent gating: Does not inspect browser parameters until user explicitly agrees.
 * 2. Standard browser APIs: Screen size, user-agent, timezone, online status.
 * 3. Permission API Demonstrations:
 *    - Geolocation: navigator.geolocation.getCurrentPosition()
 *    - Camera: navigator.mediaDevices.getUserMedia({ video: true })
 *    - Microphone: navigator.mediaDevices.getUserMedia({ audio: true })
 *    All media tracks are immediately stopped upon grant. No recording or exfiltration.
 * 4. Server-Sent Events (SSE) listener for live notifications.
 */

let currentSession = null;
let eventSource = null;

document.addEventListener("DOMContentLoaded", () => {
    setupConsentModal();
    setupTestButtons();
});

// -------------------------------------------------------------------
// 1. Consent Gating & Session Initialization
// -------------------------------------------------------------------

function setupConsentModal() {
    const consentBtn = document.getElementById("consent-btn");
    const nicknameInput = document.getElementById("nickname-input");
    const modal = document.getElementById("consent-modal");

    consentBtn.addEventListener("click", async () => {
        const nickname = nicknameInput.value.trim() || "Anonymous";

        try {
            // Step 1: Register session with server
            const res = await fetch("/api/session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nickname })
            });

            const data = await res.json();
            if (!data.success) throw new Error("Session registration failed");

            currentSession = data.session;
            modal.classList.add("hidden");

            // Step 2: Render initial server-visible data
            renderSessionData(currentSession);

            // Step 3: Collect and submit client-side browser info
            collectAndSendBrowserInfo();

            // Step 4: Connect to live SSE stream
            initSSE();

        } catch (err) {
            alert("Could not start lab session: " + err.message);
        }
    });
}

function renderSessionData(session) {
    document.getElementById("val-session-id").textContent = session.session_id;
    document.getElementById("val-nickname").textContent = session.nickname;
    document.getElementById("val-connected-at").textContent = new Date(session.connected_at).toLocaleTimeString();

    document.getElementById("val-server-ip").textContent = session.network.server_ip;
    document.getElementById("val-user-agent").textContent = session.network.user_agent;
    document.getElementById("val-accept-lang").textContent = session.network.accept_language;
}

// -------------------------------------------------------------------
// 2. Client-Side Browser Information
// -------------------------------------------------------------------

async function collectAndSendBrowserInfo() {
    const browserInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform || "Unknown",
        language: navigator.language || "Unknown",
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Unknown",
        screenWidth: window.screen.width,
        screenHeight: window.screen.height,
        devicePixelRatio: window.devicePixelRatio || 1,
        cookiesEnabled: navigator.cookieEnabled,
        onlineStatus: navigator.onLine
    };

    // Render directly on dashboard
    document.getElementById("val-platform").textContent = browserInfo.platform;
    document.getElementById("val-language").textContent = browserInfo.language;
    document.getElementById("val-timezone").textContent = browserInfo.timeZone;
    document.getElementById("val-resolution").textContent = `${browserInfo.screenWidth} x ${browserInfo.screenHeight}`;
    document.getElementById("val-dpr").textContent = browserInfo.devicePixelRatio;
    document.getElementById("val-cookies").textContent = browserInfo.cookiesEnabled ? "Yes" : "No";
    document.getElementById("val-online").textContent = browserInfo.onlineStatus ? "Online" : "Offline";

    // Send to server
    try {
        await fetch("/api/browser-info", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                info: browserInfo
            })
        });
    } catch (e) {
        console.error("Failed to sync browser info:", e);
    }
}

// -------------------------------------------------------------------
// 3. Permission Tests (Location, Camera, Microphone)
// -------------------------------------------------------------------

function setupTestButtons() {
    // Location Test
    document.getElementById("btn-test-location").addEventListener("click", testLocationPermission);

    // Camera Test
    document.getElementById("btn-test-camera").addEventListener("click", testCameraPermission);

    // Microphone Test
    document.getElementById("btn-test-microphone").addEventListener("click", testMicrophonePermission);

    // Run Security Test Button
    document.getElementById("trigger-test-btn").addEventListener("click", async () => {
        if (!currentSession) return;
        try {
            await fetch("/api/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: currentSession.session_id })
            });
        } catch (e) {
            console.error("Failed to trigger lab test:", e);
        }
    });
}

function updatePermStatus(type, status, detail = "") {
    const badge = document.getElementById(`status-${type}`);
    badge.className = `perm-badge ${status.toLowerCase()}`;
    badge.textContent = status;

    if (detail) {
        const detailEl = document.getElementById(`${type === "microphone" ? "mic" : type}-detail`);
        if (detailEl) detailEl.textContent = detail;
    }

    if (currentSession) {
        fetch("/api/permission-result", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                permission: type,
                result: status
            })
        }).catch(err => console.error(err));
    }
}

function testLocationPermission() {
    if (!("geolocation" in navigator)) {
        updatePermStatus("location", "UNSUPPORTED", "API not supported");
        return;
    }

    // Prompts native browser dialog
    navigator.geolocation.getCurrentPosition(
        (position) => {
            // Success: only display if participant explicitly grants permission
            const lat = position.coords.latitude.toFixed(4);
            const lon = position.coords.longitude.toFixed(4);
            updatePermStatus("location", "GRANTED", `Lat: ${lat}, Lon: ${lon} (1-time sample)`);
        },
        (error) => {
            // Denied or error
            updatePermStatus("location", "DENIED", error.message || "Permission declined");
        },
        { timeout: 10000, enableHighAccuracy: false, maximumAge: 60000 }
    );
}

async function testCameraPermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        updatePermStatus("camera", "UNSUPPORTED", "getUserMedia unsupported");
        return;
    }

    try {
        // Prompts native camera permission
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        updatePermStatus("camera", "GRANTED", "Camera accessed (tracks stopped immediately)");

        // PRIVACY RULE: Immediately stop all tracks. Do not record or save.
        stream.getTracks().forEach(track => track.stop());
    } catch (err) {
        updatePermStatus("camera", "DENIED", err.name || "Access denied");
    }
}

async function testMicrophonePermission() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        updatePermStatus("microphone", "UNSUPPORTED", "getUserMedia unsupported");
        return;
    }

    try {
        // Prompts native audio permission
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        updatePermStatus("microphone", "GRANTED", "Microphone accessed (tracks stopped immediately)");

        // PRIVACY RULE: Immediately stop all tracks. Do not record or save.
        stream.getTracks().forEach(track => track.stop());
    } catch (err) {
        updatePermStatus("microphone", "DENIED", err.name || "Access denied");
    }
}

// -------------------------------------------------------------------
// 4. Server-Sent Events (SSE)
// -------------------------------------------------------------------

function initSSE() {
    const badge = document.getElementById("sse-status");
    eventSource = new EventSource("/events/stream");

    eventSource.onopen = () => {
        badge.textContent = "SSE: Live";
        badge.classList.add("online");
    };

    eventSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            appendEventLog(data.timestamp, data.message);
        } catch (err) {
            console.error("Error parsing event stream message:", err);
        }
    };

    eventSource.onerror = () => {
        badge.textContent = "SSE: Reconnecting...";
        badge.classList.remove("online");
    };
}

function appendEventLog(timestamp, message) {
    const logBox = document.getElementById("events-log");
    const line = document.createElement("div");
    line.className = "event-line";

    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    line.innerHTML = `<span class="event-time">[${timeStr}]</span> ${escapeHtml(message)}`;

    logBox.appendChild(line);
    logBox.scrollTop = logBox.scrollHeight;
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}
