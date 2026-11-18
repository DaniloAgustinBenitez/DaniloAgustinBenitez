"""El puente General Belgrano (Chaco–Corrientes) de noche, en ASCII.

Vista lateral sobre el Paraná: Corrientes a la izquierda (costanera, barranca
y la ciudad), las dos torres en H con los tensores en abanico, y el viaducto
que baja hacia Resistencia a la derecha. Autos cruzando y una chata que pasa
por el río. Arriba a la derecha va la terminal que escribe.

El dibujo usa una celda más chica que el resto (letra fina) para tener más
detalle; la terminal mantiene su tamaño.

Lo usa tools/poster.py. Para verlo suelto: python tools/puente.py <archivo.svg>
"""

from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path

from generar_ascii import (
    CSS_TERMINAL,
    ESC_H,
    ESC_W,
    TERM_C0,
    TERM_C1,
    TERM_F0,
    TERM_F1,
    CH,
    CW,
    _hash,
    capas_texto,
    clamp,
    en_terminal,
    envolver,
    fbm,
    rasterizar,
    terminal,
)

# Celda fina del puente.
PCW, PCH = 5.4, 9.0
P_COLS, P_FILAS = int(ESC_W / PCW), int(ESC_H / PCH)

Y_AGUA = 300.0
TORRES = (215.0, 445.0)
TORRE_TOPE = 64.0
Y_TABLERO = 232.0
FIN_ORILLA_CTES = 78.0  # donde el tablero llega a la barranca de Corrientes
INICIO_VIADUCTO = 590.0
CAIDA_VIADUCTO = 30.0
PILAS = [122.0, 528.0] + [608.0 + k * 44 for k in range(8)]
FAROLES = [x for x in range(92, 920, 30) if all(abs(x - xt) > 16 for xt in TORRES)]
LUNA = (70.0, 62.0, 25.0)
CRATERES = [(-8, -6, 5.5), (8, 5, 4.5), (-3, 11, 3.5), (10, -9, 3)]
RAMPA_AGUA = " .-~~="

_rnd = random.Random(3)
EDIFICIOS = []
_x = -4.0
while _x < 150:
    ancho = _rnd.uniform(12, 26)
    alto = _rnd.uniform(22, 74) * (1.0 if _x < 105 else 0.5)
    EDIFICIOS.append((_x, ancho, 244 - alto))
    _x += ancho + _rnd.uniform(1, 3)
EDIFICIO_ALTO = min(EDIFICIOS, key=lambda e: e[2])
ARBOLES = [(10, 238, 8), (30, 240, 7), (50, 237, 9), (70, 241, 6)]


def y_tablero(x: float) -> float | None:
    if x < FIN_ORILLA_CTES:
        return None
    if x <= INICIO_VIADUCTO:
        return Y_TABLERO
    return Y_TABLERO + (x - INICIO_VIADUCTO) / (ESC_W - INICIO_VIADUCTO) * CAIDA_VIADUCTO


# ------------------------------------------------------------------- torres

def _torre(x: float, y: float, xt: float):
    """Torre en H vista de costado con un poco de perspectiva: dos patas,
    cabezal arriba, vigas transversales y la base sobre el agua."""
    if not (TORRE_TOPE <= y <= Y_AGUA + 5):
        return None
    dx = x - xt
    # Cabezal (donde se anclan los tensores).
    if y <= TORRE_TOPE + 20:
        mw = 7 + (y - TORRE_TOPE) * 0.1
        if abs(dx) <= mw:
            if y < TORRE_TOPE + 2:
                return 0.98
            return 0.9 if dx < 0 else 0.66
        return None
    # Base: cabezal de pilotes en el agua.
    if y >= Y_AGUA - 8:
        if abs(dx) <= 17:
            return 0.75 if y < Y_AGUA - 5 else (0.55 if dx < 0 else 0.4)
        return None
    t = clamp((y - TORRE_TOPE) / (Y_AGUA - TORRE_TOPE))
    sep = 4.5 + t * 3.5  # las patas se abren hacia abajo
    mw = 2.6 + t * 2.4
    # Vigas transversales: una arriba y otra bajo el tablero.
    if 126 <= y <= 132 or Y_TABLERO + 14 <= y <= Y_TABLERO + 21:
        if abs(dx) <= sep + mw:
            return 0.8
    if abs(dx + sep) <= mw:
        return 0.92 if dx + sep < 0 else 0.75
    if abs(dx - sep) <= mw:
        return 0.6 if dx - sep < 0 else 0.42
    return None


# ------------------------------------------------------------------- tablero

def _tablero(x: float, y: float):
    yt = y_tablero(x)
    if yt is None:
        return None
    # Baranda (pasamanos) y losa.
    if yt - 3 <= y < yt - 1.5:
        return 0.4
    if yt <= y < yt + 3:
        return 0.97
    if yt + 3 <= y < yt + 10:
        return 0.32 if (x % 14) < 1.6 else 0.62  # viga con nervios
    if yt + 10 <= y < yt + 12:
        return 0.42
    # Pilas con cabezal.
    for xp in PILAS:
        if yt + 12 <= y < yt + 16 and abs(x - xp) <= 6.5:
            return 0.7
        if yt + 16 <= y <= Y_AGUA + 3 and abs(x - xp) <= 3.2 + (y - yt) * 0.012:
            return 0.55 if x < xp else 0.32
    return None


def _farol(x: float, y: float):
    """Poste, luminaria y halo de cada farol del tablero."""
    luz = 0.0
    for xf in FAROLES:
        yt = y_tablero(xf)
        if abs(x - xf) <= 0.8 and yt - 15 <= y < yt - 4:
            return 0.55
        cx, cy = xf + 2.5, yt - 16
        d = math.hypot(x - cx, y - cy)
        if d <= 1.9:
            return 1.0
        if d < 12:
            luz = max(luz, 0.32 * math.exp(-d / 4.5))
    return luz or None


# ------------------------------------------------------------------- orillas

def _corrientes(x: float, y: float):
    # Muro de la costanera y barranca.
    borde = FIN_ORILLA_CTES + 4 - (y - 248) * 0.3
    if 246 <= y <= Y_AGUA + 2 and x < borde:
        if y < 250:
            return 0.72
        return 0.18 + fbm(x, y, 5, 31) * 0.24
    # Árboles de la costanera.
    for ax, ay, ar in ARBOLES:
        d = math.hypot(x - ax, (y - ay) * 1.15)
        if d < ar and y < 246:
            return 0.22 + fbm(x, y, 3, 37) * 0.3
        if abs(x - ax) < 1 and ay <= y < 246:
            return 0.3
    # Edificios con ventanas y una antena en el más alto.
    ex, ew, etope = EDIFICIO_ALTO
    if abs(x - (ex + ew / 2)) < 0.8 and etope - 16 <= y < etope:
        return 0.6
    if abs(x - (ex + ew / 2)) < 2 and abs(y - (etope - 17)) < 2:
        return 1.0  # baliza de la antena
    for x0, w, tope in EDIFICIOS:
        if x0 <= x < x0 + w and tope <= y < 246:
            if y < tope + 2:
                return 0.55  # borde del techo
            c, r = int(x / PCW), int(y / PCH)
            if _hash(c, r, 77) < 0.36 and x - x0 > 2:
                return 0.92  # ventana encendida
            return 0.24 + (0.14 if x - x0 < 2.5 else 0.0)
    return None


def _resistencia(x: float, y: float):
    copa = 284 - fbm(x, 0, 12, 41) * 18
    if x > 826 and copa <= y <= Y_AGUA + 2:
        if abs(y - 290) < 2 and _hash(int(x / PCW), 7, 91) < 0.18:
            return 0.95  # luces lejanas
        return 0.1 + fbm(x, y, 4, 43) * 0.26
    return None


# --------------------------------------------------------------------- agua

def _agua(x: float, y: float):
    prof = y - Y_AGUA
    v = 0.01 + fbm(x, y * 7, 46, 51) ** 3 * 0.42
    brillo = fbm(x * 1.6, y * 5, 20, 53)
    if abs(x - LUNA[0]) < 11 + prof * 0.35 and brillo > 0.5:
        v += 0.8 * (1 - prof / 140)
    for xt in TORRES:
        if abs(x - xt) < 9 + prof * 0.05 and brillo > 0.45 and prof < 90:
            v += 0.5
    for xf in FAROLES:
        if abs(x - xf - 2.5) < 1.6 + prof * 0.03 and brillo > 0.42 and prof < 70:
            v += 0.5 * (1 - prof / 70)
    reflejo_tablero = Y_AGUA + (Y_AGUA - Y_TABLERO) - 3
    if abs(y - reflejo_tablero) < 2.5 and x > FIN_ORILLA_CTES and brillo > 0.4:
        v += 0.26
    return clamp(v)


# ---------------------------------------------------------------------- cielo

def _cielo(x: float, y: float):
    lx, ly, lr = LUNA
    d = math.hypot(x - lx, y - ly)
    if d <= lr:
        v = 0.97
        for dx, dy, cr in CRATERES:
            if math.hypot(x - lx - dx, y - ly - dy) < cr:
                v = 0.7
        return v - clamp((x - lx) / lr, 0, 1) * 0.22
    v = 0.36 * math.exp(-(d - lr) / 16)
    # Nubes finas, iluminadas por la luna.
    for cy, x0, x1, semilla in ((44, 110, 430, 61), (118, 0, 300, 67), (172, 560, 900, 71)):
        if x0 <= x <= x1:
            banda = math.exp(-((y - cy) / 6.5) ** 2)
            nube = clamp((fbm(x, y * 4, 55, semilla) - 0.52) * 3.2)
            v += 0.3 * banda * nube
    # Resplandor de las ciudades sobre el horizonte.
    v += 0.1 * math.exp(-(Y_AGUA - y) / 22)
    return v


def campo_puente(x: float, y: float):
    if en_terminal(x, y):
        return 0.0, None
    for xt in TORRES:
        v = _torre(x, y, xt)
        if v is not None:
            return v, None
    for capa in (_tablero, _farol, _corrientes, _resistencia):
        v = capa(x, y)
        if v is not None:
            return v, None
    if y > Y_AGUA:
        return _agua(x, y), None, RAMPA_AGUA
    return _cielo(x, y), None


# ------------------------------------------------------------- superpuestos

def _poner(chars, tonos, c, r, car, tono, solo_vacio=True):
    if not (0 <= r < P_FILAS and 0 <= c < P_COLS):
        return
    if en_terminal((c + 0.5) * PCW, (r + 0.5) * PCH):
        return
    if solo_vacio and chars[r][c] not in " .:-":
        return
    chars[r][c] = car
    tonos[r][c] = tono


def tensores(chars, tonos):
    """Tensores en abanico: 9 por lado y por torre, dibujados con / \\ |."""
    for xt in TORRES:
        for i in range(9):
            ya = TORRE_TOPE + 14 + i * 6
            d = 26 + (8 - i) * 11.5
            for lado in (-1, 1):
                xd = xt + lado * d
                x0, y0 = xt + lado * 7, ya
                dx_cel = abs(xd - x0) / PCW
                dy_cel = abs(Y_TABLERO - 4 - y0) / PCH
                n = int(max(dx_cel, dy_cel)) + 1
                if dx_cel < dy_cel * 0.3:
                    car = "|"
                elif dy_cel < dx_cel * 0.3:
                    car = "-"
                else:
                    car = "\\" if lado == 1 else "/"
                for k in range(n + 1):
                    t = k / n
                    px, py = x0 + (xd - x0) * t, y0 + (Y_TABLERO - 4 - y0) * t
                    _poner(chars, tonos, int(px / PCW), int(py / PCH), car, "medio")
                # Anclaje en la torre.
                _poner(chars, tonos, int(x0 / PCW), int(y0 / PCH), "=", "claro", solo_vacio=False)


def rotulos(chars, tonos):
    fila = P_FILAS - 1
    for i, car in enumerate("← corrientes"):
        _poner(chars, tonos, 1 + i, fila, car, "medio", solo_vacio=False)
    texto = "resistencia →"
    for i, car in enumerate(texto):
        _poner(chars, tonos, P_COLS - 1 - len(texto) + i, fila, car, "medio", solo_vacio=False)


# ------------------------------------------------------------- lo que se mueve

def balizas() -> str:
    """Luces de balizamiento titilando en la punta de cada torre."""
    return "\n".join(
        f'<text class="acento estrella" x="{xt - CW / 2:.1f}" y="{TORRE_TOPE - 3:.1f}" '
        f'style="animation-delay:{i * 0.9:.1f}s;animation-duration:1.8s">*</text>'
        for i, xt in enumerate(TORRES)
    )


def autos() -> str:
    """Autos con luces cruzando en los dos sentidos."""
    salida = []
    largo = ESC_W - FIN_ORILLA_CTES
    for i, (dur, demora) in enumerate(((17, 0), (23, 9), (19, 14))):
        salida.append(
            f'<text class="fino auto-der" x="{FIN_ORILLA_CTES:.1f}" y="{Y_TABLERO - 1.5:.1f}" '
            f'style="animation-duration:{dur}s;animation-delay:-{demora}s">'
            f'<tspan class="acento">-</tspan><tspan class="claro">o</tspan></text>'
        )
    for i, (dur, demora) in enumerate(((21, 3), (16, 11))):
        salida.append(
            f'<text class="fino auto-izq" x="{ESC_W - 10:.1f}" y="{Y_TABLERO + CAIDA_VIADUCTO - 1.5:.1f}" '
            f'style="animation-duration:{dur}s;animation-delay:-{demora}s">'
            f'<tspan class="claro">o</tspan><tspan class="acento">-</tspan></text>'
        )
    return "\n".join(salida), largo


def chata() -> str:
    """Un remolcador empujando barcazas por el Paraná, de derecha a izquierda."""
    lineas = [
        ("              *  ", "acento"),
        ("             _|_ ", "claro"),
        ("[####][####]=|__|", "medio"),
    ]
    y0 = 334
    filas = []
    for k, (s, clase) in enumerate(lineas):
        filas.append(
            f'<text class="fino {clase}" x="0" y="{k * PCH:.1f}" xml:space="preserve">{html.escape(s)}</text>'
        )
    ancho = len(lineas[-1][0]) * PCW
    tapa = f'<rect x="-2" y="{2 * PCH - 7:.1f}" width="{ancho + 4:.1f}" height="9" fill="#0a0d10"/>'
    return (
        f'<g class="chata" transform="translate({ESC_W + 20:.1f} {y0})">'
        f'<g class="chata-mov">{tapa}{"".join(filas)}</g></g>'
    )


def estrellas() -> str:
    rnd = random.Random(42)
    salida, intentos = [], 0
    while len(salida) < 26 and intentos < 3000:
        intentos += 1
        c, r = rnd.randrange(1, int(ESC_W / CW) - 1), rnd.randrange(0, 14)
        x, y = (c + 0.5) * CW, (r + 0.5) * CH
        if TERM_C0 - 2 <= c <= TERM_C1 + 2 and TERM_F0 - 1 <= r <= TERM_F1 + 1:
            continue
        if math.hypot(x - LUNA[0], y - LUNA[1]) < LUNA[2] + 34:
            continue
        if any(abs(x - xt) < 130 and y > TORRE_TOPE - 10 for xt in TORRES):
            continue
        car = rnd.choice(["*", "+", "·", "*", "✦"])
        salida.append(
            f'<text class="claro estrella" x="{c * CW:.1f}" y="{(r + 1) * CH - 2.5:.1f}" '
            f'style="animation-delay:{rnd.uniform(0, 4):.2f}s;animation-duration:{rnd.uniform(2.5, 5):.2f}s">'
            f"{html.escape(car)}</text>"
        )
    return "\n".join(salida)


def css_puente() -> str:
    largo = ESC_W - FIN_ORILLA_CTES
    tramo = (INICIO_VIADUCTO - FIN_ORILLA_CTES) / largo * 100
    plano = INICIO_VIADUCTO - FIN_ORILLA_CTES
    return f"""
  .ascii text.fino, text.fino {{ font-size: 8.8px; }}
  .auto-der {{ animation: cruzar-der linear infinite; }}
  .auto-izq {{ animation: cruzar-izq linear infinite; }}
  @keyframes cruzar-der {{
    0% {{ transform: translate(0px, 0px); }}
    {tramo:.1f}% {{ transform: translate({plano:.0f}px, 0px); }}
    100% {{ transform: translate({largo - 10:.0f}px, {CAIDA_VIADUCTO:.0f}px); }}
  }}
  @keyframes cruzar-izq {{
    0% {{ transform: translate(0px, 0px); }}
    {100 - tramo:.1f}% {{ transform: translate(-{largo - plano - 10:.0f}px, -{CAIDA_VIADUCTO:.0f}px); }}
    100% {{ transform: translate(-{largo - 10:.0f}px, -{CAIDA_VIADUCTO:.0f}px); }}
  }}
  .chata-mov {{ animation: navegar 90s linear infinite; animation-delay: -38s; }}
  @keyframes navegar {{ from {{ transform: translateX(0px); }} to {{ transform: translateX(-{ESC_W + 140:.0f}px); }} }}
"""


CSS_PUENTE = css_puente()


def cuerpo_puente() -> str:
    chars, tonos = rasterizar(campo_puente, P_COLS, P_FILAS, cw=PCW, ch=PCH)
    tensores(chars, tonos)
    rotulos(chars, tonos)
    arte = capas_texto(chars, tonos, P_COLS * PCW, ch=PCH, clase_extra="fino")
    autos_svg, _ = autos()
    movil = (
        f'<clipPath id="recorte-puente"><rect x="0" y="0" width="{ESC_W:.1f}" height="{ESC_H:.1f}"/></clipPath>'
        f'<g clip-path="url(#recorte-puente)">{autos_svg}\n{chata()}</g>'
    )
    return "\n".join([arte, movil, estrellas(), balizas(), terminal()])


TITULO = (
    "Dibujo ASCII del puente General Belgrano entre Chaco y Corrientes de noche, sobre el Paraná, "
    "con autos cruzando, una chata en el río y una terminal que escribe: whoami, danilo benitez, full stack developer"
)

if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("puente.svg")
    destino.write_text(
        envolver(ESC_W, ESC_H, cuerpo_puente(), CSS_TERMINAL + CSS_PUENTE, True, TITULO), encoding="utf-8"
    )
    print(destino)
