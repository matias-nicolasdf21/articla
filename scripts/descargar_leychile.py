"""Descarga el XML oficial de cada norma de data/normas.json que todavía no esté en data/leychile/.

Uso:   python -m scripts.descargar_leychile
Muestra el título que devuelve LeyChile para cada idNorma: REVÍSALO. Si no corresponde a la ley
esperada, corrige el `id` en data/normas.json (el número aparece en la dirección de LeyChile
después de `idNorma=`).
"""
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma={id}"
NS = "{http://www.leychile.cl/esquemas}"


def main() -> None:
    normas = json.loads((RAIZ / "data" / "normas.json").read_text(encoding="utf-8"))
    destino = RAIZ / "data" / "leychile"
    destino.mkdir(parents=True, exist_ok=True)
    for n in normas:
        archivo = destino / n["archivo"]
        if archivo.exists():
            print(f"= {n['identificador']}: ya descargada")
            continue
        req = urllib.request.Request(URL.format(id=n["id"]), headers={"User-Agent": "Articla-proyecto-universitario"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            titulo = ET.fromstring(datos).findtext(f"{NS}Metadatos/{NS}TituloNorma") or "(sin título)"
        except Exception as e:                      # red caída, id inexistente, XML inválido…
            print(f"! {n['identificador']} (idNorma {n['id']}): no se pudo descargar ({e})")
            continue
        archivo.write_bytes(datos)
        print(f"+ {n['identificador']} (idNorma {n['id']}): {titulo[:100]}")
        time.sleep(1)                               # una petición por segundo, por cortesía con el servidor


if __name__ == "__main__":
    main()
