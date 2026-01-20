# Migrações de Uso Único

Este diretório contém scripts de migração que são executados **uma única vez** durante o deploy.

## 📋 Instruções de Uso

### No VPS (Produção):
```bash
cd /caminho/do/projeto
python one-time-migrations/2026_01_21_add_setor_to_collaborator.py
```

### Após Execução Bem-Sucedida:
Os scripts podem ser **removidos com segurança** após confirmação de que a migração foi aplicada em todos os ambientes (dev, staging, produção).

## 🗑️ Limpeza

Quando **TODAS** as seguintes condições forem atendidas:
- ✅ Script executado com sucesso no dev
- ✅ Script executado com sucesso no VPS de produção
- ✅ Aplicação funcionando normalmente há pelo menos 7 dias
- ✅ Backup do banco de dados realizado

**Então você pode deletar este diretório inteiro:**
```bash
rm -rf one-time-migrations
```

## 📝 Convenção de Nomenclatura

`YYYY_MM_DD_descricao_da_migracao.py`

Exemplo: `2026_01_21_add_setor_to_collaborator.py`

## ⚠️ IMPORTANTE

**NÃO DELETE** enquanto não tiver certeza de que:
1. A migração rodou com sucesso em produção
2. O sistema está estável
3. Você tem backup do banco de dados
