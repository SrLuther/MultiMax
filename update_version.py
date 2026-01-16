#!/usr/bin/env python3
"""
Script para atualizar versão do projeto MultiMax e criar tag Git automaticamente.

Uso:
    python update_version.py <nova_versao> [mensagem_commit]

Exemplo:
    python update_version.py 2.3.8 "Correção de bug crítico"
"""

import re
import subprocess
import sys
from pathlib import Path


def read_file(filepath):
    """Lê um arquivo"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath, content):
    """Escreve um arquivo"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def update_changelog(version, date_str="2025-01-04"):
    """Atualiza CHANGELOG.md"""
    filepath = Path("CHANGELOG.md")
    content = read_file(filepath)

    # Adiciona nova entrada no topo
    new_entry = f"""## [{version}] - {date_str}

### 🔧 Atualização

- Versão {version}

---

"""

    # Substitui a primeira linha de versão
    pattern = r"^## \[[\d.]+\] - \d{4}-\d{2}-\d{2}"
    match = re.search(pattern, content)
    content = re.sub(
        pattern,
        new_entry.rstrip() + "\n\n" + match.group(0)
        if match
        else new_entry + content,
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Se não encontrou padrão, adiciona no início
    if not re.search(r"^## \[", content):
        content = new_entry + content

    write_file(filepath, content)
    print(f"✓ CHANGELOG.md atualizado para {version}")


def update_init_py(version):
    """Atualiza multimax/__init__.py"""
    filepath = Path("multimax/__init__.py")
    content = read_file(filepath)

    # Procura por return 'X.Y.Z' na linha 634 aproximadamente
    pattern = r"return '[\d.]+'"
    replacement = f"return '{version}'"
    content = re.sub(pattern, replacement, content)

    write_file(filepath, content)
    print(f"✓ multimax/__init__.py atualizado para {version}")


def update_leia_me(version, month="Janeiro", year="2025"):
    """Atualiza LEIA-ME.txt"""
    filepath = Path("LEIA-ME.txt")
    content = read_file(filepath)

    # Linha 3: Versão X.Y.Z - Mês YYYY
    pattern1 = r"Versão [\d.]+ - \w+ \d{4}"
    replacement1 = f"Versão {version} - {month} {year}"
    content = re.sub(pattern1, replacement1, content)

    # Linha 75: PRINCIPAIS FUNCIONALIDADES DA VERSÃO X.Y.Z:
    pattern2 = r"PRINCIPAIS FUNCIONALIDADES DA VERSÃO [\d.]+:"
    replacement2 = f"PRINCIPAIS FUNCIONALIDADES DA VERSÃO {version}:"
    content = re.sub(pattern2, replacement2, content)

    write_file(filepath, content)
    print(f"✓ LEIA-ME.txt atualizado para {version}")


def update_version_sync(version):
    """Atualiza VERSION_SYNC.md"""
    filepath = Path("VERSION_SYNC.md")
    content = read_file(filepath)

    pattern = r"## Versão atual: [\d.]+"
    replacement = f"## Versão atual: {version}"
    content = re.sub(pattern, replacement, content)

    write_file(filepath, content)
    print(f"✓ VERSION_SYNC.md atualizado para {version}")


def create_git_tag(version, message=None):
    """Cria tag Git"""
    if message is None:
        message = f"Versão {version}"

    tag_name = f"v{version}"

    # Verifica se tag já existe
    result = subprocess.run(["git", "tag", "-l", tag_name], capture_output=True, text=True)
    if tag_name in result.stdout:
        print(f"⚠ Tag {tag_name} já existe. Pulando criação de tag.")
        return False

    # Cria tag anotada
    subprocess.run(["git", "tag", "-a", tag_name, "-m", message], check=True)
    print(f"✓ Tag {tag_name} criada")
    return True


def main():
    if len(sys.argv) < 2:
        print("Uso: python update_version.py <nova_versao> [mensagem_commit]")
        print('Exemplo: python update_version.py 2.3.8 "Correção de bug"')
        sys.exit(1)

    new_version = sys.argv[1]
    commit_message = sys.argv[2] if len(sys.argv) > 2 else f"Atualiza versão para {new_version}"

    # Valida formato da versão
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"Erro: Versão deve estar no formato X.Y.Z (ex: 2.3.8)")
        sys.exit(1)

    print(f"Atualizando versão para {new_version}...")
    print()

    # Atualiza arquivos
    update_changelog(new_version)
    update_init_py(new_version)
    update_leia_me(new_version)
    update_version_sync(new_version)

    print()
    print("Arquivos atualizados. Próximos passos:")
    print(f"1. git add CHANGELOG.md multimax/__init__.py LEIA-ME.txt VERSION_SYNC.md")
    print(f'2. git commit -m "{commit_message}"')
    print(f'3. git tag -a v{new_version} -m "Versão {new_version} - {commit_message}"')
    print("4. git push origin nova-versao-deploy")
    print(f"5. git push origin v{new_version}")


if __name__ == "__main__":
    main()
