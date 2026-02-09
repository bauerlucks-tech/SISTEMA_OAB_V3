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