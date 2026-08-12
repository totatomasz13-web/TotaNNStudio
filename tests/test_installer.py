import unittest
from pathlib import Path


class InstallerTests(unittest.TestCase):
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
        self.assertIn("systemctl --user enable --now totannstudio.service", script)
        self.assertIn("/etc/systemd/system/totannstudio.service", script)
        self.assertIn("systemctl enable --now totannstudio.service", script)
        self.assertIn("useradd --system", script)
        self.assertIn("User=totannstudio", script)
        self.assertIn("Group=totannstudio", script)
        self.assertIn("TOTA_MODELS_DIR=/var/lib/totannstudio/models", script)
        self.assertIn("Restart=on-failure", script)
        self.assertIn("TOTA_STUDIO_PORT=8080", script)
        self.assertIn("ip -4 route get 1.1.1.1", script)
        self.assertIn(r"192\.168\.", script)
        self.assertIn('STUDIO_HOST="$PRIVATE_IP"', script)
        self.assertIn("STUDIO_HOST=127.0.0.1", script)
        self.assertNotIn("TOTA_STUDIO_TOKEN", script)
        self.assertNotIn("rm -rf", script)


if __name__ == "__main__":
    unittest.main()