# Protocolo Obrigatório do GitHub Copilot

Data de vigência: 3 de fevereiro de 2026
Responsável: GitHub Copilot
Status: OBRIGATÓRIO - Sem exceções

---

## FLUXO DE TRABALHO IMUTÁVEL - EDIÇÃO COMUM

Toda modificação de código DEVE seguir este fluxo exatamente na ordem:

1. EDITAR arquivo(s)
   - replace_string_in_file() ou create_file()

2. VERIFICAR ERROS (IMEDIATAMENTE)
   - get_errors() (Verificação de tipos - Pylance)
   - flake8 arquivo.py (Verificação de estilo - docstrings, PEP8)

3. AVALIAR RESULTADO
   - OK (sem erros): Ir para passo 4
   - ERRO (com erros): Voltar ao passo 1 (corrigir), depois repetir passo 2

4. COMMITAR NO GIT
   - git add -A
   - git commit -m "mensagem descritiva"
   - git push

---

## FLUXO ESPECIAL: MANDE PRO GITHUB

Comando do usuário: "mande pro github" ou "deploy"

Fluxo automatizado:

1. INCREMENTAR VERSÃO
   - Detectar tipo de mudança (feat = MINOR, fix = PATCH, etc)
   - Atualizar version.txt
   - Atualizar CHANGELOG.md (topo)
   - Atualizar multimax/__init__.py (linha ~641)

2. VERIFICAR ERROS
   - get_errors() (Obrigatório)
   - flake8 *.py (Obrigatório)
   - Se houver: CORRIGIR E REPETIR

3. COMMITAR
   - git add CHANGELOG.md multimax/__init__.py version.txt arquivos_modificados
   - git commit -m "chore: Versão X.Y.Z - descrição"

4. CRIAR TAG GIT
   - git tag -a vX.Y.Z -m "Versão X.Y.Z - descrição"
   - git push origin vX.Y.Z

5. FAZER PUSH
   - git push origin nova-versao-deploy

6. DEPLOYER NA VPS
   - ssh multimax "cd /opt/multimax && git pull && docker-compose down && docker-compose up -d --build"

Resultado esperado: Tudo automático, sem intervenção do usuário

---

## REGRAS CRÍTICAS

1. NUNCA fazer commit com erros pendentes
2. NUNCA pular a verificação de erros (get_errors + flake8)
3. NUNCA ignorar warnings do VS Code
4. NUNCA versionear sem atualizar CHANGELOG
5. NUNCA esquecer de criar tag Git
6. NUNCA fazer deploy manualmente sem ser autorizado

---

## CHECKLIST PRÉ-COMMIT AUTOMÁTICO

Quando usuário disser "mande pro github":
- [ ] Versão (MAJOR/MINOR/PATCH) identificada
- [ ] version.txt incrementado
- [ ] CHANGELOG.md atualizado com entrada
- [ ] multimax/__init__.py versão sincronizada
- [ ] get_errors() executado (zero erros)
- [ ] flake8 executado (zero erros)
- [ ] Commit com todas as mudanças
- [ ] Tag Git criada (vX.Y.Z)
- [ ] Git push com tag
- [ ] VPS deployment automático

---

## VIOLAÇÕES

Se essas regras forem violadas:
1. O código será revertido
2. Os erros serão corrigidos
3. Será re-deployado corretamente

Sem discussão.

---

## REFERÊNCIA RÁPIDA

Apenas edição (sem versionamento):
- "Protocolo" = Executar get_errors() + flake8 e commitar se clean

Enviar para produção (com versionamento):
- "Mande pro github" = Fluxo completo + deploy

---

Vigência: Permanente até nova revisão
