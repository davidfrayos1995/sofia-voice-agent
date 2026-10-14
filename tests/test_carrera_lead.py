import contextlib
import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NOTION_API_KEY", "prueba")
os.environ.setdefault("NOTION_DATABASE_ID_LEADS", "db-leads")
os.environ.setdefault("NOTION_DATABASE_ID_LLAMADAS", "db-llamadas")
os.environ.setdefault("ANTHROPIC_API_KEY", "prueba")

import main
from services import notion_service as ns

TELEFONO = "+15550000009"


class NotionFalso:
    def __init__(self):
        self.paginas = []
        self.creaciones = 0
        self.mu = threading.Lock()

    def _resp(self, body):
        m = MagicMock(status_code=200)
        m.json.return_value = body
        m.text = json.dumps(body)
        return m

    def post(self, url, headers=None, json=None):
        if url.endswith("/query") and "phone_number" not in json["filter"]:
            return self._resp({"results": []})
        if url.endswith("/query"):
            tel = json["filter"]["phone_number"]["equals"]
            hits = [p for p in self.paginas if p["_tel"] == tel]
            time.sleep(0.2)
            return self._resp({"results": hits})
        with self.mu:
            self.creaciones += 1
            pagina = {"id": f"page-{self.creaciones}", "_tel": json["properties"]["Teléfono"]["phone_number"],
                      "properties": {"Resumen Llamada": {"rich_text": []}}}
            self.paginas.append(pagina)
        return self._resp({"id": pagina["id"]})

    def patch(self, url, headers=None, json=None):
        return self._resp({"id": url.rsplit("/", 1)[-1]})


def correr(con_lock):
    notion = NotionFalso()
    lock_real = main.lead_lock
    if not con_lock:
        main.lead_lock = contextlib.nullcontext()
    try:
        barrera = threading.Barrier(2)
        ended = {"call_id": "carrera-ended", "direction": "inbound", "from_number": TELEFONO, "transcript": "x", "duration_ms": 60000}
        analyzed = {"call_id": "carrera-analyzed", "direction": "inbound", "from_number": TELEFONO,
                    "call_analysis": {"call_summary": "Resumen", "custom_analysis_data": {"nombre": "Prueba"}}}
        with patch.object(ns.requests, "post", side_effect=notion.post), patch.object(ns.requests, "patch", side_effect=notion.patch), \
             patch("main.generate_call_summary", return_value="Resumen de prueba"), \
             patch("main.extract_call_metadata", return_value={"ok": True, "nombre": "Prueba", "interes": "warm"}), \
             patch("main.create_call_record", return_value={"success": True}), \
             patch("main.call_record_exists", return_value=False):
            hilos = [threading.Thread(target=lambda: (barrera.wait(), main.procesar_call_ended(ended))),
                     threading.Thread(target=lambda: (barrera.wait(), main.procesar_call_analyzed(analyzed)))]
            for h in hilos:
                h.start()
            for h in hilos:
                h.join()
    finally:
        main.lead_lock = lock_real
    return notion


class CarreraLeadTest(unittest.TestCase):
    def test_con_lock_una_sola_fila(self):
        self.assertEqual(correr(con_lock=True).creaciones, 1)

    def test_control_sin_lock_muestra_la_carrera(self):
        self.assertEqual(correr(con_lock=False).creaciones, 2)


if __name__ == "__main__":
    unittest.main()
