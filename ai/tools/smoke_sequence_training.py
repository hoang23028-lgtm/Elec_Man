"""Offline, disposable optimizer/checkpoint smoke test; not an accuracy benchmark."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time

import cv2
import numpy as np

from ai.readers.sequence import ParseqTinyReader
from ai.training.sequence_finetune import fine_tune


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--signal-progress", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.epochs <= 20:
        parser.error("epochs must be 1–20")
    with TemporaryDirectory(prefix="elec-man-reader-smoke-") as temporary:
        root = Path(temporary)
        manifest = []
        for split, count in (("train", 2), ("validation", 1)):
            (root / split).mkdir()
            lines = []
            for index in range(count):
                name = sha256(f"{split}:{index}".encode()).hexdigest()
                image = np.full((48, 180, 3), 220, dtype=np.uint8)
                cv2.putText(
                    image,
                    "00120",
                    (5, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (20, 20, 20),
                    2,
                )
                path = root / split / f"{name}.png"
                assert cv2.imwrite(str(path), image)
                lines.append(f"{split}/{name}.png\t00120")
                manifest.append(
                    {
                        "split": split,
                        "source_sha256": name,
                        "label": "00120",
                        "crop_sha256": sha256(path.read_bytes()).hexdigest(),
                    }
                )
            (root / f"{split}.tsv").write_text("\n".join(lines), encoding="utf-8")
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        baseline = ParseqTinyReader(Path("/opt/parseq"))
        original = {k: v.clone() for k, v in baseline.model.state_dict().items()}
        trained, metrics = fine_tune(
            root,
            root / "model.safetensors",
            {"epochs": args.epochs, "batch_size": 2, "learning_rate": 0.0001},
            progress=(
                lambda epoch, total, result: print(
                    json.dumps({"epoch_completed": epoch, "at": time()}), flush=True
                )
            )
            if args.signal_progress
            else None,
            max_seconds=120,
        )
        assert any(
            not original[k].equal(v) for k, v in trained.model.state_dict().items()
        )
        assert all(
            original[k].equal(v)
            for k, v in trained.model.state_dict().items()
            if k.startswith("model.encoder.")
        )
        baseline.load_checkpoint(root / "model.safetensors", metrics["sha256"])
        a = trained.predict(image, 5)
        b = baseline.predict(image, 5)
        assert a == b
        try:
            baseline.load_checkpoint(root / "model.safetensors", "0" * 64)
        except ValueError:
            pass
        else:
            raise AssertionError("Checksum mismatch was accepted")
        baseline.reset_checkpoint()
        assert all(original[k].equal(v) for k, v in baseline.model.state_dict().items())
        print(
            json.dumps(
                {
                    "optimizer_updated_decoder": True,
                    "encoder_unchanged": True,
                    "checkpoint_reload_equal": True,
                    "checksum_rejected": True,
                    "pretrained_reset_equal": True,
                    "loss": metrics["history"][0]["loss"],
                    "scope": "synthetic_smoke_not_accuracy",
                }
            )
        )


if __name__ == "__main__":
    main()
