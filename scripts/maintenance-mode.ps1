<#
Script para ativar/desativar modo de manutenção do MultiMax
Uso: .\maintenance-mode.ps1 [on|off|status]
#>

param(
    [Parameter(Position=0)]
    [ValidateSet('on','off','status','enable','disable','ativar','desativar','check')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

$EnvFile = '.env.txt'
$EnvFileAlt = '.env'

# Determina qual arquivo .env usar
if (Test-Path $EnvFile) {
    $TargetFile = $EnvFile
} elseif (Test-Path $EnvFileAlt) {
    $TargetFile = $EnvFileAlt
} else {
    Write-Host 'Nenhum arquivo .env encontrado (.env.txt ou .env)' -ForegroundColor Red
    Write-Host "Criando $EnvFile..." -ForegroundColor Yellow
    New-Item -Path $EnvFile -ItemType File -Force | Out-Null
    $TargetFile = $EnvFile
}

function Get-MaintenanceStatus {
    if (Test-Path $TargetFile) {
        $content = Get-Content $TargetFile -Raw -ErrorAction SilentlyContinue
        if ($content -match '^MAINTENANCE_MODE=true') { return 'ON' }
        if ($content -match '^MAINTENANCE_MODE=false') { return 'OFF' }
    }
    return 'NOT_SET'
}

function Enable-Maintenance {
    Write-Host 'Ativando modo de manutenção...' -ForegroundColor Cyan
    $lines = @()
    if (Test-Path $TargetFile) {
        $lines = Get-Content $TargetFile | Where-Object { $_ -notmatch '^MAINTENANCE_MODE=' }
    }
    $lines += 'MAINTENANCE_MODE=true'
    $lines | Set-Content $TargetFile -Encoding UTF8
    Write-Host "Modo de manutenção ATIVADO em $TargetFile" -ForegroundColor Green
}

function Disable-Maintenance {
    Write-Host 'Desativando modo de manutenção...' -ForegroundColor Cyan
    $lines = @()
    if (Test-Path $TargetFile) {
        $lines = Get-Content $TargetFile | Where-Object { $_ -notmatch '^MAINTENANCE_MODE=' }
    }
    $lines += 'MAINTENANCE_MODE=false'
    $lines | Set-Content $TargetFile -Encoding UTF8
    Write-Host "Modo de manutenção DESATIVADO em $TargetFile" -ForegroundColor Green
}

function Show-Status {
    $status = Get-MaintenanceStatus
    Write-Host "Arquivo: $TargetFile" -ForegroundColor Gray
    if ($status -eq 'ON') {
        Write-Host 'Status: ATIVADO (HTTP 503)' -ForegroundColor Yellow
    } elseif ($status -eq 'OFF') {
        Write-Host 'Status: DESATIVADO' -ForegroundColor Green
    } else {
        Write-Host 'Status: NÃO CONFIGURADO' -ForegroundColor DarkGray
    }
}

# Menu principal (quando sem parâmetro)
if (-not $Action) {
    Write-Host 'Uso: .\maintenance-mode.ps1 [on|off|status]' -ForegroundColor Yellow
    Write-Host 'Exemplos: .\maintenance-mode.ps1 on | off | status' -ForegroundColor Gray
    Show-Status
    exit 0
}

if ($Action -in @('on','enable','ativar')) {
    Enable-Maintenance
} elseif ($Action -in @('off','disable','desativar')) {
    Disable-Maintenance
} elseif ($Action -in @('status','check')) {
    Show-Status
} else {
    Write-Host "Comando inválido: $Action" -ForegroundColor Red
    exit 1
}
