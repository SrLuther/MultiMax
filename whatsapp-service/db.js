/**
 * db.js
 *
 * Camada simples de acesso ao SQLite para system_settings.
 */

const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

function normalizeSql(sql) {
  return sql.replace(/\$\d+/g, '?');
}

async function initDb() {
  const dbFile = process.env.DB_FILE_PATH || '/multimax-data/estoque.db';
  const db = await open({
    filename: dbFile,
    driver: sqlite3.Database,
  });

  await db.exec(`
    CREATE TABLE IF NOT EXISTS system_settings (
      key TEXT PRIMARY KEY,
      value TEXT,
      created_at TEXT,
      updated_at TEXT
    );
  `);

  return {
    async query(sql, params = []) {
      const sqlLower = sql.trim().toLowerCase();
      let normalized = normalizeSql(sql).replace(/NOW\(\)/gi, "datetime('now')");

      // Converter ON CONFLICT (PostgreSQL) para INSERT OR REPLACE (SQLite)
      if (normalized.includes('ON CONFLICT')) {
        // Extrai o valor que será inserido/atualizado
        // INSERT INTO ... VALUES (...) ON CONFLICT (...) DO UPDATE SET value = $1
        normalized = normalized.replace(
          /INSERT INTO (\w+) \(([^)]+)\) VALUES \(([^)]+)\) ON CONFLICT[^D]*DO UPDATE SET[^W]*WHERE/i,
          'INSERT OR REPLACE INTO $1 ($2) VALUES ($3) WHERE'
        );
        // Fallback simples para upserts básicos
        normalized = normalized.replace(
          /INSERT INTO (\w+) \(([^)]+)\) VALUES \(([^)]+)\) ON CONFLICT[^D]*DO UPDATE SET[^R]*RETURNING/i,
          'INSERT OR REPLACE INTO $1 ($2) VALUES ($3) RETURNING'
        );
      }

      if (sqlLower.startsWith('select')) {
        const rows = await db.all(normalized, params);
        return { rows };
      }

      if (sqlLower.includes('returning')) {
        const stripped = normalized.replace(/returning[\s\S]*/i, '').trim();
        await db.run(stripped, params);

        let key = null;
        if (sqlLower.includes("'alert_whatsapp_phone'")) {
          key = 'alert_whatsapp_phone';
        } else if (sqlLower.includes("'last_test_alert_at'")) {
          key = 'last_test_alert_at';
        }

        if (key) {
          const row = await db.get(
            'SELECT value, updated_at FROM system_settings WHERE key = ? LIMIT 1',
            [key]
          );
          return { rows: row ? [row] : [] };
        }

        return { rows: [] };
      }

      await db.run(normalized, params);
      return { rows: [] };
    },
  };
}

module.exports = { initDb };
