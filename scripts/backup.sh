#!/usr/bin/env sh
set -eu

WORKSPACE="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
cd -- "$WORKSPACE"
umask 077
ENV_FILE="${ENV_FILE:-.env}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-elec_man}"
case "$PROJECT_NAME" in ''|*[!a-z0-9_-]*|-*|_*) echo 'Invalid project name' >&2; exit 1;; esac
case "$BACKUP_ROOT" in ''|/*|*..*|*\\*) echo 'Backup root must be relative and inside the project' >&2; exit 1;; esac
for suffix in storage_data model_data; do
  owner=$(docker volume inspect --format '{{ index .Labels "com.docker.compose.project" }}' "${PROJECT_NAME}_${suffix}")
  test "$owner" = "$PROJECT_NAME" || { echo 'Volume belongs to a different project' >&2; exit 1; }
done
mkdir -p -- "$BACKUP_ROOT"
ABS_ROOT="$(cd -- "$BACKUP_ROOT" && pwd -P)"
case "$ABS_ROOT/" in "$WORKSPACE/"*) ;; *) echo 'Backup root escapes the project' >&2; exit 1;; esac
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINATION="$ABS_ROOT/$TIMESTAMP"
mkdir -- "$DESTINATION"
docker compose --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$DESTINATION/database.sql"
docker run --rm -v "${PROJECT_NAME}_storage_data:/source:ro" -v "$DESTINATION:/backup" alpine:3.21 tar -czf /backup/storage.tar.gz -C /source .
docker run --rm -v "${PROJECT_NAME}_model_data:/source:ro" -v "$DESTINATION:/backup" alpine:3.21 tar -czf /backup/models.tar.gz -C /source .
(cd -- "$DESTINATION" && sha256sum database.sql storage.tar.gz models.tar.gz > checksums.sha256)
printf '%s\n' "$DESTINATION"
