from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import sqlite3
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sistema-oab-secreto-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configurações
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

# Criar pastas necessárias
def criar_pastas():
    pastas = [
        'static/psd_base',
        'static/fotos', 
        'static/gerados',
        'static/previews',
        'static/css',
        'static/js',
        'templates'
    ]
    for pasta in pastas:
        os.makedirs(pasta, exist_ok=True)

criar_pastas()

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Configuração do sistema
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY,
            psd_frente TEXT,
            psd_verso TEXT,
            area_foto TEXT,
            atualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Campos editáveis
    c.execute('''
        CREATE TABLE IF NOT EXISTS campos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_original TEXT,
            nome_exibicao TEXT,
            tipo TEXT,
            editavel INTEGER DEFAULT 1,
            posicao TEXT
        )
    ''')
    
    # Histórico de gerações
    c.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            rg TEXT,
            foto TEXT,
            frente TEXT,
            verso TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir configuração padrão
    c.execute("INSERT OR IGNORE INTO config (id) VALUES (1)")
    
    conn.commit()
    conn.close()

init_db()

# ============ ROTAS PRINCIPAIS ============

@app.route('/')
def index():
    """Página inicial"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM config WHERE id = 1")
    config = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM historico")
    total = c.fetchone()[0]
    
    c.execute("SELECT nome, rg, data FROM historico ORDER BY id DESC LIMIT 5")
    historico = c.fetchall()
    
    conn.close()
    
    return render_template('admin.html',
                         frente=config[0] if config else None,
                         verso=config[1] if config else None,
                         area_foto=config[2] if config else None,
                         total_geracoes=total,
                         historico=historico)

@app.route('/upload_psd', methods=['POST'])
def upload_psd():
    """Upload de PSDs"""
    tipo = request.form.get('tipo')
    file = request.files.get('psd')
    
    if file and file.filename.endswith('.psd'):
        filename = f"{tipo}.psd"
        filepath = os.path.join('static', 'psd_base', filename)
        file.save(filepath)
        
        # Atualizar banco
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if tipo == 'frente':
            c.execute("UPDATE config SET psd_frente = ? WHERE id = 1", (filename,))
        else:
            c.execute("UPDATE config SET psd_verso = ? WHERE id = 1", (filename,))
        
        conn.commit()
        conn.close()
        
        # Criar preview
        try:
            from psd_tools import PSDImage
            from PIL import Image
            
            psd = PSDImage.open(filepath)
            img = psd.composite()
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            preview_path = os.path.join('static', 'previews', f'preview_{tipo}.png')
            img.save(preview_path)
        except Exception as e:
            print(f"Erro ao criar preview: {e}")
    
    return redirect('/')

@app.route('/configurar')
def configurar():
    """Configuração de campos"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar se PSDs foram carregados
    c.execute("SELECT psd_frente, psd_verso FROM config WHERE id = 1")
    psds = c.fetchone()
    
    if not psds or not all(psds):
        conn.close()
        return render_template('erro.html', 
                             mensagem="Carregue ambos os PSDs (frente e verso) antes de configurar.")
    
    # Obter campos existentes
    c.execute("SELECT * FROM campos ORDER BY tipo, id")
    campos = c.fetchall()
    
    # Separar por tipo
    campos_frente = [c for c in campos if c[3] == 'frente']
    campos_verso = [c for c in campos if c[3] == 'verso']
    
    conn.close()
    
    return render_template('configurar.html',
                         campos_frente=campos_frente,
                         campos_verso=campos_verso)

@app.route('/visualizar')
def visualizar():
    """Seleção da área da foto"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente FROM config WHERE id = 1")
    psd_frente = c.fetchone()
    
    if not psd_frente or not psd_frente[0]:
        conn.close()
        return redirect('/')
    
    # Verificar se preview existe
    preview_path = f'static/previews/preview_frente.png'
    preview_existe = os.path.exists(preview_path)
    
    # Obter área configurada
    c.execute("SELECT area_foto FROM config WHERE id = 1")
    area_foto = c.fetchone()[0]
    
    conn.close()
    
    return render_template('visualizar.html',
                         preview=preview_path if preview_existe else None,
                         area_foto=area_foto)

@app.route('/api/salvar_area', methods=['POST'])
def salvar_area():
    """Salvar área da foto (2 cliques)"""
    data = request.json
    x1 = data.get('x1')
    y1 = data.get('y1')
    x2 = data.get('x2')
    y2 = data.get('y2')
    
    if None in [x1, y1, x2, y2]:
        return jsonify({'success': False, 'error': 'Coordenadas inválidas'})
    
    area = json.dumps([x1, y1, x2, y2])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE config SET area_foto = ? WHERE id = 1", (area,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/salvar_campo', methods=['POST'])
def salvar_campo():
    """Salvar configuração de campo"""
    data = request.json
    campo_id = data.get('id')
    nome_exibicao = data.get('nome_exibicao')
    editavel = data.get('editavel')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if nome_exibicao:
        c.execute("UPDATE campos SET nome_exibicao = ? WHERE id = ?", (nome_exibicao, campo_id))
    
    if editavel is not None:
        c.execute("UPDATE campos SET editavel = ? WHERE id = ?", (editavel, campo_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/gerar')
def gerar():
    """Página para gerar carteirinha"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar configuração completa
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM config WHERE id = 1")
    config = c.fetchone()
    
    if not config or not config[0] or not config[1] or not config[2]:
        conn.close()
        return render_template('erro.html',
                             mensagem="Configure os PSDs e a área da foto antes de gerar.")
    
    # Obter campos editáveis
    c.execute("SELECT nome_exibicao FROM campos WHERE editavel = 1")
    campos = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    # Se não houver campos, usar padrão
    if not campos:
        campos = ['Nome', 'RG', 'CPF', 'Matrícula']
    
    return render_template('gerar.html', campos=campos)

@app.route('/processar', methods=['POST'])
def processar():
    """Processar geração da carteirinha"""
    # Obter dados do formulário
    dados = {}
    for key, value in request.form.items():
        if key != 'foto':
            dados[key] = value
    
    # Processar foto
    foto = request.files.get('foto')
    foto_nome = None
    if foto and foto.filename:
        ext = foto.filename.split('.')[-1].lower()
        if ext in ['png', 'jpg', 'jpeg', 'gif']:
            foto_nome = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            foto_path = os.path.join('static', 'fotos', foto_nome)
            foto.save(foto_path)
    
    # Obter configurações
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM config WHERE id = 1")
    config = c.fetchone()
    
    # Gerar nomes de arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    frente_nome = f'frente_{timestamp}.png'
    verso_nome = f'verso_{timestamp}.png'
    
    frente_path = os.path.join('static', 'gerados', frente_nome)
    verso_path = os.path.join('static', 'gerados', verso_nome)
    
    # Criar imagens (simulação)
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Frente com foto
        img = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Adicionar texto
        y = 50
        for campo, valor in dados.items():
            draw.text((50, y), f"{campo}: {valor}", fill='black')
            y += 40
        
        # Adicionar área da foto
        if config[2]:
            area = json.loads(config[2])
            x1, y1, x2, y2 = area
            draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
        
        img.save(frente_path)
        
        # Verso (simples)
        img = Image.new('RGB', (600, 400), color='lightgray')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Verso da Carteirinha", fill='black')
        draw.text((50, 100), "Sistema OAB", fill='black')
        img.save(verso_path)
        
    except Exception as e:
        # Arquivos vazios em caso de erro
        open(frente_path, 'w').close()
        open(verso_path, 'w').close()
    
    # Salvar no histórico
    nome = dados.get('Nome', 'Sem nome')
    rg = dados.get('RG', 'Sem RG')
    
    c.execute('''
        INSERT INTO historico (nome, rg, foto, frente, verso)
        VALUES (?, ?, ?, ?, ?)
    ''', (nome, rg, foto_nome, frente_nome, verso_nome))
    
    conn.commit()
    conn.close()
    
    return render_template('resultado.html',
                         nome=nome,
                         rg=rg,
                         frente=frente_nome,
                         verso=verso_nome)

@app.route('/download/<arquivo>')
def download(arquivo):
    """Download de arquivo gerado"""
    return send_file(os.path.join('static', 'gerados', arquivo), as_attachment=True)

@app.route('/api/detectar_campos/<tipo>')
def detectar_campos(tipo):
    """Detectar campos do PSD"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute(f"SELECT psd_{tipo} FROM config WHERE id = 1")
    psd_nome = c.fetchone()
    
    if not psd_nome or not psd_nome[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'PSD não encontrado'})
    
    # Simular detecção (em produção usar psd-tools)
    campos_simulados = [
        {'nome': 'Nome', 'posicao': '[100, 150, 300, 200]'},
        {'nome': 'RG', 'posicao': '[100, 220, 300, 270]'},
        {'nome': 'CPF', 'posicao': '[100, 290, 300, 340]'},
        {'nome': 'Foto', 'posicao': '[350, 100, 500, 250]'}
    ]
    
    # Salvar no banco
    for campo in campos_simulados:
        c.execute('''
            INSERT OR REPLACE INTO campos (nome_original, nome_exibicao, tipo, editavel, posicao)
            VALUES (?, ?, ?, ?, ?)
        ''', (campo['nome'], campo['nome'], tipo, 1, campo['posicao']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'campos': len(campos_simulados)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)