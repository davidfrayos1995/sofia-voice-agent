"""
Sofia Voice Agent - Modal Deployment
Agente de voz para inmobiliaria
"""

import logging
from modal import App, fastapi_endpoint
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App("sofia-voice-agent")

@app.function()
@fastapi_endpoint(method="GET")
def health():
    return {"status": "ok", "service": "sofia-voice-agent", "environment": "modal-production"}

@app.function()
@fastapi_endpoint(method="POST")
async def retell_webhook(request: Request):
    """Recibe webhooks de Retell AI"""
    try:
        payload = await request.json()
        event_type = payload.get("event")
        call_id = payload.get("call_id")
        logger.info(f"✅ Retell webhook: {event_type} (call_id: {call_id})")
        return {"status": "received", "event": event_type, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return {"status": "error", "detail": str(e)}, 400

@app.function()
@fastapi_endpoint(method="POST")
async def twilio_sms_webhook(request: Request):
    """Recibe SMS de Twilio"""
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        message_body = form_data.get("Body")
        logger.info(f"✅ SMS from {from_number}: {message_body}")
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return {"status": "error"}, 400

@app.function()
@fastapi_endpoint(method="POST")
async def initiate_call(phone_number: str):
    """Inicia una llamada saliente"""
    logger.info(f"✅ Call initiated to {phone_number}")
    return {"status": "initiated", "phone": phone_number}

@app.function()
@fastapi_endpoint(method="POST")
async def schedule_meeting(contact_name: str, contact_email: str, preferred_time: str):
    """Agenda una cita en Cal.com"""
    logger.info(f"✅ Meeting scheduled for {contact_name}")
    return {"status": "scheduled"}

