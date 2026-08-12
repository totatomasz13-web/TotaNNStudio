import unittest
import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class InstallerTests(unittest.TestCase):
    def test_unbindable_host_fails_immediately(self):
        project = Path(__file__).resolve().parents[1]
        env = os.environ | {
            "TOTA_STUDIO_CHECK_ONLY": "1",
            "TOTA_STUDIO_HOST": "192.0.2.1",
            "TOTA_STUDIO_PORT": "8080",
        }
        result = subprocess.run(
            ["bash", str(project / "install.sh")],
            env=env,
            text=True,
            capture_output=True,
            timeout=5,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nie można przypisać", result.stderr)

    def test_existing_wildcard_unit_displays_reachable_address(self):
        project = Path(__file__).resolve().parents[1]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        unit = project / "tests" / ".tmp-wildcard.service"
        unit.write_text(
            "[Service]\n"
            "ExecStart=/opt/totannstudio/.venv/bin/totannstudio\n"
            "Environment=TOTA_STUDIO_HOST=0.0.0.0\n"
            f"Environment=TOTA_STUDIO_PORT={port}\n",
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=os.environ
                | {
                    "TOTA_STUDIO_CHECK_ONLY": "1",
                    "TOTA_STUDIO_EXISTING_UNIT": str(unit),
                },
                text=True,
                capture_output=True,
                check=True,
            )
        finally:
            unit.unlink(missing_ok=True)

        self.assertIn("HOST=0.0.0.0", result.stdout)
        self.assertIn(f"URL=http://127.0.0.1:{port}/studio/", result.stdout)

    def test_same_port_on_other_address_is_not_a_conflict(self):
        project = Path(__file__).resolve().parents[1]
        with socket.socket() as occupied:
            try:
                occupied.bind(("127.0.0.2", 0))
            except OSError:
                self.skipTest("System nie obsługuje dodatkowego adresu loopback")
            occupied.listen()
            port = occupied.getsockname()[1]
            env = os.environ | {
                "TOTA_STUDIO_CHECK_ONLY": "1",
                "TOTA_STUDIO_HOST": "127.0.0.1",
                "TOTA_STUDIO_PORT": str(port),
            }
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

        self.assertIn(f"PORT={port}", result.stdout)
        self.assertNotIn("wybrano wolny port", result.stdout)

    def test_rejects_host_with_newline_before_writing_systemd_unit(self):
        project = Path(__file__).resolve().parents[1]
        env = os.environ | {
            "TOTA_STUDIO_CHECK_ONLY": "1",
            "TOTA_STUDIO_HOST": "127.0.0.1\nUser=root",
        }
        result = subprocess.run(
            ["bash", str(project / "install.sh")],
            env=env,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Nieprawidłowy TOTA_STUDIO_HOST", result.stderr)

    def test_update_reuses_host_and_distant_port_from_existing_unit(self):
        project = Path(__file__).resolve().parents[1]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            existing_port = probe.getsockname()[1]
        unit = project / "tests" / ".tmp-totannstudio.service"
        unit.write_text(
            "[Service]\n"
            "ExecStart=/opt/totannstudio/.venv/bin/totannstudio\n"
            "Environment=TOTA_STUDIO_HOST=127.0.0.1\n"
            f"Environment=TOTA_STUDIO_PORT={existing_port}\n",
            encoding="utf-8",
        )
        try:
            env = os.environ | {
                "TOTA_STUDIO_CHECK_ONLY": "1",
                "TOTA_STUDIO_EXISTING_UNIT": str(unit),
            }
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
        finally:
            unit.unlink(missing_ok=True)

        self.assertIn("HOST=127.0.0.1", result.stdout)
        self.assertIn(f"PORT={existing_port}", result.stdout)

    def test_update_keeps_existing_totannstudio_after_foreign_busy_port(self):
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'{"status":"ok","engine":"tota"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        foreign = socket.socket()
        foreign.bind(("127.0.0.1", 0))
        requested_port = foreign.getsockname()[1]
        foreign.close()
        if requested_port >= 65535:
            self.skipTest("No adjacent port available")

        foreign = socket.socket()
        try:
            foreign.bind(("127.0.0.1", requested_port))
            foreign.listen()
            try:
                server = ThreadingHTTPServer(("127.0.0.1", requested_port + 1), HealthHandler)
            except OSError:
                self.skipTest("Adjacent port unavailable")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                project = Path(__file__).resolve().parents[1]
                env = os.environ | {
                    "TOTA_STUDIO_CHECK_ONLY": "1",
                    "TOTA_STUDIO_HOST": "127.0.0.1",
                    "TOTA_STUDIO_PORT": str(requested_port),
                }
                result = subprocess.run(
                    ["bash", str(project / "install.sh")],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=True,
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
        finally:
            foreign.close()

        self.assertIn(f"PORT={requested_port + 1}", result.stdout)

    def test_strict_port_mode_fails_when_port_is_busy(self):
        project = Path(__file__).resolve().parents[1]
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            busy_port = occupied.getsockname()[1]
            env = os.environ | {
                "TOTA_STUDIO_CHECK_ONLY": "1",
                "TOTA_STUDIO_STRICT_PORT": "1",
                "TOTA_STUDIO_HOST": "127.0.0.1",
                "TOTA_STUDIO_PORT": str(busy_port),
            }
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=env,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"Port {busy_port} jest zajęty", result.stderr)

    def test_installer_keeps_port_used_by_existing_totannstudio(self):
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'{"status":"ok","engine":"tota"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            project = Path(__file__).resolve().parents[1]
            env = os.environ | {
                "TOTA_STUDIO_CHECK_ONLY": "1",
                "TOTA_STUDIO_HOST": "127.0.0.1",
                "TOTA_STUDIO_PORT": str(port),
            }
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn(f"PORT={port}", result.stdout)

    def test_installer_selects_next_port_when_requested_port_is_busy(self):
        project = Path(__file__).resolve().parents[1]
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            busy_port = occupied.getsockname()[1]
            env = os.environ | {
                "TOTA_STUDIO_CHECK_ONLY": "1",
                "TOTA_STUDIO_HOST": "127.0.0.1",
                "TOTA_STUDIO_PORT": str(busy_port),
            }
            result = subprocess.run(
                ["bash", str(project / "install.sh")],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

        self.assertIn(f"PORT={busy_port + 1}", result.stdout)
        self.assertIn(f"http://127.0.0.1:{busy_port + 1}/studio/", result.stdout)

    def test_installer_creates_private_venv_and_launcher(self):
        project = Path(__file__).resolve().parents[1]
        script = (project / "install.sh").read_text(encoding="utf-8")

        self.assertIn("python3 -m venv", script)
        self.assertIn("github.com/totatomasz13-web/TotaNNStudio", script)
        self.assertIn("$HOME/.local/bin", script)
        self.assertIn("/opt/totannstudio", script)
        self.assertIn("/usr/local/bin", script)
        self.assertIn("https://download.pytorch.org/whl/cpu", script)
        self.assertIn("$HOME/.config/systemd/user", script)
        self.assertIn("systemctl --user enable totannstudio.service", script)
        self.assertIn("systemctl --user restart totannstudio.service", script)
        self.assertIn("/etc/systemd/system/totannstudio.service", script)
        self.assertIn("systemctl enable totannstudio.service", script)
        self.assertIn("systemctl restart totannstudio.service", script)
        self.assertIn("useradd --system", script)
        self.assertIn("User=totannstudio", script)
        self.assertIn("Group=totannstudio", script)
        self.assertIn("TOTA_MODELS_DIR=/var/lib/totannstudio/models", script)
        self.assertIn("Restart=on-failure", script)
        self.assertIn('STUDIO_PORT="${TOTA_STUDIO_PORT:-${EXISTING_PORT:-8080}}"', script)
        self.assertIn('TOTA_STUDIO_HOST:-', script)
        self.assertIn("65535", script)
        self.assertIn("ip -4 route get 1.1.1.1", script)
        self.assertIn(r"192\.168\.", script)
        self.assertIn('STUDIO_HOST="$PRIVATE_IP"', script)
        self.assertIn("STUDIO_HOST=127.0.0.1", script)
        self.assertNotIn("TOTA_STUDIO_TOKEN", script)
        self.assertNotIn("rm -rf", script)


if __name__ == "__main__":
    unittest.main()