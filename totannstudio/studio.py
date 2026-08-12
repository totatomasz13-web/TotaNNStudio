"""Rdzeń Studio zbudowany na publicznym API biblioteki tota."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import torch
from tota import Layer, Network


@dataclass(frozen=True)
class LayerConfig:
    neurons: int
    activation: str = "sigmoid"

    def __post_init__(self):
        if self.neurons < 1:
            raise ValueError("neurons musi być większe od zera")


@dataclass(frozen=True)
class ModelConfig:
    name: str
    input_size: int
    layers: tuple[LayerConfig, ...]

    def __post_init__(self):
        if self.input_size < 1:
            raise ValueError("input_size musi być większe od zera")
        if not self.layers:
            raise ValueError("model musi zawierać co najmniej jedną layer")


class StudioModel:
    MAX_MODEL_FILE_BYTES = 16 * 1024 * 1024
    MAX_INPUT_SIZE = 512
    MAX_LAYERS = 10
    MAX_NEURONS = 512
    MAX_PARAMETERS = 2_000_000
    ACTIVATIONS = {"sigmoid", "relu", "tanh", "linear", "leaky_relu", "step"}

    def __init__(self, config: ModelConfig, network: Network):
        self.config = config
        self.network = network

    @classmethod
    def create(cls, config: ModelConfig):
        tota_layers = []
        inputs = config.input_size
        for layer_config in config.layers:
            tota_layers.append(
                Layer(layer_config.neurons, inputs, activation=layer_config.activation)
            )
            inputs = layer_config.neurons
        return cls(config, Network(tota_layers))

    def summary(self):
        parameters = sum(
            layer.i_n * layer.i_w + layer.i_n
            for layer in self.network.layers
        )
        return {
            "name": self.config.name,
            "input_size": self.config.input_size,
            "layers": len(self.network.layers),
            "parameters": parameters,
        }

    def forward(self, values):
        return self.network.forward(values)

    def predict(self, values):
        return self.network.predict(values)

    def train(self, training_data, learning_rate, epochs):
        return self.network.learn(
            training_data,
            learning_rate=learning_rate,
            epochs=epochs,
            show_progress=False,
        )

    def parameters_are_finite(self):
        return all(
            torch.isfinite(neuron.weight).all().item()
            and math.isfinite(float(neuron.bias.detach()))
            for layer in self.network.layers
            for neuron in layer.neurons
        )

    def save(self, path):
        if not self.parameters_are_finite():
            raise ValueError("model zawiera nieprawidłowe parametry liczbowe")
        payload = {
            "format": "totannstudio-model-v1",
            "config": {
                "name": self.config.name,
                "input_size": self.config.input_size,
                "layers": [
                    {
                        "neurons": layer.neurons,
                        "activation": layer.activation,
                    }
                    for layer in self.config.layers
                ],
            },
            "parameters": [
                {
                    "weights": [
                        neuron.weight.detach().tolist()
                        for neuron in layer.neurons
                    ],
                    "biases": [
                        float(neuron.bias.detach())
                        for neuron in layer.neurons
                    ],
                }
                for layer in self.network.layers
            ],
        }
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(destination)

    @classmethod
    def load(cls, path):
        source = Path(path)
        if source.stat().st_size > cls.MAX_MODEL_FILE_BYTES:
            raise ValueError("plik modelu jest zbyt duży")
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("model musi być obiektem JSON")
        if payload.get("format") != "totannstudio-model-v1":
            raise ValueError("nieobsługiwany format modelu")

        raw_config = payload.get("config")
        raw_parameters = payload.get("parameters")
        if not isinstance(raw_config, dict) or not isinstance(raw_parameters, list):
            raise ValueError("nieprawidłowa struktura modelu")
        raw_layers = raw_config.get("layers")
        if not isinstance(raw_layers, list) or not raw_layers:
            raise ValueError("nieprawidłowa konfiguracja warstw")
        if not isinstance(raw_config.get("name"), str):
            raise ValueError("nieprawidłowa nazwa modelu")
        if isinstance(raw_config.get("input_size"), bool) or not isinstance(raw_config.get("input_size"), int):
            raise ValueError("nieprawidłowy input_size")
        if not 1 <= raw_config["input_size"] <= cls.MAX_INPUT_SIZE:
            raise ValueError("input_size modelu przekracza limit")
        if len(raw_layers) > cls.MAX_LAYERS:
            raise ValueError("liczba warstw modelu przekracza limit")
        if not all(isinstance(layer, dict) for layer in raw_layers):
            raise ValueError("nieprawidłowa konfiguracja warstwy")
        previous_size = raw_config["input_size"]
        parameter_count = 0
        for layer in raw_layers:
            if isinstance(layer.get("neurons"), bool) or not isinstance(layer.get("neurons"), int):
                raise ValueError("nieprawidłowa liczba neuronów")
            if not 1 <= layer["neurons"] <= cls.MAX_NEURONS:
                raise ValueError("liczba neuronów modelu przekracza limit")
            if not isinstance(layer.get("activation"), str):
                raise ValueError("nieprawidłowa funkcja aktywacji")
            if layer["activation"] not in cls.ACTIVATIONS:
                raise ValueError("nieobsługiwana funkcja aktywacji")
            parameter_count += previous_size * layer["neurons"] + layer["neurons"]
            previous_size = layer["neurons"]
        if raw_layers[-1]["neurons"] != 1:
            raise ValueError("ostatnia warstwa modelu musi mieć 1 neuron")
        if parameter_count > cls.MAX_PARAMETERS:
            raise ValueError("model przekracza limit parametrów")
        config = ModelConfig(
            name=raw_config["name"],
            input_size=raw_config["input_size"],
            layers=tuple(
                LayerConfig(
                    neurons=layer["neurons"],
                    activation=layer["activation"],
                )
                for layer in raw_layers
            ),
        )
        model = cls.create(config)

        if len(raw_parameters) != len(model.network.layers):
            raise ValueError("liczba zapisanych warstw nie odpowiada konfiguracji")
        for network_layer, saved_layer in zip(model.network.layers, raw_parameters, strict=True):
            if not isinstance(saved_layer, dict):
                raise ValueError("nieprawidłowe parametry warstwy")
            weights = saved_layer.get("weights")
            biases = saved_layer.get("biases")
            if not isinstance(weights, list) or not isinstance(biases, list):
                raise ValueError("nieprawidłowe wagi lub biasy")
            if len(weights) != len(network_layer.neurons) or len(biases) != len(network_layer.neurons):
                raise ValueError("liczba parametrów nie odpowiada warstwie")
            for neuron, raw_weights, raw_bias in zip(network_layer.neurons, weights, biases, strict=True):
                if not isinstance(raw_weights, list) or len(raw_weights) != neuron.weight.numel():
                    raise ValueError("wymiary wag nie odpowiadają modelowi")
                try:
                    normalized_weights = [float(value) for value in raw_weights]
                    normalized_bias = float(raw_bias)
                except (TypeError, ValueError, OverflowError) as error:
                    raise ValueError("wagi i biasy muszą być liczbami") from error
                if not all(math.isfinite(value) for value in normalized_weights) or not math.isfinite(normalized_bias):
                    raise ValueError("model zawiera nieprawidłowe parametry liczbowe")

        with torch.no_grad():
            for layer, saved_layer in zip(
                model.network.layers,
                payload["parameters"],
                strict=True,
            ):
                for neuron, weights, bias in zip(
                    layer.neurons,
                    saved_layer["weights"],
                    saved_layer["biases"],
                    strict=True,
                ):
                    try:
                        neuron.weight.data.copy_(
                            torch.tensor(weights, dtype=neuron.weight.dtype)
                        )
                        neuron.bias.data.fill_(bias)
                    except (RuntimeError, TypeError, ValueError, OverflowError) as error:
                        raise ValueError("nie można odtworzyć parametrów modelu") from error
        if not model.parameters_are_finite():
            raise ValueError("model zawiera nieprawidłowe parametry liczbowe")
        return model
