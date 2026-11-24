"""Evalúa la calidad de Articla con una batería fija de preguntas y artículos esperados.

Uso (con los contenedores arriba):
    docker compose exec api python scripts/evaluar.py            # toda la batería
    docker compose exec api python scripts/evaluar.py --max 5    # solo las primeras 5

Cada pregunta pasa por el mismo servicio que usa la página, pero sin caché, para medir la búsqueda y la
redacción de verdad. Por cada pregunta se registra:
- norma: alguna cita es de una norma esperada;
- artículo: alguna cita es exactamente un artículo esperado;
- modo: 'ia' si Gemini redactó, 'extractiva' si se usó el respaldo;
- tiempo en segundos.
El resultado queda en data/evaluacion.md (tabla para el informe) y data/evaluacion.json.
Las respuestas se guardan con la sesión 'evaluacion-articla' y nunca se reutilizan en el caché.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.config import get_database_url  # noqa: E402
from app.ia.embeddings import Vectorizador  # noqa: E402
from app.ia.gemini import ClienteGemini  # noqa: E402
from app.repositories import consultas_repository  # noqa: E402
from app.services import consultas_service as service  # noqa: E402

SESION = "evaluacion-articla"
PAUSA_S = 8          # la capa gratuita de Gemini limita las peticiones por minuto

# (pregunta, normas aceptadas, artículos esperados). Un artículo terminado en * acepta cualquier
# artículo que empiece así (p. ej. "211*" acepta 211-A, 211-B, 211-C...). Lista vacía = solo se mide la norma.
BATERIA = [
    ("¿Me pueden subir el arriendo a mitad de contrato?", ["codigo civil", "ley 18101"], ["1545"]),
    ("El papá de mi hijo no paga la pensión de alimentos, ¿qué hago?", ["ley 14908"], []),
    ("¿Cuál es el monto mínimo de una pensión de alimentos para un hijo?", ["ley 14908"], ["3"]),
    ("¿Cuántos días de vacaciones me corresponden al año?", ["codigo del trabajo"], ["67"]),
    ("Me despidieron sin causa justificada, ¿cuánto me tienen que pagar de indemnización?", ["codigo del trabajo"], ["163", "168"]),
    ("¿Con cuánta anticipación me tienen que avisar si me despiden?", ["codigo del trabajo"], ["161", "162"]),
    ("¿Qué tiene que hacer mi empleador si denuncio acoso laboral por la Ley Karin?", ["codigo del trabajo"], ["211*"]),
    ("¿Cómo se pagan las horas extra?", ["codigo del trabajo"], ["32"]),
    ("¿Cuántas horas a la semana puedo trabajar como máximo?", ["codigo del trabajo"], ["22"]),
    ("¿Cuánto dura el postnatal?", ["codigo del trabajo"], ["195", "197 bis"]),
    ("¿En cuántos días me tienen que pagar el finiquito?", ["codigo del trabajo"], ["177"]),
    ("Compré algo por internet y me arrepentí, ¿lo puedo devolver?", ["ley 19496"], ["3 bis"]),
    ("El producto que compré salió malo a la semana, ¿qué puedo exigir?", ["ley 19496"], ["19", "20", "21"]),
    ("Mi pareja me agrede en la casa, ¿qué dice la ley?", ["ley 20066"], []),
    ("¿Qué necesito para divorciarme?", ["ley 19947"], ["54", "55"]),
    ("Mi papá murió sin testamento, ¿quiénes heredan?", ["codigo civil"], ["980", "983", "988", "989", "990"]),
    ("Mi arrendatario no me paga el arriendo, ¿cómo lo desalojo?", ["ley 18101", "ley 21461"], []),
    ("¿Qué porcentaje de mi sueldo se descuenta para la AFP?", ["dl 3500"], ["17"]),
    ("Quedé sin trabajo, ¿cómo cobro el seguro de cesantía?", ["ley 19728"], []),
    ("Tuve un accidente en el trabajo, ¿quién paga los gastos médicos?", ["ley 16744"], []),
]


def _norma(texto: str) -> str:
    """'Código del Trabajo (idNorma 207436)' -> 'codigo del trabajo'; 'Ley 14.908' -> 'ley 14908'."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\s*\(idnorma \d+\)", "", t).replace(".", "")
    return re.sub(r"\s+", " ", t).strip()


def _articulo(texto: str) -> str:
    """'art. 211 B bis' -> '211bbis' (sin espacios ni guiones, para comparar)."""
    t = re.sub(r"^art(iculo|\.)?\s*", "", _norma(texto))
    return re.sub(r"[\s\-]", "", t)


def _acierta_articulo(citas: list[dict], normas: list[str], esperados: list[str]) -> bool:
    for c in citas:
        if not any(_norma(c["fuente"]).startswith(n) for n in normas):
            continue
        a = _articulo(c["articulo"])
        for e in esperados:
            e2 = _articulo(e.rstrip("*"))
            if (e.endswith("*") and a.startswith(e2)) or a == e2:
                return True
    return False


class _SinCache:
    """El repositorio real, sin caché y sin dejar respuestas reutilizables."""
    def __getattr__(self, nombre):
        if nombre == "buscar_reciente":
            raise AttributeError(nombre)
        return getattr(consultas_repository, nombre)

    def crear(self, *a, **kw):
        kw["reutilizable"] = False
        return consultas_repository.crear(*a, **kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=len(BATERIA))
    args = ap.parse_args()
    bateria = BATERIA[: args.max]
    vect, llm, repo = Vectorizador(), ClienteGemini(), _SinCache()
    if not llm.disponible():
        print("Aviso: no hay GEMINI_API_KEY; se evaluará solo el modo extractivo.")

    filas = []
    with psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row) as conn:
        for i, (pregunta, normas, esperados) in enumerate(bateria, 1):
            t0 = time.monotonic()
            c = service.crear(conn, pregunta, repo=repo, vectorizador=vect, llm=llm, sesion=SESION)
            seg = time.monotonic() - t0
            citas = c.get("citas", [])
            ok_norma = any(_norma(x["fuente"]).startswith(n) for x in citas for n in normas)
            ok_art = _acierta_articulo(citas, normas, esperados) if esperados else None
            fila = {"n": i, "pregunta": pregunta, "modo": c.get("modo"), "segundos": round(seg, 1),
                    "norma": ok_norma, "articulo": ok_art,
                    "citas": [f"{x['fuente']} {x['articulo']}" for x in citas]}
            filas.append(fila)
            marca = lambda v: "-" if v is None else ("sí" if v else "NO")
            print(f"{i:2}. norma {marca(ok_norma):2} | artículo {marca(ok_art):2} | {fila['modo']:10} | "
                  f"{seg:5.1f} s | {pregunta}")
            if i < len(bateria):
                time.sleep(PAUSA_S)

    n = len(filas)
    con_art = [f for f in filas if f["articulo"] is not None]
    ia = [f for f in filas if f["modo"] == "ia"]
    tiempos = sorted(f["segundos"] for f in ia) or [0]
    resumen = {
        "fecha": date.today().isoformat(), "pensamiento": llm.nivel, "preguntas": n,
        "norma_correcta": sum(f["norma"] for f in filas),
        "articulo_correcto": sum(f["articulo"] for f in con_art), "con_articulo_esperado": len(con_art),
        "redactadas_con_ia": len(ia),
        "tiempo_promedio_ia_s": round(sum(tiempos) / len(tiempos), 1),
        "tiempo_mediana_ia_s": tiempos[len(tiempos) // 2],
    }
    pct = lambda a, b: f"{(100 * a / b):.0f} %" if b else "-"
    print(f"\nResumen (pensamiento de Gemini: {llm.nivel})")
    print(f"  Norma correcta:     {resumen['norma_correcta']}/{n} ({pct(resumen['norma_correcta'], n)})")
    print(f"  Artículo correcto:  {resumen['articulo_correcto']}/{len(con_art)} "
          f"({pct(resumen['articulo_correcto'], len(con_art))})")
    print(f"  Redactadas con IA:  {len(ia)}/{n}")
    print(f"  Tiempo con IA:      promedio {resumen['tiempo_promedio_ia_s']} s, mediana {resumen['tiempo_mediana_ia_s']} s")

    # data/ está montada como volumen: el resultado aparece también en la carpeta del proyecto
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    sufijo = f"_{llm.nivel}"
    with open(os.path.join(base, f"evaluacion{sufijo}.json"), "w", encoding="utf-8") as f:
        json.dump({"resumen": resumen, "filas": filas}, f, ensure_ascii=False, indent=1)
    si = lambda v: "—" if v is None else ("Sí" if v else "No")
    lineas = [f"# Evaluación de Articla ({resumen['fecha']}, pensamiento: {llm.nivel})", "",
              f"- Norma correcta: **{resumen['norma_correcta']}/{n}** ({pct(resumen['norma_correcta'], n)})",
              f"- Artículo exacto: **{resumen['articulo_correcto']}/{len(con_art)}** "
              f"({pct(resumen['articulo_correcto'], len(con_art))})",
              f"- Redactadas con IA: {len(ia)}/{n}",
              f"- Tiempo con IA: promedio {resumen['tiempo_promedio_ia_s']} s, mediana {resumen['tiempo_mediana_ia_s']} s",
              "", "| # | Pregunta | Norma | Artículo | Modo | Tiempo | Citas |", "|---|---|---|---|---|---|---|"]
    for f_ in filas:
        lineas.append(f"| {f_['n']} | {f_['pregunta']} | {si(f_['norma'])} | {si(f_['articulo'])} | "
                      f"{f_['modo']} | {f_['segundos']} s | {'; '.join(f_['citas'])} |")
    with open(os.path.join(base, f"evaluacion{sufijo}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print(f"\nGuardado en data/evaluacion{sufijo}.md y data/evaluacion{sufijo}.json")


if __name__ == "__main__":
    main()
