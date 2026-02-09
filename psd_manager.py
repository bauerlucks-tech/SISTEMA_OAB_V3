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
    
    return preview_path.replace('\', '/')

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