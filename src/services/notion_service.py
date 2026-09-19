"""
Servicio Notion para guardar información de llamadas y leads
"""

import os
import logging
import json
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"

def get_notion_headers():
    """Obtiene headers para autenticación con Notion"""
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise ValueError("NOTION_API_KEY no configurada")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def create_call_record(
    phone_number: str,
    transcript: str,
    summary: str,
    call_id: str,
    duration_minutes: int = 0,
    call_type: str = "Entrante"
) -> dict:
    """
    Crea un registro de llamada en Notion
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LLAMADAS")

        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LLAMADAS no configurada")

        payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Fecha": {"date": {"start": datetime.now().isoformat()}},
                "Contacto": {"rich_text": [{"text": {"content": phone_number}}]},
                "Teléfono": {"phone_number": phone_number},
                "Duración (min)": {"number": duration_minutes},
                "Tipo": {"select": {"name": call_type}},
                "Transcript": {"rich_text": [{"text": {"content": transcript[:2000]}}]},
                "Resumen (Anthropic)": {"rich_text": [{"text": {"content": summary[:2000]}}]},
                "Estatus": {"select": {"name": "Completada"}},
                "Call ID": {"rich_text": [{"text": {"content": call_id}}]},
            }
        }

        logger.info("=" * 80)
        logger.info("📤 ENVIANDO A NOTION (CREAR LLAMADA)")
        logger.info("=" * 80)
        logger.info(f"URL: POST {NOTION_API_URL}/pages")
        logger.info(f"Database ID: {db_id}")
        logger.info(f"\nPAYLOAD COMPLETO:")
        logger.info(json.dumps(payload, indent=2, default=str))
        logger.info("=" * 80)

        response = requests.post(
            f"{NOTION_API_URL}/pages",
            headers=get_notion_headers(),
            json=payload
        )

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.text}")

        if response.status_code != 200:
            logger.error(f"❌ ERROR (status {response.status_code}):")
            logger.error(f"Response JSON: {response.json()}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        result = response.json()
        logger.info(f"✅ Llamada guardada: {result['id']}")
        return {
            "success": True,
            "page_id": result["id"],
            "url": result.get("url", "")
        }
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ EXCEPTION EN create_call_record")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e)
        }

def create_or_update_lead(
    phone_number: str,
    name: str = "Sin nombre",
    temperatura: str = "cold",
    resumen_llamada: str = "",
    estatus: str = "Pendiente de llamar"
) -> dict:
    """
    Crea o actualiza un lead en Notion
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LEADS")

        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LEADS no configurada")

        logger.info("=" * 80)
        logger.info(f"🔍 BUSCANDO LEAD EXISTENTE PARA {phone_number}")
        logger.info("=" * 80)
        logger.info(f"Database ID: {db_id}")

        query_payload = {
            "filter": {
                "property": "Teléfono",
                "type": "phone_number",
                "phone_number": {
                    "equals": phone_number
                }
            }
        }
        logger.info(f"\nQUERY PAYLOAD:")
        logger.info(json.dumps(query_payload, indent=2))

        query_response = requests.post(
            f"{NOTION_API_URL}/databases/{db_id}/query",
            headers=get_notion_headers(),
            json=query_payload
        )

        logger.info(f"Query Status Code: {query_response.status_code}")
        logger.info(f"Query Response: {query_response.text}")

        if query_response.status_code != 200:
            logger.error(f"❌ ERROR EN QUERY (status {query_response.status_code}):")
            logger.error(f"Response JSON: {query_response.json()}")
            return {
                "success": False,
                "error": f"Query failed: HTTP {query_response.status_code}",
                "detail": query_response.text
            }

        results = query_response.json()

        if results.get("results"):
            # Actualizar existente
            page_id = results["results"][0]["id"]
            logger.info(f"📝 ACTUALIZANDO LEAD EXISTENTE: {page_id}")

            update_payload = {
                "properties": {
                    "Última Interacción": {"date": {"start": datetime.now().isoformat()}},
                    "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                    "Estatus": {"select": {"name": estatus}},
                    "Temperatura": {"select": {"name": temperatura}},
                }
            }
            logger.info(f"\nUPDATE PAYLOAD:")
            logger.info(json.dumps(update_payload, indent=2, default=str))

            update_response = requests.patch(
                f"{NOTION_API_URL}/pages/{page_id}",
                headers=get_notion_headers(),
                json=update_payload
            )

            logger.info(f"Update Status Code: {update_response.status_code}")
            logger.info(f"Update Response: {update_response.text}")

            if update_response.status_code != 200:
                logger.error(f"❌ ERROR EN UPDATE (status {update_response.status_code}):")
                logger.error(f"Response JSON: {update_response.json()}")
                return {
                    "success": False,
                    "error": f"Update failed: HTTP {update_response.status_code}",
                    "detail": update_response.text
                }

            logger.info(f"✅ Lead actualizado")
            return {
                "success": True,
                "action": "updated",
                "page_id": page_id
            }
        else:
            # Crear nuevo
            logger.info(f"➕ CREANDO NUEVO LEAD PARA {phone_number}")

            create_payload = {
                "parent": {"database_id": db_id},
                "properties": {
                    "Nombre": {"title": [{"text": {"content": name}}]},
                    "Teléfono": {"phone_number": phone_number},
                    "Temperatura": {"select": {"name": temperatura}},
                    "Estatus": {"select": {"name": estatus}},
                    "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                    "Fecha Primer Contacto": {"date": {"start": datetime.now().isoformat()}},
                }
            }
            logger.info(f"\nCREATE PAYLOAD:")
            logger.info(json.dumps(create_payload, indent=2, default=str))

            create_response = requests.post(
                f"{NOTION_API_URL}/pages",
                headers=get_notion_headers(),
                json=create_payload
            )

            logger.info(f"Create Status Code: {create_response.status_code}")
            logger.info(f"Create Response: {create_response.text}")

            if create_response.status_code != 200:
                logger.error(f"❌ ERROR EN CREATE (status {create_response.status_code}):")
                logger.error(f"Response JSON: {create_response.json()}")
                return {
                    "success": False,
                    "error": f"Create failed: HTTP {create_response.status_code}",
                    "detail": create_response.text
                }

            result = create_response.json()
            logger.info(f"✅ Lead creado: {result['id']}")
            return {
                "success": True,
                "action": "created",
                "page_id": result["id"]
            }
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ EXCEPTION EN create_or_update_lead")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e)
        }

