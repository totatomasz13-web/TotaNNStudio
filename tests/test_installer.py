import unittest
from pathlib import Path


class InstallerTests(unittest.TestCase):
    def test_installer_creates_private_venv_and_launcher(self):
        project = Path(__file__).resolve().parents[1]
        script = (project / "install.sh").read_text(encoding="utf-8")

        self.assertIn("python3 -m venv", script)
        self.assertIn("github.com/totatomasz13-web/TotaNNStudio", script)
        self.assertIn("$HOME/.local/bin", script)
        self.assertIn("https://download.pytorch.org/whl/cpu", script)
        self.assertNotIn("TOTA_STUDIO_TOKEN", script)
        self.assertNotIn("rm -rf", script)


if __name__ == "__main__":
    unittest.main()