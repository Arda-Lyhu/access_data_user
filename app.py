"""
app.py - Authorized Wi-Fi Security-Training Lab Portal

This application implements a safe, self-contained educational portal:
- Demonstrates captive portal detection probe handling (/generate_204, etc.)
- Uses Server-Sent Events (SSE) to broadcast non-sensitive lab alerts to open browsers
- Records only synthetic, non-sensitive test metadata in memory
- Does NOT inspect, capture, or harvest credentials, tokens, cookies, or device data
"""

import json
import queue
from datetime import datetime, timezone
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# In-memory storage for non-sensitive training events
events = []

# List of active client queues for Server-Sent Events (SSE)
clients = []

# HTML/JS frontend served to connected browsers
HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Wi-Fi Security Lab</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 600px;
            margin: 40px auto;
            padding: 20px;
            background: #f7f9fc;
            color: #202124;
        }
        .container {
            border: 2px solid #b00020;
            background: #ffffff;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        }
        h1 {
            color: #b00020;
            margin-top: 0;
            font-size: 1.5rem;
        }
        p {
            line-height: 1.5;
            color: #555;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            background: #eef3ff;
            border-radius: 6px;
            font-size: 0.85rem;
            margin-bottom: 16px;
        }
        input, button {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin-top: 10px;
            border-radius: 6px;
            font-size: 1rem;
        }
        input {
            border: 1px solid #ccc;
        }
        button {
            background: #0b57d0;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover {
            background: #0842a0;
        }
        #result {
            margin-top: 16px;
            font-weight: 500;
            color: #0b57d0;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>⚠️ Wi-Fi Security Lab</h1>
    <p>
        <strong>Notice:</strong> This system is strictly for authorized security education and training.
    </p>
    <p>
        This portal does <strong>not</strong> access, collect, or store passwords, cookies,
        session tokens, browser history, files, or personal messages.
    </p>

    <div class="status-badge">
        SSE Stream Status: <strong id="stream-status">Connecting...</strong>
    </div>

    <label for="test_id" style="font-size:0.85rem; color:#555;">Synthetic Test ID:</label>
    <input id="test_id" placeholder="e.g. lab-device-01" maxlength="50">

    <button onclick="runSecurityTest()">Run Security Test</button>

    <p id="result"></p>
</div>

<script>
// 1. Establish SSE connection for real-time demonstration alerts
const eventSource = new EventSource("/events/stream");

eventSource.onopen = function() {
    document.getElementById("stream-status").textContent = "Active";
};

eventSource.onmessage = function(event) {
    try {
        const payload = JSON.parse(event.data);
        // Display notification to connected user
        alert("⚠️ Wi-Fi Security Lab Alert:\\n\\n" + payload.message);
    } catch (err) {
        console.error("Error processing stream message:", err);
    }
};

eventSource.onerror = function() {
    document.getElementById("stream-status").textContent = "Disconnected / Retrying...";
};

// 2. Trigger test event
async function runSecurityTest() {
    const input = document.getElementById("test_id");
    const testId = input.value.trim();

    if (!testId) {
        document.getElementById("result").textContent = "Please provide a synthetic test ID.";
        return;
    }

    try {
        const res = await fetch("/test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ test_id: testId })
        });
        const data = await res.json();
        document.getElementById("result").textContent = data.message;
    } catch (err) {
        document.getElementById("result").textContent = "Request failed.";
        console.error(err);
    }
}
</script>

</body>
</html>
"""


# -------------------------------------------------------------------
# Core Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    """Serves the main training lab portal webpage."""
    events.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "portal_viewed"
    })
    return HTML_PAGE


@app.post("/test")
def run_test():
    """
    Handles training test trigger.
    Records only synthetic metadata and broadcasts a notification via SSE.
    """
    body = request.get_json(silent=True) or {}
    test_id = str(body.get("test_id", ""))[:50]

    # Log only synthetic metadata
    event_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "test_triggered",
        "synthetic_test_id": test_id
    }
    events.append(event_entry)

    # Broadcast notification to active SSE listeners
    broadcast_payload = {
        "message": f"Training test broadcast event. ID: {test_id}"
    }

    stale_clients = []
    for client in clients:
        try:
            client.put_nowait(broadcast_payload)
        except Exception:
            stale_clients.append(client)

    # Prune inactive connections
    for client in stale_clients:
        if client in clients:
            clients.remove(client)

    return jsonify({
        "success": True,
        "message": f"Test event recorded and broadcast (ID: {test_id})."
    })


@app.route("/events/stream")
def sse_stream():
    """
    Maintains a Server-Sent Events stream for connected clients.
    """
    client_queue = queue.Queue()
    clients.append(client_queue)

    def event_generator():
        try:
            while True:
                msg = client_queue.get()
                yield f"data: {json.dumps(msg)}\\n\\n"
        finally:
            if client_queue in clients:
                clients.remove(client_queue)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/events")
def get_events():
    """Returns the recorded synthetic test events log in JSON format."""
    return jsonify(events)


# -------------------------------------------------------------------
# Captive Portal Probe Demonstration Routes
# -------------------------------------------------------------------

@app.route("/generate_204")
def android_probe():
    """Simulates handling of Android captive portal probe."""
    return "", 302, {"Location": "/"}


@app.route("/hotspot-detect.html")
def apple_probe():
    """Simulates handling of Apple captive portal probe."""
    return "", 302, {"Location": "/"}


@app.route("/connecttest.txt")
@app.route("/ncsi.txt")
def windows_probes():
    """Simulates handling of Windows connectivity check probes."""
    return "", 302, {"Location": "/"}


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print(" Authorized Wi-Fi Security-Training Lab")
    print(" Host: 0.0.0.0 | Port: 8080")
    print(" Local address: http://127.0.0.1:8080")
    print(" Network address: http://<YOUR-LOCAL-IP>:8080")
    print("=" * 50)

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        threaded=True
    )
