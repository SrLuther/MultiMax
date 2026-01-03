#!/usr/bin/env python3
"""
Script para criar arquivo ZIP de deploy para VPS
"""
import zipfile
import os
from pathlib import Path

def should_exclude(path_str, name):
    """Verifica se o arquivo/pasta deve ser excluído"""
    exclude_patterns = [
        '.git',
        '__pycache__',
        '.pyc',
        '.pyo',
        '.pyd',
        '.gitignore',
        '.dockerignore',
        'Dockerfile',
        'docker-compose.yml',
        'pyrightconfig.json',
        'CHANGELOG.md',
        'LEIA-ME.txt',
        'README.md',
        'cron',
        '.trae',
        '.vscode',
        '.idea',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        'Thumbs.db',
        'create_deploy_zip.py',
        'multimax-vps-deploy.zip',
        '.env',
        'venv',
        'env',
        'node_modules',
    ]
    
    # Verifica padrões de exclusão
    for pattern in exclude_patterns:
        if pattern in path_str or name.endswith(pattern.replace('*', '')):
            return True
    
    # Exclui arquivos Python compilados
    if name.endswith(('.pyc', '.pyo', '.pyd')):
        return True
    
    return False

def create_deploy_zip():
    """Cria o arquivo ZIP de deploy"""
    zip_filename = 'multimax-vps-deploy.zip'
    
    # Remove ZIP anterior se existir
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
        print(f"Arquivo {zip_filename} anterior removido.")
    
    base_dir = Path('.')
    files_added = 0
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Adiciona arquivos necessários
        for file_path in base_dir.rglob('*'):
            if file_path.is_file():
                path_str = str(file_path)
                name = file_path.name
                
                # Pula arquivos que devem ser excluídos
                if should_exclude(path_str, name):
                    continue
                
                # Adiciona ao ZIP usando caminho relativo
                arcname = file_path.relative_to(base_dir)
                zipf.write(file_path, arcname)
                files_added += 1
        
        print(f"\n[OK] ZIP criado: {zip_filename}")
        print(f"[OK] Arquivos incluidos: {files_added}")
        print(f"[OK] Tamanho: {os.path.getsize(zip_filename) / 1024 / 1024:.2f} MB")
    
    return zip_filename

if __name__ == '__main__':
    print("Criando arquivo ZIP para deploy em VPS...")
    print("Excluindo arquivos desnecessarios...\n")
    zip_file = create_deploy_zip()
    print(f"\n[SUCESSO] Arquivo pronto: {zip_file}")

