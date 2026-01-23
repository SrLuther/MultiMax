# ✅ MultiMax Operation Checklists

> Checklists para operação segura e confiável

---

## 🚀 Checklist Pré-Deploy

Validar antes de fazer deploy em produção:

```
PREPARAÇÃO DO SERVIDOR
─────────────────────────
[ ] Ubuntu 24.04 LTS instalado e atualizado
[ ] Mínimo 2GB RAM disponível
[ ] Mínimo 10GB disco livre
[ ] Acesso root/sudo confirmado
[ ] Conexão SSH funcionando
[ ] Domínio DNS aponta para servidor
[ ] Porta 80, 443, 22 abertas

REPOSITÓRIO
─────────────────────────
[ ] Código testado localmente
[ ] Todas as dependências em requirements.txt
[ ] Migrations pendentes aplicadas
[ ] Variáveis de ambiente documentadas
[ ] .env adicionado a .gitignore
[ ] Testes passando (pytest)

SEGURANÇA
─────────────────────────
[ ] SECRET_KEY alterada (32+ chars aleatórios)
[ ] DEBUG=false em produção
[ ] Certificado SSL válido (Let's Encrypt)
[ ] Firewall planejado
[ ] Backups testados
[ ] Senhas banco alteradas do padrão
[ ] CORS configurado
[ ] Rate limiting ativado

DOCUMENTAÇÃO
─────────────────────────
[ ] README.md atualizado
[ ] Runbook de operação criado
[ ] Contatos de suporte documentados
[ ] Plano de incident response
[ ] Arquivo de configuração comentado
```

---

## 📋 Checklist de Deploy

Executar durante deploy:

```
ANTES DO DEPLOY
─────────────────────────
[ ] Backup atual do banco feito
[ ] Código alterado reviewado
[ ] Logs antigos arquivados
[ ] Notificar usuários de manutenção
[ ] Ativar modo manutenção (opcional)

DURANTE O DEPLOY
─────────────────────────
[ ] Parar aplicação: sudo systemctl stop multimax
[ ] Fazer backup BD: sudo multimax-db-backup.sh
[ ] Git pull latest: cd app && git pull origin main
[ ] Instalar deps: pip install -r requirements.txt
[ ] Aplicar migrations: FLASK_APP=app.py flask db upgrade
[ ] Executar testes: pytest tests/
[ ] Iniciar aplicação: sudo systemctl start multimax
[ ] Verificar logs: sudo journalctl -u multimax -f
[ ] Testar endpoint: curl https://seu-dominio.com/
[ ] Testar login: Acessar via browser
[ ] Verificar BD: Testes funcionando?

DEPOIS DO DEPLOY
─────────────────────────
[ ] Todos os testes passando
[ ] Sem erros críticos nos logs
[ ] Requisitos normais respondendo
[ ] Desativar modo manutenção
[ ] Notificar usuários de conclusão
[ ] Documentar mudanças em changelog
[ ] Monitorar por 30min para erros
```

---

## 📅 Checklist Semanal

Executar uma vez por semana:

```
SEGUNDA-FEIRA (00:00 UTC)
─────────────────────────
[ ] Revisão de logs de erro: journalctl -u multimax -p err
[ ] Verificar espaço em disco: df -h /opt/multimax
[ ] Status geral: multimax-status.sh
[ ] Testes de conectividade: curl https://seu-dominio.com
[ ] Verificar jobs agendados rodaram: grep multimax /var/log/cron

BACKUP AUTOMATIZADO
─────────────────────────
[ ] BD backup completado: ls -lt backups/ | head
[ ] Backup transferido para externa (se configurado)
[ ] Integridade de backup testada
[ ] Espaço de backup não > 50% disco

PERFORMANCE
─────────────────────────
[ ] CPU média normal: top
[ ] Memória não crescendo: free -h
[ ] Disco não crescendo acelerado: du -sh /opt/multimax
[ ] Requisições lentes? Analisar logs
[ ] Queries BD lentes? Analisar postgresql.log

SEGURANÇA
─────────────────────────
[ ] Certificado SSL válido por quantos dias: certbot certificates
[ ] Atualizações de SO disponíveis: apt list --upgradable
[ ] Logs de acesso anormal: grep 401 /var/log/nginx/multimax_access.log
```

---

## 📈 Checklist Mensal

Executar uma vez ao mês:

```
1º DIA DO MÊS
─────────────────────────
[ ] Atualizar SO: sudo apt-get update && sudo apt-get upgrade
[ ] Atualizar dependências Python: pip list --outdated
[ ] Revisar PostgreSQL logs: grep ERROR /var/log/postgresql.log
[ ] Teste de restore: multimax-db-restore.sh <backup-anterior>
[ ] Verificar espaço backups: du -sh /opt/multimax/backups

SEGURANÇA MENSAL
─────────────────────────
[ ] Review de acessos SSH: grep "Accepted\|Failed" /var/log/auth.log
[ ] Verificar usuários sistema: getent passwd
[ ] Testar firewall regras: sudo ufw status
[ ] SSL cert válido por 30+ dias? certbot certificates
[ ] Banco de dados otimizado: VACUUM ANALYZE

PERFORMANCE ANÁLISE
─────────────────────────
[ ] Revisar métricas de CPU/MEM do mês
[ ] Analisar requisições lentas (> 5s)
[ ] Verificar tamanho BD crescimento
[ ] Queries lentas reportadas? Analisar EXPLAIN ANALYZE

OPERACIONAL
─────────────────────────
[ ] Número de erros 5xx no mês? Investigar
[ ] Tempo de resposta médio? Documentar
[ ] Uptime do período? Registrar
[ ] Mudanças documentadas? Review
```

---

## ⚠️ Checklist de Emergency (Outage)

Usar quando servidor está down:

```
DIAGNÓSTICO
─────────────────────────
[ ] Aplicação respondendo? curl https://seu-dominio.com
[ ] PostgreSQL ativo? sudo systemctl status postgresql
[ ] Nginx ativo? sudo systemctl status nginx
[ ] Memória disponível? free -h
[ ] Disco cheio? df -h
[ ] Rede funcionando? ping 8.8.8.8

RECUPERAÇÃO RÁPIDA
─────────────────────────
[ ] Parar todos serviços: sudo systemctl stop multimax nginx postgresql
[ ] Aguardar 30s
[ ] Reiniciar PostgreSQL: sudo systemctl start postgresql
[ ] Aguardar 10s (setup)
[ ] Reiniciar Nginx: sudo systemctl start nginx
[ ] Reiniciar MultiMax: sudo systemctl start multimax
[ ] Esperar 20s para aquecimento
[ ] Testar: curl https://seu-dominio.com
[ ] Monitorar logs: journalctl -u multimax -f

SE AINDA FALHAR
─────────────────────────
[ ] Ver erro: sudo journalctl -u multimax -n 100 -p err
[ ] Testar em foreground: cd /opt/multimax/app && python app.py
[ ] Banco acessível? psql -U multimax -d multimax
[ ] Arquivo .env correto? cat /opt/multimax/.env
[ ] Permissões ok? ls -la /opt/multimax/
[ ] Disk space? du -sh /var/log/
```

---

## 🔄 Checklist de Atualização de Código

Quando fazer deploy de novo código:

```
PRÉ-MERGE (Desenvolvimento)
─────────────────────────
[ ] Todos os testes passam: pytest
[ ] Linting ok: pylint, bandit
[ ] Sem conflitos com main
[ ] Code review aprovado
[ ] Changelog atualizado

PRÉ-DEPLOY (Produção)
─────────────────────────
[ ] Backup BD feito: multimax-db-backup.sh
[ ] Testes de integração passam: pytest tests/integration/
[ ] Documentação atualizada
[ ] Performance testada (stress test)
[ ] Rollback plan documentado

DURANTE DEPLOY
─────────────────────────
[ ] Git pull origin main
[ ] Instalar novo deps: pip install -r requirements.txt
[ ] Executar migrations: FLASK_APP=app.py flask db upgrade
[ ] Testar em staging primeiro (se tiver)
[ ] Iniciar e monitorar por erros

PÓS-DEPLOY
─────────────────────────
[ ] Testes funcionais ok
[ ] Sem novos erros 5xx
[ ] Performance aceitável
[ ] Usuários afetados positivamente
[ ] Changelog marcado como released
[ ] Tag git criado: git tag v2.x.x
```

---

## 💻 Checklist Trimestral (A cada 3 meses)

```
REVIEW DE ARQUITETURA
─────────────────────────
[ ] Documentação ainda acurada?
[ ] Configuração nginx otimizada?
[ ] PostgreSQL tunning revisto?
[ ] Capacidade projeto vs crescimento real
[ ] Plano de escalabilidade atualizado?

TESTES E QUALIDADE
─────────────────────────
[ ] Coverage de testes >= 90%?
[ ] Testes de carga executados?
[ ] Testes de segurança realizados?
[ ] Dependências vulneráveis? (safety check)
[ ] Código review continua rigoroso?

SEGURANÇA REVIEW
─────────────────────────
[ ] Audit de acessos (SSH, sudo)
[ ] Certificados SSL revistos (renovação próxima?)
[ ] Logs de segurança analisados
[ ] Plano de incident response testado
[ ] Backup restoration testado
[ ] Firewall rules ainda apropriadas?

PLANEJAMENTO FUTURO
─────────────────────────
[ ] Recursos crescimento esperado?
[ ] Otimizações necessárias?
[ ] Novas features planejadas?
[ ] Padrão de uso mudou?
[ ] Novas integrações necessárias?
```

---

## 📊 Template de Log de Operação

Manter registro de mudanças:

```
DATE: 2025-01-15
TIME: 14:30 UTC
OPERATOR: João Silva
ACTION: Deploy de código v2.5.0

CHANGES:
- Novos campos em colaboradores
- Otimização de query de estoque
- Atualização de UI dashboard

BACKUP BEFORE: multimax_db_20250115_143000.sql.gz
ROLLBACK PLAN: Revert para commit abc123def

DURATION: 5 minutos
STATUS: ✅ Sucesso

TESTING:
✓ Testes unitários
✓ Testes integração
✓ Teste manual login
✓ Teste upload arquivo

MONITORING (Next 30min):
- CPU: Média 25% (normal)
- Memória: 380MB (normal)
- Erros 5xx: 0
- Requisições/min: 120 (normal)

NOTES:
Usuários notificados de manutenção 15min antes.
Nenhum issue reportado. Monitorado por 1h após.

═════════════════════════════════════════════════════════════════
```

---

**Última revisão:** Janeiro 2025

Imprima e coloque na parede do seu datacenter! 📌
