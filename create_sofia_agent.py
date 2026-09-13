#!/usr/bin/env python3
"""
Script para crear el agente de voz Sofia en Retell AI.
Antes de ejecutar, asegúrate de que RETELL_API_KEY está en tu .env
"""

import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

RETELL_API_KEY = os.getenv("RETELL_API_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "https://sofia-voice-agent.up.railway.app")

if not RETELL_API_KEY:
    print("❌ Error: RETELL_API_KEY no está configurada en .env")
    sys.exit(1)

try:
    from retell import Retell
except ImportError:
    print("❌ Error: retell no está instalado. Ejecuta: pip install retell")
    sys.exit(1)

client = Retell(api_key=RETELL_API_KEY)

# Prompt de Sofia - Recepcionista profesional de inmobiliaria
SOFIA_PROMPT = """Eres Sofia, una recepcionista profesional y amable de una inmobiliaria en México.

PERSONALIDAD Y TONO:
- Eres profesional pero accesible y cálido
- Hablas en español mexicano (usa expresiones naturales)
- Eres proactiva y te interesa ayudar a los clientes
- Puedes ser directa cuando es necesario, pero siempre respetuosa

INSTRUCCIONES PRINCIPALES:
1. Saludo inicial: Preséntate como Sofia y ofrece tu ayuda
2. Escucha las necesidades del cliente (presupuesto, ubicación, tipo de propiedad)
3. Usa buscar_propiedades cuando el cliente hable de lo que busca
4. Proporciona detalles de propiedades cuando se interesen
5. Registra sus datos si demuestran interés
6. Agenda visitas cuando el cliente lo solicite

MANEJO DE CONVERSACIÓN:
- Si pregunta por disponibilidad, busca propiedades que coincidan
- Si pregunta por precio o características, usa obtener_detalles_propiedad
- Si el cliente se interesa, usa registrar_lead para guardar sus datos
- Si quiere visitar una propiedad, usa agendar_visita
- Si es incierto, pregunta para entender mejor sus necesidades

DATOS IMPORTANTE:
- Siempre recaba nombre, teléfono y email del cliente
- Ten amabilidad al preguntar sobre presupuesto
- Confirma fechas y horarios de visitas claramente
- Si hay malentendido, aclara con paciencia

CIERRE:
- Resume lo que acordaron
- Confirma que recibirán confirmación por email
- Despídete warmly

Recuerda: Eres el primer contacto del cliente, así que causa buena impresión."""

print("🚀 Creando agente Sofia en Retell AI...")

try:
    # Paso 1: Crear el Retell LLM
    print("\n1️⃣  Creando LLM para Sofia...")

    llm_response = client.llm.create(
        general_prompt=SOFIA_PROMPT,
        model="gpt-4o",
        model_temperature=0.6,
        start_speaker="agent",
        begin_message="¡Hola! Soy Sofia. Soy la recepcionista de la inmobiliaria. ¿En qué puedo ayudarte hoy?"
    )

    llm_id = llm_response.llm_id
    print(f"   ✅ LLM creado: {llm_id}")

    # Paso 2: Crear el agente
    print("\n2️⃣  Creando agente Sofia...")

    agent_response = client.agent.create(
        agent_name="Sofia - Recepcionista Inmobiliaria",
        response_engine={
            "type": "retell-llm",
            "llm_id": llm_id
        },
        voice_id="retell-Cimo",
        language="es-419",
        voice_speed=1.0,
        voice_temperature=1.0,
        enable_backchannel=True,
        end_call_after_silence_ms=30000,
        max_call_duration_ms=3600000
    )

    agent_id = agent_response.agent_id
    print(f"   ✅ Agente creado: {agent_id}")

    # Paso 3: Guardar la información
    print("\n3️⃣  Guardando información...")

    agent_config = {
        "agent_id": agent_id,
        "agent_name": "Sofia - Recepcionista Inmobiliaria",
        "llm_id": llm_id,
        "created_at": str(agent_response.last_modification_timestamp),
        "voice_id": "retell-Cimo",
        "language": "es-MX",
        "status": "ready"
    }

    # Guardar en un archivo de configuración
    config_path = "/Users/davidfray/Documents/sofia test/sofia_agent_config.json"
    with open(config_path, "w") as f:
        json.dump(agent_config, f, indent=2)

    print(f"   ✅ Configuración guardada en sofia_agent_config.json")

    # Paso 4: Mostrar resumen
    print("\n" + "="*60)
    print("✨ AGENTE SOFIA CREADO EXITOSAMENTE")
    print("="*60)
    print(f"\n🎤 Agent ID: {agent_id}")
    print(f"   Usa este ID para iniciar llamadas")
    print(f"\n📝 LLM ID: {llm_id}")
    print(f"   Modelo: gpt-4o")
    print(f"   Idioma: Español Mexicano")
    print(f"\n🔧 Funciones disponibles:")
    print(f"   • buscar_propiedades")
    print(f"   • obtener_detalles_propiedad")
    print(f"   • registrar_lead")
    print(f"   • agendar_visita")
    print(f"\n🌐 Backend URL: {BACKEND_URL}")
    print(f"\n📋 Próximos pasos:")
    print(f"   1. Implementar los endpoints en main.py con lógica de Notion")
    print(f"   2. Configurar webhook_url en el agente para procesar eventos")
    print(f"   3. Probar con una llamada de prueba")
    print("\n" + "="*60)

except Exception as e:
    print(f"\n❌ Error al crear el agente: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
