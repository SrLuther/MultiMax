#!/usr/bin/env python3
"""
Hook de pre-commit para garantir disciplina total no CHANGELOG.md.

REGRAS APLICADAS:

1. Bloqueia o commit se arquivos de CÓDIGO forem alterados e o CHANGELOG.md
   não estiver incluído no stage.

2. EXIGE criação de NOVA versão sempre que houver mudança de código.
   - Versões já lançadas NUNCA podem ser editadas ou removidas.
   - Apenas [Unreleased] pode ser modificado.

3. Novas versões DEVEM ser adicionadas NO TOPO do changelog
   (logo abaixo de [Unreleased], caso exista).

4. Formato obrigatório de versão:
      X.Y.Z   (Semantic Versioning)

5. A partir da versão 3.2.0, TODAS as versões precisam conter data + hora:
      ## [X.Y.Z] - YYYY-MM-DD HH:MM:SS

6. A partir da versão 3.7.8, TODAS as versões
   DEVEM conter, IMEDIATAMENTE ACIMA de cada versão:

      ### IA responsável pelo envio
      - Nome da IA (ChatGPT, GitHub Copilot, Gemini, Grok, etc)
      - Modelo: <nome do modelo>

   Cada versão possui seu próprio registro.
   Blocos globais no topo NÃO são aceitos.

7. Commits apenas de documentação/configuração são liberados sem changelog.

Além disso:

- Caso o CHANGELOG.md ainda não exista no histórico (bootstrap inicial),
  o hook permite o primeiro commit sem exigir versões anteriores.

Filosofia do hook:
- Nunca reescrever histórico
- Sempre criar novas versões
- Preservar ordem cronológica
- Responsabilizar automações
"""

import re
import subprocess
import sys
from pathlib import Path

SEMVER_PATTERN = r"\d+\.\d+\.\d+"
VERSAO_EXIGE_IA = "3.7.8"
VERSAO_EXIGE_HORA = "3.2.0"


# ---------------------------------------------------------------------
# Utilitários básicos
# ---------------------------------------------------------------------


def run(cmd):
    """Executa comando e retorna o resultado."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def semver_tuple(version):
    """Converte X.Y.Z em tupla comparável."""
    return tuple(map(int, version.split(".")))


def versao_maior_ou_igual(a, b):
    """Retorna True se versão A >= versão B."""
    return semver_tuple(a) >= semver_tuple(b)


# ---------------------------------------------------------------------
# Funções Git
# ---------------------------------------------------------------------


def get_staged_files():
    """Obtém lista de arquivos em stage."""
    r = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return {f for f in r.stdout.splitlines() if f.strip()}


def get_versoes_head():
    """
    Extrai versões do CHANGELOG já commitado (HEAD).

    Se o arquivo ainda não existir (bootstrap inicial),
    retorna lista vazia sem erro.
    """
    r = run(["git", "show", "HEAD:CHANGELOG.md"])

    if r.returncode != 0:
        return []

    return re.findall(r"^## \[([^\]]+)\]", r.stdout, re.MULTILINE)


def get_changelog_staged():
    """Obtém conteúdo do CHANGELOG.md em stage."""
    r = run(["git", "show", ":CHANGELOG.md"])
    if r.returncode != 0:
        return ""
    return r.stdout


# ---------------------------------------------------------------------
# Classificação de arquivos
# ---------------------------------------------------------------------


def is_documentacao_apenas(staged_files):
    """
    Verifica se o commit contém apenas documentação/configuração.

    Qualquer arquivo com extensão de código exige changelog.
    """
    extensoes_codigo = {".py", ".html", ".js", ".css", ".sql", ".json"}

    for file in staged_files:
        if Path(file).suffix in extensoes_codigo:
            return False

    return True


# ---------------------------------------------------------------------
# Parsing do CHANGELOG
# ---------------------------------------------------------------------


def extrair_versoes(texto):
    """Retorna lista ordenada de versões encontradas."""
    return re.findall(r"^## \[([^\]]+)\]", texto, re.MULTILINE)


def validar_datas(texto):
    """
    Valida presença de hora (HH:MM:SS) em versões >= 3.2.0.
    """
    problemas = []

    for m in re.finditer(rf"^## \[({SEMVER_PATTERN})\] - (.+)$", texto, re.MULTILINE):
        versao, data = m.group(1), m.group(2)

        if versao_maior_ou_igual(versao, VERSAO_EXIGE_HORA):
            if not re.match(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", data):
                problemas.append(versao)

    return problemas


def bloco_acima_da_versao(texto, versao, linhas=6):
    """
    Retorna o bloco imediatamente acima da versão informada.
    Usado para validar metadados de IA.
    """
    lista = texto.splitlines()

    for i, linha in enumerate(lista):
        if linha.startswith(f"## [{versao}]"):
            inicio = max(0, i - linhas)
            return "\n".join(lista[inicio:i])

    return ""


def validar_bloco_ia(bloco):
    """Confirma presença de IA responsável + modelo."""
    tem_ia = re.search(r"IA responsável pelo envio", bloco, re.IGNORECASE)
    tem_modelo = re.search(r"Modelo:\s*\S+", bloco, re.IGNORECASE)
    return bool(tem_ia and tem_modelo)


# ---------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------


def main():  # noqa: C901
    staged_files = get_staged_files()

    # Nada em stage
    if not staged_files:
        return 0

    # Apenas documentação/configuração
    if is_documentacao_apenas(staged_files):
        return 0

    # Código mudou mas changelog não
    if "CHANGELOG.md" not in staged_files:
        print("\n[ERRO] Código modificado sem atualização do CHANGELOG.md\n")
        return 1

    changelog_staged = get_changelog_staged()
    if not changelog_staged:
        print("\n[ERRO] Não foi possível ler CHANGELOG.md staged\n")
        return 1

    versoes_head = get_versoes_head()
    versoes_staged = extrair_versoes(changelog_staged)

    # Bootstrap: CHANGELOG não existia antes
    bootstrap = not versoes_head

    # --------------------------------------------------------------
    # Validar formato das versões
    # --------------------------------------------------------------

    for v in versoes_staged:
        if v != "Unreleased" and not re.match(rf"^{SEMVER_PATTERN}$", v):
            print(f"\n[ERRO] Versão inválida encontrada: {v}\n")
            return 1

    # --------------------------------------------------------------
    # Impedir alteração de versões já lançadas
    # --------------------------------------------------------------

    if not bootstrap:
        removidas = set(versoes_head) - set(versoes_staged)
        removidas = {v for v in removidas if re.match(rf"^{SEMVER_PATTERN}$", v)}

        if removidas:
            print("\n[ERRO] Versões já lançadas foram removidas ou alteradas:")
            for v in removidas:
                print(f" - {v}")
            return 1

    # --------------------------------------------------------------
    # Exigir nova versão (exceto bootstrap)
    # --------------------------------------------------------------

    novas = [v for v in versoes_staged if v not in versoes_head and v != "Unreleased"]

    if not novas and not bootstrap:
        print("\n[ERRO] Nenhuma nova versão foi criada no CHANGELOG\n")
        return 1

    # --------------------------------------------------------------
    # Nova versão deve estar no topo
    # --------------------------------------------------------------

    if not bootstrap:
        primeira_real = None
        for v in versoes_staged:
            if v != "Unreleased":
                primeira_real = v
                break

        if primeira_real not in novas:
            print("\n[ERRO] Nova versão deve estar no TOPO do CHANGELOG\n")
            return 1

    # --------------------------------------------------------------
    # Validar data com hora (>= 3.2.0)
    # --------------------------------------------------------------

    datas_invalidas = validar_datas(changelog_staged)
    if datas_invalidas:
        print("\n[ERRO] Versões >= 3.2.0 exigem data com hora:")
        for v in datas_invalidas:
            print(f" - {v}")
        print("\nFormato: ## [X.Y.Z] - YYYY-MM-DD HH:MM:SS\n")
        return 1

    # --------------------------------------------------------------
    # Validar bloco de IA PARA CADA versão >= 3.7.8
    # --------------------------------------------------------------

    for versao in versoes_staged:

        if versao == "Unreleased":
            continue

        if not versao_maior_ou_igual(versao, VERSAO_EXIGE_IA):
            continue

        bloco = bloco_acima_da_versao(changelog_staged, versao)

        if not validar_bloco_ia(bloco):
            print(f"\n[ERRO] A versão {versao} não possui bloco de IA imediatamente acima:\n")
            print("### IA responsável pelo envio")
            print("- Nome da IA (ChatGPT, Copilot, Gemini, Grok...)")
            print("- Modelo: <modelo>\n")
            print("Cada versão >= 3.7.8 DEVE possuir seu próprio registro de IA.")
            print("Blocos globais no topo não são permitidos.\n")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
