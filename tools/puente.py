"""El puente General Belgrano (Chaco–Corrientes) de noche, en ASCII.

Vista lateral sobre el Paraná: Corrientes a la izquierda (barranca alta y la
ciudad), las dos torres con los tensores en abanico, y el viaducto que baja
hacia Resistencia a la derecha. Arriba a la derecha va la terminal que escribe.

Lo usa tools/poster.py. Para verlo suelto: python tools/puente.py <archivo.svg>
"""

from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path

from generar_ascii import (
    CH,
    CSS_TERMINAL,
    CW,
    ESC_COLS,
    ESC_FILAS,
    ESC_H,
    ESC_W,
    TERM_C0,
    TERM_C1,
    TERM_F0,
    TERM_F1,
    _hash,
    capas_texto,
    clamp,
    en_terminal,
    envolver,
    fbm,
    rasterizar,
    terminal,
)

Y_AGUA = 300.0
TORRES = (215.0, 445.0)
TORRE_TOPE = 70.0
Y_TABLERO = 232.0
FIN_ORILLA_CTES = 72.0  # donde el tablero llega a la barranca de Corrientes
INICIO_VIADUCTO = 590.0
PILAS = [120.0, 520.0] + [600.0 + k * 46 for k in range(8)]
LUNA = (70.0, 62.0, 27.0)
CRATERES = [(-9, -6, 6), (8, 5, 5), (-3, 12, 4), (11, -10, 3)]
RAMPA_AGUA = " .-~~="

_rnd = random.Random(3)
EDIFICIOS = []
_x = -4.0
while _x < 150:
    ancho = _rnd.uniform(14, 30)
    alto = _rnd.uniform(18, 66) * (1.0 if _x < 110 else 0.55)
    EDIFICIOS.append((_x, ancho, 246 - alto))
    _x += ancho + _rnd.uniform(1, 4)


def y_tablero(x: float) -> float | None:
    if x < FIN_ORILLA_CTES:
        return None
    if x <= INICIO_VIADUCTO:
        return Y_TABLERO
    return Y_TABLERO + (x - INICIO_VIADUCTO) / (ESC_W - INICIO_VIADUCTO) * 30


def medio_ancho_torre(y: float) -> float:
    t = clamp((y - TORRE_TOPE) / (Y_AGUA - TORRE_TOPE))
    return 5.0 + t * 5.0


def campo_puente(x: float, y: float):
    if en_terminal(x, y):
        return 0.0, None

    # Torres: más claras del lado de la luna (izquierda).
    for xt in TORRES:
        if TORRE_TOPE <= y <= Y_AGUA + 4:
            mw = medio_ancho_torre(y) + (3 if TORRE_TOPE + 4 <= y <= TORRE_TOPE + 16 else 0)
            if abs(x - xt) <= mw:
                v = 0.88 if x < xt else 0.6
                if Y_TABLERO + 12 <= y <= Y_TABLERO + 18:
                    v = 0.95  # viga transversal bajo el tablero
                return v, None

    # Tablero.
    yt = y_tablero(x)
    if yt is not None:
        if yt <= y < yt + 3:
            return 0.95, None
        if yt + 3 <= y < yt + 8:
            return 0.62, None
        if yt + 8 <= y < yt + 11:
            return 0.3, None
        # Pilas del viaducto y de los vanos laterales.
        for xp in PILAS:
            if abs(x - xp) <= 3.2 and yt + 11 <= y <= Y_AGUA + 3:
                return (0.5 if x < xp else 0.3), None

    # Corrientes: barranca y ciudad.
    borde = FIN_ORILLA_CTES + 6 - (y - 244) * 0.25
    if 244 <= y <= Y_AGUA + 2 and x < borde:
        return 0.2 + fbm(x, y, 6, 31) * 0.2, None
    for x0, w, tope in EDIFICIOS:
        if x0 <= x < x0 + w and tope <= y < 246:
            c, r = int(x / CW), int(y / CH)
            if _hash(c, r, 77) < 0.38 and y - tope > 6:
                return 0.9, None  # ventana encendida
            return 0.3 + (0.14 if x - x0 < 3 else 0.0), None

    # Resistencia: monte bajo de la orilla chaqueña.
    copa = 286 - fbm(x, 0, 14, 41) * 18
    if x > 828 and copa <= y <= Y_AGUA + 2:
        return 0.1 + fbm(x, y, 5, 43) * 0.22, None

    # El Paraná: ondas, reflejos de la luna, las torres y el tablero.
    if y > Y_AGUA:
        prof = y - Y_AGUA
        v = 0.03 + fbm(x, y * 7, 46, 51) ** 2 * 0.3
        brillo = fbm(x * 1.6, y * 5, 20, 53)
        lx = LUNA[0]
        if abs(x - lx) < 12 + prof * 0.35 and brillo > 0.5:
            v += 0.8 * (1 - prof / 140)
        for xt in TORRES:
            if abs(x - xt) < 7 + prof * 0.05 and brillo > 0.45 and prof < 85:
                v += 0.5
        if abs(y - (Y_AGUA + (Y_AGUA - Y_TABLERO) - 2)) < 3 and x > FIN_ORILLA_CTES and brillo > 0.4:
            v += 0.28
        return clamp(v), None, RAMPA_AGUA

    # Luna con cráteres y halo.
    lx, ly, lr = LUNA
    d = math.hypot(x - lx, y - ly)
    if d <= lr:
        v = 0.97
        for dx, dy, cr in CRATERES:
            if math.hypot(x - lx - dx, y - ly - dy) < cr:
                v = 0.7
        v -= clamp((x - lx) / lr, 0, 1) * 0.22
        return v, None
    halo = 0.38 * math.exp(-(d - lr) / 18)

    # Cielo con el resplandor de las ciudades sobre el horizonte.
    resplandor = 0.1 * math.exp(-(Y_AGUA - y) / 22)
    return halo + resplandor, None


# ------------------------------------------------------------- superpuestos

def _poner(chars, tonos, c, r, ch, tono, solo_vacio=True):
    if not (0 <= r < ESC_FILAS and 0 <= c < ESC_COLS):
        return
    if en_terminal((c + 0.5) * CW, (r + 0.5) * CH):
        return
    if solo_vacio and chars[r][c] not in " .:":
        return
    chars[r][c] = ch
    tonos[r][c] = tono


def tensores(chars, tonos):
    """Tensores en abanico: 6 por lado y por torre, dibujados con / \\ |."""
    for xt in TORRES:
        for i in range(6):
            ya = TORRE_TOPE + 12 + i * 9
            d = 26 + (5 - i) * 17
            for lado in (-1, 1):
                xd = xt + lado * d
                x0, y0 = xt + lado * 6, ya
                dx_cel = abs(xd - x0) / CW
                dy_cel = abs(Y_TABLERO - y0) / CH
                n = int(max(dx_cel, dy_cel)) + 1
                if dx_cel < dy_cel * 0.35:
                    ch = "|"
                else:
                    ch = "\\" if lado == 1 else "/"
                for k in range(n + 1):
                    t = k / n
                    px, py = x0 + (xd - x0) * t, y0 + (Y_TABLERO - y0) * t
                    _poner(chars, tonos, int(px / CW), int(py / CH), ch, "medio")


def faroles(chars, tonos):
    for c in range(int(FIN_ORILLA_CTES / CW) + 1, ESC_COLS, 5):
        x = (c + 0.5) * CW
        yt = y_tablero(x)
        if yt is None or any(abs(x - xt) < 12 for xt in TORRES):
            continue
        _poner(chars, tonos, c, int((yt - 5) / CH), "'", "claro")


def rotulos(chars, tonos):
    fila = ESC_FILAS - 1
    for i, ch in enumerate("← corrientes"):
        _poner(chars, tonos, 1 + i, fila, ch, "medio", solo_vacio=False)
    texto = "resistencia →"
    for i, ch in enumerate(texto):
        _poner(chars, tonos, ESC_COLS - 1 - len(texto) + i, fila, ch, "medio", solo_vacio=False)


def balizas() -> str:
    """Luces de balizamiento titilando en la punta de cada torre."""
    salida = []
    for i, xt in enumerate(TORRES):
        salida.append(
            f'<text class="acento estrella" x="{xt - CW / 2:.1f}" y="{TORRE_TOPE - 3:.1f}" '
            f'style="animation-delay:{i * 0.9:.1f}s;animation-duration:1.8s">*</text>'
        )
    return "\n".join(salida)


def estrellas() -> str:
    rnd = random.Random(42)
    salida, intentos = [], 0
    while len(salida) < 24 and intentos < 3000:
        intentos += 1
        c, r = rnd.randrange(1, ESC_COLS - 1), rnd.randrange(0, 13)
        x, y = (c + 0.5) * CW, (r + 0.5) * CH
        if TERM_C0 - 2 <= c <= TERM_C1 + 2 and TERM_F0 - 1 <= r <= TERM_F1 + 1:
            continue
        if math.hypot(x - LUNA[0], y - LUNA[1]) < LUNA[2] + 34:
            continue
        if any(abs(x - xt) < 130 and y > TORRE_TOPE - 10 for xt in TORRES):
            continue
        ch = rnd.choice(["*", "+", "·", "*", "✦"])
        salida.append(
            f'<text class="claro estrella" x="{c * CW:.1f}" y="{(r + 1) * CH - 2.5:.1f}" '
            f'style="animation-delay:{rnd.uniform(0, 4):.2f}s;animation-duration:{rnd.uniform(2.5, 5):.2f}s">'
            f"{html.escape(ch)}</text>"
        )
    return "\n".join(salida)


def cuerpo_puente() -> str:
    chars, tonos = rasterizar(campo_puente, ESC_COLS, ESC_FILAS)
    tensores(chars, tonos)
    faroles(chars, tonos)
    rotulos(chars, tonos)
    return "\n".join([capas_texto(chars, tonos, ESC_W), estrellas(), balizas(), terminal()])


TITULO = (
    "Dibujo ASCII del puente General Belgrano entre Chaco y Corrientes de noche, sobre el Paraná, "
    "con una terminal que escribe: whoami, danilo benitez, full stack developer"
)

if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("puente.svg")
    destino.write_text(envolver(ESC_W, ESC_H, cuerpo_puente(), CSS_TERMINAL, True, TITULO), encoding="utf-8")
    print(destino)
