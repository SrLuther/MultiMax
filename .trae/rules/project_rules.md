Contexto do Projeto
– MultiMax é um sistema real, em produção ou pré-produção
– Código foi majoritariamente gerado por IA, com padrões mistos
– Manutenibilidade e previsibilidade são mais importantes que “elegância”

Arquitetura
– Respeitar a estrutura existente
– Não mover arquivos sem necessidade explícita
– Não criar novos padrões se já existir um funcional

HTML / Templates
– Alterações visuais devem priorizar CSS, não HTML
– Evitar duplicação de estilos
– Mobile-first apenas quando solicitado

CSS
– Mudanças devem ser locais e específicas
– Evitar seletores globais agressivos
– Responsividade sem quebrar desktop

JS / Python / Backend
– Nunca alterar lógica de negócio sem pedido explícito
– Mudanças devem ser incrementais e isoladas
– Evitar efeitos colaterais

UX
– Não mudar textos, labels ou fluxos não mencionados
– Quando solicitado ajuste visual, aplicar apenas ao contexto descrito

Escopo rígido
– Se o usuário listar elementos específicos, mexer SOMENTE neles
– Ignorar qualquer outro elemento similar fora da lista

Finalização
– Após concluir a tarefa, encerrar execução
– Não sugerir melhorias extras automaticamente
– Não reabrir o problema resolvido

Execução em Sistema Gerado por IA

– Considerar o código como sensível a alterações amplas
– Priorizar mudanças mínimas e localizadas
– Nunca substituir blocos grandes de CSS
– Sempre adicionar regras novas e específicas

UI / CSS
– Ajustes visuais devem ser determinísticos
– Uma classe, um propósito
– Media query explícita para mobile
– Desktop intocável

Controle de risco:
– Se a ação não puder ser feita com segurança em um único passo,
  interromper e pedir instrução
– Caso contrário, EXECUTAR SEM COMENTAR
