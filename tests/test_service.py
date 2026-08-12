import tempfile
import unittest
from pathlib import Path

from totannstudio.service import StudioService


class StudioServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = StudioService(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_trains_real_tota_model_and_saves_it(self):
        result = self.service.train({
            "name": "Browser OR",
            "input_size": 2,
            "layers": [{"neurons": 1, "activation": "sigmoid"}],
            "learning_rate": 0.2,
            "epochs": 3000,
            "dataset": [
                {"input": [0, 0], "target": 0},
                {"input": [0, 1], "target": 1},
                {"input": [1, 0], "target": 1},
                {"input": [1, 1], "target": 1},
            ],
        })

        self.assertEqual(result["engine"], "tota")
        self.assertEqual(result["predictions"], [0, 1, 1, 1])
        self.assertTrue((Path(self.temp.name) / f'{result["model_id"]}.tota.json').exists())
        self.assertEqual(len(self.service.list_models()), 1)

    def test_rejects_excessive_training_request(self):
        with self.assertRaisesRegex(ValueError, "epochs"):
            self.service.train({
                "name": "Too long",
                "input_size": 1,
                "layers": [{"neurons": 1, "activation": "sigmoid"}],
                "learning_rate": 0.1,
                "epochs": 5001,
                "dataset": [{"input": [0], "target": 0}],
            })

    def test_predicts_with_saved_model(self):
        trained = self.service.train({
            "name": "OR",
            "input_size": 2,
            "layers": [{"neurons": 1, "activation": "sigmoid"}],
            "learning_rate": 0.2,
            "epochs": 3000,
            "dataset": [
                {"input": [0, 0], "target": 0},
                {"input": [0, 1], "target": 1},
                {"input": [1, 0], "target": 1},
                {"input": [1, 1], "target": 1},
            ],
        })

        prediction = self.service.predict(trained["model_id"], [1, 0])

        self.assertEqual(prediction["class"], 1)
        self.assertGreater(prediction["output"][0], 0.5)


if __name__ == "__main__":
    unittest.main()
