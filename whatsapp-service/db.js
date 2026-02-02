/**
 * db.js - DEPRECATED
 *
 * Este arquivo foi descontinuado. Todas as configurações
 * são agora armazenadas no PostgreSQL via Flask.
 *
 * O serviço Node.js é APENAS um executor HTTP, sem lógica de banco de dados.
 * Use Flask em /api/settings/alert-phone para todas as configurações.
 */

async function initDb(logger) {
  if (!logger) {
    logger = {
      info: (msg) => console.log(`[db.js] ${msg}`),
      error: (msg) => console.error(`[db.js] ERROR: ${msg}`),
      debug: (msg) => console.log(`[db.js] DEBUG: ${msg}`)
    };
  }

  logger.info('db.js is deprecated. All data is now in PostgreSQL via Flask.');
  logger.info('Node.js is now a stateless HTTP executor only.');

  // Retornar stub que força requisições a Flask
  return {
    async query() {
      throw new Error('db.query() is deprecated. Use Flask API /api/settings/alert-phone');
    },

    async get(sql, params = []) {
      throw new Error('db.get() is deprecated. Use Flask API /api/settings/alert-phone');
    },

    async run(sql, params = []) {
      throw new Error('db.run() is deprecated. Use Flask API /api/settings/alert-phone');
    },

    async all(sql, params = []) {
      throw new Error('db.all() is deprecated. Use Flask API /api/settings/alert-phone');
    },

    async close() {
      logger.info('No database connection to close.');
    }
  };
}

module.exports = { initDb };
