"""
Otimizações e utilitários de performance
"""
from functools import lru_cache
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

@lru_cache(maxsize=128)
def _cached_date_today():
    """Cache para date.today() - útil em loops"""
    return date.today()

@lru_cache(maxsize=64)
def _cached_datetime_now():
    """Cache para datetime.now() - útil em loops"""
    return datetime.now(ZoneInfo('America/Sao_Paulo'))

def get_today_cached():
    """Retorna date.today() com cache"""
    return _cached_date_today()

def get_now_cached():
    """Retorna datetime.now() com cache"""
    return _cached_datetime_now()

def clear_date_cache():
    """Limpa cache de datas - chamar quando necessário"""
    _cached_date_today.cache_clear()
    _cached_datetime_now.cache_clear()

