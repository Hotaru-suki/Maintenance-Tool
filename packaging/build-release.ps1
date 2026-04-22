param(
    [string]$PythonExe = "python",
    [string]$Version = "",
    [string]$PlatformTag = "win-x64"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$SpecPath = Join-Path $ProjectRoot "packaging\pyinstaller\MyTool.spec"
$InstallerScriptPath = Join-Path $ProjectRoot "packaging\installer\MyTool.iss"
$SignScriptPath = Join-Path $ProjectRoot "packaging\sign-release.ps1"
$WingetManifestScriptPath = Join-Path $ProjectRoot "scripts\packaging\generate_winget_manifest.py"
$BrandingScriptPath = Join-Path $ProjectRoot "scripts\packaging\export_branding.py"
$TemplateDir = Join-Path $ProjectRoot "packaging\config_templates"
$LauncherDir = Join-Path $ProjectRoot "launcher"
$Branding = (& $PythonExe $BrandingScriptPath | ConvertFrom-Json)
$ProductName = [string]$Branding.product_name
$ProductExeName = [string]$Branding.product_exe_name
$ProductIconName = [string]$Branding.product_icon_name
$CliName = [string]$Branding.cli_name
$DistAppRoot = Join-Path $DistRoot $ProductName

if ([string]::IsNullOrWhiteSpace($Version)) {
    $PyprojectPath = Join-Path $ProjectRoot "pyproject.toml"
    $PyprojectText = Get-Content -Path $PyprojectPath -Raw -Encoding UTF8
    $VersionMatch = [regex]::Match($PyprojectText, '(?m)^version = "([^"]+)"')
    if (-not $VersionMatch.Success) {
        throw "Could not determine version from $PyprojectPath"
    }
    $Version = $VersionMatch.Groups[1].Value
}

$VersionTag = "v$Version"

Push-Location $ProjectRoot
try {
    Set-Location $ProjectRoot
    & $PythonExe -m PyInstaller --noconfirm --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $DistAppRoot)) {
    throw "Expected PyInstaller output directory not found: $DistAppRoot"
}

if (Test-Path $SignScriptPath) {
    & $SignScriptPath -Paths @((Join-Path $DistAppRoot $ProductExeName))
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime executable signing failed with exit code $LASTEXITCODE"
    }
}

$ReleaseName = "$ProductName-$VersionTag-$PlatformTag"
$ReleaseRoot = Join-Path $DistRoot $ReleaseName
if (Test-Path $ReleaseRoot) {
    Remove-Item -Recurse -Force $ReleaseRoot
}

New-Item -ItemType Directory -Path $ReleaseRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $DistAppRoot "*") $ReleaseRoot
Copy-Item -Recurse -Force $TemplateDir (Join-Path $ReleaseRoot "config_templates")
Copy-Item -Force (Join-Path $LauncherDir "$CliName.cmd") (Join-Path $ReleaseRoot "$CliName.cmd")
Copy-Item -Force (Join-Path $LauncherDir "$CliName.ps1") (Join-Path $ReleaseRoot "$CliName.ps1")
Copy-Item -Force (Join-Path $ProjectRoot "README.md") (Join-Path $ReleaseRoot "README.md")
Copy-Item -Force (Join-Path $ProjectRoot "README.zh-CN.md") (Join-Path $ReleaseRoot "README.zh-CN.md")

$InstallerPath = $null
$WingetManifestPath = $null
if (Test-Path $InstallerScriptPath) {
    $IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($null -ne $IsccCommand) {
        Push-Location $ProjectRoot
        try {
            & $IsccCommand.Source "/DAppVersion=$Version" "/DAppName=$ProductName" "/DAppExeName=$ProductExeName" "/DAppIconName=$ProductIconName" $InstallerScriptPath
            if ($LASTEXITCODE -ne 0) {
                throw "Inno Setup compilation failed with exit code $LASTEXITCODE"
            }
            $InstallerPath = Join-Path $DistRoot "$ProductName-$VersionTag-$PlatformTag-setup.exe"
            if (Test-Path $SignScriptPath) {
                & $SignScriptPath -Paths @($InstallerPath)
                if ($LASTEXITCODE -ne 0) {
                    throw "Installer signing failed with exit code $LASTEXITCODE"
                }
            }
            if (Test-Path $WingetManifestScriptPath) {
                $InstallerSha256 = (Get-FileHash -Path $InstallerPath -Algorithm SHA256).Hash
                $InstallerLeaf = Split-Path $InstallerPath -Leaf
                $InstallerUrl = "https://github.com/Hotaru-suki/Maintenance-Tool/releases/download/$VersionTag/$InstallerLeaf"
                $WingetManifestPath = Join-Path $DistRoot "$ProductName-$VersionTag-$PlatformTag-winget.yaml"
                & $PythonExe $WingetManifestScriptPath `
                    --version $Version `
                    --installer-url $InstallerUrl `
                    --installer-sha256 $InstallerSha256 `
                    --output-path $WingetManifestPath
                if ($LASTEXITCODE -ne 0) {
                    throw "winget manifest generation failed with exit code $LASTEXITCODE"
                }
                Copy-Item -Force $WingetManifestPath (Join-Path $ReleaseRoot (Split-Path $WingetManifestPath -Leaf))
            }
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Warning "ISCC.exe not found. setup.exe was not built; release zip is still available."
    }
}

$ZipPath = Join-Path $DistRoot "$ReleaseName.zip"
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}
Compress-Archive -Path (Join-Path $ReleaseRoot "*") -DestinationPath $ZipPath
Write-Host "release_dir=$ReleaseRoot"
Write-Host "release_zip=$ZipPath"
if ($null -ne $InstallerPath) {
    Write-Host "release_setup=$InstallerPath"
}
if ($null -ne $WingetManifestPath) {
    Write-Host "release_winget_manifest=$WingetManifestPath"
}
