#!/usr/bin/env python3
"""
Script auxiliar para automatizar: incremento de versão, commit e push para GitHub
Uso: python .git_push_version.py [patch|minor|major]
Padrão: patch (ex: 2.2.0 -> 2.2.1)
"""
import re
import subprocess
import sys
from pathlib import Path

VERSION_FILE = Path("multimax/__init__.py")


def get_current_version():
    """Lê a versão atual do arquivo"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r"return '(\d+\.\d+\.\d+)'", content)
    if match:
        return match.group(1)
    raise ValueError("Versao nao encontrada no arquivo")


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


def update_version_file(new_version: str):
    """Atualiza o arquivo com a nova versão"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    new_content = re.sub(r"return '\d+\.\d+\.\d+'", f"return '{new_version}'", content)
    VERSION_FILE.write_text(new_content, encoding="utf-8")
    print(f"Versao atualizada no arquivo: {new_version}")


def git_commit_and_push(version: str):
    """Faz commit e push"""
    try:
        # Adiciona todas as mudanças
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

        # Commit
        commit_msg = f"release: v{version}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
        print(f"Commit criado: {commit_msg}")

        # Push
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print(f"Push realizado com sucesso!")

    except subprocess.CalledProcessError as e:
        print(f"Erro no git: {e}")
        sys.exit(1)


if __name__ == "__main__":
    bump_type = sys.argv[1] if len(sys.argv) > 1 else "patch"

    if bump_type not in ["patch", "minor", "major"]:
        print("Tipo de incremento invalido. Use: patch, minor ou major")
        sys.exit(1)

    current = get_current_version()
    new = increment_version(current, bump_type)

    print(f"Versao atual: {current}")
    print(f"Nova versao: {new} ({bump_type})")

    update_version_file(new)
    git_commit_and_push(new)

    print(f"\nProcesso concluido! Versao {new} enviada para o GitHub.")
