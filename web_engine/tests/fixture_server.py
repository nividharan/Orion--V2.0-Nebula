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
    </style>
</head>
<body>
    <div class="container">
        <h1>Orion WebEngine Testbed</h1>
        <div id="cookie-banner" class="cookie-modal" role="dialog" aria-modal="true">
            <p>We value your privacy.</p>
            <button id="reject-btn" role="button">Reject all</button>
            <button id="accept-btn" role="button">Accept all</button>
        </div>

        <section id="search-section">
            <h2>Portal Search</h2>
            <input type="search" role="searchbox" aria-label="Search" id="search-input" placeholder="Search catalog..." />
            <button role="button" id="search-button">Search</button>
            <div id="search-results"></div>
        </section>

        <section id="catalog-section">
            <h2>Infinite Scroll Catalog</h2>
            <div id="catalog-list">
                <div class="card item-card"><h3>Item 1</h3><span class="price">$10.00</span></div>
                <div class="card item-card"><h3>Item 2</h3><span class="price">$20.00</span></div>
                <div class="card item-card"><h3>Item 3</h3><span class="price">$30.00</span></div>
            </div>
        </section>

        <section id="iframe-section">
            <h2>Nested Frame</h2>
            <iframe id="test-iframe" srcdoc="<p id='frame-text'>Inside Test Iframe</p>"></iframe>
        </section>
    </div>

    <script>
        document.getElementById('reject-btn').onclick = () => {
            document.getElementById('cookie-banner').style.display = 'none';
        };
        document.getElementById('accept-btn').onclick = () => {
            document.getElementById('cookie-banner').style.display = 'none';
        };
        document.getElementById('search-button').onclick = () => {
            const q = document.getElementById('search-input').value;
            const res = document.getElementById('search-results');
            res.innerHTML = '<div class=\"card\">Result for: ' + q + '</div>';
        };
        // Simulated infinite scroll
        let itemIndex = 4;
        window.onscroll = () => {
            if (window.scrollY > 200 && itemIndex <= 10) {
                const list = document.getElementById('catalog-list');
                const div = document.createElement('div');
                div.className = 'card item-card';
                div.innerHTML = '<h3>Item ' + itemIndex + '</h3><span class=\"price\">$' + (itemIndex * 10) + '.00</span>';
                list.appendChild(div);
                itemIndex++;
            }
        };
    </script>
</body>
</html>
"""

class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
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
