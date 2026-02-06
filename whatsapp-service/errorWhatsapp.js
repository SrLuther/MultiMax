/**
 * errorWhatsapp.js
 *
 * Sistema central de notificações e observabilidade.
 * Envia eventos estruturados via WhatsApp para monitoramento em tempo real.
 *
 * Uso:
 *   const { sendEvent } = require('./errorWhatsapp');
 *   await sendEvent(sock, { type, level, source, ... })
 */

const dayjs = require('dayjs');
const utc = require('dayjs/plugin/utc');
const timezone = require('dayjs/plugin/timezone');

dayjs.extend(utc);
dayjs.extend(timezone);

const FLASK_API_URL = (process.env.FLASK_API_URL || process.env.APP_BASE_URL || 'http://multimax:5000').replace(/\/$/, '');

async function fetchAlertPhoneFromApi() {
  try {
    const resp = await fetch(`${FLASK_API_URL}/api/settings/alert-phone`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!resp.ok) return null;
    const payload = await resp.json();
    return payload?.data?.phone || payload?.phone || null;
  } catch (err) {
    return null;
  }
}

// Cache de anti-spam: evita reenviar eventos idênticos consecutivos
const eventCache = {
  lastHash: null,
  lastSent: null,
  ttl: 5 * 60 * 1000, // 5 minutos
};

/**
 * Calcula hash do evento para anti-spam
 */
function hashEvent(event) {
  const key = `${event.type}|${event.level}|${event.source}|${event.message}`;
  return require('crypto').createHash('md5').update(key).digest('hex');
}

/**
 * Formata mensagem WhatsApp com estructura clara
 */
function formatWhatsAppMessage(event, phoneNumber) {
  const now = dayjs().tz('America/Sao_Paulo');
  const dataHora = now.format('DD/MM/YYYY HH:mm:ss');

  // Emoji por tipo/level
  const levelEmojis = {
    info: 'ℹ️',
    warn: '⚠️',
    error: '❌',
    fatal: '🚨',
  };

  const typeEmojis = {
    error: '❌',
    docker: '🐳',
    startup: '🚀',
    heartbeat: '💚',
    test: '🧪',
    info: 'ℹ️',
  };

  const emoji = levelEmojis[event.level] || '📌';
  const typeEmoji = typeEmojis[event.type] || '📌';

  // Construir URL com parâmetros
  const baseUrl = process.env.APP_BASE_URL || 'http://localhost:5000';
  const params = new URLSearchParams();
  params.append('__error', 'true');
  if (event.context) params.append('context', event.context);
  if (event.user?.id) params.append('user', event.user.id);

  const errorUrl = event.route
    ? `${baseUrl}${event.route}?${params.toString()}`
    : `${baseUrl}?${params.toString()}`;

  // Truncar stack em ~1300 chars
  const stackStr = event.stack
    ? event.stack.substring(0, 1300) + (event.stack.length > 1300 ? '...' : '')
    : 'N/A';

  // Montar mensagem
  let msg = `${emoji} ${event.type.toUpperCase()} | ${event.level.toUpperCase()}\n\n`;

  if (event.description) {
    msg += `📝 ${event.description}\n\n`;
  }

  if (event.route) {
    msg += `📍 ${event.route}\n`;
  }

  msg += `🔗 ${errorUrl}\n\n`;

  if (event.user) {
    msg += `👤 Usuário:\n`;
    msg += `   ${event.user.nome || 'Desconhecido'} (${event.user.role || 'sem role'})\n`;
    msg += `   ID: ${event.user.id}\n\n`;
  }

  if (event.context) {
    msg += `⚙️ Contexto: ${event.context}\n`;
  }

  if (event.container) {
    msg += `🐳 Container: ${event.container}\n`;
  }

  if (event.message) {
    msg += `\n💥 ${event.message}\n`;
  }

  if (event.stack) {
    msg += `\n📄 Stack:\n${stackStr}\n`;
  }

  msg += `\n🕒 ${dataHora}`;

  if (event.ciclo) {
    msg += `\n🧭 Ciclo: ${event.ciclo}`;
  }

  return msg;
}

/**
 * Busca número de alerta do banco de dados
 */
async function getAlertPhone(db) {
  try {
    const apiPhone = await fetchAlertPhoneFromApi();
    if (apiPhone) return apiPhone;

    if (!db) return null;

    const result = await db.query(
      `SELECT value FROM system_settings WHERE key = 'alert_whatsapp_phone' LIMIT 1`
    );

    if (result && result.rows && result.rows.length > 0) {
      return result.rows[0].value;
    }
    return null;
  } catch (err) {
    console.error('[getAlertPhone] Erro:', err.message);
    return null;
  }
}

/**
 * Envia evento via WhatsApp
 *
 * @param {Object} sock - Socket Baileys conectado
 * @param {Object} event - Evento estruturado
 * @param {Object} db - Conexão com DB (opcional)
 * @returns {Promise<boolean>} true se enviado, false caso contrário
 */
async function sendEvent(sock, event, db = null) {
  try {
    // Validação mínima
    if (!sock) {
      console.error('[sendEvent] Socket não disponível');
      return false;
    }

    if (!event || !event.type) {
      console.error('[sendEvent] Evento inválido');
      return false;
    }

    // Anti-spam: não reenviar evento idêntico em menos de 5 minutos
    if (!event.force) {
      const hash = hashEvent(event);
      const now = Date.now();

      if (hash === eventCache.lastHash && (now - eventCache.lastSent) < eventCache.ttl) {
        console.log('[sendEvent] Evento ignorado por anti-spam');
        return false;
      }

      eventCache.lastHash = hash;
      eventCache.lastSent = now;
    }

    // Buscar número de alerta do DB
    const phoneNumber = event?.phone || await getAlertPhone(db);
    if (!phoneNumber) {
      console.warn('[sendEvent] Número de alerta não configurado');
      return false;
    }

    // Formatar mensagem
    const message = formatWhatsAppMessage(event, phoneNumber);

    // Enviar via Baileys
    const jid = phoneNumber.includes('@s.whatsapp.net')
      ? phoneNumber
      : `${phoneNumber}@s.whatsapp.net`;

    await sock.sendMessage(jid, { text: message });

    console.log(`[sendEvent] Evento enviado: ${event.type}/${event.level}`);
    return true;

  } catch (err) {
    console.error('[sendEvent] Erro ao enviar evento:', err.message);
    // Não re-throw para não quebrar o sistema
    return false;
  }
}

/**
 * Limpa e valida número de telefone
 */
function validatePhoneNumber(phone) {
  if (!phone || typeof phone !== 'string') return null;

  // Remove caracteres especiais
  let clean = phone.replace(/\D/g, '');

  // Força código país 55 (Brasil)
  if (!clean.startsWith('55')) {
    clean = `55${clean}`;
  }

  // Validação básica: deve ter pelo menos 13 dígitos (55 + 11 + 8 ou 9)
  if (clean.length < 13 || clean.length > 15) {
    return null;
  }

  return clean;
}

/**
 * Adiciona sufixo WhatsApp se necessário
 */
function formatPhoneForWhatsApp(phone) {
  const validated = validatePhoneNumber(phone);
  if (!validated) return null;

  if (!validated.includes('@s.whatsapp.net')) {
    return `${validated}@s.whatsapp.net`;
  }

  return validated;
}

module.exports = {
  sendEvent,
  formatWhatsAppMessage,
  getAlertPhone,
  validatePhoneNumber,
  formatPhoneForWhatsApp,
};
