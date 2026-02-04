import os

from multimax.utils import error_handlers


def test_handle_error_basic(app):
    with app.test_request_context("/boom"):
        from flask import g

        g.request_id = "test-id"
        response, status = error_handlers._handle_error(ValueError("boom"), 500, "Unexpected Error")
        data = response.get_json()

        assert status == 500
        assert data["status"] == "error"
        assert data["message"] == "Unexpected Error"
        assert data["request_id"] == "test-id"


def test_handle_error_debug_details(app, monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "true")
    with app.test_request_context("/debug"):
        response, status = error_handlers._handle_error(ValueError("boom"), 400, "Bad Request")
        data = response.get_json()

        assert status == 400
        assert data["message"] == "Bad Request"
        assert "details" in data


def test_handle_error_notify_calls(app, monkeypatch):
    called = {"value": False}

    def _fake_notify(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(error_handlers, "_notify_error_whatsapp", _fake_notify)

    with app.test_request_context("/notify"):
        response, status = error_handlers._handle_error(
            RuntimeError("fail"), 500, "Internal Error", severity="ERROR", notify=True
        )
        data = response.get_json()

        assert status == 500
        assert data["message"] == "Internal Error"
        assert called["value"] is True


def test_handle_error_db_commit_failure(app, monkeypatch):
    from multimax import db

    def _raise_commit():
        raise Exception("db fail")

    monkeypatch.setattr(db.session, "commit", _raise_commit)

    with app.test_request_context("/db-fail"):
        response, status = error_handlers._handle_error(ValueError("x"), 500, "Unexpected Error")
        data = response.get_json()

        assert status == 500
        assert data["message"] == "Unexpected Error"


def test_notify_error_whatsapp_sends(app, monkeypatch, db_session):
    from multimax.models import WhatsappConfig

    os.environ["WHATSAPP_SERVICE_URL"] = "http://example.com"

    config = WhatsappConfig(chave="alert_phone", valor="5511999999999", ativo=True)
    db_session.add(config)
    db_session.commit()

    payloads = []

    class DummyResponse:
        status_code = 200

    def _fake_post(url, json=None, timeout=None):
        payloads.append((url, json, timeout))
        return DummyResponse()

    import requests

    monkeypatch.setattr(requests, "post", _fake_post)

    with app.app_context():
        error_handlers._notify_error_whatsapp("Erro", "Falha", "container", "/rota", "req-1")

    assert payloads
    url, json_body, timeout = payloads[0]
    assert url == "http://example.com/send-alert"
    assert json_body["phone"] == "5511999999999"
    assert "Erro" in json_body["message"]
    assert timeout == 5
