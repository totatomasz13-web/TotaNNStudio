import json
import subprocess
import sys
import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_demo_trains_predicts_and_saves_model(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "logic-or.tota.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(project / "main.py"),
                    "demo",
                    "--output",
                    str(output),
                ],
                cwd=project,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn(f"Silnik: tota {version('tota')}", result.stdout)
        self.assertIn("Predykcje: [0, 1, 1, 1]", result.stdout)
        self.assertEqual(payload["format"], "totannstudio-model-v1")


if __name__ == "__main__":
    unittest.main()
