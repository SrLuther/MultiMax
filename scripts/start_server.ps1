param([int]$Port)
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
$repo = Split-Path -Parent $root

Write-Host "Iniciando MultiMax como servidor de rede..." -ForegroundColor Cyan

$bootstrap = Join-Path $repo 'scripts\bootstrap.ps1'
if (Test-Path $bootstrap) {
  $bootstrapOutput = powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap
  if ($bootstrapOutput -is [array]) { $python = $bootstrapOutput[-1] } else { $python = $bootstrapOutput }
} else {
  $venvPython = Join-Path $repo 'venv\Scripts\python.exe'
  if (Test-Path $venvPython) { $python = $venvPython } else { $python = 'python' }
}
if (-not (Test-Path $python) -and $python -ne 'python') { $python = 'python' }
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  function Start-RequirementsDialog {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Requisitos do MultiMax'
    $form.StartPosition = 'CenterScreen'
    $form.Size = New-Object System.Drawing.Size(560,380)
    $txt = New-Object System.Windows.Forms.Label
    $txt.Text = "Para iniciar o MultiMax, é necessário:\n\n• Python 3 instalado\n• Conectividade de rede local\n• Permitir criação de regra de firewall (quando solicitado)"
    $txt.Location = New-Object System.Drawing.Point(16,16)
    $txt.Size = New-Object System.Drawing.Size(520,80)
    $status = New-Object System.Windows.Forms.Label
    $status.Location = New-Object System.Drawing.Point(16,110)
    $status.Size = New-Object System.Drawing.Size(520,24)
    $hasPy = [bool](Get-Command py -ErrorAction SilentlyContinue) -or [bool](Get-Command python -ErrorAction SilentlyContinue)
    if ($hasPy) { $status.Text = 'Status: Python DETECTADO' } else { $status.Text = 'Status: Python NÃO DETECTADO' }
    $btnAuto = New-Object System.Windows.Forms.Button
    $btnAuto.Text = 'Instalar automaticamente'
    $btnAuto.Location = New-Object System.Drawing.Point(16,150)
    $btnAuto.Size = New-Object System.Drawing.Size(220,36)
    $btnManual = New-Object System.Windows.Forms.Button
    $btnManual.Text = 'Instalar manualmente'
    $btnManual.Location = New-Object System.Drawing.Point(252,150)
    $btnManual.Size = New-Object System.Drawing.Size(220,36)
    $btnContinuar = New-Object System.Windows.Forms.Button
    $btnContinuar.Text = 'Continuar'
    $btnContinuar.Location = New-Object System.Drawing.Point(16,210)
    $btnContinuar.Size = New-Object System.Drawing.Size(220,36)
    $btnCancelar = New-Object System.Windows.Forms.Button
    $btnCancelar.Text = 'Fechar'
    $btnCancelar.Location = New-Object System.Drawing.Point(252,210)
    $btnCancelar.Size = New-Object System.Drawing.Size(220,36)
    $btnContinuar.Enabled = $hasPy
    $btnAuto.Add_Click({
      $hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
      if (-not $hasWinget) { [System.Windows.Forms.MessageBox]::Show('Instalação automática indisponível nesta máquina. Use instalação manual.', 'Aviso', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning) | Out-Null; return }
      $ok = $false
      try { winget install --id Python.Python.3.12 --source winget --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch {}
      if ([bool](Get-Command py -ErrorAction SilentlyContinue) -or [bool](Get-Command python -ErrorAction SilentlyContinue)) { $ok = $true }
      if (-not $ok) {
        try { winget install --id Python.Python --source winget --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch {}
        if ([bool](Get-Command py -ErrorAction SilentlyContinue) -or [bool](Get-Command python -ErrorAction SilentlyContinue)) { $ok = $true }
      }
      if ($ok) { $status.Text = 'Status: Python INSTALADO'; $btnContinuar.Enabled = $true } else { [System.Windows.Forms.MessageBox]::Show('Falha ao instalar automaticamente. Use instalação manual.', 'Falha', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null }
    })
    $btnManual.Add_Click({ Start-Process 'https://www.python.org/downloads/windows/' | Out-Null })
    $btnContinuar.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() })
    $btnCancelar.Add_Click({ $form.DialogResult = [System.Windows.Forms.DialogResult]::Cancel; $form.Close() })
    $form.Controls.AddRange(@($txt,$status,$btnAuto,$btnManual,$btnContinuar,$btnCancelar))
    $dr = $form.ShowDialog()
    return ($dr -eq [System.Windows.Forms.DialogResult]::OK)
  }
  $okDialog = Start-RequirementsDialog
  if (-not $okDialog) { Exit 1 }
  if (Test-Path $bootstrap) {
    $bootstrapOutput = powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap
    if ($bootstrapOutput -is [array]) { $python = $bootstrapOutput[-1] } else { $python = $bootstrapOutput }
  }
}

$env:HOST = '0.0.0.0'
if ($Port) { $env:PORT = [string]$Port } elseif ([string]::IsNullOrWhiteSpace($env:PORT)) { $env:PORT = '5000' }
$env:DEBUG = 'false'

function New-FirewallRuleIfNeeded($name, $port) {
  try {
    $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if ($existing) { Write-Host "Regra de firewall já existe" -ForegroundColor DarkGreen; return }
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
      New-NetFirewallRule -DisplayName $name -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
      Write-Host ("Regra de firewall criada para porta {0}" -f $port) -ForegroundColor Green
    } else {
      Write-Host "Tentando criar regra com elevação (UAC)..." -ForegroundColor Yellow
      $cmd1 = "New-NetFirewallRule -DisplayName `"$name`" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow"
      Start-Process -FilePath (Get-Command powershell.exe).Source -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-Command",$cmd1 -Verb RunAs -Wait
      $after = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
      if (-not $after) {
        $cmd2 = "netsh advfirewall firewall add rule name=`"$name`" dir=in action=allow protocol=TCP localport=$port"
        Start-Process -FilePath (Get-Command powershell.exe).Source -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-Command",$cmd2 -Verb RunAs -Wait
      }
      $after = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
      if ($after) { Write-Host "Regra de firewall criada" -ForegroundColor Green } else { Write-Host "Sem permissão para criar regra. O servidor iniciará mesmo assim." -ForegroundColor Yellow }
    }
  } catch {
    Write-Host ("Falha ao criar regra de firewall: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
  }
}

$ruleName = "MultiMax Flask $env:PORT"
New-FirewallRuleIfNeeded -name $ruleName -port $env:PORT

Write-Host ("Usando Python: {0}" -f $python)
Write-Host ("Diretório: {0}" -f $repo)
Write-Host ("Escutando em 0.0.0.0:{0}" -f $env:PORT)

function Test-PortReady($port) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $ar = $c.BeginConnect('127.0.0.1', [int]$port, $null, $null)
    $ok = $ar.AsyncWaitHandle.WaitOne(200)
    if ($ok) { $c.EndConnect($ar); $c.Close(); return $true }
    $c.Close(); return $false
  } catch { return $false }
}

function Wait-ServerReady($port, $timeoutSec) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-PortReady $port) { return $true }
    Start-Sleep -Milliseconds 200
  }
  return $false
}

Set-Location $repo
$proc = Start-Process -FilePath $python -ArgumentList "$repo\app.py" -WorkingDirectory $repo -PassThru -NoNewWindow
if (Wait-ServerReady $env:PORT 30) {
  try {
    $ipv4s = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.ToString() -ne '127.0.0.1' }
    $local = if ($ipv4s -and $ipv4s.Length -gt 0) { $ipv4s[0].ToString() } else { '127.0.0.1' }
    Write-Host ("Servidor pronto: http://127.0.0.1:{0}" -f $env:PORT) -ForegroundColor Green
    Write-Host ("Servidor pronto: http://{0}:{1}" -f $local, $env:PORT) -ForegroundColor Green
  } catch {
    Write-Host ("Servidor pronto: http://127.0.0.1:{0}" -f $env:PORT) -ForegroundColor Green
  }
} else {
  Write-Host "Aguardando servidor iniciar..." -ForegroundColor Yellow
}
if ($proc -and -not $proc.HasExited) {
  try { Wait-Process -Id $proc.Id -ErrorAction SilentlyContinue } catch {}
} else {
  try {
    if ($proc) { Write-Host ("Servidor finalizado (ExitCode {0})" -f $proc.ExitCode) -ForegroundColor Yellow }
    else { Write-Host "Servidor finalizado" -ForegroundColor Yellow }
  } catch { Write-Host "Servidor finalizado" -ForegroundColor Yellow }
}
