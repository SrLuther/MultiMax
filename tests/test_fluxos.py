from datetime import date
from decimal import Decimal

from multimax.models import CentralColaborador, Fluxo, FluxoConfig, FluxoLancamento, User
from multimax.password_hash import generate_password_hash
from multimax.routes import fluxos


def test_week_bounds():
    ref = date(2026, 2, 4)  # quarta
    start, end = fluxos._week_bounds(ref)
    assert start.weekday() == 6  # domingo
    assert (end - start).days == 6


def test_month_bounds():
    start, end = fluxos._month_bounds(date(2026, 2, 4))
    assert start.day == 1
    assert end.month == 2


def test_fluxo_creation_and_summary(app, db_session):
    colab = CentralColaborador(nome="Teste", username="teste", permissao="operador", ativo=True)
    db_session.add(colab)
    db_session.commit()

    fluxo = fluxos._get_or_create_fluxo(date(2026, 2, 4))
    ciclo = fluxos._get_or_create_ciclo(fluxo, date(2026, 2, 5))

    lanc = FluxoLancamento(
        fluxo_id=fluxo.id,
        ciclo_id=ciclo.id,
        collaborator_id=colab.id,
        data=date(2026, 2, 5),
        horas=9,
        descricao="Outro",
    )
    db_session.add(lanc)
    db_session.commit()

    summaries = fluxos._summaries(fluxo, [colab])
    resumo = summaries[colab.id]
    assert resumo["total_horas"] == 9
    assert resumo["dias_completos"] == 1


def test_group_history(app, db_session):
    colab = CentralColaborador(nome="Hist", username="hist", permissao="operador", ativo=True)
    db_session.add(colab)
    db_session.commit()

    fluxo = fluxos._get_or_create_fluxo(date(2026, 2, 4))
    ciclo = fluxos._get_or_create_ciclo(fluxo, date(2026, 2, 6))

    lanc = FluxoLancamento(
        fluxo_id=fluxo.id,
        ciclo_id=ciclo.id,
        collaborator_id=colab.id,
        data=date(2026, 2, 6),
        horas=-8,
        descricao="Folga",
    )
    db_session.add(lanc)
    db_session.commit()

    grupos = fluxos._group_history(fluxo, colab.id)
    assert any(g["lancamentos"] for g in grupos)


def test_fluxos_routes_admin_flow(client, app, db_session):
    user = User()
    user.name = "Admin Fluxos"
    user.username = "admin_fluxos"
    user.password_hash = generate_password_hash("senha-segura")
    user.nivel = "DEV"
    db_session.add(user)
    db_session.commit()

    login_resp = client.post(
        "/login",
        data={"username": "admin_fluxos", "password": "senha-segura"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (302, 303)

    colab = CentralColaborador(nome="Rota Fluxos", username="rota_fluxos", permissao="operador", ativo=True)
    db_session.add(colab)
    db_session.commit()

    resp = client.get("/fluxos/")
    assert resp.status_code == 200

    resp = client.post(
        "/fluxos/config/valor-diaria",
        data={"valor_diaria": "120,50"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    config = FluxoConfig.query.first()
    assert config is not None
    assert float(config.valor_diaria) == float(Decimal("120.50"))

    fluxo = Fluxo.query.first()
    assert fluxo is not None
    assert float(fluxo.valor_diaria) == float(Decimal("120.50"))

    hoje = date.today()
    resp = client.post(
        "/fluxos/lancamentos/novo",
        data={
            "collaborator_id": str(colab.id),
            "horas": "9",
            "descricao": "Outro",
            "data": hoje.strftime("%Y-%m-%d"),
            "observacao": "Hora extra",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    lanc = FluxoLancamento.query.filter_by(collaborator_id=colab.id).first()
    assert lanc is not None
    assert lanc.descricao == "Outro"

    resp = client.post(
        f"/fluxos/lancamentos/{lanc.id}/editar",
        data={
            "horas": "7",
            "descricao": "Feriado",
            "data": hoje.strftime("%Y-%m-%d"),
            "observacao": "ajustado",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    db_session.refresh(lanc)
    assert lanc.horas == 7.0
    assert lanc.descricao == "Feriado"

    pdf_resp = client.get(f"/fluxos/pdf/individual/{colab.id}", follow_redirects=False)
    if fluxos.WEASYPRINT_AVAILABLE:
        assert pdf_resp.status_code == 200
    else:
        assert pdf_resp.status_code in (302, 303)

    close_resp = client.post("/fluxos/fechar", data={}, follow_redirects=False)
    assert close_resp.status_code in (302, 303)
    assert Fluxo.query.filter_by(status="fechado").first() is not None
