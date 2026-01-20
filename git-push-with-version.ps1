# Script PowerShell para fazer push com atualização automática de versão
# Uso: .\git-push-with-version.ps1 [branch] [patch|minor|major]

param(
    [string]$Branch = "nova-versao-deploy",
    [string]$BumpType = "patch"
)

Write-Host "Atualizando versao antes do push..." -ForegroundColor Cyan

# Executa o script de atualização de versão
python auto_version_update.py $BumpType

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Falha ao atualizar versao. Push cancelado." -ForegroundColor Red
    exit 1
}

# Adiciona arquivos de versão ao staging (ignora arquivos que não existem)
Write-Host "Adicionando arquivos de versao..." -ForegroundColor Yellow

$filesToAdd = @("CHANGELOG.md", "multimax/__init__.py", "LEIA-ME.txt", "VERSION_SYNC.md")
foreach ($file in $filesToAdd) {
    if (Test-Path $file) {
        git add $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK: $file adicionado" -ForegroundColor Green
        }
    } else {
        Write-Host "AVISO: $file nao encontrado, pulando..." -ForegroundColor Yellow
    }
}

# Verifica se há mudanças para commitar
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    # Não há mudanças, pula para push
    Write-Host "Nenhuma mudanca de versao detectada. Prosseguindo com push..." -ForegroundColor Yellow
} else {
    # Há mudanças, cria commit de versão
    $changelogContent = Get-Content CHANGELOG.md -Raw
    if ($changelogContent -match '## \[(\d+\.\d+\.\d+)\]') {
        $currentVersion = $matches[1]
        Write-Host "Criando commit de versao $currentVersion..." -ForegroundColor Yellow
        git commit -m "chore: Atualiza versao para $currentVersion" --no-verify

        # Cria tag se não existir
        $tagExists = git tag -l "v$currentVersion"
        if (-not $tagExists) {
            Write-Host "Criando tag v$currentVersion..." -ForegroundColor Yellow
            git tag -a "v$currentVersion" -m "Versao $currentVersion"
        }
    }
}

# Faz push do branch
Write-Host "Fazendo push para $Branch..." -ForegroundColor Cyan
git push origin $Branch

if ($LASTEXITCODE -eq 0) {
    # Faz push das tags
    Write-Host "Fazendo push das tags..." -ForegroundColor Cyan
    git push origin --tags

    Write-Host "Push concluido com sucesso!" -ForegroundColor Green
} else {
    Write-Host "ERRO: Erro ao fazer push." -ForegroundColor Red
    exit 1
}
