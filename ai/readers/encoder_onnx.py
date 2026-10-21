"""Optional PARSeq visual encoder acceleration; decoder semantics stay upstream."""

import json
from hashlib import sha256

import numpy as np

REVISION = "1902db043c029a7e03a3818c616c06600af574be"


def encoder_digest(model):
    digest = sha256()
    for name, tensor in sorted(model.model.encoder.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def export_encoder(reader, path):
    import onnx
    import torch

    if path.exists():
        raise ValueError("Không ghi đè bộ mã hóa ONNX.")
    encoder = reader.model.model.encoder.eval()
    example = torch.zeros(1, 3, *reader.model.hparams.img_size)
    torch.onnx.export(
        encoder,
        example,
        str(path),
        opset_version=17,
        input_names=["image"],
        output_names=["memory"],
    )
    graph = onnx.load(str(path))
    onnx.helper.set_model_props(
        graph,
        {"base_revision": REVISION, "encoder_sha256": encoder_digest(reader.model)},
    )
    onnx.checker.check_model(graph)
    onnx.save(graph, str(path))
    manifest = {
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "encoder_sha256": encoder_digest(reader.model),
    }
    path.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


class EncoderSession:
    def __init__(self, path):
        import onnxruntime as ort

        ort.disable_telemetry_events()

        manifest = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if (
            path.stat().st_size > 40 * 1024**2
            or sha256(path.read_bytes()).hexdigest() != manifest["sha256"]
        ):
            raise ValueError("Checksum ONNX encoder không khớp.")
        options = ort.SessionOptions()
        options.intra_op_num_threads = options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        metadata = self.session.get_modelmeta().custom_metadata_map
        self.encoder_sha256 = metadata.get("encoder_sha256")
        if (
            metadata.get("base_revision") != REVISION
            or self.encoder_sha256 != manifest["encoder_sha256"]
        ):
            raise ValueError("Encoder ONNX không tương thích.")

    def encode(self, tensor):
        import torch

        result = self.session.run(None, {"image": tensor.detach().cpu().numpy()})[0]
        if not np.isfinite(result).all():
            raise ValueError("Encoder ONNX trả dữ liệu không hữu hạn.")
        return torch.from_numpy(result).to(tensor.device)
