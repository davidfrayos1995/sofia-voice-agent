import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from src.integrations.notion_service import NotionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sofia - Agente de Voz IA")
notion = NotionService()

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

# Endpoints para funciones custom de Retell
@app.post("/functions/search_properties")
async def search_properties(request: Request):
    """
    Busca propiedades en Notion según criterios.
    Llamada por Sofia durante la conversación.
    """
    try:
        body = await request.json()
        criteria = body.get("args", {})

        logger.info(f"Search properties with criteria: {criteria}")

        properties = notion.search_properties(criteria)

        return {
            "properties": properties,
            "total": len(properties),
            "message": f"Se encontraron {len(properties)} propiedades que coinciden con tus criterios."
        }
    except Exception as e:
        logger.error(f"Error searching properties: {str(e)}")
        return {
            "properties": [],
            "total": 0,
            "error": str(e)
        }

@app.post("/functions/get_property_details")
async def get_property_details(request: Request):
    """
    Obtiene detalles completos de una propiedad.
    """
    try:
        body = await request.json()
        property_id = body.get("args", {}).get("property_id")

        logger.info(f"Get property details for: {property_id}")

        if not property_id:
            return {"error": "property_id is required"}

        details = notion.get_property_details(property_id)

        if not details:
            return {"error": f"Property {property_id} not found"}

        return details

    except Exception as e:
        logger.error(f"Error getting property details: {str(e)}")
        return {"error": str(e)}

@app.post("/functions/register_lead")
async def register_lead(request: Request):
    """
    Registra un lead en Notion con información del cliente.
    """
    try:
        body = await request.json()
        args = body.get("args", {})

        lead_data = {
            "name": args.get("name"),
            "phone": args.get("phone"),
            "email": args.get("email"),
            "interested_properties": args.get("interested_properties", []),
            "budget": args.get("budget")
        }

        logger.info(f"Registering lead: {lead_data['name']}")

        lead_id = notion.register_lead(lead_data)

        if lead_id:
            return {
                "status": "registered",
                "lead_id": lead_id,
                "message": f"Lead {lead_data['name']} registrado exitosamente en Notion"
            }
        else:
            return {
                "status": "error",
                "message": "Error al registrar el lead en Notion"
            }

    except Exception as e:
        logger.error(f"Error registering lead: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/functions/schedule_visit")
async def schedule_visit(request: Request):
    """
    Agenda una visita a una propiedad.
    """
    try:
        body = await request.json()
        args = body.get("args", {})

        visit_data = {
            "property_id": args.get("property_id"),
            "client_name": args.get("client_name"),
            "client_email": args.get("client_email"),
            "client_phone": args.get("client_phone"),
            "preferred_date": args.get("preferred_date"),
            "preferred_time": args.get("preferred_time")
        }

        logger.info(f"Scheduling visit for {visit_data['client_name']}")

        visit_id = notion.schedule_visit(visit_data)

        if visit_id:
            return {
                "status": "scheduled",
                "visit_id": visit_id,
                "confirmation_message": f"Visita a la propiedad agendada para {visit_data['preferred_date']} a las {visit_data['preferred_time']}. Te enviaremos la confirmación al correo {visit_data['client_email']}"
            }
        else:
            return {
                "status": "error",
                "message": "Error al agendar la visita en Notion"
            }

    except Exception as e:
        logger.error(f"Error scheduling visit: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
