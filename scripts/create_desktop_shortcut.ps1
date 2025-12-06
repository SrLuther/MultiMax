$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
$repo = Split-Path -Parent $root
$desktop = [Environment]::GetFolderPath('Desktop')

$pwsh7 = Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe'
if (Test-Path $pwsh7) { $target = $pwsh7 } else { $target = (Get-Command powershell.exe).Source }

function New-ServerShortcut([string]$name, [int]$port) {
  $path = Join-Path $desktop $name
  $shortcutArgs = "-NoExit -ExecutionPolicy Bypass -File `"$repo\scripts\start_server.ps1`" -Port $port"
  $ws = New-Object -ComObject WScript.Shell
  $sc = $ws.CreateShortcut($path)
  $sc.TargetPath = $target
  $sc.Arguments = $shortcutArgs
  $sc.WorkingDirectory = $repo
  $iconIco = Join-Path $repo 'static\icons\multimax.ico'
  if (Test-Path $iconIco) { $sc.IconLocation = $iconIco }
  $sc.Save()
  Write-Host "Atalho criado em: $path" -ForegroundColor Green
}

New-ServerShortcut 'MultiMax Server.lnk' 5000
New-ServerShortcut 'MultiMax Server (8080).lnk' 8080
New-ServerShortcut 'MultiMax Server (3000).lnk' 3000
