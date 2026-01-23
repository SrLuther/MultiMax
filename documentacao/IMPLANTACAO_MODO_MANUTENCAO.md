# 🔧 Modo de Manutenção - Guia Rápido de Implantação

## ✅ Implementação Completa

O modo de manutenção foi implementado com sucesso no sistema MultiMax. Esta documentação serve como guia rápido de implantação e verificação.

---

## 📦 Arquivos Criados

### 1. Página HTML de Manutenção
- **Arquivo:** `templates/maintenance.html`
- **Descrição:** Página estática institucional com design minimalista premium
- **Características:**
  - Tipografia Inter (Google Fonts)
  - Paleta neutra e sofisticada
  - Fade-in animation
  - Totalmente responsivo
  - Texto exato conforme especificado

### 2. Lógica de Middleware
- **Arquivo:** `multimax/__init__.py`
- **Função:** `_setup_maintenance_mode()`
- **Comportamento:**
  - Intercepta TODAS as requisições quando `MAINTENANCE_MODE=true`
  - Retorna HTTP 503 com header `Retry-After: 3600`
  - Não inicializa banco de dados
  - Não registra blueprints
  - Não carrega rotas

### 3. Scripts de Gerenciamento
- **Linux/macOS:** `scripts/maintenance-mode.sh`
- **Windows:** `scripts/maintenance-mode.ps1`
- **Funcionalidades:**
  - Ativar modo de manutenção
  - Desativar modo de manutenção
  - Verificar status atual
  - Interface colorida e amigável

### 4. Documentação
- `documentacao/MODO_MANUTENCAO.md` — Documentação completa
- `documentacao/DOCKER_MAINTENANCE_MODE.md` — Guia para Docker
- `.env.example` — Exemplo de configuração
- `tests/test_maintenance_mode.py` — Testes automatizados
- `README.md` — Atualizado com seção de modo de manutenção
- `scripts/README.md` — Documentação dos scripts

---

## 🚀 Como Implantar em Produção

### Passo 1: Preparação (ANTES da manutenção)

1. **Teste local primeiro:**
   ```bash
   # No ambiente de desenvolvimento
   export MAINTENANCE_MODE=true
   python app.py
   
   # Acesse http://localhost:5000
   # Verifique se página de manutenção aparece
   ```

2. **Commit e push:**
   ```bash
   git add .
   git commit -m "feat: add maintenance mode feature"
   git push origin main
   ```

### Passo 2: Implantação no Servidor

1. **Fazer backup do banco de dados:**
   ```bash
   # Se SQLite
   cp /opt/multimax-data/estoque.db /opt/multimax-data/backups/estoque-$(date +%Y%m%d).db
   
   # Se PostgreSQL
   pg_dump -h host -U user database > backup-$(date +%Y%m%d).sql
   ```

2. **Atualizar código no servidor:**
   ```bash
   cd /opt/multimax
   git pull origin main
   ```

3. **Ativar modo de manutenção:**
   ```bash
   # Método 1: Usando script
   ./scripts/maintenance-mode.sh on
   
   # Método 2: Manualmente
   echo "MAINTENANCE_MODE=true" >> .env.txt
   ```

4. **Reiniciar aplicação:**
   ```bash
   # Se usando systemd
   sudo systemctl restart multimax
   
   # Se usando Docker
   docker-compose restart
   
   # Se usando PM2
   pm2 restart multimax
   ```

### Passo 3: Verificação

1. **Verificar logs:**
   ```bash
   # Procurar por mensagem de confirmação
   tail -f /var/log/multimax/app.log | grep "MANUTENÇÃO"
   
   # Deve aparecer:
   # ⚠️  MODO DE MANUTENÇÃO ATIVO - Sistema bloqueado
   ```

2. **Testar acesso externo:**
   ```bash
   curl -I https://multimax.tec.br
   
   # Deve retornar:
   # HTTP/1.1 503 Service Unavailable
   # Retry-After: 3600
   ```

3. **Verificar página no navegador:**
   - Acessar https://multimax.tec.br
   - Verificar se página institucional aparece
   - Confirmar texto e design

### Passo 4: Realizar Manutenção

Execute os procedimentos técnicos necessários:
- Migração de banco de dados
- Atualização de infraestrutura
- Deploy de novas versões
- Configuração de serviços externos

### Passo 5: Desativar e Restaurar

1. **Desativar modo de manutenção:**
   ```bash
   # Método 1: Usando script
   ./scripts/maintenance-mode.sh off
   
   # Método 2: Manualmente
   sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' .env.txt
   ```

2. **Reiniciar aplicação:**
   ```bash
   # Se usando systemd
   sudo systemctl restart multimax
   
   # Se usando Docker
   docker-compose restart
   ```

3. **Verificar restauração:**
   ```bash
   curl -I https://multimax.tec.br
   
   # Deve retornar:
   # HTTP/1.1 200 OK ou 302 Found (redirect para login)
   ```

4. **Testar funcionalidades críticas:**
   - Login
   - Acesso ao dashboard
   - Consultas ao banco de dados
   - APIs essenciais

---

## 🧪 Checklist de Implantação

### Pré-Implantação
- [ ] Código testado localmente
- [ ] Backup do banco de dados criado
- [ ] Stakeholders notificados
- [ ] Janela de manutenção agendada
- [ ] Plano de rollback preparado

### Durante Implantação
- [ ] Modo de manutenção ativado
- [ ] Página institucional visível
- [ ] Logs confirmam bloqueio do sistema
- [ ] Manutenção executada com sucesso

### Pós-Implantação
- [ ] Modo de manutenção desativado
- [ ] Sistema restaurado e funcional
- [ ] Funcionalidades críticas testadas
- [ ] Usuários notificados da normalização
- [ ] Documentação atualizada (se necessário)

---

## 🛡️ Medidas de Segurança

1. **Backup obrigatório** antes de ativar
2. **Teste em staging** antes de produção
3. **Monitoramento ativo** durante manutenção
4. **Plano de rollback** preparado
5. **Comunicação clara** com stakeholders

---

## 📊 Monitoramento Durante Manutenção

### Verificações automáticas
```bash
# Script de monitoramento simples
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://multimax.tec.br)
  if [ "$STATUS" = "503" ]; then
    echo "$(date) - ✅ Modo de manutenção ativo (HTTP 503)"
  else
    echo "$(date) - ⚠️  Status inesperado: HTTP $STATUS"
  fi
  sleep 60
done
```

### Métricas importantes
- Taxa de requisições recebidas
- Tempo de resposta da página estática
- Uso de recursos do servidor
- Logs de erros (não devem existir)

---

## 📞 Troubleshooting

### Problema: Página de manutenção não aparece

**Solução:**
1. Verificar variável de ambiente: `echo $MAINTENANCE_MODE`
2. Verificar logs: `grep -i manutenção /var/log/multimax/app.log`
3. Reiniciar aplicação: `sudo systemctl restart multimax`

### Problema: Sistema não restaura após desativar

**Solução:**
1. Verificar `.env.txt`: `cat .env.txt | grep MAINTENANCE`
2. Deve estar: `MAINTENANCE_MODE=false`
3. Reiniciar aplicação completamente
4. Verificar logs de erros durante inicialização

### Problema: Erro ao inicializar banco

**Solução:**
1. Desativar modo de manutenção
2. Verificar string de conexão do banco
3. Testar conexão manualmente
4. Restaurar backup se necessário

---

## ✨ Resumo Técnico

**Modo de manutenção ativo:**
- ✅ Flask app criado
- ❌ Banco de dados **não** inicializado
- ❌ Blueprints **não** registrados
- ❌ Rotas **não** carregadas
- ✅ Middleware intercepta todas as requisições
- ✅ Retorna HTTP 503 com página estática

**Reversão:**
- Alterar uma variável: `MAINTENANCE_MODE=false`
- Reiniciar aplicação
- Sistema volta ao normal instantaneamente

---

## 🎯 Conclusão

O modo de manutenção está **pronto para uso em produção** e atende todos os requisitos:

✅ Bloqueio completo do sistema  
✅ Página institucional elegante  
✅ Facilmente reversível  
✅ Não remove código existente  
✅ Documentação completa  
✅ Scripts de gerenciamento  
✅ Testes automatizados  

Para ativar em produção, siga o **Passo 2** deste guia.
