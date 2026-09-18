"""
Servicio Anthropic para generar resúmenes de llamadas
"""

import os
from anthropic import Anthropic

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
            model="claude-3-sonnet-20240229",
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
        return f"Error generando resumen: {str(e)}"

def extract_call_metadata(transcript: str) -> dict:
    """
    Extrae metadata de la llamada (nombre, interés, etc.)
    """
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        
        client = Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
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
        
        import json
        try:
            return json.loads(message.content[0].text)
        except:
            return {
                "nombre": "Desconocido",
                "interes": "cold",
                "propiedades": [],
                "proximo_paso": "Seguimiento"
            }
    except Exception as e:
        return {
            "nombre": "Error",
            "interes": "cold",
            "propiedades": [],
            "proximo_paso": f"Error: {str(e)}"
        }

