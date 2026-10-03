"""
wifi_security_lab - app.py

Authorized Cybersecurity Training Laboratory.
Demonstrates what data a normal website/browser can expose versus what requires explicit user permissions.
Contains NO hacking, exploitation, surveillance, or unauthorized access tools.
"""

import json
import queue
import secrets
from datetime import datetime, timezone
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

# In-memory storage for active lab sessions and events
sessions = {}
events = []
sse_clients = []


def get_client_ip(req):
    """
    Returns the remote address directly visible to Flask.
    Does not trust spoofable client headers.
    """
    return req.remote_addr or "Unknown"


def broadcast_event(message, event_type="notification"):
    """
    Broadcasts a JSON message to all active SSE client queues.
    Removes dead/disconnected clients safely.
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "message": message,
    }
    events.append(payload)

    dead = []
    for client in sse_clients:
        try:
            client.put_nowait(payload)
        except Exception:
            dead.append(client)

    for client in dead:
        if client in sse_clients:
            sse_clients.remove(client)


# -------------------------------------------------------------------
# Page & SSE Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    """Serves the main security dashboard."""
    return render_template("index.html")


@app.route("/events")
def get_events():
    """Returns recorded lab events log as JSON."""
    return jsonify({
        "total": len(events),
        "events": events[-50:]  # Return most recent 50
    })


@app.route("/events/stream")
def sse_stream():
    """
    Server-Sent Events endpoint.
    Maintains a continuous connection per active lab participant browser.
    """
    client_queue = queue.Queue()
    sse_clients.append(client_queue)

    def event_generator():
        try:
            # Send initial keepalive/welcome
            init_msg = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "connected",
                "message": "Connected to Wi-Fi Security Lab SSE stream."
            }
            yield f"data: {json.dumps(init_msg)}\n\n"

            while True:
                msg = client_queue.get()
                yield f"data: {json.dumps(msg)}\n\n"
        finally:
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.post("/api/session")
def create_session():
    """
    Registers a synthetic session after participant consent.
    Collects only standard server-visible HTTP metadata.
    """
    data = request.get_json(silent=True) or {}
    nickname = str(data.get("nickname", "Anonymous"))[:50].strip() or "Anonymous"

    # Generate synthetic session token
    session_id = secrets.token_hex(4).upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    server_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")[:300]
    accept_lang = request.headers.get("Accept-Language", "Unknown")[:100]

    session_record = {
        "session_id": session_id,
        "nickname": nickname,
        "connected_at": now_iso,
        "network": {
            "server_ip": server_ip,
            "user_agent": user_agent,
            "accept_language": accept_lang
        },
        "browser": {},
        "permissions": {
            "location": "NOT TESTED",
            "camera": "NOT TESTED",
            "microphone": "NOT TESTED"
        }
    }
    sessions[session_id] = session_record

    broadcast_event(
        f"Participant '{nickname}' joined the lab (Session: {session_id})",
        event_type="participant_joined"
    )

    return jsonify({
        "success": True,
        "session": session_record
    })


@app.post("/api/browser-info")
def update_browser_info():
    """
    Receives non-sensitive browser environment metadata sent by the client.
    """
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", ""))[:50]

    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 404

    # Sanitize and store standard browser parameters
    info = data.get("info", {})
    cleaned_info = {
        "user_agent": str(info.get("userAgent", ""))[:300],
        "platform": str(info.get("platform", ""))[:50],
        "language": str(info.get("language", ""))[:50],
        "time_zone": str(info.get("timeZone", ""))[:50],
        "screen_resolution": f"{int(info.get('screenWidth', 0))}x{int(info.get('screenHeight', 0))}",
        "device_pixel_ratio": float(info.get("devicePixelRatio", 1.0)),
        "cookies_enabled": bool(info.get("cookiesEnabled", False)),
        "online_status": bool(info.get("onlineStatus", True))
    }

    sessions[session_id]["browser"] = cleaned_info
    return jsonify({"success": True, "browser": cleaned_info})


@app.post("/api/permission-result")
def update_permission():
    """
    Records the outcome (GRANTED/DENIED/ERROR) of a browser permission test.
    """
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", ""))[:50]
    perm_type = str(data.get("permission", ""))[:20].lower()
    result = str(data.get("result", "NOT TESTED"))[:20].upper()

    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 404

    if perm_type in ["location", "camera", "microphone"]:
        sessions[session_id]["permissions"][perm_type] = result
        nickname = sessions[session_id]["nickname"]
        broadcast_event(
            f"Session {session_id} ({nickname}) tested {perm_type.upper()}: {result}",
            event_type="permission_test"
        )
        return jsonify({"success": True, "permissions": sessions[session_id]["permissions"]})

    return jsonify({"error": "Unknown permission type"}), 400


@app.post("/api/test")
def trigger_lab_test():
    """
    Triggers a harmless training event that broadcasts across all open lab dashboards.
    """
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "UNKNOWN"))[:50]
    nickname = sessions.get(session_id, {}).get("nickname", "Participant")

    msg = f"Security training event triggered by session {session_id} ({nickname})."
    broadcast_event(msg, event_type="lab_test")

    return jsonify({
        "success": True,
        "message": msg
    })


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print(" Wi-Fi Security Lab - Educational Training Dashboard")
    print(" Running on: http://0.0.0.0:8080")
    print(" Localhost:  http://127.0.0.1:8080")
    print(" Debug Mode: False (Disabled)")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        threaded=True
    )
