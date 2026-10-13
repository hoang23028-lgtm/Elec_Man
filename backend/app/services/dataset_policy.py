"""Pure dataset policy shared by API, trainer and evaluation: no ML dependencies."""

import json
import re
from hashlib import sha256

from app.schemas.result import ReadingPolygon

POLICY_VERSION = "verified-meter-split-v1"
PARTITIONS = ("TRAIN", "VALIDATION", "HOLDOUT")


def identity_tokens(sample):
    image, reading, annotation = sample["image"], sample["reading"], sample.get("annotation") or {}
    tokens = [f"image:{image['sha256']}"]
    if reading.get("matched_customer_id"):
        tokens.append(f"customer:{reading['matched_customer_id']}")
    if reading.get("final_customer_id"):
        tokens.append(f"code:{reading['final_customer_id'].strip().upper()}")
    if annotation.get("group_key"):
        tokens.append(f"group:{annotation['group_key']}")
    return tokens


def grouped_samples(samples):
    parents = {}

    def root(token):
        parents.setdefault(token, token)
        while parents[token] != token:
            parents[token] = parents[parents[token]]
            token = parents[token]
        return token

    for sample in samples:
        tokens = identity_tokens(sample)
        for token in tokens[1:]:
            left, right = sorted((root(tokens[0]), root(token)))
            parents[right] = left
    groups = {}
    for sample in samples:
        groups.setdefault(root(identity_tokens(sample)[0]), []).append(sample)
    return groups


def sample_issues(sample):
    reading = sample.get("reading") or {}
    annotation = sample.get("annotation") or {}
    issues = []
    if reading.get("review_status") not in {"LABELED", "CONFIRMED"} or not reading.get(
        "reviewed_by"
    ):
        issues.append("Chưa có nhãn số do con người lưu")
    if not reading.get("bbox_reviewed_by") or not reading.get("meter_bbox_reviewed_by"):
        issues.append("Hai vùng cần được con người lưu")
    if not re.fullmatch(r"[0-9]{4,8}", reading.get("final_meter_reading") or ""):
        issues.append("Nhãn phải gồm 4–8 chữ số nguyên, giữ số 0 đầu và bỏ bánh đỏ")
    for key, description in (
        ("reading_polygon_json", "Thiếu/sai vùng chỉ số"),
        ("meter_polygon_json", "Thiếu/sai vùng công tơ"),
    ):
        try:
            ReadingPolygon.model_validate(reading.get(key))
        except (ValueError, TypeError):
            issues.append(description)
    if not any(issue.startswith("Thiếu/sai vùng") for issue in issues):
        frame = reading["meter_polygon_json"]["points"]
        for point in reading["reading_polygon_json"]["points"]:
            signs = []
            for a, b in zip(frame, frame[1:] + frame[:1], strict=True):
                signs.append(
                    (b["x"] - a["x"]) * (point["y"] - a["y"])
                    - (b["y"] - a["y"]) * (point["x"] - a["x"])
                )
            if min(signs) < -1e-6 and max(signs) > 1e-6:
                issues.append("Vùng chỉ số nằm ngoài vùng công tơ; cần kiểm tra lại")
                break
    if not annotation.get("group_key") or not annotation.get("identity_verified"):
        issues.append("Chưa xác minh nhóm công tơ")
    if not annotation.get("label_verified") or annotation.get("label_revision") != reading.get(
        "revision"
    ):
        issues.append("Chưa kiểm tra nhãn/vùng ở phiên bản hiện tại")
    if annotation.get("partition") not in PARTITIONS:
        issues.append("Chưa phân tập dữ liệu")
    return issues


def base_eligible(sample):
    reading = sample.get("reading") or {}
    return (
        reading.get("review_status") in {"LABELED", "CONFIRMED"}
        and reading.get("reviewed_by") is not None
        and reading.get("bbox_reviewed_by") is not None
        and reading.get("meter_bbox_reviewed_by") is not None
        and re.fullmatch(r"[0-9]{4,8}", reading.get("final_meter_reading") or "") is not None
        and all(reading.get(key) for key in ("reading_polygon_json", "meter_polygon_json"))
    )


def make_manifest(samples, *, experimental=False):
    groups = grouped_samples(samples)
    diagnostic_keys = sorted(
        (
            key
            for key, group in groups.items()
            if not any((s.get("annotation") or {}).get("partition") in PARTITIONS for s in group)
        ),
        key=lambda key: sha256(key.encode()).hexdigest(),
    )
    diagnostic_validation = set(diagnostic_keys[: max(1, len(diagnostic_keys) // 5)])
    partitions = {key: [] for key in PARTITIONS}
    skipped = []
    unknown = 0
    for key, group in groups.items():
        assigned = {(s.get("annotation") or {}).get("partition") for s in group} - {
            None,
            "UNASSIGNED",
        }
        if "HOLDOUT" in assigned:
            # A reserved image/hash/customer/group is never allowed back into training.
            if assigned - {"HOLDOUT"}:
                raise ValueError("Nhóm công tơ có ảnh holdout lẫn với tập học. Hãy sửa phân tập.")
            destination = "HOLDOUT"
        elif len(assigned) > 1:
            raise ValueError("Cùng công tơ đang nằm trong cả train và validation.")
        else:
            destination = next(iter(assigned), None)
        eligible = [s for s in group if base_eligible(s)]
        valid = [s for s in eligible if not sample_issues(s)]
        unknown += sum(
            not (
                s.get("annotation", {}).get("group_key")
                and s.get("annotation", {}).get("identity_verified")
            )
            for s in eligible
        )
        if experimental and destination != "HOLDOUT":
            # Diagnostic only: keep linked groups disjoint even without verified identity.
            valid = eligible
            destination = destination or ("VALIDATION" if key in diagnostic_validation else "TRAIN")
        if destination:
            partitions[destination].extend(valid)
        valid_ids = {s["image"]["id"] for s in valid}
        skipped.extend(s["image"]["id"] for s in group if s["image"]["id"] not in valid_ids)
    seen = set()
    for partition in PARTITIONS:
        unique = []
        for sample in sorted(partitions[partition], key=lambda s: s["image"]["sha256"]):
            digest = sample["image"]["sha256"]
            if digest not in seen:
                seen.add(digest)
                unique.append(sample)
        partitions[partition] = unique
    body = {
        "format": POLICY_VERSION,
        "experimental": experimental,
        "partitions": partitions,
        "unknown_meter_identity_samples": unknown,
        "skipped_image_ids": sorted(skipped),
        "independent_holdout": bool(partitions["HOLDOUT"]) and not experimental,
        "validation_groups_verified": bool(partitions["VALIDATION"]) and not experimental,
        "meter_identity_groups": len(groups),
    }
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {**body, "sha256": sha256(encoded).hexdigest()}
