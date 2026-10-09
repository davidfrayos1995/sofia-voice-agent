"""
Servicio Anthropic para generar resúmenes de llamadas
"""

import os
import re
import json
from anthropic import Anthropic

RESUMEN_ERROR_PREFIX = "Error generando resumen"

def resumen_es_valido(resumen: str) -> bool:
    return bool(resumen) and not resumen.startswith(RESUMEN_ERROR_PREFIX)

def generate_call_summary(transcript: str) -> str:
    """
    Genera un resumen de la llamada usando Claude.
    """
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")

        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""Eres un asistente que analiza transcripciones de llamadas para una inmobiliaria.
Genera un resumen conciso y estructurado de la siguiente llamada.

Incluye:
1. Nombre y teléfono del cliente (si está disponible)
2. Propiedades mencionadas
3. Nivel de interés (Alto/Medio/Bajo)
4. Próximos pasos sugeridos
5. Notas importantes

Transcripción:
{transcript}

Resumen:"""
                }
            ]
        )

        return message.content[0].text
    except Exception as e:
        return f"{RESUMEN_ERROR_PREFIX}: {str(e)}"

def _parsear_metadata(texto: str) -> dict:
    bloque = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
    candidato = (bloque.group(1) if bloque else texto).strip()
    try:
        datos = json.loads(candidato)
    except ValueError:
        return {"ok": False, "error": "respuesta sin JSON legible"}
    if not isinstance(datos, dict):
        return {"ok": False, "error": "JSON no es un objeto"}
    datos["ok"] = True
    return datos

def extract_call_metadata(transcript: str) -> dict:
    """
    Extrae metadata de la llamada (nombre, interés, etc.).
    Devuelve {"ok": True, ...} si se pudo leer, o {"ok": False, "error": ...} si no.
    """
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")

        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": f"""Extrae los siguientes datos de esta transcripción de llamada (devuelve JSON):
- nombre: nombre del cliente
- interes: "hot", "warm" o "cold"
- propiedades: lista de propiedades mencionadas
- proximo_paso: próxima acción recomendada

Transcripción:
{transcript}

JSON:"""
                }
            ]
        )

        return _parsear_metadata(message.content[0].text)
    except Exception as e:
        return {"ok": False, "error": str(e)}
