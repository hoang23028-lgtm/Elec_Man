#!/usr/bin/env sh
set -eu

BACKUP_DIRECTORY="${1:?Cách dùng: ./scripts/verify-backup.sh <thư-mục-backup>}"
BACKUP_DIRECTORY="$(cd "$BACKUP_DIRECTORY" && pwd)"
for name in database.sql storage.tar.gz models.tar.gz checksums.sha256; do
  test -s "$BACKUP_DIRECTORY/$name" || { printf 'Thiếu hoặc rỗng: %s\n' "$name" >&2; exit 1; }
done
(cd "$BACKUP_DIRECTORY" && sha256sum --check checksums.sha256)
docker run --rm -v "$BACKUP_DIRECTORY:/backup:ro" alpine:3.21 tar -tzf /backup/storage.tar.gz >/dev/null
docker run --rm -v "$BACKUP_DIRECTORY:/backup:ro" alpine:3.21 tar -tzf /backup/models.tar.gz >/dev/null
printf 'Backup hợp lệ: %s\n' "$BACKUP_DIRECTORY"
