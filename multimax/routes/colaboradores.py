from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import AppSetting
from ..models import Collaborator as CollaboratorModel
from ..models import Holiday, MedicalCertificate, Shift, TimeOffRecord
from ..models import Vacation as VacationModel
from ..services.notificacao_service import registrar_evento

bp = Blueprint("colaboradores", __name__)


@bp.route("/escala", strict_slashes=False)
@login_required
def escala():
    from datetime import timedelta

    try:
        from sqlalchemy import inspect, text

        insp = inspect(db.engine)
        cols_meta = [c["name"] for c in insp.get_columns("collaborator")]
        changed = False
        if "name" not in cols_meta:
            db.session.execute(text("ALTER TABLE collaborator ADD COLUMN name TEXT"))
            changed = True
            if "nome" in cols_meta:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = nome WHERE name IS NULL"))
                except Exception:
                    pass
            else:
                try:
                    db.session.execute(text("UPDATE collaborator SET name = '' WHERE name IS NULL"))
                except Exception:
                    pass
        if changed:
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    cols = CollaboratorModel.query.filter_by(active=True).order_by(CollaboratorModel.name.asc()).all()
    today = date.today()

    semana_param = request.args.get("semana", "")
    if semana_param:
        try:
            semana_inicio = datetime.strptime(semana_param, "%Y-%m-%d").date()
            semana_inicio = semana_inicio - timedelta(days=semana_inicio.weekday())
        except Exception:
            semana_inicio = today - timedelta(days=today.weekday())
    else:
        semana_inicio = today - timedelta(days=today.weekday())

    semana_fim = semana_inicio + timedelta(days=6)
    semana_anterior = (semana_inicio - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_proxima = (semana_inicio + timedelta(days=7)).strftime("%Y-%m-%d")

    dias_nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    dias_semana = []
    for i in range(7):
        d = semana_inicio + timedelta(days=i)
        dias_semana.append({"data": d, "nome": dias_nomes[i], "is_today": d == today})

    turnos_semana = Shift.query.filter(Shift.date >= semana_inicio, Shift.date <= semana_fim).all()

    turnos_map = {}
    for t in turnos_semana:
        key = (t.collaborator_id, t.date.isoformat())
        turnos_map[key] = t

    # Mapa de status (Folga, Férias, Atestado) por colaborador e data
    status_map = {}
    for colab in cols:
        for dia in dias_semana:
            key = (colab.id, dia["data"].isoformat())
            status = None

            # Verificar Folga (folga_usada)
            try:
                folgas = (
                    TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == colab.id,
                        TimeOffRecord.record_type == "folga_usada",
                        TimeOffRecord.date <= dia["data"],
                    )
                    .order_by(TimeOffRecord.date.desc())
                    .limit(5)
                    .all()
                )
                for folga in folgas:
                    days = max(1, int(folga.days or 1))
                    end_date = folga.date + timedelta(days=days - 1)
                    if folga.date <= dia["data"] <= end_date:
                        status = "Folga"
                        break
            except Exception:
                pass

            # Verificar Férias (prioridade sobre folga)
            if not status:
                try:
                    vac = VacationModel.query.filter(
                        VacationModel.collaborator_id == colab.id,
                        VacationModel.data_inicio <= dia["data"],
                        VacationModel.data_fim >= dia["data"],
                    ).first()
                    if vac:
                        status = "Férias"
                except Exception:
                    pass

            # Verificar Atestado (prioridade sobre férias e folga)
            if not status:
                try:
                    mc = MedicalCertificate.query.filter(
                        MedicalCertificate.collaborator_id == colab.id,
                        MedicalCertificate.data_inicio <= dia["data"],
                        MedicalCertificate.data_fim >= dia["data"],
                    ).first()
                    if mc:
                        status = "Atestado"
                except Exception:
                    pass

            if status:
                status_map[key] = status

    horas_turno = {
        "Abertura 5h": 8,  # 5h-11h e 13h-15h (2 pessoas)
        "Abertura 6h": 8,  # 6h-11h e 13h-16h (1 pessoa)
        "Tarde": 8,  # 9h30-13h e 15h-19h30 (3 pessoas)
        "Domingo 5h": 8,  # 5h-13h (2 pessoas)
        "Domingo 6h": 7,  # 6h-13h (1 pessoa)
        "Folga": 0,
    }
    horas_semana = {}
    for c in cols:
        total = 0
        for dia in dias_semana:
            key = (c.id, dia["data"].isoformat())
            if key in turnos_map:
                turno = turnos_map[key].turno or ""
                total += horas_turno.get(turno, 0)
        horas_semana[c.id] = total

    total_turnos_semana = len(turnos_semana)
    current_monday = today - timedelta(days=today.weekday())
    try:
        ref_monday_setting = AppSetting.query.filter_by(key="rodizio_ref_monday").first()
        ref_open_setting = AppSetting.query.filter_by(key="rodizio_open_team_ref").first()
        ref_monday = None
        if ref_monday_setting and (ref_monday_setting.value or "").strip():
            try:
                ref_monday = datetime.strptime(ref_monday_setting.value.strip(), "%Y-%m-%d").date()
            except Exception:
                ref_monday = None
        if not ref_monday:
            if not ref_monday_setting:
                ref_monday_setting = AppSetting()
                ref_monday_setting.key = "rodizio_ref_monday"
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime("%Y-%m-%d")
            db.session.commit()
            ref_monday = current_monday
        open_ref = ref_open_setting.value.strip() if ref_open_setting and ref_open_setting.value else "1"
        if open_ref not in ("1", "2"):
            open_ref = "1"
        # auto-avance semanal: se referência ficou para trás, atualiza e alterna
        if ref_monday < current_monday:
            weeks_diff = (current_monday - ref_monday).days // 7
            if weeks_diff % 2 == 1:
                open_ref = "2" if open_ref == "1" else "1"
            ref_monday = current_monday
            if not ref_monday_setting:
                ref_monday_setting = AppSetting()
                ref_monday_setting.key = "rodizio_ref_monday"
                db.session.add(ref_monday_setting)
            ref_monday_setting.value = current_monday.strftime("%Y-%m-%d")
            if not ref_open_setting:
                ref_open_setting = AppSetting()
                ref_open_setting.key = "rodizio_open_team_ref"
                db.session.add(ref_open_setting)
            ref_open_setting.value = open_ref
            db.session.commit()
        weeks = []
        for i in range(5):
            ws = current_monday + timedelta(days=7 * i)
            we = ws + timedelta(days=5)
            open_team = open_ref if (i % 2 == 0) else ("2" if open_ref == "1" else "1")
            close_team = "2" if open_team == "1" else "1"
            weeks.append(
                {
                    "start": ws,
                    "end": we,
                    "open": f"Equipe {open_team}",
                    "close": f"Equipe {close_team}",
                }
            )
    except Exception:
        weeks = []
    try:
        sun_team_setting = AppSetting.query.filter_by(key="domingo_team_ref").first()
        sun_ref_setting = AppSetting.query.filter_by(key="domingo_ref_sunday").first()
        domingo_team = sun_team_setting.value.strip() if sun_team_setting and sun_team_setting.value else None
        if domingo_team not in ("1", "2"):
            sun_m = AppSetting.query.filter_by(key="domingo_manha_team").first()
            domingo_team = sun_m.value.strip() if sun_m and sun_m.value else "1"
            if domingo_team not in ("1", "2"):
                domingo_team = "1"
        domingo_ref_date = sun_ref_setting.value.strip() if sun_ref_setting and sun_ref_setting.value else ""
    except Exception:
        domingo_team = "1"
        domingo_ref_date = ""
    events = []
    conflicts = []
    try:
        name_by_id = {c.id: c.name for c in cols}
        for t in turnos_semana:
            cid = t.collaborator_id
            d = t.date
            nm = name_by_id.get(cid) or f"ID {cid}"
            # Folga agendada
            try:
                las = (
                    TimeOffRecord.query.filter(
                        TimeOffRecord.collaborator_id == cid,
                        TimeOffRecord.record_type == "folga_usada",
                        TimeOffRecord.date <= d,
                    )
                    .order_by(TimeOffRecord.date.desc())
                    .limit(3)
                    .all()
                )
                for la in las or []:
                    days = max(1, int(la.days or 1))
                    end_date = la.date + timedelta(days=days - 1)
                    if end_date >= d:
                        conflicts.append({"type": "Folga", "name": nm, "date": d})
                        break
            except Exception:
                pass
            # Férias
            try:
                vac = VacationModel.query.filter(
                    VacationModel.collaborator_id == cid, VacationModel.data_inicio <= d, VacationModel.data_fim >= d
                ).first()
                if vac:
                    conflicts.append({"type": "Férias", "name": nm, "date": d})
            except Exception:
                pass
            # Atestado
            try:
                mc = MedicalCertificate.query.filter(
                    MedicalCertificate.collaborator_id == cid,
                    MedicalCertificate.data_inicio <= d,
                    MedicalCertificate.data_fim >= d,
                ).first()
                if mc:
                    conflicts.append({"type": "Atestado", "name": nm, "date": d})
            except Exception:
                pass
    except Exception:
        conflicts = []
    try:
        from datetime import timedelta

        base_team = domingo_team if domingo_team in ("1", "2") else "1"
        ref_sun = None
        if domingo_ref_date:
            try:
                ref_sun = datetime.strptime(domingo_ref_date, "%Y-%m-%d").date()
            except Exception:
                ref_sun = None
        for i in range(5):
            ws = current_monday + timedelta(days=7 * i)
            sunday = ws + timedelta(days=6)
            team_i = base_team
            if ref_sun:
                weeks_diff = (sunday - ref_sun).days // 7
                if weeks_diff % 2 == 1:
                    team_i = "2" if base_team == "1" else "1"
            else:
                if i % 2 == 1:
                    team_i = "2" if base_team == "1" else "1"
            events.append(
                {
                    "title": f"DOMINGO EQUIPE '{team_i}' (5h–13h)",
                    "start": sunday.strftime("%Y-%m-%d"),
                    "color": "#fd7e14",
                    "url": url_for("colaboradores.escala"),
                    "kind": "rodizio-sunday",
                    "team": team_i,
                }
            )
    except Exception:
        pass
    try:
        y = today.year
        fixed = [
            (date(y, 2, 2), "Padroeiro de Umbaúba"),
            (date(y, 2, 6), "Aniversário de Umbaúba"),
            (date(y + 1, 2, 2), "Padroeiro de Umbaúba"),
            (date(y + 1, 2, 6), "Aniversário de Umbaúba"),
        ]
        for dt, nm in fixed:
            h = Holiday.query.filter_by(date=dt).first()
            if h:
                h.name = nm
                h.kind = "municipal-Umbaúba"
            else:
                hh = Holiday()
                hh.date = dt
                hh.name = nm
                hh.kind = "municipal-Umbaúba"
                db.session.add(hh)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        ano = 2026
        fixes = [
            (date(ano, 1, 1), "Confraternização Universal"),
            (date(ano, 4, 21), "Tiradentes"),
            (date(ano, 5, 1), "Dia do Trabalho"),
            (date(ano, 9, 7), "Independência do Brasil"),
            (date(ano, 10, 12), "Nossa Senhora Aparecida"),
            (date(ano, 11, 2), "Finados"),
            (date(ano, 11, 15), "Proclamação da República"),
            (date(ano, 11, 20), "Consciência Negra"),
            (date(ano, 12, 25), "Natal"),
        ]

        def easter(y):
            a = y % 19
            b = y // 100
            c = y % 100
            d = (19 * a + b - (b // 4) - ((b - ((b + 8) // 25) + 1) // 3) + 15) % 30
            e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
            f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
            month = f // 31
            day = (f % 31) + 1
            return date(y, month, day)

        gf = easter(ano)
        try:
            from datetime import timedelta as _timedelta

            gf = gf - _timedelta(days=2)
            fixes.append((gf, "Sexta-Feira Santa"))
            cc = easter(ano) + _timedelta(days=60)
            fixes.append((cc, "Corpus Christi"))
        except Exception:
            pass
        for dt, nm in fixes:
            h = Holiday.query.filter_by(date=dt).first()
            if h:
                h.name = nm
                h.kind = "nacional"
            else:
                hh = Holiday()
                hh.date = dt
                hh.name = nm
                hh.kind = "nacional"
                db.session.add(hh)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        hs = Holiday.query.order_by(Holiday.date.asc()).all()
        color_map = {
            "nacional": "#20c997",
            "movel": "#198754",
            "estadual-SE": "#0dcaf0",
            "municipal-Umbaúba": "#0d6efd",
            "facultativo": "#adb5bd",
            "municipal": "#0d6efd",
            "estadual": "#0dcaf0",
        }
        for h in hs:
            kind = (h.kind or "feriado").strip()
            events.append(
                {
                    "title": h.name,
                    "start": h.date.strftime("%Y-%m-%d"),
                    "color": color_map.get(kind, "#20c997"),
                    "url": url_for("colaboradores.escala"),
                    "kind": kind,
                }
            )
    except Exception:
        pass
    try:
        las = (
            TimeOffRecord.query.filter(TimeOffRecord.record_type == "folga_usada")
            .order_by(TimeOffRecord.date.asc())
            .all()
        )
        name_by_id = {c.id: c.name for c in cols}
        from datetime import timedelta

        for la in las:
            base = la.date
            days = max(1, int(la.days_used or 1))
            nm = name_by_id.get(la.collaborator_id) or f"ID {la.collaborator_id}"
            for i in range(days):
                d = base + timedelta(days=i)
                events.append(
                    {
                        "title": f"FOLGA: {nm}",
                        "start": d.strftime("%Y-%m-%d"),
                        "color": "#6f42c1",
                        "url": url_for("colaboradores.escala"),
                        "kind": "folga",
                    }
                )
    except Exception:
        pass
    try:
        turno_colors = {
            "Abertura 5h": "#22c55e",
            "Abertura 6h": "#10b981",
            "Tarde": "#3b82f6",
            "Domingo 5h": "#f59e0b",
            "Domingo 6h": "#f97316",
            "Folga": "#6b7280",
        }
        name_by_id = {c.id: c.name for c in cols}
        for t in turnos_semana:
            nm = name_by_id.get(t.collaborator_id) or f"ID {t.collaborator_id}"
            events.append(
                {
                    "title": f"{t.turno}: {nm}",
                    "start": t.date.strftime("%Y-%m-%d"),
                    "color": turno_colors.get(t.turno, "#6b7280"),
                    "url": url_for("colaboradores.escala"),
                    "kind": "turno",
                }
            )
    except Exception:
        pass
    return render_template(
        "escala.html",
        colaboradores=cols,
        weeks=weeks,
        ref_open=open_ref,
        domingo_team=domingo_team,
        domingo_ref_date=domingo_ref_date,
        events=events,
        feriados=hs if "hs" in locals() else [],
        active_page="escala",
        semana_inicio=semana_inicio,
        semana_fim=semana_fim,
        semana_anterior=semana_anterior,
        semana_proxima=semana_proxima,
        dias_semana=dias_semana,
        turnos_map=turnos_map,
        status_map=status_map,
        horas_semana=horas_semana,
        total_turnos_semana=total_turnos_semana,
        conflicts=conflicts,
    )


@bp.route("/escala/domingo/configurar", methods=["POST"], strict_slashes=False)
@login_required
def domingo_configurar():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para configurar domingos.", "danger")
        return redirect(url_for("colaboradores.escala"))
    team = (request.form.get("domingo_team", "1") or "1").strip()
    date_str = request.form.get("domingo_data", "").strip() or ""
    if team not in ("1", "2"):
        flash("Seleção inválida para domingos.", "warning")
        return redirect(url_for("colaboradores.escala"))
    try:
        sm = AppSetting.query.filter_by(key="domingo_manha_team").first()
        if not sm:
            sm = AppSetting()
            sm.key = "domingo_manha_team"
            db.session.add(sm)
        sm.value = team
        stm = AppSetting.query.filter_by(key="domingo_team_ref").first()
        rs = AppSetting.query.filter_by(key="domingo_ref_sunday").first()
        if not stm:
            stm = AppSetting()
            stm.key = "domingo_team_ref"
            db.session.add(stm)
        if date_str:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                if not rs:
                    rs = AppSetting()
                    rs.key = "domingo_ref_sunday"
                    db.session.add(rs)
                rs.value = d.strftime("%Y-%m-%d")
            except Exception:
                pass
        stm.value = team
        db.session.commit()
        flash("Configuração de domingos atualizada.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao salvar configuração de domingos: {e}", "danger")
    return redirect(url_for("colaboradores.escala"))


@bp.route("/escala/feriado/criar", methods=["POST"], strict_slashes=False)
@login_required
def feriado_criar():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode configurar feriados.", "danger")
        return redirect(url_for("colaboradores.escala"))
    date_str = request.form.get("date", "").strip() or ""
    name = request.form.get("name", "").strip() or ""
    kind = request.form.get("kind", "").strip() or ""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        flash("Data inválida para feriado.", "warning")
        return redirect(url_for("colaboradores.escala"))
    if not name:
        flash("Nome do feriado é obrigatório.", "warning")
        return redirect(url_for("colaboradores.escala"))
    try:
        existing = Holiday.query.filter_by(date=d).first()
        if existing:
            existing.name = name
            existing.kind = kind or existing.kind
        else:
            h = Holiday()
            h.date = d
            h.name = name
            h.kind = kind or None
            db.session.add(h)
        db.session.commit()
        flash("Feriado salvo.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao salvar feriado: {e}", "danger")
    return redirect(url_for("colaboradores.escala"))


@bp.route("/escala/feriado/excluir/<int:id>", methods=["POST"], strict_slashes=False)
@login_required
def feriado_excluir(id: int):
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode excluir feriados.", "danger")
        return redirect(url_for("colaboradores.escala"))
    h = Holiday.query.get_or_404(id)
    try:
        db.session.delete(h)
        db.session.commit()
        flash("Feriado excluído.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir feriado: {e}", "danger")
    return redirect(url_for("colaboradores.escala"))


@bp.route("/escala/turno/atribuir", methods=["POST"], strict_slashes=False)
@login_required
def turno_atribuir():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Voce nao tem permissao para atribuir turnos.", "danger")
        return redirect(url_for("colaboradores.escala"))

    turno_id = request.form.get("turno_id", "").strip()
    collaborator_id = request.form.get("collaborator_id", type=int)
    data_str = request.form.get("data", "").strip()
    turno_tipo = request.form.get("turno", "").strip()
    observacao = request.form.get("observacao", "").strip()

    if not collaborator_id or not data_str or not turno_tipo:
        flash("Preencha todos os campos obrigatorios.", "warning")
        return redirect(url_for("colaboradores.escala"))

    try:
        data_turno = datetime.strptime(data_str, "%Y-%m-%d").date()
    except Exception:
        flash("Data invalida.", "warning")
        return redirect(url_for("colaboradores.escala"))

    try:
        if turno_id:
            shift = Shift.query.get(int(turno_id))
            if shift:
                shift.collaborator_id = collaborator_id
                shift.date = data_turno
                shift.turno = turno_tipo
                shift.observacao = observacao
                flash("Turno atualizado com sucesso.", "success")
        else:
            existing = Shift.query.filter_by(collaborator_id=collaborator_id, date=data_turno).first()
            if existing:
                existing.turno = turno_tipo
                existing.observacao = observacao
                flash("Turno atualizado com sucesso.", "success")
            else:
                shift = Shift()
                shift.collaborator_id = collaborator_id
                shift.date = data_turno
                shift.turno = turno_tipo
                shift.observacao = observacao
                db.session.add(shift)
                flash("Turno atribuido com sucesso.", "success")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao salvar turno: {e}", "danger")

    from datetime import timedelta as td

    semana = (data_turno - td(days=data_turno.weekday())).strftime("%Y-%m-%d")
    return redirect(url_for("colaboradores.escala", semana=semana))


@bp.route("/escala/turno/excluir/<int:id>", methods=["POST"], strict_slashes=False)
@login_required
def turno_excluir(id: int):
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Voce nao tem permissao para excluir turnos.", "danger")
        return redirect(url_for("colaboradores.escala"))

    from datetime import timedelta as td

    shift = Shift.query.get_or_404(id)
    semana = (shift.date - td(days=shift.date.weekday())).strftime("%Y-%m-%d")
    try:
        db.session.delete(shift)
        db.session.commit()
        flash("Turno excluido.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir turno: {e}", "danger")

    return redirect(url_for("colaboradores.escala", semana=semana))


@bp.route("/escala/equipe/configurar", methods=["POST"], strict_slashes=False)
@login_required
def equipe_configurar():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Voce nao tem permissao para configurar equipes.", "danger")
        return redirect(url_for("colaboradores.escala"))

    collaborator_id = request.form.get("collaborator_id", type=int)
    team = request.form.get("team", "").strip()
    position = request.form.get("position", type=int) or 1

    if not collaborator_id or team not in ("1", "2"):
        flash("Dados invalidos.", "warning")
        return redirect(url_for("colaboradores.escala"))

    try:
        colab = CollaboratorModel.query.get(collaborator_id)
        if colab:
            colab.regular_team = team
            colab.team_position = position
            db.session.commit()
            flash(f"{colab.name} atribuido a Equipe {team}, posicao {position}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao configurar equipe: {e}", "danger")

    return redirect(url_for("colaboradores.escala"))


@bp.route("/escala/gerar-automatica", methods=["POST"], strict_slashes=False)
@login_required
def gerar_escala_automatica():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Voce nao tem permissao para gerar escalas.", "danger")
        return redirect(url_for("colaboradores.escala"))

    from datetime import timedelta as td

    semana_str = request.form.get("semana", "").strip()
    incluir_domingo = request.form.get("incluir_domingo") == "on"

    try:
        if semana_str:
            semana_inicio = datetime.strptime(semana_str, "%Y-%m-%d").date()
            semana_inicio = semana_inicio - td(days=semana_inicio.weekday())
        else:
            today = date.today()
            semana_inicio = today - td(days=today.weekday())
    except Exception:
        flash("Data invalida.", "warning")
        return redirect(url_for("colaboradores.escala"))

    ref_monday_setting = AppSetting.query.filter_by(key="rodizio_ref_monday").first()
    ref_open_setting = AppSetting.query.filter_by(key="rodizio_open_team_ref").first()

    ref_monday = None
    if ref_monday_setting and ref_monday_setting.value:
        try:
            ref_monday = datetime.strptime(ref_monday_setting.value.strip(), "%Y-%m-%d").date()
        except Exception:
            pass
    if not ref_monday:
        ref_monday = semana_inicio

    open_ref = "1"
    if ref_open_setting and ref_open_setting.value in ("1", "2"):
        open_ref = ref_open_setting.value

    weeks_diff = (semana_inicio - ref_monday).days // 7
    if weeks_diff % 2 == 1:
        open_team = "2" if open_ref == "1" else "1"
    else:
        open_team = open_ref
    close_team = "2" if open_team == "1" else "1"

    equipe_abertura = (
        CollaboratorModel.query.filter_by(active=True, regular_team=open_team)
        .order_by(CollaboratorModel.team_position.asc())
        .all()
    )
    equipe_fechamento = (
        CollaboratorModel.query.filter_by(active=True, regular_team=close_team)
        .order_by(CollaboratorModel.team_position.asc())
        .all()
    )

    if len(equipe_abertura) < 3 or len(equipe_fechamento) < 3:
        flash(
            f"Equipe de Abertura incompleta: {len(equipe_abertura)}/3 pessoas necessárias. Equipe de Fechamento (Tarde) incompleta: {len(equipe_fechamento)}/3 pessoas necessárias. Configure as equipes primeiro.",
            "warning",
        )
        return redirect(url_for("colaboradores.escala", semana=semana_inicio.strftime("%Y-%m-%d")))

    tz = ZoneInfo("America/Sao_Paulo")
    turnos_criados = 0

    try:
        for day_offset in range(6):
            dia = semana_inicio + td(days=day_offset)

            for i, colab in enumerate(equipe_abertura[:3]):
                existing = Shift.query.filter_by(collaborator_id=colab.id, date=dia).first()
                if existing:
                    continue

                shift = Shift()
                shift.collaborator_id = colab.id
                shift.date = dia
                shift.auto_generated = True

                if i < 2:
                    shift.turno = "Abertura 5h"
                    shift.shift_type = "abertura_5h"
                    shift.start_dt = datetime(dia.year, dia.month, dia.day, 5, 0, tzinfo=tz)
                    shift.end_dt = datetime(dia.year, dia.month, dia.day, 15, 0, tzinfo=tz)
                    shift.observacao = "05:00-11:00 almoco 13:00-15:00"
                else:
                    shift.turno = "Abertura 6h"
                    shift.shift_type = "abertura_6h"
                    shift.start_dt = datetime(dia.year, dia.month, dia.day, 6, 0, tzinfo=tz)
                    shift.end_dt = datetime(dia.year, dia.month, dia.day, 16, 0, tzinfo=tz)
                    shift.observacao = "06:00-11:00 almoco 13:00-16:00"

                db.session.add(shift)
                turnos_criados += 1

            for colab in equipe_fechamento[:3]:
                existing = Shift.query.filter_by(collaborator_id=colab.id, date=dia).first()
                if existing:
                    continue

                shift = Shift()
                shift.collaborator_id = colab.id
                shift.date = dia
                shift.turno = "Tarde"
                shift.shift_type = "tarde"
                shift.auto_generated = True
                shift.start_dt = datetime(dia.year, dia.month, dia.day, 9, 30, tzinfo=tz)
                shift.end_dt = datetime(dia.year, dia.month, dia.day, 19, 30, tzinfo=tz)
                shift.observacao = "09:30-13:00 almoco 15:00-19:30"
                db.session.add(shift)
                turnos_criados += 1

        if incluir_domingo:
            domingo = semana_inicio + td(days=6)

            sun_team_setting = AppSetting.query.filter_by(key="domingo_team_ref").first()
            sun_ref_setting = AppSetting.query.filter_by(key="domingo_ref_sunday").first()

            domingo_team = sun_team_setting.value.strip() if sun_team_setting and sun_team_setting.value else "1"
            if domingo_team not in ("1", "2"):
                domingo_team = "1"

            ref_sun = None
            if sun_ref_setting and sun_ref_setting.value:
                try:
                    ref_sun = datetime.strptime(sun_ref_setting.value.strip(), "%Y-%m-%d").date()
                except Exception:
                    pass

            if ref_sun:
                weeks_diff_sun = (domingo - ref_sun).days // 7
                if weeks_diff_sun % 2 == 1:
                    domingo_team = "2" if domingo_team == "1" else "1"

            equipe_domingo = (
                CollaboratorModel.query.filter_by(active=True, regular_team=domingo_team)
                .order_by(CollaboratorModel.team_position.asc())
                .all()[:3]
            )

            for i, colab in enumerate(equipe_domingo):
                existing = Shift.query.filter_by(collaborator_id=colab.id, date=domingo).first()
                if existing:
                    continue

                shift = Shift()
                shift.collaborator_id = colab.id
                shift.date = domingo
                shift.auto_generated = True
                shift.is_sunday_holiday = True

                if i < 2:
                    shift.turno = "Domingo 5h"
                    shift.shift_type = "domingo_5h"
                    shift.start_dt = datetime(domingo.year, domingo.month, domingo.day, 5, 0, tzinfo=tz)
                    shift.end_dt = datetime(domingo.year, domingo.month, domingo.day, 13, 0, tzinfo=tz)
                    shift.observacao = "05:00-13:00 (+1 folga +1h extra)"

                    # já coberto pelo combinado acima
                else:
                    shift.turno = "Domingo 6h"
                    shift.shift_type = "domingo_6h"
                    shift.start_dt = datetime(domingo.year, domingo.month, domingo.day, 6, 0, tzinfo=tz)
                    shift.end_dt = datetime(domingo.year, domingo.month, domingo.day, 13, 0, tzinfo=tz)
                    shift.observacao = "06:00-13:00 (+1 folga)"

                db.session.add(shift)
                turnos_criados += 1

                from ..models import TemporaryEntry

                # Para 5h: crédito combinado (folga + 1h). Para 6h: apenas folga.
                if i < 2:
                    existing_b = TemporaryEntry.query.filter_by(
                        kind="folga_hour_both", collaborator_id=colab.id, date=domingo
                    ).first()
                    if not existing_b:
                        tb = TemporaryEntry()
                        tb.kind = "folga_hour_both"
                        tb.collaborator_id = colab.id
                        tb.date = domingo
                        tb.amount_days = 1
                        tb.hours = 1.0
                        tb.source = "domingo"
                        tb.reason = "Folga + 1h extra (domingo 5h)"
                        db.session.add(tb)
                else:
                    existing_lc = TemporaryEntry.query.filter_by(
                        kind="folga_credit", collaborator_id=colab.id, date=domingo
                    ).first()
                    if not existing_lc:
                        te = TemporaryEntry()
                        te.kind = "folga_credit"
                        te.collaborator_id = colab.id
                        te.date = domingo
                        te.amount_days = 1
                        te.source = "domingo"
                        te.reason = f'Trabalho no domingo {domingo.strftime("%d/%m/%Y")}'
                        db.session.add(te)

        db.session.commit()
        flash(
            f"Escala gerada com sucesso! {turnos_criados} turnos criados. Equipe {open_team} na abertura (2x Abertura 5h + 1x Abertura 6h), Equipe {close_team} no turno Tarde (3 pessoas).",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao gerar escala: {e}", "danger")

    return redirect(url_for("colaboradores.escala", semana=semana_inicio.strftime("%Y-%m-%d")))


@bp.route("/escala/limpar-semana", methods=["POST"], strict_slashes=False)
@login_required
def limpar_escala_semana():
    if current_user.nivel not in ("admin", "DEV"):
        flash("Apenas Gerente pode limpar escalas.", "danger")
        return redirect(url_for("colaboradores.escala"))

    from datetime import timedelta as td

    semana_str = request.form.get("semana", "").strip()
    apenas_automaticos = request.form.get("apenas_automaticos") == "on"

    try:
        if semana_str:
            semana_inicio = datetime.strptime(semana_str, "%Y-%m-%d").date()
            semana_inicio = semana_inicio - td(days=semana_inicio.weekday())
        else:
            today = date.today()
            semana_inicio = today - td(days=today.weekday())
    except Exception:
        flash("Data invalida.", "warning")
        return redirect(url_for("colaboradores.escala"))

    semana_fim = semana_inicio + td(days=6)

    try:
        query = Shift.query.filter(Shift.date >= semana_inicio, Shift.date <= semana_fim)
        if apenas_automaticos:
            query = query.filter(Shift.auto_generated.is_(True))

        shifts_to_delete = query.all()
        count = len(shifts_to_delete)

        for shift in shifts_to_delete:
            if shift.is_sunday_holiday:
                TimeOffRecord.query.filter(
                    TimeOffRecord.collaborator_id == shift.collaborator_id,
                    TimeOffRecord.date == shift.date,
                    TimeOffRecord.record_type == "folga_adicional",
                    TimeOffRecord.origin == "domingo",
                ).delete()
                TimeOffRecord.query.filter(
                    TimeOffRecord.collaborator_id == shift.collaborator_id,
                    TimeOffRecord.date == shift.date,
                    TimeOffRecord.record_type == "horas",
                    TimeOffRecord.notes == "Hora extra domingo (entrada 5h)",
                ).delete()
            db.session.delete(shift)

        db.session.commit()
        flash(f"{count} turnos removidos da semana (creditos associados tambem removidos).", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao limpar escala: {e}", "danger")

    return redirect(url_for("colaboradores.escala", semana=semana_inicio.strftime("%Y-%m-%d")))


@bp.route("/gestao/folga/credito", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_registrar_gestao():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para registrar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para crédito de folga.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        lc = TimeOffRecord()
        lc.collaborator_id = cid
        lc.date = d
        lc.record_type = "folga_adicional"
        lc.days = amount
        lc.origin = "manual"
        lc.notes = notes
        lc.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(lc)
        db.session.commit()
        flash("Crédito de folga registrado.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar crédito: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/credito/domingo", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_domingo():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para registrar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or "Domingo trabalhado"
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para crédito de domingo.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        exists = TimeOffRecord.query.filter(
            TimeOffRecord.collaborator_id == cid,
            TimeOffRecord.date == d,
            TimeOffRecord.record_type == "folga_adicional",
            TimeOffRecord.origin == "domingo",
        ).first()
        if not exists:
            lc = TimeOffRecord()
            lc.collaborator_id = cid
            lc.date = d
            lc.record_type = "folga_adicional"
            lc.days = amount
            lc.origin = "domingo"
            lc.notes = notes
            lc.created_by = current_user.username if current_user.is_authenticated else "sistema"
            db.session.add(lc)
            db.session.commit()
            flash("Crédito de domingo registrado.", "success")
        else:
            flash("Crédito de domingo já existe para essa data.", "info")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar crédito: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/credito/reduzir", methods=["POST"], strict_slashes=False)
@login_required
def folga_credito_reduzir():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para ajustar créditos.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    amount_str = request.form.get("amount", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or "Ajuste negativo"
    try:
        cid = int(cid_str)
        amount = max(1, int(amount_str))
    except Exception:
        flash("Dados inválidos para ajuste.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        from datetime import date as _date

        lc = TimeOffRecord()
        lc.collaborator_id = cid
        lc.date = _date.today()
        lc.record_type = "folga_adicional"
        lc.days = -amount
        lc.origin = "ajuste"
        lc.notes = notes
        db.session.add(lc)
        db.session.commit()
        flash("Ajuste aplicado: dias reduzidos.", "warning")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao ajustar créditos: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/agendar", methods=["POST"], strict_slashes=False)
@login_required
def folga_agendar():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para agendar folga.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days", "1").strip() or "1"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = max(1, int(days_str))
    except Exception:
        flash("Dados inválidos para agendamento.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        from sqlalchemy import func

        credits_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_adicional")
            .scalar()
            or 0
        )
        assigned_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "folga_usada")
            .scalar()
            or 0
        )
        converted_sum = (
            db.session.query(func.coalesce(func.sum(TimeOffRecord.days), 0))
            .filter(TimeOffRecord.collaborator_id == cid, TimeOffRecord.record_type == "conversao")
            .scalar()
            or 0
        )
        folga_balance = int(credits_sum) - int(assigned_sum) - int(converted_sum)
        if folga_balance < days:
            flash(
                f"Saldo de folga insuficiente ({folga_balance} dia(s)). Reduza os dias ou converta em dinheiro.",
                "warning",
            )
            return redirect(url_for("usuarios.gestao") + "#folgas")
    except Exception:
        pass
    try:
        from datetime import timedelta

        try:
            end_d = d + timedelta(days=max(1, days) - 1)
            feriados_no_periodo = Holiday.query.filter(Holiday.date >= d, Holiday.date <= end_d).count()
        except Exception:
            feriados_no_periodo = 0
        effective_days = max(0, int(days) - int(feriados_no_periodo))
        la = TimeOffRecord()
        la.collaborator_id = cid
        la.date = d
        la.record_type = "folga_usada"
        la.days = effective_days
        la.notes = notes
        la.origin = "manual"
        la.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(la)
        db.session.commit()
        try:
            col = CollaboratorModel.query.get(cid)
            nome = col.name if col and col.name else f"ID {cid}"
        except Exception:
            nome = f"ID {cid}"
        registrar_evento("folga cadastrada", produto=nome, quantidade=days, descricao=notes)
        flash("Folga agendada.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao agendar folga: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))


@bp.route("/gestao/folga/converter", methods=["POST"], strict_slashes=False)
@login_required
def folga_converter():
    if current_user.nivel not in ("operador", "admin", "DEV"):
        flash("Você não tem permissão para converter folga.", "danger")
        return redirect(url_for("usuarios.gestao"))
    cid_str = request.form.get("collaborator_id", "").strip() or ""
    date_str = request.form.get("date", "").strip() or ""
    days_str = request.form.get("days", "1").strip() or "1"
    amount_str = request.form.get("amount_paid", "").strip() or ""
    rate_str = request.form.get("rate_per_day", "65").strip() or "65"
    notes = request.form.get("notes", "").strip() or ""
    try:
        cid = int(cid_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days = max(1, int(days_str))
        rate = float(rate_str)
        amount_paid = float(amount_str) if amount_str else (rate * days)
    except Exception:
        flash("Dados inválidos para conversão.", "warning")
        return redirect(url_for("usuarios.gestao"))
    try:
        conv = TimeOffRecord()
        conv.collaborator_id = cid
        conv.date = d
        conv.record_type = "conversao"
        conv.days = days
        conv.amount_paid = amount_paid
        conv.rate_per_day = rate
        conv.notes = notes
        conv.origin = "manual"
        conv.created_by = current_user.username if current_user.is_authenticated else "sistema"
        db.session.add(conv)
        db.session.commit()
        flash("Conversão registrada.", "success")
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        flash(f"Erro ao registrar conversão: {e}", "danger")
    return redirect(url_for("usuarios.gestao"))
