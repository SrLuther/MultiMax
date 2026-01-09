# Instruções para Reconstruir Container Docker - Correção 502 Bad Gateway

## Objetivo
Corrigir o erro 502 Bad Gateway no site multimax.tec.br causado pela falta de dependências do sistema para WeasyPrint no container Docker.

## Alterações Realizadas

### Dockerfile Atualizado
- ✅ Adicionadas dependências do sistema para WeasyPrint:
  - `libgobject-2.0-0`
  - `libpango-1.0-0`
  - `libpangocairo-1.0-0`
  - `libcairo2`
  - `libffi-dev`
  - `shared-mime-info`
- ✅ Consolidação de todas as dependências do sistema em um único RUN
- ✅ Limpeza de caches do apt para manter imagem Docker limpa

### requirements.txt
- ✅ Já contém `weasyprint>=60.0` (sem alterações necessárias)

## Passos para Reconstruir na VPS

### 1. Conectar na VPS
```bash
ssh usuario@multimax.tec.br
```

### 2. Navegar para o diretório do projeto
```bash
cd /opt/multimax  # ou o caminho onde está o projeto
```

### 3. Atualizar código do Git
```bash
git fetch origin
git checkout nova-versao-deploy
git pull origin nova-versao-deploy
```

### 4. Verificar que o Dockerfile foi atualizado
```bash
grep -A 10 "Instala dependências do sistema" Dockerfile
# Deve mostrar as novas dependências do WeasyPrint
```

### 5. Parar o container atual
```bash
docker compose down
# ou
docker-compose down
```

### 6. Reconstruir a imagem Docker (forçar rebuild completo)
```bash
docker compose build --no-cache
# ou
docker-compose build --no-cache
```

**Nota**: O flag `--no-cache` garante que todas as camadas sejam reconstruídas, incluindo a instalação das novas dependências do sistema.

### 7. Subir o container reconstruído
```bash
docker compose up -d
# ou
docker-compose up -d
```

### 8. Verificar logs do container
```bash
docker compose logs -f --tail=50
# ou
docker-compose logs -f --tail=50
```

**Verificar que não há erros de importação do WeasyPrint**. Deve aparecer algo como:
```
[OK] Flask importado
[OK] multimax importado
[OK] Modelos importados
[OK] Rotas importadas
[OK] Aplicação criada com sucesso!
```

### 9. Verificar que o Flask está ouvindo na porta 5000
```bash
curl -I http://127.0.0.1:5000
# Deve retornar: HTTP/1.1 200 OK ou 302 Found (redirecionamento)
```

### 10. Verificar status do container
```bash
docker compose ps
# ou
docker-compose ps
# Deve mostrar status "Up" para o container multimax
```

### 11. Testar acesso externo
```bash
curl -I https://multimax.tec.br
# Deve retornar: HTTP/2 200 ou 302 (não mais 502 Bad Gateway)
```

## Verificações Adicionais

### Se o erro persistir:

1. **Verificar logs detalhados:**
```bash
docker compose logs multimax | grep -i error
docker compose logs multimax | grep -i traceback
docker compose logs multimax | grep -i weasyprint
```

2. **Verificar se WeasyPrint foi instalado corretamente:**
```bash
docker compose exec multimax python -c "from weasyprint import HTML; print('WeasyPrint OK')"
```

3. **Verificar se as dependências do sistema estão instaladas:**
```bash
docker compose exec multimax dpkg -l | grep -E "libgobject|libpango|libcairo|libffi"
```

4. **Reconstruir com logs verbosos:**
```bash
docker compose build --no-cache --progress=plain
```

## Estrutura Final do Dockerfile

```dockerfile
# Instala dependências do sistema necessárias (gcc, git e bibliotecas para WeasyPrint)
RUN apt-get update && \
    apt-get install -y \
        gcc \
        git \
        libgobject-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libffi-dev \
        shared-mime-info && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

## Notas Técnicas

- ✅ **Dependências do sistema** (apt) estão no Dockerfile
- ✅ **Pacotes Python** (pip) estão no requirements.txt
- ✅ **Limpeza de caches** do apt para manter imagem limpa
- ✅ **WeasyPrint** já está no requirements.txt (sem alterações)

## Versão
- **Tag**: v2.3.33
- **Branch**: nova-versao-deploy
- **Commit**: `59ef817` (fix docker) + `5af7998` (version bump)

## Sucesso Esperado

Após seguir todos os passos:
- ✅ Container sobe sem erros
- ✅ Flask inicia corretamente
- ✅ WeasyPrint importa sem erros
- ✅ `curl http://127.0.0.1:5000` retorna 200/302
- ✅ `curl https://multimax.tec.br` retorna 200/302 (não mais 502)
- ✅ Site acessível publicamente
