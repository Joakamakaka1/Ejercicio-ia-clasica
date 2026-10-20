"""Tests de las funciones puras del OCR (limpieza y extracción con regex)."""

from pathlib import Path

import ocr


def test_limpiar_une_palabras_partidas_y_quita_lineas_vacias():
    assert ocr.limpiar("despara-\nsitación\n\n  dosis  \n") == "desparasitación\ndosis"


def test_extrae_y_valida_campos():
    texto = (
        "Vigentes desde el 01/09/2026. Revisión 03/2024. Fecha imposible 31/02/2026.\n"
        "Consulta 35,00 € y vacunación 1.045,00 €. Nº de registro: 2113 ESP"
    )
    campos = ocr.extraer_campos(texto)
    assert campos["fechas"] == ["01/09/2026", "03/2024"]
    assert campos["importes"] == ["1.045,00 €", "35,00 €"]
    assert campos["registros_aemps"] == ["2113 ESP"]


def test_agrupa_paginas_por_documento(tmp_path: Path):
    for nombre in ["seresto_p2.png", "seresto_p1.png", "tarifas.png", "notas.txt"]:
        (tmp_path / nombre).touch()
    grupos = ocr.agrupar_paginas(tmp_path)
    assert list(grupos) == ["seresto", "tarifas"]
    assert [p.name for p in grupos["seresto"]] == ["seresto_p1.png", "seresto_p2.png"]
