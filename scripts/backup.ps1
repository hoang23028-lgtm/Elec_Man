param(
    [string]$EnvFile = ".env",
    [string]$BackupRoot = "backups",
    [string]$ProjectName = "elec_man"
)

$ErrorActionPreference = "Stop"
if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]*$') { throw "Tên dự án không hợp lệ." }
foreach ($suffix in @("storage_data", "model_data")) {
    $volume = "${ProjectName}_${suffix}"
    $owner = docker volume inspect --format '{{ index .Labels "com.docker.compose.project" }}' $volume
    if ($LASTEXITCODE -ne 0 -or $owner -ne $ProjectName) {
        throw "Volume không thuộc đúng dự án: $volume"
    }
}
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$root = [IO.Path]::GetFullPath((Join-Path $workspace $BackupRoot))
if (-not $root.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar)) {
    throw "BackupRoot phải nằm trong thư mục dự án."
}
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$destination = Join-Path $root $timestamp
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$databaseFile = Join-Path $destination "database.sql"
$databaseContainerFile = "/tmp/electric-meter-ai-backup.sql"
docker compose --project-name $ProjectName --env-file $EnvFile exec -T postgres sh -c "pg_dump -U `$POSTGRES_USER -d `$POSTGRES_DB -f $databaseContainerFile"
if ($LASTEXITCODE -ne 0) { throw "Sao lưu cơ sở dữ liệu thất bại." }
docker compose --project-name $ProjectName --env-file $EnvFile cp "postgres:$databaseContainerFile" $databaseFile
if ($LASTEXITCODE -ne 0) { throw "Không chép được bản sao lưu cơ sở dữ liệu." }
docker compose --project-name $ProjectName --env-file $EnvFile exec -T postgres rm -f $databaseContainerFile

docker run --rm -v "${ProjectName}_storage_data:/source:ro" -v "${destination}:/backup" alpine:3.21 tar -czf /backup/storage.tar.gz -C /source .
if ($LASTEXITCODE -ne 0) { throw "Sao lưu vùng lưu trữ thất bại." }
docker run --rm -v "${ProjectName}_model_data:/source:ro" -v "${destination}:/backup" alpine:3.21 tar -czf /backup/models.tar.gz -C /source .
if ($LASTEXITCODE -ne 0) { throw "Sao lưu mô hình thất bại." }

$checksums = Get-ChildItem -LiteralPath $destination -File | ForEach-Object {
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
    "$($hash.Hash.ToLowerInvariant())  $($_.Name)"
}
$checksums | Set-Content -LiteralPath (Join-Path $destination "checksums.sha256") -Encoding utf8NoBOM
Write-Output $destination
