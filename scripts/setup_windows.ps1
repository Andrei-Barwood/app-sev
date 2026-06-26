#Requires -Version 5.1
<#
.SYNOPSIS
    Preconfigura Windows para ejecutar App SEV (binario standalone).

.DESCRIPTION
    Comprueba e instala automáticamente:
      - .NET Framework 4.8 (o superior)
      - Microsoft Edge WebView2 Runtime

    Ejecutar como Administrador ANTES de abrir AppSEV.exe.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipElevation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DotNetMinRelease = 528040   # .NET Framework 4.8
$DotNetInstallerUrl = 'https://go.microsoft.com/fwlink/?LinkId=2088631'
$WebView2InstallerUrl = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "    $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "    $Message" -ForegroundColor Yellow
}

function Test-IsAdministrator {
    $current = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Request-AdministratorElevation {
    if ($SkipElevation -or (Test-IsAdministrator)) {
        return
    }

    Write-Step 'Se requieren permisos de administrador. Solicitando elevación...'
    $scriptPath = $MyInvocation.MyCommand.Path
    $args = '-ExecutionPolicy Bypass -NoProfile -File "' + $scriptPath + '" -SkipElevation'
    Start-Process -FilePath 'powershell.exe' -ArgumentList $args -Verb RunAs
    exit 0
}

function Get-DotNetFrameworkRelease {
    $key = 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
    if (-not (Test-Path $key)) {
        return $null
    }
    return (Get-ItemProperty -Path $key -Name Release -ErrorAction SilentlyContinue).Release
}

function Test-DotNetFrameworkReady {
    $release = Get-DotNetFrameworkRelease
    return ($null -ne $release -and $release -ge $DotNetMinRelease)
}

function Test-WebView2RuntimeInstalled {
    $candidatePaths = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\EdgeWebView\Application'),
        (Join-Path $env:ProgramFiles 'Microsoft\EdgeWebView\Application')
    )

    foreach ($path in $candidatePaths) {
        if (Test-Path $path) {
            return $true
        }
    }

    $regPaths = @(
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
        'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    )

    foreach ($regPath in $regPaths) {
        if (Test-Path $regPath) {
            $version = (Get-ItemProperty -Path $regPath -Name 'pv' -ErrorAction SilentlyContinue).pv
            if ($version) {
                return $true
            }
        }
    }

    return $false
}

function Invoke-QuietInstaller {
    param(
        [Parameter(Mandatory = $true)][string]$InstallerPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Label
    )

    Write-Step "Instalando $Label..."
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -Wait -PassThru -NoNewWindow

    if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
        if ($process.ExitCode -eq 3010) {
            Write-Warn "$Label instalado. Puede ser necesario reiniciar Windows."
        } else {
            Write-Ok "$Label instalado correctamente."
        }
        return
    }

    throw "La instalación de $Label finalizó con código $($process.ExitCode)."
}

function Install-WithWinget {
    param(
        [Parameter(Mandatory = $true)][string]$PackageId,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        return $false
    }

    Write-Step "Intentando instalar $Label con winget..."
    $wingetArgs = @(
        'install', '--id', $PackageId,
        '-e', '--accept-source-agreements', '--accept-package-agreements',
        '--disable-interactivity'
    )

    $process = Start-Process -FilePath 'winget' -ArgumentList $wingetArgs -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -eq 0 -or $process.ExitCode -eq -1978335189) {
        Write-Ok "$Label disponible (winget)."
        return $true
    }

    Write-Warn "winget no pudo instalar $Label (código $($process.ExitCode)). Se usará el instalador directo."
    return $false
}

function Install-DotNetFramework {
    if (Test-DotNetFrameworkReady) {
        $release = Get-DotNetFrameworkRelease
        Write-Ok ".NET Framework 4.8+ ya está instalado (Release: $release)."
        return
    }

    $tempDir = Join-Path $env:TEMP 'app-sev-setup'
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    $installer = Join-Path $tempDir 'ndp48-web.exe'

    Write-Step 'Descargando instalador de .NET Framework 4.8...'
    Invoke-WebRequest -Uri $DotNetInstallerUrl -OutFile $installer -UseBasicParsing
    Invoke-QuietInstaller -InstallerPath $installer -Arguments @('/q', '/norestart') -Label '.NET Framework 4.8'

    if (-not (Test-DotNetFrameworkReady)) {
        throw 'No se pudo verificar .NET Framework 4.8 tras la instalación.'
    }
}

function Install-WebView2Runtime {
    if (Test-WebView2RuntimeInstalled) {
        Write-Ok 'Microsoft Edge WebView2 Runtime ya está instalado.'
        return
    }

    if (Install-WithWinget -PackageId 'Microsoft.EdgeWebView2Runtime' -Label 'WebView2 Runtime') {
        Start-Sleep -Seconds 2
        if (Test-WebView2RuntimeInstalled) {
            return
        }
    }

    $tempDir = Join-Path $env:TEMP 'app-sev-setup'
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    $installer = Join-Path $tempDir 'MicrosoftEdgeWebview2Setup.exe'

    Write-Step 'Descargando instalador de WebView2 Runtime...'
    Invoke-WebRequest -Uri $WebView2InstallerUrl -OutFile $installer -UseBasicParsing
    Invoke-QuietInstaller -InstallerPath $installer -Arguments @('/silent', '/install') -Label 'WebView2 Runtime'

    if (-not (Test-WebView2RuntimeInstalled)) {
        throw 'No se pudo verificar WebView2 Runtime tras la instalación.'
    }
}

function Show-Summary {
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Green
    Write-Host ' Windows listo para ejecutar App SEV' -ForegroundColor Green
    Write-Host '========================================' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Siguiente paso:'
    Write-Host '  1. Descomprime app-sev-windows.zip (si aún no lo hiciste).'
    Write-Host '  2. Ejecuta AppSEV.exe desde la carpeta descomprimida.'
    Write-Host ''
}

try {
    if ($env:OS -notlike '*Windows*') {
        throw 'Este script solo puede ejecutarse en Windows.'
    }

    Request-AdministratorElevation

    Write-Host ''
    Write-Host 'App SEV — Preconfiguración de Windows' -ForegroundColor White
    Write-Host '--------------------------------------' -ForegroundColor DarkGray
    Write-Host ''

    Install-DotNetFramework
    Install-WebView2Runtime
    Show-Summary
    exit 0
}
catch {
    Write-Host ''
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    Write-Host 'Instalación manual:' -ForegroundColor Yellow
    Write-Host '  .NET Framework 4.8: https://dotnet.microsoft.com/download/dotnet-framework/net48'
    Write-Host '  WebView2 Runtime:   https://developer.microsoft.com/microsoft-edge/webview2'
    Write-Host ''
    exit 1
}