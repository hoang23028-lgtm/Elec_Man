#!/usr/bin/env sh
set -eu

BACKUP_DIRECTORY="${1:?Usage: sh scripts/verify-backup.sh <backup-directory>}"
BACKUP_DIRECTORY="$(cd -- "$BACKUP_DIRECTORY" && pwd)"
WORKSPACE="$(cd -- "$(dirname -- "$0")/.." && pwd)"
docker run --rm --network none --user 0 --cap-drop ALL --security-opt no-new-privileges --read-only --mount "type=bind,source=$WORKSPACE,target=/workspace,readonly" --mount "type=bind,source=$BACKUP_DIRECTORY,target=/backup,readonly" --entrypoint python elec_man-backend:latest /workspace/scripts/verify_backup.py /backup
printf 'Backup verified: %s\n' "$BACKUP_DIRECTORY"
