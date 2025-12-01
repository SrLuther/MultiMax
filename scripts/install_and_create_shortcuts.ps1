$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
$repo = Split-Path -Parent $root

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Test-Python {
  $venvPy = Join-Path $repo 'venv\Scripts\python.exe'
  if (Test-Path $venvPy) { return $true }
  if (Get-Command py -ErrorAction SilentlyContinue) { return $true }
  if (Get-Command python -ErrorAction SilentlyContinue) { return $true }
  return $false
}

function Install-Python-Auto {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $false }
  $ok = $false
  try { winget install --id Python.Python.3.12 --source winget --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch {}
  if (Test-Python) { $ok = $true }
  if (-not $ok) {
    try { winget install --id Python.Python --source winget --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch {}
  }
  return (Test-Python)
}

function Show-InstallerDialog {
  $form = New-Object System.Windows.Forms.Form
  $form.Text = 'Instalar requisitos e gerar atalhos'
  $form.StartPosition = 'CenterScreen'
  $form.Size = New-Object System.Drawing.Size(600,360)

  $lbl = New-Object System.Windows.Forms.Label
  $lbl.Text = "Para usar o MultiMax, é necessário:\n\n• Python 3 instalado\n• Conectividade de rede local\n• Permitir criação de regra de firewall quando solicitado\n\nEm seguida, serão criados os atalhos na Área de Trabalho."
  $lbl.Location = New-Object System.Drawing.Point(16,16)
  $lbl.Size = New-Object System.Drawing.Size(560,120)

  $status = New-Object System.Windows.Forms.Label
  $status.Location = New-Object System.Drawing.Point(16,140)
  $status.Size = New-Object System.Drawing.Size(560,24)
  if (Test-Python) { $status.Text = 'Status: Python DETECTADO' } else { $status.Text = 'Status: Python NÃO DETECTADO' }

  $btnAuto = New-Object System.Windows.Forms.Button
  $btnAuto.Text = 'Instalar Python automaticamente'
  $btnAuto.Location = New-Object System.Drawing.Point(16,180)
  $btnAuto.Size = New-Object System.Drawing.Size(260,36)

  $btnManual = New-Object System.Windows.Forms.Button
  $btnManual.Text = 'Instalar Python manualmente'
  $btnManual.Location = New-Object System.Drawing.Point(300,180)
  $btnManual.Size = New-Object System.Drawing.Size(260,36)

  $btnGenerate = New-Object System.Windows.Forms.Button
  $btnGenerate.Text = 'Gerar atalhos na Área de Trabalho'
  $btnGenerate.Location = New-Object System.Drawing.Point(16,236)
  $btnGenerate.Size = New-Object System.Drawing.Size(544,36)
  $btnGenerate.Enabled = (Test-Python)

  $btnClose = New-Object System.Windows.Forms.Button
  $btnClose.Text = 'Fechar'
  $btnClose.Location = New-Object System.Drawing.Point(16,292)
  $btnClose.Size = New-Object System.Drawing.Size(120,30)

  $btnAuto.Add_Click({
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
      [System.Windows.Forms.MessageBox]::Show('Instalação automática indisponível nesta máquina. Use instalação manual.', 'Aviso', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning) | Out-Null
      return
    }
    $ok = Install-Python-Auto
    if ($ok) { $status.Text = 'Status: Python INSTALADO'; $btnGenerate.Enabled = $true } else { [System.Windows.Forms.MessageBox]::Show('Falha ao instalar automaticamente. Use instalação manual.', 'Falha', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null }
  })

  $btnManual.Add_Click({ Start-Process 'https://www.python.org/downloads/windows/' | Out-Null })

  $btnGenerate.Add_Click({
    try {
      powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'scripts\create_desktop_shortcut.ps1')
      [System.Windows.Forms.MessageBox]::Show('Atalhos criados na Área de Trabalho.', 'Concluído', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    } catch {
      [System.Windows.Forms.MessageBox]::Show('Falha ao gerar atalhos.', 'Erro', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
    }
  })

  $btnClose.Add_Click({ $form.Close() })

  $form.Controls.AddRange(@($lbl,$status,$btnAuto,$btnManual,$btnGenerate,$btnClose))
  [void]$form.ShowDialog()
}

Show-InstallerDialog
