"""
Servicio Retell AI para crear el agente outbound y disparar llamadas salientes
"""

import os
import logging
import json
import requests

logger = logging.getLogger(__name__)

RETELL_API_URL = "https://api.retellai.com"

def get_retell_headers():
    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise ValueError("RETELL_API_KEY no configurada")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

OUTBOUND_PROMPT = """Eres Sofía, agente de voz de Sofia Inmobiliaria. Estás haciendo una llamada SALIENTE a un lead que mostró interés previamente en propiedades.

TONO: Respetuosa, cálida, breve. NUNCA insistente. El tiempo del lead vale más que la venta.

Datos de este lead (usa estas variables para personalizar):
- Nombre: {{lead_name}}
- Zona de interés previa: {{zona_interes}}
- Resumen de contacto anterior: {{resumen_anterior}}

FLUJO DE LA LLAMADA:

1. Apertura (siempre igual, personalizada):
"Hola{{#lead_name}} {{lead_name}}{{/lead_name}}, le habla Sofía de Sofia Inmobiliaria. Le llamo porque vi que mostró interés en propiedades por la zona de {{zona_interes}}. ¿Tiene un minuto?"

2. Si dice que NO tiene tiempo / está ocupado:
- Despídete amablemente, sin insistir: "Entiendo perfectamente, no le quito más tiempo. ¿Le parece si lo intento en otro momento?" Si dice que sí, agradece y termina. Si dice que no o es evasivo, agradece y termina la llamada sin agendar nada.
- Llama a la función `mark_lead_status` con status="Pendiente de llamar" (para reintentar después) o "No contestado" según corresponda.

3. Si dice que NO le interesa / ya no busca propiedad:
- Agradece con respeto: "Entiendo, muchas gracias por su tiempo. Que tenga excelente día."
- Llama a la función `mark_lead_status` con status="Sin interés".
- Termina la llamada.

4. Si dice que SÍ tiene interés / quiere seguir platicando:
- Recalifica brevemente: pregunta si sigue buscando en la misma zona, presupuesto aproximado, y número de recámaras.
- Usa la función `search_properties` con esos criterios para encontrar opciones reales.
- Menciona 1-2 propiedades encontradas (nombre, precio, zona) de forma natural, sin sonar a script leído.
- Si muestra interés en alguna, ofrece agendar una visita.
- Llama a la función `mark_lead_status` con status="En proceso" o "Cita agendada" según el resultado.

REGLAS IMPORTANTES:
- Nunca insistas más de una vez si el lead da señales de no querer hablar.
- Sé breve, no repitas información innecesariamente.
- Habla de forma natural, no como un robot leyendo un guion.
- Siempre usa las funciones disponibles para actualizar el estatus del lead antes de colgar.
"""

def get_or_create_outbound_llm() -> dict:
    """
    Crea (o reutiliza) el Retell LLM para el agente outbound con function calling
    hacia los endpoints de Railway.
    """
    try:
        backend_url = os.getenv("RAILWAY_URL", "").rstrip("/")
        if not backend_url:
            raise ValueError("RAILWAY_URL no configurada")

        payload = {
            "general_prompt": OUTBOUND_PROMPT,
            "begin_message": "",  # se genera dinámicamente por el prompt
            "general_tools": [
                {
                    "type": "custom",
                    "name": "search_properties",
                    "description": "Busca propiedades disponibles en la inmobiliaria según zona, precio y recámaras.",
                    "url": f"{backend_url}/api/functions/search_properties",
                    "speak_during_execution": True,
                    "speak_after_execution": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ubicacion_filter": {"type": "string", "description": "Zona o colonia de interés"},
                            "precio_max": {"type": "number", "description": "Precio máximo mensual en pesos"},
                            "recamaras_min": {"type": "number", "description": "Número mínimo de recámaras"}
                        },
                        "required": []
                    }
                },
                {
                    "type": "custom",
                    "name": "mark_lead_status",
                    "description": "Actualiza el estatus del lead en el CRM al finalizar o durante la llamada.",
                    "url": f"{backend_url}/api/functions/mark_lead_status",
                    "speak_during_execution": False,
                    "speak_after_execution": False,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {"type": "string", "description": "Teléfono del lead en formato E.164"},
                            "status": {
                                "type": "string",
                                "description": "Nuevo estatus del lead",
                                "enum": ["Pendiente de llamar", "En proceso", "Cita agendada", "No contestado", "Sin interés", "Cerrado"]
                            }
                        },
                        "required": ["phone_number", "status"]
                    }
                },
                {"type": "end_call", "name": "end_call", "description": "Termina la llamada cuando la conversación concluyó."}
            ]
        }

        logger.info("🤖 Creando/actualizando Retell LLM outbound...")
        resp = requests.post(f"{RETELL_API_URL}/create-retell-llm", headers=get_retell_headers(), json=payload)

        if resp.status_code not in (200, 201):
            logger.error(f"❌ Error creando LLM: {resp.status_code} - {resp.text}")
            return {"success": False, "error": resp.text}

        result = resp.json()
        logger.info(f"✅ Retell LLM creado: {result.get('llm_id')}")
        return {"success": True, "llm_id": result.get("llm_id")}
    except Exception as e:
        logger.error(f"❌ Error en get_or_create_outbound_llm: {str(e)}")
        return {"success": False, "error": str(e)}

def create_outbound_agent(llm_id: str, voice_id: str = "retell-Cimo") -> dict:
    """
    Crea el agente outbound en Retell asociado al LLM.
    """
    try:
        payload = {
            "response_engine": {"type": "retell-llm", "llm_id": llm_id},
            "voice_id": voice_id,
            "agent_name": "Sofia - Outbound",
            "language": "es-419",
        }

        logger.info("🤖 Creando agente outbound en Retell...")
        resp = requests.post(f"{RETELL_API_URL}/create-agent", headers=get_retell_headers(), json=payload)

        if resp.status_code not in (200, 201):
            logger.error(f"❌ Error creando agente: {resp.status_code} - {resp.text}")
            return {"success": False, "error": resp.text}

        result = resp.json()
        logger.info(f"✅ Agente outbound creado: {result.get('agent_id')}")
        return {"success": True, "agent_id": result.get("agent_id")}
    except Exception as e:
        logger.error(f"❌ Error en create_outbound_agent: {str(e)}")
        return {"success": False, "error": str(e)}

def trigger_outbound_call(
    to_number: str,
    lead_name: str = "",
    zona_interes: str = "la zona que consultó",
    resumen_anterior: str = "",
    lead_page_id: str = ""
) -> dict:
    """
    Dispara una llamada saliente usando el agente outbound de Retell.
    """
    try:
        agent_id = os.getenv("RETELL_OUTBOUND_AGENT_ID")
        from_number = os.getenv("TWILIO_PHONE_NUMBER")

        if not agent_id:
            raise ValueError("RETELL_OUTBOUND_AGENT_ID no configurada")
        if not from_number:
            raise ValueError("TWILIO_PHONE_NUMBER no configurada")

        payload = {
            "from_number": from_number,
            "to_number": to_number,
            "override_agent_id": agent_id,
            "retell_llm_dynamic_variables": {
                "lead_name": lead_name or "",
                "zona_interes": zona_interes or "la zona que consultó",
                "resumen_anterior": resumen_anterior or "Sin información previa"
            },
            "metadata": {
                "call_type": "outbound",
                "lead_page_id": lead_page_id,
                "phone_number": to_number
            }
        }

        logger.info("=" * 80)
        logger.info(f"📞 DISPARANDO LLAMADA OUTBOUND A {to_number}")
        logger.info("=" * 80)
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))

        resp = requests.post(f"{RETELL_API_URL}/v2/create-phone-call", headers=get_retell_headers(), json=payload)

        logger.info(f"Status Code: {resp.status_code}")
        logger.info(f"Response: {resp.text}")

        if resp.status_code not in (200, 201):
            logger.error(f"❌ Error disparando llamada: {resp.status_code}")
            return {"success": False, "error": resp.text}

        result = resp.json()
        logger.info(f"✅ Llamada iniciada: {result.get('call_id')}")
        return {"success": True, "call_id": result.get("call_id")}
    except Exception as e:
        logger.error(f"❌ Error en trigger_outbound_call: {str(e)}")
        return {"success": False, "error": str(e)}
