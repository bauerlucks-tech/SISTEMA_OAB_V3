// Sistema de seleção com 2 cliques
class AreaSelecao {
    constructor(containerId, imagemId) {
        this.container = document.getElementById(containerId);
        this.imagem = document.getElementById(imagemId);
        this.area = document.getElementById('area-selecao');
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        this.cliqueAtual = 0;
        
        this.inicializar();
    }
    
    inicializar() {
        // Eventos do mouse
        this.imagem.addEventListener('click', this.clicar.bind(this));
        
        // Botões
        document.getElementById('btn-limpar')?.addEventListener('click', () => this.limpar());
        document.getElementById('btn-salvar-area')?.addEventListener('click', () => this.salvar());
        
        // Carregar área existente
        this.carregarAreaExistente();
    }
    
    clicar(event) {
        const rect = this.imagem.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        if (this.cliqueAtual === 0) {
            // Primeiro clique
            this.coordenadas.x1 = Math.round(x);
            this.coordenadas.y1 = Math.round(y);
            this.area.style.left = x + 'px';
            this.area.style.top = y + 'px';
            this.area.style.display = 'block';
            this.cliqueAtual = 1;
            
            this.atualizarStatus(`✅ Primeiro ponto: (${x}, ${y}) - Clique no segundo ponto`);
        } else {
            // Segundo clique
            this.coordenadas.x2 = Math.round(x);
            this.coordenadas.y2 = Math.round(y);
            
            // Garantir que x2 > x1 e y2 > y1
            if (this.coordenadas.x2 < this.coordenadas.x1) {
                [this.coordenadas.x1, this.coordenadas.x2] = [this.coordenadas.x2, this.coordenadas.x1];
            }
            if (this.coordenadas.y2 < this.coordenadas.y1) {
                [this.coordenadas.y1, this.coordenadas.y2] = [this.coordenadas.y2, this.coordenadas.y1];
            }
            
            const width = this.coordenadas.x2 - this.coordenadas.x1;
            const height = this.coordenadas.y2 - this.coordenadas.y1;
            
            this.area.style.width = width + 'px';
            this.area.style.height = height + 'px';
            this.cliqueAtual = 0;
            
            this.atualizarStatus(`✅ Área selecionada! Clique em "Salvar Área" para confirmar.`);
            this.mostrarCoordenadas();
            document.getElementById('btn-salvar-area').disabled = false;
        }
    }
    
    carregarAreaExistente() {
        // Verificar se há área salva no banco
        // Em produção, isso viria de uma API
        const areaSalva = document.getElementById('area-salva');
        if (areaSalva && areaSalva.value) {
            try {
                const area = JSON.parse(areaSalva.value);
                this.coordenadas = { x1: area[0], y1: area[1], x2: area[2], y2: area[3] };
                
                this.area.style.left = area[0] + 'px';
                this.area.style.top = area[1] + 'px';
                this.area.style.width = (area[2] - area[0]) + 'px';
                this.area.style.height = (area[3] - area[1]) + 'px';
                this.area.style.display = 'block';
                
                this.mostrarCoordenadas();
                this.atualizarStatus('✅ Área carregada do banco de dados');
            } catch (e) {
                console.log('Nenhuma área salva encontrada');
            }
        }
    }
    
    mostrarCoordenadas() {
        const width = this.coordenadas.x2 - this.coordenadas.x1;
        const height = this.coordenadas.y2 - this.coordenadas.y1;
        
        const info = document.getElementById('coordenadas-info');
        if (info) {
            info.innerHTML = `
                <h5>📐 Coordenadas da Área</h5>
                <table class="table table-sm">
                    <tr><td><strong>X1 (esquerda):</strong></td><td>${this.coordenadas.x1}px</td></tr>
                    <tr><td><strong>Y1 (topo):</strong></td><td>${this.coordenadas.y1}px</td></tr>
                    <tr><td><strong>X2 (direita):</strong></td><td>${this.coordenadas.x2}px</td></tr>
                    <tr><td><strong>Y2 (base):</strong></td><td>${this.coordenadas.y2}px</td></tr>
                    <tr><td><strong>Largura:</strong></td><td>${width}px</td></tr>
                    <tr><td><strong>Altura:</strong></td><td>${height}px</td></tr>
                </table>
            `;
        }
    }
    
    atualizarStatus(mensagem) {
        const status = document.getElementById('status-selecao');
        if (status) {
            status.textContent = mensagem;
            status.className = mensagem.includes('✅') ? 'alert alert-success' : 'alert alert-info';
        }
    }
    
    limpar() {
        this.cliqueAtual = 0;
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        this.area.style.display = 'none';
        this.area.style.width = '0';
        this.area.style.height = '0';
        
        document.getElementById('btn-salvar-area').disabled = true;
        this.atualizarStatus('🖱️ Clique para selecionar o primeiro ponto');
        
        const info = document.getElementById('coordenadas-info');
        if (info) info.innerHTML = '';
    }
    
    salvar() {
        // Validar área mínima
        const width = this.coordenadas.x2 - this.coordenadas.x1;
        const height = this.coordenadas.y2 - this.coordenadas.y1;
        
        if (width < 50 || height < 50) {
            alert('⚠️ A área selecionada é muito pequena. Selecione uma área maior.');
            return;
        }
        
        fetch('/api/salvar_area', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(this.coordenadas)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.atualizarStatus('✅ Área salva com sucesso!');
                alert('Área da foto configurada com sucesso!');
            } else {
                alert('❌ Erro ao salvar área: ' + (data.error || 'Erro desconhecido'));
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('❌ Erro de conexão ao salvar área');
        });
    }
}

// Gerenciamento de campos
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar seletor de área
    if (document.getElementById('preview-imagem')) {
        window.seletor = new AreaSelecao('preview-container', 'preview-imagem');
    }
    
    // Atualizar campos editáveis
    document.querySelectorAll('.campo-editavel').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const campoId = this.dataset.id;
            const editavel = this.checked ? 1 : 0;
            
            fetch('/api/salvar_campo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: campoId, editavel: editavel })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    alert('Erro ao salvar configuração do campo');
                    this.checked = !this.checked; // Reverter
                }
            });
        });
    });
    
    // Atualizar nomes de exibição
    document.querySelectorAll('.nome-exibicao').forEach(input => {
        input.addEventListener('blur', function() {
            const campoId = this.dataset.id;
            const nomeExibicao = this.value.trim();
            
            if (nomeExibicao) {
                fetch('/api/salvar_campo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: campoId, nome_exibicao: nomeExibicao })
                });
            }
        });
    });
    
    // Detectar campos automaticamente
    document.querySelectorAll('.btn-detectar').forEach(btn => {
        btn.addEventListener('click', function() {
            const tipo = this.dataset.tipo;
            
            fetch(`/api/detectar_campos/${tipo}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`✅ Detectados ${data.campos} campos no PSD ${tipo}! Recarregando...`);
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        alert('❌ Erro ao detectar campos: ' + data.error);
                    }
                });
        });
    });
    
    // Preview de foto
    const inputFoto = document.getElementById('foto');
    if (inputFoto) {
        inputFoto.addEventListener('change', function() {
            const preview = document.getElementById('foto-preview');
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    preview.classList.add('fade-in');
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Validação de formulários
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            let valid = true;
            
            this.querySelectorAll('[required]').forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    valid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!valid) {
                e.preventDefault();
                alert('⚠️ Preencha todos os campos obrigatórios!');
            }
        });
    });
    
    // Animações
    const cards = document.querySelectorAll('.card-oab');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });
});

// Funções auxiliares
function mostrarLoading(mensagem = 'Processando...') {
    const loading = document.createElement('div');
    loading.id = 'loading-overlay';
    loading.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        ">
            <div class="spinner-border text-light" style="width: 3rem; height: 3rem;">
                <span class="visually-hidden">${mensagem}</span>
            </div>
        </div>
    `;
    document.body.appendChild(loading);
}

function esconderLoading() {
    const loading = document.getElementById('loading-overlay');
    if (loading) loading.remove();
}