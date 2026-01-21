from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ModuleInfo:
    key: str
    label: str
    blueprint_names: tuple[str, ...]


MODULE_REGISTRY: tuple[ModuleInfo, ...] = (
    ModuleInfo(key="estoque", label="Gestão de Estoque", blueprint_names=("estoque",)),
    ModuleInfo(key="estoque_producao", label="Estoque de Produção", blueprint_names=("estoque_producao",)),
    ModuleInfo(key="ciclos", label="Ciclos e Pagamentos", blueprint_names=("ciclos",)),
    ModuleInfo(key="colaboradores", label="Colaboradores e Escalas", blueprint_names=("colaboradores",)),
    ModuleInfo(key="relatorios", label="Relatórios e PDFs", blueprint_names=("exportacao",)),
    ModuleInfo(key="notificacoes", label="Notificações", blueprint_names=("notificacoes",)),
)


def get_active_module_labels(blueprints: Iterable[str]) -> list[str]:
    """Retorna rótulos dos módulos ativos a partir dos blueprints registrados."""
    bp_set = set(blueprints)
    out: list[str] = []
    for m in MODULE_REGISTRY:
        if any(bp in bp_set for bp in m.blueprint_names):
            out.append(m.label)
    return out
