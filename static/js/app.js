/**
 * Sistema de Pesquisa de Licitações - JavaScript
 */

// Utilitários
const API = {
    async get(url) {
        const response = await fetch(url);
        return response.json();
    },

    async post(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        return response.json();
    },

    async delete(url) {
        const response = await fetch(url, {
            method: 'DELETE',
        });
        return response.json();
    }
};

// Feedback visual
function showLoading(element) {
    element.disabled = true;
    element.dataset.originalText = element.textContent;
    element.textContent = '⏳ Aguarde...';
}

function hideLoading(element) {
    element.disabled = false;
    element.textContent = element.dataset.originalText;
}

function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        ${message}
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;

    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Pesquisa
async function executarPesquisa(termo) {
    try {
        const result = await API.post('/api/pesquisar', { termo });

        if (result.error) {
            showAlert(result.error, 'error');
        } else {
            showAlert(`Pesquisa concluída! ${result.total_encontrados} resultados encontrados, ${result.novos_salvos} novos salvos.`);
            location.reload();
        }
    } catch (e) {
        showAlert('Erro na pesquisa: ' + e.message, 'error');
    }
}

// Criar oportunidade
async function criarOportunidade(resultadoId, button) {
    if (!confirm('Deseja criar uma oportunidade para este resultado? O sistema irá extrair detalhes e baixar documentos.')) {
        return;
    }

    showLoading(button);

    try {
        const result = await API.post('/api/oportunidades', { resultado_id: resultadoId });

        if (result.error) {
            showAlert(result.error, 'error');
        } else {
            showAlert(`Oportunidade ${result.codigo} criada com sucesso!`);
            location.reload();
        }
    } catch (e) {
        showAlert('Erro ao criar oportunidade: ' + e.message, 'error');
    } finally {
        hideLoading(button);
    }
}

// Deletar palavra-chave
async function deletarPalavra(id, button) {
    if (!confirm('Tem certeza que deseja remover esta palavra-chave?')) {
        return;
    }

    try {
        const result = await API.delete(`/api/palavras-chave/${id}`);

        if (result.success) {
            button.closest('tr').remove();
            showAlert('Palavra-chave removida com sucesso!');
        } else {
            showAlert(result.error || 'Erro ao remover', 'error');
        }
    } catch (e) {
        showAlert('Erro: ' + e.message, 'error');
    }
}

// Copiar texto para clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Texto copiado!');
    }).catch(() => {
        showAlert('Erro ao copiar', 'error');
    });
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('Sistema de Pesquisa de Licitações carregado!');

    // Inicia monitoramento se estiver na página de palavras-chave
    if (document.getElementById('search-monitor')) {
        window.atualizarStatusPesquisas();
    }
});

// --- Pesquisa em Segundo Plano ---

// --- Pesquisa em Segundo Plano ---

// Função para selecionar/deselecionar toda a região
window.toggleRegion = function (checkbox, regionName) {
    const container = document.querySelector(`.region-ufs-compact[data-region="${regionName}"], .region-ufs[data-region="${regionName}"]`);
    if (!container) return;
    const inputs = container.querySelectorAll('input[type="checkbox"]');
    inputs.forEach(input => {
        input.checked = checkbox.checked;
    });
};

window.toggleAllUfs = function (checked) {
    const inputs = document.querySelectorAll('input[name="global_ufs"]');
    inputs.forEach(input => {
        input.checked = checked;
    });
    // Desmarca também as regiões
    document.querySelectorAll('.region-toggle').forEach(cb => cb.checked = false);
};

// Coleta as UFs marcadas na interface global
window.getSelectedUfs = function () {
    const checkboxes = document.querySelectorAll('input[name="global_ufs"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
};

window.pesquisarTodas = function () {
    const ufs = window.getSelectedUfs();
    const incremental = document.getElementById('check-incremental')?.checked || false;

    if (ufs.length === 0) {
        alert('Por favor, selecione pelo menos um estado (UF) para a pesquisa.');
        return;
    }

    const msg = incremental
        ? `Deseja iniciar a pesquisa INCREMENTAL para todas as palavras-chave ativas nos ${ufs.length} estados selecionados?`
        : `Deseja iniciar a pesquisa TOTAL para todas as palavras-chave ativas nos ${ufs.length} estados selecionados? Isso pode levar alguns minutos.`;

    if (!confirm(msg)) return;

    fetch('/api/pesquisar-todas', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ufs: ufs,
            incremental: incremental
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert('Pesquisa iniciada em segundo plano!', 'success');
                window.atualizarStatusPesquisas();
            } else {
                showAlert('Erro ao iniciar pesquisa: ' + (data.error || 'Erro desconhecido'), 'error');
            }
        })
        .catch(err => {
            console.error('Erro:', err);
            showAlert('Erro de conexão ao iniciar pesquisa', 'error');
        });
};

window.pesquisarPalavra = function (palavraId, termo) {
    const ufs = window.getSelectedUfs();
    const incremental = document.getElementById('check-incremental')?.checked || false;

    if (ufs.length === 0) {
        alert('Por favor, selecione pelo menos um estado (UF) para a pesquisa.');
        return;
    }

    fetch('/api/pesquisar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            palavra_id: palavraId,
            ufs: ufs,
            incremental: incremental
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert(`Pesquisa para "${termo}" iniciada nos estados selecionados!`, 'success');
                window.atualizarStatusPesquisas();
            } else {
                showAlert('Erro ao iniciar pesquisa: ' + (data.error || 'Erro desconhecido'), 'error');
            }
        })
        .catch(err => {
            console.error('Erro:', err);
            showAlert('Erro de conexão ao iniciar pesquisa', 'error');
        });
};

window.atualizarStatusPesquisas = function () {
    fetch('/api/pesquisar/status')
        .then(res => res.json())
        .then(tasks => {
            const monitor = document.getElementById('search-monitor');
            const container = document.getElementById('tasks-container');

            if (!tasks || tasks.length === 0) {
                if (monitor) monitor.style.display = 'none';
                return;
            }

            if (monitor) monitor.style.display = 'block';
            if (container) {
                container.innerHTML = '';
                tasks.forEach(task => {
                    container.appendChild(window.renderizarTarefa(task));
                });
            }

            // Se houver alguma tarefa rodando ou pendente, agenda nova atualização
            const temAtiva = tasks.some(t => t.status === 'rodando' || t.status === 'pendente');
            if (temAtiva) {
                setTimeout(window.atualizarStatusPesquisas, 3000);
            }
        })
        .catch(err => console.error('Erro ao atualizar status:', err));
};

window.renderizarTarefa = function (task) {
    const div = document.createElement('div');
    div.className = 'task-item';

    const statusClass = `status-${task.status}`;
    const termosInfo = task.termos_concluidos.length + '/' + task.termos.length;

    // Calcula progresso se for apenas um termo
    const progresso = task.progresso || 0;

    div.innerHTML = `
        <div class="task-header">
            <span><strong>Tarefa:</strong> ${task.id}</span>
            <span class="task-status ${statusClass}">${task.status}</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: ${progresso}%"></div>
        </div>
        <div class="task-footer">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #666; margin-top: 5px;">
                <span>📍 ${termosInfo} termos | ✨ ${task.novos_salvos} novos | 🔄 ${task.atualizados || 0} atualizados</span>
                <span>🕒 ${task.inicio}${task.fim ? ' - ' + task.fim : ''}</span>
            </div>
            ${task.erro ? `<div style="margin-top: 5px;"><small class="status-erro">❌ ${task.erro}</small></div>` : ''}
        </div>
    `;
    return div;
};

// Função para atualizar um resultado individual
window.atualizarResultado = function (id, btn) {
    if (btn) {
        btn.disabled = true;
        btn.classList.add('loading-spin');
        btn.innerHTML = '⏳';
    }

    fetch(`/api/resultados/${id}/atualizar`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('Resultado atualizado!', 'success');
                // Recarrega os dados do card ou a página
                setTimeout(() => location.reload(), 800);
            } else {
                showAlert('Erro ao atualizar: ' + (data.error || 'Erro desconhecido'), 'danger');
                if (btn) {
                    btn.disabled = false;
                    btn.classList.remove('loading-spin');
                    btn.innerHTML = '🔄';
                }
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            showAlert('Erro na requisição', 'danger');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('loading-spin');
                btn.innerHTML = '🔄';
            }
        });
};
