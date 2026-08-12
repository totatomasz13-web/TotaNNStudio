import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer
from totannstudio.server import StudioHandler, StudioHTTPServer
from totannstudio.service import StudioService


class HTTPTests(unittest.TestCase):
    def test_default_server_port_is_8080(self):
        from inspect import signature
        from totannstudio.server import run

        self.assertEqual(signature(run).parameters["port"].default, 8080)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = StudioHTTPServer(
            ("127.0.0.1", 0),
            StudioHandler,
            StudioService(Path(self.temp.name)),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get_json(self, path):
        with urlopen(self.url + path, timeout=5) as response:
            return response.status, json.load(response)

    def test_health_is_public_and_reports_tota_version(self):
        status, payload = self.get_json("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["engine"], "tota")
        self.assertRegex(payload["engine_version"], r"^\d+\.\d+\.\d+")

    def test_models_are_available_without_token(self):
        status, payload = self.get_json("/api/models")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"models": []})

    def test_post_rejects_non_object_json_with_400(self):
        request = Request(
            self.url + "/api/train",
            data=json.dumps([]).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_connections_have_read_timeout(self):
        connection = Mock()
        address = ("127.0.0.1", 12345)
        with patch.object(ThreadingHTTPServer, "get_request", return_value=(connection, address)):
            returned_connection, returned_address = self.server.get_request()
        connection.settimeout.assert_called_once_with(15)
        self.assertIs(returned_connection, connection)
        self.assertEqual(returned_address, address)
        self.assertEqual(self.server.request_queue_size, 32)

    def test_rejects_connections_above_bounded_worker_limit(self):
        for _ in range(self.server.max_active_requests):
            self.assertTrue(self.server.request_slots.acquire(blocking=False))
        request = Mock()
        with patch.object(self.server, "shutdown_request") as shutdown:
            self.server.process_request(request, ("127.0.0.1", 12345))
        shutdown.assert_called_once_with(request)
        for _ in range(self.server.max_active_requests):
            self.server.request_slots.release()

    def test_worker_slot_is_released_after_request_thread(self):
        self.assertTrue(self.server.request_slots.acquire(blocking=False))
        with patch.object(ThreadingHTTPServer, "process_request_thread", return_value=None):
            self.server.process_request_thread(Mock(), ("127.0.0.1", 12345))
        acquired = 0
        while self.server.request_slots.acquire(blocking=False):
            acquired += 1
        self.assertEqual(acquired, self.server.max_active_requests)
        for _ in range(acquired):
            self.server.request_slots.release()

    def test_studio_assets_are_available(self):
        with urlopen(self.url + "/studio/", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn("Create model", html)
        self.assertNotIn("Unlock your studio", html)


if __name__ == "__main__":
    unittest.main()
