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

async function listGroupsAndExit(sock) {
  try {
    const groupsMap = await sock.groupFetchAllParticipating();
    const groups = Object.values(groupsMap).sort((a, b) => (a.subject || "").localeCompare(b.subject || ""));

    if (!groups.length) {
      logger.info("Nenhum grupo encontrado para este número.");
    } else {
      logger.info("Grupos encontrados (nome -> group_id):");
      groups.forEach((g) => {
        const name = g.subject || "(sem nome)";
        logger.info(`${name} -> ${g.id}`);
      });
    }
    logger.info("Encerrando serviço após listar grupos.");
    process.exit(0);
  } catch (err) {
    logger.error({ err }, "Erro ao listar grupos");
    process.exit(1);
  }
}

async function main() {
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

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      logger.info("Escaneie o QR Code abaixo para conectar:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      logger.info("Conectado com sucesso. Listando grupos...");
      listGroupsAndExit(sock);
    }

    if (connection === "close") {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      if (statusCode === DisconnectReason.loggedOut) {
        logger.error("Sessão expirada. Apague a pasta auth/ e refaça o login.");
        process.exit(1);
      }
    }
  });
}

process.on("SIGINT", () => {
  logger.info("Interrompido pelo usuário. Encerrando...");
  process.exit(0);
});

main().catch((err) => {
  logger.error({ err }, "Falha ao iniciar o serviço WhatsApp");
  process.exit(1);
});
