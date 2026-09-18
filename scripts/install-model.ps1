param(
    [Parameter(Mandatory = $true)][string]$SourceFile,
    [Parameter(Mandatory = $true)][string]$RelativeDestination,
    [string]$ProjectName = "elec_man"
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $SourceFile).Path
$staging = Join-Path ([IO.Path]::GetTempPath()) ("model-stage-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    Copy-Item -LiteralPath $source -Destination (Join-Path $staging "model-file")
    docker run --rm -v "${ProjectName}_model_data:/models" -v "${staging}:/staging:ro" alpine:3.21 sh -c "mkdir -p \"/models/$(Split-Path $RelativeDestination -Parent)\" && cp /staging/model-file \"/models/$RelativeDestination\""
    if ($LASTEXITCODE -ne 0) { throw "Model installation failed." }
    (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
} finally {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
