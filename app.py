from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
import json

app = Flask(__name__)

# Configurações básicas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sistema_config (
            id INTEGER PRIMARY KEY,
            psd_frente TEXT,
            psd_verso TEXT,
            area_foto TEXT
        )
    ''')
    
    c.execute("INSERT OR IGNORE INTO sistema_config (id) VALUES (1)")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT psd_frente, psd_verso, area_foto FROM sistema_config WHERE id = 1")
    config = c.fetchone()
    conn.close()
    
    return render_template('admin.html',
                         frente=config[0] if config else None,
                         verso=config[1] if config else None,
                         area_configurada=config[2] if config else None)

@app.route('/upload_psd', methods=['POST'])
def upload_psd():
    tipo = request.form.get('tipo')
    file = request.files.get('psd')
    
    if file:
        # Salvar arquivo
        filename = f"{tipo}.psd"
        file.save(os.path.join('static', 'psd_base', filename))
        
        # Salvar no banco
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if tipo == 'frente':
            c.execute("UPDATE sistema_config SET psd_frente = ? WHERE id = 1", (filename,))
        else:
            c.execute("UPDATE sistema_config SET psd_verso = ? WHERE id = 1", (filename,))
        
        conn.commit()
        conn.close()
    
    return redirect('/')

@app.route('/configurar')
def configurar():
    return render_template('configurar.html')

@app.route('/visualizar')
def visualizar():
    return render_template('visualizar.html')

@app.route('/gerar')
def gerar():
    return render_template('gerar.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)