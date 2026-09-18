#!/usr/bin/env sh
set -eu

ENV_FILE="${ENV_FILE:-.env}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-elec_man}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINATION="$BACKUP_ROOT/$TIMESTAMP"
mkdir -p "$DESTINATION"

docker compose --env-file "$ENV_FILE" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$DESTINATION/database.sql"
ABS_DESTINATION="$(cd "$DESTINATION" && pwd)"
docker run --rm -v "${PROJECT_NAME}_storage_data:/source:ro" -v "$ABS_DESTINATION:/backup" alpine:3.21 tar -czf /backup/storage.tar.gz -C /source .
docker run --rm -v "${PROJECT_NAME}_model_data:/source:ro" -v "$ABS_DESTINATION:/backup" alpine:3.21 tar -czf /backup/models.tar.gz -C /source .
(cd "$DESTINATION" && sha256sum database.sql storage.tar.gz models.tar.gz > checksums.sha256)
printf '%s\n' "$DESTINATION"
