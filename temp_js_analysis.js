
// Variáveis globais
let currentCollaboratorId = null;
let currentCollaboratorName = null;
let currentPage = 1;
let currentCicloId = null;
const canEdit = {% if can_edit %}true{% else %}false{% endif %};

// Função para validar horas (múltiplos de 0.5)
// NÃO aceita vírgula - bloqueia completamente
function validarHoras(valor, origem) {
    if (!valor || !valor.trim()) {
        return { valido: false, erro: 'Campo obrigatório' };
    }
    
    valor = valor.trim();
    
    // BLOQUEAR vírgula completamente (NÃO converter)
    if (valor.includes(',')) {
        return { 
            valido: false, 
            erro: 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.' 
        };
    }
    
    // Bloquear formato 2:30
    if (valor.includes(':')) {
        return { 
            valido: false, 
            erro: 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.' 
        };
    }
    
    try {
        const num = parseFloat(valor);
        if (isNaN(num)) {
            return { 
                valido: false, 
                erro: 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.' 
            };
        }
        
        // Validar Folga utilizada: deve ser exatamente -8h (apenas se origem fornecida)
        if (origem && origem === 'Folga utilizada') {
            if (num !== -8.0) {
                return { valido: false, erro: 'Folga utilizada deve ser exatamente -8 horas.' };
            }
        } else if (origem !== undefined) {
            // Para outras origens (quando origem fornecida), não permitir negativo
            if (num < 0) {
                return { valido: false, erro: 'Valor não pode ser negativo' };
            }
        }
        // Se origem for undefined (ajustes), permitir negativo (será validado no backend)
        
        // Verificar se é múltiplo de 0.5
        const resto = Math.abs(num) % 0.5;
        if (resto > 0.001 && resto < 0.499) {
            return { 
                valido: false, 
                erro: 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.' 
            };
        }
        
        return { valido: true, valor: num };
    } catch (e) {
        return { 
            valido: false, 
            erro: 'Formato inválido. Use apenas números inteiros ou decimais com ponto (ex.: 1 ou 1.5). Apenas múltiplos de 0.5 são permitidos.' 
        };
    }
}

// Abrir modal de lançamento
function abrirLancamento(collaboratorId, collaboratorName) {
    try {
        currentCollaboratorId = collaboratorId;
        currentCollaboratorName = collaboratorName;
        
        const modalElement = document.getElementById('modalLancamento');
        if (!modalElement) {
            console.error('Modal de lançamento não encontrado');
            alert('Erro: Modal de lançamento não encontrado. Verifique se você tem permissão de edição.');
            return;
        }
        
        document.getElementById('lancamento_collaborator_id').value = collaboratorId;
        document.getElementById('lancamento_colaborador_nome').value = collaboratorName;
        document.getElementById('lancamento_data').value = new Date().toISOString().split('T')[0];
        document.getElementById('lancamento_origem').value = '';
        document.getElementById('lancamento_descricao').value = '';
        document.getElementById('lancamento_descricao_group').style.display = 'none';
        document.getElementById('lancamento_horas').value = '';
        document.getElementById('lancamento_horas').classList.remove('is-invalid');
        document.getElementById('lancamento_horas_error').textContent = '';
        document.getElementById('btnSalvarLancamento').disabled = true;
        
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap não está carregado');
            alert('Erro: Bootstrap não está carregado. Recarregue a página.');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } catch (error) {
        console.error('Erro ao abrir modal de lançamento:', error);
        alert('Erro ao abrir modal de lançamento: ' + error.message);
    }
}

// Abrir modal de histórico
function abrirHistorico(collaboratorId, collaboratorName) {
    try {
        currentCollaboratorId = collaboratorId;
        currentCollaboratorName = collaboratorName;
        currentPage = 1;
        
        const modalElement = document.getElementById('modalHistorico');
        if (!modalElement) {
            console.error('Modal de histórico não encontrado');
            alert('Erro: Modal de histórico não encontrado.');
            return;
        }
        
        document.getElementById('historico_colaborador_nome').textContent = collaboratorName;
        document.getElementById('historico_loading').style.display = 'block';
        document.getElementById('historico_content').style.display = 'none';
        document.getElementById('historico_empty').style.display = 'none';
        document.getElementById('btnAjustarHistorico').style.display = 'none';
        document.getElementById('btnPDFIndividual').style.display = 'none';
        
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap não está carregado');
            alert('Erro: Bootstrap não está carregado. Recarregue a página.');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        carregarHistorico(collaboratorId, 1);
    } catch (error) {
        console.error('Erro ao abrir modal de histórico:', error);
        alert('Erro ao abrir modal de histórico: ' + error.message);
    }
}

// Abrir modal de ajuste
function abrirAjuste(cicloId, horasAtuais, descricaoAtual) {
    currentCicloId = cicloId;
    document.getElementById('ajustar_ciclo_id').value = cicloId;
    document.getElementById('ajustar_horas').value = horasAtuais;
    document.getElementById('ajustar_descricao').value = descricaoAtual || '';
    document.getElementById('ajustar_horas').classList.remove('is-invalid');
    document.getElementById('ajustar_horas_error').textContent = '';
    document.getElementById('btnSalvarAjuste').disabled = false;
    
    const modal = new bootstrap.Modal(document.getElementById('modalAjustar'));
    modal.show();
}

// Carregar histórico paginado
function carregarHistorico(collaboratorId, page) {
    fetch(`/ciclos/historico/${collaboratorId}?page=${page}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('historico_loading').style.display = 'none';
            
            if (!data.ok) {
                alert('Erro ao carregar histórico: ' + data.error);
                return;
            }
            
            if (data.registros.length === 0) {
                document.getElementById('historico_empty').style.display = 'block';
                return;
            }
            
            document.getElementById('historico_content').style.display = 'block';
            document.getElementById('btnAjustarHistorico').style.display = 'inline-block';
            document.getElementById('btnPDFIndividual').style.display = 'inline-block';
            
            // Preencher tabela
            const tbody = document.getElementById('historico_tbody');
            tbody.innerHTML = '';
            data.registros.forEach(reg => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = reg.data;
                row.insertCell(1).textContent = reg.origem;
                row.insertCell(2).textContent = reg.descricao;
                row.insertCell(3).textContent = reg.horas + 'h';
                if (canEdit) {
                    const cellAcoes = row.insertCell(4);
                    cellAcoes.style.textAlign = 'center';
                    
                    // Botão Ajustar
                    const btnAjustar = document.createElement('button');
                    btnAjustar.className = 'btn btn-sm btn-warning me-1';
                    btnAjustar.innerHTML = '<i class="bi bi-pencil"></i>';
                    btnAjustar.title = 'Ajustar';
                    btnAjustar.onclick = function() { abrirAjuste(reg.id, reg.horas, reg.descricao); };
                    cellAcoes.appendChild(btnAjustar);
                    
                    // Botão Excluir
                    const btnExcluir = document.createElement('button');
                    btnExcluir.className = 'btn btn-sm btn-danger';
                    btnExcluir.innerHTML = '<i class="bi bi-trash"></i>';
                    btnExcluir.title = 'Excluir';
                    btnExcluir.onclick = function() { excluirRegistro(reg.id, collaboratorId); };
                    cellAcoes.appendChild(btnExcluir);
                } else {
                    row.insertCell(4).textContent = '';
                }
            });
            
            // Preencher resumo
            document.getElementById('historico_total_horas').textContent = data.balance.total_horas.toFixed(1) + 'h';
            document.getElementById('historico_dias_fechados').textContent = data.balance.dias_completos;
            document.getElementById('historico_horas_restantes').textContent = data.balance.horas_restantes.toFixed(1) + 'h';
            document.getElementById('historico_valor_aproximado').textContent = 'R$ ' + data.balance.valor_aproximado.toFixed(2);
            
            // Preencher paginação
            const pagination = document.getElementById('historico_pagination');
            pagination.innerHTML = '';
            
            if (data.pagination.has_prev) {
                const li = document.createElement('li');
                li.className = 'page-item';
                const a = document.createElement('a');
                a.className = 'page-link';
                a.href = '#';
                a.textContent = 'Anterior';
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    carregarHistorico(collaboratorId, page - 1);
                });
                li.appendChild(a);
                pagination.appendChild(li);
            }
            
            for (let i = 1; i <= data.pagination.pages; i++) {
                const li = document.createElement('li');
                li.className = 'page-item' + (i === page ? ' active' : '');
                const a = document.createElement('a');
                a.className = 'page-link';
                a.href = '#';
                a.textContent = String(i);
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    carregarHistorico(collaboratorId, i);
                });
                li.appendChild(a);
                pagination.appendChild(li);
            }
            
            if (data.pagination.has_next) {
                const li = document.createElement('li');
                li.className = 'page-item';
                const a = document.createElement('a');
                a.className = 'page-link';
                a.href = '#';
                a.textContent = 'Próxima';
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    carregarHistorico(collaboratorId, page + 1);
                });
                li.appendChild(a);
                pagination.appendChild(li);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            document.getElementById('historico_loading').style.display = 'none';
            alert('Erro ao carregar histórico');
        });
}

// Event listeners para modal de lançamento
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se Bootstrap está carregado
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap não está carregado!');
        alert('Erro: Bootstrap não está carregado. Recarregue a página.');
        return;
    }
    
    // Event listeners para botões de abrir histórico e lançamento
    document.querySelectorAll('.btn-abrir-historico').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const collaboratorId = parseInt(this.getAttribute('data-collaborator-id'));
            const collaboratorName = this.getAttribute('data-collaborator-name');
            abrirHistorico(collaboratorId, collaboratorName);
        });
    });
    
    document.querySelectorAll('.btn-abrir-lancamento').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const collaboratorId = parseInt(this.getAttribute('data-collaborator-id'));
            const collaboratorName = this.getAttribute('data-collaborator-name');
            abrirLancamento(collaboratorId, collaboratorName);
        });
    });
    
    const lancamentoOrigem = document.getElementById('lancamento_origem');
    const lancamentoDescricaoGroup = document.getElementById('lancamento_descricao_group');
    const lancamentoDescricao = document.getElementById('lancamento_descricao');
    const lancamentoHoras = document.getElementById('lancamento_horas');
    const btnSalvarLancamento = document.getElementById('btnSalvarLancamento');
    
    if (lancamentoOrigem) {
        lancamentoOrigem.addEventListener('change', function() {
            if (this.value === 'Horas adicionais' || this.value === 'Outro') {
                lancamentoDescricaoGroup.style.display = 'block';
                lancamentoDescricao.required = true;
            } else {
                lancamentoDescricaoGroup.style.display = 'none';
                lancamentoDescricao.required = false;
                lancamentoDescricao.value = '';
            }
            validarFormLancamento();
        });
    }
    
    if (lancamentoHoras) {
        lancamentoHoras.addEventListener('input', function() {
            validarFormLancamento();
        });
    }
    
    // Validar formulário de lançamento
    function validarFormLancamento() {
        const data = document.getElementById('lancamento_data').value;
        const origem = document.getElementById('lancamento_origem').value;
        const descricao = document.getElementById('lancamento_descricao').value;
        const horas = document.getElementById('lancamento_horas').value;
        
        let valido = true;
        
        if (!data || !origem || !horas) {
            valido = false;
        }
        
        if ((origem === 'Horas adicionais' || origem === 'Outro') && !descricao.trim()) {
            valido = false;
        }
        
        const validacaoHoras = validarHoras(horas, origem);
        if (!validacaoHoras.valido) {
            lancamentoHoras.classList.add('is-invalid');
            document.getElementById('lancamento_horas_error').textContent = validacaoHoras.erro;
            valido = false;
        } else {
            lancamentoHoras.classList.remove('is-invalid');
            document.getElementById('lancamento_horas_error').textContent = '';
        }
        
        btnSalvarLancamento.disabled = !valido;
    }
    
    // Botão Registrar Pagamento
    const btnRegistrarPagamento = document.getElementById('btnRegistrarPagamento');
    if (btnRegistrarPagamento) {
        btnRegistrarPagamento.addEventListener('click', function() {
            abrirModalFechamento();
        });
    }
    
    // Botão Confirmar Fechamento
    const btnConfirmarFechamento = document.getElementById('btnConfirmarFechamento');
    if (btnConfirmarFechamento) {
        btnConfirmarFechamento.addEventListener('click', function() {
            if (confirm('Tem certeza que deseja fechar o ciclo? Esta ação não pode ser desfeita.')) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '{{ url_for("ciclos.confirmar_fechamento") }}';
                
                const observacoes = document.createElement('input');
                observacoes.type = 'hidden';
                observacoes.name = 'observacoes';
                observacoes.value = document.getElementById('fechamento_observacoes').value;
                form.appendChild(observacoes);
                
                document.body.appendChild(form);
                form.submit();
            }
        });
    }
    
    // Botão PDF Individual
    const btnPDFIndividual = document.getElementById('btnPDFIndividual');
    if (btnPDFIndividual) {
        btnPDFIndividual.addEventListener('click', function() {
            window.open(`/ciclos/pdf/individual/${currentCollaboratorId}`, '_blank');
        });
    }
    
    // Botão PDF Geral
    const btnPDFGeral = document.getElementById('btnPDFGeral');
    if (btnPDFGeral) {
        btnPDFGeral.addEventListener('click', function() {
            window.open('{{ url_for("ciclos.pdf_geral") }}', '_blank');
        });
    }
    
    // Validar formulário de ajuste
    const ajustarHoras = document.getElementById('ajustar_horas');
    const btnSalvarAjuste = document.getElementById('btnSalvarAjuste');
    if (ajustarHoras && btnSalvarAjuste) {
        ajustarHoras.addEventListener('input', function() {
            // Para ajustes, não temos origem - validar apenas formato (permitir negativo)
            const validacao = validarHoras(this.value, undefined);
            if (validacao.valido) {
                this.classList.remove('is-invalid');
                document.getElementById('ajustar_horas_error').textContent = '';
                btnSalvarAjuste.disabled = false;
            } else {
                this.classList.add('is-invalid');
                document.getElementById('ajustar_horas_error').textContent = validacao.erro;
                btnSalvarAjuste.disabled = true;
            }
        });
        
        // Form de ajuste
        const formAjustar = document.getElementById('formAjustar');
        if (formAjustar) {
            formAjustar.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const cicloId = document.getElementById('ajustar_ciclo_id').value;
                
                fetch(`/ciclos/ajustar/${cicloId}`, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || 'Erro desconhecido');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('modalAjustar')).hide();
                        // Recarregar histórico ao invés de recarregar página inteira
                        if (typeof currentCollaboratorId !== 'undefined' && typeof currentPage !== 'undefined') {
                            carregarHistorico(currentCollaboratorId, currentPage);
                        } else {
                            location.reload();
                        }
                    } else {
                        alert('Erro ao ajustar registro: ' + (data.error || 'Erro desconhecido'));
                    }
                })
                .catch(error => {
                    console.error('Erro:', error);
                    alert('Erro ao ajustar registro: ' + error.message);
                });
            });
        }
    }
});

// Função para excluir registro
function excluirRegistro(cicloId, collaboratorId) {
    if (!confirm('Tem certeza que deseja excluir este registro? Esta ação não pode ser desfeita.')) {
        return;
    }
    
    fetch(`/ciclos/excluir/${cicloId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            // Recarregar histórico após exclusão
            carregarHistorico(collaboratorId, currentPage);
            // Mostrar mensagem de sucesso
            alert(data.message || 'Registro excluído com sucesso!');
        } else {
            alert('Erro ao excluir registro: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao excluir registro');
    });
}

// Abrir modal de fechamento
function abrirModalFechamento() {
    document.getElementById('fechamento_loading').style.display = 'block';
    document.getElementById('fechamento_content').style.display = 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('modalFechamento'));
    modal.show();
    
    fetch('{{ url_for("ciclos.resumo_fechamento") }}')
        .then(response => response.json())
        .then(data => {
            document.getElementById('fechamento_loading').style.display = 'none';
            
            if (!data.ok) {
                alert('Erro ao carregar resumo: ' + data.error);
                return;
            }
            
            document.getElementById('fechamento_content').style.display = 'block';
            
            // Preencher avisos
            if (data.avisos && data.avisos.length > 0) {
                document.getElementById('fechamento_avisos').style.display = 'block';
                const avisosList = document.getElementById('fechamento_avisos_list');
                avisosList.innerHTML = '';
                data.avisos.forEach(aviso => {
                    const li = document.createElement('li');
                    li.textContent = aviso;
                    avisosList.appendChild(li);
                });
            } else {
                document.getElementById('fechamento_avisos').style.display = 'none';
            }
            
            // Preencher tabela
            const tbody = document.getElementById('fechamento_tbody');
            tbody.innerHTML = '';
            data.colaboradores.forEach(colab => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = colab.nome;
                row.insertCell(1).textContent = colab.total_horas + 'h';
                row.insertCell(2).textContent = colab.dias_completos + ' dias';
                row.insertCell(3).textContent = colab.horas_restantes + 'h';
                row.insertCell(4).textContent = 'R$ ' + colab.valor.toFixed(2);
            });
            
            // Preencher totais
            document.getElementById('fechamento_total_horas').textContent = data.totais.total_horas + 'h';
            document.getElementById('fechamento_total_dias').textContent = data.totais.total_dias + ' dias';
            document.getElementById('fechamento_total_horas_restantes').textContent = data.totais.total_horas_restantes + 'h';
            document.getElementById('fechamento_total_valor').textContent = 'R$ ' + data.totais.total_valor.toFixed(2);
        })
        .catch(error => {
            console.error('Erro:', error);
            document.getElementById('fechamento_loading').style.display = 'none';
            alert('Erro ao carregar resumo');
        });
}
