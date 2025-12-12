# Changelog — Ajustes de Tabelas nos Relatórios de Carnes

Data: 2025-12-11

Principais mudanças aplicadas aos PDFs de relatório diário e semanal:

- Fonte das células reduzida para 8 e espaçamento de linha (leading) ajustado para 10, aumentando a densidade sem perder legibilidade.
- Larguras das colunas calculadas dinamicamente com base na largura útil da página para evitar vazamento de conteúdo:
  - Data/Hora: 1.2 in
  - Ref.: 0.9 in
  - Total (kg): 1.2 in
  - Recebedor: 1.5 in (ajustada automaticamente se necessário)
  - Fornecedor: ocupa o restante, com mínimo de 1.2 in
- Cabeçalho encurtado de “Total líquido (kg)” para “Total (kg)” para prevenir overflow visual e padronizar nomenclatura.
- Alinhamento à direita mantido na coluna de Totais; cabeçalho com fonte 8 para consistência visual.
- Quebra de linha em células (`wordWrap='LTR'`) para textos mais longos em Fornecedor e Recebedor sem ultrapassar os limites da tabela.

Ajustes complementares relacionados:

- Compatibilidade de timezone no cálculo de intervalos (diário/semanal) com `datetime.combine(...).replace(tzinfo=ZoneInfo('America/Sao_Paulo'))` para suportar Python anteriores ao 3.11.
- Correções de linter: uso de aliases `CleaningTaskModel` e `CleaningHistoryModel` nas rotas de exportação para evitar conflitos de símbolo.
- UI de Carnes: remoção de `_now_br` no template, passando `today_str` pela rota; largura do filtro “Tipo” ampliada para 360px para evitar truncamento do conteúdo.

