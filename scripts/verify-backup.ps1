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
    if ($line -notmatch '^([a-fA-F0-9]{64})\s{2}(database\.sql|storage\.tar\.gz|models\.tar\.gz)$') {
        throw "Dòng checksum không hợp lệ."
    }
    if ($expected.ContainsKey($Matches[2])) { throw "Checksum bị trùng: $($Matches[2])" }
    $expected[$Matches[2]] = $Matches[1].ToLowerInvariant()
}
foreach ($name in $required | Where-Object { $_ -ne "checksums.sha256" }) {
    if (-not $expected.ContainsKey($name)) { throw "Thiếu checksum: $name" }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup $name)).Hash.ToLowerInvariant()
    if ($actual -ne $expected[$name]) { throw "Checksum không khớp: $name" }
}

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
docker run --rm --network none --user 0 --cap-drop ALL --security-opt no-new-privileges --read-only --mount "type=bind,source=$workspace,target=/workspace,readonly" --mount "type=bind,source=$backup,target=/backup,readonly" --entrypoint python elec_man-backend:latest /workspace/scripts/verify_backup.py /backup
if ($LASTEXITCODE -ne 0) { throw "Kho sao lưu có đường dẫn không an toàn hoặc không đọc được." }
Write-Output "Backup hợp lệ: $backup"
