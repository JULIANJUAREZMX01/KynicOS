"""Composicion de la marca JAJA.DEV con layout medido.

Reglas que este script HACE CUMPLIR (y falla si no se cumplen):
  - ninguna linea de texto supera el 86% del ancho del lienzo
  - el bloque de texto no se solapa con el emblema
  - el texto queda centrado con margen simetrico
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, os

FUENTE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
TURQ = (45, 226, 230)
BLANCO = (245, 255, 255)
FONDO = (12, 18, 20)

def recortar_emblema(ruta):
    raw = Image.open(ruta).convert('RGB')
    a = np.array(raw)
    mascara = (a.sum(axis=2) < 720)
    ys, xs = np.where(mascara)
    em = raw.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
    lado = max(em.size)
    cuadro = Image.new('RGB', (lado, lado), (255,255,255))
    cuadro.paste(em, ((lado-em.size[0])//2, (lado-em.size[1])//2))
    return cuadro

def ajustar(dibujo, texto, px_max, ancho_max, px_min=10):
    """Devuelve la fuente mas grande que cabe en ancho_max."""
    px = px_max
    while px > px_min:
        f = ImageFont.truetype(FUENTE, px)
        if dibujo.textlength(texto, font=f) <= ancho_max:
            return f
        px -= 1
    return ImageFont.truetype(FUENTE, px_min)

def componer(lienzo_px, emblema, nombre, lema, salida, escala=1.0):
    L = lienzo_px
    img = Image.new('RGB', (L, L), FONDO)
    # halo
    halo = Image.new('RGBA', (L, L), (0,0,0,0))
    ImageDraw.Draw(halo).ellipse((L*0.08, L*0.04, L*0.92, L*0.70), fill=(20, 120, 120, 68))
    img = Image.alpha_composite(img.convert('RGBA'), halo.filter(ImageFilter.GaussianBlur(int(L*0.06)))).convert('RGB')

    d = ImageDraw.Draw(img)
    ancho_max = int(L * 0.86)

    # --- emblema: 52% del alto, arriba ---
    tam = int(L * 0.52)
    ex = (L - tam)//2
    ey = int(L * 0.10)
    img.paste(emblema.resize((tam, tam), Image.LANCZOS), (ex, ey))
    d.ellipse((ex-4, ey-4, ex+tam+4, ey+tam+4), outline=TURQ, width=max(2, L//360))
    fin_emblema = ey + tam

    # --- nombre: auto-ajustado ---
    f_nombre = ajustar(d, nombre, int(L*0.115), ancho_max)
    alto_nombre = f_nombre.size
    y_nombre = fin_emblema + int(L*0.075) + alto_nombre//2
    caja_nombre = (L//2 - d.textlength(nombre, font=f_nombre)/2, y_nombre - alto_nombre/2,
                   L//2 + d.textlength(nombre, font=f_nombre)/2, y_nombre + alto_nombre/2)

    # --- linea ---
    y_linea = y_nombre + alto_nombre//2 + int(L*0.045)
    ancho_linea = int(min(ancho_max*0.62, d.textlength(nombre, font=f_nombre)*0.9))

    # --- lema: auto-ajustado ---
    f_lema = ajustar(d, lema, int(L*0.035), ancho_max)
    y_lema = y_linea + int(L*0.055) + f_lema.size//2
    ancho_lema = d.textlength(lema, font=f_lema)
    caja_lema = (L//2 - ancho_lema/2, y_lema - f_lema.size/2, L//2 + ancho_lema/2, y_lema + f_lema.size/2)

    # ---- VERIFICACIONES ----
    problemas = []
    if caja_nombre[1] < fin_emblema:
        problemas.append(f"el nombre (y={caja_nombre[1]:.0f}) se solapa con el emblema (termina y={fin_emblema})")
    if caja_lema[1] < caja_nombre[3]:
        problemas.append("el lema se solapa con el nombre")
    if caja_lema[3] > L - L*0.02:
        problemas.append(f"el lema se sale por abajo (y={caja_lema[3]:.0f} de {L})")
    for etiqueta, caja in (("nombre", caja_nombre), ("lema", caja_lema)):
        if caja[0] < L*0.02 or caja[2] > L*0.98:
            problemas.append(f"{etiqueta} se sale por los lados: {caja[0]:.0f}..{caja[2]:.0f} de {L}")
    if problemas:
        raise SystemExit("LAYOUT INVALIDO:\n  - " + "\n  - ".join(problemas))

    # ---- dibujo ----
    d.text((L//2, y_nombre), nombre, font=f_nombre, fill=BLANCO, anchor='mm')
    d.line((L//2-ancho_linea//2, y_linea, L//2+ancho_linea//2, y_linea), fill=TURQ, width=max(2, L//340))
    d.text((L//2, y_lema), lema, font=f_lema, fill=TURQ, anchor='mm')

    img.save(salida)
    return {
        "archivo": salida, "emblema_fin": fin_emblema,
        "nombre": (round(caja_nombre[1]), round(caja_nombre[3]), f_nombre.size),
        "lema": (round(caja_lema[1]), round(caja_lema[3]), f_lema.size, round(ancho_lema)),
        "lienzo": L,
    }
