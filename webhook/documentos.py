"""Consulta documental: responde preguntas usando solo el texto OCR de los documentos.

El texto se genera una única vez con `ocr.py` y aquí solo se lee del JSON.
Al ser pocos documentos se mandan todos en el prompt (context stuffing),
sin embeddings ni base vectorial.
"""

import json
import logging
import os
from pathlib import Path

import anthropic
from anthropic.types import TextBlockParam

logger = logging.getLogger(__name__)

CARPETA = Path(__file__).resolve().parent
RUTA_DOCUMENTOS = CARPETA.parent / "data" / "documentos.json"
RUTA_PROMPT = CARPETA / "prompts" / "consulta_documental.txt"
MODELO = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")  # rápido: el webhook tiene 5 s

# Marca que devuelve el modelo cuando la respuesta no está en los documentos.
# Así el control de alucinaciones lo decide nuestro código, no el modelo.
NO_ENCONTRADO = "NO_ENCONTRADO"

SIN_INFORMACION = (
    "Lo siento, esa información no aparece en los documentos de la clínica. "
    "Si quieres, te paso con una persona del equipo."
)
ERROR_MODELO = (
    "Ahora mismo no puedo consultar los documentos. Si quieres, te paso con una persona del equipo."
)


def cargar_contexto(ruta: Path = RUTA_DOCUMENTOS) -> str:
    """Une el texto de todos los documentos en un único bloque para el prompt."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Genéralo antes con: uv run ocr.py")
    documentos = json.loads(ruta.read_text(encoding="utf-8"))
    return "\n\n".join(f"### {doc['titulo']}\n{doc['texto']}" for doc in documentos)


def construir_sistema() -> list[TextBlockParam]:
    """Instrucciones + documentos: un prompt de sistema fijo que se cachea.

    A partir de la segunda pregunta se lee de caché (más rápido y barato).
    """
    instrucciones = RUTA_PROMPT.read_text(encoding="utf-8").format(no_encontrado=NO_ENCONTRADO)
    return [
        TextBlockParam(
            type="text",
            text=f"{instrucciones}\nDOCUMENTOS:\n{cargar_contexto()}",
            cache_control={"type": "ephemeral"},
        )
    ]


SISTEMA = construir_sistema()

# Dialogflow corta el webhook a los 5 s: 4 s de margen y sin reintentos
cliente = anthropic.Anthropic(timeout=4.0, max_retries=0)  # lee ANTHROPIC_API_KEY


def responder_pregunta(pregunta: str) -> str:
    """Pregunta al LLM y traduce la marca NO_ENCONTRADO a un mensaje honesto.

    Si el modelo falla, tarda o rechaza la petición, se devuelve un mensaje de
    disculpa en vez de dejar al usuario en silencio.
    """
    try:
        respuesta = cliente.messages.create(
            model=MODELO,
            max_tokens=1024,  # margen para el razonamiento; la respuesta es corta
            system=SISTEMA,
            messages=[{"role": "user", "content": f"<pregunta>{pregunta}</pregunta>"}],
            output_config={"effort": "low"},  # poco razonamiento: menos latencia
        )
    except anthropic.APIError as error:
        logger.error("Fallo del LLM: %s", error)
        return ERROR_MODELO

    if respuesta.stop_reason == "refusal":
        logger.warning("El LLM rechazó la pregunta")
        return SIN_INFORMACION
    texto = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    if not texto or NO_ENCONTRADO in texto:
        return SIN_INFORMACION
    return texto
