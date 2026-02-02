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

async function initDb(logger) {
  const dbFile = process.env.DB_FILE_PATH || '/multimax-data/estoque.db';
  const db = await open({
    filename: dbFile,
    driver: sqlite3.Database,
  });

  // Fallback logger se não fornecido
  if (!logger) {
    logger = {
      info: (msg) => {
        console.log(`[db.js] ${msg}`);
        process.stdout.write('');
      },
      error: (msg) => {
        console.error(`[db.js] ERROR: ${msg}`);
        process.stderr.write('');
      },
      debug: (msg) => {
        console.log(`[db.js] DEBUG: ${msg}`);
        process.stdout.write('');
      }
    };
  }

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

      if (logger) logger.info(`[db.js] SQL Original: ${sql}`);

      // Converter ON CONFLICT (PostgreSQL) para INSERT OR REPLACE (SQLite)
      if (normalized.includes('ON CONFLICT')) {
        normalized = normalized
          .replace(/ON CONFLICT[^R]*RETURNING/i, 'RETURNING')
          .replace(/ON CONFLICT[^;]*$/i, '');
      }

      // Converter INSERT INTO para INSERT OR REPLACE quando há conflito
      if (sqlLower.includes('on conflict') || sqlLower.includes('insert or replace')) {
        normalized = normalized.replace(/^INSERT INTO/i, 'INSERT OR REPLACE INTO');
      }

      if (logger) logger.info(`[db.js] SQL Final: ${normalized}`);
      if (logger) logger.info(`[db.js] Params: ${JSON.stringify(params)}`);

      if (sqlLower.startsWith('select')) {
        const rows = await db.all(normalized, params);
        return { rows };
      }

      if (sqlLower.includes('returning')) {
        const stripped = normalized.replace(/returning[\s\S]*/i, '').trim();
        if (logger) logger.info(`[db.js] SQL a executar (RETURNING): ${stripped}`);
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
          if (logger) logger.info(`[db.js] Valor recuperado: ${JSON.stringify(row)} para key: ${key}`);
          return { rows: row ? [row] : [] };
        }

        return { rows: [] };
      }

      if (logger) logger.info(`[db.js] SQL a executar (normal): ${normalized}`);
      await db.run(normalized, params);
      return { rows: [] };
    },
  };
}

module.exports = { initDb };
