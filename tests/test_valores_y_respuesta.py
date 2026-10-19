import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NOTION_API_KEY", "prueba")
os.environ.setdefault("NOTION_DATABASE_ID_PROPIEDADES", "db-prop")
os.environ.setdefault("NOTION_DATABASE_ID_LEADS", "db-leads")
os.environ.setdefault("ANTHROPIC_API_KEY", "prueba")

from fastapi.testclient import TestClient
import main
from services import notion_service as ns
from services.notion_service import _zona_buscable


class ZonasGenericasTest(unittest.TestCase):
    def test_zonas_genericas_en_ingles(self):
        for zona in ["anywhere", "Anywhere.", "Any Area!", "any neighborhood", "any zone", "any location",
                     "no preference", "doesn't matter", "does not matter", "all", "All Areas", "anything", "whatever"]:
            with self.subTest(zona=zona):
                self.assertFalse(_zona_buscable(zona))

    def test_zona_real_sigue_buscable(self):
        self.assertTrue(_zona_buscable("Polanco"))
        self.assertTrue(_zona_buscable("Miami"))


class NormalizacionTest(unittest.TestCase):
    def test_tipo(self):
        for valor, esperado in [("renta", "Renta"), ("Rent", "Renta"), ("rental", "Renta"), ("RENTING", "Renta"),
                                ("compra", "Compra"), ("buy", "Compra"), ("Buying", "Compra"), ("purchase", "Compra")]:
            with self.subTest(valor=valor):
                self.assertEqual(ns.normalizar_tipo(valor), esperado)

    def test_temperatura(self):
        for valor, esperado in [("hot", "hot"), ("WARM", "warm"), (" Cold ", "cold")]:
            with self.subTest(valor=valor):
                self.assertEqual(ns.normalizar_temperatura(valor), esperado)

    def test_idioma(self):
        for valor, esperado in [("English", "English"), ("inglés", "English"), ("ingles", "English"),
                                ("Spanish", "Spanish"), ("español", "Spanish"), ("espanol", "Spanish")]:
            with self.subTest(valor=valor):
                self.assertEqual(ns.normalizar_idioma(valor), esperado)

    def test_no_reconocido_o_vacio_devuelve_none_y_avisa(self):
        with self.assertLogs("services.notion_service", level="WARNING") as capturado:
            self.assertIsNone(ns.normalizar_tipo("apartamento"))
            self.assertIsNone(ns.normalizar_temperatura("boiling"))
            self.assertIsNone(ns.normalizar_idioma("french"))
        self.assertEqual(len(capturado.output), 3)
        self.assertIsNone(ns.normalizar_tipo(""))
        self.assertIsNone(ns.normalizar_temperatura(None))


class RespuestaBusquedaTest(unittest.TestCase):
    def setUp(self):
        self.cliente = TestClient(main.app)

    ZONAS = ["Brickell", "Kissimmee"]

    def llamar(self, resultado, args=None):
        args = args if args is not None else {"ubicacion_filter": "x", "precio_max": 3000}
        with patch("main.search_properties", return_value=resultado), patch("main.zonas_con_propiedades", return_value=self.ZONAS):
            return self.cliente.post("/api/functions/search_properties", json={"args": args}).json()["result"]

    def test_sin_resultados(self):
        self.assertEqual(self.llamar({"success": True, "propiedades": []}),
                         "No listings found in 'x'. Areas with listings: Brickell, Kissimmee.")

    def test_sin_resultados_sin_zona_lista_areas(self):
        self.assertEqual(self.llamar({"success": True, "propiedades": []}, {"precio_max": 1000}),
                         "No listings match those criteria. Areas with listings: Brickell, Kissimmee.")

    def test_zona_generica_sin_resultados_lista_areas(self):
        self.assertEqual(self.llamar({"success": True, "propiedades": []}, {"ubicacion_filter": "anywhere", "precio_max": 1000}),
                         "No listings match those criteria. Areas with listings: Brickell, Kissimmee.")

    def test_sin_zona_con_resultados_agrega_areas_al_final(self):
        prop = {"nombre": "Casa Y", "ubicacion": "Kissimmee", "precio": 2900, "moneda": "USD", "recamaras": 3, "banos": 2, "tipo": None}
        self.assertEqual(self.llamar({"success": True, "propiedades": [prop]}, {"precio_max": 3000}),
                         "Found 1 listing: Casa Y in Kissimmee, $2,900 per month (USD), 3 bedrooms, 2 baths. Areas with listings: Brickell, Kissimmee.")

    def test_con_zona_y_resultados_no_agrega_areas(self):
        prop = {"nombre": "Casa Y", "ubicacion": "Kissimmee", "precio": 2900, "moneda": "USD", "recamaras": 3, "banos": 2, "tipo": None}
        self.assertNotIn("Areas with listings", self.llamar({"success": True, "propiedades": [prop]}, {"ubicacion_filter": "Kissimmee"}))

    def test_zonas_con_propiedades_cuenta_ordena_y_limita(self):
        from unittest.mock import MagicMock
        def fila(ubic):
            return {"properties": {"Ubicación": {"rich_text": [{"plain_text": ubic}]}}}
        filas = [fila("Brickell, Miami")] * 2 + [fila("Kissimmee, Orlando")] + [fila(f"Zona{i:02d}, Miami") for i in range(25)] + [fila("  , Miami")]
        respuesta = MagicMock(status_code=200)
        respuesta.json.return_value = {"results": filas, "has_more": False}
        with patch.object(ns.requests, "post", return_value=respuesta):
            zonas = ns.zonas_con_propiedades()
        self.assertEqual(zonas[0], "Brickell")
        self.assertEqual(len(zonas), 20)
        self.assertEqual(len(set(zonas)), 20)
        self.assertNotIn("", zonas)

    def test_un_resultado_en_ingles_con_moneda(self):
        propiedad = {"nombre": "Studio Miami Beach", "ubicacion": "Miami Beach", "precio": 2500, "moneda": "USD",
                     "recamaras": 0, "banos": 1, "tipo": "apartment"}
        texto = self.llamar({"success": True, "propiedades": [propiedad]})
        self.assertEqual(texto, "Found 1 listing: Studio Miami Beach (apartment) in Miami Beach, $2,500 per month (USD), studio, 1 bath.")

    def test_sin_tipo_no_muestra_parentesis(self):
        propiedad = {"nombre": "Casa X", "ubicacion": "Orlando", "precio": 2000, "moneda": "USD", "recamaras": 2, "banos": 2, "tipo": None}
        self.assertEqual(self.llamar({"success": True, "propiedades": [propiedad]}),
                         "Found 1 listing: Casa X in Orlando, $2,000 per month (USD), 2 bedrooms, 2 baths.")

    def test_varios_resultados_singular_plural_y_medio_bano(self):
        props = [
            {"nombre": "A", "ubicacion": "Orlando", "precio": 1800, "moneda": "USD", "recamaras": 1, "banos": 1},
            {"nombre": "B", "ubicacion": "Miami", "precio": 3200, "moneda": "USD", "recamaras": 3, "banos": 2.5},
        ]
        texto = self.llamar({"success": True, "propiedades": props})
        self.assertEqual(texto, "Found 2 listings: A in Orlando, $1,800 per month (USD), 1 bedroom, 1 bath; "
                                "B in Miami, $3,200 per month (USD), 3 bedrooms, 2.5 baths.")

    def test_muestra_las_mas_baratas_primero_y_avisa_el_total(self):
        props = [{"nombre": f"P{precio}", "ubicacion": "Orlando", "precio": precio, "moneda": "USD", "recamaras": 1, "banos": 1, "tipo": None}
                 for precio in [2000, 1400, 1950, 1700, 1800]]
        texto = self.llamar({"success": True, "propiedades": props})
        self.assertTrue(texto.startswith("Found 5 listings; showing 3: P1400 in Orlando"))
        self.assertIn("P1700", texto)
        self.assertNotIn("P2000", texto)
        self.assertLess(texto.index("P1400"), texto.index("P1700"))

    def test_sin_precio_va_al_final(self):
        props = [{"nombre": "Sin precio", "ubicacion": "X", "precio": None, "moneda": "USD", "recamaras": 0, "banos": 1, "tipo": None},
                 {"nombre": "Barata", "ubicacion": "X", "precio": 1000, "moneda": "USD", "recamaras": 0, "banos": 1, "tipo": None}]
        texto = self.llamar({"success": True, "propiedades": props})
        self.assertLess(texto.index("Barata"), texto.index("Sin precio"))

    def test_no_contiene_espanol(self):
        texto = self.llamar({"success": True, "propiedades": []}) + self.llamar({"success": False})
        for palabra in ["encontr", "propiedades", "mes", "recámara", "disponible"]:
            self.assertNotIn(palabra, texto.lower())


class LeadValoresTest(unittest.TestCase):
    def test_lead_escribe_idioma_y_tipo_normalizado(self):
        props = ns._lead_properties(None, None, None, None, {"tipo_operacion": "Renta", "idioma": "English"})
        self.assertEqual(props["Tipo"], {"select": {"name": "Renta"}})
        self.assertEqual(props["Idioma"], {"select": {"name": "English"}})

    def test_lead_sin_idioma_no_escribe_la_columna(self):
        self.assertNotIn("Idioma", ns._lead_properties(None, None, None, None, {}))


class EscriturasOpcionalesTest(unittest.TestCase):
    def test_reintenta_sin_columna_opcional_que_no_existe(self):
        from unittest.mock import MagicMock
        intentos = []
        def respuesta(codigo, cuerpo):
            m = MagicMock(status_code=codigo); m.json.return_value = cuerpo; m.text = str(cuerpo); return m
        def falso_post(url, headers=None, json=None):
            intentos.append(json)
            if url.endswith("/query"):
                return respuesta(200, {"results": []})
            if "Idioma" in json["properties"]:
                return respuesta(400, {"object": "error", "code": "validation_error",
                                       "message": "Could not find property with name or id: Idioma"})
            return respuesta(200, {"id": "pagina-nueva"})
        with patch.object(ns.requests, "post", side_effect=falso_post), \
             self.assertLogs("services.notion_service", level="WARNING") as capturado:
            resultado = ns.create_or_update_lead("+15550000201", name="Ana", resumen_llamada="Hola",
                                                 datos={"idioma": "English", "zona": "Miami"})
        self.assertTrue(resultado["success"])
        self.assertEqual(resultado["action"], "created")
        self.assertNotIn("Idioma", intentos[-1]["properties"])
        self.assertIn("Zona", intentos[-1]["properties"])
        self.assertTrue(any("Idioma" in linea for linea in capturado.output))

    def test_no_reintenta_por_errores_que_no_son_de_columna(self):
        from unittest.mock import MagicMock
        def falso_post(url, headers=None, json=None):
            m = MagicMock()
            if url.endswith("/query"):
                m.status_code = 200; m.json.return_value = {"results": []}; return m
            m.status_code = 400; m.json.return_value = {"message": "body failed validation"}; m.text = "x"; return m
        with patch.object(ns.requests, "post", side_effect=falso_post):
            resultado = ns.create_or_update_lead("+15550000202", name="Ana", datos={"idioma": "English"})
        self.assertFalse(resultado["success"])


if __name__ == "__main__":
    unittest.main()
