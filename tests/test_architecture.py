import unittest

from tota import Layer, Network

from totannstudio.studio import LayerConfig, ModelConfig, StudioModel


class ArchitectureTests(unittest.TestCase):
    def test_builds_real_tota_network_from_configuration(self):
        config = ModelConfig(
            name="PrimeNet",
            input_size=2,
            layers=(
                LayerConfig(neurons=4, activation="relu"),
                LayerConfig(neurons=1, activation="sigmoid"),
            ),
        )

        model = StudioModel.create(config)

        self.assertIsInstance(model.network, Network)
        self.assertTrue(all(isinstance(layer, Layer) for layer in model.network.layers))
        self.assertEqual([layer.i_w for layer in model.network.layers], [2, 4])
        self.assertEqual([layer.i_n for layer in model.network.layers], [4, 1])
        self.assertEqual(model.summary()["parameters"], 17)

    def test_rejects_layer_with_zero_neurons(self):
        with self.assertRaisesRegex(ValueError, "neurons"):
            LayerConfig(neurons=0, activation="relu")

    def test_rejects_empty_architecture(self):
        with self.assertRaisesRegex(ValueError, "layer"):
            ModelConfig(name="Empty", input_size=2, layers=())


if __name__ == "__main__":
    unittest.main()
