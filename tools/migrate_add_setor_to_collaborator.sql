-- Script de Migração: Adicionar setor_id na tabela collaborator
-- Executar este SQL no banco de dados de produção
-- Data: 2026-01-20
-- Versão: 2.6.73

-- Adicionar coluna setor_id (nullable para compatibilidade com dados existentes)
ALTER TABLE collaborator ADD COLUMN setor_id INTEGER;

-- Criar índice para melhor performance
CREATE INDEX IF NOT EXISTS ix_collaborator_setor_id ON collaborator(setor_id);

-- Adicionar Foreign Key constraint (se o banco suportar)
-- ALTER TABLE collaborator ADD CONSTRAINT fk_collaborator_setor
--   FOREIGN KEY (setor_id) REFERENCES setor(id);

-- Verificar resultado
SELECT name, setor_id FROM collaborator LIMIT 5;
