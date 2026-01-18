from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import db
from ..module_registry import get_active_module_labels
from ..models import AppSetting as AppSettingModel
from ..models import CleaningHistory, CleaningTask, Collaborator
from ..models import Historico as HistoricoModel
from ..models import Holiday, MeatReception, NotificationRead, Produto, SystemLog, TimeOffRecord

bp = Blueprint("home", __name__, url_prefix="/home")


def _get_last_update_date_from_changelog() -> str:
    """
    Retorna apenas a data (DD/MM/AAAA) do topo do CHANGELOG.md.
    Não renderiza nem replica o conteúdo do changelog (apenas metadado).
    """
    try:
        import re
        from pathlib import Path

        p = Path("CHANGELOG.md")
        if not p.exists():
            return datetime.now().strftime("%d/%m/%Y")
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lines:
            return datetime.now().strftime("%d/%m/%Y")
        first = (lines[0] or "").strip()
        m = re.match(r"^##\s*\[[^\]]+\]\s*-\s*(\d{4}-\d{2}-\d{2})\s*$", first)
        if m:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    return datetime.now().strftime("%d/%m/%Y")


def get_dashboard_metrics():
    """Retorna métricas para o dashboard"""
    metrics = {
        "total_produtos": 0,
        "produtos_baixo_estoque": 0,
        "tarefas_atrasadas": 0,
        "tarefas_proximas": 0,
        "movimentacoes_hoje": 0,
        "colaboradores_ativos": 0,
        "entradas_mes": 0,
        "saidas_mes": 0,
    }
    try:
        metrics["total_produtos"] = Produto.query.count()
        metrics["produtos_baixo_estoque"] = Produto.query.filter(
            Produto.estoque_minimo > 0, Produto.quantidade <= Produto.estoque_minimo
        ).count()
        today = date.today()
        metrics["tarefas_atrasadas"] = CleaningTask.query.filter(CleaningTask.proxima_data < today).count()
        horizon = today + timedelta(days=7)
        metrics["tarefas_proximas"] = CleaningTask.query.filter(
            CleaningTask.proxima_data >= today, CleaningTask.proxima_data <= horizon
        ).count()
        inicio_hoje = datetime.combine(today, datetime.min.time())
        metrics["movimentacoes_hoje"] = HistoricoModel.query.filter(HistoricoModel.data >= inicio_hoje).count()
        metrics["colaboradores_ativos"] = Collaborator.query.filter_by(active=True).count()
        inicio_mes = date(today.year, today.month, 1)
        inicio_mes_dt = datetime.combine(inicio_mes, datetime.min.time())
        entradas = (
            db.session.query(func.sum(HistoricoModel.quantidade))
            .filter(HistoricoModel.data >= inicio_mes_dt, func.lower(HistoricoModel.action) == "entrada")
            .scalar()
        )
        saidas = (
            db.session.query(func.sum(HistoricoModel.quantidade))
            .filter(HistoricoModel.data >= inicio_mes_dt, func.lower(HistoricoModel.action) == "saida")
            .scalar()
        )
        metrics["entradas_mes"] = entradas or 0
        metrics["saidas_mes"] = saidas or 0
    except Exception:
        pass
    return metrics


def get_stock_chart_data():
    """Retorna dados para o gráfico de movimentações dos últimos 7 dias - otimizado"""
    data = {"labels": [], "entradas": [], "saidas": []}
    try:
        today = date.today()
        inicio_7_dias = datetime.combine(today - timedelta(days=6), datetime.min.time())
        fim_hoje = datetime.combine(today, datetime.max.time())

        # Uma única query agrupada ao invés de 14 queries (2 por dia x 7 dias)
        resultados = (
            db.session.query(
                func.date(HistoricoModel.data).label("dia"),
                func.lower(HistoricoModel.action).label("acao"),
                func.coalesce(func.sum(HistoricoModel.quantidade), 0).label("total"),
            )
            .filter(
                HistoricoModel.data >= inicio_7_dias,
                HistoricoModel.data <= fim_hoje,
                func.lower(HistoricoModel.action).in_(["entrada", "saida"]),
            )
            .group_by(func.date(HistoricoModel.data), func.lower(HistoricoModel.action))
            .all()
        )

        # Criar dicionário para lookup rápido
        dados_dict = {}
        for r in resultados:
            dia_str = r.dia.strftime("%d/%m")
            if dia_str not in dados_dict:
                dados_dict[dia_str] = {"entradas": 0, "saidas": 0}
            if r.acao == "entrada":
                dados_dict[dia_str]["entradas"] = int(r.total or 0)
            elif r.acao == "saida":
                dados_dict[dia_str]["saidas"] = int(r.total or 0)

        # Preencher todos os dias na ordem correta
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            dia_str = d.strftime("%d/%m")
            dados = dados_dict.get(dia_str, {"entradas": 0, "saidas": 0})
            data["labels"].append(dia_str)
            data["entradas"].append(dados["entradas"])
            data["saidas"].append(dados["saidas"])
    except Exception:
        pass
    return data


def get_low_stock_products():
    """Retorna produtos com estoque baixo para o gráfico"""
    products = []
    try:
        low = (
            Produto.query.filter(Produto.estoque_minimo > 0, Produto.quantidade <= Produto.estoque_minimo)
            .order_by(Produto.quantidade.asc())
            .limit(10)
            .all()
        )
        for p in low:
            products.append(
                {
                    "nome": p.nome[:20] + "..." if len(p.nome) > 20 else p.nome,
                    "quantidade": p.quantidade,
                    "minimo": p.estoque_minimo,
                }
            )
    except Exception:
        pass
    return products


@bp.after_app_request
def _home_no_cache(response):
    try:
        if request.path.startswith("/home"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    except Exception:
        pass
    return response


@bp.route("/", strict_slashes=False)
def index():
    """Redireciona para o dashboard público"""
    return redirect(url_for("home.dashboard_public"))


@bp.route("/dashboard", strict_slashes=False)
def dashboard_public():
    """Dashboard público acessível sem login"""
    # Se já está autenticado, redireciona para o dashboard completo
    if current_user.is_authenticated:
        return redirect(url_for("home.dashboard_authenticated"))

    db_diag = None
    modules_active: list[str] = []
    last_update_date = datetime.now().strftime("%d/%m/%Y")
    git_version = "dev"
    try:
        from flask import current_app

        modules_active = get_active_module_labels(current_app.blueprints.keys())
        last_update_date = _get_last_update_date_from_changelog()
        git_version = current_app.config.get("APP_VERSION_RESOLVED", "dev")
    except Exception:
        pass
    try:
        from flask import current_app
        from sqlalchemy import text

        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        host = None
        try:
            if "://" in uri:
                after = uri.split("://", 1)[1]
                hostpart = after.split("@", 1)[1] if "@" in after else after
                host = hostpart.split("/", 1)[0]
        except Exception:
            host = None
        ok = True
        err = ""
        try:
            db.session.execute(text("select 1"))
        except Exception as e:
            ok = False
            err = str(e)
            try:
                db.session.rollback()
            except Exception:
                pass
        db_diag = {"ok": ok, "uri": uri, "host": host, "err": err}
    except Exception:
        db_diag = {"ok": False, "uri": "", "host": None, "err": ""}

    # Dashboard público mostra apenas informações básicas
    return render_template(
        "dashboard_public.html",
        active_page="dashboard",
        events=[],
        mural_html="",
        mural_text="",
        notifications=[],
        next_holiday=None,
        db_diag=db_diag,
        modules_active=modules_active,
        last_update_date=last_update_date,
        git_version=git_version,
    )


@bp.route("/dashboard/full", strict_slashes=False)
@login_required
def dashboard_authenticated():
    """Dashboard completo para usuários autenticados"""
    db_diag = None
    modules_active: list[str] = []
    last_update_date = datetime.now().strftime("%d/%m/%Y")
    git_version = "dev"
    try:
        from flask import current_app

        modules_active = get_active_module_labels(current_app.blueprints.keys())
        last_update_date = _get_last_update_date_from_changelog()
        git_version = current_app.config.get("APP_VERSION_RESOLVED", "dev")
    except Exception:
        pass
    try:
        from flask import current_app
        from sqlalchemy import text

        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        host = None
        try:
            if "://" in uri:
                after = uri.split("://", 1)[1]
                hostpart = after.split("@", 1)[1] if "@" in after else after
                host = hostpart.split("/", 1)[0]
        except Exception:
            host = None
        ok = True
        err = ""
        try:
            db.session.execute(text("select 1"))
        except Exception as e:
            ok = False
            err = str(e)
            try:
                db.session.rollback()
            except Exception:
                pass
        db_diag = {"ok": ok, "uri": uri, "host": host, "err": err}
    except Exception:
        db_diag = {"ok": False, "uri": "", "host": None, "err": ""}
    events = []
    try:
        from flask import current_app

        if not db_diag.get("ok", True) or not current_app.config.get("DB_OK", True):
            return render_template(
                "home.html",
                active_page="home",
                events=[],
                mural_html="",
                mural_text="",
                notifications=[],
                next_holiday=None,
                db_diag=db_diag,
                modules_active=modules_active,
                last_update_date=last_update_date,
                git_version=git_version,
            )
    except Exception:
        pass
    # Estoque (Histórico)
    try:
        hist = HistoricoModel.query.order_by(HistoricoModel.data.desc()).limit(100).all()
        for h in hist:
            t = "Entrada" if (h.action or "").lower() == "entrada" else "Saída"
            qty = h.quantidade or 0
            sign = "+" if t == "Entrada" else "-"
            events.append(
                {
                    "title": f"📦 {t}: {h.product_name} {sign}{qty}",
                    "start": (h.data or datetime.utcnow()).isoformat(),
                    "color": "#198754",
                    "url": url_for("estoque.editar", id=h.product_id) if h.product_id else None,
                }
            )
    except Exception:
        pass
    try:
        from datetime import date, timedelta

        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        ref_monday_setting = AppSettingModel.query.filter_by(key="rodizio_ref_monday").first()
        ref_open_setting = AppSettingModel.query.filter_by(key="rodizio_open_team_ref").first()
        ref_monday = None
        if ref_monday_setting and (ref_monday_setting.value or "").strip():
            try:
                ref_monday = datetime.strptime(ref_monday_setting.value.strip(), "%Y-%m-%d").date()
            except Exception:
                ref_monday = None
        if not ref_monday:
            if not ref_monday_setting:
                ref_monday_setting = AppSettingModel()
                ref_monday_setting.key = "rodizio_ref_monday"
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime("%Y-%m-%d")
            db.session.commit()
            ref_monday = current_monday
        open_ref = ref_open_setting.value.strip() if ref_open_setting and ref_open_setting.value else "1"
        if open_ref not in ("1", "2"):
            open_ref = "1"
        if ref_monday < current_monday:
            weeks_diff = (current_monday - ref_monday).days // 7
            if weeks_diff % 2 == 1:
                open_ref = "2" if open_ref == "1" else "1"
            ref_monday = current_monday
            if not ref_monday_setting:
                ref_monday_setting = AppSettingModel()
                ref_monday_setting.key = "rodizio_ref_monday"
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime("%Y-%m-%d")
            if not ref_open_setting:
                ref_open_setting = AppSettingModel()
                ref_open_setting.key = "rodizio_open_team_ref"
                db.session.add(ref_open_setting)
            ref_open_setting.value = open_ref
            db.session.commit()
        for i in range(5):
            ws = current_monday + timedelta(days=7 * i)
            we = ws + timedelta(days=5)
            open_team = open_ref if (i % 2 == 0) else ("2" if open_ref == "1" else "1")
            close_team = "2" if open_team == "1" else "1"
            d = ws
            while d <= we:
                events.append(
                    {
                        "title": f"EQUIPE ABERTURA '{open_team}'",
                        "start": d.strftime("%Y-%m-%d"),
                        "color": "#198754",
                        "url": url_for("colaboradores.escala"),
                        "kind": "rodizio-open",
                        "team": open_team,
                    }
                )
                events.append(
                    {
                        "title": f"EQUIPE FECHAMENTO '{close_team}'",
                        "start": d.strftime("%Y-%m-%d"),
                        "color": "#157347",
                        "url": url_for("colaboradores.escala"),
                        "kind": "rodizio-close",
                        "team": close_team,
                    }
                )
                d = d + timedelta(days=1)
            sunday = ws + timedelta(days=6)
            try:
                # Otimização: buscar todos os settings de domingo de uma vez
                domingo_keys = ["domingo_ref_sunday", "domingo_team_ref", "domingo_manha_team"]
                domingo_settings = {
                    s.key: s for s in AppSettingModel.query.filter(AppSettingModel.key.in_(domingo_keys)).all()
                }
                sun_ref_setting = domingo_settings.get("domingo_ref_sunday")
                sun_team_setting = domingo_settings.get("domingo_team_ref")
                base_team = sun_team_setting.value.strip() if sun_team_setting and sun_team_setting.value else None
                if base_team not in ("1", "2"):
                    # fallback para configuração antiga, se existir
                    sun_m = domingo_settings.get("domingo_manha_team")
                    base_team = sun_m.value.strip() if sun_m and sun_m.value else "1"
                    if base_team not in ("1", "2"):
                        base_team = "1"
                    if not sun_team_setting:
                        sun_team_setting = AppSettingModel()
                        sun_team_setting.key = "domingo_team_ref"
                        db.session.add(sun_team_setting)
                    sun_team_setting.value = base_team
                # definir domingo de referência se não existir
                ref_sunday = None
                if sun_ref_setting and (sun_ref_setting.value or "").strip():
                    try:
                        ref_sunday = datetime.strptime(sun_ref_setting.value.strip(), "%Y-%m-%d").date()
                    except Exception:
                        ref_sunday = None
                if not sun_ref_setting:
                    last_sunday = current_monday - timedelta(days=1)
                    if not sun_ref_setting:
                        sun_ref_setting = AppSettingModel()
                        sun_ref_setting.key = "domingo_ref_sunday"
                        db.session.add(sun_ref_setting)
                    sun_ref_setting.value = last_sunday.strftime("%Y-%m-%d")
                    db.session.commit()
                    ref_sunday = last_sunday
                # calcular equipe do domingo pelo número de semanas desde a referência
                weeks_since_ref = 0
                try:
                    if ref_sunday:
                        weeks_since_ref = max(0, (sunday - ref_sunday).days // 7)
                except Exception:
                    weeks_since_ref = 0
                domingo_val = base_team if (weeks_since_ref % 2 == 0) else ("2" if base_team == "1" else "1")
                events.append(
                    {
                        "title": f"DOMINGO EQUIPE '{domingo_val}' (5h–13h)",
                        "start": sunday.strftime("%Y-%m-%d"),
                        "color": "#fd7e14",
                        "url": url_for("colaboradores.escala"),
                        "kind": "rodizio-sunday",
                        "team": domingo_val,
                    }
                )
            except Exception:
                pass
    except Exception:
        pass
    try:
        from datetime import date, timedelta

        today = date.today()
        horizon = today + timedelta(days=45)
        tasks = (
            CleaningTask.query.filter(CleaningTask.proxima_data.isnot(None), CleaningTask.proxima_data <= horizon)
            .order_by(CleaningTask.proxima_data.asc())
            .limit(60)
            .all()
        )
        for t in tasks:
            if t.proxima_data:
                events.append(
                    {
                        "title": f"🧼 Limpeza prevista: {t.nome_limpeza}",
                        "start": t.proxima_data.strftime("%Y-%m-%d"),
                        "color": "#20c997",
                        "url": url_for("cronograma.cronograma"),
                    }
                )
    except Exception:
        pass
    # Limpeza concluída
    try:
        ch = CleaningHistory.query.order_by(CleaningHistory.data_conclusao.desc()).limit(50).all()
        for c in ch:
            events.append(
                {
                    "title": f"✅ Limpeza concluída: {c.nome_limpeza}",
                    "start": (c.data_conclusao or datetime.utcnow()).isoformat(),
                    "color": "#198754",
                    "url": url_for("cronograma.cronograma"),
                }
            )
    except Exception:
        pass
    # Carnes
    try:
        recs = MeatReception.query.order_by(MeatReception.data.desc()).limit(50).all()
        for r in recs:
            events.append(
                {
                    "title": f"🥩 Recepção de carnes: {r.fornecedor} ({r.tipo})",
                    "start": (r.data or datetime.utcnow()).isoformat(),
                    "color": "#6c757d",
                    "url": url_for("carnes.index"),
                }
            )
    except Exception:
        pass
    # Sistema
    try:
        logs = SystemLog.query.order_by(SystemLog.data.desc()).limit(50).all()
        for lg in logs:
            events.append(
                {
                    "title": f"⚙️ {lg.origem}: {lg.evento}",
                    "start": (lg.data or datetime.utcnow()).isoformat(),
                    "color": "#6610f2",
                    "url": url_for("usuarios.monitor") if lg.origem in ("Usuarios", "Sistema") else None,
                }
            )
    except Exception:
        pass
    # Feriados
    try:
        from datetime import date as _date

        def _fixed(mm: int, dd: int, yy: int):
            return _date(yy, mm, dd).strftime("%Y-%m-%d")

        def _easter_date(yy: int):
            a = yy % 19
            b = yy // 100
            c = yy % 100
            d = (19 * a + b - (b // 4) - ((b + 8) // 25) + 15) % 30
            e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
            m = (d + e + 114) // 31
            p = ((d + e + 114) % 31) + 1
            return _date(yy, m, p)

        def _movable_holidays(yy: int):
            from datetime import timedelta as _td

            easter = _easter_date(yy)
            carnival = easter - _td(days=47)
            good_friday = easter - _td(days=2)
            corpus_christi = easter + _td(days=60)
            return [
                {"title": "🎉 Carnaval", "start": carnival.strftime("%Y-%m-%d"), "color": "#dc3545", "kind": "holiday"},
                {
                    "title": "✝️ Paixão de Cristo",
                    "start": good_friday.strftime("%Y-%m-%d"),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "✝️ Corpus Christi",
                    "start": corpus_christi.strftime("%Y-%m-%d"),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
            ]

        def _federal_holidays(yy: int):
            return [
                {
                    "title": "🎉 Feriado Nacional: Confraternização Universal",
                    "start": _fixed(1, 1, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Tiradentes",
                    "start": _fixed(4, 21, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Dia do Trabalho",
                    "start": _fixed(5, 1, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Independência do Brasil",
                    "start": _fixed(9, 7, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Nossa Senhora Aparecida",
                    "start": _fixed(10, 12, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Finados",
                    "start": _fixed(11, 2, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Proclamação da República",
                    "start": _fixed(11, 15, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
                {
                    "title": "🎉 Feriado Nacional: Natal",
                    "start": _fixed(12, 25, yy),
                    "color": "#dc3545",
                    "kind": "holiday",
                },
            ]

        years = []
        try:
            y0 = _date.today().year
            years = [y0 - 1, y0, y0 + 1]
        except Exception:
            years = []
        hols = []
        for yy in years:
            hols.extend(_federal_holidays(yy))
            hols.extend(_movable_holidays(yy))
        events.extend(hols)
    except Exception:
        pass
    try:
        credits = (
            TimeOffRecord.query.filter(TimeOffRecord.record_type == "folga_adicional")
            .order_by(TimeOffRecord.date.desc())
            .limit(100)
            .all()
        )
        for lc in credits:
            events.append(
                {
                    "title": f"🏖️ Crédito de Folga: +{lc.days}",
                    "start": lc.date.strftime("%Y-%m-%d"),
                    "color": "#ffa94d",
                    "url": url_for("colaboradores.escala"),
                }
            )
    except Exception:
        pass

    mural_text = ""
    try:
        s = AppSettingModel.query.filter_by(key="mural_text").first()
        mural_text = (s.value or "") if s else ""
    except Exception:
        mural_text = ""

    def _to_html(txt: str) -> str:
        import html

        esc = html.escape(txt or "")
        esc = esc.replace("\n", "<br>")
        return esc

    mural_html = _to_html(mural_text)
    next_holiday = None
    try:
        from datetime import date as _date

        today = _date.today()
        nh = Holiday.query.filter(Holiday.date >= today).order_by(Holiday.date.asc()).first()
        if nh:
            next_holiday = {"name": nh.name, "date_str": nh.date.strftime("%d/%m/%Y")}
    except Exception:
        next_holiday = None
    notifications = []
    try:
        crit = (
            Produto.query.filter(
                Produto.estoque_minimo.isnot(None),
                Produto.estoque_minimo > 0,
                Produto.quantidade <= Produto.estoque_minimo,
            )
            .order_by(Produto.nome.asc())
            .limit(10)
            .all()
        )
        for p in crit:
            try:
                is_read = (
                    NotificationRead.query.filter_by(user_id=current_user.id, tipo="estoque", ref_id=p.id).first()
                    is not None
                )
            except Exception:
                is_read = False
            if is_read:
                continue
            notifications.append(
                {
                    "id": p.id,
                    "type": "estoque",
                    "title": f"Estoque crítico: {p.nome}",
                    "subtitle": f"Disponível: {p.quantidade} • Mínimo: {p.estoque_minimo}",
                    "color": "text-bg-danger",
                    "emoji": "⚠️",
                    "url": url_for("estoque.index"),
                }
            )
    except Exception:
        pass
    try:
        from datetime import date as _date
        from datetime import timedelta as _td

        horizon = _date.today() + _td(days=3)
        tasks = (
            CleaningTask.query.filter(CleaningTask.proxima_data.isnot(None), CleaningTask.proxima_data <= horizon)
            .order_by(CleaningTask.proxima_data.asc())
            .limit(10)
            .all()
        )
        for t in tasks:
            try:
                is_read = (
                    NotificationRead.query.filter_by(user_id=current_user.id, tipo="limpeza", ref_id=t.id).first()
                    is not None
                )
            except Exception:
                is_read = False
            if is_read:
                continue
            notifications.append(
                {
                    "id": t.id,
                    "type": "limpeza",
                    "title": f"Tarefa próxima: {t.nome_limpeza}",
                    "subtitle": f"Prevista: {t.proxima_data.strftime('%d/%m/%Y')}",
                    "color": "text-bg-warning",
                    "emoji": "📅",
                    "url": url_for("cronograma.cronograma"),
                }
            )
    except Exception:
        pass
    if next_holiday:
        notifications.append(
            {
                "id": None,
                "type": "holiday",
                "title": f"Próximo feriado: {next_holiday['name']}",
                "subtitle": f"Data: {next_holiday['date_str']}",
                "color": "text-bg-primary",
                "emoji": "🚩",
                "url": url_for("colaboradores.escala"),
            }
        )
    metrics = get_dashboard_metrics()
    chart_data = get_stock_chart_data()
    low_stock = get_low_stock_products()
    return render_template(
        "home.html",
        active_page="home",
        events=events,
        mural_html=mural_html,
        mural_text=mural_text,
        notifications=notifications,
        next_holiday=next_holiday,
        db_diag=db_diag,
        metrics=metrics,
        chart_data=chart_data,
        low_stock=low_stock,
        modules_active=modules_active,
        last_update_date=last_update_date,
        git_version=git_version,
    )


@bp.route("/mural", methods=["POST"], strict_slashes=False)
def update_mural():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode editar o mural.", "danger")
        return redirect(url_for("home.index"))
    txt = request.form.get("mural_text", "").strip()
    try:
        s = AppSettingModel.query.filter_by(key="mural_text").first()
        if not s:
            s = AppSettingModel()
            s.key = "mural_text"
            db.session.add(s)
        s.value = txt
        db.session.commit()
        flash("Mural atualizado.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao atualizar mural: {e}", "danger")
    return redirect(url_for("home.index"))


@bp.route("/changelog", methods=["GET"])
def changelog_redirect():
    """Redireciona /changelog para /changelog/versoes para manter compatibilidade"""
    return redirect(url_for('home.changelog_versoes'))


@bp.route("/changelog/versoes", methods=["GET"])
def changelog_versoes():
    """Exibe página de changelog formatada baseada no arquivo CHANGELOG.md"""
    try:
        from pathlib import Path
        import re

        changelog_path = Path("CHANGELOG.md")
        if not changelog_path.exists():
            return render_template(
                "changelog_versoes.html",
                changelog_content=None,
                error="Arquivo CHANGELOG.md não encontrado"
            )

        content = changelog_path.read_text(encoding="utf-8", errors="ignore")

        # Processa o conteúdo para facilitar a renderização
        versions = []
        current_version = None

        lines = content.split('\n')
        for line in lines:
            line = line.strip()

            # Detecta início de versão ## [X.Y.Z] - data
            version_match = re.match(r'^## \[([\d.]+)\] - (\d{4}-\d{2}-\d{2})', line)
            if version_match:
                if current_version:
                    versions.append(current_version)

                current_version = {
                    'version': version_match.group(1),
                    'date': version_match.group(2),
                    'sections': []
                }
                continue

            # Detecta seção ### Nome
            section_match = re.match(r'^### (.+)', line)
            if section_match and current_version:
                current_version['sections'].append({
                    'title': section_match.group(1),
                    'items': []
                })
                continue

            # Detecta item da lista - texto
            if line.startswith('- ') and current_version and current_version['sections']:
                item_text = line[2:].strip()
                current_version['sections'][-1]['items'].append(item_text)

        # Adiciona a última versão se existir
        if current_version:
            versions.append(current_version)

        return render_template(
            "changelog_versoes.html",
            changelog_content=versions,
            total_versions=len(versions)
        )

    except Exception as e:
        return render_template(
            "changelog_versoes.html",
            changelog_content=None,
            error=f"Erro ao ler changelog: {str(e)}"
        )


@bp.route("/changelog", methods=["POST"], strict_slashes=False)
def update_changelog():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode editar o changelog.", "danger")
        return redirect(url_for("home.index"))
    txt = request.form.get("changelog_text", "").strip()
    try:
        s = AppSettingModel.query.filter_by(key="changelog_text").first()
        if not s:
            s = AppSettingModel()
            s.key = "changelog_text"
            db.session.add(s)
        s.value = txt
        db.session.commit()
        flash("Changelog atualizado.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao atualizar changelog: {e}", "danger")
    return redirect(url_for("home.index"))
