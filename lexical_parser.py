#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser Léxico para JavaScript
Analisa o código JavaScript caractere por caractere para identificar erros sintáticos
"""

def analyze_javascript(js_code):
    """Analisa JavaScript e identifica erros léxicos"""
    in_single_quote = False
    in_double_quote = False
    in_template_literal = False
    escape_next = False
    
    open_braces = 0
    open_parens = 0
    open_brackets = 0
    
    lines = js_code.split('\n')
    line_num = 1
    char_pos = 0
    
    errors = []
    last_valid_pos = 0
    last_valid_line = 1
    
    for i, char in enumerate(js_code):
        if char == '\n':
            line_num += 1
            char_pos = 0
        else:
            char_pos += 1
        
        # Tratar escape
        if escape_next:
            escape_next = False
            last_valid_pos = i
            last_valid_line = line_num
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        # Verificar strings
        if not in_single_quote and not in_double_quote and not in_template_literal:
            # Fora de strings - verificar delimitadores
            if char == "'":
                in_single_quote = True
            elif char == '"':
                in_double_quote = True
            elif char == '`':
                in_template_literal = True
            elif char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
                if open_braces < 0:
                    errors.append({
                        'type': 'unbalanced_brace',
                        'line': line_num,
                        'pos': char_pos,
                        'char': char,
                        'message': 'Chave fechada sem abertura correspondente'
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
                        'char': char,
                        'message': 'Parêntese fechado sem abertura correspondente'
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
                        'char': char,
                        'message': 'Colchete fechado sem abertura correspondente'
                    })
        else:
            # Dentro de string - verificar fechamento
            if char == "'" and in_single_quote:
                in_single_quote = False
            elif char == '"' and in_double_quote:
                in_double_quote = False
            elif char == '`' and in_template_literal:
                in_template_literal = False
        
        last_valid_pos = i
        last_valid_line = line_num
    
    # Verificar strings não fechadas
    if in_single_quote:
        errors.append({
            'type': 'unclosed_string',
            'string_type': 'single_quote',
            'line': last_valid_line,
            'pos': char_pos,
            'message': 'String com aspas simples não fechada'
        })
    if in_double_quote:
        errors.append({
            'type': 'unclosed_string',
            'string_type': 'double_quote',
            'line': last_valid_line,
            'pos': char_pos,
            'message': 'String com aspas duplas não fechada'
        })
    if in_template_literal:
        errors.append({
            'type': 'unclosed_string',
            'string_type': 'template_literal',
            'line': last_valid_line,
            'pos': char_pos,
            'message': 'Template literal não fechado'
        })
    
    # Verificar balanceamento
    if open_braces != 0:
        errors.append({
            'type': 'unbalanced_braces',
            'count': open_braces,
            'message': f'Chaves não balanceadas: {open_braces} abertas sem fechar'
        })
    if open_parens != 0:
        errors.append({
            'type': 'unbalanced_parens',
            'count': open_parens,
            'message': f'Parênteses não balanceados: {open_parens} abertos sem fechar'
        })
    if open_brackets != 0:
        errors.append({
            'type': 'unbalanced_brackets',
            'count': open_brackets,
            'message': f'Colchetes não balanceados: {open_brackets} abertos sem fechar'
        })
    
    return {
        'errors': errors,
        'last_valid_pos': last_valid_pos,
        'last_valid_line': last_valid_line,
        'total_chars': len(js_code),
        'total_lines': len(lines),
        'in_string': in_single_quote or in_double_quote or in_template_literal
    }

if __name__ == '__main__':
    with open('temp_js_lexical.js', 'r', encoding='utf-8') as f:
        js_code = f.read()
    
    result = analyze_javascript(js_code)
    
    print("=" * 80)
    print("ANÁLISE LÉXICA DO JAVASCRIPT")
    print("=" * 80)
    print(f"Total de caracteres: {result['total_chars']}")
    print(f"Total de linhas: {result['total_lines']}")
    print(f"Última posição válida: {result['last_valid_pos']}/{result['total_chars']}")
    print(f"Última linha válida: {result['last_valid_line']}")
    print(f"Em string: {result['in_string']}")
    print()
    
    if result['errors']:
        print("ERROS ENCONTRADOS:")
        print("-" * 80)
        for error in result['errors']:
            print(f"Tipo: {error['type']}")
            if 'line' in error:
                print(f"Linha: {error['line']}")
            if 'pos' in error:
                print(f"Posição: {error['pos']}")
            print(f"Mensagem: {error['message']}")
            print()
    else:
        print("NENHUM ERRO LÉXICO ENCONTRADO")
        print("O JavaScript está sintaticamente correto do ponto de vista léxico.")
    
    # Mostrar contexto ao redor da última posição válida
    if result['last_valid_pos'] < len(js_code) - 1:
        start = max(0, result['last_valid_pos'] - 100)
        end = min(len(js_code), result['last_valid_pos'] + 100)
        print("=" * 80)
        print("CONTEXTO AO REDOR DA ÚLTIMA POSIÇÃO VÁLIDA:")
        print("-" * 80)
        context = js_code[start:end]
        print(repr(context))
        print()
        print("Linhas ao redor:")
        lines = js_code.split('\n')
        start_line = max(0, result['last_valid_line'] - 3)
        end_line = min(len(lines), result['last_valid_line'] + 3)
        for i in range(start_line, end_line):
            marker = ">>> " if i == result['last_valid_line'] - 1 else "    "
            print(f"{marker}{i+1:4d}: {lines[i]}")
