"""Manejadores de cada intención: traducen la petición en una respuesta SSML.

Todo texto variable se escapa antes de meterlo en el SSML: así un valor
inesperado no puede romper la respuesta ni inyectar etiquetas.
"""

import logging
from collections.abc import Callable
from html import escape

from webhook import documentos
from webhook.citas import Cita, fecha_en_palabras, generar_referencia
from webhook.modelos import ParametrosCita, QueryResult

logger = logging.getLogger(__name__)

CONTEXTO_CITA = "ctx_solicitud_en_curso"


def cita_desde(parametros: dict) -> Cita:
    """Valida los parámetros de Dialogflow y los convierte en una cita del dominio.

    @sys.date y @sys.time llegan como fechas completas: se toma el día de la
    primera y la hora de la segunda.
    """
    p = ParametrosCita.model_validate(parametros)
    return Cita.crear(p.dni, p.especie, p.servicio, p.fecha.date(), p.hora.time())


def pedir_cita(resultado: QueryResult) -> str:
    """Valida los datos recogidos y pide confirmación con el resumen y el precio."""
    cita = cita_desde(resultado.parameters)
    if error := cita.error():
        return escape(error)

    return (
        f"Te resumo: cita de {escape(cita.servicio)} para tu {escape(cita.especie)} "
        f"{fecha_en_palabras(cita.fecha_hora)}. "
        f'El precio es de <say-as interpret-as="cardinal">{cita.precio}</say-as> euros. '
        f'<break time="400ms"/>¿Confirmo la cita?'
    )


def confirmar_cita(resultado: QueryResult) -> str:
    """Confirma la cita (follow-up «sí») y devuelve un código de referencia."""
    cita = cita_desde(resultado.parametros_de_contexto(CONTEXTO_CITA))
    if error := cita.error():  # por si se confirma sin haber corregido el dato
        return escape(error)

    referencia = generar_referencia()
    logger.info("Cita confirmada %s: %s el %s", referencia, cita.servicio, cita.fecha_hora)
    return (
        f"¡Hecho! Tu cita queda confirmada {fecha_en_palabras(cita.fecha_hora)}. "
        f'Tu código de referencia es <say-as interpret-as="characters">{referencia}</say-as>. '
        f'<break time="300ms"/>¿Puedo ayudarte en algo más?'
    )


def consulta_documental(resultado: QueryResult) -> str:
    """Responde preguntas sobre los documentos de la clínica con el LLM."""
    return escape(documentos.responder_pregunta(resultado.query_text))


MANEJADORES: dict[str, Callable[[QueryResult], str]] = {
    "pedir_cita": pedir_cita,
    "pedir_cita - si": confirmar_cita,
    "consulta_documental": consulta_documental,
    # Lo que Dialogflow no entiende se intenta responder con los documentos;
    # si no está ahí, el LLM lo dice en vez de inventar.
    "Default Fallback Intent": consulta_documental,
}


def gestionar(resultado: QueryResult) -> str:
    """Ejecuta el manejador de la intención o una respuesta por defecto."""
    manejador = MANEJADORES.get(resultado.intent.display_name)
    if manejador is None:
        return "Todavía no sé gestionar esa petición."
    return manejador(resultado)
