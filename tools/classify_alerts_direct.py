#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para classificar alertas diretamente da saída do js_safety_check.py
"""

import subprocess
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


def run_check():
    """Executa o js_safety_check.py e retorna a saída"""
    try:
        result = subprocess.run(
            ["python", "tools/js_safety_check.py"], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.stdout
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        return ""


def parse_output(output):
    """Parseia a saída do script"""
    alerts: list[dict[str, Any]] = []
    current: dict[str, Any] = {}

    for line in output.split("\n"):
        if line.strip() == "[ALERTA]":
            if current.get("file"):
                alerts.append(current)
            current = {}
        elif line.startswith("Arquivo:"):
            current["file"] = line.replace("Arquivo:", "").strip()
        elif line.startswith("Linha:"):
            try:
                current["line"] = int(line.replace("Linha:", "").strip())
            except Exception:
                pass
        elif line.startswith("Tipo:"):
            current["type"] = line.replace("Tipo:", "").strip()
        elif line.startswith("Trecho:"):
            current["snippet"] = line.replace("Trecho:", "").strip()

    if current.get("file"):
        alerts.append(current)

    return alerts


def classify(alert_type):
    """Classifica um alerta"""
    for pattern in CRITICAL_PATTERNS:
        if pattern in alert_type:
            return "CRÍTICO"
    for pattern in ATTENTION_PATTERNS:
        if pattern in alert_type:
            return "ATENÇÃO"
    return "MANUTENÇÃO"


def generate_report(alerts):  # noqa: C901
    """Gera o relatório"""
    critical = [a for a in alerts if classify(a["type"]) == "CRÍTICO"]
    attention = [a for a in alerts if classify(a["type"]) == "ATENÇÃO"]
    maintenance = [a for a in alerts if classify(a["type"]) == "MANUTENÇÃO"]

    def group_by_file(alerts_list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for alert in alerts_list:
            f = alert["file"]
            if f not in grouped:
                grouped[f] = []
            grouped[f].append(alert)
        return grouped

    critical_by_file = group_by_file(critical)
    attention_by_file = group_by_file(attention)
    maintenance_by_file = group_by_file(maintenance)

    report = []
    report.append("# Classificação Técnica dos Alertas de Segurança JavaScript\n")
    report.append("**Data:** 2026-01-10\n")
    report.append("**Fonte:** `tools/js_safety_check.py`\n")
    report.append("\n---\n")

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

    # Prioridades
    report.append("## 🎯 O que deve ser corrigido primeiro (CRÍTICOS)\n")
    if critical:
        fetch_alerts = [a for a in critical if "fetch()" in a["type"]]
        window_open_alerts = [a for a in critical if "window.open()" in a["type"]]
        jinja_string_alerts = [a for a in critical if "Jinja2 dentro de strings JavaScript" in a["type"]]
        innerhtml_alerts = [a for a in critical if "innerHTML" in a["type"]]
        template_alerts = [a for a in critical if "Template string" in a["type"]]

        report.append("### Prioridade 1: Jinja2 em funções JavaScript sem tojson\n")
        if fetch_alerts:
            report.append(f"- **Jinja2 em fetch() sem tojson:** {len(fetch_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            report.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")
        if window_open_alerts:
            report.append(f"- **Jinja2 em window.open() sem tojson:** {len(window_open_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            report.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags\n")

        report.append("### Prioridade 2: Jinja2 dentro de strings JavaScript\n")
        if jinja_string_alerts:
            report.append(f"- **Total:** {len(jinja_string_alerts)} ocorrências")
            report.append("  - Risco: Quebra parsing quando valores contêm aspas ou caracteres especiais")
            report.append("  - Solução: Extrair para constantes JS usando `|tojson` ou meta tags\n")

        report.append("### Prioridade 3: innerHTML com dados dinâmicos\n")
        if innerhtml_alerts:
            report.append(f"- **Total:** {len(innerhtml_alerts)} ocorrências")
            report.append("  - Risco: XSS (Cross-Site Scripting) se dados vierem do backend")
            report.append("  - Solução: Usar `textContent` ou sanitizar dados antes de inserir\n")

        report.append("### Prioridade 4: Template strings com interpolação dinâmica\n")
        if template_alerts:
            report.append(f"- **Total:** {len(template_alerts)} ocorrências")
            report.append("  - Risco: XSS se dados não forem escapados corretamente")
            report.append("  - Solução: Escapar dados ou usar `textContent`/`createElement`\n")
    else:
        report.append("*Nenhum alerta crítico encontrado.*\n")

    report.append("\n---\n")
    report.append("## 📝 Notas\n")
    report.append("- Esta classificação foi gerada automaticamente\n")
    report.append("- Nenhum código funcional foi alterado durante a geração deste relatório\n")
    report.append("- Para corrigir os alertas, consulte a documentação técnica do projeto\n")

    return "\n".join(report)


if __name__ == "__main__":
    print("Executando verificação de segurança JavaScript...")
    output = run_check()

    if not output or "ALERTAS DE SEGURANÇA JAVASCRIPT ENCONTRADOS" not in output:
        print("Nenhum alerta encontrado ou erro na execução.")
        sys.exit(0)

    alerts = parse_output(output)

    if not alerts:
        print("Nenhum alerta parseado.")
        sys.exit(0)

    print(f"Processando {len(alerts)} alertas...")
    report = generate_report(alerts)

    output_file = Path("documentacao/js-safety-classification.md")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Relatório gerado em: {output_file}")
    print(f"Total de alertas processados: {len(alerts)}")
