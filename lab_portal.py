from flask import Flask, request, jsonify, Response
from datetime import datetime, timezone
import json
import queue

app = Flask(__name__)

# Store lab events in memory.
events = []

# Each connected browser gets its own queue.
clients = []


HTML = """<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">

    <title>Wi-Fi Security Lab</title>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", Roboto, sans-serif;

            max-width: 600px;
            margin: 40px auto;
            padding: 20px;

            background: #f7f9fc;
            color: #333;
        }

        .warning {
            border: 2px solid #b00020;
            background: white;
            padding: 24px;
            border-radius: 12px;

            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
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

        input,
        button {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin-top: 12px;
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

        .status {
            padding: 10px;
            margin-top: 15px;
            border-radius: 6px;
            background: #eef3ff;
        }
    </style>
</head>

<body>

<div class="warning">

    <h1>⚠️ Wi-Fi Security Lab</h1>

    <p>
        This is an authorized security-training demonstration.
    </p>

    <p>
        This demonstration does <strong>NOT</strong> collect passwords,
        cookies, files, messages, authentication tokens,
        or browser history.
    </p>

    <div class="status">
        Connection:
        <strong id="connection">Connecting...</strong>
    </div>

    <label
        for="test_id"
        style="font-size:0.85rem;color:#666;"
    >
        Synthetic test ID:
    </label>

    <input
        id="test_id"
        placeholder="e.g. test-session-01"
        maxlength="50"
    >

    <button onclick="runTest()">
        Run Security Test
    </button>

    <p id="result"></p>

</div>


<script>

// ---------------------------------------------------------
// CONNECT TO FLASK USING SERVER-SENT EVENTS
// ---------------------------------------------------------

const source = new EventSource("/events/stream");


source.onopen = function() {

    document.getElementById("connection").textContent =
        "Connected";
};


// Receive an event from Flask.
source.onmessage = function(event) {

    const data = JSON.parse(event.data);

    console.log("Received lab event:", data);

    // Display an alert on this browser.
    alert(
        "⚠️ Wi-Fi Security Lab\\n\\n" +
        data.message
    );
};


source.onerror = function() {

    document.getElementById("connection").textContent =
        "Disconnected / reconnecting...";
};


// ---------------------------------------------------------
// RUN TEST
// ---------------------------------------------------------

async function runTest() {

    const input = document.getElementById("test_id");

    const id = input.value.trim();

    if (!id) {

        document.getElementById("result").textContent =
            "Please enter a synthetic test ID.";

        return;
    }


    try {

        const response = await fetch("/test", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                test_id: id
            })
        });


        const result = await response.json();


        document.getElementById("result").textContent =
            result.message;

    }
    catch (error) {

        document.getElementById("result").textContent =
            "Request failed.";

        console.error(error);
    }
}

</script>

</body>
</html>
"""


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@app.route("/")
def portal():

    events.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "event": "portal_opened"
    })

    return HTML


# ---------------------------------------------------------
# SECURITY TEST
# ---------------------------------------------------------

@app.post("/test")
def test():

    data = request.get_json(silent=True) or {}

    # Only synthetic information is accepted.
    test_id = str(data.get("test_id", ""))[:50]

    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": "test_completed",
        "test_id": test_id
    }

    events.append(event)


    # Send an alert to all currently connected browsers.
    message = {
        "message":
            f"Security test completed successfully. "
            f"Test ID: {test_id}"
    }


    dead_clients = []


    for client in clients:

        try:
            client.put_nowait(message)

        except Exception:
            dead_clients.append(client)


    # Remove disconnected clients.
    for client in dead_clients:

        if client in clients:
            clients.remove(client)


    return jsonify({
        "success": True,
        "message": "Security test completed safely."
    })


# ---------------------------------------------------------
# SERVER-SENT EVENTS STREAM
# ---------------------------------------------------------

@app.route("/events/stream")
def events_stream():

    # Create a queue for this browser.
    client_queue = queue.Queue()

    clients.append(client_queue)


    def generate():

        try:

            # Keep this connection alive.
            while True:

                message = client_queue.get()

                yield (
                    "data: "
                    + json.dumps(message)
                    + "\\n\\n"
                )

        finally:

            # Browser disconnected.
            if client_queue in clients:
                clients.remove(client_queue)


    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ---------------------------------------------------------
# CAPTIVE PORTAL DETECTION ENDPOINTS
# ---------------------------------------------------------

@app.route("/generate_204")
def android_check():

    return "", 302, {
        "Location": "/"
    }


@app.route("/hotspot-detect.html")
def apple_check():

    return "", 302, {
        "Location": "/"
    }


@app.route("/connecttest.txt")
def windows_check():

    return "", 302, {
        "Location": "/"
    }


@app.route("/ncsi.txt")
def windows_ncsi():

    return "", 302, {
        "Location": "/"
    }


# ---------------------------------------------------------
# VIEW LAB EVENTS
# ---------------------------------------------------------

@app.route("/events")
def show_events():

    return jsonify(events)


# ---------------------------------------------------------
# START SERVER
# ---------------------------------------------------------

if __name__ == "__main__":

    print("=" * 40)
    print(" Wi-Fi Security Lab")
    print("=" * 40)

    print()
    print("Open on this computer:")
    print("http://127.0.0.1:8080")

    print()
    print("For other devices on the same Wi-Fi:")
    print("http://YOUR-LAN-IP:8080")

    print()
    print("Example:")
    print("http://192.168.1.25:8080")

    print()
    print("Press CTRL+C to stop.")
    print("=" * 40)


    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        threaded=True
    )