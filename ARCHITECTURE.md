# Arquitectura: Sofia (Agente de Voz para Inmobiliaria)

## Diagrama de flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CANALES EXTERNOS                            │
└─────────────────────────────────────────────────────────────────────┘

    Llamadas      SMS        Llamadas
    Entrantes     Entrantes  Salientes
       │             │          │
       ▼             ▼          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    RETELL AI (Agente de Voz)                         │
│  - Procesa voz natural                                               │
│  - Maneja conversaciones                                             │
│  - Envía webhooks cuando llama termina                               │
└──────────────────────────────────────────────────────────────────────┘
       │
       │ Webhook: call.ended
       │ + transcript + call_id
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   RAILWAY (Backend Sofia)                            │
│                      uvicorn + FastAPI                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  POST /webhooks/retell                                      │   │
│  │  - Recibe fin de llamada                                    │   │
│  │  - Extrae transcript                                        │   │
│  │  - Genera resumen con Anthropic                             │   │
│  │  - Guarda en Notion                                         │   │
│  │  - Crea evento en Cal.com si es necesario                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  POST /webhooks/twilio/sms                                  │   │
│  │  - Recibe SMS de clientes                                   │   │
│  │  - Pasa a Retell AI para procesamiento                      │   │
│  │  - O responde directamente                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  POST /api/call/initiate                                    │   │
│  │  - Inicia llamada saliente desde Notion                     │   │
│  │  - Integra con Retell AI                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  POST /api/schedule/meeting                                 │   │
│  │  - Agenda cita con Cal.com después de una llamada           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
    ┌──────┐    ┌─────────┐    ┌──────────┐   ┌──────────┐
    │Notion│    │Anthropic│    │Cal.com   │   │ Twilio   │
    │(CRM) │    │(Resumen)│    │(Citas)   │   │(SMS)     │
    └──────┘    └─────────┘    └──────────┘   └──────────┘

```

## Flujos principales

### Flujo 1: Llamada entrante
```
1. Cliente llama al número de Twilio
2. Twilio redirige a Retell AI
3. Retell AI: IVR + conversación automática
4. Retell AI: recopila info (nombre, propiedad interesada, etc.)
5. Fin de llamada → Retell AI envía webhook a Railway
6. Railway recibe /webhooks/retell:
   - Extrae transcript
   - Llama Anthropic API para generar resumen
   - Crea "Lead" en Notion con resumen
   - Clasifica propiedad si es necesario
7. Notion: base de datos "Contactos" y "Llamadas" se actualizan
```

### Flujo 2: SMS de cliente
```
1. Cliente envía SMS al número Twilio
2. Twilio envía webhook a Railway (/webhooks/twilio/sms)
3. Railway procesa el SMS:
   - Identifica al cliente en Notion
   - Pasa el mensaje a Retell AI (si es necesario)
   - O responde con info de propiedades
4. Respuesta se envía vía Twilio SMS
```

### Flujo 3: Llamada saliente (seguimiento)
```
1. Operario en Notion marca contacto para "seguimiento"
2. Trigger en Railway detecta cambio (via polling o webhook)
3. Railway llama POST /api/call/initiate
4. Retell AI inicia llamada saliente automáticamente
5. Agente: "Hola, soy Sofia, te llamaba para..."
6. Misma lógica que Flujo 1 al terminar
```

### Flujo 4: Agendar cita
```
1. Durante/después de llamada: cliente acepta ver propiedad
2. Retell AI detecta en conversación
3. Railway procesa confirmación
4. Llama Cal.com API para crear evento
5. Notifica a cliente vía SMS (Twilio)
6. Guarda cita en Notion bajo contacto
```

## Diferencia Modal vs Railway

| Aspecto | Modal | Railway |
|---------|-------|---------|
| **Deploy** | Requiere aprobación manual | Automático desde GitHub |
| **Trigger** | `@app.function` (serverless) | `FastAPI` con uvicorn (always-on) |
| **Variables de entorno** | CLI + modal.toml | Dashboard Railway |
| **Scaling** | Automático por función | Réplicas configurables |
| **Logs** | `modal logs` | Dashboard web |
| **Costos iniciales** | $0 (rechazó tu cuenta) | $5/mes free tier |

**Importante**: Con Railway usás un servidor siempre activo (no serverless). Esto es mejor para:
- ✅ Webhooks (necesitan servidor escuchando)
- ✅ Polling a Notion cada X minutos
- ✅ State compartido entre requests

## Variables de entorno requeridas en Railway

```
PORT=8000
ANTHROPIC_API_KEY=sk-ant-...
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID_CONTACTS=...
NOTION_DATABASE_ID_CALLS=...
CALCOM_API_KEY=cal_live_...
RETELL_API_KEY=key_...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
RAILWAY_URL=https://your-project.railway.app
```

## Next steps

1. **Inicializar git** e hacer push a GitHub
   ```bash
   cd "/Users/davidfray/Documents/sofia test"
   git init
   git add .
   git commit -m "Initial commit: Sofia voice agent backend with Railway"
   git remote add origin https://github.com/YOUR_USERNAME/sofia-voice-agent
   git push -u origin main
   ```

2. **Crear cuenta en Railway** y conectar repo

3. **Crear bases de datos en Notion**
   - Tabla "Contactos" (nombre, teléfono, propiedades interesadas, etc.)
   - Tabla "Llamadas" (fecha, duración, transcript, resumen, outcome)
   - Tabla "Propiedades" (dirección, precio, descripción, etc.)

4. **Implementar servicios** en `src/services/`:
   - `notion_service.py` - crear/actualizar contactos y registros
   - `anthropic_service.py` - generar resúmenes
   - `twilio_service.py` - enviar SMS
   - `calcom_service.py` - agendar reuniones
   - `retell_service.py` - iniciar llamadas salientes

5. **Probar webhooks** con simuladores (Postman, curl, etc.)

