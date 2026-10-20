"""OCR offline de los documentos de la clínica (se ejecuta una sola vez).

Lee las imágenes de `documentos/`, las pasa por Tesseract, extrae y valida
campos con expresiones regulares y guarda el resultado en
`data/documentos.json`, que es lo que usa el webhook.

Las páginas de un mismo documento se agrupan por nombre: `milbemax_perros_p1.png`,
`milbemax_perros_p2.png`... forman el documento «milbemax_perros».

Uso:
    python ocr.py
"""

import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps

RAIZ = Path(__file__).parent
CARPETA = RAIZ / "documentos"
SALIDA = RAIZ / "data" / "documentos.json"

# Si Tesseract no está en el PATH, se usa la ruta por defecto del instalador de Windows
if shutil.which("tesseract") is None:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PATRONES = {
    # dd/mm/aaaa (tarifas) o mm/aaaa (revisión de los prospectos)
    "fechas": re.compile(r"\b(?:\d{1,2}/)?\d{1,2}/\d{4}\b"),
    "importes": re.compile(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\s?€"),
    # Número de registro de la AEMPS, p. ej. «2113 ESP»
    "registros_aemps": re.compile(r"\b\d{3,4}\s?ESP\b"),
}


def leer_imagen(ruta: Path) -> str:
    """Pasa una imagen por Tesseract en español.

    Preprocesado: escala de grises y autocontraste, que limpia el fondo
    grisáceo de los escaneos sin coste.

    --psm 6 (un bloque de texto) mantiene cada fila junta: con el modo por
    defecto la columna de precios de las tarifas salía separada de su servicio.
    """
    imagen = ImageOps.autocontrast(Image.open(ruta).convert("L"))
    return pytesseract.image_to_string(imagen, lang="spa", config="--psm 6")


def limpiar(texto: str) -> str:
    """Une palabras partidas con guion al final de línea y quita líneas vacías."""
    texto = re.sub(r"-\n(\w)", r"\1", texto)
    return "\n".join(linea.strip() for linea in texto.splitlines() if linea.strip())


def fecha_valida(fecha: str) -> bool:
    """La regex solo garantiza el formato; aquí se comprueba que la fecha exista."""
    formato = "%d/%m/%Y" if fecha.count("/") == 2 else "%m/%Y"
    try:
        datetime.strptime(fecha, formato)
        return True
    except ValueError:
        return False


def extraer_campos(texto: str) -> dict[str, list[str]]:
    """Aplica las regex sobre el texto reconocido y descarta fechas imposibles."""
    campos = {nombre: sorted(set(patron.findall(texto))) for nombre, patron in PATRONES.items()}
    campos["fechas"] = [f for f in campos["fechas"] if fecha_valida(f)]
    return campos


def agrupar_paginas(carpeta: Path) -> dict[str, list[Path]]:
    """{nombre_documento: [páginas ordenadas]} a partir de los nombres de fichero."""
    documentos = defaultdict(list)
    for ruta in sorted(carpeta.glob("*.png")):
        documentos[re.sub(r"_p\d+$", "", ruta.stem)].append(ruta)
    return documentos


def main() -> None:
    resultado = []
    for nombre, paginas in agrupar_paginas(CARPETA).items():
        texto = limpiar("\n".join(leer_imagen(p) for p in paginas))
        campos = extraer_campos(texto)
        resultado.append(
            {
                "titulo": nombre.replace("_", " ").capitalize(),
                "paginas": [p.name for p in paginas],
                "campos": campos,
                "texto": texto,
            }
        )
        print(f"OCR {nombre}: {len(paginas)} páginas, {len(texto)} caracteres, campos {campos}")

    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
