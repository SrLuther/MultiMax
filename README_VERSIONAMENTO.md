# ⚠️ IMPORTANTE: Versionamento Automático

## 🚨 REGRA CRÍTICA

**NUNCA faça `git push` diretamente!**

**SEMPRE use um dos scripts de push com versionamento:**

### Windows (PowerShell):
```powershell
.\git-push-with-version.ps1
```

### Linux/Mac (Bash):
```bash
./git-push-with-version.sh
```

## 📋 Por quê?

O sistema de versionamento automático garante que:
- ✅ Toda versão enviada ao GitHub seja registrada
- ✅ CHANGELOG.md seja sempre atualizado
- ✅ Tags Git sejam criadas automaticamente
- ✅ Histórico de versões seja mantido

## 🔄 O que acontece automaticamente?

1. Detecta a versão atual
2. Incrementa a versão (patch por padrão)
3. Atualiza CHANGELOG.md, multimax/__init__.py, LEIA-ME.txt
4. Cria commit de versão
5. Cria tag Git
6. Faz push do branch
7. Faz push das tags

## 📚 Documentação Completa

Veja `VERSIONAMENTO_AUTOMATICO.md` para documentação completa.
