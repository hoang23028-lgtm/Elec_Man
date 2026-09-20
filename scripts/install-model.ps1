param(
    [Parameter(Mandatory = $true)][string]$SourceFile,
    [Parameter(Mandatory = $true)][string]$RelativeDestination,
    [string]$ProjectName = "elec_man"
)

$ErrorActionPreference = "Stop"
$normalizedDestination = $RelativeDestination.Replace("\", "/").Trim("/")
$segments = $normalizedDestination.Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)
if (
    [IO.Path]::IsPathRooted($RelativeDestination) -or
    -not $normalizedDestination -or
    $normalizedDestination -notmatch '^[A-Za-z0-9._/-]+$' -or
    $segments -contains "." -or
    $segments -contains ".."
) {
    throw "RelativeDestination phải là đường dẫn tương đối an toàn trong vùng mô hình."
}
$source = (Resolve-Path -LiteralPath $SourceFile).Path
$staging = Join-Path ([IO.Path]::GetTempPath()) ("model-stage-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    Copy-Item -LiteralPath $source -Destination (Join-Path $staging "model-file")
    $destinationParent = Split-Path $normalizedDestination -Parent
    docker run --rm -v "${ProjectName}_model_data:/models" -v "${staging}:/staging:ro" alpine:3.21 sh -c "mkdir -p \"/models/$destinationParent\" && cp /staging/model-file \"/models/$normalizedDestination\""
    if ($LASTEXITCODE -ne 0) { throw "Cài đặt mô hình thất bại." }
    (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
} finally {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
