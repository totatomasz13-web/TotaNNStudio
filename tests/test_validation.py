import math
import tempfile
import unittest
from pathlib import Path

from totannstudio.service import StudioService


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = StudioService(Path(self.temp.name))
        self.valid = {
            "name": "Safe model",
            "input_size": 1,
            "layers": [{"neurons": 1, "activation": "sigmoid"}],
            "learning_rate": 0.1,
            "epochs": 1,
            "dataset": [{"input": [0], "target": 0}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_non_object_request(self):
        with self.assertRaisesRegex(ValueError, "obiektem"):
            self.service.train([])

    def test_rejects_non_finite_input(self):
        request = {**self.valid, "dataset": [{"input": [math.nan], "target": 0}]}
        with self.assertRaisesRegex(ValueError, "skończone"):
            self.service.train(request)

    def test_rejects_non_finite_target(self):
        request = {**self.valid, "dataset": [{"input": [0], "target": math.inf}]}
        with self.assertRaisesRegex(ValueError, "skończone"):
            self.service.train(request)

    def test_rejects_non_finite_learning_rate(self):
        request = {**self.valid, "learning_rate": math.nan}
        with self.assertRaisesRegex(ValueError, "learning_rate"):
            self.service.train(request)

    def test_rejects_non_object_layer_and_sample(self):
        with self.assertRaisesRegex(ValueError, "warstwa"):
            self.service.train({**self.valid, "layers": [1]})
        with self.assertRaisesRegex(ValueError, "próbka"):
            self.service.train({**self.valid, "dataset": [1]})

    def test_rejects_fractional_integer_fields(self):
        with self.assertRaisesRegex(ValueError, "input_size"):
            self.service.train({**self.valid, "input_size": 1.5})
        with self.assertRaisesRegex(ValueError, "epochs"):
            self.service.train({**self.valid, "epochs": 1.5})
        with self.assertRaisesRegex(ValueError, "neurons"):
            self.service.train({**self.valid, "layers": [{"neurons": 1.5, "activation": "sigmoid"}]})

    def test_rejects_excessive_combined_training_work(self):
        request = {
            **self.valid,
            "input_size": 512,
            "layers": [{"neurons": 512, "activation": "relu"}, {"neurons": 1, "activation": "sigmoid"}],
            "epochs": 5000,
            "dataset": [{"input": [0] * 512, "target": 0}],
        }
        with self.assertRaisesRegex(ValueError, "zbyt kosztowne"):
            self.service.train(request)

    def test_prediction_rejects_non_finite_values(self):
        result = self.service.train(self.valid)
        with self.assertRaisesRegex(ValueError, "skończone"):
            self.service.predict(result["model_id"], [math.nan])

    def test_rejects_excessive_finite_values(self):
        request = {**self.valid, "dataset": [{"input": [1_000_001], "target": 0}]}
        with self.assertRaisesRegex(ValueError, "nie mogą przekraczać"):
            self.service.train(request)
        result = self.service.train(self.valid)
        with self.assertRaisesRegex(ValueError, "nie mogą przekraczać"):
            self.service.predict(result["model_id"], [1_000_001])

    def test_rejects_non_text_name_and_activation(self):
        with self.assertRaisesRegex(ValueError, "name"):
            self.service.train({**self.valid, "name": ["model"]})
        with self.assertRaisesRegex(ValueError, "activation"):
            self.service.train({**self.valid, "layers": [{"neurons": 1, "activation": ["sigmoid"]}]})

    def test_huge_integer_conversions_return_validation_errors(self):
        huge = 10 ** 10000
        with self.assertRaises(ValueError):
            self.service.train({**self.valid, "learning_rate": huge})
        with self.assertRaisesRegex(ValueError, "próbkę"):
            self.service.train({**self.valid, "dataset": [{"input": [huge], "target": 0}]})


if __name__ == "__main__":
    unittest.main()
