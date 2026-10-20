"""Tests de las reglas de negocio de las citas."""

from datetime import date, datetime, time

import pytest

from webhook.citas import ZONA, Cita, ajustar_am_pm, dni_valido, error_horario, normalizar_dni

AHORA = datetime(2026, 10, 20, 12, 0, tzinfo=ZONA)  # martes


@pytest.mark.parametrize("dictado", ["12.345.678 z", "1234 5678 z", "12345678-Z"])
def test_normaliza_dni_dictado_por_voz(dictado):
    assert normalizar_dni(dictado) == "12345678Z"


def test_dni_con_letra_correcta_es_valido():
    assert dni_valido("12345678Z")


def test_dni_con_letra_incorrecta_no_es_valido():
    assert not dni_valido("12345678A")


def test_dni_con_formato_incorrecto_no_es_valido():
    assert not dni_valido("1234Z")


def test_horario_valido():
    assert error_horario(datetime(2026, 10, 21, 10, 30, tzinfo=ZONA), AHORA) is None


def test_fecha_pasada():
    assert "ya ha pasado" in error_horario(datetime(2026, 10, 19, 10, 0, tzinfo=ZONA), AHORA)


def test_domingo_cerrado():
    assert "domingos" in error_horario(datetime(2026, 10, 25, 10, 0, tzinfo=ZONA), AHORA)


def test_sabado_por_la_tarde_fuera_de_horario():
    assert "sábado" in error_horario(datetime(2026, 10, 24, 17, 0, tzinfo=ZONA), AHORA)


@pytest.mark.parametrize(
    "dicha, esperada",
    [
        (time(22, 30), time(10, 30)),
        (time(5, 0), time(17, 0)),
        (time(12, 0), time(12, 0)),
    ],
)
def test_ajusta_horas_ambiguas_al_horario(dicha, esperada):
    assert ajustar_am_pm(dicha) == esperada


def test_crear_cita_normaliza_dni_y_hora():
    cita = Cita.crear("12345678 z", "perro", "vacunación", date(2026, 10, 21), time(22, 30))
    assert cita.dni == "12345678Z"
    assert cita.fecha_hora == datetime(2026, 10, 21, 10, 30, tzinfo=ZONA)
    assert cita.precio == 45
    assert cita.error(AHORA) is None


def test_servicio_sin_tarifa_no_es_valido():
    cita = Cita.crear("12345678Z", "perro", "castración", date(2026, 10, 21), time(10, 30))
    assert "no lo ofrecemos" in cita.error(AHORA)
