"""Modelos del contrato de webhook de Dialogflow ES (solo los campos que usamos).

Dialogflow envía y espera los campos en camelCase; en Python se usan en
snake_case gracias al alias automático.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ModeloDialogflow(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Intencion(ModeloDialogflow):
    display_name: str


class Contexto(ModeloDialogflow):
    name: str
    parameters: dict = {}


class QueryResult(ModeloDialogflow):
    query_text: str = ""
    parameters: dict = {}
    intent: Intencion
    output_contexts: list[Contexto] = []

    def parametros_de_contexto(self, nombre: str) -> dict:
        """Parámetros guardados en un contexto activo, o {} si no está activo."""
        for contexto in self.output_contexts:
            if contexto.name.endswith(f"/contexts/{nombre}"):
                return contexto.parameters
        return {}


class PeticionDialogflow(ModeloDialogflow):
    query_result: QueryResult


class RespuestaDialogflow(ModeloDialogflow):
    fulfillment_text: str


class ParametrosCita(BaseModel):
    """Parámetros de `pedir_cita`. Pydantic convierte las fechas ISO y, si falta
    alguno o llega mal formado, falla aquí en vez de propagar un dato inválido.
    Los campos `*.original` que añade Dialogflow se ignoran."""

    dni: str
    especie: str
    servicio: str
    fecha: datetime
    hora: datetime
