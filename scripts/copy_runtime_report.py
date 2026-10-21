"""Copy a generated benchmark JSON from a container tmpfs, without secrets/env."""

import argparse
import json
import re

from managed_backup import ROOT, docker, inventory


def copy_report(project, name):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", project):
        raise ValueError("Tên project không hợp lệ.")
    if not re.fullmatch(r"(?:encoder|automatic-latency)[a-z0-9-]{0,80}\.json", name):
        raise ValueError("Tên report không hợp lệ.")
    worker = inventory(project)["worker"]["Id"]
    raw = docker(
        "exec",
        worker,
        "python",
        "-c",
        "import sys;sys.stdout.buffer.write(open(sys.argv[1],'rb').read(5242881))",
        f"/tmp/{name}",
        timeout=60,
    )
    if len(raw.encode()) > 5 * 1024**2:
        raise ValueError("Report vượt giới hạn.")
    report = json.loads(raw)
    if (
        not isinstance(report, dict)
        or report.get("scope") != "saved_labels_diagnostic_not_independent_holdout"
        or report.get("database_mutated") is not False
    ):
        raise ValueError("Không phải report benchmark hợp lệ.")
    folder = ROOT / ".codex-tmp"
    if folder.is_symlink() or folder.resolve().parent != ROOT.resolve():
        raise ValueError("Thư mục report không hợp lệ.")
    folder.mkdir(exist_ok=True)
    path = folder / name
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="elec_man")
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    print(copy_report(args.project, args.name))


if __name__ == "__main__":
    main()
