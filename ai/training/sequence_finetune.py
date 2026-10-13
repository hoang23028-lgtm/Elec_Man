"""Supervised PARSeq-tiny adaptation with teacher forcing, never pickle artifacts."""

import json
import re
from hashlib import sha256
from pathlib import Path
from time import monotonic, perf_counter

import cv2

from ai.readers.sequence import ParseqTinyReader
from ai.training.metrics import reading_metrics

PARSEQ_REVISION = "1902db043c029a7e03a3818c616c06600af574be"


def dataset_items(root, split):
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected = {(r["split"], r["source_sha256"]): r for r in manifest}
    rows = []
    for line in (root / f"{split}.tsv").read_text(encoding="utf-8").splitlines():
        relative, label = line.split("\t")
        path = (root / relative).resolve()
        if (
            not path.is_relative_to(root / split)
            or path.suffix != ".png"
            or not re.fullmatch(r"[0-9]{4,8}", label)
        ):
            raise ValueError("Bộ crop/nhãn huấn luyện không hợp lệ.")
        entry = expected.get((split, path.stem))
        if (
            not entry
            or entry["label"] != label
            or sha256(path.read_bytes()).hexdigest() != entry["crop_sha256"]
        ):
            raise ValueError("Checksum/nhãn crop không khớp manifest.")
        rows.append((path, label))
    return rows


def autoregressive_loss(system, images, labels):
    import torch
    from torch.nn.functional import cross_entropy

    tokens = system.tokenizer.encode(labels, images.device)
    context, expected = tokens[:, :-1], tokens[:, 1:]
    memory = system.model.encode(images)
    content_mask, query_mask = system.generate_attn_masks(
        torch.arange(tokens.shape[1], device=images.device)
    )
    padding = (context == system.pad_id) | (context == system.eos_id)
    states = system.model.decode(
        context, memory, content_mask, padding, tgt_query_mask=query_mask
    )
    return cross_entropy(
        system.model.head(states).flatten(0, 1),
        expected.flatten(),
        ignore_index=system.pad_id,
    )


def evaluate_reader(reader, items):
    records = []
    for path, label in items:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError("Không thể đọc crop đánh giá.")
        started = perf_counter()
        predicted, confidence = reader.predict(image, len(label))
        records.append(
            {
                "expected": label,
                "predicted": predicted,
                "confidence": confidence,
                "elapsed_ms": (perf_counter() - started) * 1000,
            }
        )
    return reading_metrics(records)


def fine_tune(
    dataset_root, artifact, options, progress=None, *, max_seconds=7200, checkpoint=None
):
    import torch
    from PIL import Image
    from safetensors.torch import save_file

    if artifact.exists():
        raise ValueError("Artifact của phiên đã tồn tại; không được ghi đè.")
    train = dataset_items(dataset_root, "train")
    validation = dataset_items(dataset_root, "validation")
    if len(train) < 2 or not validation:
        raise ValueError("Thiếu tập train/validation tách biệt.")
    torch.set_num_threads(1)
    torch.manual_seed(42)
    reader = ParseqTinyReader(Path("/opt/parseq"))
    model = reader.model
    # Adapt decoder/head on small datasets; the visual encoder stays pretrained.
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(not name.startswith("model.encoder."))
    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=options["learning_rate"],
        weight_decay=0.01,
    )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    best_score = -1.0
    best_epoch = 0
    history = []
    deadline = monotonic() + max_seconds
    for epoch in range(options["epochs"]):
        if monotonic() > deadline:
            raise TimeoutError("Phiên huấn luyện vượt ngân sách thời gian.")
        model.train()
        model.model.encoder.eval()
        losses = []
        order = torch.randperm(len(train)).tolist()
        for start in range(0, len(train), options["batch_size"]):
            if checkpoint:
                checkpoint()
            if monotonic() > deadline:
                raise TimeoutError("Phiên huấn luyện vượt ngân sách thời gian.")
            rows = [train[i] for i in order[start : start + options["batch_size"]]]
            tensors = []
            for path, _ in rows:
                with Image.open(path) as image:
                    tensors.append(reader.transform(image.convert("RGB")))
            optimizer.zero_grad(set_to_none=True)
            loss = autoregressive_loss(
                model, torch.stack(tensors), [label for _, label in rows]
            )
            if not torch.isfinite(loss):
                raise ValueError("Loss huấn luyện không hữu hạn.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        metrics = evaluate_reader(reader, validation)
        history.append(
            {
                "epoch": epoch + 1,
                "loss": sum(losses) / len(losses),
                "validation": metrics,
            }
        )
        score = metrics["exact_accuracy"] - metrics["character_error_rate"] * 0.01
        if score > best_score:
            state = {
                name: tensor.detach().cpu().contiguous().clone()
                for name, tensor in model.state_dict().items()
            }
            temporary = artifact.with_suffix(".tmp")
            save_file(
                state,
                str(temporary),
                metadata={
                    "base_model": "parseq_tiny",
                    "base_revision": PARSEQ_REVISION,
                    "training": "supervised-autoregressive-v1",
                },
            )
            temporary.replace(artifact)
            best_score, best_epoch = score, epoch + 1
        if progress:
            progress(epoch + 1, options["epochs"], history[-1])
    digest = sha256(artifact.read_bytes()).hexdigest()
    reader.load_checkpoint(artifact, digest)
    return reader, {
        "epochs": options["epochs"],
        "best_epoch": best_epoch,
        "history": history,
        "validation": evaluate_reader(reader, validation),
        "sha256": digest,
        "algorithm": "parseq-tiny-supervised-autoregressive-v1",
        "encoder_frozen": True,
    }
