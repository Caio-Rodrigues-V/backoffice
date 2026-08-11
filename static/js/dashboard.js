// ==========================================================================
// DDM Backoffice - Script de Controle do Dashboard (Interação & API Client)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Inicialização
    carregarDados();
    
    // Configura atualização automática a cada 15 segundos
    setInterval(carregarDados, 15000);
    
    // Event Listeners dos Botões de Ação Principal
    document.getElementById('btn-refresh').addEventListener('click', carregarDados);
    
    // Event Listeners de Busca e Filtros
    document.getElementById('search-input').addEventListener('input', filtrarLotes);
    document.getElementById('status-filter').addEventListener('change', filtrarLotes);
});

// Cache local de lotes para filtragem rápida
let cacheLotes = [];

/**
 * Carrega estatísticas e lotes do banco de dados simultaneamente.
 */
async function carregarDados() {
    try {
        await Promise.all([
            atualizarEstatisticas(),
            atualizarListaLotes()
        ]);
    } catch (error) {
        console.error("Erro ao carregar dados do dashboard:", error);
    }
}

/**
 * Consulta a API de Estatísticas e atualiza os contadores no topo.
 */
async function atualizarEstatisticas() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('stat-total-lotes').innerText = data.total_lotes;
            document.getElementById('stat-total-alunos').innerText = data.total_alunos;
            document.getElementById('stat-total-acordos').innerText = data.total_acordos;
            document.getElementById('stat-taxa-conversao').innerText = `${data.taxa_conversao}%`;
        }
    } catch (error) {
        console.error("Erro ao carregar estatísticas:", error);
    }
}

/**
 * Consulta todos os lotes e renderiza a lista.
 */
async function atualizarListaLotes() {
    try {
        const response = await fetch('/api/lotes');
        const data = await response.json();
        
        if (response.ok) {
            cacheLotes = data;
            renderizarLotes(cacheLotes);
        }
    } catch (error) {
        console.error("Erro ao obter lotes:", error);
        document.getElementById('lotes-list').innerHTML = `
            <div class="loading-spinner">
                <p style="color: var(--status-error)">Erro ao se conectar ao banco de dados.</p>
            </div>
        `;
    }
}

/**
 * Renderiza os cards de lotes na tela.
 */
function renderizarLotes(lotes) {
    const container = document.getElementById('lotes-list');
    
    if (lotes.length === 0) {
        container.innerHTML = `
            <div class="glass-card" style="padding: 3rem; text-align: center; color: var(--text-secondary)">
                <h3>Nenhum lote registrado</h3>
                <p style="margin-top: 0.5rem; font-size: 0.9rem">Envie e-mails com o assunto "Negociação" e clique em "Buscar E-mails" para começar.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    lotes.forEach(lote => {
        // Formata data
        let dataFormatada = 'Data inválida';
        try {
            const date = new Date(lote.received_at);
            dataFormatada = date.toLocaleString('pt-BR');
        } catch (e) {}
        
        // Define o status do lote
        const statusLoteText = lote.status === 'concluido' ? 'Concluído' : 'Processando';
        const statusLoteClass = lote.status === 'concluido' ? 'badge-success' : 'badge-active';
        
        // Calcula progresso do lote
        const totalAlunos = lote.alunos.length;
        const concluidos = lote.alunos.filter(a => ['acordo_fechado', 'sem_retorno', 'erro'].includes(a.status_whatsapp)).length;
        const progressText = `${concluidos}/${totalAlunos} atendidos`;
        
        html += `
            <div class="lote-wrapper glass-card" id="lote-wrapper-${lote.id}">
                <div class="lote-header" onclick="toggleLoteExpansion(${lote.id})">
                    <span class="lote-toggle-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
                    </span>
                    <div class="lote-subject-group">
                        <h4>${lote.subject}</h4>
                        <span>De: ${lote.sender}</span>
                    </div>
                    <span class="lote-meta">${dataFormatada}</span>
                    <span class="lote-meta" style="font-weight: 600; color: var(--text-primary)">${progressText}</span>
                    <span class="badge ${statusLoteClass}">${statusLoteText}</span>
                </div>
                
                <div class="lote-details">
                    <table class="alunos-table">
                        <thead>
                            <tr>
                                <th>Identificador (RA/CPF)</th>
                                <th>Nome do Aluno</th>
                                <th>Telefone</th>
                                <th>Status GoGenier (Julia)</th>
                                <th style="text-align: right">Última Atualização</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${lote.alunos.map(aluno => renderAlunoRow(aluno)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Renderiza uma linha de aluno na tabela interna do lote.
 */
function renderAlunoRow(aluno) {
    let statusText = 'Pendente';
    let statusClass = 'badge-pending';
    
    if (aluno.status_whatsapp === 'contatando') {
        statusText = 'Abordagem Ativa';
        statusClass = 'badge-active';
    } else if (aluno.status_whatsapp === 'acordo_fechado') {
        statusText = 'Acordo Fechado';
        statusClass = 'badge-success';
    } else if (aluno.status_whatsapp === 'sem_retorno') {
        statusText = 'Sem Retorno';
        statusClass = 'badge-error';
    } else if (aluno.status_whatsapp === 'erro') {
        statusText = 'Erro';
        statusClass = 'badge-error';
    }
    
    // Formata o timestamp do último retorno
    let atualizacaoText = 'Aguardando envio';
    if (aluno.status_whatsapp !== 'pendente') {
        atualizacaoText = 'Pendente';
        if (aluno.last_update) {
            try {
                const date = new Date(aluno.last_update);
                atualizacaoText = date.toLocaleString('pt-BR');
            } catch (e) {}
        }
    }
    
    return `
        <tr>
            <td style="font-family: monospace; font-weight: 500">${aluno.ra_cpf || 'Não informado'}</td>
            <td style="font-weight: 500">${aluno.nome}</td>
            <td>${aluno.telefone || 'Sem número'}</td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
            <td style="text-align: right; font-size: 0.85rem; color: var(--text-secondary)">${atualizacaoText}</td>
        </tr>
    `;
}

/**
 * Controla a expansão/retração sanfonada dos lotes.
 */
function toggleLoteExpansion(idLote) {
    const wrapper = document.getElementById(`lote-wrapper-${idLote}`);
    wrapper.classList.toggle('expanded');
}

/**
 * Filtra a lista de lotes no frontend.
 */
function filtrarLotes() {
    const searchVal = document.getElementById('search-input').value.toLowerCase().strip;
    const filterStatus = document.getElementById('status-filter').value;
    
    const lotesFiltrados = cacheLotes.filter(lote => {
        // Filtro de Busca por assunto, remetente ou nome de alunos
        const matchesSearch = 
            lote.subject.toLowerCase().includes(searchVal) ||
            lote.sender.toLowerCase().includes(searchVal) ||
            lote.alunos.some(a => 
                a.nome.toLowerCase().includes(searchVal) || 
                (a.ra_cpf && a.ra_cpf.includes(searchVal))
            );
            
        // Filtro de status do aluno
        let matchesStatus = true;
        if (filterStatus !== 'todos') {
            matchesStatus = lote.alunos.some(a => a.status_whatsapp === filterStatus);
        }
        
        return matchesSearch && matchesStatus;
    });
    
    renderizarLotes(lotesFiltrados);
}

/**
 * Ação: Buscar novos e-mails (Sincronização manual).
 */
async function syncEmails() {
    mostrarToast("Verificando e-mails...", "info");
    const btn = document.getElementById('btn-sync-emails');
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/acao/buscar-emails', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            mostrarToast("Sincronização concluída!", "success");
            carregarDados();
        } else {
            mostrarToast(data.message || "Erro ao buscar e-mails.", "error");
        }
    } catch (e) {
        mostrarToast("Erro de conexão.", "error");
    } finally {
        btn.disabled = false;
    }
}

/**
 * Ação: Enviar relatórios de retorno final.
 */
async function sendReturns() {
    mostrarToast("Processando retornos finais...", "info");
    const btn = document.getElementById('btn-send-returns');
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/acao/enviar-retornos', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            mostrarToast("Retornos processados com sucesso!", "success");
            carregarDados();
        } else {
            mostrarToast(data.message || "Sem lotes prontos para retorno.", "error");
        }
    } catch (e) {
        mostrarToast("Erro de conexão.", "error");
    } finally {
        btn.disabled = false;
    }
}

/**
 * Ação: Simular a resposta de webhook da GoGenier para um aluno.
 */
async function simularResposta(alunoId, resposta) {
    mostrarToast("Simulando webhook...", "info");
    
    try {
        const response = await fetch('/api/acao/simular-resposta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aluno_id: alunoId, resposta: resposta })
        });
        const data = await response.json();
        
        if (response.ok && data.success) {
            mostrarToast("Webhook simulado!", "success");
            carregarDados();
        }
    } catch (e) {
        mostrarToast("Erro ao processar simulação.", "error");
    }
}

/**
 * Exibe notificações toast no canto da tela.
 */
function mostrarToast(mensagem, tipo = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;
    
    let icon = '';
    if (tipo === 'success') icon = '✓';
    else if (tipo === 'error') icon = '✗';
    else icon = 'ℹ';
    
    toast.innerHTML = `<span>${icon}</span> <p>${mensagem}</p>`;
    container.appendChild(toast);
    
    // Anima a entrada
    setTimeout(() => toast.classList.add('show'), 50);
    
    // Remove após 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Extensão do String.prototype para evitar erros de strip no IE/antigos
if (!String.prototype.strip) {
    String.prototype.strip = function() {
        return this.replace(/^\s+|\s+$/g, '');
    };
}
