# Wi-Fi Security Lab - Educational Training Dashboard

## Purpose
This application is an **authorized cybersecurity-training laboratory**. It demonstrates what information a standard website can obtain from a participating phone or computer browser, and contrasts it with what strictly requires explicit user permissions.

> **Security & Privacy Guarantee:**
> This application does **NOT** perform hacking, exploitation, packet interception, credential theft, surveillance, or unauthorized access to other devices.

---

## What the Lab Demonstrates

1. **Standard Server-Visible Network Data:**
   - Client IP address (as visible to the HTTP server).
   - HTTP `User-Agent` and `Accept-Language` headers sent by standard web requests.

2. **Standard Client-Reported Browser Info:**
   - Operating system platform, screen resolution, device pixel ratio, timezone, and online status.

3. **Explicit Browser Permission Controls:**
   - **Location:** Uses `navigator.geolocation.getCurrentPosition()`. Requires user consent via the browser's native prompt. No continuous tracking is performed.
   - **Camera:** Uses `navigator.mediaDevices.getUserMedia({ video: true })`. Triggers native permission prompt. **Immediately stops all camera tracks** without recording, storing, or uploading footage.
   - **Microphone:** Uses `navigator.mediaDevices.getUserMedia({ audio: true })`. Triggers native permission prompt. **Immediately stops all audio tracks** without recording or transmitting audio.

4. **Security Boundaries & Limitations:**
   - A normal website **cannot** read another website's cookies, passwords, SMS messages, contacts, saved Wi-Fi passwords, private files, or data belonging to other applications.

---

## Installation & Setup

### 1. Requirements
- Python 3.9+ installed on your computer.

### 2. Install Dependencies
Navigate into the project directory and install Flask:

```bash
cd wifi_security_lab
pip install -r requirements.txt
```

*(If using a virtual environment:)*
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start the Server
Run the Flask application using Python 3:

```bash
python3 app.py
```
*(Or using the project's virtual environment:)*
```bash
../.venv/bin/python3 app.py
```

The server binds to `0.0.0.0:8080`, allowing other devices on the same Wi-Fi network to connect.

---

## Connecting Authorized Test Devices

1. **Find your computer's local Wi-Fi IP address:**
   - **macOS:**
     ```bash
     ipconfig getifaddr en0
     ```
   - **Windows:**
     ```cmd
     ipconfig
     ```
     *(Look for "IPv4 Address" under your Wireless LAN adapter, e.g. `192.168.1.25`)*
   - **Linux:**
     ```bash
     ip addr
     ```

2. **Open the lab on your test device (Phone / Laptop):**
   - Connect the authorized test phone to the **same Wi-Fi network**.
   - Open any browser (Safari, Chrome, Firefox) and navigate to:
     ```
     http://YOUR-LAN-IP:8080
     ```
     *(Example: `http://192.168.1.25:8080`)*

3. **Consent & Participation:**
   - The participant must voluntarily open the URL. Same-Wi-Fi access does **not** automatically expose any private phone data to the server.
   - Click **"I Agree & Start Lab"** to initiate the demonstration.
   - Use the permission test buttons to observe how native browser permission prompts protect user hardware.
