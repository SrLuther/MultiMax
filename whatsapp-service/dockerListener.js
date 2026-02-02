/**
 * dockerListener.js
 *
 * Monitora eventos de todos os containers Docker em tempo real.
 * Envia alertas via WhatsApp para: start, stop, die, restart
 */

const { spawn } = require('child_process');
const { sendEvent } = require('./errorWhatsapp');

class DockerListener {
  constructor(sock, db) {
    this.sock = sock;
    this.db = db;
    this.process = null;
    this.isRunning = false;
  }

  /**
   * Inicia listener de docker events
   */
  start() {
    if (this.isRunning) {
      console.log('[DockerListener] Já em execução');
      return;
    }

    console.log('[DockerListener] Iniciando...');

    try {
      this.process = spawn('docker', ['events', '--format', '{{json .}}']);

      this.process.on('error', (err) => {
        console.error('[DockerListener] Erro ao iniciar docker events:', err.message);
        this.isRunning = false;
        setTimeout(() => this.start(), 10000);
      });

      this.process.stdout.on('data', (data) => {
        this.handleEvent(data.toString());
      });

      this.process.stderr.on('data', (data) => {
        console.error('[DockerListener] Erro:', data.toString());
      });

      this.process.on('close', (code) => {
        console.log(`[DockerListener] Processo encerrado com código ${code}`);
        this.isRunning = false;
        // Reiniciar automaticamente após 10 segundos
        setTimeout(() => this.start(), 10000);
      });

      this.isRunning = true;
      console.log('[DockerListener] Ativo');
    } catch (err) {
      console.error('[DockerListener] Erro ao iniciar:', err.message);
      this.isRunning = false;
      // Tentar reiniciar
      setTimeout(() => this.start(), 10000);
    }
  }

  /**
   * Processa linha de evento Docker
   */
  handleEvent(line) {
    try {
      const event = JSON.parse(line);

      // Filtrar apenas eventos de container
      if (event.Type !== 'container') return;

      // Ações relevantes
      const relevantActions = ['start', 'stop', 'die', 'restart'];
      if (!relevantActions.includes(event.Action)) return;

      const containerName = event.Actor?.Attributes?.name || 'unknown';
      const timestamp = event.time || Date.now();

      // Mapear emoji e level por ação
      const actionConfig = {
        start: { emoji: '🟢', level: 'info', desc: 'iniciado' },
        stop: { emoji: '🟡', level: 'info', desc: 'parado' },
        die: { emoji: '🔴', level: 'warn', desc: 'travou/morreu' },
        restart: { emoji: '🔄', level: 'info', desc: 'reiniciado' },
      };

      const config = actionConfig[event.Action] || { emoji: '⚫', level: 'info', desc: event.Action };

      // Enviar evento
      sendEvent(this.sock, {
        id: `docker_${event.id}_${timestamp}`,
        type: 'docker',
        level: config.level,
        source: 'docker',
        context: `docker_${event.Action}`,
        description: `Container ${config.desc}: ${containerName}`,
        message: `Ação: ${event.Action}`,
        container: containerName,
        host: 'docker-daemon',
        timestamp: new Date(timestamp * 1000).toISOString(),
      }, this.db).catch(err => {
        console.error('[DockerListener] Erro ao enviar evento:', err.message);
      });

    } catch (err) {
      // JSON parse error - ignorar linhas inválidas
      if (!line.startsWith('{')) return;
      console.error('[DockerListener] Erro ao processar evento:', err.message);
    }
  }

  /**
   * Para o listener
   */
  stop() {
    if (this.process) {
      this.process.kill();
      this.isRunning = false;
      console.log('[DockerListener] Parado');
    }
  }
}

module.exports = DockerListener;
