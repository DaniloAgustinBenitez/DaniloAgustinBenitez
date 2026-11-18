"""Genera los dibujos ASCII del README de perfil (assets/*.svg).

Cada dibujo se define como un campo de luz (0 = oscuro, 1 = luz plena) en
coordenadas de píxel del SVG. El campo se muestrea por celda de carácter, se
tramea con una matriz de Bayer y se convierte en caracteres de más o menos
"densidad". El resultado es texto monoespaciado dentro de un SVG animado.

Es la biblioteca de dibujos del póster (tools/poster.py).
Para ver cada pieza suelta: python tools/generar_ascii.py <carpeta>
"""

from __future__ import annotations

import html
import math
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"

# Celda de carácter en unidades del SVG (proporción típica de una monoespaciada).
CW, CH = 7.2, 12.0
FUENTE = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"
RAMPA = " .:-=+*#%@"

BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]

# Colores por tono (sobre fondo oscuro de GitHub).
COLORES = {
    "tenue": "#3d444d",
    "medio": "#7d8590",
    "claro": "#e6edf3",
    "yerba": "#3fb950",
    "acento": "#7ee787",
}
FONDO_TARJETA = "#0d1117"
BORDE_TARJETA = "#30363d"


# ---------------------------------------------------------------- utilidades

def _hash(ix: int, iy: int, semilla: int) -> float:
    n = ix * 374761393 + iy * 668265263 + semilla * 1442695041
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFFFF) / 0xFFFFFF


def ruido(x: float, y: float, escala: float, semilla: int = 1) -> float:
    """Ruido de valor suave en [0, 1]."""
    x, y = x / escala, y / escala
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, semilla)
    b = _hash(ix + 1, iy, semilla)
    c = _hash(ix, iy + 1, semilla)
    d = _hash(ix + 1, iy + 1, semilla)
    return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy


def fbm(x: float, y: float, escala: float, semilla: int = 1, octavas: int = 3) -> float:
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octavas):
        total += ruido(x, y, escala / (2 ** o), semilla + o) * amp
        norm += amp
        amp *= 0.5
    return total / norm


def clamp(v: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, v))


def rasterizar(campo, cols: int, filas: int, sub: int = 3):
    """Devuelve (caracteres, tonos) como listas de listas."""
    chars, tonos = [], []
    for r in range(filas):
        fila_c, fila_t = [], []
        for c in range(cols):
            total, clase = 0.0, None
            for sy in range(sub):
                for sx in range(sub):
                    px = (c + (sx + 0.5) / sub) * CW
                    py = (r + (sy + 0.5) / sub) * CH
                    v, k = campo(px, py)
                    total += v
                    if sx == sub // 2 and sy == sub // 2:
                        clase = k
            v = clamp(total / (sub * sub))
            if v < 0.05:
                v = 0.0  # sin trama en el cielo casi negro
            umbral = (BAYER[r % 4][c % 4] + 0.5) / 16 - 0.5
            idx = int(round(clamp(v * (len(RAMPA) - 1) + umbral * 0.9, 0, len(RAMPA) - 1)))
            ch = RAMPA[idx]
            if clase is None:
                clase = "tenue" if v < 0.24 else ("medio" if v < 0.58 else "claro")
            fila_c.append(ch)
            fila_t.append(clase)
        chars.append(fila_c)
        tonos.append(fila_t)
    return chars, tonos


def capas_texto(chars, tonos, ancho: float) -> str:
    """Una capa de <text> por tono; cada fila ocupa exactamente el ancho total."""
    salida = []
    for tono in COLORES:
        for r, (fila_c, fila_t) in enumerate(zip(chars, tonos)):
            s = "".join(ch if t == tono else " " for ch, t in zip(fila_c, fila_t))
            if not s.strip():
                continue
            y = (r + 1) * CH - 2.5
            salida.append(
                f'<text class="{tono}" x="0" y="{y:.1f}" textLength="{ancho:.1f}" '
                f'lengthAdjust="spacingAndGlyphs">{html.escape(s)}</text>'
            )
    return "\n".join(salida)


def envolver(ancho: float, alto: float, cuerpo: str, css_extra: str, tarjeta: bool, titulo: str) -> str:
    colores = "\n".join(f"  .{k} {{ fill: {v}; }}" for k, v in COLORES.items())
    pad = 14 if tarjeta else 0
    fondo = ""
    if tarjeta:
        fondo = (
            f'<rect x="{-pad + 0.5}" y="{-pad + 0.5}" width="{ancho + 2 * pad - 1:.1f}" '
            f'height="{alto + 2 * pad - 1:.1f}" rx="12" fill="{FONDO_TARJETA}" stroke="{BORDE_TARJETA}"/>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {ancho + 2 * pad:.1f} {alto + 2 * pad:.1f}" width="{ancho + 2 * pad:.0f}" height="{alto + 2 * pad:.0f}" role="img" aria-label="{html.escape(titulo)}">
<title>{html.escape(titulo)}</title>
<style>
  text {{ font-family: {FONDO_FUENTE}; font-size: 11.5px; white-space: pre; }}
{colores}
{css_extra}
  @media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; }}
  }}
</style>
{fondo}
<g xml:space="preserve">
{cuerpo}
</g>
</svg>
"""


FONDO_FUENTE = FUENTE.replace("'", "&apos;")


# ------------------------------------------------------------- la cordillera

CORD_COLS, CORD_FILAS = 128, 34
CORD_W, CORD_H = CORD_COLS * CW, CORD_FILAS * CH

LUNA = (150.0, 92.0, 36.0)
CRATERES = [(-12, -8, 8), (10, 6, 6), (-4, 16, 5), (15, -14, 4)]

# Terminal (en celdas): columna/fila de inicio y fin, inclusive.
TERM_C0, TERM_C1, TERM_F0, TERM_F1 = 66, 123, 1, 11

PICOS_FONDO = [(60, 228), (235, 185), (410, 212), (585, 150), (760, 196), (905, 226)]
PICOS_MEDIO = [(0, 292), (150, 262), (330, 282), (500, 255), (690, 276), (870, 260)]


def _cresta(x: float, picos, pendiente: float, semilla: int):
    """Altura (y) de la cresta y el pico dominante en x."""
    mejor_y, mejor = 1e9, None
    for xc, yc in picos:
        y = yc + abs(x - xc) * pendiente
        if y < mejor_y:
            mejor_y, mejor = y, (xc, yc)
    mejor_y += (fbm(x, semilla * 50, 40, semilla) - 0.5) * 14
    return mejor_y, mejor


def campo_cordillera(x: float, y: float):
    # Terminal: se deja limpio para dibujar el marco encima.
    if TERM_C0 * CW - CW <= x <= (TERM_C1 + 2) * CW and TERM_F0 * CH - CH * 0.5 <= y <= (TERM_F1 + 1.5) * CH:
        return 0.0, None

    # Cerros del frente: lomas suaves, casi siluetas.
    y_frente = 352 + math.sin(x / 95) * 12 + math.sin(x / 37 + 1) * 5
    if y >= y_frente:
        return 0.04 + fbm(x, y, 16, 7) ** 2 * 0.42, None

    # Cordón medio.
    y_medio, pico = _cresta(x, PICOS_MEDIO, 0.5, 3)
    if y >= y_medio:
        iluminado = x < pico[0]
        base = 0.4 if iluminado else 0.2
        return base + (fbm(x, y, 14, 11) - 0.5) * 0.24, None

    # Cordillera del fondo, con nieve en las cumbres.
    y_fondo, pico = _cresta(x, PICOS_FONDO, 0.78, 5)
    if y >= y_fondo:
        iluminado = x < pico[0]
        prof = y - y_fondo
        limite_nieve = 22 + (pico[1] < 200) * 18 + (fbm(x, y, 9, 13) - 0.5) * 18
        if prof < limite_nieve and y < 250:
            return (0.95 if iluminado else 0.66), None
        base = 0.72 if iluminado else 0.42
        return base + (fbm(x, y, 11, 17) - 0.5) * 0.22, None

    # Luna con cráteres y halo.
    lx, ly, lr = LUNA
    d = math.hypot(x - lx, y - ly)
    if d <= lr:
        v = 0.97
        for dx, dy, cr in CRATERES:
            if math.hypot(x - lx - dx, y - ly - dy) < cr:
                v = 0.7
        # sombra suave del lado derecho
        v -= clamp((x - lx) / lr, 0, 1) * 0.22
        return v, None
    halo = 0.38 * math.exp(-(d - lr) / 20)

    # Cielo: casi negro, apenas más claro cerca del horizonte.
    cielo = 0.11 * (y / CORD_H) ** 3
    return cielo + halo, None


def estrellas_cordillera() -> str:
    rnd = random.Random(42)
    salida = []
    intentos = 0
    while len(salida) < 26 and intentos < 2000:
        intentos += 1
        c, r = rnd.randrange(1, CORD_COLS - 1), rnd.randrange(0, 13)
        x, y = (c + 0.5) * CW, (r + 0.5) * CH
        if TERM_C0 - 2 <= c <= TERM_C1 + 2 and TERM_F0 - 1 <= r <= TERM_F1 + 1:
            continue
        if math.hypot(x - LUNA[0], y - LUNA[1]) < LUNA[2] + 40:
            continue
        if y > _cresta(x, PICOS_FONDO, 0.78, 5)[0] - 10:
            continue
        ch = rnd.choice(["*", "+", "·", "*", "✦"])
        demora = rnd.uniform(0, 4)
        dur = rnd.uniform(2.5, 5)
        salida.append(
            f'<text class="claro estrella" x="{c * CW:.1f}" y="{(r + 1) * CH - 2.5:.1f}" '
            f'style="animation-delay:{demora:.2f}s;animation-duration:{dur:.2f}s">{html.escape(ch)}</text>'
        )
    return "\n".join(salida)


LINEAS_TERMINAL = [
    ("prompt", "$ whoami"),
    ("salida", "danilo benitez — full stack developer"),
    ("prompt", "$ cat stack.txt"),
    ("salida", "java · spring boot · react · typescript"),
    ("prompt", "$ ./deploy --prod"),
    ("ok", "✓ en producción, todos los días"),
]


def marco(c0: int, c1: int, f0: int, f1: int, titulo: str) -> list[str]:
    """Ventana de terminal dibujada con caracteres de caja (columnas/filas inclusive)."""
    ancho_cel = c1 - c0 + 1
    titulo = f" {titulo} "
    controles = " ─ □ × "
    relleno = ancho_cel - 2 - len(titulo) - len(controles) - 1
    filas = ["┌─" + titulo + "─" * relleno + controles + "┐"]
    for _ in range(f0 + 1, f1):
        filas.append("│" + " " * (ancho_cel - 2) + "│")
    filas.append("└" + "─" * (ancho_cel - 2) + "┘")

    salida = []
    ancho = ancho_cel * CW
    for i, fila in enumerate(filas):
        y = (f0 + i + 1) * CH - 2.5
        salida.append(
            f'<text class="marco" x="{c0 * CW:.1f}" y="{y:.1f}" textLength="{ancho:.1f}" '
            f'lengthAdjust="spacingAndGlyphs">{html.escape(fila)}</text>'
        )
    return salida


def tipear(texto: str, clase: str, x0: float, y: float, inicio: float, paso: float) -> list[str]:
    """Una <text> por letra, cada una aparece con su demora (efecto de tipeo)."""
    salida = []
    for k, ch in enumerate(texto):
        if ch != " ":
            salida.append(
                f'<text class="{clase} letra" x="{x0 + k * CW:.1f}" y="{y:.1f}" '
                f'style="animation-delay:{inicio + k * paso:.3f}s">{html.escape(ch)}</text>'
            )
    return salida


def terminal() -> str:
    c0, c1, f0, f1 = TERM_C0, TERM_C1, TERM_F0, TERM_F1
    salida = marco(c0, c1, f0, f1, "danilo@argentina: ~")

    # Texto que se va escribiendo, letra por letra (cada letra aparece con su demora).
    tiempo = 0.6
    x0 = (c0 + 2) * CW
    for i, (tipo, texto) in enumerate(LINEAS_TERMINAL):
        y = (f0 + 3 + i) * CH - 2.5
        paso = 0.06 if tipo == "prompt" else 0.018
        salida += tipear(texto, tipo, x0, y, tiempo, paso)
        tiempo += len(texto) * paso + (0.3 if tipo == "prompt" else 0.55)

    # Cursor parpadeante después de la última línea.
    fila = f0 + 2 + len(LINEAS_TERMINAL)
    salida.append(
        f'<text class="acento cursor" x="{x0:.1f}" y="{(fila + 1) * CH - 2.5:.1f}" '
        f'style="animation-delay:{tiempo:.2f}s">$ █</text>'
    )
    return "\n".join(salida)


CSS_CORDILLERA = """
  .marco { fill: #7d8590; }
  .prompt { fill: #7ee787; }
  .salida { fill: #e6edf3; }
  .ok { fill: #7ee787; }
  .estrella { animation: titilar 4s ease-in-out infinite; }
  .letra { opacity: 0; animation: aparecer 0.01s forwards; }
  .cursor { opacity: 0; animation: aparecer 0.01s forwards, parpadear 1.1s steps(1) infinite; }
  @keyframes titilar { 0%, 100% { opacity: 1; } 50% { opacity: 0.15; } }
  @keyframes aparecer { to { opacity: 1; } }
  @keyframes parpadear { 50% { fill-opacity: 0; } }
"""


def cuerpo_cordillera() -> str:
    chars, tonos = rasterizar(campo_cordillera, CORD_COLS, CORD_FILAS)
    return capas_texto(chars, tonos, CORD_W) + "\n" + estrellas_cordillera() + "\n" + terminal()


def generar_cordillera(tarjeta: bool) -> str:
    cuerpo = cuerpo_cordillera()
    titulo = "Dibujo ASCII de la cordillera de noche con una terminal que escribe: whoami, danilo benitez, full stack developer"
    return envolver(CORD_W, CORD_H, cuerpo, CSS_CORDILLERA, tarjeta, titulo)


# -------------------------------------------------------------- el tech stack

STACK = [
    ("backend", "java · spring boot · node.js · express · hono"),
    ("frontend", "react · typescript · tailwind · tanstack query"),
    ("datos", "postgresql · redis · mysql · prisma"),
    ("tiempo-real", "websocket / stomp · socket.io"),
    ("seguridad", "keycloak · row-level security"),
    ("infra", "docker · github actions · cloudflare · railway"),
    ("observabilidad", "prometheus · grafana · k6"),
    ("testing", "junit · testcontainers · vitest · playwright"),
    ("ia", "openai gpt-4o · whisper"),
]
STACK_COLS = 80
STACK_FILAS = len(STACK) + 6


def generar_stack(tarjeta: bool) -> str:
    titulo = "Tech stack: " + "; ".join(f"{c}: {i}" for c, i in STACK)
    return envolver(STACK_COLS * CW, STACK_FILAS * CH, cuerpo_stack(), CSS_CORDILLERA, tarjeta, titulo)


def cuerpo_stack() -> str:
    c1, f1 = STACK_COLS - 1, STACK_FILAS - 1
    salida = marco(0, c1, 0, f1, "danilo@argentina: ~/stack")
    x0 = 2 * CW

    comando = "$ tree --dirsfirst ~/stack"
    tiempo = 0.4
    salida += tipear(comando, "prompt", x0, 3 * CH - 2.5, tiempo, 0.05)
    tiempo += len(comando) * 0.05 + 0.35

    ancho_carpeta = max(len(c) for c, _ in STACK) + 2
    for i, (carpeta, items) in enumerate(STACK):
        y = (4 + i) * CH - 2.5
        rama = "└── " if i == len(STACK) - 1 else "├── "
        demora = f'style="animation-delay:{tiempo:.2f}s"'
        salida.append(f'<text class="marco letra" x="{x0:.1f}" y="{y:.1f}" {demora}>{rama}</text>')
        salida.append(
            f'<text class="prompt letra" x="{x0 + 4 * CW:.1f}" y="{y:.1f}" {demora}>{html.escape(carpeta)}/</text>'
        )
        salida.append(
            f'<text class="salida letra" x="{x0 + (4 + ancho_carpeta) * CW:.1f}" y="{y:.1f}" '
            f'{demora}>{html.escape(items)}</text>'
        )
        tiempo += 0.12

    y = (4 + len(STACK) + 1) * CH - 2.5
    resumen = f"{len(STACK)} directorios, {sum(len(i.split(' · ')) for _, i in STACK)} herramientas"
    salida.append(
        f'<text class="marco letra" x="{x0:.1f}" y="{y:.1f}" style="animation-delay:{tiempo:.2f}s">'
        f'{html.escape(resumen)}</text>'
    )
    salida.append(
        f'<text class="acento cursor" x="{x0 + (len(resumen) + 2) * CW:.1f}" y="{y:.1f}" '
        f'style="animation-delay:{tiempo + 0.3:.2f}s">$ █</text>'
    )

    return "\n".join(salida)


# ------------------------------------------------------------------- el mate

MATE_COLS, MATE_FILAS = 56, 31
MATE_W, MATE_H = MATE_COLS * CW, MATE_FILAS * CH
MCX = 190.0
LUZ = (-0.55, -0.6, 0.58)


def _normal_elipse(x, y, cx, cy, rx, ry):
    nx, ny = (x - cx) / rx, (y - cy) / ry
    q = nx * nx + ny * ny
    if q > 1:
        return None
    nz = math.sqrt(1 - q)
    return nx, ny, nz


def _lambert(n):
    lx, ly, lz = LUZ
    norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    return max(0.0, (n[0] * lx + n[1] * ly + n[2] * lz) / norm)


def _bombilla(x, y):
    # Segmento recto desde la yerba hacia arriba a la derecha, y la boquilla.
    ax, ay, bx, by = MCX + 26, 128, MCX + 112, 34
    vx, vy = bx - ax, by - ay
    t = clamp(((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy))
    d = math.hypot(x - (ax + vx * t), y - (ay + vy * t))
    if d < 5.5:
        return 0.98 if d < 2.5 else 0.72
    # boquilla doblada
    cx, cy = bx + 16, by - 6
    if math.hypot(x - cx, y - cy) < 6 or (bx <= x <= cx and abs(y - (by + (cy - by) * (x - bx) / 16)) < 5):
        return 0.9
    return None


def campo_mate(x, y):
    # Bombilla por encima de todo.
    b = _bombilla(x, y)
    if b is not None and y < 132:
        return b, None

    # Boca: elipse con la yerba.
    if _normal_elipse(x, y, MCX, 128, 70, 15):
        if b is not None:
            return b, None
        v = 0.3 + fbm(x, y, 5, 21) * 0.4
        return v, "yerba"

    # Virola (borde metálico) debajo de la boca.
    if 128 <= y <= 150 and _normal_elipse(x, y, MCX, 139, 76, 28) and not _normal_elipse(x, y, MCX, 128, 70, 15):
        rayas = 0.12 if int(x / 10) % 3 == 0 else 0.0
        return 0.88 - rayas - clamp((x - MCX) / 76, 0, 1) * 0.3, None

    # Cuerpo: cuello + panza, unidos.
    n = _normal_elipse(x, y, MCX, 252, 122, 112)
    if n is None and y >= 140:
        n = _normal_elipse(x, y, MCX, 178, 80, 60)
    if n is not None:
        v = 0.12 + 0.82 * _lambert(n)
        if n[2] < 0.32:
            v = max(v, 0.4)  # contorno para que no se pierda el lado oscuro
        # pirograbado: una guarda en zigzag sobre la panza
        if 214 <= y <= 236:
            zig = abs(((x / 14) % 2) - 1) * 16 + 217
            if abs(y - zig) < 2.4:
                v = max(v, 0.78) if v > 0.3 else 0.55
        return v, None

    # Sombra en la mesa.
    if _normal_elipse(x, y, MCX + 18, 366, 150, 7):
        return 0.16, None
    return 0.0, None


CSS_MATE = """
  .vapor { fill: #7d8590; opacity: 0; animation: subir 4.5s ease-out infinite; }
  @keyframes subir {
    0% { opacity: 0; transform: translate(0, 0); }
    25% { opacity: 0.9; }
    100% { opacity: 0; transform: translate(-6px, -42px); }
  }
"""


def vapor() -> str:
    hilos = [
        (MCX - 40, 106, ["(", " )", "(", " )"], 0.0),
        (MCX - 14, 100, [")", "(", " )", "("], 1.5),
        (MCX - 56, 110, ["~", " ~", "~"], 3.0),
    ]
    salida = []
    for x, y, trazos, demora in hilos:
        for i, t in enumerate(trazos):
            salida.append(
                f'<text class="vapor" x="{x:.1f}" y="{y - i * CH:.1f}" '
                f'style="animation-delay:{demora + i * 0.25:.2f}s">{html.escape(t)}</text>'
            )
    return "\n".join(salida)


def cuerpo_mate() -> str:
    chars, tonos = rasterizar(campo_mate, MATE_COLS, MATE_FILAS)
    return capas_texto(chars, tonos, MATE_W) + "\n" + vapor()


def generar_mate(tarjeta: bool) -> str:
    titulo = "Dibujo ASCII de un mate con bombilla y vapor"
    return envolver(MATE_W, MATE_H, cuerpo_mate(), CSS_MATE, tarjeta, titulo)


# --------------------------------------------------------------------- main

def main() -> None:
    """Escribe cada pieza suelta (para previsualizarla) en la carpeta indicada."""
    import sys

    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, gen in (("cordillera", generar_cordillera), ("mate", generar_mate), ("stack", generar_stack)):
        (destino / f"{nombre}.svg").write_text(gen(True), encoding="utf-8")
        print(destino / f"{nombre}.svg")


if __name__ == "__main__":
    main()
