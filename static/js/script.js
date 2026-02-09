// Sistema de seleção com 2 cliques
class SelecionadorArea {
    constructor(containerId, imagemId) {
        this.container = document.getElementById(containerId);
        this.imagem = document.getElementById(imagemId);
        this.area = document.getElementById('area-selecao');
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        this.cliqueAtual = 0;
        this.inicializar();
    }
    
    inicializar() {
        this.imagem.addEventListener('click', this.clicar.bind(this));
        
        // Botão limpar
        document.getElementById('btn-limpar').addEventListener('click', () => {
            this.limpar();
        });
        
        // Botão salvar
        document.getElementById('btn-salvar-area').addEventListener('click', () => {
            this.salvar();
        });
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
            
            document.getElementById('status-selecao').textContent = 
                `Primeiro ponto: (${x}, ${y}) - Clique no segundo ponto`;
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
            
            // Atualizar interface
            document.getElementById('status-selecao').textContent = 
                `Área selecionada: (${this.coordenadas.x1}, ${this.coordenadas.y1}) até (${this.coordenadas.x2}, ${this.coordenadas.y2})`;
            
            document.getElementById('btn-salvar-area').disabled = false;
            
            // Mostrar coordenadas
            document.getElementById('coordenadas-info').innerHTML = `
                <strong>Coordenadas da área da foto:</strong><br>
                X1: ${this.coordenadas.x1}px<br>
                Y1: ${this.coordenadas.y1}px<br>
                X2: ${this.coordenadas.x2}px<br>
                Y2: ${this.coordenadas.y2}px<br>
                Largura: ${width}px<br>
                Altura: ${height}px
            `;
        }
    }
    
    limpar() {
        this.cliqueAtual = 0;
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        this.area.style.display = 'none';
        this.area.style.width = '0';
        this.area.style.height = '0';
        document.getElementById('btn-salvar-area').disabled = true;
        document.getElementById('status-selecao').textContent = 'Clique para selecionar o primeiro ponto';
        document.getElementById('coordenadas-info').innerHTML = '';
    }
    
    salvar() {
        fetch('/api/salvar_area_foto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(this.coordenadas)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Área da foto salva com sucesso!');
            } else {
                alert('Erro ao salvar área: ' + (data.error || 'Desconhecido'));
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao salvar área da foto');
        });
    }
}

// Gerenciador de campos
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar seletor de área se existir na página
    if (document.getElementById('preview-imagem')) {
        window.selecionador = new SelecionadorArea('preview-container', 'preview-imagem');
    }
    
    // Gerenciar campos editáveis
    document.querySelectorAll('.campo-editavel-check').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const campoId = this.dataset.campoId;
            const editavel = this.checked ? 1 : 0;
            
            fetch('/api/atualizar_campo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: campoId,
                    editavel: editavel
                })
            });
        });
    });
    
    // Atualizar nomes de exibição
    document.querySelectorAll('.nome-exibicao-input').forEach(input => {
        input.addEventListener('blur', function() {
            const campoId = this.dataset.campoId;
            const nomeExibicao = this.value;
            
            fetch('/api/atualizar_campo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: campoId,
                    nome_exibicao: nomeExibicao
                })
            });
        });
    });
    
    // Detectar campos automaticamente
    const btnDetectar = document.getElementById('btn-detectar-campos');
    if (btnDetectar) {
        btnDetectar.addEventListener('click', function() {
            const tipo = this.dataset.tipo;
            
            fetch(`/api/detectar_campos/${tipo}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(`Detectados ${data.total_campos} campos no PSD ${tipo}. Recarregue a página para vê-los.`);
                        location.reload();
                    } else {
                        alert('Erro ao detectar campos: ' + data.error);
                    }
                });
        });
    }
    
    // Preview de foto
    const inputFoto = document.getElementById('foto-input');
    if (inputFoto) {
        inputFoto.addEventListener('change', function() {
            const preview = document.getElementById('foto-preview');
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
});