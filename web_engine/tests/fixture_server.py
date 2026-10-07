"""
🌌 Orion × Nebula Web Engine - Local Fixture Server
Lightweight local HTTP testbed server providing zero-network-flakiness testing for:
- Cookie banner with 'Reject all' and 'Accept all'
- Role-based search input
- Dynamic infinite scroll catalog
- Form authentication and iframe content
"""

import http.server
import threading
import time
from typing import Optional

FIXTURE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Orion WebEngine Testbed</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f8f9fa; min-height: 2500px; }
        .cookie-modal { position: fixed; bottom: 10px; right: 10px; background: #fff; padding: 15px; border: 1px solid #ccc; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 8px; z-index: 1000; }
        .card { background: #fff; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; height: 120px; }
        .container { max-width: 800px; margin: auto; }
        #cmp-pref-panel { display: none; margin-top: 10px; border-top: 1px dashed #aaa; padding-top: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Orion WebEngine Testbed</h1>

        <!-- 1. Direct Cookie Banner -->
        <div id="cookie-banner" class="cookie-modal" role="dialog" aria-modal="true">
            <p>We value your privacy.</p>
            <button id="reject-btn" role="button">Reject all</button>
            <button id="accept-btn" role="button">Accept all</button>
        </div>

        <!-- 2. Multi-step CMP Banner (OneTrust / Cookiebot simulation) -->
        <div id="cmp-modal" class="cookie-modal" role="dialog" style="bottom: 120px; display: none;">
            <p>CMP Privacy Preferences</p>
            <button id="cmp-manage-btn" role="button">Manage preferences</button>
            <div id="cmp-pref-panel">
                <button id="cmp-reject-all" role="button">Reject all</button>
                <button id="cmp-confirm-btn" role="button">Confirm my choices</button>
            </div>
        </div>

        <!-- 3. Portal Search -->
        <section id="search-section">
            <h2>Portal Search</h2>
            <input type="search" role="searchbox" aria-label="Search" id="search-input" placeholder="Search catalog..." />
            <button role="button" id="search-button">Search</button>
            <div id="search-results"></div>
        </section>

        <!-- 4. Delayed Element Container (Appears after 500ms) -->
        <section id="delayed-section">
            <h2>Delayed Dynamic Rendering</h2>
            <div id="delayed-container"></div>
        </section>

        <!-- 5. Sensitive Target Actions (Dangerous Buttons) -->
        <section id="sensitive-section">
            <h2>Sensitive Target Guards</h2>
            <button id="place-order-btn" role="button">Place order</button>
            <button id="delete-account-btn" role="button">Delete account</button>
        </section>

        <!-- 6. Shadow DOM Host -->
        <section id="shadow-section">
            <h2>Shadow DOM Component</h2>
            <div id="shadow-host"></div>
        </section>

        <!-- 7. Popup Link -->
        <section id="popup-section">
            <h2>Popup Link</h2>
            <a id="popup-link" href="/popup" target="_blank">Open New Tab</a>
        </section>

        <!-- 8. Infinite Scroll Catalog -->
        <section id="catalog-section">
            <h2>Infinite Scroll Catalog</h2>
            <div id="catalog-list">
                <div class="card item-card"><h3>Item 1</h3><span class="price">$10.00</span></div>
                <div class="card item-card"><h3>Item 2</h3><span class="price">$20.00</span></div>
                <div class="card item-card"><h3>Item 3</h3><span class="price">$30.00</span></div>
            </div>
        </section>

        <section id="iframe-section">
            <h2>Nested Frames & Iframe Consent</h2>
            <iframe id="test-iframe" srcdoc="<p id='frame-text'>Inside Test Iframe</p>"></iframe>
            <iframe id="consent-iframe" srcdoc="<div role='dialog' aria-modal='true'><button id='iframe-reject-btn' role='button'>Reject all</button></div>"></iframe>
            <iframe id="parent-frame" srcdoc="<iframe id='child-frame' srcdoc='<p id=&quot;nested-child-text&quot;>Nested Child Content</p>'></iframe>"></iframe>
        </section>
    </div>

    <script>
        document.getElementById('reject-btn').onclick = () => {
            document.getElementById('cookie-banner').style.display = 'none';
        };
        document.getElementById('accept-btn').onclick = () => {
            document.getElementById('cookie-banner').style.display = 'none';
        };

        // Multi-step CMP handlers
        document.getElementById('cmp-manage-btn').onclick = () => {
            document.getElementById('cmp-pref-panel').style.display = 'block';
        };
        document.getElementById('cmp-reject-all').onclick = () => {
            document.getElementById('cmp-modal').style.display = 'none';
        };
        document.getElementById('cmp-confirm-btn').onclick = () => {
            document.getElementById('cmp-modal').style.display = 'none';
        };

        document.getElementById('search-button').onclick = () => {
            const q = document.getElementById('search-input').value;
            const res = document.getElementById('search-results');
            res.innerHTML = '<div class="card">Result for: ' + q + '</div>';
        };

        // 500ms delayed element injection (catches instant is_visible() bug)
        setTimeout(() => {
            const container = document.getElementById('delayed-container');
            if (container) {
                const btn = document.createElement('button');
                btn.id = 'delayed-target-btn';
                btn.setAttribute('role', 'button');
                btn.textContent = 'Delayed Action Button';
                container.appendChild(btn);
            }
        }, 500);

        // Shadow DOM setup
        const shadowHost = document.getElementById('shadow-host');
        if (shadowHost) {
            const shadowRoot = shadowHost.attachShadow({ mode: 'open' });
            shadowRoot.innerHTML = '<button id="shadow-inside-btn" role="button">Shadow Action</button>';
        }

        // Simulated infinite scroll
        let itemIndex = 4;
        window.onscroll = () => {
            if (window.scrollY > 200 && itemIndex <= 10) {
                const list = document.getElementById('catalog-list');
                const div = document.createElement('div');
                div.className = 'card item-card';
                div.innerHTML = '<h3>Item ' + itemIndex + '</h3><span class="price">$' + (itemIndex * 10) + '.00</span>';
                list.appendChild(div);
                itemIndex++;
            }
        };
    </script>
</body>
</html>
"""

POPUP_HTML = """<!DOCTYPE html>
<html><head><title>Popup Window</title></head><body><h1>Popup Window Loaded</h1></body></html>"""


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/rate-limit":
            # Simulate 429 Too Many Requests with Retry-After header
            self.send_response(429)
            self.send_header("Retry-After", "1")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Rate limit reached. Retry-After: 1")
            return

        if self.path == "/popup":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(POPUP_HTML.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(POPUP_HTML.encode("utf-8"))
            return

        if self.path == "/session-check":
            cookie_header = self.headers.get("Cookie", "")
            if "session_token=active_valid_session" in cookie_header:
                body = b"Session is valid"
                self.send_response(200)
            else:
                body = b"Session expired. Please log in."
                self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(FIXTURE_HTML.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(FIXTURE_HTML.encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy HTTP logs during testing
        pass



class LocalFixtureServer:
    def __init__(self, port: int = 8989):
        self.port = port
        self.server: Optional[http.server.HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), FixtureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.thread = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"
