"""Evaluación de la consulta documental con el LLM real.

Cada caso de `casos.json` indica qué debe contener la respuesta (cualquiera de
las palabras de `contiene`) o, si `contiene` es null, que el asistente diga que
la información no está en los documentos (control de alucinaciones).

Llama a la API de verdad (cuesta céntimos): ejecutar antes de cambiar el
prompt o el modelo, no en cada test.

Uso:
    uv run python -m evals.evaluar
"""

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from webhook.documentos import SIN_INFORMACION, responder_pregunta  # noqa: E402

CASOS = Path(__file__).parent / "casos.json"
LIMITE_SEGUNDOS = 4.0  # el webhook tiene 5 s; dejamos margen


def es_correcta(respuesta: str, contiene: list[str] | None) -> bool:
    """Comprueba la respuesta frente a lo esperado, sin distinguir mayúsculas."""
    if contiene is None:
        return respuesta == SIN_INFORMACION
    return any(palabra.lower() in respuesta.lower() for palabra in contiene)


def main() -> None:
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    aciertos, latencias = 0, []
    for caso in casos:
        inicio = time.perf_counter()
        respuesta = responder_pregunta(caso["pregunta"])
        latencias.append(time.perf_counter() - inicio)
        ok = es_correcta(respuesta, caso["contiene"])
        aciertos += ok
        estado = "OK " if ok else "MAL"
        print(f"{estado} {latencias[-1]:4.1f}s  {caso['pregunta']}\n       {respuesta}")

    lentas = sum(t > LIMITE_SEGUNDOS for t in latencias)
    print(
        f"\nAciertos: {aciertos}/{len(casos)} · latencia máx. {max(latencias):.1f}s · "
        f"por encima de {LIMITE_SEGUNDOS:.0f}s: {lentas}"
    )
    sys.exit(0 if aciertos == len(casos) and lentas == 0 else 1)


if __name__ == "__main__":
    main()
