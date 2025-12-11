# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

## v1.3.5 — 2025-12-10

- Corrige PDFs em branco ao aplicar o modelo de página; reescreve a finalização de PDF usando `PyPDF2` com transformação de escala e deslocamento (
  `multimax/routes/exportacao.py:56-143`).
- Remove colunas "Custo (R$)" e "Venda (R$)" do Relatório de Estoque; atualiza cabeçalhos, linhas e larguras (
  `multimax/routes/exportacao.py:400,419,455-467`).
- Oculta o sumário com âncoras no topo em dispositivos móveis com classes responsivas do Bootstrap (
  `templates/gestao.html:8`).
- Import dinâmico de `PyPDF2` para maior robustez em ambientes sem resolução de dependências (
  `multimax/routes/exportacao.py:83-85`).

Notas:
- A versão exibida na interface é obtida do último tag Git (`git describe --tags`).
- O modelo PDF utilizado, se presente, é `templates/ModeloBasePDF.pdf`.

