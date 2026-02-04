from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import CentralColaborador, CentralLog
from ..password_hash import generate_password_hash

bp = Blueprint("central", __name__, url_prefix="/central")

PERMISSION_LEVELS = [
    ("visualizador", "Visualizador"),
    ("operador", "Operador"),
    ("gerente", "Gerente"),
    ("desenvolvedor", "Desenvolvedor"),
]

PERMISSION_RANK = {
    "visualizador": 1,
    "operador": 2,
    "gerente": 3,
    "desenvolvedor": 4,
}


def _current_actor_level() -> str:
    if current_user.nivel == "DEV":
        return "desenvolvedor"
    if current_user.nivel == "admin":
        return "gerente"
    return "visualizador"


def _can_assign_permission(target_level: str) -> bool:
    actor_level = _current_actor_level()
    if actor_level == "visualizador":
        return False
    return PERMISSION_RANK.get(actor_level, 0) >= PERMISSION_RANK.get(target_level, 0)


def _log_action(action: str, target: CentralColaborador | None, details: str | None = None) -> None:
    entry = CentralLog(
        action=action,
        actor=(current_user.nome or current_user.username),
        target_id=(target.id if target else None),
        target_nome=(target.nome if target else None),
        details=details,
        created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    db.session.add(entry)


@bp.route("/")
@login_required
def index():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado. Apenas Administradores.", "danger")
        return redirect(url_for("home.index"))

    colaboradores = CentralColaborador.query.order_by(CentralColaborador.nome.asc()).all()
    logs = CentralLog.query.order_by(CentralLog.created_at.desc()).limit(50).all()

    total = len(colaboradores)
    ativos = len([c for c in colaboradores if c.ativo])
    desenvolvedores = len([c for c in colaboradores if c.permissao == "desenvolvedor"])

    return render_template(
        "central.html",
        colaboradores=colaboradores,
        logs=logs,
        total_colaboradores=total,
        total_ativos=ativos,
        total_devs=desenvolvedores,
        permission_levels=PERMISSION_LEVELS,
        actor_level=_current_actor_level(),
    )


@bp.route("/colaborador/novo", methods=["POST"])
@login_required
def create():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("central.index"))

    nome = (request.form.get("nome") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    cargo = (request.form.get("cargo") or "").strip()
    setor = (request.form.get("setor") or "").strip()
    permissao = (request.form.get("permissao") or "visualizador").strip()
    ativo = (request.form.get("ativo") or "1").strip() == "1"
    senha = (request.form.get("senha") or "").strip()

    if not nome or not username:
        flash("Nome e usuário são obrigatórios.", "warning")
        return redirect(url_for("central.index"))

    if permissao not in PERMISSION_RANK:
        permissao = "visualizador"

    if not _can_assign_permission(permissao):
        flash("Você não pode atribuir essa permissão.", "danger")
        return redirect(url_for("central.index"))

    if CentralColaborador.query.filter_by(username=username).first():
        flash("Usuário já existe na Central.", "warning")
        return redirect(url_for("central.index"))

    password_hash = generate_password_hash(senha) if senha else None

    colaborador = CentralColaborador(
        nome=nome,
        username=username,
        email=email or None,
        cargo=cargo or None,
        setor=setor or None,
        permissao=permissao,
        ativo=ativo,
        password_hash=password_hash,
        created_by=(current_user.nome or current_user.username),
    )

    db.session.add(colaborador)
    _log_action("criar", colaborador, details=f"Permissão {permissao}")
    db.session.commit()

    flash("Colaborador criado com sucesso.", "success")
    return redirect(url_for("central.index"))


@bp.route("/colaborador/<int:colab_id>/editar", methods=["POST"])
@login_required
def edit(colab_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("central.index"))

    colaborador = CentralColaborador.query.get_or_404(colab_id)

    colaborador.nome = (request.form.get("nome") or colaborador.nome).strip()
    colaborador.email = (request.form.get("email") or "").strip() or None
    colaborador.cargo = (request.form.get("cargo") or "").strip() or None
    colaborador.setor = (request.form.get("setor") or "").strip() or None
    colaborador.ativo = (request.form.get("ativo") or "1").strip() == "1"
    colaborador.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    colaborador.updated_by = current_user.nome or current_user.username

    _log_action("editar", colaborador)
    db.session.commit()

    flash("Colaborador atualizado.", "success")
    return redirect(url_for("central.index"))


@bp.route("/colaborador/<int:colab_id>/permissao", methods=["POST"])
@login_required
def update_permission(colab_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("central.index"))

    colaborador = CentralColaborador.query.get_or_404(colab_id)
    nova_permissao = (request.form.get("permissao") or "visualizador").strip()

    if nova_permissao not in PERMISSION_RANK:
        flash("Permissão inválida.", "warning")
        return redirect(url_for("central.index"))

    if not _can_assign_permission(nova_permissao):
        flash("Você não pode atribuir essa permissão.", "danger")
        return redirect(url_for("central.index"))

    colaborador.permissao = nova_permissao
    colaborador.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    colaborador.updated_by = current_user.nome or current_user.username

    _log_action("permissao", colaborador, details=f"Permissão {nova_permissao}")
    db.session.commit()

    flash("Permissão atualizada.", "success")
    return redirect(url_for("central.index"))


@bp.route("/colaborador/<int:colab_id>/senha", methods=["POST"])
@login_required
def update_password(colab_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("central.index"))

    colaborador = CentralColaborador.query.get_or_404(colab_id)
    senha = (request.form.get("senha") or "").strip()

    if not senha:
        flash("Informe a nova senha.", "warning")
        return redirect(url_for("central.index"))

    colaborador.password_hash = generate_password_hash(senha)
    colaborador.last_password_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    colaborador.updated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    colaborador.updated_by = current_user.nome or current_user.username

    _log_action("senha", colaborador, details="Senha atualizada")
    db.session.commit()

    flash("Senha atualizada.", "success")
    return redirect(url_for("central.index"))


@bp.route("/colaborador/<int:colab_id>/excluir", methods=["POST"])
@login_required
def delete(colab_id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Acesso negado.", "danger")
        return redirect(url_for("central.index"))

    colaborador = CentralColaborador.query.get_or_404(colab_id)

    _log_action("excluir", colaborador)
    db.session.delete(colaborador)
    db.session.commit()

    flash("Colaborador excluído.", "success")
    return redirect(url_for("central.index"))
