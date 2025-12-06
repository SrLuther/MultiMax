$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
$repo = Split-Path -Parent $root
$venvPy = Join-Path $repo 'venv\Scripts\python.exe'
function Open-Url($url) { Start-Process $url | Out-Null }

function Initialize-PythonVenv {
  if (Test-Path $venvPy) { return $true }
  $pyCmd = $null
  if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = 'py -3' }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyCmd = 'python' }
  if (-not $pyCmd) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      try { winget install --id Python.Python.3.12 --source winget --silent --accept-package-agreements --accept-source-agreements } catch {}
      if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        try { winget install --id Python.Python --source winget --silent --accept-package-agreements --accept-source-agreements } catch {}
      }
      if (Get-Command py -ErrorAction SilentlyContinue) { $pyCmd = 'py -3' }
      elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyCmd = 'python' }
  } else {
      Write-Host 'Python não detectado e winget indisponível.' -ForegroundColor Yellow
      return $false
    }
  }
  if (-not $pyCmd) { return $false }
  Push-Location $repo
  Invoke-Expression "$pyCmd -m venv venv"
  Pop-Location
  return (Test-Path $venvPy)
}

function Install-PythonRequirements {
  if (-not (Test-Path $venvPy)) { return }
  & $venvPy -m pip install --upgrade pip -q --disable-pip-version-check | Out-Null
  & $venvPy -m pip install -r (Join-Path $repo 'requirements.txt') -q | Out-Null
}

if (-not (Initialize-PythonVenv)) { Exit 1 }

Install-PythonRequirements
Write-Output $venvPy
