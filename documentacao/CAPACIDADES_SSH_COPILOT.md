# Capacidades SSH do GitHub Copilot

## ✅ CONFIRMADO: SSH TOTALMENTE FUNCIONAL E NÃO-INTERATIVO

**Última atualização:** 24 de janeiro de 2026

Este documento registra oficialmente que o projeto possui acesso SSH automatizado à VPS, sem necessidade de senha ou passphrase.

---

## 🎯 Host oficial

Todo acesso remoto deve ser feito EXCLUSIVAMENTE através do alias:

```bash
ssh multimax
```

Este alias está configurado em:

`C:\Users\Ciano\.ssh\config`

Com:

- Usuário: multimax
- Host: www.multimax.tec.br
- Chave: id_ed25519_nopass (SEM passphrase)
- KeepAlive: ativo
- Host checking: desabilitado

### 🚨 REGRA OBRIGATÓRIA PARA EXECUÇÕES SSH

✅ SEMPRE usar:

```bash
ssh multimax "comando"
```

Exemplo:

```bash
ssh multimax "whoami && hostname && pwd"
```

❌ NUNCA usar:

```bash
ssh root@...
ssh usuario@www.multimax.tec.br
ssh usuario@IP
```


## 📁 Caminho oficial do projeto na VPS

Todo comando de deploy, atualização ou manutenção deve ser executado dentro do diretório:

```
/opt/multimax
```

Banco de dados está localizado em:

```
/opt/multimax-data
```

Exemplo de uso:

```
ssh multimax "cd /opt/multimax && <comando>"
```

---

### Motivo técnico

Apenas o alias `multimax` utiliza a chave correta:

`C:\Users\Ciano\.ssh\id_ed25519_nopass`

Qualquer outro formato ignora essa configuração e cai na chave antiga:

`id_ed25519`

Essa chave antiga possui passphrase, o que quebra a automação e impede o Copilot de operar.
