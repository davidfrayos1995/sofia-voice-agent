"""
Servicio Notion para guardar información de llamadas, leads y buscar propiedades
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
    Crea o actualiza un lead en Notion.
    Si estatus es None, no se modifica el campo Estatus (usado en llamadas outbound
    donde el estatus ya fue actualizado por mark_lead_status durante la llamada).
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
                    "Temperatura": {"select": {"name": temperatura}},
                }
            }
            if estatus is not None:
                update_payload["properties"]["Estatus"] = {"select": {"name": estatus}}
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
                    "Name": {"title": [{"text": {"content": name}}]},
                    "Teléfono": {"phone_number": phone_number},
                    "Temperatura": {"select": {"name": temperatura}},
                    "Estatus": {"select": {"name": estatus or "Pendiente de llamar"}},
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

def search_properties(
    ubicacion_filter: str = None,
    precio_max: int = None,
    precio_min: int = None,
    recamaras_min: int = None,
    disponible_only: bool = True
) -> dict:
    """
    Busca propiedades en Notion según criterios

    Args:
        ubicacion_filter: Texto para buscar en ubicación (zona)
        precio_max: Precio máximo mensual
        precio_min: Precio mínimo mensual
        recamaras_min: Número mínimo de recámaras
        disponible_only: Si solo buscar propiedades disponibles
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_PROPIEDADES")

        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_PROPIEDADES no configurada")

        logger.info("=" * 80)
        logger.info("🔍 BUSCANDO PROPIEDADES EN NOTION")
        logger.info("=" * 80)
        logger.info(f"Ubicación: {ubicacion_filter or 'sin filtro'}")
        precio_min_str = f"${precio_min:,}" if precio_min else "$0"
        precio_max_str = f"${precio_max:,}" if precio_max else "sin límite"
        logger.info(f"Precio: {precio_min_str} - {precio_max_str}")
        logger.info(f"Recámaras mínimas: {recamaras_min or 'sin filtro'}")
        logger.info(f"Solo disponibles: {disponible_only}")

        filters = []

        if disponible_only:
            filters.append({
                "property": "Disponible",
                "select": {
                    "equals": "Sí"
                }
            })

        if precio_max:
            filters.append({
                "property": "Precio Mensual",
                "number": {
                    "less_than_or_equal_to": precio_max
                }
            })

        if precio_min:
            filters.append({
                "property": "Precio Mensual",
                "number": {
                    "greater_than_or_equal_to": precio_min
                }
            })

        if recamaras_min:
            filters.append({
                "property": "Recámaras",
                "number": {
                    "greater_than_or_equal_to": recamaras_min
                }
            })

        query_payload = {}
        if filters:
            if len(filters) == 1:
                query_payload["filter"] = filters[0]
            else:
                query_payload["filter"] = {
                    "and": filters
                }

        logger.info(f"\nQuery payload: {json.dumps(query_payload, indent=2)}")

        response = requests.post(
            f"{NOTION_API_URL}/databases/{db_id}/query",
            headers=get_notion_headers(),
            json=query_payload
        )

        logger.info(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Error en búsqueda: {response.status_code}")
            logger.error(response.text)
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

        results = response.json().get("results", [])
        propiedades = []

        for page in results:
            props = page["properties"]
            prop_data = {
                "id": page["id"],
                "nombre": props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                "ubicacion": props.get("Ubicación", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "precio": props.get("Precio Mensual", {}).get("number"),
                "recamaras": props.get("Recámaras", {}).get("number"),
                "banos": props.get("Baños", {}).get("number"),
                "m2": props.get("m²", {}).get("number"),
                "disponible": props.get("Disponible", {}).get("select", {}).get("name", ""),
                "descripcion": props.get("Descripción", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            }
            propiedades.append(prop_data)

        # Filtro adicional en memoria para ubicación (búsqueda por texto)
        if ubicacion_filter:
            ubicacion_lower = ubicacion_filter.lower()
            propiedades = [
                p for p in propiedades
                if ubicacion_lower in p.get("ubicacion", "").lower() or
                   ubicacion_lower in p.get("nombre", "").lower()
            ]

        logger.info(f"\n✅ Encontradas {len(propiedades)} propiedades")
        for prop in propiedades:
            precio = prop.get('precio') or 0
            logger.info(f"  • {prop['nombre']} - ${precio:,} - {prop['ubicacion']}")

        return {
            "success": True,
            "count": len(propiedades),
            "propiedades": propiedades
        }
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ EXCEPTION EN search_properties")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e)
        }

def get_pending_leads() -> dict:
    """
    Obtiene todos los leads con estatus "Pendiente de llamar" de la base de datos de Leads
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LEADS")
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LEADS no configurada")

        query_payload = {
            "filter": {
                "property": "Estatus",
                "select": {
                    "equals": "Pendiente de llamar"
                }
            }
        }

        logger.info("🔍 Consultando leads con estatus 'Pendiente de llamar'")

        response = requests.post(
            f"{NOTION_API_URL}/databases/{db_id}/query",
            headers=get_notion_headers(),
            json=query_payload
        )

        if response.status_code != 200:
            logger.error(f"❌ Error consultando leads pendientes: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text}

        results = response.json().get("results", [])
        leads = []
        for page in results:
            props = page["properties"]
            name_title = props.get("Name", {}).get("title", [])
            resumen_rt = props.get("Resumen Llamada", {}).get("rich_text", [])
            leads.append({
                "page_id": page["id"],
                "nombre": name_title[0]["text"]["content"] if name_title else "Desconocido",
                "telefono": props.get("Teléfono", {}).get("phone_number", ""),
                "temperatura": (props.get("Temperatura", {}).get("select") or {}).get("name", ""),
                "resumen_llamada": resumen_rt[0]["text"]["content"] if resumen_rt else ""
            })

        logger.info(f"✅ {len(leads)} leads pendientes encontrados")
        return {"success": True, "leads": leads}
    except Exception as e:
        logger.error(f"❌ Error en get_pending_leads: {str(e)}")
        return {"success": False, "error": str(e)}

def update_lead_status_by_id(page_id: str, status: str) -> dict:
    """
    Actualiza únicamente el estatus de un lead por su page_id (rápido, sin query)
    """
    try:
        payload = {
            "properties": {
                "Estatus": {"select": {"name": status}},
                "Última Interacción": {"date": {"start": datetime.now().isoformat()}}
            }
        }

        response = requests.patch(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=get_notion_headers(),
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"❌ Error actualizando estatus de lead {page_id}: {response.text}")
            return {"success": False, "error": response.text}

        logger.info(f"✅ Lead {page_id} actualizado a estatus '{status}'")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Error en update_lead_status_by_id: {str(e)}")
        return {"success": False, "error": str(e)}

def update_lead_status_by_phone(phone_number: str, status: str) -> dict:
    """
    Busca un lead por teléfono y actualiza su estatus (usado por la función de Retell durante la llamada)
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LEADS")
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LEADS no configurada")

        query_payload = {
            "filter": {
                "property": "Teléfono",
                "type": "phone_number",
                "phone_number": {"equals": phone_number}
            }
        }

        response = requests.post(
            f"{NOTION_API_URL}/databases/{db_id}/query",
            headers=get_notion_headers(),
            json=query_payload
        )

        if response.status_code != 200 or not response.json().get("results"):
            logger.error(f"❌ No se encontró lead con teléfono {phone_number}")
            return {"success": False, "error": "Lead no encontrado"}

        page_id = response.json()["results"][0]["id"]
        return update_lead_status_by_id(page_id, status)
    except Exception as e:
        logger.error(f"❌ Error en update_lead_status_by_phone: {str(e)}")
        return {"success": False, "error": str(e)}

