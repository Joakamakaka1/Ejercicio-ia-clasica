"""Cliente de voz: micrófono -> Dialogflow ES (STT + intención + TTS) -> altavoz.

Usa el STT y el TTS nativos de Dialogflow: el audio va dentro del mismo
detect_intent, sin servicios externos de voz.

Necesita en el .env:
    DIALOGFLOW_PROJECT_ID=<id del proyecto>
    GOOGLE_APPLICATION_CREDENTIALS=<ruta a la clave JSON de la cuenta de servicio>

Uso:
    uv run cliente_voz.py
"""

import io
import os
import re
import sys
import time
import uuid
import wave

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google.cloud import dialogflow

load_dotenv()

PROJECT_ID = os.getenv("DIALOGFLOW_PROJECT_ID") or sys.exit("Falta DIALOGFLOW_PROJECT_ID (.env)")
IDIOMA = "es"
FS = 16000  # Dialogflow espera 16 kHz en LINEAR_16
SEGUNDOS = 7  # con 5 s no da tiempo a dictar un DNI completo

# Una sesión por conversación: los contextos y el slot filling viven en ella
clientes = dialogflow.SessionsClient()
sesion = clientes.session_path(PROJECT_ID, str(uuid.uuid4()))


def escuchar(segundos: int = SEGUNDOS) -> bytes:
    """Graba del micrófono durante unos segundos y devuelve el audio PCM."""
    print(f"\nHabla ({segundos}s)...")
    audio = sd.rec(int(segundos * FS), samplerate=FS, channels=1, dtype="int16")
    sd.wait()
    return audio.tobytes()


def reproducir(wav_bytes: bytes) -> None:
    """Reproduce el WAV que devuelve Dialogflow (LINEAR_16 ya trae cabecera RIFF)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        muestras = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        sd.play(muestras, wav.getframerate())
    sd.wait()


def hablar_con_el_agente(audio_bytes: bytes):
    """Envía el audio a Dialogflow y pide la respuesta también en audio."""
    entrada = dialogflow.QueryInput(
        audio_config=dialogflow.InputAudioConfig(
            audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
            language_code=IDIOMA,
            sample_rate_hertz=FS,
        )
    )
    salida = dialogflow.OutputAudioConfig(
        audio_encoding=dialogflow.OutputAudioEncoding.OUTPUT_AUDIO_ENCODING_LINEAR_16,
    )
    return clientes.detect_intent(
        request={
            "session": sesion,
            "query_input": entrada,
            "input_audio": audio_bytes,
            "output_audio_config": salida,
        }
    )


def sin_ssml(texto: str) -> str:
    """Quita las etiquetas SSML para mostrar la respuesta en la terminal."""
    return re.sub(r"<[^>]+>", "", texto).strip()


def main() -> None:
    print(f"Clínica Veterinaria Patitas · proyecto {PROJECT_ID}")
    print("Enter para hablar, 'q' + Enter para salir.")

    while input("\n> ").strip().lower() != "q":
        audio = escuchar()
        inicio = time.perf_counter()
        respuesta = hablar_con_el_agente(audio)
        latencia = time.perf_counter() - inicio

        r = respuesta.query_result
        if not r.query_text:
            print("  No te he oído, prueba otra vez.")
            continue
        print(f"  Has dicho  : {r.query_text}")
        print(f"  Intención  : {r.intent.display_name} ({r.intent_detection_confidence:.2f})")
        print(f"  Responde   : {sin_ssml(r.fulfillment_text)}")
        print(f"  Latencia   : {latencia:.1f} s")

        if respuesta.output_audio:
            reproducir(respuesta.output_audio)


if __name__ == "__main__":
    main()
