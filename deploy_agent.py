#!/usr/bin/env python3
"""
Deploy Agent - Serviço de Atualização Automática do MultiMax

Este serviço roda diretamente no HOST (fora do Docker) e é responsável por:
- Executar comandos Git (fetch, reset)
- Executar comandos Docker (build, down, up)

O MultiMax (container) faz requisições HTTP para este serviço, que então
executa os comandos no HOST.

ARQUITETURA:
- MultiMax (site): Faz POST para http://<host>:9000/deploy
- Deploy Agent (HOST): Executa comandos Git/Docker no HOST
- Segurança: Protegido por token via header Authorization: Bearer

REQUISITOS:
- Python 3.8+
- Flask
- Acesso ao diretório /opt/multimax
- Permissões para executar git e docker-compose

INSTALAÇÃO (como serviço systemd):
1. Copiar este arquivo para /opt/multimax/deploy_agent.py
2. Criar /etc/systemd/system/deploy-agent.service:
   [Unit]
   Description=MultiMax Deploy Agent
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/multimax
   ExecStart=/usr/bin/python3 /opt/multimax/deploy_agent.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target

3. Executar:
   sudo systemctl daemon-reload
   sudo systemctl enable deploy-agent
   sudo systemctl start deploy-agent

4. Verificar logs:
   sudo journalctl -u deploy-agent -f
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from functools import wraps

# Configuração
REPO_DIR = os.getenv('GIT_REPO_DIR', '/opt/multimax')
DEPLOY_AGENT_PORT = int(os.getenv('DEPLOY_AGENT_PORT', '9000'))
DEPLOY_AGENT_TOKEN = os.getenv('DEPLOY_AGENT_TOKEN', '')  # Opcional: token de segurança

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/deploy-agent.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def require_token(f):
    """Decorator para validar token de segurança (se configurado)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if DEPLOY_AGENT_TOKEN:
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if token != DEPLOY_AGENT_TOKEN:
                logger.warning(f'Tentativa de acesso sem token válido de {request.remote_addr}')
                return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def execute_command(command, description, cwd=None, timeout=300):
    """
    Executa um comando e retorna o resultado
    
    Args:
        command: Lista com comando e argumentos
        description: Descrição do comando para logs
        cwd: Diretório de trabalho
        timeout: Timeout em segundos (padrão 5 minutos)
    
    Returns:
        dict com 'success', 'returncode', 'stdout', 'stderr', 'duration'
    """
    start_time = datetime.now()
    cwd = cwd or REPO_DIR
    
    logger.info(f'Executando: {description}')
    logger.info(f'Comando: {" ".join(command)}')
    logger.info(f'Diretório: {cwd}')
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Não lançar exceção em erro
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Log resultado
        if result.returncode == 0:
            logger.info(f'{description} - Sucesso ({duration:.2f}s)')
            if result.stdout:
                logger.debug(f'STDOUT: {result.stdout[:500]}')
        else:
            logger.error(f'{description} - Falhou (código: {result.returncode}, {duration:.2f}s)')
            if result.stderr:
                logger.error(f'STDERR: {result.stderr[:500]}')
            if result.stdout:
                logger.debug(f'STDOUT: {result.stdout[:500]}')
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'duration': duration,
            'description': description
        }
    except subprocess.TimeoutExpired as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f'{description} - Timeout após {duration:.2f}s')
        return {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': f'Timeout após {timeout}s',
            'duration': duration,
            'description': description,
            'error': 'timeout'
        }
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f'{description} - Erro: {str(e)} ({duration:.2f}s)')
        return {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'duration': duration,
            'description': description,
            'error': 'exception'
        }

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    return jsonify({
        'ok': True,
        'service': 'deploy-agent',
        'version': '1.0.0',
        'repo_dir': REPO_DIR,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/deploy', methods=['POST'])
@require_token
def deploy():
    """
    Endpoint principal de deploy
    
    Executa a sequência fixa de comandos:
    1. git fetch origin
    2. git reset --hard origin/nova-versao-deploy
    3. docker-compose build --no-cache
    4. docker-compose down
    5. docker-compose up -d
    
    Parâmetros JSON (opcional):
        force (bool): Se True, força atualização mesmo se já estiver atualizado
    """
    # Validar diretório do repositório
    if not os.path.exists(REPO_DIR):
        error_msg = f'Diretório do repositório não encontrado: {REPO_DIR}'
        logger.error(error_msg)
        return jsonify({'ok': False, 'error': error_msg}), 400
    
    if not os.path.exists(os.path.join(REPO_DIR, '.git')):
        error_msg = f'Diretório .git não encontrado em: {REPO_DIR}'
        logger.error(error_msg)
        return jsonify({'ok': False, 'error': error_msg}), 400
    
    # Obter parâmetros (opcional)
    force = False
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
    except Exception:
        pass
    
    logger.info(f'Iniciando deploy (force={force})')
    
    # Verificar se há atualização disponível (a menos que seja forçado)
    if not force:
        try:
            fetch_result = execute_command(
                ['git', 'fetch', 'origin', 'nova-versao-deploy', '--prune'],
                'Verificando atualizações disponíveis',
                timeout=30
            )
            
            if not fetch_result['success']:
                logger.warning(f'Erro ao fazer fetch: {fetch_result["stderr"]}')
            
            # Verificar commits
            local_result = execute_command(
                ['git', 'rev-parse', 'HEAD'],
                'Obtendo commit local',
                timeout=5
            )
            remote_result = execute_command(
                ['git', 'rev-parse', 'origin/nova-versao-deploy'],
                'Obtendo commit remoto',
                timeout=5
            )
            
            if (local_result['success'] and remote_result['success'] and
                local_result['stdout'].strip() == remote_result['stdout'].strip()):
                logger.info('Sistema já está atualizado')
                return jsonify({
                    'ok': False,
                    'error': 'Sistema já está atualizado',
                    'already_up_to_date': True,
                    'local_commit': local_result['stdout'].strip(),
                    'remote_commit': remote_result['stdout'].strip()
                }), 200
        except Exception as e:
            logger.warning(f'Erro ao verificar atualização disponível: {e}. Prosseguindo...')
    
    # Sequência de comandos fixa
    commands = [
        (['git', 'fetch', 'origin'], 'Fetch do repositório remoto', 30),
        (['git', 'reset', '--hard', 'origin/nova-versao-deploy'], 'Reset para branch remoto', 10),
        (['docker-compose', 'build', '--no-cache'], 'Rebuild completo do container (sem cache)', 600),  # 10 minutos para build
        (['docker-compose', 'down'], 'Parando containers Docker', 60),
        (['docker-compose', 'up', '-d'], 'Iniciando containers Docker', 60),
    ]
    
    results = []
    total_duration = 0.0
    
    try:
        for command, description, timeout in commands:
            result = execute_command(command, description, timeout=timeout)
            results.append(result)
            total_duration += result['duration']
            
            if not result['success']:
                error_msg = f'Erro ao executar: {description}'
                error_details = result.get('stderr', 'Sem detalhes')
                
                logger.error(f'{error_msg}: {error_details[:500]}')
                
                return jsonify({
                    'ok': False,
                    'error': error_msg,
                    'details': error_details[:1000],  # Limitar tamanho
                    'failed_step': description,
                    'results': results,
                    'duration': total_duration
                }), 500
        
        # Sucesso
        logger.info(f'Deploy concluído com sucesso em {total_duration:.2f}s')
        return jsonify({
            'ok': True,
            'message': 'Deploy concluído com sucesso',
            'results': results,
            'duration': total_duration,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f'Erro inesperado durante deploy: {str(e)}'
        logger.error(error_msg, exc_info=True)
        
        return jsonify({
            'ok': False,
            'error': error_msg,
            'results': results,
            'duration': total_duration
        }), 500

@app.route('/status', methods=['GET'])
@require_token
def status():
    """Retorna status atual do Deploy Agent e do repositório"""
    status_info = {
        'ok': True,
        'service': 'deploy-agent',
        'repo_dir': REPO_DIR,
        'repo_exists': os.path.exists(REPO_DIR),
        'git_exists': os.path.exists(os.path.join(REPO_DIR, '.git')) if REPO_DIR else False,
        'timestamp': datetime.now().isoformat()
    }
    
    # Tentar obter commit atual
    if status_info['git_exists']:
        try:
            result = execute_command(
                ['git', 'rev-parse', 'HEAD'],
                'Status: Obtendo commit atual',
                timeout=5
            )
            if result['success']:
                status_info['current_commit'] = result['stdout'].strip()
        except Exception:
            pass
    
    return jsonify(status_info)

if __name__ == '__main__':
    logger.info('=' * 60)
    logger.info('MultiMax Deploy Agent iniciando...')
    logger.info(f'Repositório: {REPO_DIR}')
    logger.info(f'Porta: {DEPLOY_AGENT_PORT}')
    logger.info(f'Token: {"Configurado" if DEPLOY_AGENT_TOKEN else "Não configurado (desabilitado)"}')
    logger.info('=' * 60)
    
    # Validar diretório do repositório
    if not os.path.exists(REPO_DIR):
        logger.error(f'Diretório do repositório não encontrado: {REPO_DIR}')
        logger.error('Configure a variável de ambiente GIT_REPO_DIR ou ajuste o código')
        sys.exit(1)
    
    if not os.path.exists(os.path.join(REPO_DIR, '.git')):
        logger.warning(f'Diretório .git não encontrado em: {REPO_DIR}')
        logger.warning('O serviço iniciará, mas operações Git falharão')
    
    # Iniciar servidor Flask
    app.run(
        host='0.0.0.0',  # Aceitar conexões externas
        port=DEPLOY_AGENT_PORT,
        debug=False,  # Nunca em produção
        threaded=True
    )
