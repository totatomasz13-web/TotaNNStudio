"""Bezpieczna warstwa usług dla panelu WWW TotaNNStudio."""

import math
import re
from importlib.metadata import version
from pathlib import Path

from .studio import LayerConfig, ModelConfig, StudioModel


class StudioService:
    MAX_EPOCHS = 5000
    MAX_SAMPLES = 1000
    MAX_LAYERS = 10
    MAX_NEURONS = 512
    MAX_ABS_VALUE = 1_000_000
    MAX_TRAINING_WORK = 2_000_000
    ACTIVATIONS = {"sigmoid", "relu", "tanh", "linear", "leaky_relu", "step"}

    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _model_id(name):
        value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return (value or "model")[:60]

    def _unique_model_id(self, name):
        base = self._model_id(name)
        candidate = base
        number = 2
        while (self.models_dir / f"{candidate}.tota.json").exists():
            candidate = f"{base}-{number}"
            number += 1
        return candidate

    @staticmethod
    def _integer(value, field):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} musi być liczbą całkowitą")
        return value

    def _validate_request(self, request):
        if not isinstance(request, dict):
            raise ValueError("żądanie musi być obiektem JSON")
        raw_name = request.get("name", "")
        if not isinstance(raw_name, str):
            raise ValueError("name musi być tekstem")
        name = raw_name.strip()
        if not name or len(name) > 80:
            raise ValueError("name musi mieć od 1 do 80 znaków")

        input_size = self._integer(request.get("input_size", 0), "input_size")
        if not 1 <= input_size <= 512:
            raise ValueError("input_size musi być w zakresie 1–512")

        raw_layers = request.get("layers")
        if not isinstance(raw_layers, list) or not 1 <= len(raw_layers) <= self.MAX_LAYERS:
            raise ValueError(f"layers musi zawierać od 1 do {self.MAX_LAYERS} warstw")

        layers = []
        previous_size = input_size
        parameter_count = 0
        for raw_layer in raw_layers:
            if not isinstance(raw_layer, dict):
                raise ValueError("każda warstwa musi być obiektem JSON")
            neurons = self._integer(raw_layer.get("neurons", 0), "neurons")
            activation = raw_layer.get("activation", "")
            if not isinstance(activation, str):
                raise ValueError("activation musi być tekstem")
            if not 1 <= neurons <= self.MAX_NEURONS:
                raise ValueError(f"neurons musi być w zakresie 1–{self.MAX_NEURONS}")
            if activation not in self.ACTIVATIONS:
                raise ValueError("nieobsługiwana activation")
            parameter_count += previous_size * neurons + neurons
            previous_size = neurons
            layers.append(LayerConfig(neurons=neurons, activation=activation))

        if layers[-1].neurons != 1:
            raise ValueError("ostatnia warstwa musi mieć 1 neuron")

        epochs = self._integer(request.get("epochs", 0), "epochs")
        if not 1 <= epochs <= self.MAX_EPOCHS:
            raise ValueError(f"epochs musi być w zakresie 1–{self.MAX_EPOCHS}")

        try:
            learning_rate = float(request.get("learning_rate", 0))
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("learning_rate musi być liczbą") from error
        if not math.isfinite(learning_rate) or not 0 < learning_rate <= 1:
            raise ValueError("learning_rate musi być skończone, większe od 0 i nie większe niż 1")

        raw_dataset = request.get("dataset")
        if not isinstance(raw_dataset, list) or not 1 <= len(raw_dataset) <= self.MAX_SAMPLES:
            raise ValueError(f"dataset musi zawierać od 1 do {self.MAX_SAMPLES} próbek")

        dataset = []
        for sample in raw_dataset:
            if not isinstance(sample, dict):
                raise ValueError("każda próbka datasetu musi być obiektem JSON")
            values = sample.get("input")
            if not isinstance(values, list) or len(values) != input_size:
                raise ValueError("każda próbka input musi odpowiadać input_size")
            try:
                normalized = [float(value) for value in values]
                target = float(sample["target"])
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError("dataset zawiera nieprawidłową próbkę") from error
            if not all(math.isfinite(value) for value in normalized) or not math.isfinite(target):
                raise ValueError("wartości datasetu muszą być skończone")
            if any(abs(value) > self.MAX_ABS_VALUE for value in normalized) or abs(target) > self.MAX_ABS_VALUE:
                raise ValueError(f"wartości datasetu nie mogą przekraczać ±{self.MAX_ABS_VALUE}")
            dataset.append((normalized, target))

        training_work = parameter_count * len(dataset) * epochs
        if training_work > self.MAX_TRAINING_WORK:
            raise ValueError(
                "żądanie treningu jest zbyt kosztowne; zmniejsz sieć, dataset lub liczbę epok"
            )

        return (
            ModelConfig(name=name, input_size=input_size, layers=tuple(layers)),
            dataset,
            learning_rate,
            epochs,
        )

    def train(self, request):
        config, dataset, learning_rate, epochs = self._validate_request(request)
        model = StudioModel.create(config)
        report = model.train(dataset, learning_rate=learning_rate, epochs=epochs)
        if not model.parameters_are_finite():
            raise ValueError("trening wygenerował nieprawidłowe parametry; zmniejsz wartości lub learning rate")
        outputs = [model.forward(values)[0] for values, _ in dataset]
        if not all(math.isfinite(output) for output in outputs):
            raise ValueError("trening wygenerował nieprawidłowe wyniki liczbowe")
        model_id = self._unique_model_id(config.name)
        model.save(self.models_dir / f"{model_id}.tota.json")
        return {
            "engine": "tota",
            "engine_version": version("tota"),
            "model_id": model_id,
            "summary": model.summary(),
            "report": report,
            "predictions": [int(output >= 0.5) for output in outputs],
            "outputs": outputs,
        }

    def _path_for(self, model_id):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", model_id):
            raise ValueError("nieprawidłowy model_id")
        path = self.models_dir / f"{model_id}.tota.json"
        if not path.exists():
            raise FileNotFoundError("model nie istnieje")
        return path

    def predict(self, model_id, values):
        model = StudioModel.load(self._path_for(model_id))
        if not isinstance(values, list) or len(values) != model.config.input_size:
            raise ValueError("input nie odpowiada input_size modelu")
        try:
            normalized = [float(value) for value in values]
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("input musi zawierać liczby") from error
        if not all(math.isfinite(value) for value in normalized):
            raise ValueError("wartości input muszą być skończone")
        if any(abs(value) > self.MAX_ABS_VALUE for value in normalized):
            raise ValueError(f"wartości input nie mogą przekraczać ±{self.MAX_ABS_VALUE}")
        result = model.forward(normalized)
        if not all(math.isfinite(value) for value in result):
            raise ValueError("model zwrócił nieprawidłowy wynik liczbowy")
        return {"class": int(result[0] >= 0.5), "output": result}

    def list_models(self):
        models = []
        for path in sorted(self.models_dir.glob("*.tota.json"), reverse=True):
            try:
                model = StudioModel.load(path)
            except (ValueError, KeyError, TypeError, OverflowError):
                continue
            models.append({"id": path.name.removesuffix(".tota.json"), **model.summary()})
        return models
