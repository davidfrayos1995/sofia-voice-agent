"""
Sofia Voice Agent - FastAPI Backend
Agente de voz IA para inmobiliaria con Retell AI
"""

import os
import json
import logging
import threading
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from retell.lib.webhook_auth import verify as verificar_firma_retell

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.anthropic_service import generate_call_summary, extract_call_metadata, resumen_es_valido
from services.notion_service import (
    _zona_buscable,
    actualizar_resumen_llamada,
    normalizar_idioma,
    normalizar_temperatura,
    normalizar_tipo,
    call_record_exists,
    create_call_record,
    create_or_update_lead,
    search_properties,
    update_lead_status_by_phone,
    zonas_con_propiedades,
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
lead_lock = threading.Lock()

def _es_outbound(call: dict) -> bool:
    return call.get("direction") == "outbound"

def _telefono_del_lead(call: dict) -> str:
    return (call.get("to_number") if _es_outbound(call) else call.get("from_number")) or ""

NOMBRES_INVALIDOS = {"", "Error", "Desconocido"}
RETELL_SIGNATURE_MODE = os.getenv("RETELL_SIGNATURE_MODE", "log").lower()

def _nombre_valido(metadata: dict):
    if metadata.get("ok") is not True:
        return None
    nombre = (metadata.get("nombre") or "").strip()
    return None if nombre in NOMBRES_INVALIDOS else nombre

def _temperatura_valida(metadata: dict):
    if metadata.get("ok") is not True:
        return None
    return normalizar_temperatura(metadata.get("interes"))

VALORES_SIN_DATO = {"", "no especificado", "no especificada", "desconocido", "desconocida", "n/a", "na", "none", "null", "sin dato"}
resumenes_retell_pendientes = {}

def _dato(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return None if texto.lower() in VALORES_SIN_DATO else texto

def _dato_numerico(valor):
    texto = _dato(valor)
    if texto is None:
        return None
    try:
        numero = float(texto)
    except ValueError:
        return None
    if numero == 0:
        return None
    return int(numero) if numero.is_integer() else numero

def procesar_call_ended(call: dict):
    call_id = call.get("call_id")
    phone_number = _telefono_del_lead(call)
    outbound = _es_outbound(call)

    if not phone_number:
        logger.warning(f"⚠️ call_ended {call_id} sin teléfono, se omite")
        return

    try:
        if call_record_exists(call_id):
            logger.info(f"⏭️ call_ended {call_id} ya procesado, se omite")
            return

        transcript = call.get("transcript") or "Sin transcripción disponible"
        summary = generate_call_summary(transcript)
        resumen_ok = resumen_es_valido(summary)
        metadata = extract_call_metadata(transcript)

        with lead_lock:
            if call_record_exists(call_id):
                logger.info(f"⏭️ call_ended {call_id} ya procesado, se omite")
                return

            resumen_retell = resumenes_retell_pendientes.pop(call_id, None)
            resumen_llamada = resumen_retell or (summary if resumen_ok else "Sin resumen disponible")

            create_call_record(
                phone_number=phone_number,
                transcript=transcript,
                summary=resumen_llamada,
                call_id=call_id,
                duration_minutes=round((call.get("duration_ms") or 0) / 60000, 2),
                call_type="Saliente" if outbound else "Entrante",
                start_timestamp_ms=call.get("start_timestamp"),
                nombre=_nombre_valido(metadata),
            )

            create_or_update_lead(
                phone_number=phone_number,
                estatus=None if outbound else "En proceso",
                resumen_llamada=resumen_retell,
                resumen_respaldo=summary if resumen_ok else None,
                call_id=call_id,
                nombre_respaldo=_nombre_valido(metadata),
                temperatura_respaldo=_temperatura_valida(metadata),
            )
        logger.info(f"✅ call_ended procesado: {call_id}")
    except Exception:
        logger.exception(f"❌ Error procesando call_ended {call_id}")

def procesar_call_analyzed(call: dict):
    call_id = call.get("call_id")
    phone_number = _telefono_del_lead(call)
    if not phone_number:
        logger.warning(f"⚠️ call_analyzed {call_id} sin teléfono, se omite")
        return

    call_analysis = call.get("call_analysis") or {}
    analysis = call_analysis.get("custom_analysis_data") or {}
    resumen_retell = _dato(call_analysis.get("call_summary"))
    datos = {
        "correo": _dato(analysis.get("correo")),
        "zona": _dato(analysis.get("zona")),
        "presupuesto": _dato(analysis.get("presupuesto")),
        "recamaras": _dato_numerico(analysis.get("recamaras")),
        "tipo_operacion": normalizar_tipo(_dato(analysis.get("tipo_operacion"))),
        "propiedad_ofrecida": _dato(analysis.get("propiedad_ofrecida")),
        "idioma": normalizar_idioma(_dato(analysis.get("idioma"))),
    }

    try:
        with lead_lock:
            create_or_update_lead(
                phone_number=phone_number,
                name=_dato(analysis.get("nombre")),
                temperatura=normalizar_temperatura(_dato(analysis.get("temperatura"))),
                resumen_llamada=resumen_retell,
                estatus=None if _es_outbound(call) else "En proceso",
                call_id=call_id,
                datos=datos,
            )
            if resumen_retell and not actualizar_resumen_llamada(call_id, resumen_retell):
                resumenes_retell_pendientes[call_id] = resumen_retell
        logger.info(f"✅ call_analyzed procesado: {call_id}")
    except Exception:
        logger.exception(f"❌ Error procesando call_analyzed {call_id}")

@app.post("/webhooks/retell")
async def retell_webhook(request: Request, background_tasks: BackgroundTasks):
    raw = await request.body()
    firma = request.headers.get("x-retell-signature", "")
    api_key = os.getenv("RETELL_API_KEY", "")
    firma_valida = bool(api_key and firma) and verificar_firma_retell(raw.decode("utf-8"), api_key, firma)
    if not firma_valida:
        if RETELL_SIGNATURE_MODE == "strict":
            logger.warning("❌ Webhook rechazado: firma de Retell inválida o ausente")
            raise HTTPException(status_code=401, detail="firma inválida")
        logger.warning("⚠️ Firma de Retell inválida o ausente (modo log: se acepta)")

    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event = payload.get("event")
    call = payload.get("call") or {}
    call_id = call.get("call_id")
    logger.info(f"🔔 Retell webhook: {event} ({call_id})")

    if event == "call_started":
        return {"status": "acknowledged", "call_id": call_id}
    if event == "call_ended":
        background_tasks.add_task(procesar_call_ended, call)
        return {"status": "accepted", "call_id": call_id}
    if event == "call_analyzed":
        background_tasks.add_task(procesar_call_analyzed, call)
        return {"status": "accepted", "call_id": call_id}

    logger.info(f"ℹ️ Evento ignorado: {event}")
    return {"status": "ignored", "event": event}

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

def _texto_zonas() -> str:
    zonas = zonas_con_propiedades()
    return ", ".join(zonas) if zonas else "none right now"

def _describir_propiedad(p: dict) -> str:
    nombre = f"{p['nombre']} ({p['tipo']})" if p.get("tipo") else p["nombre"]
    partes = [f"{nombre} in {p['ubicacion']}"]
    if p.get("precio") is not None:
        partes.append(f"${p['precio']:,.0f} per month ({p.get('moneda') or 'MXN'})")
    if p.get("recamaras") is not None:
        n = int(p["recamaras"])
        partes.append("studio" if n == 0 else f"{n} bedroom{'' if n == 1 else 's'}")
    if p.get("banos") is not None:
        b = p["banos"]
        partes.append(f"{b:g} bath{'' if b == 1 else 's'}")
    return ", ".join(partes)

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
            return {"result": "Listings are unavailable right now."}

        zona_pedida = args.get("ubicacion_filter")
        buscando_zona = _zona_buscable(zona_pedida)
        todas = result.get("propiedades", [])
        if not todas:
            if buscando_zona:
                return {"result": f"No listings found in '{zona_pedida}'. Areas with listings: {_texto_zonas()}."}
            return {"result": f"No listings match those criteria. Areas with listings: {_texto_zonas()}."}

        por_precio = sorted(todas, key=lambda p: (p.get("precio") is None, p.get("precio") or 0))
        mostradas = por_precio[:3]
        descripciones = "; ".join(_describir_propiedad(p) for p in mostradas)
        if len(todas) > len(mostradas):
            encabezado = f"Found {len(todas)} listings; showing {len(mostradas)}"
        else:
            encabezado = f"Found {len(todas)} listing{'' if len(todas) == 1 else 's'}"
        texto = f"{encabezado}: {descripciones}."
        if not buscando_zona:
            texto += f" Areas with listings: {_texto_zonas()}."
        return {"result": texto}
    except Exception as e:
        logger.error(f"❌ Error en function_search_properties: {str(e)}", exc_info=True)
        return {"result": "There was a problem searching listings. Let's continue the call."}

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

