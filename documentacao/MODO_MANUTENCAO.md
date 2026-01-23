# Modo de Manutenção do Sistema MultiMax

## 📋 Descrição

O modo de manutenção permite bloquear completamente o acesso ao sistema MultiMax, exibindo uma página institucional elegante que comunica aos usuários que o sistema está temporariamente indisponível.

## 🎯 Características

- **Bloqueio completo**: Nenhuma rota, API ou funcionalidade do sistema fica acessível
- **Sem inicialização**: Banco de dados, blueprints e serviços não são carregados
- **Página estática**: Design minimalista premium e institucional
- **Reversível**: Controlado por uma única variável de ambiente
- **Status HTTP 503**: Retorna código apropriado com header `Retry-After`

## 🚀 Como Ativar

### 1. Via Variável de Ambiente

Defina a variável `MAINTENANCE_MODE` como `true`:

```bash
export MAINTENANCE_MODE=true
```

Ou no Windows PowerShell:

```powershell
$env:MAINTENANCE_MODE = "true"
```

### 2. Via arquivo .env ou .env.txt

Adicione ou edite a linha:

```env
MAINTENANCE_MODE=true
```

### 3. Reiniciar a aplicação

Após definir a variável, reinicie o servidor:

```bash
# Para desenvolvimento
python app.py

# Para produção com Docker
docker-compose restart
```

## ✅ Como Desativar

### Método 1: Remover a variável

```bash
unset MAINTENANCE_MODE
```

Ou no Windows PowerShell:

```powershell
Remove-Item Env:MAINTENANCE_MODE
```

### Método 2: Definir como false

```bash
export MAINTENANCE_MODE=false
```

Ou editar `.env.txt`:

```env
MAINTENANCE_MODE=false
```

Depois, reinicie a aplicação.

## 🎨 Design da Página

A página de manutenção possui:

- **Tipografia**: Inter (Google Fonts) com fallback para fontes system
- **Paleta**: Tons neutros e sofisticados (cinza claro, grafite)
- **Layout**: Centralizado vertical e horizontalmente
- **Animação**: Fade-in sutil de 0.8s
- **Responsivo**: Adapta-se perfeitamente a mobile, tablet e desktop

## 📝 Texto Exibido

```
MultiMax

Sistema temporariamente em manutenção

Estamos realizando ajustes técnicos para garantir estabilidade, 
segurança e continuidade do serviço. Durante esse período, 
o acesso ao sistema permanece indisponível.

───

A normalização do acesso ocorrerá conforme a conclusão dos 
procedimentos técnicos necessários, incluindo etapas que 
dependem de validações e serviços de terceiros.

Agradecemos a compreensão.
```

## ⚙️ Comportamento Técnico

Quando `MAINTENANCE_MODE=true`:

1. ✅ Flask app é criado
2. ❌ Banco de dados **não** é inicializado
3. ❌ Blueprints **não** são registrados
4. ❌ Nenhuma rota interna é carregada
5. ✅ Middleware `before_request` intercepta **todas** as requisições
6. ✅ Retorna página estática com HTTP 503

## 🔍 Verificação

Para verificar se o modo de manutenção está ativo:

```bash
# Verificar variável de ambiente
echo $MAINTENANCE_MODE

# Testar acesso ao sistema
curl -I https://multimax.tec.br
# Deve retornar: HTTP/1.1 503 Service Unavailable
```

No log da aplicação, você verá:

```
⚠️  MODO DE MANUTENÇÃO ATIVO - Sistema bloqueado
```

## 🛡️ Segurança

- Nenhuma informação sensível é exposta
- Banco de dados não é acessado
- Nenhuma lógica de negócio é executada
- Página totalmente estática e segura

## 📌 Casos de Uso

Use o modo de manutenção quando:

- Realizar migração de banco de dados
- Atualizar infraestrutura crítica
- Fazer deploy de mudanças breaking
- Executar manutenção preventiva
- Aguardar validações externas (DNS, certificados, etc)

## 🎯 Benefícios

- **Comunicação profissional**: Linguagem institucional e preventiva
- **Controle total**: Sistema completamente pausado
- **Reversão instantânea**: Basta alterar uma variável
- **Preservação do código**: Nada é removido ou modificado
- **Performance**: Mínimo de recursos consumidos
