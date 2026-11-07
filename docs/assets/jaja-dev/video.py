from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, os, math, subprocess

os.makedirs('brand_jaja/frames', exist_ok=True)
BASE = Image.open('brand_jaja/out/jaja-dev-logo.png').convert('RGB')
W = 1080
TURQ = (45, 226, 230); BLANCO = (245, 255, 255)
FUENTE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

L = 720  # se renderiza a 720 y ffmpeg escala a 1080
base = BASE.resize((L, L), Image.LANCZOS)
emblema = Image.open('brand_jaja/out/jaja-dev-logo.png').convert('RGB').crop((150, 90, 930, 870)).resize((580,580), Image.LANCZOS)

FPS = 30
DUR = 6.0
N = int(FPS*DUR)

def suave(t):
    return t*t*(3-2*t)

def clamp01(x): return max(0.0, min(1.0, x))

for i in range(N):
    t = i / FPS
    # fondo con halo que respira
    img = Image.new('RGB', (L, L), (12, 18, 20))
    halo = Image.new('RGBA', (L, L), (0,0,0,0))
    hd = ImageDraw.Draw(halo)
    pulso = 0.5 + 0.5*math.sin(t*2.2)
    radio = 250 + 22*pulso
    hd.ellipse((L/2-radio, L/2-radio, L/2+radio, L/2+radio), fill=(20, 120, 120, int(45+35*pulso)))
    halo = halo.filter(ImageFilter.GaussianBlur(60))
    img = Image.alpha_composite(img.convert('RGBA'), halo).convert('RGB')

    # 0.0-1.4s: emblema entra con zoom y fade
    p = clamp01((t-0.15)/1.25)
    if p > 0:
        e = suave(p)
        tam = int(430 + 150*e)
        ee = emblema.resize((tam, tam), Image.LANCZOS)
        alfa = int(255*e)
        capa = Image.new('RGBA', (L, L), (0,0,0,0))
        capa.paste(ee.convert('RGBA'), ((L-tam)//2, (L-tam)//2 - 70))
        capa.putalpha(capa.split()[3].point(lambda v: v*alfa//255))
        img = Image.alpha_composite(img.convert('RGBA'), capa).convert('RGB')

    # 1.2-2.6s: barrido de luz vertical
    ps = clamp01((t-1.15)/1.4)
    if 0 < ps < 1:
        y = int(-200 + (L+400)*suave(ps))
        banda = Image.new('RGBA', (L, L), (0,0,0,0))
        bd = ImageDraw.Draw(banda)
        bd.rectangle((0, y-90, L, y+90), fill=(90, 255, 255, 46))
        banda = banda.filter(ImageFilter.GaussianBlur(28))
        img = Image.alpha_composite(img.convert('RGBA'), banda).convert('RGB')

    # 2.2-3.4s: nombre
    pn = clamp01((t-2.15)/1.15)
    if pn > 0:
        capa = Image.new('RGBA', (L, L), (0,0,0,0))
        cd = ImageDraw.Draw(capa)
        f = ImageFont.truetype(FUENTE, 82)
        alfa = int(255*suave(pn))
        cd.text((L/2, L-150), 'JAJA.DEV', font=f, fill=BLANCO+(alfa,), anchor='mm')
        img = Image.alpha_composite(img.convert('RGBA'), capa).convert('RGB')

    # 3.2-4.2s: linea y lema
    pl = clamp01((t-3.15)/1.05)
    if pl > 0:
        capa = Image.new('RGBA', (L, L), (0,0,0,0))
        cd = ImageDraw.Draw(capa)
        e = suave(pl)
        ancho = int(340*e)
        cd.line((L/2-ancho, L-98, L/2+ancho, L-98), fill=TURQ+(int(255*e),), width=3)
        f2 = ImageFont.truetype(FUENTE, 24)
        cd.text((L/2, L-62), 'S O F T W A R E  ·  S E C U R I T Y  ·  A U T O M A T I O N',
                font=f2, fill=TURQ+(int(255*e),), anchor='mm')
        img = Image.alpha_composite(img.convert('RGBA'), capa).convert('RGB')

    # cierre: fundido final suave
    if t > 5.55:
        k = (t-5.55)/0.45
        img = Image.blend(img, Image.new('RGB',(L,L),(12,18,20)), 0.35*k)

    img.save(f'brand_jaja/frames/f{i:04d}.png')

print('frames:', N)
