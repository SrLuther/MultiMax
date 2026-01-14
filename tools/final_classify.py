#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

CRITICAL = ['Jinja2 em fetch() sem tojson', 'Jinja2 em window.open() sem tojson', 
            'Jinja2 dentro de strings JavaScript', 'Uso de innerHTML', 'Template string JavaScript']

ATTENTION = ['Evento onclick inline', 'Evento onchange inline', 'Evento onsubmit inline']

def classify(t):
    for p in CRITICAL:
        if p in t:
            return 'CRÍTICO'
    for p in ATTENTION:
        if p in t:
            return 'ATENÇÃO'
    return 'MANUTENÇÃO'

def parse():
    fpath = Path('temp_alerts_clean.txt')
    if not fpath.exists():
        fpath = Path('temp_alerts.txt')
    if not fpath.exists():
        return []
    
    content = fpath.read_text(encoding='utf-8', errors='replace')
    
    # Regex para encontrar blocos de alerta - formato mais flexível
    pattern = r'\[ALERTA\]\s*\n\s*Arquivo:\s*(.+?)\s*\n\s*Linha:\s*(\d+)\s*\n\s*Tipo:\s*(.+?)\s*\n\s*Trecho:\s*(.+?)(?=\s*\n\s*\[ALERTA\]|\s*\n\s*===|$)'
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    alerts = []
    for match in matches:
        alerts.append({
            'file': match[0].strip(),
            'line': int(match[1].strip()),
            'type': match[2].strip(),
            'snippet': match[3].strip()[:100]
        })
    
    return alerts

def generate_report(alerts):
    critical = [a for a in alerts if classify(a['type']) == 'CRÍTICO']
    attention = [a for a in alerts if classify(a['type']) == 'ATENÇÃO']
    maintenance = [a for a in alerts if classify(a['type']) == 'MANUTENÇÃO']
    
    def group_by_file(alerts_list):
        grouped = {}
        for alert in alerts_list:
            f = alert['file']
            if f not in grouped:
                grouped[f] = []
            grouped[f].append(alert)
        return grouped
    
    critical_by_file = group_by_file(critical)
    attention_by_file = group_by_file(attention)
    maintenance_by_file = group_by_file(maintenance)
    
    lines = []
    lines.append("# Classificação Técnica dos Alertas de Segurança JavaScript\n")
    lines.append("**Data:** 2026-01-10\n")
    lines.append("**Fonte:** `tools/js_safety_check.py`\n")
    lines.append("\n---\n")
    
    lines.append("## Resumo Numérico\n")
    lines.append(f"- **CRÍTICO:** {len(critical)} alertas\n")
    lines.append(f"- **ATENÇÃO:** {len(attention)} alertas\n")
    lines.append(f"- **MANUTENÇÃO:** {len(maintenance)} alertas\n")
    lines.append(f"- **TOTAL:** {len(alerts)} alertas\n")
    lines.append("\n---\n")
    
    # CRÍTICO
    lines.append("## 🔴 CRÍTICO - Pode quebrar parsing JavaScript ou causar erro imediato\n")
    if critical:
        for file in sorted(critical_by_file.keys()):
            lines.append(f"### {file}\n")
            for alert in sorted(critical_by_file[file], key=lambda x: x.get('line', 0)):
                lines.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get('snippet'):
                    snippet = alert['snippet']
                    if len(snippet) > 100:
                        snippet = snippet[:97] + '...'
                    lines.append(f"  ```\n  {snippet}\n  ```")
                lines.append("")
    else:
        lines.append("*Nenhum alerta crítico encontrado.*\n")
    lines.append("\n---\n")
    
    # ATENÇÃO
    lines.append("## 🟡 ATENÇÃO - Não quebra agora, mas pode virar erro\n")
    if attention:
        for file in sorted(attention_by_file.keys()):
            lines.append(f"### {file}\n")
            for alert in sorted(attention_by_file[file], key=lambda x: x.get('line', 0)):
                lines.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get('snippet'):
                    snippet = alert['snippet']
                    if len(snippet) > 100:
                        snippet = snippet[:97] + '...'
                    lines.append(f"  ```\n  {snippet}\n  ```")
                lines.append("")
    else:
        lines.append("*Nenhum alerta de atenção encontrado.*\n")
    lines.append("\n---\n")
    
    # MANUTENÇÃO
    lines.append("## 🔵 MANUTENÇÃO - Apenas má prática\n")
    if maintenance:
        for file in sorted(maintenance_by_file.keys()):
            lines.append(f"### {file}\n")
            for alert in sorted(maintenance_by_file[file], key=lambda x: x.get('line', 0)):
                lines.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get('snippet'):
                    snippet = alert['snippet']
                    if len(snippet) > 100:
                        snippet = snippet[:97] + '...'
                    lines.append(f"  ```\n  {snippet}\n  ```")
                lines.append("")
    else:
        lines.append("*Nenhum alerta de manutenção encontrado.*\n")
    lines.append("\n---\n")
    
    # Prioridades
    lines.append("## 🎯 O que deve ser corrigido primeiro (CRÍTICOS)\n")
    if critical:
        fetch_alerts = [a for a in critical if 'fetch()' in a['type']]
        window_open_alerts = [a for a in critical if 'window.open()' in a['type']]
        jinja_string_alerts = [a for a in critical if 'Jinja2 dentro de strings JavaScript' in a['type']]
        innerhtml_alerts = [a for a in critical if 'innerHTML' in a['type']]
        template_alerts = [a for a in critical if 'Template string' in a['type']]
        
        lines.append("### Prioridade 1: Jinja2 em funções JavaScript sem tojson\n")
        if fetch_alerts:
            lines.append(f"- **Jinja2 em fetch() sem tojson:** {len(fetch_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            lines.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")
        if window_open_alerts:
            lines.append(f"- **Jinja2 em window.open() sem tojson:** {len(window_open_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            lines.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")
        
        lines.append("### Prioridade 2: Jinja2 dentro de strings JavaScript\n")
        if jinja_string_alerts:
            lines.append(f"- **Total:** {len(jinja_string_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing quando valores contêm aspas ou caracteres especiais")
            lines.append("  - Solução: Extrair para constantes JS usando `|tojson` ou meta tags\n")
        
        lines.append("### Prioridade 3: innerHTML com dados dinâmicos\n")
        if innerhtml_alerts:
            lines.append(f"- **Total:** {len(innerhtml_alerts)} ocorrências")
            lines.append("  - Risco: XSS (Cross-Site Scripting) se dados vierem do backend")
            lines.append("  - Solução: Usar `textContent` ou sanitizar dados antes de inserir\n")
        
        lines.append("### Prioridade 4: Template strings com interpolação dinâmica\n")
        if template_alerts:
            lines.append(f"- **Total:** {len(template_alerts)} ocorrências")
            lines.append("  - Risco: XSS se dados não forem escapados corretamente")
            lines.append("  - Solução: Escapar dados ou usar `textContent`/`createElement`\n")
    else:
        lines.append("*Nenhum alerta crítico encontrado.*\n")
    
    lines.append("\n---\n")
    lines.append("## 📝 Notas\n")
    lines.append("- Esta classificação foi gerada automaticamente\n")
    lines.append("- Nenhum código funcional foi alterado durante a geração deste relatório\n")
    lines.append("- Para corrigir os alertas, consulte a documentação técnica do projeto\n")
    
    return '\n'.join(lines)

if __name__ == '__main__':
    alerts = parse()
    print(f"Processando {len(alerts)} alertas...")
    
    if not alerts:
        print("Nenhum alerta encontrado. Verifique se o arquivo temp_alerts_clean.txt existe.")
        sys.exit(1)
    
    report = generate_report(alerts)
    
    output_file = Path('documentacao/js-safety-classification.md')
    output_file.parent.mkdir(exist_ok=True)
    
    output_file.write_text(report, encoding='utf-8')
    
    print(f"Relatório gerado em: {output_file}")
    print(f"Total de alertas processados: {len(alerts)}")
