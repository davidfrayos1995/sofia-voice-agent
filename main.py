import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sofia - Agente de Voz IA")

# Health check para Railway
@app.get("/health")
async def health():
    return {"status": "ok", "service": "sofia-voice-agent"}

# Webhook de Retell AI (llamadas entrantes/salientes)
@app.post("/webhooks/retell")
async def retell_webhook(request: Request):
    """
    Recibe eventos de Retell AI:
    - call.started
    - call.ended
    - message.received
    - etc.
    """
    try:
        payload = await request.json()
        event_type = payload.get("event")
        logger.info(f"Retell webhook received: {event_type}")

        # TODO: Procesar eventos según tipo
        # - call.started → crear registro en Notion
        # - call.ended → generar resumen con Anthropic, guardar en Notion
        # - message.received → procesar y responder

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error in retell_webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Webhook de Twilio (SMS entrantes)
@app.post("/webhooks/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """
    Recibe SMS de Twilio cuando alguien manda un mensaje al número.
    """
    try:
        form_data = await request.form()
        from_number = form_data.get("From")
        message_body = form_data.get("Body")

        logger.info(f"SMS from {from_number}: {message_body}")

        # TODO: Procesar SMS, pasar a Retell AI o responder directamente

        return JSONResponse({"status": "processed"})
    except Exception as e:
        logger.error(f"Error in twilio_sms_webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para triggerear llamadas salientes (desde Notion/Admin)
@app.post("/api/call/initiate")
async def initiate_call(phone_number: str, script: str = None):
    """
    Inicia una llamada saliente a un número.
    """
    try:
        # TODO: Validar número, crear llamada en Retell AI
        logger.info(f"Initiating call to {phone_number}")
        return {"status": "initiated", "phone": phone_number}
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para agendar cita en Cal.com
@app.post("/api/schedule/meeting")
async def schedule_meeting(contact_name: str, contact_email: str, preferred_time: str):
    """
    Agenda una cita en Cal.com después de una llamada.
    """
    try:
        # TODO: Crear evento en Cal.com, notificar
        logger.info(f"Scheduling meeting for {contact_name}")
        return {"status": "scheduled"}
    except Exception as e:
        logger.error(f"Error scheduling meeting: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
