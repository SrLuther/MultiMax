#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação Preventiva de Segurança JavaScript
Detecta padrões perigosos que podem causar erros de parsing JavaScript em templates Jinja2
"""

import os
import re
import sys
from pathlib import Path

# Padrões perigosos a detectar
PATTERNS = {
    'jinja2_in_fetch': {
        'description': 'Jinja2 em fetch() sem tojson',
        'pattern': r'fetch\s*\(\s*["\']\s*\{\{[^}]+\}\}',
        'flags': re.IGNORECASE | re.DOTALL
    },
    'jinja2_in_window_open': {
        'description': 'Jinja2 em window.open() sem tojson',
        'pattern': r'window\.open\s*\(\s*["\']\s*\{\{[^}]+\}\}',
        'flags': re.IGNORECASE | re.DOTALL
    },
    'jinja2_in_js_string': {
        'description': 'Jinja2 dentro de strings JavaScript (dentro de <script>)',
        'pattern': r'["\'].*?\{\{[^}]+\}\}.*?["\']',
        'flags': re.DOTALL,
        'context': 'script'  # Apenas dentro de blocos <script>
    },
    'inline_onclick': {
        'description': 'Evento onclick inline',
        'pattern': r'\bonclick\s*=',
        'flags': re.IGNORECASE
    },
    'inline_onchange': {
        'description': 'Evento onchange inline',
        'pattern': r'\bonchange\s*=',
        'flags': re.IGNORECASE
    },
    'inline_onsubmit': {
        'description': 'Evento onsubmit inline',
        'pattern': r'\bonsubmit\s*=',
        'flags': re.IGNORECASE
    },
    'innerhtml_usage': {
        'description': 'Uso de innerHTML (risco XSS)',
        'pattern': r'\.innerHTML\s*=',
        'flags': re.IGNORECASE
    },
    'template_string_interpolation': {
        'description': 'Template string JavaScript com interpolação dinâmica',
        'pattern': r'`[^`]*\$\{[^}]+\}[^`]*`',
        'flags': re.DOTALL,
        'context': 'script'  # Apenas dentro de blocos <script>
    }
}

def is_in_script_block(content, position):
    """Verifica se uma posição está dentro de um bloco <script>"""
    # Encontrar o último <script> antes da posição
    script_start = content.rfind('<script', 0, position)
    if script_start == -1:
        return False
    
    # Verificar se não há </script> entre script_start e position
    script_end = content.find('</script>', script_start, position)
    if script_end != -1:
        return False
    
    # Verificar se o script não está comentado ou em template string
    # (verificação básica - pode ter falsos positivos em casos complexos)
    return True

def find_all_occurrences(content, pattern_name, pattern_info):
    """Encontra todas as ocorrências de um padrão no conteúdo"""
    occurrences = []
    pattern = pattern_info['pattern']
    flags = pattern_info['flags']
    require_script_context = pattern_info.get('context') == 'script'
    
    for match in re.finditer(pattern, content, flags):
        # Se o padrão requer contexto de script, verificar
        if require_script_context and not is_in_script_block(content, match.start()):
            continue
        
        line_num = content[:match.start()].count('\n') + 1
        line_start = content.rfind('\n', 0, match.start()) + 1
        line_end = content.find('\n', match.end())
        if line_end == -1:
            line_end = len(content)
        
        line_content = content[line_start:line_end].strip()
        occurrences.append({
            'line': line_num,
            'match': match.group(0),
            'line_content': line_content
        })
    
    return occurrences

def check_file(file_path):
    """Verifica um arquivo HTML em busca de padrões perigosos"""
    alerts = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return [{
            'type': 'ERRO_LEITURA',
            'line': 0,
            'message': f'Erro ao ler arquivo: {e}'
        }]
    
    # Verificar cada padrão
    for pattern_name, pattern_info in PATTERNS.items():
        occurrences = find_all_occurrences(content, pattern_name, pattern_info)
        
        for occ in occurrences:
            alerts.append({
                'type': pattern_info['description'],
                'line': occ['line'],
                'snippet': occ['line_content']
            })
    
    return alerts

def main():
    """Função principal"""
    templates_dir = Path('templates')
    
    if not templates_dir.exists():
        print(f"ERRO: Diretório '{templates_dir}' não encontrado.")
        sys.exit(1)
    
    all_alerts = []
    
    # Percorrer recursivamente todos os arquivos .html
    for html_file in templates_dir.rglob('*.html'):
        relative_path = html_file.relative_to(Path('.'))
        alerts = check_file(html_file)
        
        for alert in alerts:
            alert['file'] = str(relative_path).replace('\\', '/')
            all_alerts.append(alert)
    
    # Reportar resultados
    if all_alerts:
        print("=" * 80)
        print("ALERTAS DE SEGURANÇA JAVASCRIPT ENCONTRADOS")
        print("=" * 80)
        print()
        
        for alert in all_alerts:
            print("[ALERTA]")
            print(f"Arquivo: {alert['file']}")
            print(f"Linha: {alert['line']}")
            print(f"Tipo: {alert['type']}")
            if 'snippet' in alert:
                snippet = alert['snippet']
                if len(snippet) > 120:
                    snippet = snippet[:117] + '...'
                print(f"Trecho: {snippet}")
            print()
        
        print("=" * 80)
        print(f"Total de alertas encontrados: {len(all_alerts)}")
        print("=" * 80)
        sys.exit(1)
    else:
        print("Verificação concluída: nenhum padrão perigoso encontrado.")
        sys.exit(0)

if __name__ == '__main__':
    main()
