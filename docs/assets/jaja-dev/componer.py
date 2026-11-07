from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, math, os

os.makedirs('brand_jaja/out', exist_ok=True)
raw = Image.open('brand_jaja/emblema_raw.png').convert('RGB')

# 1) Recortar el emblema: quitar el blanco exterior
a = np.array(raw)
mascara = (a.sum(axis=2) < 720)  # todo lo que no sea blanco puro
ys, xs = np.where(mascara)
caja = (xs.min(), ys.min(), xs.max()+1, ys.max()+1)
emblema = raw.crop(caja)
lado = max(emblema.size)
cuadro = Image.new('RGB', (lado, lado), (255,255,255))
cuadro.paste(emblema, ((lado-emblema.size[0])//2, (lado-emblema.size[1])//2))
emblema = cuadro
print('emblema recortado:', emblema.size)

TURQ = (45, 226, 230)
BLANCO = (245, 255, 255)
FUENTE = None
for ruta in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
             '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
    if os.path.exists(ruta):
        FUENTE = ruta; break
print('fuente:', FUENTE)

def fuente(px):
    return ImageFont.truetype(FUENTE, px)

def texto_curvado(lienzo, texto, centro, radio, angulo_ini, fuente_obj, relleno, tracking=1.0):
    """Dibuja el texto siguiendo un arco. angulo_ini en grados, 270 = arriba."""
    d = ImageDraw.Draw(lienzo)
    letras = list(texto)
    anchos = [d.textlength(l, font=fuente_obj) for l in letras]
    total = sum(anchos) + tracking * (len(letras)-1)
    # angulo por unidad de ancho
    perim = 2 * math.pi * radio
    paso = 360 * (1.0/len(letras))
    ang = angulo_ini - (paso * (len(letras)-1)) / 2
    for l in letras:
        capa = Image.new('RGBA', (len(l) and 200 or 1, 200), (0,0,0,0))
        # dibujar letra rotada
        gl = Image.new('RGBA', (160,160), (0,0,0,0))
        gd = ImageDraw.Draw(gl)
        gd.text((80,80), l, font=fuente_obj, fill=relleno, anchor='mm')
        gl = gl.rotate(-ang, resample=Image.BICUBIC, expand=False)
        rad = math.radians(ang)
        x = centro[0] + radio * math.cos(rad) - 80
        y = centro[1] + radio * math.sin(rad) - 80
        lienzo.alpha_composite(gl, (int(x), int(y)))
        ang += paso
    return lienzo

# 2) Composición estática final
L = 1080
comp = Image.new('RGBA', (L, L), (12, 18, 20, 255))
# halo
halo = Image.new('RGBA', (L, L), (0,0,0,0))
hd = ImageDraw.Draw(halo)
hd.ellipse((L*0.10, L*0.10, L*0.90, L*0.90), fill=(20, 120, 120, 70))
halo = halo.filter(ImageFilter.GaussianBlur(70))
comp.alpha_composite(halo)

em_tam = 640
em = emblema.resize((em_tam, em_tam), Image.LANCZOS)
pos = ((L-em_tam)//2, 150)
comp.paste(em, pos)
# aro fino
d = ImageDraw.Draw(comp)
d.ellipse((pos[0]-6, pos[1]-6, pos[0]+em_tam+6, pos[1]+em_tam+6), outline=TURQ, width=3)

# nombre
f_nombre = fuente(120)
d.text((L//2, 880), 'JAJA.DEV', font=f_nombre, fill=BLANCO, anchor='mm')
# linea y lema
d.line((L//2-260, 946, L//2+260, 946), fill=TURQ, width=3)
f_lema = fuente(34)
d.text((L//2, 986), 'S O F T W A R E   ·   S E C U R I T Y   ·   A U T O M A T I O N',
       font=f_lema, fill=TURQ, anchor='mm')
comp.convert('RGB').save('brand_jaja/out/jaja-dev-logo.png')
comp.convert('RGB').save('brand_jaja/out/jaja-dev-logo.jpg', quality=94)
print('logo final listo')
