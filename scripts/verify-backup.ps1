param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory
)

$ErrorActionPreference = "Stop"
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
$required = @("database.sql", "storage.tar.gz", "models.tar.gz", "checksums.sha256")
foreach ($name in $required) {
    $path = Join-Path $backup $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Thiếu tệp sao lưu: $name"
    }
    if ((Get-Item -LiteralPath $path).Length -eq 0) {
        throw "Tệp sao lưu rỗng: $name"
    }
}

$expected = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $backup "checksums.sha256")) {
    if ($line -notmatch '^([a-fA-F0-9]{64})\s+(.+)$') {
        throw "Dòng checksum không hợp lệ."
    }
    $expected[$Matches[2]] = $Matches[1].ToLowerInvariant()
}
foreach ($name in $required | Where-Object { $_ -ne "checksums.sha256" }) {
    if (-not $expected.ContainsKey($name)) { throw "Thiếu checksum: $name" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup $name)).Hash.ToLowerInvariant()
    if ($actual -ne $expected[$name]) { throw "Checksum không khớp: $name" }
}

docker run --rm -v "${backup}:/backup:ro" alpine:3.21 tar -tzf /backup/storage.tar.gz | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Kho ảnh sao lưu không đọc được." }
docker run --rm -v "${backup}:/backup:ro" alpine:3.21 tar -tzf /backup/models.tar.gz | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Kho mô hình sao lưu không đọc được." }
Write-Output "Backup hợp lệ: $backup"
