"""
Servicio Notion para guardar información de llamadas y leads
"""

import os
from datetime import datetime
from notion_client import Client

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
        
        response = client.pages.create(
            parent={"database_id": db_id},
            properties={
                "Fecha": {"date": {"start": datetime.now().isoformat()}},
                "Contacto": {"rich_text": [{"text": {"content": phone_number}}]},
                "Teléfono": {"phone_number": phone_number},
                "Duración (min)": {"number": duration_minutes},
                "Tipo": {"select": {"name": call_type}},
                "Transcript": {"rich_text": [{"text": {"content": transcript[:2000]}}]},  # Limitar a 2000 chars
                "Resumen (Anthropic)": {"rich_text": [{"text": {"content": summary[:2000]}}]},
                "Estatus": {"select": {"name": "Completada"}},
                "Call ID": {"rich_text": [{"text": {"content": call_id}}]},
            }
        )
        
        return {
            "success": True,
            "page_id": response["id"],
            "url": response["url"]
        }
    except Exception as e:
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
        existing = client.databases.query(
            database_id=db_id,
            filter={
                "property": "Teléfono",
                "phone_number": {
                    "equals": phone_number
                }
            }
        )
        
        if existing["results"]:
            # Actualizar existente
            page_id = existing["results"][0]["id"]
            client.pages.update(
                page_id=page_id,
                properties={
                    "Última Interacción": {"date": {"start": datetime.now().isoformat()}},
                    "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                    "Estatus": {"select": {"name": estatus}},
                    "Temperatura": {"select": {"name": temperatura}},
                }
            )
            return {
                "success": True,
                "action": "updated",
                "page_id": page_id
            }
        else:
            # Crear nuevo
            response = client.pages.create(
                parent={"database_id": db_id},
                properties={
                    "Nombre": {"title": [{"text": {"content": name}}]},
                    "Teléfono": {"phone_number": phone_number},
                    "Temperatura": {"select": {"name": temperatura}},
                    "Estatus": {"select": {"name": estatus}},
                    "Resumen Llamada": {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]},
                    "Fecha Primer Contacto": {"date": {"start": datetime.now().isoformat()}},
                }
            )
            return {
                "success": True,
                "action": "created",
                "page_id": response["id"]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

