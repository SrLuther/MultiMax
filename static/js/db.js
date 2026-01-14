/**
 * Database Admin Module - JavaScript externo
 * Sem dependências de Jinja2 ou template rendering
 */

(function() {
    'use strict';

    // Estado global do módulo
    const state = {
        urls: {},
        intervals: {
            healthCheck: null,
            logs: null,
            metrics: null,
            gitStatus: null
        },
        charts: {
            cpu: null,
            mem: null,
            trends: null
        },
        logsPaused: false,
        gitStatusInterval: null,
        updateCountdownInterval: null,
        updateCountdown: 10
    };

    // Função auxiliar para escapar HTML (prevenir XSS)
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    // Função auxiliar para criar elementos DOM de forma segura
    function createElement(tag, attributes, textContent) {
        const el = document.createElement(tag);
        if (attributes) {
            Object.keys(attributes).forEach(key => {
                if (key === 'className') {
                    el.className = attributes[key];
                } else if (key === 'innerHTML') {
                    // innerHTML só para conteúdo estático/controlado
                    el.innerHTML = attributes[key];
                } else {
                    el.setAttribute(key, attributes[key]);
                }
            });
        }
        if (textContent !== undefined) {
            el.textContent = textContent;
        }
        return el;
    }

    /**
     * Inicialização: ler configurações do DOM
     */
    function initialize() {
        // Ler URLs das meta tags
        const urlMetaTags = [
            'db-url-metrics',
            'db-url-health',
            'db-url-logs',
            'db-url-metrics-trends',
            'db-url-slow-queries',
            'db-url-maintenance-stats',
            'db-url-maintenance-recommendations',
            'db-url-maintenance-history',
            'db-url-maintenance-cleanup',
            'db-url-maintenance-optimize',
            'db-url-verify-backups',
            'db-url-maintenance-run-all',
            'db-url-maintenance-export-report',
            'db-url-git-status',
            'db-url-git-update'
        ];

        urlMetaTags.forEach(name => {
            const meta = document.querySelector(`meta[name="${name}"]`);
            if (meta) {
                const key = name.replace('db-url-', '').replace(/-/g, '_');
                state.urls[key] = meta.getAttribute('content');
            }
        });
    }

    // Chart.js loader
    var __mmChartsLoaded = false;
    function ensureChartJs(cb) {
        if (window.Chart) {
            __mmChartsLoaded = true;
            cb();
            return;
        }
        if (__mmChartsLoaded) {
            cb();
            return;
        }
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        s.onload = function() {
            __mmChartsLoaded = true;
            cb();
        };
        document.head.appendChild(s);
    }

    function startResourceCharts() {
        var cpuCtx = document.getElementById('cpuChart');
        var memCtx = document.getElementById('memChart');
        if (!cpuCtx || !memCtx) return;

        var labels = [];
        var cpuData = [];
        var memData = [];

        var cpuChart = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CPU %',
                    data: cpuData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.15)',
                    tension: 0.25,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });

        var memChart = new Chart(memCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Memória %',
                    data: memData,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.15)',
                    tension: 0.25,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });

        state.charts.cpu = cpuChart;
        state.charts.mem = memChart;

        function pushPoint(ts, cpu, mem) {
            var t = new Date(ts);
            var hh = String(t.getHours()).padStart(2, '0');
            var mm = String(t.getMinutes()).padStart(2, '0');
            var ss = String(t.getSeconds()).padStart(2, '0');
            labels.push(hh + ':' + mm + ':' + ss);
            cpuData.push(cpu);
            memData.push(mem);
            if (labels.length > 60) {
                labels.shift();
                cpuData.shift();
                memData.shift();
            }
            cpuChart.update('none');
            memChart.update('none');
        }

        function updateServerClock(ts) {
            var el = document.getElementById('serverClock');
            if (!el) return;
            var t = new Date(ts);
            var hh = String(t.getHours()).padStart(2, '0');
            var mm = String(t.getMinutes()).padStart(2, '0');
            var ss = String(t.getSeconds()).padStart(2, '0');
            el.textContent = 'Servidor — ' + hh + ':' + mm + ':' + ss;
        }

        async function fetchMetrics() {
            try {
                if (!state.urls.metrics) return;
                var resp = await fetch(state.urls.metrics);
                var json = await resp.json();
                if (!json || !json.ok || json.cpu == null || json.mem == null) return;
                pushPoint(json.ts, json.cpu, json.mem);
                updateServerClock(json.ts);
            } catch(e) {
                console.error('Erro ao buscar métricas:', e);
            }
        }

        fetchMetrics();
        state.intervals.metrics = setInterval(fetchMetrics, 10000);

        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                if (state.intervals.metrics) {
                    clearInterval(state.intervals.metrics);
                    state.intervals.metrics = null;
                }
            } else {
                if (!state.intervals.metrics) {
                    fetchMetrics();
                    state.intervals.metrics = setInterval(fetchMetrics, 10000);
                }
            }
        });
    }

    function resizeDbFrame() {
        var f = document.getElementById('dbStatusFrame');
        if (!f) return;
        try {
            var doc = f.contentWindow && f.contentWindow.document;
            if (!doc) return;
            var h1 = doc.documentElement ? doc.documentElement.scrollHeight : 0;
            var h2 = doc.body ? doc.body.scrollHeight : 0;
            var h = Math.max(h1, h2);
            if (h && h > 0) {
                f.style.height = (h + 16) + 'px';
            }
        } catch (e) {
            // ignore
        }
    }

    function reloadDiag() {
        var f = document.getElementById('dbStatusFrame');
        if (!f) return;
        var base = f.src.split('?')[0];
        f.src = base + '?t=' + Date.now();
    }

    // Health Checks
    function getStatusIcon(status) {
        if (status === 'ok') return '<i class="bi bi-check-circle-fill" style="color: #10b981;"></i>';
        if (status === 'warning') return '<i class="bi bi-exclamation-triangle-fill" style="color: #f59e0b;"></i>';
        return '<i class="bi bi-x-circle-fill" style="color: #ef4444;"></i>';
    }

    function getStatusBadgeClass(status) {
        if (status === 'ok') return 'db-badge-success';
        if (status === 'warning') return 'db-badge-warning';
        return 'db-badge-danger';
    }

    function formatTimestamp(isoString) {
        if (!isoString) return '-';
        var d = new Date(isoString);
        return d.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    function getServiceName(service) {
        var names = {
            'database': 'Banco de Dados',
            'backend': 'Backend',
            'nginx': 'Nginx',
            'port': 'Porta 5000 (Backend)',
            'cpu': 'CPU',
            'memory': 'Memória',
            'disk': 'Disco'
        };
        return names[service] || service;
    }

    async function refreshHealthChecks() {
        try {
            if (!state.urls.health) return;
            var resp = await fetch(state.urls.health);
            var json = await resp.json();
            if (!json || !json.ok || !json.health) return;

            var grid = document.getElementById('healthChecksGrid');
            if (!grid) return;

            // Criar elementos DOM de forma segura ao invés de innerHTML
            grid.innerHTML = ''; // Limpar primeiro

            var services = ['database', 'backend', 'nginx', 'port', 'cpu', 'memory', 'disk'];

            services.forEach(function(service) {
                var health = json.health[service];
                if (!health) return;

                var item = createElement('div', { className: 'db-health-item' });
                var header = createElement('div', { className: 'db-health-header' });
                var icon = createElement('div', { className: 'db-health-icon', innerHTML: getStatusIcon(health.status) });
                var title = createElement('div', { className: 'db-health-title' }, getServiceName(service));
                var badge = createElement('span', {
                    className: 'db-badge-modern ' + getStatusBadgeClass(health.status)
                }, health.status.toUpperCase());

                header.appendChild(icon);
                header.appendChild(title);
                header.appendChild(badge);

                var message = createElement('div', { className: 'db-health-message' }, health.message || '-');
                item.appendChild(header);
                item.appendChild(message);

                if (health.response_time_ms !== undefined && health.response_time_ms !== null) {
                    var detail1 = createElement('div', { className: 'db-health-detail' },
                        'Tempo de resposta: ' + health.response_time_ms.toFixed(2) + 'ms');
                    item.appendChild(detail1);
                }


                if (health.usage_percent !== undefined && health.usage_percent !== null) {
                    var detail3 = createElement('div', { className: 'db-health-detail' },
                        'Uso: ' + health.usage_percent + '%');
                    item.appendChild(detail3);
                }

                if (health.available_gb !== undefined && health.available_gb !== null) {
                    var detail4 = createElement('div', { className: 'db-health-detail' },
                        'Disponível: ' + health.available_gb + ' GB');
                    item.appendChild(detail4);
                }

                var time = createElement('div', { className: 'db-health-time' },
                    'Verificado: ' + formatTimestamp(health.checked_at));
                item.appendChild(time);

                grid.appendChild(item);
            });

            var lastCheck = document.getElementById('lastHealthCheck');
            if (lastCheck) {
                lastCheck.textContent = formatTimestamp(new Date().toISOString());
            }
        } catch(e) {
            console.error('Erro ao atualizar health checks:', e);
        }
    }

    // Logs em Tempo Real
    async function updateLogs() {
        if (state.logsPaused) return;

        try {
            var type = document.getElementById('logTypeFilter')?.value || 'all';
            var level = document.getElementById('logLevelFilter')?.value || 'all';

            if (!state.urls.logs) return;
            var url = state.urls.logs + '?type=' + encodeURIComponent(type) + '&level=' + encodeURIComponent(level) + '&limit=100';

            var resp = await fetch(url);
            var json = await resp.json();
            if (!json || !json.ok || !json.logs) return;

            var container = document.getElementById('logsContainer');
            if (!container) return;

            // Criar elementos DOM de forma segura
            container.innerHTML = '';

            json.logs.forEach(function(log) {
                var levelClass = 'db-log-info';
                if (log.level === 'ERROR') levelClass = 'db-log-error';
                else if (log.level === 'WARNING') levelClass = 'db-log-warning';

                var entry = createElement('div', { className: 'db-log-entry ' + levelClass });
                var time = createElement('div', { className: 'db-log-time' }, formatTimestamp(log.timestamp));
                var levelEl = createElement('div', { className: 'db-log-level' }, log.level);
                var origin = createElement('div', { className: 'db-log-origin' }, log.origin || '-');
                var message = createElement('div', { className: 'db-log-message' }, log.message || '-');

                entry.appendChild(time);
                entry.appendChild(levelEl);
                entry.appendChild(origin);
                entry.appendChild(message);
                container.appendChild(entry);
            });

            if (!state.logsPaused) {
                container.scrollTop = container.scrollHeight;
            }
        } catch(e) {
            console.error('Erro ao atualizar logs:', e);
        }
    }

    function toggleLogsPause() {
        state.logsPaused = !state.logsPaused;
        var btn = document.getElementById('pauseLogsBtn');
        if (btn) {
            if (state.logsPaused) {
                btn.innerHTML = '<i class="bi bi-play-fill"></i> Continuar';
                btn.classList.remove('db-btn-outline');
                btn.classList.add('db-btn-primary');
            } else {
                btn.innerHTML = '<i class="bi bi-pause-fill"></i> Pausar';
                btn.classList.remove('db-btn-primary');
                btn.classList.add('db-btn-outline');
                updateLogs();
            }
        }
    }

    function clearLogs() {
        var container = document.getElementById('logsContainer');
        if (container) {
            var loading = createElement('div', { className: 'db-logs-loading' }, 'Logs limpos');
            container.innerHTML = '';
            container.appendChild(loading);
        }
    }

    // Tendências
    var trendsChart = null;
    async function updateTrends() {
        try {
            var metricType = document.getElementById('trendMetricType')?.value || 'cpu';
            var hours = parseInt(document.getElementById('trendHours')?.value || 24);

            if (!state.urls.metrics_trends) return;
            var url = state.urls.metrics_trends + '?type=' + encodeURIComponent(metricType) + '&hours=' + hours;

            var resp = await fetch(url);
            var json = await resp.json();
            if (!json || !json.ok || !json.trends) return;

            var trends = json.trends;
            var statsEl = document.getElementById('trendsStats');
            if (statsEl) {
                statsEl.innerHTML = '';
                var stats = [
                    { label: 'Média:', value: trends.average },
                    { label: 'Mín:', value: trends.min },
                    { label: 'Máx:', value: trends.max },
                    { label: 'Tendência:', value: trends.trend === 'increasing' ? '↑ Crescendo' : trends.trend === 'decreasing' ? '↓ Diminuindo' : '→ Estável' }
                ];
                stats.forEach(function(stat) {
                    var item = createElement('div', { className: 'db-trend-stats-item' });
                    var strong = createElement('strong', {}, stat.label + ' ');
                    item.appendChild(strong);
                    item.appendChild(document.createTextNode(stat.value));
                    statsEl.appendChild(item);
                });
            }

            var ctx = document.getElementById('trendsChart');
            if (!ctx) return;

            ensureChartJs(function() {
                if (trendsChart) {
                    trendsChart.destroy();
                }
                trendsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: trends.timestamps.map(function(ts) {
                            var d = new Date(ts);
                            return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                        }),
                        datasets: [{
                            label: metricType.toUpperCase(),
                            data: trends.values,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                            x: { grid: { display: false } }
                        }
                    }
                });
                state.charts.trends = trendsChart;
            });
        } catch(e) {
            console.error('Erro ao atualizar tendências:', e);
        }
    }

    // Queries lentas
    async function updateSlowQueries() {
        try {
            if (!state.urls.slow_queries) return;
            var resp = await fetch(state.urls.slow_queries);
            var json = await resp.json();
            if (!json || !json.ok || !json.queries) return;

            var tbody = document.getElementById('slowQueriesTableBody');
            if (!tbody) return;

            tbody.innerHTML = '';

            if (json.queries.length === 0) {
                var row = createElement('tr');
                var cell = createElement('td', { colSpan: '4', className: 'text-center' }, 'Nenhuma query lenta encontrada');
                row.appendChild(cell);
                tbody.appendChild(row);
            } else {
                json.queries.forEach(function(q) {
                    var row = createElement('tr', { className: 'db-table-row' });
                    var dateCell = createElement('td', { className: 'db-table-date' }, formatTimestamp(q.timestamp));
                    var timeCell = createElement('td');
                    var badge = createElement('span', { className: 'db-badge-modern db-badge-warning' }, q.execution_time_ms.toFixed(2) + ' ms');
                    timeCell.appendChild(badge);
                    var endpointCell = createElement('td');
                    var code1 = createElement('code', { className: 'db-code-modern' }, q.endpoint || '-');
                    endpointCell.appendChild(code1);
                    var queryCell = createElement('td');
                    var code2 = createElement('code', { className: 'db-code-modern', style: 'font-size: 0.75rem;' }, q.query);
                    queryCell.appendChild(code2);

                    row.appendChild(dateCell);
                    row.appendChild(timeCell);
                    row.appendChild(endpointCell);
                    row.appendChild(queryCell);
                    tbody.appendChild(row);
                });
            }
        } catch(e) {
            console.error('Erro ao atualizar queries:', e);
        }
    }

    // Manutenção
    var maintenanceStats = null;
    var maintenanceRecommendations = [];

    async function loadMaintenanceStats() {
        try {
            if (!state.urls.maintenance_stats) return;
            var resp = await fetch(state.urls.maintenance_stats);
            var json = await resp.json();
            if (json && json.ok) {
                maintenanceStats = json;
                updateMaintenanceDisplay();
            }
        } catch(e) {
            console.error('Erro ao carregar estatísticas:', e);
        }
    }

    async function loadMaintenanceRecommendations() {
        try {
            if (!state.urls.maintenance_recommendations) return;
            var resp = await fetch(state.urls.maintenance_recommendations);
            var json = await resp.json();
            if (json && json.ok) {
                maintenanceRecommendations = json.recommendations || [];
                updateRecommendationsDisplay();
            }
        } catch(e) {
            console.error('Erro ao carregar recomendações:', e);
        }
    }

    function updateMaintenanceDisplay() {
        if (!maintenanceStats) return;

        var statsEl = document.getElementById('maintenanceQuickStats');
        if (statsEl && maintenanceStats.database) {
            var db = maintenanceStats.database;
            var logs = maintenanceStats.logs;
            var backups = maintenanceStats.backups;

            statsEl.innerHTML = '';
            var container = createElement('div', { className: 'db-maintenance-quick-stats' });

            var stat1 = createElement('div', { className: 'db-quick-stat-item' });
            var label1 = createElement('span', { className: 'db-quick-stat-label' }, 'Banco:');
            var value1 = createElement('span', { className: 'db-quick-stat-value' }, (db.size_mb || 0).toFixed(2) + ' MB');
            stat1.appendChild(label1);
            stat1.appendChild(value1);

            var stat2 = createElement('div', { className: 'db-quick-stat-item' });
            var label2 = createElement('span', { className: 'db-quick-stat-label' }, 'Logs:');
            var value2 = createElement('span', { className: 'db-quick-stat-value' }, (logs.total_estimated_size_mb || 0).toFixed(2) + ' MB');
            stat2.appendChild(label2);
            stat2.appendChild(value2);

            var stat3 = createElement('div', { className: 'db-quick-stat-item' });
            var label3 = createElement('span', { className: 'db-quick-stat-label' }, 'Backups:');
            var value3 = createElement('span', { className: 'db-quick-stat-value' }, (backups.count || 0).toString());
            stat3.appendChild(label3);
            stat3.appendChild(value3);

            container.appendChild(stat1);
            container.appendChild(stat2);
            container.appendChild(stat3);
            statsEl.appendChild(container);
        }
    }

    function updateRecommendationsDisplay() {
        var recEl = document.getElementById('maintenanceRecommendations');
        if (!recEl) return;

        recEl.innerHTML = '';

        if (maintenanceRecommendations.length === 0) {
            var empty = createElement('div', { className: 'db-no-recommendations' }, 'Nenhuma recomendação no momento.');
            recEl.appendChild(empty);
            return;
        }

        var list = createElement('div', { className: 'db-recommendations-list' });
        maintenanceRecommendations.forEach(function(rec) {
            var priorityClass = 'db-rec-' + rec.priority;
            var priorityIcon = rec.priority === 'high' ? 'bi-exclamation-triangle-fill' :
                               rec.priority === 'medium' ? 'bi-info-circle-fill' : 'bi-lightbulb-fill';

            var item = createElement('div', { className: 'db-recommendation-item ' + priorityClass });
            var icon = createElement('i', { className: 'bi ' + priorityIcon });
            var span = createElement('span', {}, rec.message);
            item.appendChild(icon);
            item.appendChild(span);
            list.appendChild(item);
        });
        recEl.appendChild(list);
    }

    async function loadMaintenanceHistory() {
        try {
            var type = document.getElementById('maintenanceHistoryType')?.value || 'all';
            var status = document.getElementById('maintenanceHistoryStatus')?.value || 'all';

            if (!state.urls.maintenance_history) return;
            var url = state.urls.maintenance_history + '?type=' + encodeURIComponent(type) + '&status=' + encodeURIComponent(status) + '&limit=20';

            var resp = await fetch(url);
            var json = await resp.json();
            if (!json || !json.ok || !json.history) return;

            var tbody = document.getElementById('maintenanceHistoryBody');
            if (!tbody) return;

            tbody.innerHTML = '';

            if (json.history.length === 0) {
                var row = createElement('tr');
                var cell = createElement('td', { colSpan: '6', className: 'text-center' }, 'Nenhuma manutenção encontrada');
                row.appendChild(cell);
                tbody.appendChild(row);
            } else {
                json.history.forEach(function(m) {
                    var date = m.created_at ? new Date(m.created_at).toLocaleString('pt-BR') : '-';
                    var duration = m.duration_seconds ? m.duration_seconds.toFixed(2) + 's' : '-';
                    var items = m.items_processed !== null ? m.items_processed.toString() : '-';
                    var statusBadge = m.status === 'completed' ? 'db-badge-success' :
                                     m.status === 'failed' ? 'db-badge-danger' : 'db-badge-warning';
                    var typeLabel = m.maintenance_type === 'cleanup_logs' ? 'Limpeza' :
                                   m.maintenance_type === 'optimize_database' ? 'Otimização' :
                                   m.maintenance_type === 'cleanup_backups' ? 'Limpeza Backups' :
                                   m.maintenance_type === 'verify_backups' ? 'Verificação' : m.maintenance_type;

                    var row = createElement('tr', { className: 'db-table-row' });
                    var dateCell = createElement('td', { className: 'db-table-date' }, date);
                    var typeCell = createElement('td', {}, typeLabel);
                    var statusCell = createElement('td');
                    var badge = createElement('span', { className: 'db-badge-modern ' + statusBadge }, m.status);
                    statusCell.appendChild(badge);
                    var durationCell = createElement('td', {}, duration);
                    var itemsCell = createElement('td', {}, items);
                    var executedCell = createElement('td', {}, m.executed_by || '-');

                    row.appendChild(dateCell);
                    row.appendChild(typeCell);
                    row.appendChild(statusCell);
                    row.appendChild(durationCell);
                    row.appendChild(itemsCell);
                    row.appendChild(executedCell);
                    tbody.appendChild(row);
                });
            }
        } catch(e) {
            console.error('Erro ao carregar histórico:', e);
            var tbody = document.getElementById('maintenanceHistoryBody');
            if (tbody) {
                tbody.innerHTML = '';
                var row = createElement('tr');
                var cell = createElement('td', { colSpan: '6', className: 'text-center' }, 'Erro ao carregar histórico');
                row.appendChild(cell);
                tbody.appendChild(row);
            }
        }
    }

    async function runMaintenanceCleanup() {
        if (!confirm('Executar limpeza de logs antigos?')) return;
        try {
            if (!state.urls.maintenance_cleanup) return;
            var resp = await fetch(state.urls.maintenance_cleanup, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            var json = await resp.json();
            if (json && json.ok) {
                var result = json.result;
                var msg = 'Limpeza concluída!\n';
                msg += 'Itens removidos: ' + result.deleted + '\n';
                msg += 'Duração: ' + result.duration.toFixed(2) + 's\n';
                if (result.space_freed_mb !== undefined) {
                    msg += 'Espaço liberado: ' + result.space_freed_mb + ' MB\n';
                    if (result.size_before_mb !== undefined && result.size_after_mb !== undefined) {
                        msg += 'Antes: ' + result.size_before_mb.toFixed(2) + ' MB\n';
                        msg += 'Depois: ' + result.size_after_mb.toFixed(2) + ' MB';
                    }
                }
                alert(msg);
                loadMaintenanceStats();
                loadMaintenanceHistory();
                updateSlowQueries();
            } else {
                alert('Erro: ' + (json.error || 'Erro desconhecido'));
            }
        } catch(e) {
            alert('Erro ao executar limpeza: ' + e.message);
        }
    }

    async function runMaintenanceOptimize() {
        if (!confirm('Otimizar banco de dados? Isso pode levar alguns segundos.')) return;
        try {
            if (!state.urls.maintenance_optimize) return;
            var resp = await fetch(state.urls.maintenance_optimize, { method: 'POST' });
            var json = await resp.json();
            if (json && json.ok) {
                var result = json.result;
                var msg = 'Otimização concluída!\n';
                msg += 'Duração: ' + result.duration.toFixed(2) + 's\n';
                if (result.space_freed_mb !== undefined) {
                    msg += 'Espaço liberado: ' + result.space_freed_mb + ' MB\n';
                    if (result.size_before_mb !== undefined && result.size_after_mb !== undefined) {
                        msg += 'Antes: ' + result.size_before_mb.toFixed(2) + ' MB\n';
                        msg += 'Depois: ' + result.size_after_mb.toFixed(2) + ' MB';
                    }
                }
                alert(msg);
                loadMaintenanceStats();
                loadMaintenanceHistory();
            } else {
                alert('Erro: ' + (json.error || 'Erro desconhecido'));
            }
        } catch(e) {
            alert('Erro ao otimizar: ' + e.message);
        }
    }

    async function verifyAllBackups() {
        if (!confirm('Verificar integridade de todos os backups?')) return;
        try {
            if (!state.urls.verify_backups) return;
            var resp = await fetch(state.urls.verify_backups, { method: 'POST' });
            var json = await resp.json();
            if (json && json.ok) {
                var msg = 'Verificação concluída:\n';
                json.results.forEach(function(r) {
                    msg += r.filename + ': ' + r.status + '\n';
                });
                alert(msg);
                loadMaintenanceStats();
                loadMaintenanceRecommendations();
            } else {
                alert('Erro: ' + (json.error || 'Erro desconhecido'));
            }
        } catch(e) {
            alert('Erro ao verificar backups: ' + e.message);
        }
    }

    async function runMaintenanceAll() {
        if (!confirm('Executar todas as manutenções? Isso pode levar alguns minutos.')) return;
        try {
            if (!state.urls.maintenance_run_all) return;
            var resp = await fetch(state.urls.maintenance_run_all, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cleanup: true, optimize: true, verify: true})
            });
            var json = await resp.json();
            if (json && json.ok) {
                var msg = 'Manutenções executadas com sucesso!\n\n';
                if (json.results.cleanup) {
                    msg += 'Limpeza: ' + json.results.cleanup.deleted + ' itens removidos\n';
                }
                if (json.results.optimize) {
                    msg += 'Otimização: concluída\n';
                }
                if (json.results.verify) {
                    msg += 'Verificação: concluída\n';
                }
                alert(msg);
                loadMaintenanceStats();
                loadMaintenanceRecommendations();
                loadMaintenanceHistory();
            } else {
                alert('Erro: ' + (json.error || 'Erro desconhecido'));
            }
        } catch(e) {
            alert('Erro ao executar manutenções: ' + e.message);
        }
    }

    function exportMaintenanceReport() {
        if (!state.urls.maintenance_export_report) return;
        window.location.href = state.urls.maintenance_export_report;
    }

    // Git Update Monitoring
    function refreshGitStatus(force) {
        force = force || false;
        const btn = document.getElementById(force ? 'forceCheckBtn' : 'refreshGitBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (force ? 'Forçando...' : 'Atualizando...');
        }

        if (!state.urls.git_status) return;
        const url = state.urls.git_status + '?t=' + Date.now() + (force ? '&force=true' : '');

        fetch(url, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.ok) {
                updateGitStatusDisplay(data);
            } else {
                const errorMsg = data.error || 'Erro ao buscar status do Git';
                console.error('Erro na resposta:', errorMsg);
                showGitError(errorMsg);
            }
        })
        .catch(error => {
            console.error('Erro ao buscar status Git:', error);
            showGitError('Erro de conexão: ' + error.message);
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> ' + (force ? 'Forçar Checagem' : 'Atualizar');
            }
        });
    }

    function updateGitStatusDisplay(data) {
        const currentVersion = document.getElementById('currentVersion');
        const currentCommit = document.getElementById('currentCommit');
        const latestCommit = document.getElementById('latestCommit');
        const commitMessage = document.getElementById('commitMessage');

        if (currentVersion) currentVersion.textContent = data.current_version || 'N/A';
        if (currentCommit) currentCommit.textContent = data.current_commit || data.current_commit_hash || 'N/A';
        if (latestCommit) latestCommit.textContent = data.latest_commit || data.latest_commit_hash || data.remote_commit_hash || 'N/A';
        if (commitMessage) commitMessage.textContent = data.commit_message || data.remote_commit_msg || 'N/A';

        const indicator = document.getElementById('updateIndicator');
        const applyBtn = document.getElementById('applyUpdateBtn');

        if (indicator) {
            if (data.update_available) {
                indicator.className = 'db-git-update-indicator update-available';
                indicator.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i><span><strong>Atualização disponível!</strong> Há uma nova versão no repositório remoto.</span>';
                if (applyBtn) applyBtn.disabled = false;
            } else {
                indicator.className = 'db-git-update-indicator up-to-date';
                indicator.innerHTML = '<i class="bi bi-check-circle-fill"></i><span>Sistema está atualizado. Você está na versão mais recente.</span>';
                if (applyBtn) applyBtn.disabled = true;
            }
        }
    }

    function showGitError(message) {
        const indicator = document.getElementById('updateIndicator');
        if (indicator) {
            indicator.className = 'db-git-update-indicator error';
            indicator.innerHTML = '<i class="bi bi-x-circle-fill"></i><span>' + escapeHtml(message) + '</span>';
        }

        const fields = ['currentVersion', 'currentCommit', 'latestCommit', 'commitMessage'];
        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.textContent = 'Erro ao carregar';
                field.style.color = '#dc2626';
            }
        });

        const applyBtn = document.getElementById('applyUpdateBtn');
        if (applyBtn) {
            applyBtn.disabled = true;
        }
    }

    function fetchVersionInfo() {
        if (!state.urls.git_status) return;
        fetch(state.urls.git_status + '?force=false')
        .then(response => response.json())
        .then(data => {
            const currentVersionEl = document.getElementById('currentVersionInfo');
            const latestVersionEl = document.getElementById('latestVersionInfo');

            if (data.ok) {
                if (currentVersionEl) {
                    currentVersionEl.innerHTML = '<span style="color: #059669;">' + escapeHtml(data.current_version || 'N/A') + '</span>';
                }
                if (latestVersionEl) {
                    const latestVersion = data.latest_version || 'N/A';
                    latestVersionEl.innerHTML = '<span style="color: #3b82f6;">' + escapeHtml(latestVersion) + '</span>';
                }
            } else {
                if (currentVersionEl) {
                    currentVersionEl.innerHTML = '<span style="color: #dc2626;">Erro ao verificar</span>';
                }
                if (latestVersionEl) {
                    latestVersionEl.innerHTML = '<span style="color: #dc2626;">Erro ao verificar</span>';
                }
            }
        })
        .catch(error => {
            const currentVersionEl = document.getElementById('currentVersionInfo');
            const latestVersionEl = document.getElementById('latestVersionInfo');

            if (currentVersionEl) {
                currentVersionEl.innerHTML = '<span style="color: #dc2626;">Erro de conexão</span>';
            }
            if (latestVersionEl) {
                latestVersionEl.innerHTML = '<span style="color: #dc2626;">Erro de conexão</span>';
            }
        });
    }

    function showUpdateConfirmation(force) {
        force = force || false;
        const overlay = createElement('div', { className: 'db-git-modal-overlay', id: 'updateModalOverlay' });
        const modal = createElement('div', { className: 'db-git-modal' });

        // Criar estrutura do modal usando createElement (simplificado para evitar innerHTML perigoso)
        // Nota: Para modais complexos com muito HTML dinâmico, usar template strings é aceitável
        // desde que os dados sejam escapados adequadamente
        modal.innerHTML = `
            <div class="db-git-modal-header">
                <i class="bi bi-exclamation-triangle-fill" style="color: #f59e0b; font-size: 2rem;"></i>
                <h3 class="db-git-modal-title">Confirmar Atualização do Sistema</h3>
            </div>
            <div class="db-git-modal-body">
                <div class="db-git-modal-message">
                    <p style="font-size: 1.1rem; margin-bottom: 1rem;"><strong>${force ? 'O sistema aplicará a atualização forçada (reinstalação).' : 'O sistema aplicará a atualização completa.'}</strong></p>
                    ${force ? '<p style="margin-bottom: 0.75rem; color: #f59e0b; font-weight: 600;">⚠️ Esta é uma reinstalação forçada. O sistema será atualizado mesmo se já estiver na versão mais recente.</p>' : ''}
                    <div id="versionInfoContainer" style="margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #e5e7eb;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;">
                            <i class="bi bi-info-circle" style="color: #3b82f6; font-size: 1.25rem;"></i>
                            <strong style="color: #1f2937; font-size: 1rem;">Informações de Versão</strong>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                            <div>
                                <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Versão Instalada:</div>
                                <div id="currentVersionInfo" style="font-size: 1.125rem; font-weight: 600; color: #1f2937;">
                                    <i class="bi bi-hourglass-split" style="animation: spin 1s linear infinite;"></i>
                                    Verificando...
                                </div>
                            </div>
                            <div>
                                <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Versão Mais Recente (GitHub):</div>
                                <div id="latestVersionInfo" style="font-size: 1.125rem; font-weight: 600; color: #1f2937;">
                                    <i class="bi bi-hourglass-split" style="animation: spin 1s linear infinite;"></i>
                                    Verificando...
                                </div>
                            </div>
                        </div>
                    </div>
                    <p style="margin-bottom: 0.75rem;">Esta operação inclui:</p>
                    <ul style="margin-left: 1.5rem; margin-bottom: 1rem; color: #4b5563;">
                        <li>Atualização do código do GitHub${force ? ' (forçado)' : ''}</li>
                        <li>Rebuild completo do container Docker (sem cache)</li>
                        <li>Reinicialização do sistema</li>
                    </ul>
                    <p style="margin-bottom: 1.5rem; color: #dc2626; font-weight: 600;">
                        ⚠️ A página ficará temporariamente indisponível. Aguarde até 5 minutos e depois atualize a página.
                    </p>
                </div>
                <div class="db-git-countdown-container">
                    <div class="db-git-countdown">
                        <div class="db-git-countdown-value" id="countdownValue" style="font-size: 3rem; font-weight: 700; color: #dc2626;">10</div>
                        <div class="db-git-countdown-label">segundos</div>
                    </div>
                </div>
            </div>
            <div class="db-git-modal-actions">
                <button type="button" class="db-git-modal-btn db-git-modal-btn-cancel" data-action="close">Cancelar</button>
                <button type="button" class="db-git-modal-btn db-git-modal-btn-confirm" id="confirmUpdateBtn" data-action="confirm" data-force="${force}" disabled>
                    <i class="bi bi-cloud-arrow-down"></i>
                    ${force ? 'Reinstalar Atualização' : 'Aplicar Atualização'}
                </button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Event listeners para botões do modal
        overlay.querySelector('[data-action="close"]').addEventListener('click', closeUpdateModal);
        overlay.querySelector('[data-action="confirm"]').addEventListener('click', function() {
            const forceValue = this.getAttribute('data-force') === 'true';
            applyUpdate(forceValue);
        });

        fetchVersionInfo();

        state.updateCountdown = 10;
        const countdownValue = document.getElementById('countdownValue');
        const confirmBtn = document.getElementById('confirmUpdateBtn');

        state.updateCountdownInterval = setInterval(() => {
            state.updateCountdown--;
            if (countdownValue) {
                countdownValue.textContent = state.updateCountdown;
                if (state.updateCountdown <= 3) {
                    countdownValue.style.color = '#dc2626';
                    countdownValue.style.animation = 'pulse 0.5s infinite';
                }
            }

            if (state.updateCountdown <= 0) {
                clearInterval(state.updateCountdownInterval);
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.style.opacity = '1';
                    confirmBtn.style.cursor = 'pointer';
                }
                setTimeout(() => {
                    if (document.getElementById('updateModalOverlay')) {
                        closeUpdateModal();
                    }
                }, 10000);
            }
        }, 1000);
    }

    function closeUpdateModal() {
        const overlay = document.getElementById('updateModalOverlay');
        if (overlay) {
            overlay.remove();
        }
        if (state.updateCountdownInterval) {
            clearInterval(state.updateCountdownInterval);
        }
        state.updateCountdown = 10;
    }

    function applyUpdate(force) {
        force = force || false;
        const confirmBtn = document.getElementById('confirmUpdateBtn');
        const countdownValue = document.getElementById('countdownValue');

        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Aplicando...';
        }

        if (countdownValue) {
            countdownValue.textContent = '0';
            countdownValue.style.color = '#16a34a';
        }

        if (!state.urls.git_update) return;

        fetch(state.urls.git_update, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ force: force })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    if (err.already_up_to_date) {
                        throw new Error(err.error || 'Sistema já está atualizado');
                    }
                    let errorMsg = err.error || `HTTP ${response.status}`;
                    if (err.suggestion) {
                        errorMsg += '\n\n💡 Sugestão: ' + err.suggestion;
                    }
                    if (err.details) {
                        errorMsg += '\n\nDetalhes: ' + err.details.substring(0, 300);
                    }
                    const errorObj = new Error(errorMsg);
                    errorObj.errorData = err;
                    throw errorObj;
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.ok) {
                const modalBody = document.querySelector('.db-git-modal-body');
                if (modalBody) {
                    const processingMsg = document.getElementById('processingMsg');
                    if (processingMsg) {
                        processingMsg.className = 'db-git-success-msg';
                        processingMsg.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <i class="bi bi-check-circle-fill"></i>
                                <div>
                                    <strong>Atualização completa aplicada com sucesso!</strong>
                                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">O sistema será reiniciado. Aguarde até 5 minutos.</p>
                                </div>
                            </div>
                        `;
                    }
                }
                setTimeout(() => {
                    closeUpdateModal();
                }, 3000);
            } else {
                alert('Erro: ' + (data.error || 'Erro desconhecido'));
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="bi bi-cloud-arrow-down"></i> Aplicar Atualização';
                }
            }
        })
        .catch(error => {
            console.error('Erro ao aplicar atualização:', error);
            alert('Erro: ' + error.message);
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="bi bi-cloud-arrow-down"></i> ' + (force ? 'Reinstalar Atualização' : 'Aplicar Atualização');
            }
        });
    }

    function downloadErrorText(blobUrl, filename) {
        try {
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(blobUrl);
            }, 100);
        } catch (err) {
            console.error('Erro ao fazer download do arquivo:', err);
            alert('Erro ao fazer download do arquivo. Por favor, copie a mensagem manualmente.');
        }
    }

    // Expor funções globalmente
    window.dbAdmin = {
        refreshHealthChecks: refreshHealthChecks,
        updateLogs: updateLogs,
        toggleLogsPause: toggleLogsPause,
        clearLogs: clearLogs,
        updateTrends: updateTrends,
        updateSlowQueries: updateSlowQueries,
        loadMaintenanceStats: loadMaintenanceStats,
        loadMaintenanceRecommendations: loadMaintenanceRecommendations,
        loadMaintenanceHistory: loadMaintenanceHistory,
        runMaintenanceCleanup: runMaintenanceCleanup,
        runMaintenanceOptimize: runMaintenanceOptimize,
        verifyAllBackups: verifyAllBackups,
        runMaintenanceAll: runMaintenanceAll,
        exportMaintenanceReport: exportMaintenanceReport,
        refreshGitStatus: refreshGitStatus,
        showUpdateConfirmation: showUpdateConfirmation,
        closeUpdateModal: closeUpdateModal,
        applyUpdate: applyUpdate,
        resizeDbFrame: resizeDbFrame,
        reloadDiag: reloadDiag
    };

    // Inicialização quando DOM estiver pronto
    document.addEventListener('DOMContentLoaded', function() {
        initialize();

        var f = document.getElementById('dbStatusFrame');
        if (f) {
            f.addEventListener('load', resizeDbFrame);
        }
        ensureChartJs(startResourceCharts);

        refreshHealthChecks();
        state.intervals.healthCheck = setInterval(refreshHealthChecks, 30000);

        updateLogs();
        state.intervals.logs = setInterval(updateLogs, 10000);

        updateTrends();
        updateSlowQueries();

        if (document.getElementById('gitUpdateCard')) {
            refreshGitStatus();
            state.gitStatusInterval = setInterval(refreshGitStatus, 60000);
        }
    });

    // Limpar intervalos ao sair da página
    window.addEventListener('beforeunload', function() {
        if (state.gitStatusInterval) {
            clearInterval(state.gitStatusInterval);
        }
        if (state.updateCountdownInterval) {
            clearInterval(state.updateCountdownInterval);
        }
        if (state.intervals.healthCheck) {
            clearInterval(state.intervals.healthCheck);
        }
        if (state.intervals.logs) {
            clearInterval(state.intervals.logs);
        }
        if (state.intervals.metrics) {
            clearInterval(state.intervals.metrics);
        }
    });

})();
