#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Análise léxica do JavaScript no template"""

with open('templates/ciclos/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extrair JavaScript
script_start = content.find('<script>', content.find('{% block content'))
script_end = content.find('</script>', script_start)
js_code = content[script_start+8:script_end]

lines = js_code.split('\n')

print("=" * 80)
print("ANÁLISE LÉXICA DO JAVASCRIPT")
print("=" * 80)
print(f"Total de linhas: {len(lines)}")
print(f"Total de caracteres: {len(js_code)}")
print()

# Encontrar linhas com Jinja2 em strings
print("LINHAS COM JINJA2 EM STRINGS JAVASCRIPT:")
print("-" * 80)
jinja_in_strings = []
for i, line in enumerate(lines, 1548):
    if "'{{" in line or '"{{' in line:
        jinja_in_strings.append((i, line))
        print(f"Linha {i}: {repr(line[:120])}")

print()
print(f"Total encontrado: {len(jinja_in_strings)}")
print()

# Análise léxica básica
print("ANÁLISE DE BALANCEAMENTO:")
print("-" * 80)
open_braces = 0
open_parens = 0
open_brackets = 0
in_single = False
in_double = False
escape = False

for i, char in enumerate(js_code):
    if escape:
        escape = False
        continue
    if char == '\\':
        escape = True
        continue
    
    if not in_single and not in_double:
        if char == "'":
            in_single = True
        elif char == '"':
            in_double = True
        elif char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
        elif char == '(':
            open_parens += 1
        elif char == ')':
            open_parens -= 1
        elif char == '[':
            open_brackets += 1
        elif char == ']':
            open_brackets -= 1
    else:
        if char == "'" and in_single:
            in_single = False
        elif char == '"' and in_double:
            in_double = False

print(f"Chaves balanceadas: {open_braces == 0} (diff: {open_braces})")
print(f"Parênteses balanceados: {open_parens == 0} (diff: {open_parens})")
print(f"Colchetes balanceados: {open_brackets == 0} (diff: {open_brackets})")
print(f"String single aberta: {in_single}")
print(f"String double aberta: {in_double}")

if in_single or in_double:
    print()
    print("ERRO LEXICAL CONFIRMADO:")
    print(f"- Tipo: String não fechada ({'single_quote' if in_single else 'double_quote'})")
    print(f"- Linha HTML renderizado: ~{len(lines)} (final do script)")
    print(f"- Último token válido: fim do arquivo")
    print(f"- Token ausente: {'aspas simples' if in_single else 'aspas duplas'} de fechamento")
    print(f"- Prova técnica: Estado final do parser mostra string aberta")
else:
    print()
    print("Não existe erro sintático. O erro é lógico ou de execução.")
