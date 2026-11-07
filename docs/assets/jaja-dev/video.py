"""Video de la marca JAJA.DEV: capas separadas, layout ya validado."""
import sys; sys.path.insert(0, 'brand_jaja')
from marca import recortar_emblema, FUENTE, TURQ, BLANCO, FONDO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os, shutil

shutil.rmtree('brand_jaja/frames', ignore_errors=True)
os.makedirs('brand_jaja/frames', exist_ok=True)

L = 810                      # se renderiza a 810 y ffmpeg escala a 1080
ESC = L / 1080.0
FPS, DUR = 30, 6.0
N = int(FPS * DUR)

# --- capas a resolucion de trabajo ---
em = recortar_emblema('brand_jaja/emblema_v2.png')
tam = int(1080 * 0.52 * ESC)
emblema = em.resize((tam, tam), Image.LANCZOS)

# texto en capa aparte
capa_txt = Image.new('RGBA', (L, L), (0, 0, 0, 0))
d = ImageDraw.Draw(capa_txt)
f_nombre = ImageFont.truetype(FUENTE, int(124 * ESC))
f_lema = ImageFont.truetype(FUENTE, int(37 * ESC))
y_nombre, y_linea, y_lema = int(812*ESC), int(905*ESC), int(999*ESC)
d.text((L//2, y_nombre), 'JAJA.DEV', font=f_nombre, fill=BLANCO, anchor='mm')
ancho_linea = int(420 * ESC)
d.line((L//2-ancho_linea//2, y_linea, L//2+ancho_linea//2, y_linea), fill=TURQ, width=max(2, int(3*ESC)))
d.text((L//2, y_lema), 'SOFTWARE · SECURITY · AUTOMATION', font=f_lema, fill=TURQ, anchor='mm')

ey = int(108 * ESC)   # 0.10 * L
# verificar que el texto no toca el emblema
assert ey + tam <= y_nombre - int(62*ESC), "emblema y nombre se solapan"
print(f"layout: emblema {ey}..{ey+tam} | nombre y={y_nombre} | lema y={y_lema} | lienzo {L}")

def clamp01(x): return max(0.0, min(1.0, x))
def suave(t): return t*t*(3-2*t)

for i in range(N):
    t = i / FPS
    img = Image.new('RGB', (L, L), FONDO)
    # halo que respira
    pulso = 0.5 + 0.5*math.sin(t*2.2)
    halo = Image.new('RGBA', (L, L), (0,0,0,0))
    r = int((250 + 25*pulso) * ESC)
    cx, cy = L//2, int(L*0.36)
    ImageDraw.Draw(halo).ellipse((cx-r, cy-r, cx+r, cy+r), fill=(20,120,120,int(45+35*pulso)))
    img = Image.alpha_composite(img.convert('RGBA'), halo.filter(ImageFilter.GaussianBlur(int(55*ESC)))).convert('RGB')

    # emblema: entra con zoom y fade (0.2-1.5s)
    p = clamp01((t-0.2)/1.3)
    if p > 0:
        e = suave(p)
        s = int(tam * (0.86 + 0.14*e))
        ee = emblema.resize((s, s), Image.LANCZOS).convert('RGBA')
        capa = Image.new('RGBA', (L, L), (0,0,0,0))
        capa.paste(ee, ((L-s)//2, ey + (tam-s)//2))
        capa.putalpha(capa.split()[3].point(lambda v: v*int(255*e)//255))
        img = Image.alpha_composite(img.convert('RGBA'), capa).convert('RGB')

    # barrido de luz (1.4-2.8s)
    ps = clamp01((t-1.4)/1.4)
    if 0 < ps < 1:
        y = int(-120 + (L+240)*suave(ps))
        banda = Image.new('RGBA', (L, L), (0,0,0,0))
        ImageDraw.Draw(banda).rectangle((0, y-70, L, y+70), fill=(90,255,255,42))
        img = Image.alpha_composite(img.convert('RGBA'), banda.filter(ImageFilter.GaussianBlur(int(26*ESC)))).convert('RGB')

    # texto completo entra (2.4-3.8s), sin trocear lineas
    pt = clamp01((t-2.4)/1.4)
    if pt > 0:
        capa = capa_txt.copy()
        capa.putalpha(capa.split()[3].point(lambda v: v*int(255*suave(pt))//255))
        img = Image.alpha_composite(img.convert('RGBA'), capa).convert('RGB')

    # cierre en fundido
    if t > 5.55:
        k = (t-5.55)/0.45
        img = Image.blend(img, Image.new('RGB',(L,L),FONDO), 0.30*k)

    img.save(f'brand_jaja/frames/f{i:04d}.png')
print('frames:', N)
