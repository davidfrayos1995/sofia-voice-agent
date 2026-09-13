# Sofia — Agente de Voz IA para Inmobiliaria

## Descripción del proyecto

Sistema de inteligencia artificial basado en agentes de voz para una inmobiliaria. El agente debe poder:

- Recibir llamadas entrantes
- Realizar llamadas salientes
- Recibir y responder mensajes

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Agente de voz IA | **Retell AI** |
| Hosting de automatizaciones | **Railway** |
| CRM | **Notion** |
| Telefonía (número y mensajería) | **Twilio** |
| Agendamiento de citas | **Cal.com** |
| Resúmenes post-llamada | **Anthropic** |

## Estado actual

Estructura base creada:
- ✅ Backend FastAPI configurado para Railway
- ✅ Endpoints principales creados (webhooks de Retell/Twilio, APIs internas)
- ✅ Variables de entorno y configuración (.env, Procfile, Dockerfile)
- ✅ Documentación de arquitectura y setup
- ⏳ Implementar servicios de integración (Notion, Anthropic, Cal.com, Twilio)
- ⏳ Crear esquema de bases de datos en Notion
- ⏳ Probar webhooks end-to-end

## Cambio: Modal → Railway

**Razón**: Cuenta de Modal rechazada (requería aprobación manual). Railway no requiere aprobación y deploya automáticamente.

**Ventajas de Railway**:
- Deploy automático desde GitHub (5 minutos)
- No requiere tarjeta de crédito al inicio
- $5/mes en crédito gratis (suficiente para MVP)
- Perfecto para webhooks (servidor siempre activo vs serverless)

## Notas para colaboración

- El usuario habla español — responder en español por defecto.
- Priorizar simplicidad al inicio; no adelantar arquitectura compleja hasta que se pida.
- Para desplegar en Railway, ver [RAILWAY_SETUP.md](RAILWAY_SETUP.md)
- Para entender flujos de datos, ver [ARCHITECTURE.md](ARCHITECTURE.md)
