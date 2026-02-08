"""Create initial tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_ativo", "users", ["ativo"])

    # Create colaboradores table
    op.create_table(
        "colaboradores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=False),
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("departamento", sa.String(100), nullable=True),
        sa.Column("funcao", sa.String(100), nullable=True),
        sa.Column("data_admissao", sa.Date(), nullable=True),
        sa.Column("data_demissao", sa.Date(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("horas_ciclo", sa.Float(), nullable=False, server_default="0"),
        sa.Column("saldo_horas", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_colaboradores_nome", "colaboradores", ["nome"])
    op.create_index("ix_colaboradores_cpf", "colaboradores", ["cpf"], unique=True)
    op.create_index("ix_colaboradores_ativo", "colaboradores", ["ativo"])

    # Create ciclos_semanais table
    op.create_table(
        "ciclos_semanais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_ciclo", sa.Integer(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_ciclo", name="uq_numero_ciclo"),
    )
    op.create_index("ix_ciclos_semanais_numero_ciclo", "ciclos_semanais", ["numero_ciclo"])
    op.create_index("ix_ciclos_semanais_data_inicio", "ciclos_semanais", ["data_inicio"])

    # Create ciclos_mensais table
    op.create_table(
        "ciclos_mensais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("fechado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mes", "ano", name="uq_ciclo_mes_ano"),
    )

    # Create historico_colaborador table
    op.create_table(
        "historico_colaborador",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("colaborador_id", sa.Integer(), nullable=False),
        sa.Column("ciclo_semanal_id", sa.Integer(), nullable=False),
        sa.Column("horas_trabalhadas", sa.Float(), nullable=False, server_default="0"),
        sa.Column("horas_falta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("horas_atraso", sa.Float(), nullable=False, server_default="0"),
        sa.Column("horas_extra", sa.Float(), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["colaborador_id"],
            ["colaboradores.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ciclo_semanal_id"],
            ["ciclos_semanais.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historico_colaborador_colaborador_id", "historico_colaborador", ["colaborador_id"])
    op.create_index("ix_historico_colaborador_ciclo_semanal_id", "historico_colaborador", ["ciclo_semanal_id"])

    # Create whatsapp_config table
    op.create_table(
        "whatsapp_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(100), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave", name="uq_whatsapp_config_chave"),
    )
    op.create_index("ix_whatsapp_config_chave", "whatsapp_config", ["chave"])

    # Create whatsapp_messages table
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telefone_destino", sa.String(20), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("resposta_whatsapp", sa.Text(), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("ciclo_semanal_id", sa.Integer(), nullable=True),
        sa.Column("colaborador_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("enviado_em", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whatsapp_messages_telefone_destino", "whatsapp_messages", ["telefone_destino"])
    op.create_index("ix_whatsapp_messages_status", "whatsapp_messages", ["status"])
    op.create_index("ix_whatsapp_messages_tipo", "whatsapp_messages", ["tipo"])
    op.create_index("ix_whatsapp_messages_data", "whatsapp_messages", ["created_at"])

    # Create log_erros table
    op.create_table(
        "log_erros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("rota", sa.String(255), nullable=True),
        sa.Column("usuario", sa.String(100), nullable=True),
        sa.Column("container", sa.String(100), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_erros_nivel", "log_erros", ["nivel"])
    op.create_index("ix_log_erros_created_at", "log_erros", ["created_at"])
    op.create_index("ix_log_erros_request_id", "log_erros", ["request_id"])
    op.create_index("ix_log_erros_nivel_data", "log_erros", ["nivel", "created_at"])

    # Create log_whatsapp table
    op.create_table(
        "log_whatsapp",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("acao", sa.String(100), nullable=False),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.Column("resposta_api", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_whatsapp_acao", "log_whatsapp", ["acao"])
    op.create_index("ix_log_whatsapp_created_at", "log_whatsapp", ["created_at"])

    # Create log_deploy table
    op.create_table(
        "log_deploy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.String(50), nullable=False),
        sa.Column("evento", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.Column("container", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_deploy_versao", "log_deploy", ["versao"])
    op.create_index("ix_log_deploy_created_at", "log_deploy", ["created_at"])

    # Create heartbeat table
    op.create_table(
        "heartbeat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("container", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="online"),
        sa.Column("versao", sa.String(50), nullable=True),
        sa.Column("uptime_segundos", sa.Integer(), nullable=True),
        sa.Column("cpu_percent", sa.String(20), nullable=True),
        sa.Column("memoria_mb", sa.Integer(), nullable=True),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_container", "heartbeat", ["container"])
    op.create_index("ix_heartbeat_created_at", "heartbeat", ["created_at"])
    op.create_index("ix_heartbeat_container_data", "heartbeat", ["container", "created_at"])


def downgrade() -> None:
    op.drop_table("heartbeat")
    op.drop_table("log_deploy")
    op.drop_table("log_whatsapp")
    op.drop_table("log_erros")
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_config")
    op.drop_table("historico_colaborador")
    op.drop_table("ciclos_mensais")
    op.drop_table("ciclos_semanais")
    op.drop_table("colaboradores")
    op.drop_table("users")
