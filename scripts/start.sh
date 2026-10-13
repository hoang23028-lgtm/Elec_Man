#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-elec_man}"
ENV_FILE="${ENV_FILE:-.env}"
PORT="${NGINX_HTTP_PORT:-80}"
USERNAME="${ADMIN_USERNAME:-admin}"
[[ "$PROJECT_NAME" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo 'Invalid project name' >&2; exit 1; }
[[ "$ENV_FILE" =~ ^\.env(\.[a-zA-Z0-9_-]+)?$ && "$ENV_FILE" != .env.example ]] || { echo 'Invalid private environment filename' >&2; exit 1; }
[[ "$PORT" =~ ^[0-9]+$ ]] && ((PORT >= 1 && PORT <= 65535)) || { echo 'Invalid HTTP port' >&2; exit 1; }
docker info --format '{{.ServerVersion}}'
docker compose version
if [[ ! -e "$ENV_FILE" ]]; then
  containers=$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT_NAME")
  volumes=$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT_NAME")
  if [[ -n "$containers$volumes" ]]; then
    echo "Existing deployment has no $ENV_FILE. Recover original configuration; do not rotate secrets." >&2
    exit 1
  fi
fi
if [[ "${SKIP_BUILD:-0}" != 1 ]]; then docker build --tag elec_man-backend:latest backend; fi
docker run --rm --network none --user 0 --mount "type=bind,source=$PWD,target=/workspace" --entrypoint python elec_man-backend:latest /workspace/scripts/bootstrap.py --env-file "$ENV_FILE" --port "$PORT"
compose=(docker compose --project-name "$PROJECT_NAME" --env-file "$ENV_FILE")
"${compose[@]}" config --quiet
if [[ "${SKIP_BUILD:-0}" != 1 ]]; then "${compose[@]}" build; fi
"${compose[@]}" up -d --wait --wait-timeout 120 postgres
"${compose[@]}" run --rm --no-deps migrate
"${compose[@]}" up -d --wait --wait-timeout 300
status=0
"${compose[@]}" exec -T backend python -m app.scripts.init_admin --check || status=$?
if ((status == 1)); then
  if [[ -z "${ADMIN_INITIAL_PASSWORD:-}" ]]; then
    [[ -t 0 ]] || { echo 'First start needs ADMIN_INITIAL_PASSWORD in the process environment.' >&2; exit 1; }
    read -r -s -p "Password for $USERNAME (12-256 characters): " ADMIN_INITIAL_PASSWORD
    printf '\n'
  fi
  export ADMIN_INITIAL_PASSWORD
  trap 'unset ADMIN_INITIAL_PASSWORD' EXIT
  "${compose[@]}" exec -T -e ADMIN_INITIAL_PASSWORD backend python -m app.scripts.init_admin --username "$USERNAME"
elif ((status != 0)); then
  echo 'Unable to check the administrator account.' >&2
  exit "$status"
fi
printf 'Ready. Open FRONTEND_ORIGIN in %s (default http://localhost/).\n' "$ENV_FILE"
printf 'Stop: docker compose --project-name %s --env-file %s stop\n' "$PROJECT_NAME" "$ENV_FILE"
