#!/usr/bin/env python3
import os
import re

# Verificar arquivos de configuração
config_files = ['.env.txt', '.env', 'config.py', 'instance/config.py']
for file in config_files:
    if os.path.exists(file):
        print(f'Arquivo encontrado: {file}')
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Verificar senhas ou chaves expostas
            if re.search(r'password\s*=\s*["\'].+["\']', content, re.IGNORECASE):
                print(f'  ⚠️ Possível senha exposta em {file}')
            if re.search(r'secret\s*=\s*["\'].+["\']', content, re.IGNORECASE):
                print(f'  ⚠️ Possível secret exposto em {file}')
            if re.search(r'key\s*=\s*["\'].+["\']', content, re.IGNORECASE):
                print(f'  ⚠️ Possível chave exposta em {file}')
    else:
        print(f'Arquivo não encontrado: {file}')
