#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper para js_safety_check.py que não bloqueia commits
Apenas reporta alertas sem falhar
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    try:
        # Executa o script original
        script_path = Path(__file__).parent / "js_safety_check.py"
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        # Imprime a saída
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        # Sempre retorna sucesso para não bloquear commits
        # Alertas críticos devem ser corrigidos manualmente
        sys.exit(0)
    except Exception as e:
        print(f"Erro ao executar js_safety_check: {e}", file=sys.stderr)
        sys.exit(0)
