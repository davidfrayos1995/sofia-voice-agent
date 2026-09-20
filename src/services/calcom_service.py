"""
Servicio Cal.com para agendamiento de citas
"""

import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CALCOM_API_URL = "https://api.cal.com/v1"

def get_calcom_headers():
    """Obtiene headers para autenticación con Cal.com"""
    api_key = os.getenv("CALCOM_API_KEY")
    if not api_key:
        raise ValueError("CALCOM_API_KEY no configurada")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def create_booking(
    guest_name: str,
    guest_email: str,
    guest_phone: str,
    event_type_id: int,
    start_time: str,
    notes: str = ""
) -> dict:
    """
    Crea una cita en Cal.com

    Args:
        guest_name: Nombre del cliente
        guest_email: Email del cliente
        guest_phone: Teléfono del cliente
        event_type_id: ID del tipo de evento en Cal.com
        start_time: Hora de inicio (ISO format: 2024-12-20T15:00:00)
        notes: Notas adicionales
    """
    try:
        logger.info("=" * 80)
        logger.info("📅 CREANDO CITA EN CAL.COM")
        logger.info("=" * 80)
        logger.info(f"Guest: {guest_name} <{guest_email}>")
        logger.info(f"Teléfono: {guest_phone}")
        logger.info(f"Event Type ID: {event_type_id}")
        logger.info(f"Start Time: {start_time}")

        payload = {
            "eventTypeId": event_type_id,
            "start": start_time,
            "guests": [guest_email],
            "name": guest_name,
            "email": guest_email,
            "notes": notes or f"Teléfono: {guest_phone}"
        }

        logger.info(f"\nPAYLOAD:")
        import json
        logger.info(json.dumps(payload, indent=2))

        response = requests.post(
            f"{CALCOM_API_URL}/bookings",
            headers=get_calcom_headers(),
            json=payload
        )

        logger.info(f"\nStatus Code: {response.status_code}")
        logger.info(f"Response: {response.text}")

        if response.status_code not in [200, 201]:
            logger.error(f"❌ ERROR (status {response.status_code}):")
            logger.error(f"Response: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        result = response.json()
        booking_id = result.get("booking", {}).get("id") or result.get("id")
        logger.info(f"✅ Cita creada: {booking_id}")

        return {
            "success": True,
            "booking_id": booking_id,
            "booking_url": result.get("booking", {}).get("rescheduleUrl") or ""
        }
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ EXCEPTION EN create_booking")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e)
        }

def get_available_slots(
    event_type_id: int,
    start_date: str = None,
    end_date: str = None
) -> dict:
    """
    Obtiene slots disponibles para un evento

    Args:
        event_type_id: ID del tipo de evento
        start_date: Fecha inicial (YYYY-MM-DD), default: hoy
        end_date: Fecha final (YYYY-MM-DD), default: +30 días
    """
    try:
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        logger.info(f"📅 Obteniendo slots disponibles para evento {event_type_id}")
        logger.info(f"Rango: {start_date} a {end_date}")

        response = requests.get(
            f"{CALCOM_API_URL}/availability",
            headers=get_calcom_headers(),
            params={
                "eventTypeId": event_type_id,
                "startDate": start_date,
                "endDate": end_date
            }
        )

        if response.status_code != 200:
            logger.error(f"Error obteniendo slots: {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

        result = response.json()
        slots = result.get("slots", {})
        logger.info(f"✅ {len(slots)} slots disponibles")

        return {
            "success": True,
            "slots": slots
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def get_event_types() -> dict:
    """
    Obtiene los tipos de eventos disponibles en Cal.com
    """
    try:
        logger.info("📅 Obteniendo tipos de eventos de Cal.com")

        response = requests.get(
            f"{CALCOM_API_URL}/event-types",
            headers=get_calcom_headers()
        )

        if response.status_code != 200:
            logger.error(f"Error: {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

        result = response.json()
        event_types = result.get("event_types", [])
        logger.info(f"✅ {len(event_types)} tipos de eventos encontrados")

        for et in event_types:
            logger.info(f"  • {et.get('title')} (ID: {et.get('id')})")

        return {
            "success": True,
            "event_types": event_types
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
