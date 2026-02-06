/**
 * whatsapp-service/index.js
 *
 * Central de Notificações e Observabilidade MultiMax
 *
 * - Monitora erros do API e frontend
 * - Eventos Docker em tempo real
 * - Heartbeat periódico
 * - Alertas via WhatsApp
 * - Healthcheck integrado
 */

// Injetar crypto.webcrypto como global para compatibilidade com Node 18
if (!global.crypto) {
  const { webcrypto } = require("crypto");
  global.crypto = webcrypto;
}

const path = require("path");
const pino = require("pino");
const qrcode = require("qrcode-terminal");
const qrcodePng = require("qrcode");
const express = require("express");
const {
  default: makeWASocket,
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = require("@whiskeysockets/baileys");

const { sendEvent, validatePhoneNumber, formatPhoneForWhatsApp } = require("./errorWhatsapp");
const DockerListener = require("./dockerListener");
const { initDb } = require("./db");
const FLASK_API_URL = (process.env.FLASK_API_URL || process.env.APP_BASE_URL || "http://multimax:5000").replace(/\/$/, "");

async function fetchAlertPhoneFromApi() {
  try {
    const resp = await fetch(`${FLASK_API_URL}/api/settings/alert-phone`, {
      headers: { Accept: "application/json" },
    });
    if (resp.status === 404) {
      return { phone: null, status: 404, payload: null };
    }
    const payload = await resp.json().catch(() => null);
    return {
      phone: payload?.data?.phone || payload?.phone || null,
      status: resp.status,
      payload,
    };
  } catch (err) {
    return { phone: null, status: 500, payload: { erro: err.message } };
  }
}

async function updateAlertPhoneInApi(phone) {
  try {
    const resp = await fetch(`${FLASK_API_URL}/api/settings/alert-phone`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ phone }),
    });
    const payload = await resp.json().catch(() => null);
    return { status: resp.status, payload };
  } catch (err) {
    return { status: 500, payload: { erro: err.message } };
  }
}

// Custom logger que garante output em Docker
const serializeError = (err) => {
  if (!err) return undefined;
  if (err instanceof Error) {
    return {
      name: err.name,
      message: err.message,
      stack: err.stack,
    };
  }
  if (typeof err === "object") {
    return {
      message: err.message || String(err),
      stack: err.stack,
      ...err,
    };
  }
  return { message: String(err) };
};

const createLogger = (module) => {
  const levels = { trace: 10, debug: 20, info: 30, warn: 40, error: 50, fatal: 60 };

  const writeLog = (levelName, dataOrMsg, maybeMsg) => {
    let payload = {};
    let msg = "";

    if (typeof dataOrMsg === "string") {
      msg = dataOrMsg;
    } else if (dataOrMsg && typeof dataOrMsg === "object") {
      payload = { ...dataOrMsg };
      msg = typeof maybeMsg === "string" ? maybeMsg : "";
    }

    if (payload && payload.err) {
      payload.err = serializeError(payload.err);
    }

    const logEntry = JSON.stringify({
      level: levels[levelName] ?? 30,
      time: Date.now(),
      module,
      ...payload,
      msg,
    });

    if (levels[levelName] >= 50) {
      console.error(logEntry);
      process.stderr.write("");
    } else {
      console.log(logEntry);
      process.stdout.write("");
    }
  };

  return {
    trace: (dataOrMsg, maybeMsg) => writeLog("trace", dataOrMsg, maybeMsg),
    debug: (dataOrMsg, maybeMsg) => writeLog("debug", dataOrMsg, maybeMsg),
    info: (dataOrMsg, maybeMsg) => writeLog("info", dataOrMsg, maybeMsg),
    warn: (dataOrMsg, maybeMsg) => writeLog("warn", dataOrMsg, maybeMsg),
    error: (dataOrMsg, maybeMsg) => writeLog("error", dataOrMsg, maybeMsg),
    fatal: (dataOrMsg, maybeMsg) => writeLog("fatal", dataOrMsg, maybeMsg),
    child: () => createLogger(module),
  };
};

const logger = createLogger("whatsapp-service");

let globalSocket = null;
let globalDb = null;
let reconnectTimeout = null;
let notifyGroupId = null;
let dockerListener = null;
let startupAlertSent = false;
let heartbeatInterval = null;
let baileysConnected = false;
let lastQr = null;
let lastQrAt = null;
let lastQrPng = null;

// ============================================================================
// STARTUP ALERT
// ============================================================================

async function sendStartupAlert() {
  if (!globalSocket || !baileysConnected || startupAlertSent) return;

  try {
    await sendEvent(globalSocket, {
      type: "startup",
      level: "info",
      source: "whatsapp-service",
      description: "MultiMax iniciado com sucesso",
      message: `NODE_ENV: ${process.env.NODE_ENV || 'development'}, PID: ${process.pid}`,
      context: "startup",
      host: process.env.HOSTNAME || 'unknown',
      timestamp: new Date().toISOString(),
    }, globalDb);

    startupAlertSent = true;
    logger.info("✓ Startup alert enviado");
  } catch (err) {
    logger.error({ err }, "Erro ao enviar startup alert");
  }
}

// ============================================================================
// HEARTBEAT (a cada 6 horas)
// ============================================================================

function setupHeartbeat() {
  // Enviar primeira vez após 10 segundos
  setTimeout(() => {
    sendHeartbeat();
  }, 10000);

  // Depois a cada 6 horas
  heartbeatInterval = setInterval(() => {
    sendHeartbeat();
  }, 6 * 60 * 60 * 1000);
}

async function sendHeartbeat() {
  if (!globalSocket || !baileysConnected) return;

  try {
    await sendEvent(globalSocket, {
      type: "heartbeat",
      level: "info",
      source: "whatsapp-service",
      description: "MultiMax online e operacional",
      message: "Health check periódico",
      context: "heartbeat",
      host: process.env.HOSTNAME || 'unknown',
      timestamp: new Date().toISOString(),
    }, globalDb);

    logger.info("💚 Heartbeat enviado");
  } catch (err) {
    logger.error({ err }, "Erro ao enviar heartbeat");
  }
}

// ============================================================================
// PROCESSO: UNHANDLED REJECTION E UNCAUGHT EXCEPTION
// ============================================================================

process.on("unhandledRejection", async (reason, promise) => {
  logger.error({ reason, promise }, "Unhandled Rejection");

  try {
    await sendEvent(globalSocket, {
      type: "error",
      level: "fatal",
      source: "system",
      description: "Promise rejection não tratada",
      message: reason?.message || String(reason),
      stack: reason?.stack,
      context: "unhandled_rejection",
      host: process.env.HOSTNAME || 'unknown',
      timestamp: new Date().toISOString(),
    }, globalDb);
  } catch (err) {
    logger.error({ err }, "Erro ao enviar unhandled rejection alert");
  }
});

process.on("uncaughtException", async (error) => {
  logger.error({ err: error }, "Uncaught Exception");

  try {
    await sendEvent(globalSocket, {
      type: "error",
      level: "fatal",
      source: "system",
      description: "Exceção não tratada no processo Node.js",
      message: error.message,
      stack: error.stack,
      context: "uncaught_exception",
      host: process.env.HOSTNAME || 'unknown',
      timestamp: new Date().toISOString(),
    }, globalDb);
  } catch (err) {
    logger.error({ err }, "Erro ao enviar uncaught exception alert");
  }

  process.exit(1);
});

/**
 * Lista grupos disponíveis (chamado uma vez na conexão inicial)
 */
async function listGroups(sock) {
  try {
    const groupsMap = await sock.groupFetchAllParticipating();
    const groups = Object.values(groupsMap).sort((a, b) => (a.subject || "").localeCompare(b.subject || ""));

    if (!groups.length) {
      logger.info("Nenhum grupo encontrado para este número.");
    } else {
      logger.info("Grupos disponíveis (nome -> group_id):");
      groups.forEach((g) => {
        const name = g.subject || "(sem nome)";
        logger.info(`  ${name} -> ${g.id}`);

        // Identificar o grupo "Notify" para envio via endpoint
        if (name.toLowerCase() === "notify") {
          notifyGroupId = g.id;
          logger.info(`✓ Grupo Notify identificado: ${g.id}`);
        }
      });
    }
    logger.info("Serviço ativo. Aguardando eventos...");
  } catch (err) {
    logger.error({ err }, "Erro ao listar grupos");
  }
}

/**
 * Envia mensagem para o grupo Notify
 */
async function sendToNotifyGroup(mensagem, arquivoBase64, nomeArquivo) {
  if (!globalSocket) {
    throw new Error("WhatsApp não está conectado");
  }

  if (!notifyGroupId) {
    throw new Error("Grupo Notify não encontrado");
  }

  try {
    const messageContent = {};

    // Adicionar texto da mensagem
    if (mensagem) {
      messageContent.text = mensagem;
    }

    // Adicionar arquivo se fornecido
    if (arquivoBase64 && nomeArquivo) {
      const buffer = Buffer.from(arquivoBase64, "base64");
      messageContent.document = buffer;
      messageContent.fileName = nomeArquivo;
      messageContent.mimetype = "application/pdf";
    }

    await globalSocket.sendMessage(notifyGroupId, messageContent);
    const logMsg = arquivoBase64
      ? `Mensagem com arquivo (${nomeArquivo}) enviada com sucesso`
      : "Mensagem enviada com sucesso";
    logger.info({ grupo: "Notify", tamanho: mensagem?.length || 0, arquivo: nomeArquivo }, logMsg);
    return true;
  } catch (err) {
    // Ignorar erros de histórico do WhatsApp
    if (err.message && err.message.includes("history")) {
      logger.warn({ err: err.message }, "Aviso de histórico ignorado");
      return true;
    }
    logger.error({ err, grupo: "Notify" }, "Falha ao enviar mensagem");
    throw err;
  }
}

/**
 * Inicializa rotinas automáticas (placeholder para futuras implementações)
 */
function setupAutomatedTasks(sock) {
  // Exemplo: tarefas periódicas podem ser adicionadas aqui
  // setInterval(() => { ... }, 60000);
  logger.info("Rotinas automáticas preparadas (aguardando implementação).");
}

/**
 * Conecta ao WhatsApp e mantém conexão ativa
 */
async function connectToWhatsApp() {
  const authFolder = path.join(__dirname, "auth");
  const { state, saveCreds } = await useMultiFileAuthState(authFolder);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: false,
    logger,
    markOnlineOnConnect: false,
    browser: ["MultiMax", "Desktop", "1.0.0"],
  });

  globalSocket = sock;

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      logger.info("Escaneie o QR Code abaixo para conectar:");
      logger.info(`QR_CODE_DATA:${qr}`);
      try {
        const fs = require("fs");
        fs.writeFileSync(path.join(__dirname, "auth", "last-qr.txt"), qr, "utf8");
      } catch (err) {
        logger.error({ err }, "Falha ao salvar QR em arquivo");
      }
      lastQr = qr;
      lastQrAt = new Date();
      try {
        lastQrPng = await qrcodePng.toBuffer(qr, { type: "png", margin: 1, width: 320 });
      } catch (err) {
        logger.error({ err }, "Erro ao gerar QR em PNG");
        lastQrPng = null;
      }
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      logger.info("✓ Conectado com sucesso ao WhatsApp");
      baileysConnected = true;
      await listGroups(sock);
      setupAutomatedTasks(sock);

      // Enviar startup alert
      setTimeout(() => sendStartupAlert(), 2000);

      // Iniciar heartbeat
      setupHeartbeat();

      // Iniciar listener docker
      if (dockerListener) {
        dockerListener.start();
      }
    }

    if (connection === "close") {
      baileysConnected = false;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      if (statusCode === DisconnectReason.loggedOut) {
        logger.error("✗ Sessão expirada. Apague a pasta auth/ e refaça o login.");
        process.exit(1);
      } else if (shouldReconnect) {
        logger.warn("Conexão perdida. Reconectando em 5 segundos...");
        reconnectTimeout = setTimeout(() => {
          connectToWhatsApp();
        }, 5000);
      }
    }
  });

  return sock;
}

/**
 * Configura servidor HTTP com endpoints de notificação e configuração
 */
function setupHttpServer(db) {
  const app = express();
  app.use(express.json());

  // ========== HEALTHCHECK ==========
  app.get("/health", (req, res) => {
    res.status(200).json({
      status: "ok",
      service: "whatsapp-service",
      whatsapp_connected: baileysConnected,
      timestamp: new Date().toISOString(),
    });
  });

  app.get("/health/whatsapp", (req, res) => {
    res.status(200).json({
      connected: baileysConnected,
      timestamp: new Date().toISOString(),
    });
  });

  // ========== QR CODE (PNG) ==========
  app.get("/qr.png", (req, res) => {
    if (!lastQrPng) {
      return res.status(404).json({ status: "error", message: "QR Code não disponível" });
    }
    res.setHeader("Content-Type", "image/png");
    res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
    res.setHeader("Pragma", "no-cache");
    res.setHeader("Expires", "0");
    if (lastQrAt) {
      res.setHeader("X-QR-Generated-At", lastQrAt.toISOString());
    }
    return res.status(200).send(lastQrPng);
  });

  // ========== NOTIFICAÇÕES (Grupo Notify) ==========
  app.post("/notify", async (req, res) => {
    const { mensagem, origin, arquivo_base64, nome_arquivo } = req.body;

    if (!mensagem && !arquivo_base64) {
      logger.warn("Requisição /notify sem mensagem ou arquivo");
      return res.status(400).json({ erro: "Campo 'mensagem' ou 'arquivo_base64' é obrigatório" });
    }

    try {
      logger.info({ origem: origin || "unknown" }, "Processando envio de mensagem");
      await sendToNotifyGroup(mensagem, arquivo_base64, nome_arquivo);
      res.status(200).json({ sucesso: true, mensagem: "Enviado para grupo Notify" });
    } catch (err) {
      logger.error({ err, origin }, "Erro ao processar /notify");
      res.status(500).json({ erro: err.message || "Falha ao enviar mensagem" });
    }
  });

  // ========== CONFIGURAÇÃO: GET alert-phone ==========
  app.get("/settings/alert-phone", async (req, res) => {
    try {
      const { phone, status, payload } = await fetchAlertPhoneFromApi();
      if (status >= 400 && status !== 404) {
        return res.status(status).json({ erro: payload?.message || payload?.erro || "Falha ao buscar número" });
      }

      return res.status(200).json({
        phone,
        configured: !!phone,
        last_test: null, // TODO: implementar rastreamento
      });
    } catch (err) {
      logger.error({ err }, "Erro ao buscar alert-phone");
      res.status(500).json({ erro: err.message });
    }
  });

  // ========== CONFIGURAÇÃO: PUT alert-phone ==========
  app.put("/settings/alert-phone", async (req, res) => {
    const { phone } = req.body;

    try {
      if (!phone) {
        return res.status(400).json({ erro: "Campo 'phone' é obrigatório" });
      }

      // Validar e formatar
      const validated = validatePhoneNumber(phone);
      if (!validated) {
        return res.status(400).json({
          erro: "Número inválido. Esperado: 11987654321 ou +5511987654321",
        });
      }

      const { status, payload } = await updateAlertPhoneInApi(validated);
      if (status >= 400) {
        return res.status(status).json({ erro: payload?.message || payload?.erro || "Falha ao atualizar número" });
      }

      const formatted = formatPhoneForWhatsApp(validated);
      const newPhone = payload?.data?.phone || payload?.phone || validated;

      logger.info({ phone: newPhone }, "alert-phone atualizado");

      return res.status(200).json({
        sucesso: true,
        phone: newPhone,
        message: "Número de alerta atualizado com sucesso",
        whatsapp_jid: formatted,
      });
    } catch (err) {
      logger.error({ err }, "Erro ao atualizar alert-phone");
      res.status(500).json({ erro: err.message });
    }
  });

  // ========== TESTE: POST test-alert-phone ==========
  app.post("/settings/test-alert-phone", async (req, res) => {
    try {
      if (!baileysConnected) {
        return res.status(503).json({ erro: "WhatsApp não está conectado" });
      }

      const { phone, status, payload } = await fetchAlertPhoneFromApi();
      if (status >= 400 || !phone) {
        return res.status(404).json({ erro: payload?.message || payload?.erro || "Número não configurado" });
      }

      const sent = await sendEvent(globalSocket, {
        type: "test",
        level: "info",
        source: "whatsapp-service",
        description: "🧪 Teste da Central de Notificações MultiMax",
        message: `Teste de conectividade do sistema de alertas (${new Date().toISOString()})`,
        context: "test_alert",
        host: process.env.HOSTNAME || "unknown",
        timestamp: new Date().toISOString(),
        phone,
        force: true,
      }, db);

      if (!sent) {
        return res.status(500).json({
          erro: "Falha ao enviar teste. Número configurado?",
        });
      }

      res.status(200).json({
        sucesso: true,
        message: "Teste enviado com sucesso",
      });
    } catch (err) {
      logger.error({ err }, "Erro ao enviar teste");
      res.status(500).json({ erro: err.message });
    }
  });

  // ========== ERRO PROPOSITAL (teste) ==========
  app.post("/test-error-log", async (req, res) => {
    try {
      throw new Error("Erro proposital para teste do sistema de alertas");
    } catch (err) {
      await sendEvent(globalSocket, {
        type: "error",
        level: "error",
        source: "whatsapp-service",
        description: "Erro proposital gerado por teste manual",
        message: err.message,
        stack: err.stack,
        context: "manual_test",
        route: "/test-error-log",
        host: process.env.HOSTNAME || "unknown",
        timestamp: new Date().toISOString(),
      }, db);

      res.status(200).json({
        sucesso: true,
        message: "Erro de teste enviado para alertas",
      });
    }
  });

  app.listen(3001, "0.0.0.0", () => {
    logger.info("Servidor HTTP rodando na porta 3001");
    logger.info("Endpoints disponíveis:");
    logger.info("  GET  /health");
    logger.info("  GET  /health/whatsapp");
    logger.info("  POST /notify");
    logger.info("  GET  /settings/alert-phone");
    logger.info("  PUT  /settings/alert-phone");
    logger.info("  POST /settings/test-alert-phone");
    logger.info("  POST /test-error-log");
  });
}

/**
 * Ponto de entrada principal
 */
async function main() {
  logger.info("Iniciando Central de Notificações MultiMax...");

  try {
    globalDb = await initDb(logger);
    logger.info("✓ DB SQLite conectado");
  } catch (err) {
    logger.warn({ err }, "DB indisponível, endpoints de settings desativados");
    globalDb = null;
  }

  // Inicializar docker listener (mas não iniciar ainda, espera Baileys conectar)
  dockerListener = new DockerListener(globalSocket, globalDb);

  setupHttpServer(globalDb);
  await connectToWhatsApp();
}

process.on("SIGINT", () => {
  logger.info("SIGINT recebido. Encerrando graciosamente...");
  cleanup();
  process.exit(0);
});

process.on("SIGTERM", () => {
  logger.info("SIGTERM recebido. Encerrando graciosamente...");
  cleanup();
  process.exit(0);
});

function cleanup() {
  if (reconnectTimeout) clearTimeout(reconnectTimeout);
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  if (globalSocket) globalSocket.end();
  if (dockerListener) dockerListener.stop();
}

main().catch((err) => {
  logger.error({ err }, "Falha crítica ao iniciar");
  process.exit(1);
});
