from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
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

def processar_psd_para_banco(psd_path, tipo_psd, db_path):
    """Processa um PSD e salva suas camadas no banco"""
    camadas = extrair_camadas_psd(psd_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Remover camadas antigas do mesmo tipo
    c.execute("DELETE FROM campos_config WHERE tipo_psd = ?", (tipo_psd,))
    
    # Inserir novas camadas (apenas texto)
    ordem = 0
    for camada in camadas:
        if camada['tipo'] == 'type':  # Apenas camadas de texto
            c.execute('''
                INSERT INTO campos_config (nome_original, nome_exibicao, tipo_psd, ordem)
                VALUES (?, ?, ?, ?)
            ''', (camada['nome'], camada['nome'], tipo_psd, ordem))
            ordem += 1
    
    conn.commit()
    conn.close()
    
    return len([c for c in camadas if c['tipo'] == 'type'])

def gerar_preview_psd(psd_path, previews_dir, tamanho_max=(800, 600)):
    """Gera uma imagem preview do PSD"""
    try:
        psd = PSDImage.open(psd_path)
        img = psd.composite()
        
        # Redimensionar se necessário
        if img.width > tamanho_max[0] or img.height > tamanho_max[1]:
            img.thumbnail(tamanho_max, Image.Resampling.LANCZOS)
        
        # Salvar preview
        preview_path = os.path.join(previews_dir, 'preview.png')
        img.save(preview_path)
        
        return preview_path
    
    except Exception as e:
        print(f"Erro ao gerar preview: {e}")
        return None

def gerar_carteirinha_completa(psd_path, dados, output_path, db_path, foto_path=None, area_foto=None):
    """Gera uma carteirinha completa a partir do PSD"""
    try:
        # Abrir PSD
        psd = PSDImage.open(psd_path)
        img = psd.composite()
        
        # Converter para RGB para manipulação
        img = img.convert("RGB")
        
        # Criar objeto para desenho
        draw = ImageDraw.Draw(img)
        
        # Tentar carregar fonte
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font = ImageFont.load_default()
        
        # Determinar tipo (frente ou verso)
        tipo = 'frente' if 'frente' in psd_path.lower() else 'verso'
        
        # Obter configuração de campos do banco
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT nome_original, nome_exibicao FROM campos_config WHERE tipo_psd = ? AND editavel = 1", (tipo,))
        campos = c.fetchall()
        
        # Obter posições dos campos
        c.execute("SELECT nome_original, posicao FROM campos_posicoes WHERE tipo_psd = ?", (tipo,))
        posicoes = {row[0]: json.loads(row[1]) for row in c.fetchall()}
        
        conn.close()
        
        # Aplicar dados nos campos
        for nome_original, nome_exibicao in campos:
            if nome_original in dados:
                valor = dados[nome_original]['valor']
                
                # Buscar posição do campo
                if nome_original in posicoes:
                    x, y, x2, y2 = posicoes[nome_original]
                    # Centralizar texto na área
                    text_width = draw.textlength(valor, font=font)
                    text_x = x + (x2 - x - text_width) // 2
                    text_y = y + (y2 - y - 24) // 2
                    
                    draw.text((text_x, text_y), str(valor), fill=(0, 0, 0), font=font)
        
        # Inserir foto se for a frente e tiver área definida
        if foto_path and area_foto and tipo == 'frente':
            try:
                foto = Image.open(foto_path).convert("RGB")
                
                # Redimensionar para a área
                x1, y1, x2, y2 = area_foto
                foto = foto.resize((x2 - x1, y2 - y1))
                
                # Colar a foto
                img.paste(foto, (x1, y1))
            except Exception as e:
                print(f"Erro ao inserir foto: {e}")
        
        # Salvar resultado
        img.save(output_path)
        
        return True
        
    except Exception as e:
        print(f"Erro ao gerar carteirinha: {e}")
        return False