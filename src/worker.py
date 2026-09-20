"""
Worker autónomo: revisa leads "Pendiente de llamar" en Notion y dispara
llamadas outbound con el agente Sofia (Retell), espaciadas para no saturar.
"""

import os
import time
import logging

from services.notion_service import get_pending_leads, update_lead_status_by_id
from services.retell_service import trigger_outbound_call

logger = logging.getLogger(__name__)

SECONDS_BETWEEN_CALLS = int(os.getenv("OUTBOUND_CALL_DELAY_SECONDS", "30"))

def process_pending_leads():
    """
    Job principal del worker. Se ejecuta cada hora (o manualmente).
    """
    logger.info("=" * 80)
    logger.info("🔄 WORKER INICIADO - Revisando leads pendientes de llamar")
    logger.info("=" * 80)

    result = get_pending_leads()

    if not result.get("success"):
        logger.error(f"❌ Worker abortado: no se pudo consultar leads - {result.get('error')}")
        return {"success": False, "error": result.get("error")}

    leads = result.get("leads", [])
    logger.info(f"📋 {len(leads)} leads pendientes encontrados")

    if not leads:
        logger.info("✅ No hay leads pendientes. Worker termina sin acción.")
        return {"success": True, "processed": 0, "calls_triggered": 0}

    calls_triggered = 0
    calls_failed = 0
    skipped_no_phone = 0

    for i, lead in enumerate(leads, 1):
        nombre = lead.get("nombre", "Desconocido")
        telefono = lead.get("telefono", "")
        page_id = lead.get("page_id")

        logger.info("-" * 80)
        logger.info(f"👤 [{i}/{len(leads)}] Procesando lead: {nombre} ({telefono})")

        if not telefono:
            logger.warning(f"⚠️  Lead {nombre} no tiene teléfono. Se salta.")
            skipped_no_phone += 1
            continue

        # 1. Marcar de inmediato como "En proceso" para evitar llamadas duplicadas
        #    si el worker vuelve a correr antes de que termine esta llamada.
        update_result = update_lead_status_by_id(page_id, "En proceso")
        if not update_result.get("success"):
            logger.error(f"❌ No se pudo actualizar estatus de {nombre} antes de llamar. Se salta para evitar llamada duplicada.")
            calls_failed += 1
            continue

        logger.info(f"✅ Lead {nombre} marcado como 'En proceso' (evita doble llamada)")

        # 2. Disparar la llamada outbound
        logger.info(f"📞 Llamando a {nombre} ({telefono})...")
        call_result = trigger_outbound_call(
            to_number=telefono,
            lead_name=nombre,
            zona_interes=lead.get("zona_interes", "la zona que consultó"),
            resumen_anterior=lead.get("resumen_llamada", ""),
            lead_page_id=page_id
        )

        if call_result.get("success"):
            logger.info(f"✅ Llamada disparada exitosamente a {nombre} (call_id: {call_result.get('call_id')})")
            calls_triggered += 1
        else:
            logger.error(f"❌ Falló la llamada a {nombre}: {call_result.get('error')}")
            calls_failed += 1
            # Revertir estatus para reintentar en la siguiente corrida
            update_lead_status_by_id(page_id, "Pendiente de llamar")
            logger.info(f"↩️  Lead {nombre} revertido a 'Pendiente de llamar' para reintentar después")

        # 3. Esperar antes de la siguiente llamada (excepto en la última)
        if i < len(leads):
            logger.info(f"⏳ Esperando {SECONDS_BETWEEN_CALLS}s antes de la siguiente llamada...")
            time.sleep(SECONDS_BETWEEN_CALLS)

    logger.info("=" * 80)
    logger.info(f"✅ WORKER FINALIZADO: {calls_triggered} llamadas disparadas, "
                f"{calls_failed} fallidas, {skipped_no_phone} sin teléfono")
    logger.info("=" * 80)

    return {
        "success": True,
        "processed": len(leads),
        "calls_triggered": calls_triggered,
        "calls_failed": calls_failed,
        "skipped_no_phone": skipped_no_phone
    }
