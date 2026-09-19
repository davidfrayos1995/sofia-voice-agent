"""
Servicio Notion para guardar información de llamadas y leads
"""

import os
import logging
import json
from datetime import datetime
from notion_client import Client

logger = logging.getLogger(__name__)

def get_notion_client():
    """Obtiene cliente de Notion autenticado"""
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise ValueError("NOTION_API_KEY no configurada")
    return Client(auth=api_key)

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
        client = get_notion_client()
        db_id = os.getenv("NOTION_DATABASE_ID_LLAMADAS")
        
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LLAMADAS no configurada")
        
        properties = {
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
        
        logger.info(f"📤 Enviando a Notion (crear llamada):")
        logger.info(f"Database ID: {db_id}")
        logger.info(f"Payload: {json.dumps(properties, indent=2)}")
        
        response = client.pages.create(
            parent={"database_id": db_id},
            properties=properties
        )
        
        logger.info(f"✅ Llamada guardada: {response['id']}")
        return {
            "success": True,
            "page_id": response["id"],
            "url": response["url"]
        }
    except Exception as e:
        logger.error(f"❌ Error guardando llamada en Notion:")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"Response body: {getattr(e.response, 'text', 'N/A')}")
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
        client = get_notion_client()
        db_id = os.getenv("NOTION_DATABASE_ID_LEADS")
        
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LEADS no configurada")
        
        # Primero buscar si existe
        logger.info(f"🔍 Buscando lead existente para {phone_number}")
        logger.info(f"Database ID: {db_id}")
        
        query_filter = {
            "property": "Teléfono",
            "phone_number": {
                "equals": phone_number
            }
        }
        logger.info(f"Query filter: {json.dumps(query_filter, indent=2)}")
        
        existing = client.databases.query(
            database_id=db_id,
            filter=query_filter
        )
        
        if existing["results"]:
            # Actualizar existente
            page_id = existing["results"][0]["id"]
            logger.info(f"📝 Actualizando lead existente: {page_id}")
            
            update_props = {
                "Última Interacción": {"date": {"start": datetime.now().isoformat()}},
                "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                "Estatus": {"select": {"name": estatus}},
                "Temperatura": {"select": {"name": temperatura}},
            }
            logger.info(f"Update payload: {json.dumps(update_props, indent=2)}")
            
            client.pages.update(
                page_id=page_id,
                properties=update_props
            )
            return {
                "success": True,
                "action": "updated",
                "page_id": page_id
            }
        else:
            # Crear nuevo
            logger.info(f"➕ Creando nuevo lead para {phone_number}")
            
            create_props = {
                "Nombre": {"title": [{"text": {"content": name}}]},
                "Teléfono": {"phone_number": phone_number},
                "Temperatura": {"select": {"name": temperatura}},
                "Estatus": {"select": {"name": estatus}},
                "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                "Fecha Primer Contacto": {"date": {"start": datetime.now().isoformat()}},
            }
            logger.info(f"Create payload: {json.dumps(create_props, indent=2)}")
            
            response = client.pages.create(
                parent={"database_id": db_id},
                properties=create_props
            )
            logger.info(f"✅ Lead creado: {response['id']}")
            return {
                "success": True,
                "action": "created",
                "page_id": response["id"]
            }
    except Exception as e:
        logger.error(f"❌ Error procesando lead en Notion:")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logger.error(f"Response body: {getattr(e.response, 'text', 'N/A')}")
        return {
            "success": False,
            "error": str(e)
        }

