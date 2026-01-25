#!/usr/bin/env python3
"""
Script cron para envio automático do PDF de ciclos abertos via WhatsApp.
Executa todo sábado às 20h (horário de Brasília).

Uso:
    python cron/envio_ciclo_aberto.py

Configuração no crontab:
    0 20 * * 6 cd /opt/multimax && /opt/multimax/.venv/bin/python3 \\
        cron/envio_ciclo_aberto.py >> /var/log/multimax/cron_ciclo_aberto.log 2>&1
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Adicionar diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports após ajuste do path
from multimax import create_app, db  # noqa: E402
from multimax.models import SystemLog  # noqa: E402
from multimax.routes.ciclos import _gerar_pdf_ciclo_aberto_bytes  # noqa: E402
from multimax.services.whatsapp_gateway import get_auto_notifications_enabled, send_whatsapp_message  # noqa: E402


def log_system(event: str, details: str) -> None:
    """Registra ação no SystemLog."""
    try:
        log = SystemLog()
        log.origem = "cron_ciclo_aberto"
        log.evento = event
        log.detalhes = (details or "")[:255]
        log.usuario = "sistema"
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Erro ao registrar log: {e}", file=sys.stderr)
        try:
            db.session.rollback()
        except Exception:
            pass


def main():
    """Função principal do script."""
    # Criar contexto da aplicação Flask
    app = create_app()

    with app.app_context():
        try:
            # Verificar se é sábado
            now = datetime.now(ZoneInfo("America/Sao_Paulo"))
            dia_semana = now.weekday()  # 0=Segunda, 5=Sábado, 6=Domingo

            if dia_semana != 5:  # Se não for sábado
                print(f"Hoje não é sábado (dia da semana: {dia_semana}). Script abortado.")
                log_system("agendamento_ignorado", f"Execução ignorada: hoje é {now.strftime('%A')}, não sábado")
                return

            # Verificar se é aproximadamente 20h (aceitar janela de 1 hora)
            hora = now.hour
            if not (19 <= hora <= 20):
                print(f"Hora atual ({hora}h) fora da janela de execução (19h-20h). Script abortado.")
                log_system("agendamento_ignorado", f"Execução ignorada: hora atual {hora}h, esperado 19h-20h")
                return

            # Verificar se Bloco B (Controle Automático) está ativado
            if not get_auto_notifications_enabled():
                print("⚠️  Bloco B (Controle Automático) desativado. Envio automático suspenso.")
                log_system("agendamento_ignorado", "Execução ignorada: Bloco B (Controle Automático) desativado")
                return

            pdf_bytes, ciclo_id, mes_inicio = _gerar_pdf_ciclo_aberto_bytes()

            if pdf_bytes is None:
                print("Nenhum dado de ciclo aberto encontrado. Abortando.")
                log_system("envio_abortado", "Não há dados de ciclos abertos para enviar")
                return

            print(f"PDF gerado com sucesso (Ciclo {ciclo_id}, {mes_inicio})")

            # Preparar mensagem do WhatsApp
            mensagem = (
                "📊 *Registro de Ciclos - Colaboradores*\n\n"
                "Segue anexo do registro de ciclos de todos os colaboradores, por favor, "
                "confiram seus próprios dias trabalhados, horas extras e todas as informações "
                "antes da conclusão final de todos os ciclos.\n\n"
                "_[Essa mensagem é enviada por um sistema automatizado existente em www.multimax.tec.br]_"
            )

            # Enviar via WhatsApp com arquivo PDF
            print("Enviando PDF via WhatsApp...")
            # Usar data atual para montar nome do arquivo (mes_inicio é texto com nome do mês)
            now_date = datetime.now(ZoneInfo("America/Sao_Paulo"))
            nome_arquivo = f"Ciclos_{now_date.strftime('%m_%Y')}.pdf"
            sucesso, erro = send_whatsapp_message(
                message=mensagem,
                actor="sistema",
                origin="ciclo_aberto_cron",
                arquivo_bytes=pdf_bytes,
                nome_arquivo=nome_arquivo,
            )

            if sucesso:
                print("✅ PDF enviado com sucesso via WhatsApp")
                log_system(
                    "envio_automatico_sucesso",
                    f"PDF de ciclo aberto ({len(pdf_bytes)} bytes) enviado via cron (Ciclo {ciclo_id}, {mes_inicio})",
                )
            else:
                print(f"❌ Erro ao enviar PDF: {erro}")
                log_system("envio_automatico_falha", f"Erro ao enviar: {erro}")
                sys.exit(1)

        except Exception as e:
            import traceback

            error_msg = f"Erro na execução do cron: {str(e)}"
            print(f"❌ {error_msg}", file=sys.stderr)
            traceback.print_exc()
            log_system("erro_execucao", error_msg)
            sys.exit(1)


if __name__ == "__main__":
    main()
