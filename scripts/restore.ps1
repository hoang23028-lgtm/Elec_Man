param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [switch]$ConfirmRestore,
    [string]$EnvFile = ".env",
    [string]$ProjectName = "elec_man"
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Khôi phục sẽ thay thế dữ liệu hiện tại. Hãy chạy lại với -ConfirmRestore." }
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
$required = @("database.sql", "storage.tar.gz", "models.tar.gz", "checksums.sha256")
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $backup $name) -PathType Leaf)) { throw "Thiếu tệp sao lưu: $name" }
}
foreach ($line in Get-Content -LiteralPath (Join-Path $backup "checksums.sha256")) {
    $parts = $line -split "\s+", 2
    if ($parts.Count -ne 2) { continue }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup $parts[1])).Hash.ToLowerInvariant()
    if ($actual -ne $parts[0]) { throw "Checksum không khớp: $($parts[1])" }
}

docker compose --env-file $EnvFile stop nginx frontend backend worker
docker compose --env-file $EnvFile cp (Join-Path $backup "database.sql") postgres:/tmp/electric-meter-ai-restore.sql
docker compose --env-file $EnvFile exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/electric-meter-ai-restore.sql'
if ($LASTEXITCODE -ne 0) { throw "Khôi phục cơ sở dữ liệu thất bại; các dịch vụ ứng dụng vẫn đang dừng." }
docker run --rm -v "${ProjectName}_storage_data:/target" -v "${backup}:/backup:ro" alpine:3.21 sh -c "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/storage.tar.gz -C /target"
docker run --rm -v "${ProjectName}_model_data:/target" -v "${backup}:/backup:ro" alpine:3.21 sh -c "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/models.tar.gz -C /target"
docker compose --env-file $EnvFile exec -T postgres rm -f /tmp/electric-meter-ai-restore.sql
docker compose --env-file $EnvFile up -d
