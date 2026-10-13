param(
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')][string]$ProjectName = "elec_man",
    [ValidatePattern('^\.env(\.[a-zA-Z0-9_-]+)?$')][string]$EnvFile = ".env",
    [ValidateRange(1, 65535)][int]$Port = 80,
    [string]$Username = "admin",
    [switch]$SkipBuild,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ($EnvFile -eq ".env.example") { throw "Không dùng .env.example làm cấu hình riêng." }
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker thất bại (mã $LASTEXITCODE). Xem hướng dẫn xử lý lỗi." }
}
Push-Location -LiteralPath $workspace
try {
    Invoke-Docker info --format '{{.ServerVersion}}'
    Invoke-Docker compose version
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        $containers = Invoke-Docker ps -aq --filter "label=com.docker.compose.project=$ProjectName"
        $volumes = Invoke-Docker volume ls -q --filter "label=com.docker.compose.project=$ProjectName"
        if ($containers -or $volumes) {
            throw "Dự án đã có dữ liệu nhưng thiếu $EnvFile. Khôi phục cấu hình gốc; không tạo secret mới."
        }
    }
    if (-not $SkipBuild) { Invoke-Docker build --tag elec_man-backend:latest backend }
    Invoke-Docker run --rm --network none --user 0 --mount "type=bind,source=$workspace,target=/workspace" --entrypoint python elec_man-backend:latest /workspace/scripts/bootstrap.py --env-file $EnvFile --port $Port
    $compose = @("compose", "--project-name", $ProjectName, "--env-file", $EnvFile)
    Invoke-Docker @compose config --quiet
    if (-not $SkipBuild) { Invoke-Docker @compose build }
    # Recreate the one-shot migration so repeat starts also apply pending migrations.
    Invoke-Docker @compose up -d --wait --wait-timeout 120 postgres
    Invoke-Docker @compose run --rm --no-deps migrate
    Invoke-Docker @compose up -d --wait --wait-timeout 300
    & docker @compose exec -T backend python -m app.scripts.init_admin --check
    $adminStatus = $LASTEXITCODE
    if ($adminStatus -eq 1) {
        $previousPassword = $env:ADMIN_INITIAL_PASSWORD
        $pointer = [IntPtr]::Zero
        try {
            if (-not $env:ADMIN_INITIAL_PASSWORD) {
                if ($NonInteractive) { throw "Cần ADMIN_INITIAL_PASSWORD để tạo quản trị lần đầu." }
                $securePassword = Read-Host "Mật khẩu cho $Username (12-256 ký tự)" -AsSecureString
                $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
                $env:ADMIN_INITIAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
            }
            # Docker receives the value from the process environment, never argv.
            Invoke-Docker @compose exec -T -e ADMIN_INITIAL_PASSWORD backend python -m app.scripts.init_admin --username $Username
        } finally {
            $env:ADMIN_INITIAL_PASSWORD = $previousPassword
            if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        }
    } elseif ($adminStatus -ne 0) { throw "Không kiểm tra được tài khoản quản trị." }
    Write-Output "Hệ thống đã sẵn sàng. Mở FRONTEND_ORIGIN trong $EnvFile (mặc định http://localhost/)."
    Write-Output "Dừng: docker compose --project-name $ProjectName --env-file $EnvFile stop"
} finally { Pop-Location }
