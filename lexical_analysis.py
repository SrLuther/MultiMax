#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Análise léxica completa do JavaScript"""

with open('templates/ciclos/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extrair JavaScript
script_start = content.find('<script>', content.find('{% block content'))
script_end = content.find('</script>', script_start)
js_code = content[script_start+8:script_end]

print("=" * 80)
print("ANÁLISE LÉXICA DO JAVASCRIPT")
print("=" * 80)
print(f"Tamanho: {len(js_code)} caracteres")
print(f"Linhas: {len(js_code.split(chr(10)))}")
print()

# Análise caractere por caractere
in_single = False
in_double = False
in_template = False
escape = False
open_braces = 0
open_parens = 0
open_brackets = 0

line_num = 1
char_pos = 0
last_valid_pos = 0
last_valid_line = 1

errors = []

for i, char in enumerate(js_code):
    if char == '\n':
        line_num += 1
        char_pos = 0
    else:
        char_pos += 1
    
    if escape:
        escape = False
        last_valid_pos = i
        last_valid_line = line_num
        continue
    
    if char == '\\':
        escape = True
        continue
    
    if not in_single and not in_double and not in_template:
        # Fora de strings
        if char == "'":
            in_single = True
        elif char == '"':
            in_double = True
        elif char == '`':
            in_template = True
        elif char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
            if open_braces < 0:
                errors.append({
                    'type': 'unbalanced_brace',
                    'line': line_num,
                    'pos': char_pos,
                    'char': char
                })
        elif char == '(':
            open_parens += 1
        elif char == ')':
            open_parens -= 1
            if open_parens < 0:
                errors.append({
                    'type': 'unbalanced_paren',
                    'line': line_num,
                    'pos': char_pos,
                    'char': char
                })
        elif char == '[':
            open_brackets += 1
        elif char == ']':
            open_brackets -= 1
            if open_brackets < 0:
                errors.append({
                    'type': 'unbalanced_bracket',
                    'line': line_num,
                    'pos': char_pos,
                    'char': char
                })
    else:
        # Dentro de string
        if char == "'" and in_single:
            in_single = False
        elif char == '"' and in_double:
            in_double = False
        elif char == '`' and in_template:
            in_template = False
    
    last_valid_pos = i
    last_valid_line = line_num

# Verificar strings não fechadas
if in_single:
    errors.append({
        'type': 'unclosed_string',
        'string_type': 'single_quote',
        'line': last_valid_line,
        'pos': char_pos
    })
if in_double:
    errors.append({
        'type': 'unclosed_string',
        'string_type': 'double_quote',
        'line': last_valid_line,
        'pos': char_pos
    })
if in_template:
    errors.append({
        'type': 'unclosed_string',
        'string_type': 'template_literal',
        'line': last_valid_line,
        'pos': char_pos
    })

# Verificar balanceamento
if open_braces != 0:
    errors.append({
        'type': 'unbalanced_braces',
        'count': open_braces
    })
if open_parens != 0:
    errors.append({
        'type': 'unbalanced_parens',
        'count': open_parens
    })
if open_brackets != 0:
    errors.append({
        'type': 'unbalanced_brackets',
        'count': open_brackets
    })

print("RESULTADO DA ANÁLISE:")
print("-" * 80)
print(f"Última posição válida: {last_valid_pos}/{len(js_code)}")
print(f"Última linha válida: {last_valid_line}")
print(f"Chaves balanceadas: {open_braces == 0} (diff: {open_braces})")
print(f"Parênteses balanceados: {open_parens == 0} (diff: {open_parens})")
print(f"Colchetes balanceados: {open_brackets == 0} (diff: {open_brackets})")
print(f"String single aberta: {in_single}")
print(f"String double aberta: {in_double}")
print(f"Template literal aberto: {in_template}")
print()

if errors:
    print("ERRO LEXICAL CONFIRMADO:")
    print("-" * 80)
    for error in errors:
        if error['type'] == 'unclosed_string':
            print(f"- Tipo: String não fechada ({error['string_type']})")
            print(f"- Linha HTML renderizado: ~{error['line']} (aproximadamente linha {1547 + error['line']} do arquivo fonte)")
            print(f"- Último token válido: fim da string (posição {error['pos']})")
            print(f"- Token ausente: {'aspas simples' if error['string_type'] == 'single_quote' else 'aspas duplas' if error['string_type'] == 'double_quote' else 'backtick'} de fechamento")
            print(f"- Prova técnica: Parser léxico detectou string aberta no final do arquivo")
        elif error['type'].startswith('unbalanced'):
            print(f"- Tipo: {error['type']}")
            print(f"- Linha HTML renderizado: ~{error.get('line', 'N/A')}")
            print(f"- Último token válido: {error.get('char', 'N/A')}")
            print(f"- Token ausente: {'chave de fechamento' if 'brace' in error['type'] else 'parêntese de fechamento' if 'paren' in error['type'] else 'colchete de fechamento'}")
            print(f"- Prova técnica: Balanceamento incorreto ({error.get('count', 0)} diferença)")
        print()
else:
    print("Não existe erro sintático. O erro é lógico ou de execução.")

# Mostrar contexto das linhas com Jinja2
print("=" * 80)
print("LINHAS COM JINJA2 EM STRINGS:")
print("-" * 80)
lines = js_code.split('\n')
for i, line in enumerate(lines, 1548):
    if "'{{" in line or '"{{' in line:
        print(f"Linha {i}: {repr(line)}")
