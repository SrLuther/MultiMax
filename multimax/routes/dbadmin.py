from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app, request, jsonify
from flask_login import login_required, current_user
import os
import shutil
import time
import subprocess
import socket
import logging
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from .. import db
from ..models import UserLogin, SystemLog, Incident, MetricHistory, Alert, MaintenanceLog, QueryLog, BackupVerification
from sqlalchemy import text
import json

try:
    import psutil  # type: ignore
except Exception:
    psutil = None

bp = Blueprint('dbadmin', __name__, url_prefix='/db')

# ============================================================================
# Utilitários de Detecção de Ambiente
# ============================================================================

def _is_docker_environment():
    """Detecta se estamos rodando em um container Docker"""
    return os.path.exists('/.dockerenv') or os.path.exists('/proc/self/cgroup')

def _can_write_to_git(git_dir):
    """
    Verifica se podemos escrever no diretório .git
    Retorna (pode_escrever, erro, is_docker)
    """
    is_docker = _is_docker_environment()
    
    # Em Docker, assumir que .git pode estar somente leitura
    # Tentar teste de escrita apenas se não for Docker ou se variável de ambiente permitir
    skip_write_test = is_docker and os.getenv('GIT_SKIP_WRITE_TEST', 'false').lower() != 'true'
    
    if skip_write_test:
        # Em Docker, assumir que pode estar somente leitura
        # Tentar operações Git mesmo assim (algumas funcionam em modo leitura)
        current_app.logger.info(f'Ambiente Docker detectado. Pulando teste de escrita em {git_dir}')
        return (False, None, is_docker)
    
    try:
        test_file = os.path.join(git_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return (True, None, is_docker)
        except (IOError, OSError, PermissionError) as perm_error:
            return (False, str(perm_error), is_docker)
    except Exception as e:
        current_app.logger.warning(f'Erro ao verificar permissões do .git: {e}')
        return (False, str(e), is_docker)

# ============================================================================
# Controle de Acesso
# ============================================================================

def _check_dev_access():
    """Verifica se o usuário tem permissão de desenvolvedor"""
    if not current_user.is_authenticated:
        return False
    return current_user.nivel == 'DEV'

def _log_unauthorized_access():
    """Registra tentativa de acesso não autorizada"""
    try:
        log = SystemLog()
        log.origem = 'Segurança'
        log.evento = 'acesso_negado'
        log.detalhes = f'Tentativa de acesso não autorizada à página Banco de Dados - Usuário: {current_user.username if current_user.is_authenticated else "Não autenticado"}'
        log.usuario = current_user.username if current_user.is_authenticated else 'Sistema'
        db.session.add(log)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

# ============================================================================
# Health Checks
# ============================================================================

def _check_database_health():
    """Verifica saúde do banco de dados"""
    try:
        start = time.time()
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        response_time = (time.time() - start) * 1000  # ms
        
        status = 'ok'
        if response_time > 1000:
            status = 'warning'
        if response_time > 5000:
            status = 'error'
        
        return {
            'status': status,
            'response_time_ms': round(response_time, 2),
            'message': f'Banco de dados respondendo em {response_time:.2f}ms' if status == 'ok' else f'Resposta lenta: {response_time:.2f}ms',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('database', 'connection_error', str(e))
        return {
            'status': 'error',
            'response_time_ms': None,
            'message': f'Erro de conexão: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_backend_health():
    """Verifica saúde do backend"""
    try:
        # Verifica se a aplicação Flask está respondendo
        start = time.time()
        with current_app.test_client() as client:
            response = client.get('/health')
            response_time = (time.time() - start) * 1000
        
        status = 'ok'
        if response.status_code != 200:
            status = 'error'
        elif response_time > 1000:
            status = 'warning'
        
        return {
            'status': status,
            'response_time_ms': round(response_time, 2),
            'status_code': response.status_code,
            'message': f'Backend respondendo (HTTP {response.status_code})' if status == 'ok' else f'Backend com problemas (HTTP {response.status_code})',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('backend', 'connection_error', str(e))
        return {
            'status': 'error',
            'response_time_ms': None,
            'status_code': None,
            'message': f'Erro ao verificar backend: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_nginx_health():
    """Verifica saúde do Nginx - testa portas 80 (HTTP) e 443 (HTTPS) e segue redirecionamentos"""
    try:
        # Função auxiliar para testar conexão em uma porta
        def _test_port(host, port, timeout=2):
            """Testa se uma porta está aberta e respondendo"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except Exception:
                return False
        
        # Função auxiliar para verificar redirecionamento HTTP → HTTPS
        def _check_http_redirect():
            """Verifica se HTTP redireciona para HTTPS"""
            try:
                # Cria um opener que segue redirecionamentos
                opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
                opener.addheaders = [('User-Agent', 'MultiMax-HealthCheck/1.0')]
                
                # Tenta fazer requisição HTTP para o hostname real
                req = urllib.request.Request('http://multimax.tec.br/', method='HEAD')
                response = opener.open(req, timeout=3)
                
                # Verifica se houve redirecionamento
                if hasattr(response, 'url') and response.url.startswith('https://'):
                    return True, 'HTTP redireciona para HTTPS'
                return True, 'HTTP respondendo'
            except urllib.error.HTTPError as e:
                # Alguns códigos HTTP ainda indicam que o servidor está respondendo
                if e.code in (301, 302, 303, 307, 308):
                    # Verifica o header Location
                    location = e.headers.get('Location', '')
                    if location.startswith('https://'):
                        return True, f'HTTP redireciona para HTTPS (código {e.code})'
                return False, f'HTTP retornou código {e.code}'
            except (urllib.error.URLError, socket.timeout, Exception) as e:
                return False, None
        
        # Testa porta 80 (HTTP)
        port_80_ok = _test_port('multimax.tec.br', 80)
        
        # Testa porta 443 (HTTPS)
        port_443_ok = _test_port('multimax.tec.br', 443)
        
        # Se ambas as portas estão abertas
        if port_80_ok and port_443_ok:
            return {
                'status': 'ok',
                'message': 'Nginx respondendo nas portas 80 (HTTP) e 443 (HTTPS)',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        
        # Se apenas porta 443 está aberta
        if port_443_ok:
            return {
                'status': 'ok',
                'message': 'Nginx respondendo na porta 443 (HTTPS)',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        
        # Se apenas porta 80 está aberta, verifica redirecionamento
        if port_80_ok:
            redirect_ok, redirect_msg = _check_http_redirect()
            if redirect_ok:
                return {
                    'status': 'ok',
                    'message': f'Nginx respondendo na porta 80: {redirect_msg}',
                    'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
                }
            else:
                return {
                    'status': 'ok',
                    'message': 'Nginx respondendo na porta 80 (HTTP)',
                    'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
                }
        
        # Se nenhuma porta responde, verifica se processo nginx está rodando
        try:
            if psutil:
                for proc in psutil.process_iter(['pid', 'name']):
                    if 'nginx' in proc.info['name'].lower():
                        return {
                            'status': 'warning',
                            'message': 'Processo Nginx encontrado mas portas 80 e 443 não respondem',
                            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
                        }
        except Exception:
            pass
        
        # Nenhuma porta responde e processo não encontrado
        _register_incident('nginx', 'service_down', 'Nginx não está respondendo nas portas 80 e 443')
        return {
            'status': 'error',
            'message': 'Nginx não está respondendo nas portas 80 (HTTP) e 443 (HTTPS)',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('nginx', 'check_error', str(e))
        return {
            'status': 'error',
            'message': f'Erro ao verificar Nginx: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_port_health(port=5000):
    """Verifica se a porta da aplicação está aberta"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            return {
                'status': 'ok',
                'message': f'Porta {port} está aberta e respondendo',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        else:
            _register_incident('port', 'port_closed', f'Porta {port} não está respondendo')
            return {
                'status': 'error',
                'message': f'Porta {port} não está respondendo',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
    except Exception as e:
        _register_incident('port', 'check_error', str(e))
        return {
            'status': 'error',
            'message': f'Erro ao verificar porta {port}: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_cpu_health():
    """Verifica uso de CPU"""
    try:
        if psutil is None:
            return {
                'status': 'warning',
                'usage_percent': None,
                'message': 'psutil não disponível',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        status = 'ok'
        if cpu_percent > 80:
            status = 'error'
            _register_incident('cpu', 'high_usage', f'Uso de CPU alto: {cpu_percent:.1f}%')
        elif cpu_percent > 60:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': round(cpu_percent, 1),
            'message': f'CPU: {cpu_percent:.1f}%' if status == 'ok' else f'Uso de CPU alto: {cpu_percent:.1f}%',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('cpu', 'check_error', str(e))
        return {
            'status': 'error',
            'usage_percent': None,
            'message': f'Erro ao verificar CPU: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_memory_health():
    """Verifica uso de memória"""
    try:
        if psutil is None:
            return {
                'status': 'warning',
                'usage_percent': None,
                'available_gb': None,
                'message': 'psutil não disponível',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        mem_available_gb = mem.available / (1024**3)
        
        status = 'ok'
        if mem_percent > 90:
            status = 'error'
            _register_incident('memory', 'high_usage', f'Uso de memória alto: {mem_percent:.1f}%')
        elif mem_percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': round(mem_percent, 1),
            'available_gb': round(mem_available_gb, 2),
            'message': f'Memória: {mem_percent:.1f}% ({mem_available_gb:.2f} GB livres)',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('memory', 'check_error', str(e))
        return {
            'status': 'error',
            'usage_percent': None,
            'available_gb': None,
            'message': f'Erro ao verificar memória: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _check_disk_health():
    """Verifica espaço em disco"""
    try:
        if psutil is None:
            return {
                'status': 'warning',
                'usage_percent': None,
                'free_gb': None,
                'message': 'psutil não disponível',
                'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
            }
        
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        
        status = 'ok'
        if disk_percent > 90:
            status = 'error'
            _register_incident('disk', 'low_space', f'Espaço em disco baixo: {disk_percent:.1f}% usado')
        elif disk_percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': round(disk_percent, 1),
            'free_gb': round(disk_free_gb, 2),
            'message': f'Disco: {disk_percent:.1f}% usado ({disk_free_gb:.2f} GB livres)',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        _register_incident('disk', 'check_error', str(e))
        return {
            'status': 'error',
            'usage_percent': None,
            'free_gb': None,
            'message': f'Erro ao verificar disco: {str(e)}',
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

def _get_all_health_checks():
    """Executa todos os health checks"""
    health_checks = {
        'database': _check_database_health(),
        'backend': _check_backend_health(),
        'nginx': _check_nginx_health(),
        'port': _check_port_health(5000),
        'cpu': _check_cpu_health(),
        'memory': _check_memory_health(),
        'disk': _check_disk_health(),
        'http_latency': _check_http_latency()
    }
    
    # Salvar métricas no histórico
    _save_health_metrics_to_history(health_checks)
    
    # Verificar e criar alertas
    _check_and_create_alerts(health_checks)
    
    return health_checks

# ============================================================================
# Registro de Incidentes
# ============================================================================

def _register_incident(service, error_type, message, severity='error'):
    """Registra um incidente automaticamente"""
    try:
        # Evita duplicar incidentes muito recentes (últimos 5 minutos)
        cutoff = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(minutes=5)
        recent = Incident.query.filter(
            Incident.service == service,
            Incident.error_type == error_type,
            Incident.created_at >= cutoff,
            Incident.status == 'open'
        ).first()
        
        if recent:
            return  # Já existe incidente recente
        
        incident = Incident()
        incident.service = service
        incident.error_type = error_type
        incident.message = message[:1000] if len(message) > 1000 else message
        incident.severity = severity
        incident.status = 'open'
        db.session.add(incident)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

# ============================================================================
# Sistema de Alertas Proativos
# ============================================================================

ALERT_THRESHOLDS = {
    'cpu': {'warning': 60.0, 'critical': 80.0},
    'memory': {'warning': 80.0, 'critical': 90.0},
    'disk': {'warning': 80.0, 'critical': 90.0},
    'database_response_time': {'warning': 1000.0, 'critical': 5000.0},  # ms
    'http_latency': {'warning': 500.0, 'critical': 2000.0}  # ms
}

def _check_and_create_alerts(health_checks):
    """Verifica métricas e cria alertas proativos"""
    try:
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        
        # CPU
        if 'cpu' in health_checks:
            cpu = health_checks['cpu']
            if cpu.get('usage_percent') is not None:
                cpu_val = cpu['usage_percent']
                if cpu_val >= ALERT_THRESHOLDS['cpu']['critical']:
                    _create_alert('cpu_high', 'cpu', ALERT_THRESHOLDS['cpu']['critical'], cpu_val, 
                                f'CPU crítica: {cpu_val:.1f}%', 'critical')
                elif cpu_val >= ALERT_THRESHOLDS['cpu']['warning']:
                    _create_alert('cpu_high', 'cpu', ALERT_THRESHOLDS['cpu']['warning'], cpu_val, 
                                f'CPU alta: {cpu_val:.1f}%', 'warning')
        
        # Memória
        if 'memory' in health_checks:
            mem = health_checks['memory']
            if mem.get('usage_percent') is not None:
                mem_val = mem['usage_percent']
                if mem_val >= ALERT_THRESHOLDS['memory']['critical']:
                    _create_alert('memory_high', 'memory', ALERT_THRESHOLDS['memory']['critical'], mem_val, 
                                f'Memória crítica: {mem_val:.1f}%', 'critical')
                elif mem_val >= ALERT_THRESHOLDS['memory']['warning']:
                    _create_alert('memory_high', 'memory', ALERT_THRESHOLDS['memory']['warning'], mem_val, 
                                f'Memória alta: {mem_val:.1f}%', 'warning')
        
        # Disco
        if 'disk' in health_checks:
            disk = health_checks['disk']
            if disk.get('usage_percent') is not None:
                disk_val = disk['usage_percent']
                if disk_val >= ALERT_THRESHOLDS['disk']['critical']:
                    _create_alert('disk_high', 'disk', ALERT_THRESHOLDS['disk']['critical'], disk_val, 
                                f'Espaço em disco crítico: {disk_val:.1f}% usado', 'critical')
                elif disk_val >= ALERT_THRESHOLDS['disk']['warning']:
                    _create_alert('disk_high', 'disk', ALERT_THRESHOLDS['disk']['warning'], disk_val, 
                                f'Espaço em disco alto: {disk_val:.1f}% usado', 'warning')
        
        # Database response time
        if 'database' in health_checks:
            db = health_checks['database']
            if db.get('response_time_ms') is not None:
                db_time = db['response_time_ms']
                if db_time >= ALERT_THRESHOLDS['database_response_time']['critical']:
                    _create_alert('database_slow', 'database_response_time', 
                                ALERT_THRESHOLDS['database_response_time']['critical'], db_time, 
                                f'Banco de dados muito lento: {db_time:.2f}ms', 'critical')
                elif db_time >= ALERT_THRESHOLDS['database_response_time']['warning']:
                    _create_alert('database_slow', 'database_response_time', 
                                ALERT_THRESHOLDS['database_response_time']['warning'], db_time, 
                                f'Banco de dados lento: {db_time:.2f}ms', 'warning')
    except Exception:
        pass

def _create_alert(alert_type, metric_type, threshold, current_value, message, severity='warning'):
    """Cria um alerta se não existir um ativo recente"""
    try:
        cutoff = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(minutes=5)
        recent = Alert.query.filter(
            Alert.alert_type == alert_type,
            Alert.status == 'active',
            Alert.created_at >= cutoff
        ).first()
        
        if recent:
            return
        
        alert = Alert()
        alert.alert_type = alert_type
        alert.metric_type = metric_type
        alert.threshold_value = threshold
        alert.current_value = current_value
        alert.message = message
        alert.severity = severity
        alert.status = 'active'
        db.session.add(alert)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

# ============================================================================
# Histórico de Métricas e Análise de Tendências
# ============================================================================

def _save_metric_history(metric_type, value, unit=None, extra_data=None):
    """Salva métrica no histórico"""
    try:
        import json
        metric = MetricHistory()
        metric.metric_type = metric_type
        metric.value = value
        metric.unit = unit
        if extra_data:
            metric.extra_data = json.dumps(extra_data) if isinstance(extra_data, dict) else str(extra_data)
        db.session.add(metric)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

def _save_health_metrics_to_history(health_checks):
    """Salva métricas dos health checks no histórico"""
    try:
        if 'cpu' in health_checks and health_checks['cpu'].get('usage_percent') is not None:
            _save_metric_history('cpu', health_checks['cpu']['usage_percent'], 'percent')
        if 'memory' in health_checks and health_checks['memory'].get('usage_percent') is not None:
            _save_metric_history('memory', health_checks['memory']['usage_percent'], 'percent')
        if 'disk' in health_checks and health_checks['disk'].get('usage_percent') is not None:
            _save_metric_history('disk', health_checks['disk']['usage_percent'], 'percent')
        if 'database' in health_checks and health_checks['database'].get('response_time_ms') is not None:
            _save_metric_history('database_response_time', health_checks['database']['response_time_ms'], 'ms')
    except Exception:
        pass

def _get_metric_trends(metric_type, hours=24):
    """Obtém tendências de métricas"""
    try:
        cutoff = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(hours=hours)
        metrics = MetricHistory.query.filter(
            MetricHistory.metric_type == metric_type,
            MetricHistory.timestamp >= cutoff
        ).order_by(MetricHistory.timestamp.asc()).all()
        
        if not metrics:
            return None
        
        values = [m.value for m in metrics]
        timestamps = [m.timestamp.isoformat() if m.timestamp else None for m in metrics]
        
        avg = sum(values) / len(values) if values else 0
        min_val = min(values) if values else 0
        max_val = max(values) if values else 0
        
        # Tendência (últimos 25% vs primeiros 25%)
        if len(values) >= 4:
            first_quarter = values[:len(values)//4]
            last_quarter = values[-len(values)//4:]
            first_avg = sum(first_quarter) / len(first_quarter)
            last_avg = sum(last_quarter) / len(last_quarter)
            trend = 'increasing' if last_avg > first_avg * 1.1 else ('decreasing' if last_avg < first_avg * 0.9 else 'stable')
        else:
            trend = 'stable'
        
        return {
            'values': values,
            'timestamps': timestamps,
            'average': round(avg, 2),
            'min': round(min_val, 2),
            'max': round(max_val, 2),
            'trend': trend,
            'count': len(values)
        }
    except Exception:
        return None

def _predict_disk_full_date():
    """Prediz quando o disco ficará cheio baseado na taxa de crescimento"""
    try:
        if psutil is None:
            return None
        
        disk = psutil.disk_usage('/')
        current_usage_percent = disk.percent
        current_free_gb = disk.free / (1024**3)
        
        if current_usage_percent >= 95:
            return {'predicted_date': None, 'message': 'Disco quase cheio', 'days_remaining': 0}
        
        # Buscar histórico dos últimos 7 dias
        cutoff = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(days=7)
        metrics = MetricHistory.query.filter(
            MetricHistory.metric_type == 'disk',
            MetricHistory.timestamp >= cutoff
        ).order_by(MetricHistory.timestamp.asc()).all()
        
        if len(metrics) < 2:
            return None
        
        # Calcular taxa de crescimento diária
        first_usage = metrics[0].value
        last_usage = metrics[-1].value
        days_passed = (metrics[-1].timestamp - metrics[0].timestamp).total_seconds() / 86400
        
        if days_passed < 1:
            return None
        
        daily_growth = (last_usage - first_usage) / days_passed
        
        if daily_growth <= 0:
            return {'predicted_date': None, 'message': 'Sem crescimento detectado', 'days_remaining': None}
        
        # Calcular quando atingirá 90%
        remaining_to_90 = 90 - current_usage_percent
        days_to_90 = remaining_to_90 / daily_growth if daily_growth > 0 else None
        
        if days_to_90 and days_to_90 > 0:
            predicted_date = datetime.now(ZoneInfo('America/Sao_Paulo')) + timedelta(days=int(days_to_90))
            return {
                'predicted_date': predicted_date.isoformat(),
                'days_remaining': int(days_to_90),
                'daily_growth_percent': round(daily_growth, 2),
                'current_usage_percent': round(current_usage_percent, 2)
            }
        
        return None
    except Exception:
        return None

# ============================================================================
# Monitoramento de Queries do Banco
# ============================================================================

def _log_slow_query(query, execution_time_ms, rows_returned=None, endpoint=None, user_id=None):
    """Registra query lenta (>1s)"""
    try:
        if execution_time_ms < 1000:
            return
        
        query_log = QueryLog()
        query_log.query = query[:5000] if len(query) > 5000 else query
        query_log.execution_time_ms = execution_time_ms
        query_log.rows_returned = rows_returned
        query_log.endpoint = endpoint
        query_log.user_id = user_id
        db.session.add(query_log)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

def _get_slow_queries(limit=20):
    """Obtém queries mais lentas"""
    try:
        return QueryLog.query.order_by(QueryLog.execution_time_ms.desc()).limit(limit).all()
    except Exception:
        return []

def _get_database_stats():
    """Obtém estatísticas do banco de dados"""
    try:
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
        
        if is_sqlite:
            db_path = str(current_app.config.get('DB_FILE_PATH') or '').strip()
            if db_path and os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                size_mb = size_bytes / (1024 * 1024)
                
                # Contar tabelas
                result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
                tables_count = len([t for t in tables if not t.startswith('sqlite_')])
                
                return {
                    'size_mb': round(size_mb, 2),
                    'size_bytes': size_bytes,
                    'tables_count': tables_count,
                    'type': 'SQLite'
                }
        
        return {'type': 'Unknown', 'size_mb': None, 'tables_count': None}
    except Exception:
        return {'type': 'Error', 'size_mb': None, 'tables_count': None}

# ============================================================================
# Verificação de Backups
# ============================================================================

def _verify_backup(backup_path):
    """Verifica integridade de um backup"""
    try:
        if not os.path.exists(backup_path):
            return {'status': 'failed', 'message': 'Arquivo não encontrado'}
        
        size = os.path.getsize(backup_path)
        if size == 0:
            return {'status': 'corrupted', 'message': 'Arquivo vazio'}
        
        # Para SQLite, verifica se é um arquivo válido
        if backup_path.endswith('.sqlite'):
            try:
                # Tenta abrir o arquivo
                with open(backup_path, 'rb') as f:
                    header = f.read(16)
                    if not header.startswith(b'SQLite format 3'):
                        return {'status': 'corrupted', 'message': 'Formato SQLite inválido'}
            except Exception as e:
                return {'status': 'corrupted', 'message': f'Erro ao ler arquivo: {str(e)}'}
        
        return {'status': 'verified', 'message': 'Backup verificado com sucesso', 'size': size}
    except Exception as e:
        return {'status': 'failed', 'message': f'Erro na verificação: {str(e)}'}

def _verify_all_backups():
    """Verifica todos os backups"""
    try:
        bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
        if not bdir:
            return []
        
        results = []
        for name in os.listdir(bdir):
            path = os.path.join(bdir, name)
            if os.path.isfile(path) and name.endswith('.sqlite'):
                verification = _verify_backup(path)
                
                # Salvar verificação no banco
                backup_ver = BackupVerification()
                backup_ver.backup_filename = name
                backup_ver.backup_size = verification.get('size')
                backup_ver.verification_status = verification['status']
                backup_ver.verification_method = 'size_check'
                backup_ver.error_message = verification.get('message') if verification['status'] != 'verified' else None
                backup_ver.verified_by = 'system'
                db.session.add(backup_ver)
                
                results.append({
                    'filename': name,
                    'status': verification['status'],
                    'message': verification.get('message')
                })
        
        db.session.commit()
        return results
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return []

# ============================================================================
# Limpeza e Otimização Automática
# ============================================================================

def _cleanup_old_logs(days=30):
    """Limpa logs antigos"""
    try:
        start_time = time.time()
        cutoff = datetime.now(ZoneInfo('America/Sao_Paulo')) - timedelta(days=days)
        
        # Limpar SystemLog
        deleted_system = SystemLog.query.filter(SystemLog.data < cutoff).delete()
        
        # Limpar QueryLog antigo (manter últimos 1000)
        query_logs = QueryLog.query.order_by(QueryLog.timestamp.desc()).offset(1000).all()
        deleted_queries = 0
        for qlog in query_logs:
            db.session.delete(qlog)
            deleted_queries += 1
        
        # Limpar MetricHistory antigo (manter últimos 30 dias)
        deleted_metrics = MetricHistory.query.filter(MetricHistory.timestamp < cutoff).delete()
        
        db.session.commit()
        duration = time.time() - start_time
        
        # Registrar manutenção
        maint = MaintenanceLog()
        maint.maintenance_type = 'cleanup_logs'
        maint.description = f'Limpeza de logs: {deleted_system} SystemLog, {deleted_queries} QueryLog, {deleted_metrics} MetricHistory'
        maint.status = 'completed'
        maint.duration_seconds = duration
        maint.items_processed = deleted_system + deleted_queries + deleted_metrics
        maint.executed_by = 'system'
        db.session.add(maint)
        db.session.commit()
        
        return {'deleted': deleted_system + deleted_queries + deleted_metrics, 'duration': duration}
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return {'error': str(e)}

def _optimize_database():
    """Otimiza banco de dados"""
    try:
        start_time = time.time()
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
        
        if is_sqlite:
            # VACUUM e ANALYZE para SQLite
            db.session.execute(text('VACUUM'))
            db.session.execute(text('ANALYZE'))
            db.session.commit()
        
        duration = time.time() - start_time
        
        # Registrar manutenção
        maint = MaintenanceLog()
        maint.maintenance_type = 'optimize_database'
        maint.description = 'Otimização do banco de dados (VACUUM + ANALYZE)'
        maint.status = 'completed'
        maint.duration_seconds = duration
        maint.executed_by = 'system'
        db.session.add(maint)
        db.session.commit()
        
        return {'status': 'completed', 'duration': duration}
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return {'error': str(e)}

def _cleanup_old_backups(keep_count=20):
    """Remove backups antigos, mantendo apenas os N mais recentes"""
    try:
        bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
        if not bdir:
            return {'deleted': 0}
        
        backups = []
        for name in os.listdir(bdir):
            path = os.path.join(bdir, name)
            if os.path.isfile(path) and name.endswith('.sqlite'):
                try:
                    mtime = os.path.getmtime(path)
                    backups.append((mtime, path, name))
                except Exception:
                    pass
        
        backups.sort(key=lambda x: x[0], reverse=True)
        
        deleted = 0
        if len(backups) > keep_count:
            for mtime, path, name in backups[keep_count:]:
                try:
                    if not name.startswith('backup-24h'):  # Não deletar backup diário
                        os.remove(path)
                        deleted += 1
                except Exception:
                    pass
        
        return {'deleted': deleted}
    except Exception:
        return {'deleted': 0}

# ============================================================================
# Dashboard Consolidado
# ============================================================================

def _get_system_health_score(health_checks):
    """Calcula score de saúde do sistema (0-100)"""
    try:
        scores = []
        
        if 'database' in health_checks:
            db_status = health_checks['database'].get('status', 'error')
            scores.append(100 if db_status == 'ok' else (50 if db_status == 'warning' else 0))
        
        if 'backend' in health_checks:
            backend_status = health_checks['backend'].get('status', 'error')
            scores.append(100 if backend_status == 'ok' else (50 if backend_status == 'warning' else 0))
        
        if 'cpu' in health_checks:
            cpu_percent = health_checks['cpu'].get('usage_percent', 100)
            scores.append(max(0, 100 - cpu_percent))
        
        if 'memory' in health_checks:
            mem_percent = health_checks['memory'].get('usage_percent', 100)
            scores.append(max(0, 100 - mem_percent))
        
        if 'disk' in health_checks:
            disk_percent = health_checks['disk'].get('usage_percent', 100)
            scores.append(max(0, 100 - disk_percent))
        
        return round(sum(scores) / len(scores), 1) if scores else 0
    except Exception:
        return 0

# ============================================================================
# Monitoramento de Rede e Latência
# ============================================================================

def _check_http_latency():
    """Verifica latência HTTP"""
    try:
        start = time.time()
        with current_app.test_client() as client:
            response = client.get('/health')
            latency_ms = (time.time() - start) * 1000
        
        status = 'ok'
        if latency_ms > 2000:
            status = 'error'
        elif latency_ms > 500:
            status = 'warning'
        
        return {
            'status': status,
            'latency_ms': round(latency_ms, 2),
            'status_code': response.status_code,
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'latency_ms': None,
            'status_code': None,
            'error': str(e),
            'checked_at': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
        }

# ============================================================================
# Backups
# ============================================================================

def _list_backups():
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    try:
        if bdir:
            os.makedirs(bdir, exist_ok=True)
    except Exception:
        pass
    items = []
    try:
        if not bdir:
            return []
        for name in os.listdir(bdir):
            path = os.path.join(bdir, name)
            if not os.path.isfile(path):
                continue
            try:
                sz = os.path.getsize(path)
                mt = os.path.getmtime(path)
            except Exception:
                sz = 0
                mt = 0
            try:
                from datetime import datetime
                mt_str = datetime.fromtimestamp(mt).strftime('%d/%m/%Y %H:%M:%S') if mt else '-'
            except Exception:
                mt_str = '-'
            items.append({'name': name, 'size': sz, 'mtime': mt, 'mtime_str': mt_str})
        items.sort(key=lambda it: it['mtime'], reverse=True)
    except Exception:
        pass
    return items

# ============================================================================
# Rotas
# ============================================================================

@bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    """Página principal - Acesso exclusivo para desenvolvedores"""
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado. Esta página é exclusiva para desenvolvedores.', 'danger')
        return redirect(url_for('home.index'))
    
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    backups = _list_backups()
    daily = None
    try:
        daily = next((it for it in backups if it.get('name') == 'backup-24h.sqlite'), None)
    except Exception:
        daily = None
    
    # Paginação de backups
    try:
        page = int(request.args.get('page', '1'))
    except Exception:
        page = 1
    if page < 1:
        page = 1
    per_page = 10
    total = len(backups)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    backups_page = backups[start:end]
    
    # Paginação de logins
    try:
        login_page = int(request.args.get('login_page', '1'))
    except Exception:
        login_page = 1
    if login_page < 1:
        login_page = 1
    try:
        logins_pag = UserLogin.query.order_by(UserLogin.login_at.desc()).paginate(page=login_page, per_page=10, error_out=False)
        logins = list(logins_pag.items or [])
    except Exception:
        logins_pag = None
        logins = []
    
    # Health checks iniciais
    health_checks = _get_all_health_checks()
    health_score = _get_system_health_score(health_checks)
    
    # Incidentes recentes
    try:
        incidents = Incident.query.order_by(Incident.created_at.desc()).limit(20).all()
    except Exception:
        incidents = []
    
    # Alertas ativos
    try:
        active_alerts = Alert.query.filter(Alert.status == 'active').order_by(Alert.created_at.desc()).limit(10).all()
    except Exception:
        active_alerts = []
    
    # Estatísticas do banco
    db_stats = _get_database_stats()
    
    # Previsão de disco
    disk_prediction = _predict_disk_full_date()
    
    return render_template(
        'db.html',
        active_page='dbadmin',
        is_sqlite=is_sqlite,
        backups=backups_page,
        page=page,
        total_pages=total_pages,
        daily_backup=daily,
        logins=logins,
        logins_pag=logins_pag,
        health_checks=health_checks,
        health_score=health_score,
        incidents=incidents,
        active_alerts=active_alerts,
        db_stats=db_stats,
        disk_prediction=disk_prediction
    )

@bp.route('/health', methods=['GET'], strict_slashes=False)
@login_required
def health():
    """Endpoint JSON para health checks"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    health_checks = _get_all_health_checks()
    return jsonify({'ok': True, 'health': health_checks})

@bp.route('/metrics', methods=['GET'], strict_slashes=False)
@login_required
def metrics():
    """Endpoint JSON para métricas de recursos"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    cpu = None
    mem = None
    disk = None
    try:
        if psutil is not None:
            cpu = float(psutil.cpu_percent(interval=0.05))
            mem = float(psutil.virtual_memory().percent)
            disk_usage = psutil.disk_usage('/')
            disk = float(disk_usage.percent)
        else:
            cpu = None
            mem = None
            disk = None
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    
    from datetime import datetime
    return jsonify({
        'ok': True,
        'ts': datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
        'cpu': cpu,
        'mem': mem,
        'disk': disk
    })

@bp.route('/logs', methods=['GET'], strict_slashes=False)
@login_required
def logs():
    """Endpoint JSON para logs em tempo real"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    log_type = request.args.get('type', 'all')  # 'all', 'app', 'system', 'database'
    level = request.args.get('level', 'all')  # 'all', 'INFO', 'WARNING', 'ERROR'
    limit = int(request.args.get('limit', 100))
    
    try:
        # Logs do sistema (SystemLog)
        system_logs = []
        query = SystemLog.query
        
        if log_type in ('system', 'all'):
            if level != 'all':
                # SystemLog não tem nível, mas podemos filtrar por evento
                if level == 'ERROR':
                    query = query.filter(SystemLog.evento.in_(['erro', 'falha', 'error', 'exception']))
                elif level == 'WARNING':
                    query = query.filter(SystemLog.evento.in_(['aviso', 'warning', 'alerta']))
            
            system_logs_query = query.order_by(SystemLog.data.desc()).limit(limit).all()
            for log in system_logs_query:
                system_logs.append({
                    'timestamp': log.data.isoformat() if log.data else datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
                    'type': 'system',
                    'level': 'INFO',
                    'origin': log.origem or 'Sistema',
                    'event': log.evento or '',
                    'message': log.detalhes or '',
                    'user': log.usuario or ''
                })
        
        # Ordenar por timestamp
        all_logs = sorted(system_logs, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        return jsonify({'ok': True, 'logs': all_logs})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/incidents', methods=['GET'], strict_slashes=False)
@login_required
def incidents():
    """Endpoint JSON para listar incidentes"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    service = request.args.get('service', 'all')
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))
    
    try:
        query = Incident.query
        
        if service != 'all':
            query = query.filter(Incident.service == service)
        if status != 'all':
            query = query.filter(Incident.status == status)
        
        incidents_list = query.order_by(Incident.created_at.desc()).limit(limit).all()
        
        result = []
        for inc in incidents_list:
            result.append({
                'id': inc.id,
                'created_at': inc.created_at.isoformat() if inc.created_at else None,
                'service': inc.service,
                'error_type': inc.error_type,
                'message': inc.message,
                'status': inc.status,
                'severity': inc.severity,
                'resolved_at': inc.resolved_at.isoformat() if inc.resolved_at else None
            })
        
        return jsonify({'ok': True, 'incidents': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/alerts', methods=['GET'], strict_slashes=False)
@login_required
def alerts():
    """Endpoint JSON para listar alertas"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    status = request.args.get('status', 'active')
    limit = int(request.args.get('limit', 50))
    
    try:
        query = Alert.query
        if status != 'all':
            query = query.filter(Alert.status == status)
        
        alerts_list = query.order_by(Alert.created_at.desc()).limit(limit).all()
        
        result = []
        for alert in alerts_list:
            result.append({
                'id': alert.id,
                'created_at': alert.created_at.isoformat() if alert.created_at else None,
                'alert_type': alert.alert_type,
                'metric_type': alert.metric_type,
                'threshold_value': alert.threshold_value,
                'current_value': alert.current_value,
                'message': alert.message,
                'severity': alert.severity,
                'status': alert.status,
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            })
        
        return jsonify({'ok': True, 'alerts': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/alerts/clear', methods=['POST'], strict_slashes=False)
@login_required
def clear_alerts():
    """Limpar todos os alertas ativos"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        # Marcar todos os alertas ativos como resolvidos
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        active_alerts = Alert.query.filter(Alert.status == 'active').all()
        count = len(active_alerts)
        
        for alert in active_alerts:
            alert.status = 'resolved'
            alert.resolved_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
        
        db.session.commit()
        
        # Registrar no log
        log = SystemLog()
        log.origem = 'Alertas'
        log.evento = 'alerts_cleared'
        log.detalhes = f'{count} alerta(s) limpo(s) por {current_user.username}'
        log.usuario = current_user.username
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'ok': True,
            'message': f'{count} alerta(s) limpo(s) com sucesso.',
            'count': count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/metrics/trends', methods=['GET'], strict_slashes=False)
@login_required
def metrics_trends():
    """Endpoint JSON para análise de tendências"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    metric_type = request.args.get('type', 'cpu')
    hours = int(request.args.get('hours', 24))
    
    try:
        trends = _get_metric_trends(metric_type, hours)
        return jsonify({'ok': True, 'trends': trends})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/metrics/predict', methods=['GET'], strict_slashes=False)
@login_required
def metrics_predict():
    """Endpoint JSON para análise preditiva"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        prediction = _predict_disk_full_date()
        return jsonify({'ok': True, 'prediction': prediction})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/queries/slow', methods=['GET'], strict_slashes=False)
@login_required
def slow_queries():
    """Endpoint JSON para queries lentas"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    limit = int(request.args.get('limit', 20))
    
    try:
        queries = _get_slow_queries(limit)
        result = []
        for q in queries:
            result.append({
                'id': q.id,
                'timestamp': q.timestamp.isoformat() if q.timestamp else None,
                'query': q.query[:200] + '...' if len(q.query) > 200 else q.query,
                'execution_time_ms': q.execution_time_ms,
                'rows_returned': q.rows_returned,
                'endpoint': q.endpoint
            })
        return jsonify({'ok': True, 'queries': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/database/stats', methods=['GET'], strict_slashes=False)
@login_required
def database_stats():
    """Endpoint JSON para estatísticas do banco"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        stats = _get_database_stats()
        return jsonify({'ok': True, 'stats': stats})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/backups/verify', methods=['POST'], strict_slashes=False)
@login_required
def verify_backups():
    """Verifica integridade de todos os backups"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        results = _verify_all_backups()
        return jsonify({'ok': True, 'results': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/maintenance/cleanup', methods=['POST'], strict_slashes=False)
@login_required
def maintenance_cleanup():
    """Executa limpeza de logs antigos"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    days = int(request.args.get('days', 30))
    
    try:
        result = _cleanup_old_logs(days)
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/maintenance/optimize', methods=['POST'], strict_slashes=False)
@login_required
def maintenance_optimize():
    """Executa otimização do banco de dados"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        result = _optimize_database()
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/dashboard', methods=['GET'], strict_slashes=False)
@login_required
def dashboard():
    """Endpoint JSON para dashboard consolidado"""
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    try:
        health_checks = _get_all_health_checks()
        health_score = _get_system_health_score(health_checks)
        db_stats = _get_database_stats()
        disk_prediction = _predict_disk_full_date()
        
        # Alertas ativos
        active_alerts = Alert.query.filter(Alert.status == 'active').count()
        
        # Incidentes abertos
        open_incidents = Incident.query.filter(Incident.status == 'open').count()
        
        return jsonify({
            'ok': True,
            'health_score': health_score,
            'health_checks': health_checks,
            'database_stats': db_stats,
            'disk_prediction': disk_prediction,
            'active_alerts': active_alerts,
            'open_incidents': open_incidents
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/backup', methods=['POST'], strict_slashes=False)
@login_required
def backup_now():
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    ok = False
    try:
        fn = getattr(current_app, 'perform_backup', None)
        if callable(fn):
            ok = bool(fn(retain_count=20, force=True))
    except Exception:
        ok = False
    flash('Backup criado.' if ok else 'Falha ao criar backup.', 'success' if ok else 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/download/<path:name>', methods=['GET'], strict_slashes=False)
@login_required
def download(name: str):
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    if not bdir:
        flash('Diretório de backup inválido.', 'danger')
        return redirect(url_for('dbadmin.index'))
    path = os.path.join(bdir, name)
    if not os.path.isfile(path):
        flash('Arquivo não encontrado.', 'warning')
        return redirect(url_for('dbadmin.index'))
    return send_file(path, as_attachment=True, download_name=name)

@bp.route('/excluir/<path:name>', methods=['POST'], strict_slashes=False)
@login_required
def excluir(name: str):
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    if not bdir:
        flash('Diretório de backup inválido.', 'danger')
        return redirect(url_for('dbadmin.index'))
    path = os.path.join(bdir, name)
    try:
        if os.path.isfile(path):
            os.remove(path)
            flash('Backup excluído.', 'danger')
        else:
            flash('Arquivo não encontrado.', 'warning')
    except Exception as e:
        flash(f'Erro ao excluir: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/restaurar/<path:name>', methods=['POST'], strict_slashes=False)
@login_required
def restaurar(name: str):
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    if not is_sqlite:
        flash('Restauração disponível apenas para banco SQLite.', 'warning')
        return redirect(url_for('dbadmin.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    db_path = str(current_app.config.get('DB_FILE_PATH') or '').strip()
    if not bdir or not db_path:
        flash('Configuração de backup ou banco inválida.', 'danger')
        return redirect(url_for('dbadmin.index'))
    src = os.path.join(bdir, name)
    if not os.path.isfile(src):
        flash('Backup não encontrado.', 'warning')
        return redirect(url_for('dbadmin.index'))
    try:
        try:
            from .. import db
            db.session.close()
            db.engine.dispose()
        except Exception:
            pass
        try:
            ok = False
            fn = getattr(current_app, 'perform_backup', None)
            if callable(fn):
                ok = bool(fn(retain_count=20, force=True))
            if not ok and os.path.exists(db_path):
                ts = time.strftime('%Y%m%d-%H%M%S')
                snap = os.path.join(bdir, f'pre-restore-{ts}.sqlite')
                shutil.copy2(db_path, snap)
            if ok:
                flash('Backup automático criado antes da restauração.', 'info')
        except Exception:
            pass
        shutil.copy2(src, db_path)
        flash('Banco restaurado a partir do backup.', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/restaurar/snapshot', methods=['POST'], strict_slashes=False)
@login_required
def restaurar_snapshot():
    if not _check_dev_access():
        _log_unauthorized_access()
        flash('Acesso negado.', 'danger')
        return redirect(url_for('home.index'))
    
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = isinstance(uri, str) and uri.startswith('sqlite:')
    if not is_sqlite:
        flash('Restauração disponível apenas para banco SQLite.', 'warning')
        return redirect(url_for('dbadmin.index'))
    bdir = str(current_app.config.get('BACKUP_DIR') or '').strip()
    db_path = str(current_app.config.get('DB_FILE_PATH') or '').strip()
    if not bdir or not db_path:
        flash('Configuração de backup ou banco inválida.', 'danger')
        return redirect(url_for('dbadmin.index'))
    try:
        candidates = []
        for name in os.listdir(bdir):
            if not isinstance(name, str):
                continue
            if not name.lower().endswith('.sqlite'):
                continue
            if not name.startswith('pre-restore-'):
                continue
            p = os.path.join(bdir, name)
            if os.path.isfile(p):
                try:
                    mt = os.path.getmtime(p)
                except Exception:
                    mt = 0
                candidates.append((mt, p))
        if not candidates:
            flash('Nenhum snapshot encontrado.', 'warning')
            return redirect(url_for('dbadmin.index'))
        candidates.sort(key=lambda t: t[0], reverse=True)
        src = candidates[0][1]
        try:
            from .. import db
            db.session.close()
            db.engine.dispose()
        except Exception:
            pass
        shutil.copy2(src, db_path)
        flash('Banco restaurado a partir do último snapshot.', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar snapshot: {e}', 'danger')
    return redirect(url_for('dbadmin.index'))

@bp.route('/git/status', methods=['GET'], strict_slashes=False)
@login_required
def git_status():
    """Retorna status do Git e commit mais recente
    
    Parâmetros:
        force (bool): Se True, força um fetch mais agressivo com --all e --prune
    """
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    force = request.args.get('force', 'false').lower() == 'true'
    
    try:
        # Tentar encontrar o diretório do repositório Git
        repo_dir = None
        
        # 1. Variável de ambiente (prioridade)
        env_repo_dir = os.getenv('GIT_REPO_DIR')
        if env_repo_dir and os.path.exists(os.path.join(env_repo_dir, '.git')):
            repo_dir = env_repo_dir
        
        # 2. Tentar diretórios padrão de produção
        if not repo_dir:
            # Calcular diretório raiz do projeto
            current_file = os.path.abspath(__file__)
            project_root = current_file
            # Subir até encontrar arquivos característicos do projeto
            for _ in range(5):
                if os.path.exists(os.path.join(project_root, 'multimax')) or \
                   os.path.exists(os.path.join(project_root, 'app.py')) or \
                   os.path.exists(os.path.join(project_root, 'docker-compose.yml')):
                    break
                project_root = os.path.dirname(project_root)
                if project_root == os.path.dirname(project_root):  # Chegou na raiz
                    break
            
            production_dirs = [
                '/opt/multimax',  # VPS produção
                '/app',  # Dentro do container Docker
                project_root,  # Raiz calculada do projeto
            ]
            for dir_path in production_dirs:
                if dir_path and os.path.exists(dir_path) and os.path.exists(os.path.join(dir_path, '.git')):
                    repo_dir = dir_path
                    current_app.logger.info(f'Repositório Git encontrado em: {repo_dir}')
                    break
        
        # 3. Tentar diretório atual e pais (desenvolvimento)
        if not repo_dir:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            search_dirs = [
                current_dir,
                os.path.dirname(current_dir),
                os.path.dirname(os.path.dirname(current_dir)),
                os.path.dirname(os.path.dirname(os.path.dirname(current_dir))),
            ]
            for dir_path in search_dirs:
                if dir_path and os.path.exists(os.path.join(dir_path, '.git')):
                    repo_dir = dir_path
                    current_app.logger.info(f'Repositório Git encontrado em (dev): {repo_dir}')
                    break
        
        # Verificar se é diretório Git
        if not repo_dir or not os.path.exists(os.path.join(repo_dir, '.git')):
            searched_dirs = [
                env_repo_dir or 'N/A (GIT_REPO_DIR não definido)',
                '/opt/multimax',
                '/app',
                'diretórios pais do arquivo atual'
            ]
            return jsonify({
                'ok': False,
                'error': f'Repositório Git não encontrado. Procurado em: {", ".join(searched_dirs)}',
                'current_version': None,
                'latest_commit': None,
                'repo_dir': repo_dir,
                'hint': 'Configure a variável de ambiente GIT_REPO_DIR ou verifique se o diretório contém .git'
            })
        
        # Obter versão atual do sistema
        current_version = None
        try:
            # Tentar obter versão do Git
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                current_version = result.stdout.strip()
                current_app.logger.info(f'Versão obtida do Git: {current_version}')
            else:
                # Fallback: versão do __init__.py
                init_path = os.path.join(repo_dir, 'multimax', '__init__.py')
                if os.path.exists(init_path):
                    with open(init_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        import re
                        match = re.search(r"return '([\d.]+)'", content)
                        if match:
                            current_version = match.group(1)
                            current_app.logger.info(f'Versão obtida do __init__.py: {current_version}')
                else:
                    current_app.logger.warning(f'Arquivo __init__.py não encontrado em: {init_path}')
        except Exception as e:
            current_app.logger.error(f'Erro ao obter versão: {e}', exc_info=True)
        
        # Obter commit atual
        current_commit = None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                current_commit = result.stdout.strip()
                current_app.logger.info(f'Commit atual obtido: {current_commit[:7]} (full: {current_commit})')
            else:
                current_app.logger.warning(f'Erro ao obter commit atual. Return code: {result.returncode}, stderr: {result.stderr[:200]}')
        except Exception as e:
            current_app.logger.error(f'Erro ao obter commit atual: {e}', exc_info=True)
        
        # Obter commit mais recente do branch remoto
        latest_commit_hash = None
        commit_message = None
        commit_date = None
        try:
            # Verificar se o repositório remoto está configurado
            remote_check = subprocess.run(
                ['git', 'remote', '-v'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if remote_check.returncode == 0:
                current_app.logger.info(f'Remotes configurados: {remote_check.stdout[:200]}')
            
            # Fetch do branch remoto (sempre fazer fetch para obter commits mais recentes)
            # Se force=True, usar --all para buscar todos os remotes e --prune para limpar referências obsoletas
            fetch_cmd = ['git', 'fetch']
            if force:
                fetch_cmd.extend(['--all', '--prune', '--force'])
                current_app.logger.info('Forçando fetch completo (--all --prune --force)')
            else:
                fetch_cmd.extend(['origin', 'nova-versao-deploy', '--prune'])
            
            fetch_result = subprocess.run(
                fetch_cmd,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30 if force else 20  # Timeout maior para fetch forçado
            )
            if fetch_result.returncode != 0:
                current_app.logger.warning(f'Erro ao fazer fetch. Return code: {fetch_result.returncode}, stderr: {fetch_result.stderr[:300]}, stdout: {fetch_result.stdout[:300]}')
            else:
                current_app.logger.info(f'Fetch realizado com sucesso. Output: {fetch_result.stdout[:200] if fetch_result.stdout else "sem output"}')
            
            # Verificar se a referência remota existe após o fetch
            ref_check = subprocess.run(
                ['git', 'ls-remote', '--heads', 'origin', 'nova-versao-deploy'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if ref_check.returncode == 0 and ref_check.stdout.strip():
                remote_ref_hash = ref_check.stdout.strip().split()[0] if ref_check.stdout.strip() else None
                current_app.logger.info(f'Commit remoto via ls-remote: {remote_ref_hash[:7] if remote_ref_hash else "N/A"}')
            
            # Obter último commit do branch remoto
            result = subprocess.run(
                ['git', 'rev-parse', 'origin/nova-versao-deploy'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                latest_commit_hash = result.stdout.strip()
                current_app.logger.info(f'Commit remoto obtido via rev-parse: {latest_commit_hash[:7]} (full: {latest_commit_hash})')
            else:
                current_app.logger.warning(f'Erro ao obter commit remoto. Return code: {result.returncode}, stderr: {result.stderr[:300]}, stdout: {result.stdout[:300]}')
                # Tentar alternativa: usar ls-remote diretamente
                if 'remote_ref_hash' in locals() and remote_ref_hash:
                    latest_commit_hash = remote_ref_hash
                    current_app.logger.info(f'Usando commit remoto de ls-remote: {latest_commit_hash[:7]}')
            
            # Obter mensagem do commit
            if latest_commit_hash:
                result = subprocess.run(
                    ['git', 'log', '-1', '--pretty=format:%s', latest_commit_hash],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    commit_message = result.stdout.strip()
                else:
                    current_app.logger.warning(f'Erro ao obter mensagem do commit: {result.stderr[:200]}')
                
                # Obter data do commit
                result = subprocess.run(
                    ['git', 'log', '-1', '--pretty=format:%ci', latest_commit_hash],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    commit_date = result.stdout.strip()
        except Exception as e:
            current_app.logger.error(f'Erro ao obter commit remoto: {e}', exc_info=True)
        
        # Verificar se há atualização disponível
        update_available = False
        if current_commit and latest_commit_hash:
            update_available = current_commit != latest_commit_hash
            current_app.logger.info(f'Comparação de commits: local={current_commit[:7] if current_commit else None} (full: {current_commit}), remoto={latest_commit_hash[:7] if latest_commit_hash else None} (full: {latest_commit_hash}), atualização disponível={update_available}')
            if not update_available:
                current_app.logger.info(f'Commits são idênticos - sistema está atualizado')
            else:
                current_app.logger.info(f'Atualização disponível! Commit remoto é diferente do local.')
        else:
            missing = []
            if not current_commit:
                missing.append('current_commit')
            if not latest_commit_hash:
                missing.append('latest_commit_hash')
            current_app.logger.warning(f'Não foi possível comparar commits. Faltando: {", ".join(missing)}. current_commit={current_commit[:7] if current_commit else None}, latest_commit_hash={latest_commit_hash[:7] if latest_commit_hash else None}')
        
        return jsonify({
            'ok': True,
            'current_version': current_version,
            'current_commit': current_commit[:7] if current_commit else None,
            'latest_commit': latest_commit_hash[:7] if latest_commit_hash else None,
            'latest_commit_full': latest_commit_hash,
            'commit_message': commit_message,
            'commit_date': commit_date,
            'update_available': update_available,
            'repo_url': 'https://github.com/SrLuther/MultiMax',
            'branch': 'nova-versao-deploy'
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'current_version': None,
            'latest_commit': None
        }), 500

@bp.route('/git/update', methods=['POST'], strict_slashes=False)
@login_required
def git_update():
    """
    Aplica atualização do MultiMax via Deploy Agent
    
    IMPORTANTE: Este endpoint NÃO executa comandos Git ou Docker diretamente.
    Ele apenas faz uma requisição HTTP para o Deploy Agent (serviço separado no HOST),
    que então executa os comandos no HOST, fora do container Docker.
    
    ARQUITETURA:
    - MultiMax (container): Faz POST para http://127.0.0.1:9000/deploy
    - Deploy Agent (HOST): Executa comandos Git/Docker no HOST
    
    O Deploy Agent executa a sequência fixa:
    1. git fetch origin
    2. git reset --hard origin/nova-versao-deploy
    3. docker-compose build --no-cache
    4. docker-compose down
    5. docker-compose up -d
    
    Parâmetros JSON:
        force (bool): Se True, força atualização mesmo se o sistema estiver atualizado
    
    Segurança:
    - Deploy Agent aceita apenas conexões localhost (127.0.0.1)
    - Não expõe porta externamente
    - Opcionalmente requer token de autenticação via DEPLOY_AGENT_TOKEN
    """
    if not _check_dev_access():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    
    # Verificar se é atualização forçada
    force = False
    try:
        data = request.get_json() or {}
        force = data.get('force', False)
    except Exception:
        pass
    
    # Configuração do Deploy Agent
    deploy_agent_url = os.getenv('DEPLOY_AGENT_URL', 'http://127.0.0.1:9000')
    deploy_agent_token = os.getenv('DEPLOY_AGENT_TOKEN', '')
    
    # Validar URL do Deploy Agent (deve ser localhost)
    if not deploy_agent_url.startswith(('http://127.0.0.1:', 'http://localhost:', 'http://::1:')):
        error_msg = f'URL do Deploy Agent inválida (deve ser localhost): {deploy_agent_url}'
        current_app.logger.error(error_msg)
        return jsonify({
            'ok': False,
            'error': error_msg,
            'suggestion': 'Configure DEPLOY_AGENT_URL para http://127.0.0.1:9000'
        }), 400
    
    # Registrar início da atualização
    try:
        log = SystemLog()
        log.origem = 'GitUpdate'
        log.evento = 'update_start'
        update_type = 'forçada' if force else 'normal'
        log.detalhes = f'Iniciando atualização {update_type} via Deploy Agent por {current_user.username}'
        log.usuario = current_user.username
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Erro ao registrar início da atualização: {e}')
    
    # Fazer requisição HTTP para o Deploy Agent
    # IMPORTANTE: O MultiMax (container) NÃO executa comandos Git ou Docker diretamente
    # Toda execução é delegada ao Deploy Agent (HOST)
    try:
        import requests
        from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError
        
        # Preparar headers
        headers = {
            'Content-Type': 'application/json'
        }
        if deploy_agent_token:
            headers['Authorization'] = f'Bearer {deploy_agent_token}'
        
        # Preparar payload
        payload = {
            'force': force
        }
        
        # URL do endpoint de deploy
        deploy_endpoint = f'{deploy_agent_url}/deploy'
        
        current_app.logger.info(f'Enviando requisição de deploy para: {deploy_endpoint}')
        
        # Fazer requisição POST com timeout adequado (build pode demorar até 10 minutos)
        response = requests.post(
            deploy_endpoint,
            json=payload,
            headers=headers,
            timeout=900  # 15 minutos de timeout (build + down + up)
        )
        
        # Verificar resposta
        if response.status_code == 200:
            result_data = response.json()
            if result_data.get('ok'):
                # Sucesso
                current_app.logger.info('Deploy concluído com sucesso via Deploy Agent')
                
                # Registrar sucesso no log
                try:
                    log = SystemLog()
                    log.origem = 'GitUpdate'
                    log.evento = 'update_success'
                    log.detalhes = f'Atualização aplicada com sucesso via Deploy Agent por {current_user.username}. Duração: {result_data.get("duration", 0):.2f}s'
                    log.usuario = current_user.username
                    db.session.add(log)
                    db.session.commit()
                except Exception as e:
                    current_app.logger.error(f'Erro ao registrar sucesso da atualização: {e}')
                
                return jsonify({
                    'ok': True,
                    'message': 'Atualização aplicada com sucesso. Sistema será reiniciado.',
                    'duration': result_data.get('duration', 0),
                    'results': result_data.get('results', [])
                })
            else:
                # Erro retornado pelo Deploy Agent
                error_msg = result_data.get('error', 'Erro desconhecido no Deploy Agent')
                error_details = result_data.get('details', '')
                failed_step = result_data.get('failed_step', '')
                
                current_app.logger.error(f'Erro no Deploy Agent: {error_msg}')
                if error_details:
                    current_app.logger.error(f'Detalhes: {error_details[:500]}')
                
                # Registrar erro no log
                _log_git_update_error(f'{error_msg}. {error_details[:200]}', current_user.username)
                
                return jsonify({
                    'ok': False,
                    'error': error_msg,
                    'details': error_details[:1000],  # Limitar tamanho
                    'failed_step': failed_step,
                    'results': result_data.get('results', []),
                    'duration': result_data.get('duration', 0)
                }), 500
        
        elif response.status_code == 401:
            error_msg = 'Token de autenticação inválido ou ausente'
            current_app.logger.error(error_msg)
            return jsonify({
                'ok': False,
                'error': error_msg,
                'suggestion': 'Configure DEPLOY_AGENT_TOKEN ou verifique se o token está correto'
            }), 401
        
        elif response.status_code == 403:
            error_msg = 'Acesso negado - requisição deve vir de localhost'
            current_app.logger.error(error_msg)
            return jsonify({
                'ok': False,
                'error': error_msg,
                'suggestion': 'O Deploy Agent aceita apenas conexões localhost. Verifique a configuração.'
            }), 403
        
        else:
            # Outro código de erro HTTP
            try:
                error_data = response.json()
                error_msg = error_data.get('error', f'Erro HTTP {response.status_code}')
            except Exception:
                error_msg = f'Erro HTTP {response.status_code}'
            
            current_app.logger.error(f'Erro HTTP do Deploy Agent: {response.status_code} - {error_msg}')
            _log_git_update_error(f'Erro HTTP {response.status_code}: {error_msg}', current_user.username)
            
            return jsonify({
                'ok': False,
                'error': error_msg,
                'http_status': response.status_code
            }), response.status_code
    
    except Timeout:
        error_msg = 'Timeout ao aguardar resposta do Deploy Agent (limite: 15 minutos)'
        current_app.logger.error(error_msg)
        _log_git_update_error(error_msg, current_user.username)
        return jsonify({
            'ok': False,
            'error': error_msg,
            'suggestion': 'O processo de deploy pode estar demorando mais do que o esperado. Verifique os logs do Deploy Agent.'
        }), 504
    
    except RequestsConnectionError as e:
        error_msg = f'Não foi possível conectar ao Deploy Agent: {str(e)}'
        current_app.logger.error(error_msg)
        _log_git_update_error(error_msg, current_user.username)
        return jsonify({
            'ok': False,
            'error': error_msg,
            'suggestion': (
                'O Deploy Agent não está respondendo. Verifique:\n'
                '1) O Deploy Agent está rodando? (sudo systemctl status deploy-agent)\n'
                '2) O Deploy Agent está escutando na porta 9000? (netstat -tlnp | grep 9000)\n'
                '3) A URL está correta? (DEPLOY_AGENT_URL=http://127.0.0.1:9000)\n'
                '4) Verifique os logs do Deploy Agent: sudo journalctl -u deploy-agent -f'
            ),
            'deploy_agent_url': deploy_agent_url
        }), 503
    
    except RequestException as e:
        error_msg = f'Erro na requisição ao Deploy Agent: {str(e)}'
        current_app.logger.error(error_msg, exc_info=True)
        _log_git_update_error(error_msg, current_user.username)
        return jsonify({
            'ok': False,
            'error': error_msg,
            'suggestion': 'Verifique os logs do sistema para mais detalhes.'
        }), 500
    
    except Exception as e:
        error_msg = f'Erro inesperado ao comunicar com Deploy Agent: {str(e)}'
        current_app.logger.error(error_msg, exc_info=True)
        _log_git_update_error(error_msg, current_user.username)
        return jsonify({
            'ok': False,
            'error': error_msg,
            'suggestion': 'Verifique os logs do sistema para mais detalhes.'
        }), 500

def _log_git_update_error(error_msg, username, results=None):
    """Registra erro de atualização Git no log do sistema"""
    try:
        log = SystemLog()
        log.origem = 'GitUpdate'
        log.evento = 'update_error'
        log.detalhes = f'Erro na atualização por {username}: {error_msg}'
        log.usuario = username
        log.severity = 'ERROR'
        if results:
            log.detalhes += f' | Resultados: {len(results)} comandos executados'
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Erro ao registrar erro de atualização: {e}')
