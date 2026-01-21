from multimax.module_registry import get_active_module_labels


def test_get_active_module_labels_empty():
    assert get_active_module_labels([]) == []


def test_get_active_module_labels_unknown_blueprints_ignored():
    assert get_active_module_labels(["foo", "bar"]) == []


def test_get_active_module_labels_returns_expected_labels_in_registry_order():
    # Ordem deve seguir o MODULE_REGISTRY, não a ordem de entrada.
    blueprints = ["notificacoes", "ciclos", "estoque_producao"]
    assert get_active_module_labels(blueprints) == [
        "Gestão de Estoque",
        "Ciclos e Pagamentos",
        "Notificações",
    ]


def test_get_active_module_labels_handles_iterable_types():
    # Aceitar qualquer Iterable[str]
    blueprints = {"estoque_producao", "exportacao", "colaboradores", "ciclos", "notificacoes"}
    labels = get_active_module_labels(blueprints)
    assert labels == [
        "Gestão de Estoque",
        "Ciclos e Pagamentos",
        "Colaboradores e Escalas",
        "Relatórios e PDFs",
        "Notificações",
    ]
