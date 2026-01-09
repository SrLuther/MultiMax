#!/usr/bin/env python3
"""Script de diagnóstico para testar criação do app Flask"""
import sys
import traceback

print("=" * 60)
print("DIAGNÓSTICO DE INICIALIZAÇÃO DO FLASK APP")
print("=" * 60)

try:
    print("\n[1/5] Importando módulos base...")
    from flask import Flask
    print("[OK] Flask importado")
    
    print("\n[2/5] Importando multimax...")
    from multimax import db, create_app
    print("[OK] multimax importado")
    
    print("\n[3/5] Importando modelos...")
    from multimax.models import MonthStatus, JornadaArchive
    print("[OK] Modelos importados")
    print(f"  - MonthStatus tem payment_date: {hasattr(MonthStatus, 'payment_date')}")
    print(f"  - MonthStatus tem payment_amount: {hasattr(MonthStatus, 'payment_amount')}")
    print(f"  - JornadaArchive tem payment_date: {hasattr(JornadaArchive, 'payment_date')}")
    print(f"  - JornadaArchive tem payment_amount: {hasattr(JornadaArchive, 'payment_amount')}")
    
    print("\n[4/5] Importando rotas...")
    from multimax.routes import jornada, jornada_pdf
    print("[OK] Rotas importadas")
    
    print("\n[5/5] Criando aplicação Flask...")
    app = create_app()
    print("[OK] Aplicação criada com sucesso!")
    
    print("\n[TESTE] Verificando rotas registradas...")
    routes_jornada = [r.rule for r in app.url_map.iter_rules() if r.endpoint.startswith('jornada.')]
    print(f"[OK] {len(routes_jornada)} rotas de jornada registradas")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] TODOS OS TESTES PASSARAM")
    print("=" * 60)
    sys.exit(0)
    
except SyntaxError as e:
    print(f"\n[ERROR] ERRO DE SINTAXE:")
    print(f"  Arquivo: {e.filename}")
    print(f"  Linha: {e.lineno}")
    print(f"  Mensagem: {e.msg}")
    traceback.print_exc()
    sys.exit(1)
    
except ImportError as e:
    print(f"\n[ERROR] ERRO DE IMPORTAÇÃO:")
    print(f"  Módulo: {e.name}")
    print(f"  Mensagem: {str(e)}")
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print(f"\n[ERROR] ERRO INESPERADO:")
    print(f"  Tipo: {type(e).__name__}")
    print(f"  Mensagem: {str(e)}")
    traceback.print_exc()
    sys.exit(1)
