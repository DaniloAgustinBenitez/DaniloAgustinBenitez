"""Gráfico de contribuciones del último año en ASCII.

Pide el calendario de contribuciones a la API GraphQL de GitHub y arma el
panel de contribuciones del póster (lo usa tools/poster.py).
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.request

from generar_ascii import CH, CW

USUARIO = os.environ.get("PERFIL", "DaniloAgustinBenitez")

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

NIVELES = {
    "NONE": ("·", "n0"),
    "FIRST_QUARTILE": (":", "n1"),
    "SECOND_QUARTILE": ("+", "n2"),
    "THIRD_QUARTILE": ("#", "n3"),
    "FOURTH_QUARTILE": ("@", "n4"),
}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = {1: "lun", 3: "mié", 5: "vie"}

CSS = """
  .n0 { fill: #30363d; }
  .n1 { fill: #238636; }
  .n2 { fill: #2ea043; }
  .n3 { fill: #3fb950; }
  .n4 { fill: #7ee787; }
  .titulo { fill: #e6edf3; }
  .rotulo { fill: #7d8590; }
  .dato { fill: #7ee787; }
  .col { opacity: 0; animation: aparecer 0.35s ease-out forwards; }
  @keyframes aparecer { to { opacity: 1; } }
"""

MARGEN_IZQ = 6  # columnas para "lun  "


def pedir_calendario(token: str) -> dict:
    cuerpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=cuerpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        datos = json.load(resp)
    if "errors" in datos:
        raise SystemExit(f"Error de la API de GitHub: {datos['errors']}")
    return datos["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def rachas(dias: list[dict], hoy: dt.date) -> tuple[int, int]:
    """Racha más larga y racha actual (si hoy todavía no hay contribuciones, cuenta desde ayer)."""
    pasados = [d for d in dias if dt.date.fromisoformat(d["date"]) <= hoy]
    larga = actual = 0
    for d in pasados:
        actual = actual + 1 if d["contributionCount"] > 0 else 0
        larga = max(larga, actual)
    actual = 0
    for i, d in enumerate(reversed(pasados)):
        if d["contributionCount"] > 0:
            actual += 1
        elif i > 0 or dt.date.fromisoformat(d["date"]) != hoy:
            break
    return larga, actual


def t(x_col: float, fila: int, texto: str, clase: str, extra: str = "") -> str:
    return f'<text class="{clase}" x="{x_col * CW:.1f}" y="{(fila + 1) * CH - 2.5:.1f}"{extra}>{html.escape(texto)}</text>'


def cuerpo_contribuciones(cal: dict) -> tuple[str, float, float, str]:
    """Devuelve (svg interno, ancho, alto, descripción)."""
    semanas = cal["weeks"]
    dias = [d for s in semanas for d in s["contributionDays"]]
    hoy = dt.date.fromisoformat(dias[-1]["date"])
    total = cal["totalContributions"]
    larga, actual = rachas(dias, hoy)
    mejor = max(dias, key=lambda d: d["contributionCount"])
    mejor_fecha = dt.date.fromisoformat(mejor["date"])

    cols = MARGEN_IZQ + len(semanas) * 2
    filas = 13
    salida = []

    # Encabezado.
    salida.append(t(0, 0, "$ git log --since='1 year ago' | contribuciones", "dato"))
    total_txt = f"{total} contribuciones"
    salida.append(t(cols - len(total_txt), 0, total_txt, "titulo"))

    # Rótulos de los días.
    for wd, nombre in DIAS.items():
        salida.append(t(0, 2 + wd, nombre, "rotulo"))

    # Grilla: una columna por semana, aparecen de izquierda a derecha.
    ultimo_mes, ultima_col = None, -10
    for i, semana in enumerate(semanas):
        x = MARGEN_IZQ + i * 2
        celdas = []
        for d in semana["contributionDays"]:
            ch, clase = NIVELES[d["contributionLevel"]]
            celdas.append(t(x, 2 + d["weekday"], ch, clase))
        salida.append(f'<g class="col" style="animation-delay:{i * 0.025:.3f}s">{"".join(celdas)}</g>')

        # Rótulo del mes en la semana donde empieza (si no pisa al anterior).
        for d in semana["contributionDays"]:
            fecha = dt.date.fromisoformat(d["date"])
            if fecha.day == 1 and fecha.month != ultimo_mes and x - ultima_col >= 8:
                salida.append(t(x, 10, MESES[fecha.month - 1], "rotulo"))
                ultimo_mes, ultima_col = fecha.month, x

    # Pie: rachas y leyenda.
    pie = [
        ("racha más larga ", "rotulo"), (f"{larga} día{'s' if larga != 1 else ''}", "dato"),
        ("  ·  racha actual ", "rotulo"), (f"{actual} día{'s' if actual != 1 else ''}", "dato"),
        ("  ·  mejor día ", "rotulo"),
        (f"{mejor['contributionCount']} ({mejor_fecha.day} {MESES[mejor_fecha.month - 1]})", "dato"),
    ]
    x = 0
    for texto, clase in pie:
        salida.append(t(x, 12, texto, clase))
        x += len(texto)
    leyenda = [("menos ", "rotulo"), ("· ", "n0"), (": ", "n1"), ("+ ", "n2"), ("# ", "n3"), ("@ ", "n4"), ("más", "rotulo")]
    x = cols - sum(len(s) for s, _ in leyenda)
    for texto, clase in leyenda:
        salida.append(t(x, 12, texto, clase))
        x += len(texto)

    titulo = (
        f"Contribuciones de {USUARIO} en el último año: {total}. "
        f"Racha más larga {larga} días, racha actual {actual} días."
    )
    return "\n".join(salida), cols * CW, filas * CH, titulo
