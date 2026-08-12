import json
import tempfile
import unittest
from pathlib import Path

from totannstudio.studio import LayerConfig, ModelConfig, StudioModel


class ModelWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config = ModelConfig(
            name="LogicOR",
            input_size=2,
            layers=(LayerConfig(neurons=1, activation="sigmoid"),),
        )
        self.training_data = [
            ([0, 0], 0),
            ([0, 1], 1),
            ([1, 0], 1),
            ([1, 1], 1),
        ]

    def test_trains_and_predicts_using_tota_network(self):
        model = StudioModel.create(self.config)

        report = model.train(
            self.training_data,
            learning_rate=0.2,
            epochs=3000,
        )

        self.assertIn("Uczenie zakonczone", report)
        self.assertEqual([model.predict(row) for row, _ in self.training_data], [0, 1, 1, 1])

    def test_saved_model_loads_with_same_forward_result(self):
        model = StudioModel.create(self.config)
        model.train(self.training_data, learning_rate=0.2, epochs=500)
        before = model.forward([1, 0])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logic-or.tota.json"
            model.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            loaded = StudioModel.load(path)

        self.assertEqual(payload["format"], "totannstudio-model-v1")
        self.assertEqual(loaded.config, model.config)
        self.assertEqual(loaded.forward([1, 0]), before)

    def test_load_rejects_malformed_model_files(self):
        malformed = [
            [],
            {"format": "totannstudio-model-v1", "config": {}, "parameters": []},
            {
                "format": "totannstudio-model-v1",
                "config": {"name": "bad", "input_size": 2, "layers": [{"neurons": 1, "activation": "sigmoid"}]},
                "parameters": [{"weights": [[float("nan"), 0]], "biases": [0]}],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.tota.json"
            for payload in malformed:
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    StudioModel.load(path)

    def test_load_rejects_architecture_above_safe_limits_before_create(self):
        payload = {
            "format": "totannstudio-model-v1",
            "config": {
                "name": "too-large",
                "input_size": StudioModel.MAX_INPUT_SIZE + 1,
                "layers": [{"neurons": 1, "activation": "sigmoid"}],
            },
            "parameters": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-large.tota.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "input_size"):
                StudioModel.load(path)


if __name__ == "__main__":
    unittest.main()
