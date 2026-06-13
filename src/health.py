"""Tiny HTTP health server.

Render's free tier only offers Web Services, which must bind to ``$PORT``.
The bot itself is a long-running poller with no real HTTP API, so this module
spins up a minimal health endpoint on a daemon thread purely to satisfy the
platform and to give an external uptime pinger (e.g. UptimeRobot) a URL to hit
every few minutes — which is what keeps a free Web Service from spinning down.
"""

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — stdlib naming
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"arsenal-bot alive\n")

    def do_HEAD(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_args) -> None:
        # Silence per-request logging (the pinger hits us constantly).
        pass


def start_health_server() -> None:
    """Start the health server on $PORT in a background daemon thread.

    No-op only in the sense that failures are swallowed: the bot must keep
    running even if the health port is unavailable locally.
    """
    port = int(os.getenv("PORT", "10000"))
    try:
        # Bind all interfaces: required so Render can reach the health check.
        # The server only ever returns a static "alive" string — no data exposed.
        server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)  # nosec B104
    except OSError:
        log.exception("Could not bind health server on port %s", port)
        return
    thread = threading.Thread(target=server.serve_forever, name="health", daemon=True)
    thread.start()
    log.info("Health server listening on port %s", port)
