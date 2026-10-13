"""HTTP/security probe overlapping real CPU training on disposable synthetic data."""

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from verification_probe import probe_application
from verification_sandbox import ROOT, TEST_PASSWORD


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("report must be a new file")
    marker = TemporaryDirectory(prefix="elec-man-mixed-probe-")
    stop_file = Path(marker.name) / "stop"
    sandbox = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts/verification_sandbox.py"),
            "--minutes",
            "10",
            "--stop-file",
            str(stop_file),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    name = f"elec-man-training-probe-{uuid4().hex}"
    training = None
    try:
        url = None
        for line in sandbox.stdout:
            if line.startswith("READY "):
                url = line.strip().split(" ", 1)[1]
                break
        if not url:
            raise RuntimeError("Disposable sandbox did not start")
        training = subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                name,
                "--label",
                "elec-man.verification=true",
                "--cpus",
                "1",
                "--memory",
                "2g",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp:size=256m,mode=1777",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "elec_man-trainer",
                "python",
                "-m",
                "ai.tools.smoke_sequence_training",
                "--epochs",
                "20",
                "--signal-progress",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        events = []
        ready = threading.Event()

        def collect():
            for line in training.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                events.append(event)
                if "epoch_completed" in event:
                    ready.set()
            ready.set()

        collector = threading.Thread(target=collect, daemon=True)
        collector.start()
        if not ready.wait(90) or not events or "epoch_completed" not in events[0]:
            raise RuntimeError("Training did not start")
        started = time.time()
        report = probe_application(url, TEST_PASSWORD, True)
        completed = time.time()
        training.wait(timeout=180)
        collector.join(timeout=5)
        if training.returncode != 0 or not any(
            e.get("optimizer_updated_decoder") for e in events
        ):
            raise RuntimeError("Synthetic training smoke failed")
        epoch_times = [e["at"] for e in events if "epoch_completed" in e]
        report.update(
            {
                "scope": "disposable_synthetic_http_plus_cpu_optimizer_not_production_sla",
                "training_epochs": len(epoch_times),
                "training_epoch_events_during_http": sum(
                    started <= t <= completed for t in epoch_times
                ),
                "http_duration_seconds": round(completed - started, 3),
                "training_optimizer_verified": True,
                "real_data_used": False,
                "live_database_or_volumes_used": False,
            }
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        if training and training.poll() is None:
            subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            training.wait(timeout=30)
        if sandbox.poll() is None:
            stop_file.touch()
            sandbox.wait(timeout=60)
        marker.cleanup()


if __name__ == "__main__":
    main()
