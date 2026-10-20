"""Webhook de Dialogflow ES para la Clínica Veterinaria Patitas (capa HTTP).

Arrancar desde la raíz del proyecto:
    uv run uvicorn webhook.main:app --port 8000
"""

import logging
import time

from dotenv import load_dotenv

load_dotenv()  # antes de importar el resto: el cliente de Anthropic necesita la API key

from fastapi import FastAPI  # noqa: E402

from webhook.intenciones import gestionar  # noqa: E402
from webhook.modelos import PeticionDialogflow, RespuestaDialogflow  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ERROR_INESPERADO = "Perdona, ha habido un problema. ¿Me lo repites?"

app = FastAPI(title="Webhook Clínica Veterinaria Patitas")


@app.post("/webhook", response_model=RespuestaDialogflow)
def webhook(peticion: PeticionDialogflow) -> RespuestaDialogflow:
    """Punto de entrada de Dialogflow: delega en la intención y responde en SSML."""
    resultado = peticion.query_result
    intencion = resultado.intent.display_name
    inicio = time.perf_counter()
    try:
        texto = gestionar(resultado)
    except Exception:
        # Última barrera: un error nunca debe dejar al usuario en silencio.
        logger.exception("Error gestionando la intención %s", intencion)
        texto = ERROR_INESPERADO
    # Los parámetros no se registran: contienen el DNI del cliente.
    logger.info("%s respondida en %.0f ms", intencion, (time.perf_counter() - inicio) * 1000)
    return RespuestaDialogflow(fulfillment_text=f"<speak>{texto}</speak>")


@app.get("/")
def estado() -> dict[str, str]:
    """Comprobación rápida de que el túnel llega hasta el webhook."""
    return {"estado": "ok"}
