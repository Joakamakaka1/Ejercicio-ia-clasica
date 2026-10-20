"""Tests del webhook simulando peticiones de Dialogflow (sin llamar al LLM)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ANTHROPIC_API_KEY", "clave-de-prueba")  # el cliente de Anthropic la exige

from webhook import documentos, main  # noqa: E402

PARAMETROS = {
    "dni": "12345678Z",
    "especie": "gato",
    "servicio": "peluquería",
    "fecha": "2099-06-03T12:00:00+02:00",  # miércoles
    "hora": "2099-06-03T11:00:00+02:00",
}
cliente = TestClient(main.app)


def peticion(intencion: str, texto: str = "", parametros=None, contextos=None) -> dict:
    """Cuerpo mínimo de una petición de Dialogflow ES."""
    return {
        "queryResult": {
            "queryText": texto,
            "intent": {"displayName": intencion},
            "parameters": parametros or {},
            "outputContexts": contextos or [],
        }
    }


def respuesta(cuerpo: dict) -> str:
    return cliente.post("/webhook", json=cuerpo).json()["fulfillmentText"]


def test_pedir_cita_resume_y_da_precio():
    texto = respuesta(peticion("pedir_cita", parametros=PARAMETROS))
    assert texto.startswith("<speak>")
    assert "peluquería" in texto and "30" in texto and "¿Confirmo la cita?" in texto


def test_pedir_cita_con_dni_invalido_lo_vuelve_a_pedir():
    texto = respuesta(peticion("pedir_cita", parametros=PARAMETROS | {"dni": "12345678A"}))
    assert "no es válido" in texto


def test_confirmar_cita_lee_el_contexto_y_da_referencia():
    # Contexto tal y como llega de Dialogflow: con campos *.original y el DNI dictado por voz
    contexto = {
        "name": "projects/p/agent/sessions/s/contexts/ctx_solicitud_en_curso",
        "parameters": PARAMETROS | {"dni": "12 345 678 Z", "dni.original": "12 345 678 Z"},
    }
    texto = respuesta(peticion("pedir_cita - si", contextos=[contexto]))
    assert "confirmada" in texto and 'interpret-as="characters"' in texto


def test_parametros_incompletos_no_dejan_al_usuario_en_silencio():
    texto = respuesta(peticion("pedir_cita", parametros=PARAMETROS | {"fecha": ""}))
    assert texto == f"<speak>{main.ERROR_INESPERADO}</speak>"


def test_intencion_sin_manejador():
    assert "Todavía no sé" in respuesta(peticion("intencion_nueva"))


@pytest.mark.parametrize("intencion", ["consulta_documental", "Default Fallback Intent"])
def test_consulta_documental_usa_el_llm(monkeypatch, intencion):
    monkeypatch.setattr(documentos, "responder_pregunta", lambda p: f"Respuesta a {p} & más")
    texto = respuesta(peticion(intencion, texto="¿cada cuánto pongo la pipeta?"))
    assert "Respuesta a ¿cada cuánto pongo la pipeta? &amp; más" in texto
