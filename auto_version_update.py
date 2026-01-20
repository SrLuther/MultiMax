#!/usr/bin/env python3
"""
Script para atualizar versão automaticamente antes de cada push.
Este script incrementa a versão patch automaticamente e atualiza todos os arquivos necessários.

Uso:
    python auto_version_update.py [patch|minor|major]
    Padrão: patch (ex: 2.6.0 -> 2.6.1)
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path


def get_current_version_from_changelog():
    """Lê a versão atual do CHANGELOG.md"""
    changelog = Path("CHANGELOG.md")
    if changelog.exists():
        content = changelog.read_text(encoding="utf-8")
        match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", content, re.MULTILINE)
        if match:
            return match.group(1)
    return None


def get_current_version_from_init():
    """Lê a versão atual do multimax/__init__.py"""
    init_file = Path("multimax/__init__.py")
    if init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        # Procura por "return '2.6.0'" ou similar
        match = re.search(r"return ['\"](\d+\.\d+\.\d+)['\"]", content)
        if match:
            return match.group(1)
    return None


def get_current_version():
    """Obtém a versão atual de qualquer fonte disponível"""
    version = get_current_version_from_changelog()
    if version:
        return version
    version = get_current_version_from_init()
    if version:
        return version
    raise ValueError("Não foi possível determinar a versão atual")


def increment_version(version: str, bump_type: str = "patch") -> str:
    """Incrementa a versão conforme o tipo"""
    parts = list(map(int, version.split(".")))

    if bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    else:  # patch
        parts[2] += 1

    return ".".join(map(str, parts))


def ensure_descriptive_text(text: str, new_version: str) -> str:
    """Simplesmente retorna o texto como está"""
    return text.strip()


def update_changelog(new_version: str, commit_message: str | None = None):
    """Atualiza CHANGELOG.md"""
    changelog = Path("CHANGELOG.md")
    today = date.today().isoformat()

    if not changelog.exists():
        print("AVISO: CHANGELOG.md nao encontrado, criando...")
        description = commit_message or "Atualização do sistema"
        changelog_content = f"## [{new_version}] - {today}\n\n### Atualização\n\n- {description}\n\n"
        changelog.write_text(changelog_content, encoding="utf-8")
        return

    content = changelog.read_text(encoding="utf-8")

    # Determina o tipo de mudança e seção apropriada
    section, description = determine_section_and_description(commit_message or "Atualização do sistema")

    # Cria nova entrada
    new_entry = f"## [{new_version}] - {today}\n\n{section}\n\n- {description}\n\n"

    # Adiciona no topo
    pattern = r"^## \[[\d.]+\] - \d{4}-\d{2}-\d{2}"
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        replacement = new_entry.rstrip() + "\n\n" + match.group(0)
        content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    else:
        content = new_entry + content

    changelog.write_text(content, encoding="utf-8")
    print(f"OK: CHANGELOG.md atualizado para {new_version}")


def determine_section_and_description(message: str) -> tuple[str, str]:
    """Determina a seção e descrição apropriada baseada na mensagem (PT-BR)."""
    msg_lower = message.lower()

    if any(keyword in msg_lower for keyword in ["fix", "correç", "erro", "bug", "error"]):
        section = "### Correções"
        if "fix(" in message:
            match = re.search(r"fix\([^)]+\):\s*(.+)", message)
            if match:
                return section, f"fix{match.group(0)}"
        return section, message

    if any(keyword in msg_lower for keyword in ["feat", "nova", "adiciona", "novo", "implementa"]):
        section = "### Novidades"
        if "feat(" in message:
            match = re.search(r"feat\([^)]+\):\s*(.+)", message)
            if match:
                return section, f"feat{match.group(0)}"
        return section, message

    if any(keyword in msg_lower for keyword in ["refactor", "melhoria", "otimiza", "melhora"]):
        section = "### Melhorias"
        return section, message

    if "design" in msg_lower:
        section = "### Design"
        return section, message

    if "docs" in msg_lower or "documenta" in msg_lower:
        section = "### Documentação"
        return section, message

    if "versao" in msg_lower or "versão" in msg_lower:
        if len(message.split("-")) > 1:
            desc = message.split("-", 1)[1].strip()
            return determine_section_and_description(desc)
        return "### Atualização", message

    return "### Atualização", message


def update_init_py(new_version: str):
    """Atualiza multimax/__init__.py"""
    init_file = Path("multimax/__init__.py")
    if not init_file.exists():
        print("AVISO: multimax/__init__.py nao encontrado")
        return

    content = init_file.read_text(encoding="utf-8")

    # Atualiza todas as ocorrências de versão
    content = re.sub(r"return ['\"]\d+\.\d+\.\d+['\"]", f"return '{new_version}'", content)

    # Também atualiza se estiver em uma string direta
    content = re.sub(r"['\"]\d+\.\d+\.\d+['\"]", f"'{new_version}'", content)

    init_file.write_text(content, encoding="utf-8")
    print(f"OK: multimax/__init__.py atualizado para {new_version}")


def update_leia_me(new_version: str):
    """Atualiza LEIA-ME.txt"""
    leia_me = Path("LEIA-ME.txt")
    if not leia_me.exists():
        print("AVISO: LEIA-ME.txt nao encontrado, pulando...")
        return

    content = leia_me.read_text(encoding="utf-8")

    # Atualiza versão
    content = re.sub(r"Versão \d+\.\d+\.\d+", f"Versão {new_version}", content)
    content = re.sub(r"VERSÃO [\d.]+", f"VERSÃO {new_version}", content)
    content = re.sub(r"versão [\d.]+", f"versão {new_version}", content)

    leia_me.write_text(content, encoding="utf-8")
    print(f"OK: LEIA-ME.txt atualizado para {new_version}")


def update_version_sync(new_version: str):
    """Atualiza VERSION_SYNC.md"""
    version_sync = Path("VERSION_SYNC.md")
    if not version_sync.exists():
        print("AVISO: VERSION_SYNC.md nao encontrado, pulando...")
        return

    content = version_sync.read_text(encoding="utf-8")
    content = re.sub(r"## Versão atual: [\d.]+", f"## Versão atual: {new_version}", content)
    version_sync.write_text(content, encoding="utf-8")
    print(f"OK: VERSION_SYNC.md atualizado para {new_version}")


def create_git_tag(new_version: str, commit_message: str | None = None):
    """Cria tag Git"""
    tag_name = f"v{new_version}"

    # Verifica se tag já existe
    result = subprocess.run(["git", "tag", "-l", tag_name], capture_output=True, text=True)
    if tag_name in result.stdout:
        print(f"AVISO: Tag {tag_name} ja existe. Pulando criacao de tag.")
        return False

    # Cria tag anotada
    tag_message = commit_message or f"Versao {new_version}"
    subprocess.run(["git", "tag", "-a", tag_name, "-m", tag_message], check=True)
    print(f"OK: Tag {tag_name} criada")
    return True


def get_descriptive_commit_message(new_version: str) -> str:  # noqa: C901
    """Analisa mudanças e gera mensagem descritiva para o changelog (PT-BR e não genérica)."""

    # 1. Tenta obter mensagens de commits não enviados
    try:
        result = subprocess.run(
            ["git", "log", "origin/nova-versao-deploy..HEAD", "--oneline"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            commits = result.stdout.strip().split("\n")
            relevant = []
            for commit in commits:
                if any(keyword in commit.lower() for keyword in ["chore:", "merge", "versao", "version"]):
                    continue
                # Remove hash
                cleaned = commit.split(" ", 1)[1] if " " in commit else commit
                relevant.append(cleaned)
            if relevant:
                # Usa até duas mensagens para ficar mais descritivo
                joined = "; ".join(relevant[:2])
                return f"{joined}"
    except Exception:
        pass

    # 2. Se não há commits não enviados, analisa staged changes
    try:
        result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            changed_files = result.stdout.strip().split("\n")

            # Analisa tipos de mudanças baseado nos arquivos
            changes = []
            for file in changed_files:
                if "models.py" in file:
                    changes.append("atualização de modelos de dados")
                elif "routes/" in file:
                    changes.append("correções de rotas")
                elif "templates/" in file:
                    changes.append("ajustes de interface")
                elif "__init__.py" in file:
                    continue  # Ignora mudanças de versão
                elif any(ext in file for ext in [".py", ".js", ".html"]):
                    changes.append("melhorias de código")

            if changes:
                return ", ".join(changes[:2])
    except Exception:
        pass

    # 3. Se não há staged changes, analisa working directory
    try:
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")

            # Analisa mudanças não commitadas
            changes = []
            for line in lines:
                if "models.py" in line:
                    changes.append("atualização de modelos de dados")
                elif "routes/" in line:
                    changes.append("correções de rotas")
                elif "templates/" in line:
                    changes.append("ajustes de interface")

            if changes:
                return ", ".join(changes[:2])
    except Exception:
        pass

    # 4. Sem descrição suficiente: retorna mensagem padrão
    return f"Atualização do sistema para versão {new_version}"


def main():
    """Função principal"""
    bump_type = sys.argv[1] if len(sys.argv) > 1 else "patch"

    if bump_type not in ["patch", "minor", "major"]:
        print("ERRO: Tipo de incremento invalido. Use: patch, minor ou major")
        sys.exit(1)

    try:
        current_version = get_current_version()
    except ValueError as e:
        print(f"ERRO: {e}")
        sys.exit(1)

    new_version = increment_version(current_version, bump_type)

    print(f"Versao atual: {current_version}")
    print(f"Nova versao: {new_version} ({bump_type})")
    print()

    # Obtém mensagem descritiva das mudanças
    commit_message = get_descriptive_commit_message(new_version)

    # Atualiza arquivos
    update_changelog(new_version, commit_message)
    update_init_py(new_version)
    update_leia_me(new_version)
    update_version_sync(new_version)

    print()
    print("Arquivos atualizados!")
    print()
    print("Proximos passos (ou use git-push-with-version.ps1):")
    print("1. git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md")
    print(f'2. git commit -m "chore: Atualiza versao para {new_version}"')
    print(f'3. git tag -a v{new_version} -m "Versao {new_version}"')
    print("4. git push origin nova-versao-deploy")
    print(f"5. git push origin v{new_version}")


if __name__ == "__main__":
    main()
