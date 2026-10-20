"""Dominio de citas de la Clínica Veterinaria Patitas.

Reglas de negocio puras (sin FastAPI ni Dialogflow): validación del DNI,
horario de la clínica y tarifas.
"""

import re
import secrets
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("Europe/Madrid")

# DNI: 8 dígitos + letra de control. Se aplica sobre el texto ya normalizado.
DNI_REGEX = re.compile(r"^\d{8}[A-Z]$")
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"

# Euros por servicio. Son los mismos que figuran en el documento de tarifas.
TARIFAS = {
    "consulta general": 35,
    "vacunación": 45,
    "desparasitación": 20,
    "peluquería": 30,
}

# Horario por día de la semana (0 = lunes). El domingo no aparece: cerrado.
HORARIO = {dia: (time(9), time(20)) for dia in range(5)} | {5: (time(10), time(14))}

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


@dataclass(frozen=True)
class Cita:
    """Cita solicitada por un cliente, tal y como la recoge el agente."""

    dni: str
    especie: str
    servicio: str
    fecha_hora: datetime

    @classmethod
    def crear(cls, dni: str, especie: str, servicio: str, dia: date, hora: time) -> "Cita":
        """Construye la cita normalizando el DNI dictado y las horas ambiguas."""
        return cls(
            dni=normalizar_dni(dni),
            especie=especie,
            servicio=servicio,
            fecha_hora=datetime.combine(dia, ajustar_am_pm(hora), ZONA),
        )

    @property
    def precio(self) -> int:
        return TARIFAS[self.servicio]

    def error(self, ahora: datetime | None = None) -> str | None:
        """Devuelve el motivo por el que la cita no es válida, o None si lo es."""
        if self.servicio not in TARIFAS:
            return "Ese servicio no lo ofrecemos. ¿Qué servicio necesitas?"
        if not dni_valido(self.dni):
            return f"El DNI {self.dni} no es válido. ¿Me lo puedes repetir?"
        return error_horario(self.fecha_hora, ahora)


def normalizar_dni(texto: str) -> str:
    """Quita espacios, puntos y guiones que mete el reconocimiento de voz.

    '12.345.678 z' -> '12345678Z'
    """
    return re.sub(r"[\s.\-]", "", texto).upper()


def dni_valido(dni: str) -> bool:
    """Comprueba el formato con regex y la letra de control (número módulo 23)."""
    if not DNI_REGEX.match(dni):
        return False
    return LETRAS_DNI[int(dni[:8]) % 23] == dni[8]


def ajustar_am_pm(hora: time) -> time:
    """Corrige horas ambiguas dichas sin «mañana» o «tarde».

    Dialogflow resuelve «a las 10:30» como la próxima 10:30, que por la noche
    es 22:30. Si la hora cae fuera del horario de la clínica se toma la del
    otro tramo de 12 h: 22:30 -> 10:30 y 5:00 -> 17:00.
    """
    if hora.hour < 9:
        return hora.replace(hour=hora.hour + 12)
    if hora.hour > 20:
        return hora.replace(hour=hora.hour - 12)
    return hora


def error_horario(fecha_hora: datetime, ahora: datetime | None = None) -> str | None:
    """Comprueba que la cita sea futura y caiga dentro del horario de la clínica."""
    ahora = ahora or datetime.now(ZONA)
    if fecha_hora <= ahora:
        return "Esa fecha ya ha pasado. ¿Qué otro día y hora te viene bien?"

    horario = HORARIO.get(fecha_hora.weekday())
    if horario is None:
        return "Los domingos la clínica está cerrada. ¿Qué otro día y hora te viene bien?"

    apertura, cierre = horario
    if not apertura <= fecha_hora.time() < cierre:
        return (
            f"Los {DIAS[fecha_hora.weekday()]} atendemos de {hora_en_palabras(apertura)} "
            f"a {hora_en_palabras(cierre)}. ¿Qué otro día y hora te viene bien?"
        )
    return None


def generar_referencia() -> str:
    """Código de cita fácil de deletrear por voz (sin O/0 ni I/1)."""
    return "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))


def fecha_en_palabras(fecha_hora: datetime) -> str:
    """'el lunes 26 de octubre a las 10:30'."""
    return (
        f"el {DIAS[fecha_hora.weekday()]} {fecha_hora.day} de "
        f"{MESES[fecha_hora.month - 1]} a las {hora_en_palabras(fecha_hora.time())}"
    )


def hora_en_palabras(hora: time) -> str:
    """'10:30'."""
    return f"{hora.hour}:{hora.minute:02d}"
