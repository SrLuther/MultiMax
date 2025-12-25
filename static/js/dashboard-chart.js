/**
 * Dashboard Chart Module
 * Responsável por renderizar o gráfico de movimentações do dashboard
 */

(function() {
    'use strict';

    /**
     * Inicializa o gráfico de movimentações
     * @param {Object} chartData - Dados do gráfico
     */
    function initMovimentacoesChart(chartData) {
        const canvas = document.getElementById('chartMovimentacoes');
        if (!canvas || !chartData) return;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        
        // eslint-disable-next-line no-undef
        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: 'Entradas',
                        data: chartData.entradas,
                        backgroundColor: 'rgba(0, 255, 136, 0.7)',
                        borderColor: 'rgba(0, 255, 136, 1)',
                        borderWidth: 2,
                        borderRadius: 6
                    },
                    {
                        label: 'Saídas',
                        data: chartData.saidas,
                        backgroundColor: 'rgba(239, 68, 68, 0.7)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 2,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: isDark ? '#cbd5e1' : '#475569',
                            font: { family: 'Inter', weight: '500' }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' },
                        ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                    }
                }
            }
        });
    }

    /**
     * Carrega dados do gráfico via data attribute
     */
    function loadChartData() {
        const chartElement = document.getElementById('chartMovimentacoes');
        if (!chartElement) return;

        try {
            // Pega dados do atributo data-chart
            const chartData = JSON.parse(chartElement.getAttribute('data-chart') || '{}');
            if (chartData && Object.keys(chartData).length > 0) {
                initMovimentacoesChart(chartData);
            }
        } catch (error) {
            console.error('Erro ao carregar dados do gráfico:', error);
        }
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadChartData);
    } else {
        loadChartData();
    }

})();