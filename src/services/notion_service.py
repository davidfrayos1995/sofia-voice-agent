"""
Servicio Notion para guardar información de llamadas, leads y buscar propiedades
"""

import os
import logging
import json
import unicodedata
import requests
from datetime import datetime, timezone
from typing import Optional

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
    duration_minutes: float = 0,
    call_type: str = "Entrante",
    start_timestamp_ms: Optional[int] = None,
    nombre: Optional[str] = None,
) -> dict:
    """
    Crea un registro de llamada en Notion. La fecha es el inicio de la llamada en UTC.
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LLAMADAS")
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LLAMADAS no configurada")

        inicio = (datetime.fromtimestamp(start_timestamp_ms / 1000, tz=timezone.utc)
                  if start_timestamp_ms else datetime.now(timezone.utc))
        etiqueta = nombre or phone_number
        titulo = f"Llamada · {etiqueta} · {inicio.strftime('%Y-%m-%d %H:%M')} UTC"

        payload = {
            "parent": {"database_id": db_id},
            "properties": {
                "Name": {"title": [{"text": {"content": titulo}}]},
                "Fecha": {"date": {"start": inicio.isoformat()}},
                "Contacto": {"rich_text": [{"text": {"content": phone_number}}]},
                "Teléfono": {"phone_number": phone_number},
                "Duración (min)": {"number": duration_minutes},
                "Tipo": {"select": {"name": call_type}},
                "Transcript": {"rich_text": [{"text": {"content": transcript[:2000]}}]},
                "Resumen": {"rich_text": [{"text": {"content": summary[:2000]}}]},
                "Estatus": {"select": {"name": "Completada"}},
                "Call ID": {"rich_text": [{"text": {"content": call_id}}]},
            }
        }

        response = requests.post(
            f"{NOTION_API_URL}/pages",
            headers=get_notion_headers(),
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"❌ Llamada {call_id} no guardada: HTTP {response.status_code} - {response.json().get('message')}")
            return {"success": False, "error": f"HTTP {response.status_code}"}

        logger.info(f"💾 Llamada guardada en Notion: {call_id}")
        return {"success": True, "page_id": response.json()["id"]}
    except Exception as e:
        logger.error(f"❌ Error en create_call_record ({call_id}): {type(e).__name__}: {str(e)}")
        return {"success": False, "error": str(e)}

def _lead_properties(name, temperatura, resumen_llamada, call_id, datos) -> dict:
    props = {}
    if name:
        props["Name"] = {"title": [{"text": {"content": name}}]}
    if temperatura:
        props["Temperatura"] = {"select": {"name": temperatura}}
    if resumen_llamada is not None:
        props["Resumen Llamada"] = {"rich_text": [{"text": {"content": resumen_llamada[:2000]}}]}
    if call_id:
        props["Call ID"] = {"rich_text": [{"text": {"content": call_id}}]}
    datos = datos or {}
    correo = (datos.get("correo") or "").strip()
    if "@" in correo and "." in correo.split("@")[-1]:
        props["Correo"] = {"email": correo}
    for campo, columna in (("zona", "Zona"), ("presupuesto", "Presupuesto")):
        if datos.get(campo):
            props[columna] = {"rich_text": [{"text": {"content": str(datos[campo])[:2000]}}]}
    if datos.get("recamaras") is not None:
        props["Recámaras"] = {"number": datos["recamaras"]}
    if datos.get("tipo_operacion"):
        props["Tipo"] = {"select": {"name": datos["tipo_operacion"]}}
    if datos.get("idioma"):
        props["Idioma"] = {"select": {"name": datos["idioma"]}}
    if datos.get("propiedad_ofrecida"):
        props["Propiedad ofrecida"] = {"rich_text": [{"text": {"content": str(datos["propiedad_ofrecida"])[:2000]}}]}
    return props

def call_record_exists(call_id: str) -> bool:
    """Consulta si ya existe un registro en Llamadas con este Call ID. Ante error, devuelve False."""
    db_id = os.getenv("NOTION_DATABASE_ID_LLAMADAS")
    response = requests.post(
        f"{NOTION_API_URL}/databases/{db_id}/query",
        headers=get_notion_headers(),
        json={"filter": {"property": "Call ID", "rich_text": {"equals": call_id}}},
    )
    if response.status_code != 200:
        logger.warning(f"⚠️ No se pudo verificar Call ID {call_id}: HTTP {response.status_code}")
        return False
    return bool(response.json().get("results"))

def actualizar_resumen_llamada(call_id: str, resumen: str) -> bool:
    """Escribe el resumen de Retell en la fila de Llamadas con ese Call ID. False si no existe."""
    db_id = os.getenv("NOTION_DATABASE_ID_LLAMADAS")
    response = requests.post(
        f"{NOTION_API_URL}/databases/{db_id}/query",
        headers=get_notion_headers(),
        json={"filter": {"property": "Call ID", "rich_text": {"equals": call_id}}},
    )
    if response.status_code != 200 or not response.json().get("results"):
        return False
    page_id = response.json()["results"][0]["id"]
    patch = requests.patch(
        f"{NOTION_API_URL}/pages/{page_id}",
        headers=get_notion_headers(),
        json={"properties": {"Resumen": {"rich_text": [{"text": {"content": resumen[:2000]}}]}}},
    )
    if patch.status_code != 200:
        logger.error(f"❌ No se actualizó Resumen de {call_id}: HTTP {patch.status_code}")
        return False
    return True

PROPIEDADES_OPCIONALES = {"Idioma", "Propiedad ofrecida", "Moneda", "Tipo de propiedad"}

def _escribir_pagina(metodo: str, url: str, props: dict, extra: Optional[dict] = None):
    """Escribe en Notion; si falta una propiedad opcional, reintenta sin ella para no perder el registro."""
    props = dict(props)
    while True:
        payload = {**(extra or {}), "properties": props}
        response = getattr(requests, metodo.lower())(url, headers=get_notion_headers(), json=payload)
        if response.status_code != 400:
            return response
        try:
            mensaje = response.json().get("message", "")
        except ValueError:
            return response
        faltantes = [nombre for nombre in PROPIEDADES_OPCIONALES if nombre in props and nombre in mensaje]
        if not faltantes:
            return response
        for nombre in faltantes:
            logger.warning(f"⚠️ Notion no tiene la columna '{nombre}'; se guarda sin ella")
            props.pop(nombre)

def create_or_update_lead(
    phone_number: str,
    name: Optional[str] = None,
    temperatura: Optional[str] = None,
    resumen_llamada: Optional[str] = None,
    estatus: Optional[str] = "Pendiente de llamar",
    call_id: Optional[str] = None,
    datos: Optional[dict] = None,
    resumen_respaldo: Optional[str] = None,
    nombre_respaldo: Optional[str] = None,
    temperatura_respaldo: Optional[str] = None,
) -> dict:
    """
    Crea o actualiza un lead por teléfono. Si estatus es None, no toca el campo Estatus
    en actualizaciones (usado en outbound, donde mark_lead_status ya lo cambió durante la llamada).
    """
    try:
        db_id = os.getenv("NOTION_DATABASE_ID_LEADS")
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID_LEADS no configurada")

        query_response = requests.post(
            f"{NOTION_API_URL}/databases/{db_id}/query",
            headers=get_notion_headers(),
            json={
                "filter": {
                    "property": "Teléfono",
                    "type": "phone_number",
                    "phone_number": {"equals": phone_number}
                }
            }
        )
        if query_response.status_code != 200:
            logger.error(f"❌ Query de lead falló: HTTP {query_response.status_code} - {query_response.text}")
            return {
                "success": False,
                "error": f"Query failed: HTTP {query_response.status_code}",
                "detail": query_response.text
            }

        props = _lead_properties(name, temperatura, resumen_llamada, call_id, datos)
        results = query_response.json().get("results", [])

        if resumen_llamada is None and resumen_respaldo:
            existente = results[0]["properties"].get("Resumen Llamada", {}).get("rich_text") if results else None
            if not existente:
                props["Resumen Llamada"] = {"rich_text": [{"text": {"content": resumen_respaldo[:2000]}}]}

        if results:
            page_id = results[0]["id"]
            props["Última Interacción"] = {"date": {"start": datetime.now().isoformat()}}
            if estatus is not None:
                props["Estatus"] = {"select": {"name": estatus}}
            response = _escribir_pagina("PATCH", f"{NOTION_API_URL}/pages/{page_id}", props)
            action = "updated"
        else:
            if nombre_respaldo and "Name" not in props:
                props["Name"] = {"title": [{"text": {"content": nombre_respaldo}}]}
            if temperatura_respaldo and "Temperatura" not in props:
                props["Temperatura"] = {"select": {"name": temperatura_respaldo}}
            props.setdefault("Name", {"title": [{"text": {"content": "Desconocido"}}]})
            props.setdefault("Temperatura", {"select": {"name": "cold"}})
            props.setdefault("Resumen Llamada", {"rich_text": []})
            props["Teléfono"] = {"phone_number": phone_number}
            props["Estatus"] = {"select": {"name": estatus or "Pendiente de llamar"}}
            props["Fecha Primer Contacto"] = {"date": {"start": datetime.now().isoformat()}}
            props["Última Interacción"] = {"date": {"start": datetime.now().isoformat()}}
            response = _escribir_pagina("POST", f"{NOTION_API_URL}/pages", props, {"parent": {"database_id": db_id}})
            action = "created"

        if response.status_code != 200:
            logger.error(f"❌ Lead {action} falló: HTTP {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": f"{action} failed: HTTP {response.status_code}",
                "detail": response.text
            }

        page_id = response.json()["id"]
        logger.info(f"✅ Lead {action}: {page_id}")
        return {"success": True, "action": action, "page_id": page_id}
    except Exception as e:
        logger.error(f"❌ Error en create_or_update_lead: {type(e).__name__}: {str(e)}")
        return {"success": False, "error": str(e)}

def _normalizar_texto(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    sin_puntuacion = "".join(" " if unicodedata.category(c).startswith("P") else c for c in sin_acentos)
    return " ".join(sin_puntuacion.lower().split())

_ZONAS_GENERICAS_ES = [
    "", "cualquiera", "cualquier zona", "cualquier colonia", "cualquier lugar", "donde sea",
    "todas", "todas las zonas", "no importa", "me da igual", "indistinto", "sin preferencia",
    "ninguna", "ninguna zona",
]
_ZONAS_GENERICAS_EN = [
    "anywhere", "any area", "any neighborhood", "any zone", "any location", "no preference",
    "doesn't matter", "does not matter", "all", "all areas", "anything", "whatever",
]
ZONAS_GENERICAS = {_normalizar_texto(z) for z in _ZONAS_GENERICAS_ES + _ZONAS_GENERICAS_EN}

TIPOS_OPERACION = {
    "renta": "Renta", "rent": "Renta", "rental": "Renta", "renting": "Renta",
    "compra": "Compra", "buy": "Compra", "buying": "Compra", "purchase": "Compra",
}
TEMPERATURAS = {"hot": "hot", "warm": "warm", "cold": "cold"}
IDIOMAS = {"english": "English", "ingles": "English", "spanish": "Spanish", "espanol": "Spanish"}

def _normalizar_catalogo(valor, catalogo: dict, campo: str):
    if valor is None or not _normalizar_texto(valor):
        return None
    resultado = catalogo.get(_normalizar_texto(valor))
    if resultado is None:
        logger.warning(f"⚠️ Valor no reconocido para {campo}: {valor!r}; no se escribe")
    return resultado

def normalizar_tipo(valor):
    return _normalizar_catalogo(valor, TIPOS_OPERACION, "Tipo")

def normalizar_temperatura(valor):
    return _normalizar_catalogo(valor, TEMPERATURAS, "Temperatura")

def normalizar_idioma(valor):
    return _normalizar_catalogo(valor, IDIOMAS, "Idioma")

def _zona_buscable(zona) -> bool:
    if not zona:
        return False
    return _normalizar_texto(zona) not in ZONAS_GENERICAS

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
                "moneda": (props.get("Moneda", {}).get("select") or {}).get("name") or "MXN",
                "tipo": (props.get("Tipo de propiedad", {}).get("select") or {}).get("name"),
                "recamaras": props.get("Recámaras", {}).get("number"),
                "banos": props.get("Baños", {}).get("number"),
                "m2": props.get("m²", {}).get("number"),
                "disponible": props.get("Disponible", {}).get("select", {}).get("name", ""),
                "descripcion": props.get("Descripción", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            }
            propiedades.append(prop_data)

        if _zona_buscable(ubicacion_filter):
            zona = _normalizar_texto(ubicacion_filter)
            propiedades = [
                p for p in propiedades
                if zona in _normalizar_texto(p.get("ubicacion", "")) or
                   zona in _normalizar_texto(p.get("nombre", ""))
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

