$host.UI.RawUI.WindowTitle = 'MultiMax - deploy produção'
Write-Host 'Iniciando deploy de produção do MultiMax...' -ForegroundColor Green
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $root '.env.txt'
if (Test-Path $envFile) {
  Write-Host ('Carregando variáveis de: {0}' -f $envFile) -ForegroundColor DarkGray
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') {
      $k = $Matches[1]
      $v = $Matches[2]
      if ($v -match '^\s*"(.*)"\s*$') { $v = $Matches[1] }
      Set-Item -Path "Env:$k" -Value $v
    }
  }
}

# Configurações padrão de produção
Set-Item -Path Env:DEBUG -Value 'false'
Set-Item -Path Env:DB_BACKUP_ENABLED -Value 'true'
Set-Item -Path Env:APP_VERSION -Value 'v1.3.4'

$activate = Join-Path $root '.venv\\Scripts\\Activate.ps1'
if (Test-Path $activate) { & $activate }
Set-Location $root
$pyVenv = Join-Path $root '.venv\Scripts\python.exe'
$python = if (Test-Path $pyVenv) { $pyVenv } else { 'python' }
Write-Host ('Usando Python: {0}' -f $python) -ForegroundColor DarkGray
$port = [Environment]::GetEnvironmentVariable('PORT')
if (-not $port -or $port -eq '') { $port = '5000' }
Write-Host ('Servidor (produção) em http://localhost:{0}' -f $port) -ForegroundColor Yellow
& $python 'app.py'
