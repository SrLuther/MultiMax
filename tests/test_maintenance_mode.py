"""
Testes para o Modo de ManutenÃ§Ã£o do Sistema MultiMax

Este arquivo demonstra como testar o modo de manutenÃ§Ã£o.
"""

import os

from multimax import create_app


class TestMaintenanceMode:
    """Testes para o modo de manutenÃ§Ã£o"""

    def test_maintenance_mode_disabled_by_default(self):
        """Sistema deve funcionar normalmente quando MAINTENANCE_MODE nÃ£o estÃ¡ definido"""
        # Garantir que variÃ¡vel nÃ£o estÃ¡ definida
        if "MAINTENANCE_MODE" in os.environ:
            del os.environ["MAINTENANCE_MODE"]

        app = create_app()
        assert app is not None
        assert app.config.get("DB_OK") is not None

    def test_maintenance_mode_when_false(self):
        """Sistema deve funcionar normalmente quando MAINTENANCE_MODE=false"""
        os.environ["MAINTENANCE_MODE"] = "false"

        try:
            app = create_app()
            assert app is not None
            # Sistema deve inicializar banco normalmente
            assert app.config.get("SQLALCHEMY_DATABASE_URI") is not None
        finally:
            if "MAINTENANCE_MODE" in os.environ:
                del os.environ["MAINTENANCE_MODE"]

    def test_maintenance_mode_when_active(self):
        """Quando MAINTENANCE_MODE=true, sistema deve retornar pÃ¡gina de manutenÃ§Ã£o"""
        os.environ["MAINTENANCE_MODE"] = "true"

        try:
            app = create_app()

            with app.test_client() as client:
                # Testar rota raiz
                response = client.get("/")
                assert response.status_code == 503
                assert b"temporariamente em manuten" in response.data

                # Testar rota de login
                response = client.get("/login")
                assert response.status_code == 503

                # Testar rota de API
                response = client.get("/api/v1/usuarios")
                assert response.status_code == 503

                # Verificar header Retry-After
                assert "Retry-After" in response.headers

        finally:
            if "MAINTENANCE_MODE" in os.environ:
                del os.environ["MAINTENANCE_MODE"]

    def test_maintenance_page_content(self):
        """PÃ¡gina de manutenÃ§Ã£o deve conter texto correto"""
        os.environ["MAINTENANCE_MODE"] = "true"

        try:
            app = create_app()

            with app.test_client() as client:
                response = client.get("/")

                # Verificar conteÃºdo HTML
                html = response.data.decode("utf-8")

                # TÃ­tulo
                assert "Sistema temporariamente em manuten" in html

                # Texto secundÃ¡rio
                assert "Estamos realizando ajustes t" in html
                assert "estabilidade, seguran" in html

                # Estimativa
                assert "normaliza" in html
                assert "procedimentos t" in html

                # Nota final
                assert "Agradecemos a compreens" in html

                # Tipografia
                assert "Inter" in html or "IBM Plex Sans" in html

        finally:
            if "MAINTENANCE_MODE" in os.environ:
                del os.environ["MAINTENANCE_MODE"]

    def test_maintenance_mode_no_database_connection(self):
        """Quando em manutenÃ§Ã£o, banco de dados nÃ£o deve ser inicializado"""
        os.environ["MAINTENANCE_MODE"] = "true"

        try:
            app = create_app()

            # Verificar que DB_OK nÃ£o foi definido (banco nÃ£o foi inicializado)
            assert app.config.get("DB_OK") is None

        finally:
            if "MAINTENANCE_MODE" in os.environ:
                del os.environ["MAINTENANCE_MODE"]


if __name__ == "__main__":
    # Executar testes manualmente
    import sys

    print("=" * 60)
    print("TESTES DO MODO DE MANUTENÃ‡ÃƒO")
    print("=" * 60)
    print()

    test = TestMaintenanceMode()

    tests = [
        ("Modo desabilitado (padrÃ£o)", test.test_maintenance_mode_disabled_by_default),
        ("Modo explicitamente false", test.test_maintenance_mode_when_false),
        ("Modo ativado (true)", test.test_maintenance_mode_when_active),
        ("ConteÃºdo da pÃ¡gina", test.test_maintenance_page_content),
        ("Banco nÃ£o inicializado", test.test_maintenance_mode_no_database_connection),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"â–¶ {name}...", end=" ")
            test_func()
            print("âœ… PASSOU")
            passed += 1
        except AssertionError as e:
            print("âŒ FALHOU")
            print(f"  Erro: {e}")
            failed += 1
        except Exception as e:
            print("âŒ ERRO")
            print(f"  ExceÃ§Ã£o: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Resultados: {passed} passaram, {failed} falharam")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
