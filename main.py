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

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.anthropic_service import generate_call_summary, extract_call_metadata
from services.notion_service import create_call_record, create_or_update_lead

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sofia - Agente de Voz IA")

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
            phone_number = payload.get("from_number") or payload.get("phone_number") or "Desconocido"
            transcript = payload.get("transcript", "Sin transcripción disponible")
            duration = payload.get("duration_minutes", 0)
            
            logger.info(f"📞 Llamada finalizada: {call_id} desde {phone_number}")
            
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
                call_type="Entrante"
            )
            
            # 4. Crear o actualizar lead en Notion
            logger.info("👤 Creando/actualizando lead...")
            lead_result = create_or_update_lead(
                phone_number=phone_number,
                name=metadata.get("nombre", "Desconocido"),
                temperatura=metadata.get("interes", "cold"),
                resumen_llamada=summary,
                estatus="En proceso"
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

# API para iniciar llamadas salientes (placeholder)
@app.post("/api/call/initiate")
async def initiate_call(phone_number: str, script: str = None):
    """Inicia una llamada saliente"""
    logger.info(f"📞 Initiating call to {phone_number}")
    return {"status": "initiated", "phone": phone_number}

# API para agendar citas (placeholder)
@app.post("/api/schedule/meeting")
async def schedule_meeting(contact_name: str, contact_email: str, preferred_time: str):
    """Agenda una cita en Cal.com"""
    logger.info(f"📅 Scheduling meeting for {contact_name}")
    return {"status": "scheduled"}

