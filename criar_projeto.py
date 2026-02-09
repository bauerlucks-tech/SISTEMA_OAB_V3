import os

# Estrutura de arquivos
files = {
    "app.py": """
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import sqlite3
import os
import json
from werkzeug.utils import secure_filename
from psd_manager import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sistema_oab_secret'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configurações de pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PSD = os.path.join(BASE_DIR, 'static', 'psd_base')
UPLOAD_FOTOS = os.path.join(BASE_DIR, 'static', 'fotos')
GERADOS = os.path.join(BASE_DIR, 'static', 'gerados')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

# Criar pastas se não existirem
for pasta in [UPLOAD_PSD, UPLOAD_FOTOS, GERADOS]:
    os.makedirs(pasta, exist_ok=True)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'psd', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sistema_config (
            id INTEGER PRIMARY KEY,
            psd_frente TEXT,
            psd_verso TEXT,
            area_foto TEXT,
            atualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS campos_config (
            id INTEGER PRIMARY KEY,
            tipo TEXT,
            nome_original TEXT,
            nome_campo TEXT,
            posicao TEXT,
            editavel INTEGER DEFAULT 1
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM sistema_config WHERE id = 1")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO sistema_config (id) VALUES (1)")
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    frente = config[0] if config and config[0] else None
    verso = config[1] if config and config[1] else None
    
    conn.close()
    
    return render_template('admin.html', frente=frente, verso=verso)

@app.route('/upload_psd', methods=['POST'])
def upload_psd():
    tipo = request.form.get('tipo')
    
    if 'psd' not in request.files:
        return redirect(request.url)
    
    file = request.files['psd']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = f"{tipo}.psd"
        filepath = os.path.join(UPLOAD_PSD, filename)
        file.save(filepath)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if tipo == 'frente':
            c.execute("UPDATE sistema_config SET psd_frente = ? WHERE id = 1", (filename,))
        else:
            c.execute("UPDATE sistema_config SET psd_verso = ? WHERE id = 1", (filename,))
        
        conn.commit()
        conn.close()
        
        try:
            if tipo == 'frente':
                camadas = extrair_camadas_psd(filepath)
                salvar_camadas_config(camadas, 'frente')
        except Exception as e:
            print(f"Erro ao processar PSD: {e}")
    
    return redirect(url_for('index'))

@app.route('/configurar')
def configurar():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    if not config or not all(config):
        conn.close()
        return "Por favor, envie ambos PSDs (frente e verso) antes de configurar."
    
    c.execute("SELECT * FROM campos_config WHERE tipo = 'frente'")
    campos_frente = c.fetchall()
    
    c.execute("SELECT * FROM campos_config WHERE tipo = 'verso'")
    campos_verso = c.fetchall()
    
    conn.close()
    
    frente_path = os.path.join(UPLOAD_PSD, config[0])
    preview_path = None
    if os.path.exists(frente_path):
        preview_path = gerar_preview_psd(frente_path)
    
    return render_template('configurar.html', 
                         campos_frente=campos_frente,
                         campos_verso=campos_verso,
                         preview=preview_path)

@app.route('/api/salvar_area_foto', methods=['POST'])
def salvar_area_foto():
    data = request.json
    area = data.get('area')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sistema_config SET area_foto = ? WHERE id = 1", (json.dumps(area),))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/salvar_campos', methods=['POST'])
def salvar_campos():
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("DELETE FROM campos_config")
    
    for campo in data.get('campos', []):
        c.execute('''
            INSERT INTO campos_config (tipo, nome_original, nome_campo, posicao, editavel)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            campo['tipo'],
            campo['nome_original'],
            campo['nome_campo'],
            json.dumps(campo['posicao']),
            campo.get('editavel', 1)
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/visualizar')
def visualizar():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT psd_frente FROM sistema_config WHERE id = 1")
    psd_frente = c.fetchone()[0]
    conn.close()
    
    if not psd_frente:
        return redirect(url_for('index'))
    
    psd_path = os.path.join(UPLOAD_PSD, psd_frente)
    preview_path = gerar_preview_psd(psd_path)
    
    return render_template('visualizar.html', preview=preview_path)

@app.route('/gerar')
def gerar():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT * FROM campos_config WHERE editavel = 1")
    campos = c.fetchall()
    
    conn.close()
    
    return render_template('gerar.html', campos=campos)

@app.route('/processar_geracao', methods=['POST'])
def processar_geracao():
    dados = {}
    for key, value in request.form.items():
        if key != 'foto':
            dados[key] = value
    
    foto = request.files.get('foto')
    foto_path = None
    if foto and allowed_file(foto.filename):
        foto_filename = secure_filename(foto.filename)
        foto_path = os.path.join(UPLOAD_FOTOS, foto_filename)
        foto.save(foto_path)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    c.execute("SELECT * FROM campos_config")
    campos_config = c.fetchall()
    
    conn.close()
    
    if not config or not config[0] or not config[1]:
        return "Erro: PSDs não configurados."
    
    frente_path = os.path.join(UPLOAD_PSD, config[0])
    verso_path = os.path.join(UPLOAD_PSD, config[1])
    
    area_foto = json.loads(config[2]) if config[2] else None
    
    try:
        frente_output = os.path.join(GERADOS, 'frente_gerada.png')
        verso_output = os.path.join(GERADOS, 'verso_gerado.png')
        
        gerar_carteirinha(
            frente_path,
            dados,
            campos_config,
            frente_output,
            foto_path,
            area_foto
        )
        
        gerar_carteirinha(
            verso_path,
            dados,
            campos_config,
            verso_output
        )
        
        return render_template('resultado.html', 
                             frente=frente_output.replace('static/', ''),
                             verso=verso_output.replace('static/', ''))
    
    except Exception as e:
        return f"Erro ao gerar carteirinha: {str(e)}"

@app.route('/download/<tipo>')
def download(tipo):
    if tipo == 'frente':
        filepath = os.path.join(GERADOS, 'frente_gerada.png')
    else:
        filepath = os.path.join(GERADOS, 'verso_gerado.png')
    
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
""",
    
    "psd_manager.py": """
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
import os
import json
import sqlite3

def extrair_camadas_psd(psd_path):
    psd = PSDImage.open(psd_path)
    camadas = []
    
    for layer in psd.descendants():
        if layer.is_visible():
            bbox = layer.bbox
            camada_info = {
                'nome': layer.name,
                'tipo': layer.kind,
                'posicao': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                'texto': layer.text if layer.kind == 'type' else None
            }
            camadas.append(camada_info)
    
    return camadas

def salvar_camadas_config(camadas, tipo):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM campos_config WHERE tipo = ?", (tipo,))
    
    for camada in camadas:
        if camada['tipo'] == 'type':
            c.execute('''
                INSERT INTO campos_config (tipo, nome_original, nome_campo, posicao, editavel)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                tipo,
                camada['nome'],
                camada['nome'],
                json.dumps(camada['posicao']),
                1
            ))
    
    conn.commit()
    conn.close()

def gerar_preview_psd(psd_path, tamanho_max=(800, 800)):
    psd = PSDImage.open(psd_path)
    img = psd.composite()
    
    if img.width > tamanho_max[0] or img.height > tamanho_max[1]:
        img.thumbnail(tamanho_max, Image.Resampling.LANCZOS)
    
    preview_dir = os.path.join('static', 'previews')
    os.makedirs(preview_dir, exist_ok=True)
    
    preview_path = os.path.join(preview_dir, 'preview.png')
    img.save(preview_path)
    
    return preview_path.replace('\\', '/')

def gerar_carteirinha(psd_path, dados, campos_config, output_path, foto_path=None, area_foto=None):
    psd = PSDImage.open(psd_path)
    
    if psd_path.endswith('frente.psd'):
        base_img = psd.composite().convert("RGBA")
    else:
        base_img = psd.composite().convert("RGBA")
    
    draw_img = Image.new("RGBA", base_img.size)
    draw = ImageDraw.Draw(draw_img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    for campo in campos_config:
        campo_id, tipo, nome_original, nome_campo, posicao_json, editavel = campo
        
        if not editavel:
            continue
        
        valor = dados.get(nome_campo, '')
        if not valor:
            continue
        
        posicao = json.loads(posicao_json)
        x, y = posicao[0], posicao[1]
        
        draw.text((x, y), str(valor), fill=(0, 0, 0, 255), font=font)
    
    if foto_path and area_foto and psd_path.endswith('frente.psd'):
        try:
            foto = Image.open(foto_path).convert("RGBA")
            
            x1, y1, x2, y2 = area_foto
            largura = x2 - x1
            altura = y2 - y1
            
            foto = foto.resize((largura, altura))
            
            base_img.paste(foto, (x1, y1), foto)
        except Exception as e:
            print(f"Erro ao inserir foto: {e}")
    
    resultado = Image.alpha_composite(base_img, draw_img)
    
    resultado = resultado.convert("RGB")
    
    resultado.save(output_path)
    
    return output_path

def testar_psd(psd_path):
    try:
        psd = PSDImage.open(psd_path)
        return True, f"PSD aberto com sucesso. Dimensões: {psd.width}x{psd.height}"
    except Exception as e:
        return False, f"Erro ao abrir PSD: {str(e)}"
""",
    
    "requirements.txt": """
flask==2.3.3
psd-tools==1.9.28
pillow==10.1.0
gunicorn==21.2.0
""",
    
    "Procfile": """
web: gunicorn app:app
""",
    
    "runtime.txt": """
python-3.9.0
""",
    
    "static/css/style.css": """
:root {
    --azul-oab: #003366;
    --dourado-oab: #D4AF37;
    --cinza-claro: #f8f9fa;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: var(--cinza-claro);
}

.navbar-oab {
    background: linear-gradient(135deg, var(--azul-oab) 0%, #004080 100%);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
    color: white !important;
    font-weight: bold;
    font-size: 1.5rem;
}

.card-oab {
    border: 2px solid var(--dourado-oab);
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s;
}

.card-oab:hover {
    transform: translateY(-5px);
}

.btn-oab {
    background: linear-gradient(135deg, var(--azul-oab) 0%, #004080 100%);
    color: white;
    border: none;
    padding: 10px 25px;
    border-radius: 5px;
    font-weight: bold;
    transition: all 0.3s;
}

.btn-oab:hover {
    background: linear-gradient(135deg, #004080 0%, #0055a5 100%);
    color: white;
    transform: scale(1.05);
}

.btn-dourado {
    background-color: var(--dourado-oab);
    color: var(--azul-oab);
    border: none;
    padding: 10px 25px;
    border-radius: 5px;
    font-weight: bold;
}

.area-selecao {
    position: relative;
    border: 2px dashed var(--azul-oab);
    cursor: crosshair;
}

.selecao-foto {
    position: absolute;
    border: 2px solid var(--dourado-oab);
    background-color: rgba(212, 175, 55, 0.2);
}

.status-psd {
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}

.status-ok {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.status-erro {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.campo-editavel {
    background-color: #e8f4fd;
    border-left: 4px solid var(--azul-oab);
    padding: 10px;
    margin: 5px 0;
}

.preview-psd {
    max-width: 100%;
    border: 1px solid #ddd;
    border-radius: 5px;
}

.resultado-img {
    max-width: 400px;
    border: 3px solid var(--dourado-oab);
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}
""",
    
    "static/js/script.js": """
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
""",
    
    "templates/admin.html": """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema OAB - Administração</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-oab">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-id-card"></i> Sistema OAB - Gerador de Carteirinhas
            </a>
            <div class="navbar-text text-white">
                <i class="fas fa-user-shield"></i> Modo Administrador
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <h2 class="card-title text-azul-oab">
                            <i class="fas fa-cogs"></i> Configuração do Sistema
                        </h2>
                        <p class="card-text">
                            Configure os PSDs base (frente e verso) para gerar carteirinhas automaticamente.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card card-oab">
                    <div class="card-header bg-azul-oab text-white">
                        <i class="fas fa-file-image"></i> PSD Frente
                    </div>
                    <div class="card-body">
                        {% if frente %}
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i> PSD carregado: {{ frente }}
                            </div>
                        {% else %}
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i> Nenhum PSD carregado
                            </div>
                        {% endif %}
                        
                        <form action="{{ url_for('upload_psd') }}" method="post" enctype="multipart/form-data">
                            <input type="hidden" name="tipo" value="frente">
                            <div class="mb-3">
                                <label for="frente_psd" class="form-label">Selecione o PSD da Frente:</label>
                                <input class="form-control" type="file" name="psd" id="frente_psd" accept=".psd" required>
                            </div>
                            <button type="submit" class="btn btn-oab w-100">
                                <i class="fas fa-upload"></i> Upload PSD Frente
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card card-oab">
                    <div class="card-header bg-azul-oab text-white">
                        <i class="fas fa-file-image"></i> PSD Verso
                    </div>
                    <div class="card-body">
                        {% if verso %}
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i> PSD carregado: {{ verso }}
                            </div>
                        {% else %}
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i> Nenhum PSD carregado
                            </div>
                        {% endif %}
                        
                        <form action="{{ url_for('upload_psd') }}" method="post" enctype="multipart/form-data">
                            <input type="hidden" name="tipo" value="verso">
                            <div class="mb-3">
                                <label for="verso_psd" class="form-label">Selecione o PSD do Verso:</label>
                                <input class="form-control" type="file" name="psd" id="verso_psd" accept=".psd" required>
                            </div>
                            <button type="submit" class="btn btn-oab w-100">
                                <i class="fas fa-upload"></i> Upload PSD Verso
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <h4>Próximos Passos</h4>
                        <div class="d-grid gap-2 d-md-block mt-3">
                            {% if frente and verso %}
                                <a href="{{ url_for('configurar') }}" class="btn btn-dourado btn-lg mx-2">
                                    <i class="fas fa-sliders-h"></i> Configurar Campos
                                </a>
                                <a href="{{ url_for('visualizar') }}" class="btn btn-oab btn-lg mx-2">
                                    <i class="fas fa-crop"></i> Definir Área da Foto
                                </a>
                            {% else %}
                                <button class="btn btn-secondary btn-lg mx-2" disabled>
                                    <i class="fas fa-sliders-h"></i> Configurar Campos (antes envie os PSDs)
                                </button>
                            {% endif %}
                            
                            <a href="{{ url_for('gerar') }}" class="btn btn-success btn-lg mx-2">
                                <i class="fas fa-id-card"></i> Gerar Carteirinha
                            </a>
                        </div>
                        
                        {% if frente and verso %}
                            <div class="mt-4">
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle"></i> Ambos PSDs carregados! Clique em "Configurar Campos" para continuar.
                                </div>
                            </div>
                        {% else %}
                            <div class="mt-4">
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle"></i> É necessário carregar ambos PSDs (frente e verso) antes de continuar.
                                </div>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <footer class="mt-5 text-center text-muted">
            <p>Sistema OAB - Gerador de Carteirinhas | Versão 2.0</p>
            <p><small>Desenvolvido para automatização de carteirinhas profissionais</small></p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
""",
    
    "templates/configurar.html": """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configurar Campos - Sistema OAB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-oab">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-id-card"></i> Sistema OAB
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link text-white" href="/">
                    <i class="fas fa-home"></i> Voltar ao Início
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="card card-oab mb-4">
                    <div class="card-header bg-azul-oab text-white">
                        <i class="fas fa-sliders-h"></i> Configuração dos Campos
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            Configure os campos editáveis que aparecerão no formulário de geração.
                            O sistema detectou automaticamente as camadas de texto dos PSDs.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header">
                        <i class="fas fa-eye"></i> Preview do Layout
                    </div>
                    <div class="card-body text-center">
                        {% if preview %}
                            <img src="{{ url_for('static', filename=preview.replace('static/', '')) }}" 
                                 class="preview-psd" 
                                 alt="Preview do PSD">
                        {% else %}
                            <div class="alert alert-warning">
                                Preview não disponível. Certifique-se de que os PSDs foram carregados.
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header bg-success text-white">
                        <i class="fas fa-id-card"></i> Campos da Frente
                    </div>
                    <div class="card-body">
                        <div id="lista-campos-frente">
                            {% for campo in campos_frente %}
                            <div class="campo-editavel mb-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>{{ campo[2] }}</strong>
                                        <small class="text-muted">({{ campo[3] }})</small>
                                        <br>
                                        <small>Posição: {{ campo[4] }}</small>
                                    </div>
                                    <div>
                                        <div class="form-check form-switch">
                                            <input class="form-check-input" 
                                                   type="checkbox" 
                                                   id="editavel_{{ campo[0] }}"
                                                   {% if campo[5] == 1 %}checked{% endif %}
                                                   onchange="atualizarEditavel({{ campo[0] }}, this.checked)">
                                            <label class="form-check-label" for="editavel_{{ campo[0] }}">
                                                Editável
                                            </label>
                                        </div>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <input type="text" 
                                           class="form-control form-control-sm" 
                                           placeholder="Nome do campo no formulário"
                                           value="{{ campo[3] }}"
                                           onchange="atualizarNomeCampo({{ campo[0] }}, this.value)">
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header bg-info text-white">
                        <i class="fas fa-id-card"></i> Campos do Verso
                    </div>
                    <div class="card-body">
                        <div id="lista-campos-verso">
                            {% for campo in campos_verso %}
                            <div class="campo-editavel mb-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>{{ campo[2] }}</strong>
                                        <small class="text-muted">({{ campo[3] }})</small>
                                        <br>
                                        <small>Posição: {{ campo[4] }}</small>
                                    </div>
                                    <div>
                                        <div class="form-check form-switch">
                                            <input class="form-check-input" 
                                                   type="checkbox" 
                                                   id="editavel_{{ campo[0] }}"
                                                   {% if campo[5] == 1 %}checked{% endif %}
                                                   onchange="atualizarEditavel({{ campo[0] }}, this.checked)">
                                            <label class="form-check-label" for="editavel_{{ campo[0] }}">
                                                Editável
                                            </label>
                                        </div>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <input type="text" 
                                           class="form-control form-control-sm" 
                                           placeholder="Nome do campo no formulário"
                                           value="{{ campo[3] }}"
                                           onchange="atualizarNomeCampo({{ campo[0] }}, this.value)">
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-5">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <div class="d-grid gap-2 d-md-block">
                            <button class="btn btn-dourado btn-lg mx-2" onclick="salvarConfiguracao()">
                                <i class="fas fa-save"></i> Salvar Configuração
                            </button>
                            <a href="{{ url_for('visualizar') }}" class="btn btn-oab btn-lg mx-2">
                                <i class="fas fa-crop"></i> Definir Área da Foto
                            </a>
                            <a href="{{ url_for('gerar') }}" class="btn btn-success btn-lg mx-2">
                                <i class="fas fa-play"></i> Ir para Geração
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
    <script>
        function atualizarEditavel(id, editavel) {
            fetch('/api/atualizar_campo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: id,
                    editavel: editavel ? 1 : 0
                })
            });
        }
        
        function atualizarNomeCampo(id, nome) {
            fetch('/api/atualizar_campo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: id,
                    nome_campo: nome
                })
            });
        }
        
        function salvarConfiguracao() {
            const campos = [];
            
            document.querySelectorAll('#lista-campos-frente .campo-editavel').forEach(item => {
                const id = item.querySelector('input[type="checkbox"]').id.replace('editavel_', '');
                const editavel = item.querySelector('input[type="checkbox"]').checked;
                const nomeCampo = item.querySelector('input[type="text"]').value;
                
                campos.push({
                    id: parseInt(id),
                    editavel: editavel,
                    nome_campo: nomeCampo,
                    tipo: 'frente'
                });
            });
            
            document.querySelectorAll('#lista-campos-verso .campo-editavel').forEach(item => {
                const id = item.querySelector('input[type="checkbox"]').id.replace('editavel_', '');
                const editavel = item.querySelector('input[type="checkbox"]').checked;
                const nomeCampo = item.querySelector('input[type="text"]').value;
                
                campos.push({
                    id: parseInt(id),
                    editavel: editavel,
                    nome_campo: nomeCampo,
                    tipo: 'verso'
                });
            });
            
            fetch('/api/salvar_config_campos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ campos: campos })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Configuração salva com sucesso!');
                } else {
                    alert('Erro ao salvar configuração.');
                }
            });
        }
    </script>
</body>
</html>
""",
    
    "templates/visualizar.html": """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Definir Área da Foto - Sistema OAB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-oab">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-id-card"></i> Sistema OAB
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link text-white" href="/configurar">
                    <i class="fas fa-arrow-left"></i> Voltar
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header bg-azul-oab text-white">
                        <i class="fas fa-crop"></i> Definir Área da Foto 3x4
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            Clique e arraste na imagem abaixo para selecionar a área onde a foto 3x4 será inserida.
                            A área selecionada será salva automaticamente.
                        </p>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i> 
                            Dica: A foto será redimensionada automaticamente para caber na área selecionada.
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <div id="area-selecao-container" class="area-selecao d-inline-block">
                            {% if preview %}
                                <img id="preview-imagem" 
                                     src="{{ url_for('static', filename=preview.replace('static/', '')) }}" 
                                     alt="Preview do PSD"
                                     class="preview-psd">
                            {% else %}
                                <div class="alert alert-warning">
                                    Preview não disponível.
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="mt-3">
                            <button class="btn btn-oab" onclick="limparSelecao()">
                                <i class="fas fa-times"></i> Limpar Seleção
                            </button>
                        </div>
                        
                        <div class="mt-3">
                            <label for="coordenadas-area" class="form-label">Coordenadas da área selecionada:</label>
                            <input type="text" 
                                   id="coordenadas-area" 
                                   class="form-control" 
                                   readonly
                                   placeholder="Clique e arraste na imagem acima">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <div class="d-grid gap-2 d-md-block">
                            <a href="{{ url_for('configurar') }}" class="btn btn-secondary btn-lg mx-2">
                                <i class="fas fa-arrow-left"></i> Voltar
                            </a>
                            <a href="{{ url_for('gerar') }}" class="btn btn-success btn-lg mx-2">
                                <i class="fas fa-play"></i> Continuar para Geração
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
""",
    
    "templates/gerar.html": """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerar Carteirinha - Sistema OAB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-oab">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-id-card"></i> Sistema OAB
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link text-white" href="/configurar">
                    <i class="fas fa-cog"></i> Configuração
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header bg-success text-white">
                        <i class="fas fa-id-card"></i> Gerar Nova Carteirinha
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            Preencha os dados abaixo para gerar uma nova carteirinha.
                            A foto 3x4 será automaticamente inserida na área definida anteriormente.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <form action="{{ url_for('processar_geracao') }}" method="post" enctype="multipart/form-data">
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card card-oab">
                        <div class="card-header">
                            <i class="fas fa-user"></i> Dados Pessoais
                        </div>
                        <div class="card-body">
                            {% for campo in campos %}
                                {% if campo[1] == 'frente' %}
                                    <div class="mb-3">
                                        <label for="{{ campo[3] }}" class="form-label">{{ campo[2] }}</label>
                                        <input type="text" 
                                               class="form-control" 
                                               id="{{ campo[3] }}" 
                                               name="{{ campo[3] }}"
                                               placeholder="Digite {{ campo[2] }}"
                                               required>
                                    </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="card card-oab">
                        <div class="card-header">
                            <i class="fas fa-camera"></i> Foto 3x4
                        </div>
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <label for="foto" class="form-label">Selecione uma foto 3x4:</label>
                                <input type="file" 
                                       class="form-control" 
                                       id="foto" 
                                       name="foto"
                                       accept="image/*"
                                       onchange="previewFoto(this)"
                                       required>
                                <div class="form-text">
                                    A foto será redimensionada automaticamente para 3x4 cm.
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <img id="foto-preview" 
                                     src="" 
                                     alt="Preview da foto" 
                                     class="preview-psd"
                                     style="display: none; max-width: 200px;">
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-12">
                    <div class="card card-oab">
                        <div class="card-header">
                            <i class="fas fa-id-card"></i> Dados do Verso
                        </div>
                        <div class="card-body">
                            {% for campo in campos %}
                                {% if campo[1] == 'verso' %}
                                    <div class="mb-3">
                                        <label for="{{ campo[3] }}" class="form-label">{{ campo[2] }}</label>
                                        <input type="text" 
                                               class="form-control" 
                                               id="{{ campo[3] }}" 
                                               name="{{ campo[3] }}"
                                               placeholder="Digite {{ campo[2] }}"
                                               {% if campo[5] == 1 %}required{% endif %}>
                                    </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-12">
                    <div class="card card-oab">
                        <div class="card-body text-center">
                            <button type="submit" class="btn btn-success btn-lg">
                                <i class="fas fa-magic"></i> Gerar Carteirinha
                            </button>
                            <a href="/" class="btn btn-secondary btn-lg">
                                <i class="fas fa-times"></i> Cancelar
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </form>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
""",
    
    "templates/resultado.html": """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resultado - Sistema OAB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-oab">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-id-card"></i> Sistema OAB
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link text-white" href="/gerar">
                    <i class="fas fa-plus"></i> Nova Carteirinha
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-header bg-success text-white">
                        <i class="fas fa-check-circle"></i> Carteirinha Gerada com Sucesso!
                    </div>
                    <div class="card-body text-center">
                        <p class="card-text">
                            Sua carteirinha foi gerada com sucesso. Você pode visualizar, baixar ou gerar uma nova.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card card-oab">
                    <div class="card-header">
                        <i class="fas fa-id-card"></i> Frente
                    </div>
                    <div class="card-body text-center">
                        <img src="{{ url_for('static', filename=frente) }}" 
                             class="resultado-img mb-3" 
                             alt="Frente da carteirinha">
                        <br>
                        <a href="{{ url_for('download', tipo='frente') }}" 
                           class="btn btn-oab">
                            <i class="fas fa-download"></i> Baixar Frente
                        </a>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card card-oab">
                    <div class="card-header">
                        <i class="fas fa-id-card"></i> Verso
                    </div>
                    <div class="card-body text-center">
                        <img src="{{ url_for('static', filename=verso) }}" 
                             class="resultado-img mb-3" 
                             alt="Verso da carteirinha">
                        <br>
                        <a href="{{ url_for('download', tipo='verso') }}" 
                           class="btn btn-oab">
                            <i class="fas fa-download"></i> Baixar Verso
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card card-oab">
                    <div class="card-body text-center">
                        <div class="d-grid gap-2 d-md-block">
                            <a href="/gerar" class="btn btn-success btn-lg mx-2">
                                <i class="fas fa-plus"></i> Gerar Outra Carteirinha
                            </a>
                            <a href="/" class="btn btn-secondary btn-lg mx-2">
                                <i class="fas fa-home"></i> Voltar ao Início
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
}

# Criar diretórios
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Criar arquivos
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())

print("Projeto criado com sucesso!")