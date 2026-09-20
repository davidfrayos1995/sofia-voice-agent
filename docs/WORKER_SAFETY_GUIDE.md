# Worker Automático: Guía de Protecciones de Gasto

Sofia incluye un **worker automático** que revisa leads con estatus "Pendiente de llamar" y les dispara llamadas outbound. Para proteger tu presupuesto (proyecto de práctica), el worker tiene **3 capas de seguridad**.

## 1️⃣ Scheduler Desactivado por Defecto

El scheduler (que hace correr el worker cada hora) **está DESACTIVADO por defecto**.

- ✅ No gasta dinero sin que lo pidas
- ✅ Tienes control total

Para activarlo:
```bash
# En Railway, agregar variable de entorno:
ENABLE_OUTBOUND_SCHEDULER=true
```

Sin esta variable, el scheduler nunca corre automáticamente. El endpoint manual siempre funciona.

---

## 2️⃣ Límite Máximo de Llamadas por Ejecución

Incluso si el scheduler está activo, puedes limitar cuántas llamadas se disparan en una sola ejecución.

```bash
# Default: 999 (prácticamente ilimitado)
# Para limitar a 3 llamadas por hora:
OUTBOUND_MAX_CALLS_PER_RUN=3

# Para limitar a 1 sola:
OUTBOUND_MAX_CALLS_PER_RUN=1
```

Si hay 10 leads pendientes y pones `MAX=3`, solo dispara 3 llamadas y los otros 7 quedan para la siguiente ejecución (1 hora después).

---

## 3️⃣ Modo Dry-Run (Simular sin Gastar)

Antes de activar llamadas reales, prueba la lógica en modo dry-run: **simula las llamadas, registra todo en logs, pero NO gasta dinero**.

```bash
# Activar dry-run:
OUTBOUND_DRY_RUN_MODE=true
```

Con esto:
- El worker consulta los leads pendientes ✅
- Marca cada uno como "En proceso" ✅
- Registra en logs a quién llamaría ✅
- **NO dispara la llamada real** ❌ (no cuesta dinero)

En los logs verás líneas como:
```
🎬 [DRY-RUN] Llamaría a Juan García (+525551234567) - SIN DISPARAR REAL
```

---

## 📋 Casos de Uso Recomendados

### Caso 1: Testing Local (Antes de Demo)
```bash
ENABLE_OUTBOUND_SCHEDULER=false
OUTBOUND_DRY_RUN_MODE=true
OUTBOUND_MAX_CALLS_PER_RUN=3
```

Dispara manualmente el worker en tu terminal:
```bash
curl -X POST http://localhost:8000/api/worker/trigger-outbound
```

Verás en los logs exactamente a quién llamaría, sin gastar un centavo.

### Caso 2: Demo en Video (Pocas Llamadas Reales)
```bash
ENABLE_OUTBOUND_SCHEDULER=false
OUTBOUND_DRY_RUN_MODE=false
OUTBOUND_MAX_CALLS_PER_RUN=2  # solo 2 llamadas reales por demo
```

Dispara manualmente desde Railway:
```bash
curl -X POST https://web-production-f9e22.up.railway.app/api/worker/trigger-outbound
```

Solo dispara 2 llamadas reales, no más.

### Caso 3: Producción Segura (Cuando estés listo)
```bash
ENABLE_OUTBOUND_SCHEDULER=true
OUTBOUND_DRY_RUN_MODE=false
OUTBOUND_MAX_CALLS_PER_RUN=5  # máximo 5 leads por hora
OUTBOUND_CALL_DELAY_SECONDS=30  # espera 30s entre llamadas
```

El worker corre cada hora, máximo 5 llamadas, sin dry-run.

---

## 🔍 Revisar Logs del Worker

En Railway:

1. Ve a **Logs**
2. Filtra por las líneas que contienen:
   - `🔄 WORKER INICIADO` — inicio del worker
   - `🎬 [DRY-RUN]` — simulaciones (sin gastar)
   - `📞 Llamando a` — llamadas reales siendo disparadas
   - `✅ Llamada disparada exitosamente` — llamada completada
   - `❌ Falló la llamada` — llamada que no se pudo hacer
   - `↩️ Lead revertido` — lead que vuelve a "Pendiente" para reintentar

---

## 💡 Comando para Disparar Manualmente (Demo)

### Local (durante development):
```bash
curl -X POST http://localhost:8000/api/worker/trigger-outbound
```

### En Production (Railway):
```bash
curl -X POST https://web-production-f9e22.up.railway.app/api/worker/trigger-outbound
```

Respuesta:
```json
{
  "success": true,
  "processed": 3,
  "calls_triggered": 2,
  "calls_failed": 0,
  "skipped_no_phone": 1
}
```

---

## ⚠️ Resumen: Protecciones Activas

| Protección | Default | Efecto |
|---|---|---|
| **Scheduler automático** | ❌ OFF | No gasta sin tu permiso |
| **Límite de llamadas/ejecución** | 999 (ilimitado) | Configurable, para limitar riesgo |
| **Dry-run mode** | ❌ OFF | Prueba sin gastar |

**Combinación recomendada para tu demo:**
```
ENABLE_OUTBOUND_SCHEDULER=false
OUTBOUND_DRY_RUN_MODE=true
OUTBOUND_MAX_CALLS_PER_RUN=3
```

Luego dispara manualmente desde la terminal cuando quieras demostrar.
