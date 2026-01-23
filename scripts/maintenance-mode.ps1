# Script para ativar/desativar modo de manutenção do MultiMax
# Uso: .\maintenance-mode.ps1 [on|off|status]

param(
    [Parameter(Position=0)]
    [ValidateSet('on', 'off', 'status', 'enable', 'disable', 'ativar', 'desativar', 'check')]
    [string]$Action
)

$ErrorActionPreference = "Stop"

$EnvFile = ".env.txt"
$EnvFileAlt = ".env"

# Determina qual arquivo .env usar
if (Test-Path $EnvFile) {
    $TargetFile = $EnvFile
} elseif (Test-Path $EnvFileAlt) {
    $TargetFile = $EnvFileAlt
} else {
    Write-Host "❌ Nenhum arquivo .env encontrado (.env.txt ou .env)" -ForegroundColor Red
    Write-Host "💡 Criando $EnvFile..." -ForegroundColor Yellow
    New-Item -Path $EnvFile -ItemType File -Force | Out-Null
    $TargetFile = $EnvFile
}

# Função para obter status atual
function Get-MaintenanceStatus {
    if (Test-Path $TargetFile) {
        $content = Get-Content $TargetFile -Raw -ErrorAction SilentlyContinue
        if ($content -match "^MAINTENANCE_MODE=true") {
            return "ON"
        } elseif ($content -match "^MAINTENANCE_MODE=false") {
            return "OFF"
        }
    }
    return "NOT_SET"
}

# Função para ativar modo de manutenção
function Enable-Maintenance {
    Write-Host "🔧 Ativando modo de manutenção..." -ForegroundColor Cyan

    # Le conteúdo atual
    if (Test-Path $TargetFile) {
        $lines = Get-Content $TargetFile | Where-Object { $_ -notmatch "^MAINTENANCE_MODE=" }
    } else {
        $lines = @()
    }

    # Adiciona nova configuração
    $lines += "MAINTENANCE_MODE=true"

    # Salva arquivo
    $lines | Set-Content $TargetFile -Encoding UTF8

    Write-Host "✅ Modo de manutenção ATIVADO em $TargetFile" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Próximos passos:" -ForegroundColor Yellow
    Write-Host "   1. Reinicie a aplicação:"
    Write-Host "      • python app.py"
    Write-Host "      • docker-compose restart (se usando Docker)"
    Write-Host ""
    Write-Host "   2. Verifique o status:"
    Write-Host "      curl -I https://multimax.tec.br"
    Write-Host "      (deve retornar HTTP 503)"
    Write-Host ""
    Write-Host "   3. Para desativar, execute:"
    Write-Host "      .\maintenance-mode.ps1 off"
}

# Função para desativar modo de manutenção
function Disable-Maintenance {
    Write-Host "🔓 Desativando modo de manutenção..." -ForegroundColor Cyan

    # Le conteúdo atual
    if (Test-Path $TargetFile) {
        $lines = Get-Content $TargetFile | Where-Object { $_ -notmatch "^MAINTENANCE_MODE=" }
    } else {
        $lines = @()
    }

    # Adiciona nova configuração
    $lines += "MAINTENANCE_MODE=false"

    # Salva arquivo
    $lines | Set-Content $TargetFile -Encoding UTF8

    Write-Host "✅ Modo de manutenção DESATIVADO em $TargetFile" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Próximos passos:" -ForegroundColor Yellow
    Write-Host "   1. Reinicie a aplicação:"
    Write-Host "      • python app.py"
    Write-Host "      • docker-compose restart (se usando Docker)"
    Write-Host ""
    Write-Host "   2. Verifique o acesso:"
    Write-Host "      https://multimax.tec.br"
}

# Função para mostrar status
function Show-Status {
    $status = Get-MaintenanceStatus

    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  STATUS DO MODO DE MANUTENÇÃO" -ForegroundColor White
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Arquivo: $TargetFile" -ForegroundColor Gray
    Write-Host ""

    switch ($status) {
        "ON" {
            Write-Host "🔧 Status: ATIVADO" -ForegroundColor Red
            Write-Host "⚠️  Sistema está em modo de manutenção" -ForegroundColor Yellow
            Write-Host "📄 Usuários veem: página estática institucional" -ForegroundColor Gray
            Write-Host "🚫 Acesso bloqueado: todas as rotas, APIs e banco de dados" -ForegroundColor Gray
        }
        "OFF" {
            Write-Host "✅ Status: DESATIVADO" -ForegroundColor Green
            Write-Host "🟢 Sistema está operacional" -ForegroundColor Green
            Write-Host "📄 Usuários veem: sistema completo" -ForegroundColor Gray
        }
        "NOT_SET" {
            Write-Host "⚪ Status: NÃO CONFIGURADO" -ForegroundColor Gray
            Write-Host "ℹ️  Variável MAINTENANCE_MODE não definida" -ForegroundColor Cyan
            Write-Host "📝 Sistema funciona normalmente (padrão: desativado)" -ForegroundColor Gray
        }
    }

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

# Menu principal
if (-not $Action) {
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Gerenciador de Modo de Manutenção" -ForegroundColor White
    Write-Host "  Sistema MultiMax" -ForegroundColor White
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso: .\maintenance-mode.ps1 [comando]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Comandos disponíveis:" -ForegroundColor White
    Write-Host "  on, enable, ativar       Ativa modo de manutenção" -ForegroundColor Gray
    Write-Host "  off, disable, desativar  Desativa modo de manutenção" -ForegroundColor Gray
    Write-Host "  status, check            Mostra status atual" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Exemplos:" -ForegroundColor White
    Write-Host "  .\maintenance-mode.ps1 on      # Ativar" -ForegroundColor Gray
    Write-Host "  .\maintenance-mode.ps1 off     # Desativar" -ForegroundColor Gray
    Write-Host "  .\maintenance-mode.ps1 status  # Ver status" -ForegroundColor Gray
    Write-Host ""
    Show-Status
    exit 0
}

switch ($Action) {
    { $_ -in 'on', 'enable', 'ativar' } {
        Enable-Maintenance
    }
    { $_ -in 'off', 'disable', 'desativar' } {
        Disable-Maintenance
    }
    { $_ -in 'status', 'check' } {
        Show-Status
    }
}
