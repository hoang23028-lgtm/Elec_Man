param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [switch]$ConfirmRestore,
    [string]$EnvFile = ".env",
    [string]$ProjectName = "elec_man"
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Khôi phục sẽ thay thế dữ liệu hiện tại. Hãy chạy lại với -ConfirmRestore." }
if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]*$') { throw "Tên dự án không hợp lệ." }
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
& (Join-Path $PSScriptRoot "verify-backup.ps1") -BackupDirectory $backup
foreach ($suffix in @("storage_data", "model_data")) {
    $volume = "${ProjectName}_${suffix}"
    $owner = docker volume inspect --format '{{ index .Labels "com.docker.compose.project" }}' $volume
    if ($LASTEXITCODE -ne 0 -or $owner -ne $ProjectName) {
        throw "Volume không thuộc đúng dự án: $volume"
    }
}

docker compose --project-name $ProjectName --env-file $EnvFile stop nginx frontend backend worker trainer
if ($LASTEXITCODE -ne 0) { throw "Không dừng được dịch vụ; chưa thay thế dữ liệu." }
docker compose --project-name $ProjectName --env-file $EnvFile cp (Join-Path $backup "database.sql") postgres:/tmp/electric-meter-ai-restore.sql
if ($LASTEXITCODE -ne 0) { throw "Không chép được database dump; chưa thay thế dữ liệu." }
# Schema replacement and SQL import share one transaction: SQL failure rolls back both.
docker compose --project-name $ProjectName --env-file $EnvFile exec -T postgres sh -c '{ printf "DROP SCHEMA public CASCADE; CREATE SCHEMA public;\n"; cat /tmp/electric-meter-ai-restore.sql; } | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 --single-transaction'
if ($LASTEXITCODE -ne 0) { throw "Khôi phục cơ sở dữ liệu thất bại; các dịch vụ ứng dụng vẫn đang dừng." }
docker run --rm -v "${ProjectName}_storage_data:/target" -v "${backup}:/backup:ro" alpine:3.21 sh -c "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/storage.tar.gz -C /target"
if ($LASTEXITCODE -ne 0) { throw "Khôi phục kho ảnh thất bại; dịch vụ vẫn đang dừng." }
docker run --rm -v "${ProjectName}_model_data:/target" -v "${backup}:/backup:ro" alpine:3.21 sh -c "find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/models.tar.gz -C /target"
if ($LASTEXITCODE -ne 0) { throw "Khôi phục kho mô hình thất bại; dịch vụ vẫn đang dừng." }
docker compose --project-name $ProjectName --env-file $EnvFile exec -T postgres rm -f /tmp/electric-meter-ai-restore.sql
docker compose --project-name $ProjectName --env-file $EnvFile up -d
if ($LASTEXITCODE -ne 0) { throw "Dữ liệu đã phục hồi nhưng dịch vụ chưa khởi động thành công." }
