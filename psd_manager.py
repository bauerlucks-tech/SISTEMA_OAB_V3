from psd_tools import PSDImage
from PIL import Image, ImageDraw
import os
import json
import sqlite3

def extrair_camadas_psd(psd_path):
    """Extrai todas as camadas de um PSD"""
    try:
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
    except Exception as e:
        print(f"Erro ao extrair camadas PSD: {e}")
        return []

def gerar_preview_psd(psd_path, tamanho_max=(800, 800)):
    """Gera uma imagem preview do PSD"""
    try:
        psd = PSDImage.open(psd_path)
        img = psd.composite()
        
        # Redimensionar se necessário
        if img.width > tamanho_max[0] or img.height > tamanho_max[1]:
            img.thumbnail(tamanho_max, Image.Resampling.LANCZOS)
        
        # Salvar preview
        preview_dir = os.path.join('static', 'previews')
        os.makedirs(preview_dir, exist_ok=True)
        
        preview_path = os.path.join(preview_dir, 'preview.png')
        img.save(preview_path)
        
        # CORREÇÃO AQUI - usar os.path.normpath
        return os.path.normpath(preview_path).replace('\\', '/')
    
    except Exception as e:
        print(f"Erro ao gerar preview: {e}")
        return None

def testar_psd(psd_path):
    """Testa se um PSD pode ser aberto"""
    try:
        psd = PSDImage.open(psd_path)
        return True, f"PSD aberto com sucesso. Dimensões: {psd.width}x{psd.height}"
    except Exception as e:
        return False, f"Erro ao abrir PSD: {str(e)}"

# Funções adicionais para o sistema...
def criar_banco_se_nao_existir():
    """Cria o banco de dados SQLite se não existir"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sistema_config (
            id INTEGER PRIMARY KEY,
            psd_frente TEXT,
            psd_verso TEXT,
            area_foto TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS campos_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_campo TEXT,
            tipo_campo TEXT,
            editavel INTEGER DEFAULT 1
        )
    ''')
    
    # Inserir configuração padrão
    c.execute("INSERT OR IGNORE INTO sistema_config (id) VALUES (1)")
    
    conn.commit()
    conn.close()

def processar_psd_para_banco(psd_path, tipo):
    """Processa um PSD e salva suas camadas no banco"""
    camadas = extrair_camadas_psd(psd_path)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Remover camadas antigas do mesmo tipo
    c.execute("DELETE FROM campos_config WHERE tipo_campo = ?", (tipo,))
    
    # Inserir novas camadas
    for camada in camadas:
        if camada['tipo'] == 'type':  # Apenas texto
            c.execute('''
                INSERT INTO campos_config (nome_campo, tipo_campo, editavel)
                VALUES (?, ?, ?)
            ''', (camada['nome'], tipo, 1))
    
    conn.commit()
    conn.close()
    
    return len(camadas)
#