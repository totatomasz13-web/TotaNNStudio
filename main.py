"""Pierwszy uruchamialny pion TotaNNStudio."""

import argparse
from importlib.metadata import version
from pathlib import Path

from totannstudio import LayerConfig, ModelConfig, StudioModel


def run_demo(output: Path):
    training_data = [
        ([0, 0], 0),
        ([0, 1], 1),
        ([1, 0], 1),
        ([1, 1], 1),
    ]
    config = ModelConfig(
        name="LogicOR",
        input_size=2,
        layers=(LayerConfig(neurons=1, activation="sigmoid"),),
    )
    model = StudioModel.create(config)
    print(f"Silnik: tota {version('tota')}")
    print(f"Model: {model.summary()}")
    print(model.train(training_data, learning_rate=0.2, epochs=3000))
    predictions = [model.predict(row) for row, _ in training_data]
    print(f"Predykcje: {predictions}")
    model.save(output)
    print(f"Zapisano: {output}")


def parse_args():
    parser = argparse.ArgumentParser(description="TotaNNStudio")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Trenuje demonstracyjny model OR")
    demo.add_argument(
        "--output",
        type=Path,
        default=Path("models/logic-or.tota.json"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "demo":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        run_demo(args.output)


if __name__ == "__main__":
    main()
