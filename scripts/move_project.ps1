# stop python processes
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }

$src = 'C:\Users\Ciano\Documents\trae_projects\MM\MultiMax'
$dst = 'C:\Users\Ciano\Documents\MultiMax-DEV'

New-Item -ItemType Directory -Path $dst -Force | Out-Null
Write-Output "Copying from $src to $dst"
robocopy $src $dst /MIR /COPY:DAT /XJ /R:3 /W:5
$rc = $LASTEXITCODE
Write-Output "Robocopy exit code: $rc"
if ($rc -lt 8) {
    Write-Output "Copy succeeded"
    # ensure not inside source
    Set-Location 'C:\Users\Ciano\Documents\trae_projects\MM'
    Remove-Item -LiteralPath 'MultiMax' -Recurse -Force
    Write-Output "Source removed"
    exit 0
} else {
    Write-Error "Robocopy failed with code $rc"
    exit $rc
}
