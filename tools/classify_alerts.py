#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script auxiliar para classificar alertas de segurança JavaScript
"""

import sys
from pathlib import Path
from typing import Any

# Classificação dos tipos de alerta
CRITICAL_PATTERNS = [
    "Jinja2 em fetch() sem tojson",
    "Jinja2 em window.open() sem tojson",
    "Jinja2 dentro de strings JavaScript",
    "Uso de innerHTML (risco XSS)",
    "Template string JavaScript com interpolação dinâmica",
]

ATTENTION_PATTERNS = ["Evento onclick inline", "Evento onchange inline", "Evento onsubmit inline"]


def parse_alerts_from_file(file_path):
    """Parseia alertas de um arquivo de texto"""
    alerts: list[dict[str, Any]] = []
    current_alert: dict[str, Any] = {}

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}", file=sys.stderr)
        return []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == "[ALERTA]":
            if current_alert and "file" in current_alert:
                alerts.append(current_alert)
            current_alert = {}
            i += 1
        elif line.startswith("Arquivo:"):
            current_alert["file"] = line.replace("Arquivo:", "").strip()
            i += 1
        elif line.startswith("Linha:"):
            try:
                current_alert["line"] = int(line.replace("Linha:", "").strip())
            except ValueError:
                pass
            i += 1
        elif line.startswith("Tipo:"):
            current_alert["type"] = line.replace("Tipo:", "").strip()
            i += 1
        elif line.startswith("Trecho:"):
            snippet = line.replace("Trecho:", "").strip()
            # Pode haver múltiplas linhas no trecho, mas vamos pegar só a primeira
            current_alert["snippet"] = snippet
            i += 1
        else:
            i += 1

    if current_alert and "file" in current_alert:
        alerts.append(current_alert)

    return alerts


def classify_alert(alert_type):
    """Classifica um alerta em CRÍTICO, ATENÇÃO ou MANUTENÇÃO"""
    # Verificar padrões críticos
    for pattern in CRITICAL_PATTERNS:
        if pattern in alert_type:
            return "CRÍTICO"

    # Verificar padrões de atenção
    for pattern in ATTENTION_PATTERNS:
        if pattern in alert_type:
            return "ATENÇÃO"

    # Por padrão, classificar como MANUTENÇÃO
    return "MANUTENÇÃO"


def generate_report(alerts):  # noqa: C901
    """Gera o relatório de classificação"""
    critical = []
    attention = []
    maintenance = []

    for alert in alerts:
        category = classify_alert(alert["type"])
        if category == "CRÍTICO":
            critical.append(alert)
        elif category == "ATENÇÃO":
            attention.append(alert)
        else:
            maintenance.append(alert)

    # Agrupar por arquivo
    def group_by_file(alerts_list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for alert in alerts_list:
            file = alert["file"]
            if file not in grouped:
                grouped[file] = []
            grouped[file].append(alert)
        return grouped

    critical_by_file = group_by_file(critical)
    attention_by_file = group_by_file(attention)
    maintenance_by_file = group_by_file(maintenance)

    report = []
    report.append("# Classificação Técnica dos Alertas de Segurança JavaScript\n")
    report.append("**Data:** 2026-01-10\n")
    report.append("**Fonte:** `tools/js_safety_check.py`\n")
    report.append("\n---\n")

    # Resumo numérico
    report.append("## Resumo Numérico\n")
    report.append(f"- **CRÍTICO:** {len(critical)} alertas\n")
    report.append(f"- **ATENÇÃO:** {len(attention)} alertas\n")
    report.append(f"- **MANUTENÇÃO:** {len(maintenance)} alertas\n")
    report.append(f"- **TOTAL:** {len(alerts)} alertas\n")
    report.append("\n---\n")

    # CRÍTICO
    report.append("## 🔴 CRÍTICO - Pode quebrar parsing JavaScript ou causar erro imediato\n")
    if critical:
        for file in sorted(critical_by_file.keys()):
            report.append(f"### {file}\n")
            for alert in sorted(critical_by_file[file], key=lambda x: x.get("line", 0)):
                report.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get("snippet"):
                    snippet = alert["snippet"]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    report.append(f"  ```\n  {snippet}\n  ```")
                report.append("")
    else:
        report.append("*Nenhum alerta crítico encontrado.*\n")
    report.append("\n---\n")

    # ATENÇÃO
    report.append("## 🟡 ATENÇÃO - Não quebra agora, mas pode virar erro\n")
    if attention:
        for file in sorted(attention_by_file.keys()):
            report.append(f"### {file}\n")
            for alert in sorted(attention_by_file[file], key=lambda x: x.get("line", 0)):
                report.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get("snippet"):
                    snippet = alert["snippet"]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    report.append(f"  ```\n  {snippet}\n  ```")
                report.append("")
    else:
        report.append("*Nenhum alerta de atenção encontrado.*\n")
    report.append("\n---\n")

    # MANUTENÇÃO
    report.append("## 🔵 MANUTENÇÃO - Apenas má prática\n")
    if maintenance:
        for file in sorted(maintenance_by_file.keys()):
            report.append(f"### {file}\n")
            for alert in sorted(maintenance_by_file[file], key=lambda x: x.get("line", 0)):
                report.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get("snippet"):
                    snippet = alert["snippet"]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    report.append(f"  ```\n  {snippet}\n  ```")
                report.append("")
    else:
        report.append("*Nenhum alerta de manutenção encontrado.*\n")
    report.append("\n---\n")

    # O que deve ser corrigido primeiro
    report.append("## 🎯 O que deve ser corrigido primeiro (CRÍTICOS)\n")
    if critical:
        report.append("### Prioridade 1: Jinja2 em funções JavaScript sem tojson\n")
        fetch_alerts = [a for a in critical if "fetch()" in a["type"]]
        window_open_alerts = [a for a in critical if "window.open()" in a["type"]]

        if fetch_alerts:
            report.append(f"- **Jinja2 em fetch() sem tojson:** {len(fetch_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            report.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")

        if window_open_alerts:
            report.append(f"- **Jinja2 em window.open() sem tojson:** {len(window_open_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            report.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")

        report.append("### Prioridade 2: Jinja2 dentro de strings JavaScript\n")
        jinja_string_alerts = [a for a in critical if "Jinja2 dentro de strings JavaScript" in a["type"]]
        if jinja_string_alerts:
            report.append(f"- **Total:** {len(jinja_string_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing quando valores contêm aspas ou caracteres especiais")
            report.append("  - Solução: Extrair para constantes JS usando `|tojson` ou meta tags\n")

        report.append("### Prioridade 3: innerHTML com dados dinâmicos\n")
        innerhtml_alerts = [a for a in critical if "innerHTML" in a["type"]]
        if innerhtml_alerts:
            report.append(f"- **Total:** {len(innerhtml_alerts)} ocorrências")
            report.append("  - Risco: XSS (Cross-Site Scripting) se dados vierem do backend")
            report.append("  - Solução: Usar `textContent` ou sanitizar dados antes de inserir\n")

        report.append("### Prioridade 4: Template strings com interpolação dinâmica\n")
        template_alerts = [a for a in critical if "Template string" in a["type"]]
        if template_alerts:
            report.append(f"- **Total:** {len(template_alerts)} ocorrências")
            report.append("  - Risco: XSS se dados não forem escapados corretamente")
            report.append("  - Solução: Escapar dados ou usar `textContent`/`createElement`\n")
    else:
        report.append("*Nenhum alerta crítico encontrado.*\n")

    report.append("\n---\n")
    report.append("## 📝 Notas\n")
    report.append("- Esta classificação foi gerada automaticamente pelo script `tools/classify_alerts.py`\n")
    report.append("- Nenhum código funcional foi alterado durante a geração deste relatório\n")
    report.append("- Para corrigir os alertas, consulte a documentação técnica do projeto\n")

    return "\n".join(report)


if __name__ == "__main__":
    # Tentar ler do arquivo temp_alerts.txt primeiro
    temp_file = Path("temp_alerts.txt")

    if temp_file.exists():
        print("Lendo alertas do arquivo temp_alerts.txt...")
        alerts = parse_alerts_from_file(temp_file)
    else:
        print(
            "Arquivo temp_alerts.txt não encontrado. Execute primeiro: "
            "python tools/js_safety_check.py > temp_alerts.txt"
        )
        sys.exit(1)

    if not alerts:
        print("Nenhum alerta encontrado.")
        sys.exit(0)

    print(f"Processando {len(alerts)} alertas...")
    report = generate_report(alerts)

    output_file = Path("documentacao/js-safety-classification.md")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Relatório gerado em: {output_file}")
    print(f"Total de alertas processados: {len(alerts)}")
