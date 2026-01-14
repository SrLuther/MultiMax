#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

CRITICAL = [
    "Jinja2 em fetch() sem tojson",
    "Jinja2 em window.open() sem tojson",
    "Jinja2 dentro de strings JavaScript",
    "Uso de innerHTML",
    "Template string JavaScript",
]

ATTENTION = ["Evento onclick inline", "Evento onchange inline", "Evento onsubmit inline"]


def classify(t):
    for p in CRITICAL:
        if p in t:
            return "CRÍTICO"
    for p in ATTENTION:
        if p in t:
            return "ATENÇÃO"
    return "MANUTENÇÃO"


def parse():
    fpath = Path("temp_final.txt")
    if not fpath.exists():
        return []

    alerts = []
    current = {}

    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if "[ALERTA]" in line:
            if current.get("file"):
                alerts.append(current.copy())
            current = {}
        elif line.startswith("Arquivo:"):
            current["file"] = line[8:].strip()
        elif line.startswith("Linha:"):
            try:
                current["line"] = int(line[6:].strip())
            except:
                pass
        elif line.startswith("Tipo:"):
            current["type"] = line[5:].strip()
        elif line.startswith("Trecho:"):
            current["snippet"] = line[7:].strip()[:100]

        i += 1

    if current.get("file"):
        alerts.append(current)

    return alerts


def generate_report(alerts):
    critical = [a for a in alerts if classify(a["type"]) == "CRÍTICO"]
    attention = [a for a in alerts if classify(a["type"]) == "ATENÇÃO"]
    maintenance = [a for a in alerts if classify(a["type"]) == "MANUTENÇÃO"]

    def group_by_file(alerts_list):
        grouped = {}
        for alert in alerts_list:
            f = alert["file"]
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
            for alert in sorted(critical_by_file[file], key=lambda x: x.get("line", 0)):
                lines.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get("snippet"):
                    snippet = alert["snippet"]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    lines.append(f"  ```\n  {snippet}\n  ```")
                lines.append("")
    else:
        lines.append("*Nenhum alerta crítico encontrado.*\n")
    lines.append("\n---\n")

    # ATENÇÃO - Resumido por arquivo
    lines.append("## 🟡 ATENÇÃO - Não quebra agora, mas pode virar erro\n")
    if attention:
        for file in sorted(attention_by_file.keys()):
            count = len(attention_by_file[file])
            types = {}
            for alert in attention_by_file[file]:
                t = alert["type"]
                types[t] = types.get(t, 0) + 1
            lines.append(f"### {file}\n")
            lines.append(f"**Total:** {count} ocorrências\n")
            for t, c in sorted(types.items()):
                lines.append(f"- {t}: {c} ocorrências")
            lines.append("")
    else:
        lines.append("*Nenhum alerta de atenção encontrado.*\n")
    lines.append("\n---\n")

    # MANUTENÇÃO
    lines.append("## 🔵 MANUTENÇÃO - Apenas má prática\n")
    if maintenance:
        for file in sorted(maintenance_by_file.keys()):
            lines.append(f"### {file}\n")
            for alert in sorted(maintenance_by_file[file], key=lambda x: x.get("line", 0)):
                lines.append(f"- **Linha {alert.get('line', '?')}:** {alert['type']}")
                if alert.get("snippet"):
                    snippet = alert["snippet"]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    lines.append(f"  ```\n  {snippet}\n  ```")
                lines.append("")
    else:
        lines.append("*Nenhum alerta de manutenção encontrado.*\n")
    lines.append("\n---\n")

    # Prioridades
    lines.append("## 🎯 O que deve ser corrigido primeiro (CRÍTICOS)\n")
    if critical:
        fetch_alerts = [a for a in critical if "fetch()" in a["type"]]
        window_open_alerts = [a for a in critical if "window.open()" in a["type"]]
        jinja_string_alerts = [a for a in critical if "Jinja2 dentro de strings JavaScript" in a["type"]]
        innerhtml_alerts = [a for a in critical if "innerHTML" in a["type"]]
        template_alerts = [a for a in critical if "Template string" in a["type"]]

        lines.append("### Prioridade 1: Jinja2 em funções JavaScript sem tojson\n")
        if fetch_alerts:
            lines.append(f"- **Jinja2 em fetch() sem tojson:** {len(fetch_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            lines.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags")
            for alert in fetch_alerts:
                lines.append(f"  - `{alert['file']}` linha {alert.get('line', '?')}")
            lines.append("")
        if window_open_alerts:
            lines.append(f"- **Jinja2 em window.open() sem tojson:** {len(window_open_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais")
            lines.append("  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags")
            for alert in window_open_alerts:
                lines.append(f"  - `{alert['file']}` linha {alert.get('line', '?')}")
            lines.append("")

        lines.append("### Prioridade 2: Jinja2 dentro de strings JavaScript\n")
        if jinja_string_alerts:
            lines.append(f"- **Total:** {len(jinja_string_alerts)} ocorrências")
            lines.append("  - Risco: Quebra parsing quando valores contêm aspas ou caracteres especiais")
            lines.append("  - Solução: Extrair para constantes JS usando `|tojson` ou meta tags")
            files_affected = {}
            for alert in jinja_string_alerts:
                f = alert["file"]
                if f not in files_affected:
                    files_affected[f] = []
                files_affected[f].append(alert.get("line", 0))
            for f, lines_list in sorted(files_affected.items()):
                lines.append(
                    f"  - `{f}`: {len(lines_list)} ocorrências (linhas: {', '.join(map(str, sorted(lines_list)[:10]))}{'...' if len(lines_list) > 10 else ''})"
                )
            lines.append("")

        lines.append("### Prioridade 3: innerHTML com dados dinâmicos\n")
        if innerhtml_alerts:
            lines.append(f"- **Total:** {len(innerhtml_alerts)} ocorrências")
            lines.append("  - Risco: XSS (Cross-Site Scripting) se dados vierem do backend")
            lines.append("  - Solução: Usar `textContent` ou sanitizar dados antes de inserir")
            files_affected = {}
            for alert in innerhtml_alerts:
                f = alert["file"]
                files_affected[f] = files_affected.get(f, 0) + 1
            for f, count in sorted(files_affected.items()):
                lines.append(f"  - `{f}`: {count} ocorrências")
            lines.append("")

        lines.append("### Prioridade 4: Template strings com interpolação dinâmica\n")
        if template_alerts:
            lines.append(f"- **Total:** {len(template_alerts)} ocorrências")
            lines.append("  - Risco: XSS se dados não forem escapados corretamente")
            lines.append("  - Solução: Escapar dados ou usar `textContent`/`createElement`")
            files_affected = {}
            for alert in template_alerts:
                f = alert["file"]
                files_affected[f] = files_affected.get(f, 0) + 1
            for f, count in sorted(files_affected.items()):
                lines.append(f"  - `{f}`: {count} ocorrências")
            lines.append("")
    else:
        lines.append("*Nenhum alerta crítico encontrado.*\n")

    lines.append("\n---\n")
    lines.append("## 📝 Notas\n")
    lines.append("- Esta classificação foi gerada automaticamente\n")
    lines.append("- Nenhum código funcional foi alterado durante a geração deste relatório\n")
    lines.append("- Para corrigir os alertas, consulte a documentação técnica do projeto\n")

    return "\n".join(lines)


if __name__ == "__main__":
    alerts = parse()
    print(f"Processando {len(alerts)} alertas...")

    if not alerts:
        print("Nenhum alerta encontrado")
        sys.exit(1)

    report = generate_report(alerts)

    output_file = Path("documentacao/js-safety-classification.md")
    output_file.parent.mkdir(exist_ok=True)

    output_file.write_text(report, encoding="utf-8")

    print(f"Relatório gerado em: {output_file}")
    print(f"Total de alertas processados: {len(alerts)}")
