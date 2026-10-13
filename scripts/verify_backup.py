"""Check a backup manifest and archive paths without connecting to a database."""

import argparse
import tarfile
from pathlib import Path

from rehearse_backup import safe_members, verify_payloads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    verify_payloads(args.directory)
    for name in ("storage.tar.gz", "models.tar.gz"):
        with tarfile.open(args.directory / name, "r:gz") as archive:
            safe_members(archive)
    print("Backup checksums and archive paths verified.")


if __name__ == "__main__":
    main()
