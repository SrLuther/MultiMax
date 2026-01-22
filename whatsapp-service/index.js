// Injetar crypto.webcrypto como global para compatibilidade com Node 18
if (!global.crypto) {
  const { webcrypto } = require("crypto");
  global.crypto = webcrypto;
}

const path = require("path");
const pino = require("pino");
const qrcode = require("qrcode-terminal");
const {
  default: makeWASocket,
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = require("@whiskeysockets/baileys");

const logger = pino({ level: "info" }).child({ module: "whatsapp-service" });

let globalSocket = null;
let reconnectTimeout = null;

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
      });
    }
    logger.info("Serviço ativo. Aguardando eventos...");
  } catch (err) {
    logger.error({ err }, "Erro ao listar grupos");
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
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      logger.info("✓ Conectado com sucesso ao WhatsApp");
      await listGroups(sock);
      setupAutomatedTasks(sock);
    }

    if (connection === "close") {
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
 * Ponto de entrada principal
 */
async function main() {
  logger.info("Iniciando serviço WhatsApp (modo daemon)...");
  await connectToWhatsApp();
}

process.on("SIGINT", () => {
  logger.info("Sinal de interrupção recebido. Encerrando graciosamente...");
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
  }
  if (globalSocket) {
    globalSocket.end();
  }
  process.exit(0);
});

process.on("SIGTERM", () => {
  logger.info("Sinal de término recebido. Encerrando graciosamente...");
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
  }
  if (globalSocket) {
    globalSocket.end();
  }
  process.exit(0);
});

main().catch((err) => {
  logger.error({ err }, "Falha crítica ao iniciar o serviço WhatsApp");
  process.exit(1);
});
