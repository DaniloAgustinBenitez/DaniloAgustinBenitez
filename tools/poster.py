"""Arma el póster del perfil (assets/poster.svg).

Junta en una sola imagen los dibujos ASCII (puente, mate, stack), el panel
de contribuciones y los adornos de estilo póster: paneles de borde fino,
entradas de diccionario, código de barras, grilla deformada, espiral, etc.

Uso:  GITHUB_TOKEN=<token> python tools/poster.py
Lo corre todos los días la GitHub Action para actualizar las contribuciones.
"""

from __future__ import annotations

import html
import math
import os
import random
import textwrap

from contribuciones import CSS as CSS_CONTRIB
from contribuciones import cuerpo_contribuciones, pedir_calendario
from puente import CSS_PUENTE, cuerpo_puente
from generar_ascii import (
    ASSETS,
    COLORES,
    CSS_TERMINAL,
    CSS_MATE,
    FUENTE,

    cuerpo_mate,
    cuerpo_stack,
)

W, H = 960, 2290

FONDO = "#0a0d10"
LINEA = "#3d444d"
PALIDO = "#d2f8da"
TEXTO = "#c9d1d9"
APAGADO = "#7d8590"
V1, V2, V3 = "#7ee787", "#3fb950", "#238636"
SERIF = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"


# ------------------------------------------------------------------ primitivas

def txt(x, y, s, clase, ancla="start", extra=""):
    return f'<text class="{clase}" x="{x:.1f}" y="{y:.1f}" text-anchor="{ancla}"{extra}>{html.escape(s)}</text>'


def panel(x, y, w, h):
    return f'<rect class="p-panel" x="{x}" y="{y}" width="{w}" height="{h}"/>'


def linea_punteada(x1, y, x2):
    return f'<line class="p-punteada" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>'


def chispa(cx, cy, r, color=PALIDO):
    """Estrella de cuatro puntas con lados curvos."""
    k = r * 0.18
    d = (
        f"M{cx},{cy - r} Q{cx + k},{cy - k} {cx + r},{cy} Q{cx + k},{cy + k} {cx},{cy + r} "
        f"Q{cx - k},{cy + k} {cx - r},{cy} Q{cx - k},{cy - k} {cx},{cy - r}Z"
    )
    return f'<path d="{d}" fill="{color}"/>'


def rayado(x, y, w, h, paso=5):
    lineas = "".join(
        f'<line x1="{x + i}" y1="{y + h}" x2="{x + i + h}" y2="{y}"/>' for i in range(-h, w, paso)
    )
    return (
        f'<clipPath id="ray{x}_{y}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>'
        f'<g clip-path="url(#ray{x}_{y})" stroke="{TEXTO}" stroke-width="1.2">{lineas}</g>'
    )


def codigo_barras(x, y, w, h, semilla=7):
    rnd = random.Random(semilla)
    barras, cx = [], x
    while cx < x + w:
        ancho = rnd.choice([1, 1, 2, 2, 3, 4])
        if cx + ancho > x + w:
            break
        barras.append(f'<rect x="{cx}" y="{y}" width="{ancho}" height="{h}"/>')
        cx += ancho + rnd.choice([1, 2, 2, 3])
    return f'<g fill="{TEXTO}">{"".join(barras)}</g>'


def grilla_deformada(x, y, w, h, n=10, amp=7.0, color=TEXTO):
    def punto(u, v):
        px = x + u * w + amp * math.sin(v * math.pi * 2.1 + u * 2.6)
        py = y + v * h + amp * math.sin(u * math.pi * 2.3 + v * 1.7)
        return f"{px:.1f},{py:.1f}"

    pasos = 24
    lineas = []
    for i in range(n + 1):
        t = i / n
        lineas.append(" ".join(punto(k / pasos, t) for k in range(pasos + 1)))
        lineas.append(" ".join(punto(t, k / pasos) for k in range(pasos + 1)))
    polis = "".join(f'<polyline points="{p}"/>' for p in lineas)
    return f'<g fill="none" stroke="{color}" stroke-width="0.8" opacity="0.8">{polis}</g>'


def espiral(cx, cy, r, brazos=3):
    salida = []
    for b in range(brazos):
        pts = []
        for k in range(60):
            t = k / 59
            ang = b * 2 * math.pi / brazos + t * 3.2
            rr = 3 + t * r
            pts.append(f"{cx + rr * math.cos(ang):.1f},{cy + rr * math.sin(ang) * 0.62:.1f}")
        salida.append(f'<polyline points="{" ".join(pts)}"/>')
    rnd = random.Random(5)
    puntos = "".join(
        f'<circle cx="{cx + rnd.gauss(0, r * 0.45):.1f}" cy="{cy + rnd.gauss(0, r * 0.28):.1f}" r="{rnd.uniform(0.5, 1.3):.1f}"/>'
        for _ in range(40)
    )
    return (
        f'<g class="p-gira" style="transform-origin:{cx}px {cy}px">'
        f'<g fill="none" stroke="{V2}" stroke-width="1.1">{"".join(salida)}</g>'
        f'<g fill="{PALIDO}">{puntos}</g></g>'
    )


def anillos(cx, y0, n=10, rx=17, ry=5.5, gap=9):
    elipses = "".join(f'<ellipse cx="{cx}" cy="{y0 + i * gap}" rx="{rx}" ry="{ry}"/>' for i in range(n))
    return f'<g fill="none" stroke="{TEXTO}" stroke-width="0.9">{elipses}</g>'


def circulos(cx, y0, n=7, gap=22, r=4.5):
    return "".join(f'<circle class="p-trazo" cx="{cx}" cy="{y0 + i * gap}" r="{r}"/>' for i in range(n))


def mira(cx, cy, r=7):
    return (
        f'<g class="p-trazo"><circle cx="{cx}" cy="{cy}" r="{r}"/>'
        f'<line x1="{cx - r - 3}" y1="{cy}" x2="{cx + r + 3}" y2="{cy}"/>'
        f'<line x1="{cx}" y1="{cy - r - 3}" x2="{cx}" y2="{cy + r + 3}"/></g>'
    )


def ojo(cx, cy, w=16, h=7):
    return (
        f'<g class="p-trazo"><ellipse cx="{cx}" cy="{cy}" rx="{w}" ry="{h}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{h * 0.55}"/></g>{chispa(cx, cy, h * 0.5, V1)}'
    )


def globo(cx, cy, r=9):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r + 3}" fill="{FONDO}"/>'
        f'<g class="p-trazo"><circle cx="{cx}" cy="{cy}" r="{r}"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r * 0.45}" ry="{r}"/>'
        f'<line x1="{cx - r}" y1="{cy}" x2="{cx + r}" y2="{cy}"/></g>'
    )


def rosa_vientos(cx, cy, r):
    pts = []
    for i in range(16):
        ang = -math.pi / 2 + i * math.pi / 8
        rr = r if i % 4 == 0 else (r * 0.45 if i % 2 == 0 else r * 0.16)
        pts.append(f"{cx + rr * math.cos(ang):.1f},{cy + rr * math.sin(ang):.1f}")
    return (
        f'<circle class="p-trazo" cx="{cx}" cy="{cy}" r="{r * 0.72}"/>'
        f'<circle class="p-trazo" cx="{cx}" cy="{cy}" r="{r * 1.25}" stroke-dasharray="2 3"/>'
        f'<polygon points="{" ".join(pts)}" fill="{V1}"/>'
    )


def pastilla(x, y, s):
    w = len(s) * 7 + 14
    return (
        f'<rect x="{x}" y="{y - 11}" width="{w}" height="16" rx="8" fill="none" stroke="{TEXTO}"/>'
        + txt(x + w / 2, y + 1, s, "p-mono-chico", "middle")
    )


def etiqueta_marco(x, y, s):
    """Rótulo chico apoyado sobre el borde de un panel."""
    w = len(s) * 6.2 + 16
    return (
        f'<rect x="{x}" y="{y - 8}" width="{w:.1f}" height="16" fill="{FONDO}" stroke="{LINEA}"/>'
        + txt(x + 8, y + 3.5, s, "p-mono-chico p-verde")
    )


def parrafos(x, y, textos, ancho=44, interlinea=22, separacion=10, clase="p-cuerpo"):
    salida = []
    for t in textos:
        for linea in textwrap.wrap(t, ancho):
            salida.append(txt(x, y, linea, clase))
            y += interlinea
        y += separacion
    return salida, y


def ascii_en(x, y, escala, cuerpo):
    return f'<g class="ascii" xml:space="preserve" transform="translate({x} {y}) scale({escala})">{cuerpo}</g>'


# ------------------------------------------------------------------ secciones

def titulo():
    s = []
    s.append(txt(28, 40, "El software", "p-italica"))
    s.append(txt(28, 57, "se usa todos los días.", "p-italica"))
    s.append(txt(932, 40, "N.º 001 — 2026", "p-mono-chico", "end"))
    # órbita: la mitad de atrás va antes del título, la de adelante después.
    orbita = f'<ellipse cx="480" cy="130" rx="350" ry="50" fill="none" stroke="{V2}" stroke-width="2.4"/>'
    s.append(f'<g transform="rotate(-7 480 130)">{orbita}</g>')
    s.append(txt(480, 172, "Danilo", "p-titulo", "middle"))
    s.append(
        '<clipPath id="frente"><rect x="0" y="131" width="960" height="120"/></clipPath>'
        f'<g transform="rotate(-7 480 130)" clip-path="url(#frente)">{orbita}</g>'
    )
    s += [chispa(858, 88, 12), chispa(882, 70, 6), chispa(878, 110, 4), chispa(96, 186, 6), chispa(118, 172, 3)]
    for i in range(2):
        for j in range(2):
            s.append(f'<rect x="{30 + i * 8}" y="{200 + j * 8}" width="6" height="6" fill="{TEXTO}"/>')
    s.append(rayado(640, 206, 290, 7))
    s.append(txt(480, 242, "DESARROLLADOR FULL STACK · ARGENTINA", "p-subtitulo", "middle"))
    return s


def seccion_puente():
    s = [panel(24, 262, 912, 412)]
    s.append(ascii_en(42, 274, 0.95, cuerpo_puente()))
    s.append(etiqueta_marco(56, 262, "FIG. 01 — PUENTE GRAL. BELGRANO"))
    s.append(globo(902, 262))
    s.append(
        '<text class="p-vertical" transform="translate(15 468) rotate(-90)" text-anchor="middle">'
        "RESISTENCIA — CORRIENTES · 1973</text>"
    )
    return s


def seccion_sobre_mi():
    s = [panel(24, 694, 500, 420)]
    s.append(txt(46, 772, "código", "p-palabra"))
    s.append(txt(50, 800, "[có·di·go]", "p-mono p-verde"))
    s.append(txt(50, 821, "s. Lo que queda cuando una idea ya funciona.", "p-italica"))
    s.append(linea_punteada(48, 842, 400))
    lineas, _ = parrafos(
        48,
        874,
        [
            "Soy Danilo, desarrollador full stack de Argentina y estudiante de la Tecnicatura "
            "Universitaria en Programación en la UTN.",
            "Me gusta el trabajo de punta a punta: la base de datos, la API, la pantalla, "
            "el deploy y medir que ande rápido.",
            "Busco un puesto como desarrollador full stack o backend.",
        ],
    )
    s += lineas
    s += [chispa(458, 728, 10), chispa(479, 746, 4)]
    s.append(f'<polygon points="458,778 470,798 446,798" fill="none" stroke="{TEXTO}"/>')
    s.append(anillos(458, 828))
    s.append(ojo(458, 940))
    s.append(mira(458, 985))
    s.append(rayado(48, 1088, 130, 6))

    s.append(panel(544, 694, 392, 420))
    s.append(ascii_en(562, 714, 0.84, cuerpo_mate()))
    s.append(txt(566, 738, "mate", "p-palabra-chica"))
    s.append(txt(568, 756, "[má·te]", "p-mono-chico p-verde"))
    s.append(rosa_vientos(890, 752, 18))
    s.append(circulos(914, 852))
    s.append(txt(566, 1066, "$ ./cebar --agua=80°C", "p-mono p-verde"))
    s.append(txt(566, 1086, "# el mate no se apura. el deploy tampoco.", "p-mono p-apagado"))
    return s


PROYECTOS = [
    ("CRM Repuestos Requena", "EN PRODUCCIÓN",
     "Inbox de WhatsApp en tiempo real con IA que arma presupuestos y transcribe audios.",
     "java 21 · spring boot · react · postgresql · equipo de 4", "crmrequena.com"),
    ("mobot", "PILOTO",
     "CRM inmobiliario SaaS: leads, pipeline y unidades por torre en vivo, multi-organización.",
     "spring boot 4 · keycloak · redis · react 19 · row-level security", "código privado"),
    ("Dompri", "EN LÍNEA",
     "Tienda online de impresión 3D con seguimiento de pedidos y panel de ventas.",
     "react 19 · hono · cloudflare d1 · 99 tests · $0/mes de hosting", "dompri.pages.dev"),
    ("EduControl", "OPEN SOURCE",
     "Gestión escolar con inscripciones online y app mobile para tutores y docentes.",
     "laravel · mysql · expo · github actions", "github.com/DaniloAgustinBenitez/EduControl"),
    ("RunicTCG", "UTN",
     "Colecciones de cartas con escaneo, torneos y subastas en tiempo real.",
     "express · prisma · react · socket.io · equipo de 3", "código privado"),
]


def seccion_proyectos():
    y0 = 1134
    s = [panel(24, y0, 912, 476)]
    s.append(txt(48, y0 + 44, "PROYECTOS", "p-seccion"))
    s.append(txt(312, y0 + 43, "→ → →", "p-mono p-verde"))
    for i, x in enumerate((706, 734, 762)):
        s.append(mira(x, y0 + 38, 6) if i != 1 else ojo(x, y0 + 38, 9, 5))
    s.append(pastilla(790, y0 + 42, "20 · 26"))
    s.append(chispa(890, y0 + 36, 7))
    y = y0 + 76
    for i, (nombre, estado, desc, stack, enlace) in enumerate(PROYECTOS):
        s.append(txt(48, y + 22, f"{i + 1:02d}", "p-mono p-verde"))
        s.append(txt(84, y + 22, nombre, "p-proyecto"))
        w = len(estado) * 6.6 + 18
        s.append(f'<rect x="{912 - w:.1f}" y="{y + 9}" width="{w:.1f}" height="17" fill="none" stroke="{V2}"/>')
        s.append(txt(912 - w / 2, y + 21.5, estado, "p-mono-chico p-verde", "middle"))
        s.append(txt(84, y + 45, desc, "p-cuerpo-chico"))
        s.append(txt(84, y + 64, stack, "p-mono p-verde-2"))
        s.append(txt(912, y + 64, enlace, "p-mono-chico p-apagado", "end"))
        if i < len(PROYECTOS) - 1:
            s.append(linea_punteada(48, y + 78, 912))
        y += 80
    return s


def seccion_stack():
    y0 = 1630
    s = [panel(24, y0, 620, 230)]
    s.append(ascii_en(44, y0 + 22, 1.0, cuerpo_stack()))
    s.append(panel(664, y0, 272, 230))
    s.append(grilla_deformada(686, y0 + 22, 228, 136))
    s.append(chispa(906, y0 + 22, 9))
    s.append(txt(686, y0 + 192, "stack", "p-palabra-chica"))
    s.append(txt(764, y0 + 192, "[stak]  s.", "p-mono-chico p-verde"))
    s.append(txt(686, y0 + 212, "las herramientas de todos los días.", "p-italica-chica"))
    return s


def seccion_contribuciones(cal):
    y0 = 1880
    cuerpo, w, h, descripcion = cuerpo_contribuciones(cal)
    s = [panel(24, y0, 912, 200)]
    s.append(ascii_en(24 + (912 - w) / 2, y0 + 24, 1.0, cuerpo))
    s.append(etiqueta_marco(56, y0, "FIG. 02 — ACTIVIDAD · 365 DÍAS"))
    s.append(globo(902, y0))
    return s, descripcion


def pie():
    y0 = 2100
    s = [panel(24, y0, 912, 112)]
    s.append(grilla_deformada(40, y0 + 14, 112, 84, n=7, amp=5))
    s += [chispa(190, y0 + 46, 11), chispa(212, y0 + 28, 5), chispa(176, y0 + 80, 4)]
    for k in range(3):
        s.append(f'<rect class="p-trazo" x="{240 + k * 8}" y="{y0 + 40 + k * 8}" width="22" height="22"/>')
    for k, c in enumerate([PALIDO, V1, V2, V3, "#1b4721"]):
        s.append(f'<rect x="{300 + k * 24}" y="{y0 + 48}" width="18" height="18" fill="{c}"/>')
    s.append(codigo_barras(440, y0 + 24, 170, 46))
    s.append(txt(440, y0 + 86, "SOFTWARE QUE SE USA TODOS LOS DÍAS", "p-mono-mini"))
    s.append(espiral(668, y0 + 56, 34))
    s.append(txt(912, y0 + 36, "Pensalo.", "p-italica-grande", "end"))
    s.append(txt(912, y0 + 61, "Codealo.", "p-italica-grande", "end"))
    s.append(txt(912, y0 + 86, "Deployalo.", "p-italica-grande", "end"))
    s.append(txt(480, y0 + 142,
                 "danilo-benitez.pages.dev  ·  Danilo.A.Benitez@gmail.com  ·  linkedin.com/in/danilobenitez",
                 "p-mono p-apagado", "middle"))
    s.append(txt(480, y0 + 164, "hecho con python, svg y mucho mate", "p-mono-mini p-apagado", "middle"))
    return s


# ------------------------------------------------------------------- armado

CSS_POSTER = f"""
  .ascii text {{ font-family: {FUENTE}; font-size: 11.5px; white-space: pre; }}
  .p-panel {{ fill: none; stroke: {LINEA}; stroke-width: 1; }}
  .p-punteada {{ stroke: {APAGADO}; stroke-dasharray: 2 4; }}
  .p-trazo {{ fill: none; stroke: {TEXTO}; stroke-width: 1; }}
  .p-titulo {{ font-family: {SERIF}; font-size: 150px; font-weight: 700; fill: {PALIDO}; letter-spacing: -3px; filter: url(#grunge); }}
  .p-palabra {{ font-family: {SERIF}; font-size: 66px; font-weight: 700; fill: {PALIDO}; filter: url(#grunge); }}
  .p-palabra-chica {{ font-family: {SERIF}; font-size: 26px; font-weight: 700; fill: {PALIDO}; }}
  .p-seccion {{ font-family: {SERIF}; font-size: 22px; fill: {PALIDO}; letter-spacing: 12px; }}
  .p-proyecto {{ font-family: {SERIF}; font-size: 19px; font-weight: 700; fill: {PALIDO}; }}
  .p-cuerpo {{ font-family: {SERIF}; font-size: 15px; fill: {TEXTO}; }}
  .p-cuerpo-chico {{ font-family: {SERIF}; font-size: 14.5px; fill: {TEXTO}; }}
  .p-italica {{ font-family: {SERIF}; font-size: 13.5px; font-style: italic; fill: {TEXTO}; }}
  .p-italica-chica {{ font-family: {SERIF}; font-size: 12.5px; font-style: italic; fill: {APAGADO}; }}
  .p-italica-grande {{ font-family: {SERIF}; font-size: 19px; font-style: italic; fill: {PALIDO}; }}
  .p-subtitulo {{ font-family: {FUENTE}; font-size: 12px; letter-spacing: 5px; fill: {APAGADO}; }}
  .p-mono {{ font-family: {FUENTE}; font-size: 11.5px; fill: {TEXTO}; }}
  .p-mono-chico {{ font-family: {FUENTE}; font-size: 10px; letter-spacing: 1px; fill: {TEXTO}; }}
  .p-mono-mini {{ font-family: {FUENTE}; font-size: 8.5px; letter-spacing: 1.5px; fill: {TEXTO}; }}
  .p-vertical {{ font-family: {FUENTE}; font-size: 9px; letter-spacing: 3px; fill: {APAGADO}; }}
  .p-verde {{ fill: {V1}; }}
  .p-verde-2 {{ fill: {V2}; }}
  .p-apagado {{ fill: {APAGADO}; }}
  .p-gira {{ animation: girar 40s linear infinite; }}
  @keyframes girar {{ to {{ transform: rotate(360deg); }} }}
"""

FILTROS = """
<filter id="grunge" x="-5%" y="-5%" width="110%" height="110%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" result="ruido"/>
  <feColorMatrix in="ruido" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -6.5 4.3" result="mascara"/>
  <feComposite in="SourceGraphic" in2="mascara" operator="in"/>
</filter>
<filter id="grano" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="9"/>
  <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.09 -0.02"/>
</filter>
"""


def armar(cal) -> str:
    contrib, descripcion = seccion_contribuciones(cal)
    partes = titulo() + seccion_puente() + seccion_sobre_mi() + seccion_proyectos() + seccion_stack() + contrib + pie()
    colores = "\n".join(f"  .{k} {{ fill: {v}; }}" for k, v in COLORES.items())
    css = colores + CSS_TERMINAL + CSS_MATE + CSS_CONTRIB + CSS_PUENTE + CSS_POSTER
    resumen = (
        "Póster del perfil de Danilo Agustín Benitez, desarrollador full stack de Argentina. "
        "Proyectos: CRM Repuestos Requena, mobot, Dompri, EduControl y RunicTCG. "
        "Stack: Java, Spring Boot, React, TypeScript, PostgreSQL, Redis, Docker. " + descripcion
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{html.escape(resumen)}">
<title>{html.escape(resumen)}</title>
<defs>{FILTROS}</defs>
<style>
{css}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .letra, .cursor, .col {{ opacity: 1; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{FONDO}" stroke="{LINEA}"/>
{chr(10).join(partes)}
<rect x="0" y="0" width="{W}" height="{H}" rx="14" filter="url(#grano)" pointer-events="none"/>
</svg>
"""


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Falta la variable de entorno GITHUB_TOKEN")
    cal = pedir_calendario(token)
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "poster.svg").write_text(armar(cal), encoding="utf-8", newline="\n")
    print(f"assets/poster.svg ({cal['totalContributions']} contribuciones)")


if __name__ == "__main__":
    main()
