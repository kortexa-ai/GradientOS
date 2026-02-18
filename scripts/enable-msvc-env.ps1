[CmdletBinding()]
param(
    [ValidateSet("x64", "x86")]
    [string]$Arch = "x64",

    [ValidateSet("x64", "x86")]
    [string]$HostArch = "x64"
)

$ErrorActionPreference = "Stop"

function Get-VsWherePath {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
        "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Import-VsDevCmdEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$VsDevCmdPath,
        [Parameter(Mandatory = $true)]
        [string]$ArchValue,
        [Parameter(Mandatory = $true)]
        [string]$HostArchValue
    )

    $cmdLine = "`"$VsDevCmdPath`" -no_logo -arch=$ArchValue -host_arch=$HostArchValue && set"
    $envDump = & cmd.exe /s /c $cmdLine

    foreach ($line in $envDump) {
        if ($line -notmatch "=") {
            continue
        }

        $name, $value = $line -split "=", 2
        if ([string]::IsNullOrWhiteSpace($name)) {
            continue
        }
        Set-Item -Path "Env:$name" -Value $value
    }
}

$vsWhere = Get-VsWherePath
if (-not $vsWhere) {
    throw "vswhere.exe not found. Install Visual Studio Build Tools first."
}

$installPath = & $vsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ([string]::IsNullOrWhiteSpace($installPath)) {
    throw "No Visual Studio installation with C++ tools found."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
if (-not (Test-Path -LiteralPath $vsDevCmd)) {
    throw "VsDevCmd.bat not found at '$vsDevCmd'."
}

Import-VsDevCmdEnvironment -VsDevCmdPath $vsDevCmd -ArchValue $Arch -HostArchValue $HostArch

Write-Host "Loaded MSVC environment from '$installPath' (arch=$Arch host=$HostArch)."
Write-Host "cl:    $((Get-Command cl -ErrorAction SilentlyContinue).Source)"
Write-Host "nmake: $((Get-Command nmake -ErrorAction SilentlyContinue).Source)"
