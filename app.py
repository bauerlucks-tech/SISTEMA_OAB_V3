from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
import sqlite3
import os
import json
import uuid
from datetime import datetime
import psd_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sistema_oab_2024_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configurações de pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PSD = os.path.join('static', 'psd_base')
UPLOAD_FOTOS = os.path.join('static', 'fotos')
GERADOS = os.path.join('static', 'gerados')
PREVIEWS = os.path.join('static', 'previews')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

# Criar pastas se não existirem
for pasta in [UPLOAD_PSD, UPLOAD_FOTOS, GERADOS, PREVIEWS]:
    os.makedirs(pasta, exist_ok=True)

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabela de configuração do sistema
    c.execute('''
        CREATE TABLE IF NOT EXISTS sistema_config (
            id INTEGER PRIMARY KEY,
            psd_frente TEXT,
            psd_verso TEXT,
            area_foto TEXT,
            data_config TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de campos configurados
    c.execute('''
        CREATE TABLE IF NOT EXISTS campos_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_original TEXT,
            nome_exibicao TEXT,
            tipo_psd TEXT,
            editavel INTEGER DEFAULT 1,
            ordem INTEGER DEFAULT 0
        )
    ''')
    
    # Tabela de gerações
    c.execute('''
        CREATE TABLE IF NOT EXISTS geracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_pessoa TEXT,
            rg TEXT,
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            arquivo_frente TEXT,
            arquivo_verso TEXT
        )
    ''')
    
    # Inserir configuração padrão
    c.execute("INSERT OR IGNORE INTO sistema_config (id) VALUES (1)")
    
    conn.commit()
    conn.close()

# Inicializar banco
init_db()

# ============ ROTAS PRINCIPAIS ============

@app.route('/')
def index():
    """Página inicial/admin"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Obter status dos PSDs
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    # Contar gerações
    c.execute("SELECT COUNT(*) FROM geracoes")
    total_geracoes = c.fetchone()[0]
    
    # Últimas gerações
    c.execute("SELECT nome_pessoa, rg, data_geracao FROM geracoes ORDER BY id DESC LIMIT 5")
    ultimas_geracoes = c.fetchall()
    
    conn.close()
    
    return render_template('admin.html',
                         frente=config[0] if config else None,
                         verso=config[1] if config else None,
                         area_configurada=config[2] if config else None,
                         total_geracoes=total_geracoes,
                         ultimas_geracoes=ultimas_geracoes)

@app.route('/upload_psd', methods=['POST'])
def upload_psd():
    """Upload dos PSDs base (frente e verso)"""
    tipo = request.form.get('tipo')
    acao = request.form.get('acao', 'upload')
    
    if 'psd' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['psd']
    
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file and file.filename.lower().endswith('.psd'):
        # Gerar nome único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{tipo}_{timestamp}.psd"
        filepath = os.path.join(UPLOAD_PSD, filename)
        file.save(filepath)
        
        # Salvar no banco
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if tipo == 'frente':
            c.execute("UPDATE sistema_config SET psd_frente = ? WHERE id = 1", (filename,))
        elif tipo == 'verso':
            c.execute("UPDATE sistema_config SET psd_verso = ? WHERE id = 1", (filename,))
        
        conn.commit()
        conn.close()
        
        # Processar PSD para extrair campos
        if acao == 'processar':
            psd_manager.processar_psd_para_banco(filepath, tipo)
    
    return redirect(url_for('configurar'))

@app.route('/configurar')
def configurar():
    """Página de configuração dos campos"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar PSDs
    c.execute("SELECT psd_frente, psd_verso FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    if not config or not all(config):
        conn.close()
        return render_template('erro.html', 
                             mensagem="Por favor, envie ambos os PSDs (frente e verso) antes de configurar.")
    
    # Obter campos detectados
    c.execute("SELECT * FROM campos_config ORDER BY tipo_psd, ordem")
    campos = c.fetchall()
    
    # Obter área da foto se existir
    c.execute("SELECT area_foto FROM sistema_config WHERE id = 1")
    area_foto = c.fetchone()[0]
    
    conn.close()
    
    # Organizar campos por tipo
    campos_frente = [c for c in campos if c[3] == 'frente']
    campos_verso = [c for c in campos if c[3] == 'verso']
    
    return render_template('configurar.html',
                         campos_frente=campos_frente,
                         campos_verso=campos_verso,
                         area_foto=area_foto)

@app.route('/api/atualizar_campo', methods=['POST'])
def atualizar_campo():
    """Atualizar configuração de um campo via AJAX"""
    data = request.json
    campo_id = data.get('id')
    nome_exibicao = data.get('nome_exibicao')
    editavel = data.get('editavel')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if nome_exibicao is not None:
        c.execute("UPDATE campos_config SET nome_exibicao = ? WHERE id = ?", 
                 (nome_exibicao, campo_id))
    
    if editavel is not None:
        c.execute("UPDATE campos_config SET editavel = ? WHERE id = ?", 
                 (editavel, campo_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/visualizar')
def visualizar():
    """Página para marcar área da foto com 2 cliques"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente FROM sistema_config WHERE id = 1")
    psd_frente = c.fetchone()
    
    if not psd_frente or not psd_frente[0]:
        conn.close()
        return redirect(url_for('index'))
    
    # Gerar preview do PSD
    psd_path = os.path.join(UPLOAD_PSD, psd_frente[0])
    preview_path = psd_manager.gerar_preview_psd(psd_path)
    
    # Obter área atual se existir
    c.execute("SELECT area_foto FROM sistema_config WHERE id = 1")
    area_foto = c.fetchone()[0]
    
    conn.close()
    
    return render_template('visualizar.html',
                         preview=preview_path,
                         area_foto=area_foto)

@app.route('/api/salvar_area_foto', methods=['POST'])
def salvar_area_foto():
    """Salvar área da foto com 2 cliques"""
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
    c.execute("UPDATE sistema_config SET area_foto = ? WHERE id = 1", (area,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'area': area})

@app.route('/gerar')
def gerar_carteirinha():
    """Página para gerar nova carteirinha"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar se tudo está configurado
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    if not config or not all(config[:2]) or not config[2]:
        conn.close()
        return render_template('erro.html',
                             mensagem="Configure os PSDs e a área da foto antes de gerar carteirinhas.")
    
    # Obter campos editáveis
    c.execute("SELECT nome_exibicao FROM campos_config WHERE editavel = 1 ORDER BY ordem")
    campos = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    return render_template('gerar.html', campos=campos)

@app.route('/processar_geracao', methods=['POST'])
def processar_geracao():
    """Processar geração da carteirinha"""
    # Obter dados do formulário
    dados_form = {}
    for key, value in request.form.items():
        if key != 'foto':
            dados_form[key] = value
    
    # Processar foto
    foto = request.files.get('foto')
    foto_path = None
    if foto and foto.filename:
        # Validar extensão
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' in foto.filename and foto.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            foto_filename = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{foto.filename.rsplit('.', 1)[1].lower()}"
            foto_path = os.path.join(UPLOAD_FOTOS, foto_filename)
            foto.save(foto_path)
    
    # Obter configurações
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    
    c.execute("SELECT nome_original, nome_exibicao, tipo_psd FROM campos_config WHERE editavel = 1")
    campos_config = c.fetchall()
    
    if not config or not config[0] or not config[1]:
        conn.close()
        return "Erro: PSDs não configurados."
    
    # Preparar dados para processamento
    dados_processar = {}
    for campo in campos_config:
        nome_original, nome_exibicao, tipo_psd = campo
        if nome_exibicao in dados_form:
            dados_processar[nome_original] = {
                'valor': dados_form[nome_exibicao],
                'tipo': tipo_psd
            }
    
    # Área da foto
    area_foto = json.loads(config[2]) if config[2] else None
    
    # Gerar carteirinha
    try:
        # Caminhos dos PSDs
        frente_path = os.path.join(UPLOAD_PSD, config[0])
        verso_path = os.path.join(UPLOAD_PSD, config[1])
        
        # Nomes de saída
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        frente_output = os.path.join(GERADOS, f'frente_{timestamp}.png')
        verso_output = os.path.join(GERADOS, f'verso_{timestamp}.png')
        
        # Gerar frente (com foto)
        psd_manager.gerar_carteirinha_completa(
            frente_path,
            dados_processar,
            frente_output,
            foto_path,
            area_foto
        )
        
        # Gerar verso (sem foto)
        psd_manager.gerar_carteirinha_completa(
            verso_path,
            dados_processar,
            verso_output
        )
        
        # Salvar no histórico
        nome_pessoa = dados_form.get('Nome', 'Sem nome')
        rg = dados_form.get('RG', 'Sem RG')
        
        c.execute('''
            INSERT INTO geracoes (nome_pessoa, rg, arquivo_frente, arquivo_verso)
            VALUES (?, ?, ?, ?)
        ''', (nome_pessoa, rg, 
              frente_output.replace('static/', ''),
              verso_output.replace('static/', '')))
        
        conn.commit()
        conn.close()
        
        return render_template('resultado.html',
                             frente=frente_output.replace('static/', ''),
                             verso=verso_output.replace('static/', ''),
                             nome_pessoa=nome_pessoa,
                             rg=rg)
    
    except Exception as e:
        conn.close()
        return f"Erro ao gerar carteirinha: {str(e)}"

@app.route('/download/<tipo>/<filename>')
def download_arquivo(tipo, filename):
    """Download dos arquivos gerados"""
    if tipo == 'frente':
        return send_file(os.path.join('static', 'gerados', filename), as_attachment=True)
    elif tipo == 'verso':
        return send_file(os.path.join('static', 'gerados', filename), as_attachment=True)
    else:
        return "Arquivo não encontrado", 404

@app.route('/historico')
def historico():
    """Histórico de gerações"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id, nome_pessoa, rg, data_geracao, arquivo_frente, arquivo_verso FROM geracoes ORDER BY id DESC")
    historico = c.fetchall()
    
    conn.close()
    
    return render_template('historico.html', historico=historico)

# ============ API PARA AJAX ============

@app.route('/api/detectar_campos/<tipo>')
def detectar_campos(tipo):
    """Detectar campos de um PSD via AJAX"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute(f"SELECT psd_{tipo} FROM sistema_config WHERE id = 1")
    psd_nome = c.fetchone()
    
    if not psd_name or not psd_nome[0]:
        conn.close()
        return jsonify({'success': False, 'error': 'PSD não encontrado'})
    
    psd_path = os.path.join(UPLOAD_PSD, psd_nome[0])
    
    try:
        # Detectar campos usando psd_manager
        campos = psd_manager.extrair_camadas_psd(psd_path)
        
        # Filtrar apenas campos de texto
        campos_texto = [c for c in campos if c['tipo'] == 'type']
        
        # Salvar no banco
        for i, campo in enumerate(campos_texto):
            c.execute('''
                INSERT OR IGNORE INTO campos_config (nome_original, nome_exibicao, tipo_psd, ordem)
                VALUES (?, ?, ?, ?)
            ''', (campo['nome'], campo['nome'], tipo, i))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'total_campos': len(campos_texto),
            'campos': campos_texto
        })
    
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)