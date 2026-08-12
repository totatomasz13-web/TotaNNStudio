"""Serwer HTTP panelu TotaNNStudio — bez zewnętrznego frameworka."""

import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

from .service import StudioService

PROJECT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"
MARKETING_DIR = Path(os.environ.get("TOTA_MARKETING_DIR", PACKAGE_DIR / "marketing"))
MODELS_DIR = Path(os.environ.get("TOTA_MODELS_DIR", PROJECT_DIR / "models"))
MAX_BODY_BYTES = 1_000_000


class StudioHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32
    max_active_requests = 16

    def __init__(self, address, handler, service):
        super().__init__(address, handler)
        self.service = service
        self.training_lock = threading.Lock()
        self.request_slots = threading.BoundedSemaphore(self.max_active_requests)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(15)
        return connection, address

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "TotaNNStudio/0.2"

    def log_message(self, format, *args):
        print(f"[studio] {self.address_string()} {format % args}")

    def _security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
        )

    def _send_bytes(self, body, content_type, status=HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)


    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("nieprawidłowy Content-Length") from error
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError("nieprawidłowy rozmiar żądania")
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError("nieprawidłowy JSON") from error

    def _serve_file(self, root, relative):
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        self._send_bytes(path.read_bytes(), types.get(path.suffix, "application/octet-stream"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"status": "ok", "engine": "tota", "engine_version": version("tota")})
            return
        if path == "/api/models":
            self._json({"models": self.server.service.list_models()})
            return
        if path in {"/studio", "/studio/"}:
            self._serve_file(WEB_DIR, "index.html")
            return
        if path.startswith("/studio/"):
            self._serve_file(WEB_DIR, path.removeprefix("/studio/"))
            return
        if path == "/":
            self._serve_file(MARKETING_DIR, "index.html")
            return
        self._serve_file(MARKETING_DIR, path.lstrip("/"))

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise ValueError("żądanie musi być obiektem JSON")
            if path == "/api/train":
                if not self.server.training_lock.acquire(blocking=False):
                    self._json({"error": "Inny trening już trwa"}, HTTPStatus.CONFLICT)
                    return
                try:
                    result = self.server.service.train(payload)
                finally:
                    self.server.training_lock.release()
                self._json(result, HTTPStatus.CREATED)
                return
            if path.startswith("/api/models/") and path.endswith("/predict"):
                model_id = path.removeprefix("/api/models/").removesuffix("/predict")
                self._json(self.server.service.predict(model_id, payload.get("input")))
                return
            self._json({"error": "Nieznany endpoint"}, HTTPStatus.NOT_FOUND)
        except FileNotFoundError as error:
            self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, KeyError) as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            self._json({"error": "Wewnętrzny błąd serwera"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def run(host="127.0.0.1", port=4173):
    server = StudioHTTPServer(
        (host, port),
        StudioHandler,
        StudioService(MODELS_DIR),
    )
    print(f"TotaNNStudio: http://{host}:{port}/studio/")
    server.serve_forever()


def main():
    run(
        host=os.environ.get("TOTA_STUDIO_HOST", "127.0.0.1"),
        port=int(os.environ.get("TOTA_STUDIO_PORT", "4173")),
    )


if __name__ == "__main__":
    main()
