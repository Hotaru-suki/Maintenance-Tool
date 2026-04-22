param(
    [string[]]$Paths
)

$ErrorActionPreference = "Stop"

if (-not $Paths -or $Paths.Count -eq 0) {
    Write-Host "No signing targets supplied."
    exit 0
}

$CertPath = $env:WINDOWS_CODESIGN_CERT_PATH
$CertPassword = $env:WINDOWS_CODESIGN_CERT_PASSWORD
$TimestampUrl = if ([string]::IsNullOrWhiteSpace($env:WINDOWS_CODESIGN_TIMESTAMP_URL)) {
    "http://timestamp.digicert.com"
}
else {
    $env:WINDOWS_CODESIGN_TIMESTAMP_URL
}

if ([string]::IsNullOrWhiteSpace($CertPath) -or [string]::IsNullOrWhiteSpace($CertPassword)) {
    Write-Host "Code signing skipped: WINDOWS_CODESIGN_CERT_PATH or WINDOWS_CODESIGN_CERT_PASSWORD not set."
    exit 0
}

$SignTool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if ($null -eq $SignTool) {
    Write-Warning "signtool.exe not found. Code signing skipped."
    exit 0
}

foreach ($Path in $Paths) {
    if (-not (Test-Path $Path)) {
        throw "Signing target not found: $Path"
    }
    & $SignTool.Source sign /f $CertPath /p $CertPassword /tr $TimestampUrl /td sha256 /fd sha256 $Path
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed for $Path with exit code $LASTEXITCODE"
    }
}
