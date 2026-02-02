-- mssql ignore all
-- This file contains PostgreSQL syntax (NOT MSSQL/T-SQL)
-- MSSQL linter errors are false positives
--
-- whatsapp-service/schema-postgresql.sql
--
-- Schema para Central de Notificações MultiMax
-- PostgreSQL 12+
--
-- NOTA: Os erros do linter MSSQL são FALSOS POSITIVOS.
-- Este arquivo usa sintaxe PostgreSQL, não SQL Server.
-- Use este arquivo com: psql -U multimax -d multimax -f schema.sql
--
-- Erros do MSSQL que podem aparecer:
-- - CREATE TABLE IF NOT EXISTS (sintaxe PostgreSQL válida)
-- - CREATE INDEX IF NOT EXISTS (sintaxe PostgreSQL válida)
-- - CREATE OR REPLACE FUNCTION (sintaxe PostgreSQL válida)
-- - TRIGGER com BEFORE (sintaxe PostgreSQL válida)
--
-- Estes NÃO são erros - é apenas que o linter MSSQL não entende PostgreSQL.

-- ============================================================================
-- Criar tabela system_settings (se não existir)
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_settings (
  id SERIAL PRIMARY KEY,
  key VARCHAR(255) NOT NULL UNIQUE,
  value TEXT,
  description VARCHAR(1024),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Criar índice para busca rápida por chave
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);

-- ============================================================================
-- Inserir valores iniciais (se não existirem)
-- ============================================================================

INSERT INTO system_settings (key, value, description)
VALUES
  ('alert_whatsapp_phone', '', 'Número de WhatsApp para alertas (formato: 5511987654321@s.whatsapp.net)'),
  ('last_test_alert_at', '', 'Timestamp do último teste de alerta enviado')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Criar função para atualizar updated_at automaticamente
-- ============================================================================

CREATE OR REPLACE FUNCTION update_system_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Criar trigger para atualizar updated_at
-- ============================================================================

DROP TRIGGER IF EXISTS trg_system_settings_update ON system_settings;

CREATE TRIGGER trg_system_settings_update
BEFORE UPDATE ON system_settings
FOR EACH ROW
EXECUTE FUNCTION update_system_settings_timestamp();

-- ============================================================================
-- Exemplos de consultas
-- ============================================================================

-- Buscar número de alerta
-- SELECT value FROM system_settings WHERE key = 'alert_whatsapp_phone';

-- Atualizar número de alerta
-- UPDATE system_settings SET value = '5511987654321@s.whatsapp.net' WHERE key = 'alert_whatsapp_phone';

-- Listar todas as configurações
-- SELECT key, value, updated_at FROM system_settings ORDER BY updated_at DESC;

-- Limpar teste antigo (manter histórico)
-- UPDATE system_settings SET value = NULL WHERE key = 'last_test_alert_at';
