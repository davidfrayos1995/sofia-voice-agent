import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("NOTION_API_KEY", "prueba")
os.environ.setdefault("NOTION_DATABASE_ID_PROPIEDADES", "db-prop")

from services import notion_service as ns


def pagina(nombre, ubicacion, precio, recamaras):
    return {"id": nombre, "properties": {
        "Name": {"title": [{"text": {"content": nombre}}]},
        "Ubicación": {"rich_text": [{"text": {"content": ubicacion}}]},
        "Precio Mensual": {"number": precio},
        "Recámaras": {"number": recamaras},
        "Baños": {"number": 1},
        "m²": {"number": 40},
        "Disponible": {"select": {"name": "Sí"}},
        "Descripción": {"rich_text": [{"text": {"content": ""}}]},
    }}


PROPIEDADES = [
    pagina("Estudio Coyoacán Centro", "Coyoacán", 9000, 1),
    pagina("Loft Polanco - Penthouse", "Polanco, Miguel Hidalgo", 45000, 2),
    pagina("Depto Roma Norte", "Roma Norte, Cuauhtémoc", 10000, 2),
]


def _notion_falso(url, headers=None, json=None):
    precio_max = None
    filtro = json.get("filter", {})
    for condicion in filtro.get("and", [filtro] if filtro else []):
        if condicion.get("property") == "Precio Mensual":
            precio_max = condicion["number"].get("less_than_or_equal_to", precio_max)
    resultados = [p for p in PROPIEDADES if precio_max is None or p["properties"]["Precio Mensual"]["number"] <= precio_max]
    respuesta = MagicMock(status_code=200)
    respuesta.json.return_value = {"results": resultados}
    return respuesta


class BusquedaZonaTest(unittest.TestCase):
    def nombres(self, zona):
        with patch.object(ns.requests, "post", side_effect=_notion_falso):
            resultado = ns.search_properties(ubicacion_filter=zona, precio_max=10000)
        return [p["nombre"] for p in resultado["propiedades"]]

    def test_zonas_genericas_no_filtran(self):
        todas = ["Estudio Coyoacán Centro", "Depto Roma Norte"]
        for zona in ["cualquiera", "cualquiera.", "Cualquier Zona!", "¡cualquiera!", "donde sea", "todas", "", None, "no importa", "Ninguna zona"]:
            with self.subTest(zona=zona):
                self.assertEqual(self.nombres(zona), todas)

    def test_coincidencia_sin_acentos_mayusculas_ni_puntuacion(self):
        for zona in ["Coyoacán", "coyoacan", "COYOACÁN", "Coyoacán, centro!", "coyoacán centro"]:
            with self.subTest(zona=zona):
                self.assertEqual(self.nombres(zona), ["Estudio Coyoacán Centro"])

    def test_zona_sin_propiedades_devuelve_vacio(self):
        self.assertEqual(self.nombres("Iztapalapa"), [])


if __name__ == "__main__":
    unittest.main()
