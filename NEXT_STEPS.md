# ✅ Próximos pasos — Sofia Voice Agent

Migraste de Modal → Railway. Acá está qué hacer ahora.

## Fase 1: Desplegar en Railway (esta semana)

- [ ] **Inicializar Git**
  ```bash
  cd "/Users/davidfray/Documents/sofia test"
  git init
  git add .
  git commit -m "Initial commit: Sofia voice agent with Railway"
  git remote add origin https://github.com/YOUR_USERNAME/sofia-voice-agent
  git push -u origin main
  ```

- [ ] **Crear cuenta en Railway**
  - Andá a https://railway.app/
  - Registrate con GitHub
  - Crea nuevo proyecto

- [ ] **Conectar repositorio a Railway**
  - New Project → Deploy from GitHub
  - Seleccioná tu repositorio
  - Railway automáticamente detectará Dockerfile/Procfile

- [ ] **Configurar variables de entorno en Railway**
  - En el dashboard, andá a **Settings → Variables**
  - Copia todas las variables del `.env` local (excepto PORT)
  - Verifica que Railway asigne un dominio (ej: sofia-voice-agent-prod.railway.app)

- [ ] **Probar que el servidor está vivo**
  ```bash
  curl https://your-railway-url.railway.app/health
  # Debe devolver: {"status":"ok","service":"sofia-voice-agent"}
  ```

## Fase 2: Crear esquema en Notion (semana próxima)

- [ ] **Base de datos "Contactos"** con campos:
  - Nombre (text)
  - Teléfono (phone)
  - Email (email)
  - Propiedades interesadas (multiselect)
  - Estado (single select): "Lead", "Interesado", "Visitó propiedad", "Cerrado"
  - Notas (long text)
  - Fecha de primer contacto (date)
  - Última interacción (date)

- [ ] **Base de datos "Llamadas"** con campos:
  - Contacto (relation → Contactos)
  - Fecha (date)
  - Duración (number)
  - Transcript (long text)
  - Resumen (long text) ← generado por Anthropic
  - Call ID de Retell (text)
  - Tipo (select): "Entrante", "Saliente"
  - Propiedad mencionada (text)

- [ ] **Base de datos "Propiedades"** (opcional pero útil):
  - Dirección (text)
  - Precio (number)
  - Descripción (long text)
  - Tipo (select): "Casa", "Departamento", "Terreno"
  - Disponible (checkbox)

- [ ] **Base de datos "Citas"** con campos:
  - Contacto (relation → Contactos)
  - Fecha/hora (date)
  - Propiedad (relation → Propiedades)
  - Agente (text)
  - Notas (long text)

- [ ] **Conectar integración Sofia a cada base**
  - Para cada tabla: menú `···` → **Connections** → seleccioná **Sofia**

- [ ] **Copiar IDs de bases de datos**
  - Para cada tabla, sacá el ID de la URL de Notion
  - Agregalos al `.env` (NOTION_DATABASE_ID_CONTACTS, NOTION_DATABASE_ID_CALLS, etc.)
  - Actualiza en Railway

## Fase 3: Implementar servicios de integración (semanas 2-3)

### 3a. Notion Service (`src/services/notion_service.py`)
- [ ] Crear función para agregar contacto
- [ ] Crear función para crear registro de llamada
- [ ] Crear función para actualizar estado de contacto
- [ ] Crear función para listar contactos y filtrar

### 3b. Anthropic Service (`src/services/anthropic_service.py`)
- [ ] Generar resúmen de transcript
- [ ] Extraer sentimiento (positivo/negativo/neutral)
- [ ] Clasificar intent de contacto

### 3c. Retell AI Service (`src/services/retell_service.py`)
- [ ] Iniciar llamada saliente
- [ ] Obtener detalles de llamada completada
- [ ] Descargar transcript

### 3d. Twilio Service (`src/services/twilio_service.py`)
- [ ] Enviar SMS de respuesta automática
- [ ] Enviar SMS de confirmación de cita
- [ ] Enviar SMS recordatorio de cita

### 3e. Cal.com Service (`src/services/calcom_service.py`)
- [ ] Crear evento de cita
- [ ] Obtener disponibilidad

## Fase 4: Conectar webhooks (semana 3-4)

- [ ] **Configurar webhook en Retell AI**
  - Dashboard Retell → Agent → Webhooks
  - URL: `https://your-railway-url/webhooks/retell`
  - Eventos: call.started, call.ended

- [ ] **Configurar webhook en Twilio**
  - Console Twilio → Phone Numbers → Your Number
  - Messaging Webhook: `https://your-railway-url/webhooks/twilio/sms`

- [ ] **Probar flujo completo**
  - Llamada de prueba → Retell → Railway → Notion
  - Verifica que el registro se crea en Notion
  - Verifica que se genera resumen con Anthropic

## Fase 5: Testing y refinamientos (semana 4+)

- [ ] Probar casos edge (números inválidos, timeouts, etc.)
- [ ] Agregar logging y monitoring
- [ ] Optimizar prompts de Anthropic
- [ ] Ajustar flujo conversacional en Retell AI

## Checklist rápido de ahora

```
✅ Migración Modal → Railway completada
✅ Backend FastAPI levantado
✅ Variables de entorno configuradas
⏳ Git inicializado y pusheado
⏳ Railway desplegado
⏳ Notion configurado
⏳ Webhooks conectados
⏳ End-to-end funcionando
```

---

**Tip**: Si en cualquier momento tenés error, revisá:
1. Logs de Railway: `railway logs`
2. Que las variables de entorno estén bien en Railway (copypaste exacto)
3. Que los webhooks de Retell/Twilio apunten a la URL correcta de Railway
4. Usa `curl -X POST -H "Content-Type: application/json" -d '{"event":"test"}' https://your-url/webhooks/retell` para probar

