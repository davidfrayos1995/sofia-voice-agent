# Despliegue en Railway

Railway es mucho más sencillo que Modal — no requiere aprobación manual y se deploya automáticamente desde GitHub.

## Pasos para desplegar en Railway

### 1. Crear cuenta en Railway
1. Andá a https://railway.app/
2. Registrate con GitHub, GitLab, Bitbucket o email
3. No requiere tarjeta de crédito para empezar (crédito gratis inicial)

### 2. Conectar tu repositorio
1. En Railway, clic en **+ New Project**
2. Seleccioná **Deploy from GitHub**
3. Autorizá Railway para acceder a tu GitHub
4. Seleccioná este repositorio (`sofia-voice-agent` o como lo llames)
5. Railway automáticamente detectará el `Dockerfile` o `Procfile`

### 3. Configurar variables de entorno
1. Una vez que el proyecto esté en Railway, andá a **Settings → Variables**
2. Agregá todas las variables del `.env`:
   - ANTHROPIC_API_KEY
   - NOTION_API_KEY
   - NOTION_DATABASE_ID_CONTACTS
   - NOTION_DATABASE_ID_CALLS
   - CALCOM_API_KEY
   - RETELL_API_KEY
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_PHONE_NUMBER

3. Railway automáticamente asignará un dominio (ej: `sofia-voice-agent-production.railway.app`)
   - Copiá esta URL y pegala en RAILWAY_URL

### 4. Primera vez que se deploya
- Railway automáticamente instala dependencias (`pip install -r requirements.txt`)
- Ejecuta el comando del `Procfile`
- El servicio está listo en 2-5 minutos

### 5. Configurar webhooks en Retell AI y Twilio
Una vez que tengas el dominio de Railway:

**Para Retell AI:**
- Andá al dashboard de Retell AI
- En tu agente, configurá **Webhook URL**: `https://your-railway-url.railway.app/webhooks/retell`

**Para Twilio (SMS):**
- En Twilio Console, andá a **Phone Numbers → Manage Numbers → Your Number**
- Bajo **Messaging**, sección **Webhook**, configurá:
  - URL: `https://your-railway-url.railway.app/webhooks/twilio/sms`
  - Method: HTTP POST

## Ventajas de Railway vs Modal

| Característica | Railway | Modal |
|---|---|---|
| Aprobación manual | ❌ No | ✅ Sí (rechazó tu cuenta) |
| Setup | ⚡ 5 minutos | Esperar revisión |
| Tarjeta de crédito | Opcional al inicio | Requerida |
| Auto-scaling | Sí | Sí |
| Precio inicial | $5-10/mes | $0 con crédito |
| GitHub deploy | ✅ Automático | ✅ Automático |

## Costos estimados en Railway

- **Starter plan (free tier)**: $5/mes en crédito (suficiente para desarrollo)
- **Por uso**: ~$0.00011 por CPU-segundo
- Para nuestro MVP con pocas llamadas: ~$5-15/mes

## Debugging en Railway

Para ver logs:
1. En el dashboard de Railway, seleccioná tu proyecto
2. Clic en **Logs**
3. Ves los logs en tiempo real

```
# Ver logs específicos:
railway logs --service main
```

## Next steps

Una vez deployado en Railway:
1. Crear las bases de datos en Notion (Contactos, Llamadas, Interacciones)
2. Implementar los servicios en `src/services/` para cada integración
3. Probar webhooks de Retell AI (simular una llamada)
4. Implementar resúmenes con Anthropic
