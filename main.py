"""
Sofia Voice Agent - FastAPI Backend
Agente de voz IA para inmobiliaria con Retell AI
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import sys
from apscheduler.schedulers.background import BackgroundScheduler

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.anthropic_service import generate_call_summary, extract_call_metadata
from services.notion_service import (
    create_call_record,
    create_or_update_lead,
    search_properties,
    update_lead_status_by_phone,
)
from worker import process_pending_leads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sofia - Agente de Voz IA")

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    enable_scheduler = os.getenv("ENABLE_OUTBOUND_SCHEDULER", "false").lower() == "true"

    if enable_scheduler:
        scheduler.add_job(
            process_pending_leads,
            "interval",
            hours=1,
            id="outbound_leads_worker",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("🕐 ✅ Scheduler ACTIVADO: worker de leads outbound correrá cada hora")
    else:
        scheduler.start()  # inicia pero sin jobs, solo para shutdown limpio
        logger.info("🕐 ⏸️  Scheduler desactivado (ENABLE_OUTBOUND_SCHEDULER=false). "
                   "Usa POST /api/worker/trigger-outbound para disparar manualmente.")

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "sofia-voice-agent",
        "timestamp": datetime.now().isoformat()
    }

# Webhook de Retell AI
@app.post("/webhooks/retell")
async def retell_webhook(request: Request):
    """
    Procesa eventos de Retell AI:
    - call.started: registra inicio de llamada
    - call.ended: genera resumen, crea lead, guarda en Notion
    """
    try:
        payload = await request.json()
        event_type = payload.get("event")
        
        logger.info(f"🔔 Retell webhook: {event_type}")
        
        # Evento: Fin de llamada
        if event_type == "call.ended":
            call_id = payload.get("call_id")
            call_metadata = payload.get("metadata", {}) or {}
            is_outbound = call_metadata.get("call_type") == "outbound"

            if is_outbound:
                phone_number = call_metadata.get("phone_number") or payload.get("to_number") or "Desconocido"
            else:
                phone_number = payload.get("from_number") or payload.get("phone_number") or "Desconocido"

            transcript = payload.get("transcript", "Sin transcripción disponible")
            duration = payload.get("duration_minutes", 0)
            call_type_label = "Saliente" if is_outbound else "Entrante"

            logger.info(f"📞 Llamada finalizada ({call_type_label}): {call_id} - {phone_number}")

            # 1. Generar resumen con Anthropic
            logger.info("⏳ Generando resumen con Anthropic...")
            summary = generate_call_summary(transcript)

            # 2. Extraer metadata (nombre, interés, etc.)
            logger.info("📊 Extrayendo metadata...")
            metadata = extract_call_metadata(transcript)

            # 3. Guardar registro de llamada en Notion
            logger.info("💾 Guardando llamada en Notion...")
            call_result = create_call_record(
                phone_number=phone_number,
                transcript=transcript,
                summary=summary,
                call_id=call_id,
                duration_minutes=duration,
                call_type=call_type_label
            )

            # 4. Crear o actualizar lead en Notion
            # En llamadas outbound, el estatus ya lo actualizó la función mark_lead_status
            # durante la llamada; aquí solo refrescamos resumen/temperatura sin pisarlo.
            logger.info("👤 Creando/actualizando lead...")
            lead_result = create_or_update_lead(
                phone_number=phone_number,
                name=metadata.get("nombre", "Desconocido"),
                temperatura=metadata.get("interes", "cold"),
                resumen_llamada=summary,
                estatus=None if is_outbound else "En proceso"
            )
            
            logger.info(f"✅ Procesamiento completado para {call_id}")
            
            return {
                "status": "processed",
                "call_id": call_id,
                "summary_generated": True,
                "notion_call_saved": call_result.get("success", False),
                "notion_lead_saved": lead_result.get("success", False),
                "metadata": metadata
            }
        
        # Evento: Inicio de llamada
        elif event_type == "call.started":
            call_id = payload.get("call_id")
            logger.info(f"📞 Llamada iniciada: {call_id}")
            return {"status": "acknowledged", "call_id": call_id}
        
        # Otros eventos
        else:
            logger.info(f"ℹ️ Evento ignorado: {event_type}")
            return {"status": "received", "event": event_type}
            
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# Webhook de Twilio (placeholder)
@app.post("/webhooks/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """Recibe SMS de Twilio"""
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        message_body = form_data.get("Body")
        logger.info(f"📱 SMS from {from_number}: {message_body}")
        return JSONResponse({"status": "processed"})
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------------------------
# Custom functions llamadas por Retell durante la llamada outbound (function calling)
# ---------------------------------------------------------------------------

@app.post("/api/functions/search_properties")
async def function_search_properties(request: Request):
    """Función custom de Retell: busca propiedades durante la llamada"""
    try:
        body = await request.json()
        args = body.get("args", body)  # Retell envía {"args": {...}}, soportamos ambos formatos

        logger.info(f"🔧 [Retell function] search_properties args={args}")

        result = search_properties(
            ubicacion_filter=args.get("ubicacion_filter"),
            precio_max=args.get("precio_max"),
            recamaras_min=args.get("recamaras_min"),
        )

        if not result.get("success"):
            return {"result": "No pude consultar las propiedades en este momento."}

        propiedades = result.get("propiedades", [])[:3]
        if not propiedades:
            return {"result": "No encontré propiedades disponibles con esos criterios por ahora."}

        resumen = "; ".join(
            f"{p['nombre']} en {p['ubicacion']}, ${p['precio']:,.0f} al mes, {int(p['recamaras'])} recámaras"
            for p in propiedades
        )
        return {"result": f"Encontré estas opciones: {resumen}."}
    except Exception as e:
        logger.error(f"❌ Error en function_search_properties: {str(e)}", exc_info=True)
        return {"result": "Tuve un problema buscando propiedades, sigamos con la llamada."}

@app.post("/api/functions/mark_lead_status")
async def function_mark_lead_status(request: Request):
    """Función custom de Retell: actualiza el estatus del lead durante/al final de la llamada"""
    try:
        body = await request.json()
        args = body.get("args", body)

        phone_number = args.get("phone_number")
        status = args.get("status")

        logger.info(f"🔧 [Retell function] mark_lead_status phone={phone_number} status={status}")

        if not phone_number or not status:
            return {"result": "Faltan datos para actualizar el lead."}

        result = update_lead_status_by_phone(phone_number, status)

        if result.get("success"):
            return {"result": f"Estatus actualizado a {status}."}
        return {"result": "No pude actualizar el estatus del lead."}
    except Exception as e:
        logger.error(f"❌ Error en function_mark_lead_status: {str(e)}", exc_info=True)
        return {"result": "Tuve un problema actualizando el estatus."}

# ---------------------------------------------------------------------------
# Worker autónomo de leads outbound
# ---------------------------------------------------------------------------

@app.post("/api/worker/trigger-outbound")
async def trigger_outbound_worker():
    """
    Dispara manualmente el worker que revisa leads 'Pendiente de llamar'
    y les marca la llamada outbound. Uso: demos, pruebas, o forzar una corrida.
    """
    logger.info("🖱️  Worker disparado MANUALMENTE vía endpoint")
    result = process_pending_leads()
    return result

