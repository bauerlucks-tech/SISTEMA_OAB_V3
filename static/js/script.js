// Sistema de seleção de área da foto
class AreaSelecao {
    constructor(containerId, imagemId) {
        this.container = document.getElementById(containerId);
        this.imagem = document.getElementById(imagemId);
        this.selecao = null;
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        this.isDrawing = false;
        
        this.inicializar();
    }
    
    inicializar() {
        this.selecao = document.createElement('div');
        this.selecao.className = 'selecao-foto';
        this.selecao.style.display = 'none';
        this.container.appendChild(this.selecao);
        
        this.imagem.addEventListener('mousedown', this.iniciarSelecao.bind(this));
        this.imagem.addEventListener('mousemove', this.desenharSelecao.bind(this));
        this.imagem.addEventListener('mouseup', this.finalizarSelecao.bind(this));
        
        this.imagem.addEventListener('touchstart', this.iniciarSelecaoTouch.bind(this));
        this.imagem.addEventListener('touchmove', this.desenharSelecaoTouch.bind(this));
        this.imagem.addEventListener('touchend', this.finalizarSelecaoTouch.bind(this));
    }
    
    getMousePos(e) {
        const rect = this.imagem.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    getTouchPos(e) {
        const rect = this.imagem.getBoundingClientRect();
        const touch = e.touches[0];
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
    }
    
    iniciarSelecao(e) {
        e.preventDefault();
        const pos = this.getMousePos(e);
        this.coordenadas = { x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y };
        this.isDrawing = true;
        this.atualizarSelecao();
    }
    
    iniciarSelecaoTouch(e) {
        e.preventDefault();
        const pos = this.getTouchPos(e);
        this.coordenadas = { x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y };
        this.isDrawing = true;
        this.atualizarSelecao();
    }
    
    desenharSelecao(e) {
        if (!this.isDrawing) return;
        e.preventDefault();
        const pos = this.getMousePos(e);
        this.coordenadas.x2 = pos.x;
        this.coordenadas.y2 = pos.y;
        this.atualizarSelecao();
    }
    
    desenharSelecaoTouch(e) {
        if (!this.isDrawing) return;
        e.preventDefault();
        const pos = this.getTouchPos(e);
        this.coordenadas.x2 = pos.x;
        this.coordenadas.y2 = pos.y;
        this.atualizarSelecao();
    }
    
    finalizarSelecao(e) {
        if (!this.isDrawing) return;
        e.preventDefault();
        this.isDrawing = false;
        this.salvarArea();
    }
    
    finalizarSelecaoTouch(e) {
        if (!this.isDrawing) return;
        e.preventDefault();
        this.isDrawing = false;
        this.salvarArea();
    }
    
    atualizarSelecao() {
        const x = Math.min(this.coordenadas.x1, this.coordenadas.x2);
        const y = Math.min(this.coordenadas.y1, this.coordenadas.y2);
        const width = Math.abs(this.coordenadas.x2 - this.coordenadas.x1);
        const height = Math.abs(this.coordenadas.y2 - this.coordenadas.y1);
        
        this.selecao.style.left = x + 'px';
        this.selecao.style.top = y + 'px';
        this.selecao.style.width = width + 'px';
        this.selecao.style.height = height + 'px';
        this.selecao.style.display = 'block';
        
        document.getElementById('coordenadas-area').value = 
            `[${Math.round(x)}, ${Math.round(y)}, ${Math.round(x + width)}, ${Math.round(y + height)}]`;
    }
    
    salvarArea() {
        const x = parseInt(this.selecao.style.left);
        const y = parseInt(this.selecao.style.top);
        const width = parseInt(this.selecao.style.width);
        const height = parseInt(this.selecao.style.height);
        
        const area = [x, y, x + width, y + height];
        
        fetch('/api/salvar_area_foto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ area: area })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Área da foto salva com sucesso!');
            }
        })
        .catch(error => {
            console.error('Erro ao salvar área:', error);
            alert('Erro ao salvar área da foto.');
        });
    }
    
    limparSelecao() {
        this.selecao.style.display = 'none';
        this.coordenadas = { x1: 0, y1: 0, x2: 0, y2: 0 };
        document.getElementById('coordenadas-area').value = '';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('area-selecao-container') && document.getElementById('preview-imagem')) {
        window.seletorArea = new AreaSelecao('area-selecao-container', 'preview-imagem');
    }
    
    const uploadInputs = document.querySelectorAll('input[type="file"]');
    uploadInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0].name;
            const label = this.nextElementSibling;
            if (label && label.classList.contains('custom-file-label')) {
                label.textContent = fileName;
            }
        });
    });
    
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const required = this.querySelectorAll('[required]');
            let isValid = true;
            
            required.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Por favor, preencha todos os campos obrigatórios.');
            }
        });
    });
});

function limparSelecao() {
    if (window.seletorArea) {
        window.seletorArea.limparSelecao();
    }
}

function salvarCampos() {
    // Implementar se necessário
}

function testarPSD(tipo) {
    const input = document.querySelector(`input[name="${tipo}_psd"]`);
    if (!input || !input.files[0]) {
        alert('Selecione um arquivo PSD primeiro.');
        return;
    }
    
    const formData = new FormData();
    formData.append('psd', input.files[0]);
    
    fetch('/api/testar_psd', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const statusDiv = document.getElementById(`status-${tipo}`);
        if (statusDiv) {
            statusDiv.className = data.success ? 'status-ok' : 'status-erro';
            statusDiv.textContent = data.message;
        }
    });
}

function previewFoto(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('foto-preview');
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
        }
        reader.readAsDataURL(input.files[0]);
    }
}