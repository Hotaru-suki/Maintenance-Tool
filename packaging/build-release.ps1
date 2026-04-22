param(
    [string]$PythonExe = "python",
    [string]$Version = "",
    [string]$PlatformTag = "win-x64"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$SpecPath = Join-Path $ProjectRoot "packaging\pyinstaller\MaintenanceTool.spec"
$InstallerScriptPath = Join-Path $ProjectRoot "packaging\installer\MaintenanceTool.iss"
$SignScriptPath = Join-Path $ProjectRoot "packaging\sign-release.ps1"
$WingetManifestScriptPath = Join-Path $ProjectRoot "scripts\packaging\generate_winget_manifest.py"
$TemplateDir = Join-Path $ProjectRoot "packaging\config_templates"
$LauncherDir = Join-Path $ProjectRoot "launcher"
$DistAppRoot = Join-Path $DistRoot "MaintenanceTool"
$VersionTag = "v$Version"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $PyprojectPath = Join-Path $ProjectRoot "pyproject.toml"
    $PyprojectText = Get-Content -Path $PyprojectPath -Raw -Encoding UTF8
    $VersionMatch = [regex]::Match($PyprojectText, '(?m)^version = "([^"]+)"')
    if (-not $VersionMatch.Success) {
        throw "Could not determine version from $PyprojectPath"
    }
    $Version = $VersionMatch.Groups[1].Value
}

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
    & $SignScriptPath -Paths @((Join-Path $DistAppRoot "MaintenanceTool.exe"))
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime executable signing failed with exit code $LASTEXITCODE"
    }
}

$ReleaseName = "MaintenanceTool-$VersionTag-$PlatformTag"
$ReleaseRoot = Join-Path $DistRoot $ReleaseName
if (Test-Path $ReleaseRoot) {
    Remove-Item -Recurse -Force $ReleaseRoot
}

New-Item -ItemType Directory -Path $ReleaseRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $DistAppRoot "*") $ReleaseRoot
Copy-Item -Recurse -Force $TemplateDir (Join-Path $ReleaseRoot "config_templates")
Copy-Item -Force (Join-Path $LauncherDir "mtool.cmd") (Join-Path $ReleaseRoot "mtool.cmd")
Copy-Item -Force (Join-Path $LauncherDir "mtool.ps1") (Join-Path $ReleaseRoot "mtool.ps1")
Copy-Item -Force (Join-Path $LauncherDir "MaintenanceTool.bat") (Join-Path $ReleaseRoot "MaintenanceTool.bat")
Copy-Item -Force (Join-Path $LauncherDir "MaintenanceTool.ps1") (Join-Path $ReleaseRoot "MaintenanceTool.ps1")
Copy-Item -Force (Join-Path $ProjectRoot "README.md") (Join-Path $ReleaseRoot "README.md")
Copy-Item -Force (Join-Path $ProjectRoot "README.zh-CN.md") (Join-Path $ReleaseRoot "README.zh-CN.md")

$InstallerPath = $null
$WingetManifestPath = $null
if (Test-Path $InstallerScriptPath) {
    $IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($null -ne $IsccCommand) {
        Push-Location $ProjectRoot
        try {
            & $IsccCommand.Source "/DAppVersion=$Version" $InstallerScriptPath
            if ($LASTEXITCODE -ne 0) {
                throw "Inno Setup compilation failed with exit code $LASTEXITCODE"
            }
            $InstallerPath = Join-Path $DistRoot "MaintenanceTool-$VersionTag-$PlatformTag-setup.exe"
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
                $WingetManifestPath = Join-Path $DistRoot "MaintenanceTool-$VersionTag-$PlatformTag-winget.yaml"
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
