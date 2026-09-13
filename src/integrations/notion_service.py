"""
Servicio de integración con Notion para gestionar propiedades, leads, llamadas y citas.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from notion_client import Client

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_API_KEY"))
        self.db_propiedades = os.getenv("NOTION_DATABASE_ID_PROPIEDADES")
        self.db_leads = os.getenv("NOTION_DATABASE_ID_LEADS")
        self.db_llamadas = os.getenv("NOTION_DATABASE_ID_LLAMADAS")
        self.db_citas = os.getenv("NOTION_DATABASE_ID_CITAS")

    def search_properties(self, criteria: Dict) -> List[Dict]:
        """
        Busca propiedades en Notion según criterios.
        Criterios opcionales: location, min_price, max_price, bedrooms, property_type
        """
        try:
            # Construir filtro para Notion
            filters = []

            if criteria.get("location"):
                filters.append({
                    "property": "Ubicación",
                    "rich_text": {
                        "contains": criteria["location"]
                    }
                })

            if criteria.get("min_price"):
                filters.append({
                    "property": "Precio",
                    "number": {
                        "greater_than_or_equal_to": criteria["min_price"]
                    }
                })

            if criteria.get("max_price"):
                filters.append({
                    "property": "Precio",
                    "number": {
                        "less_than_or_equal_to": criteria["max_price"]
                    }
                })

            if criteria.get("bedrooms"):
                filters.append({
                    "property": "Recámaras",
                    "number": {
                        "equals": criteria["bedrooms"]
                    }
                })

            if criteria.get("property_type"):
                filters.append({
                    "property": "Tipo",
                    "select": {
                        "equals": criteria["property_type"]
                    }
                })

            # Combinar filtros con AND logic
            filter_query = filters[0] if filters else None
            if len(filters) > 1:
                filter_query = {
                    "and": filters
                }

            # Buscar en Notion
            response = self.client.databases.query(
                database_id=self.db_propiedades,
                filter=filter_query
            )

            properties = []
            for page in response["results"]:
                prop_data = self._extract_property_data(page)
                if prop_data:
                    properties.append(prop_data)

            return properties

        except Exception as e:
            logger.error(f"Error searching properties: {str(e)}")
            return []

    def get_property_details(self, property_id: str) -> Optional[Dict]:
        """
        Obtiene detalles completos de una propiedad.
        """
        try:
            page = self.client.pages.retrieve(property_id)
            return self._extract_property_data(page)
        except Exception as e:
            logger.error(f"Error getting property details: {str(e)}")
            return None

    def register_lead(self, lead_data: Dict) -> Optional[str]:
        """
        Registra un nuevo lead en Notion.
        Espera: name, phone, email, interested_properties (lista), budget (opcional)
        """
        try:
            properties = {
                "Nombre": {
                    "title": [
                        {
                            "text": {
                                "content": lead_data.get("name", "")
                            }
                        }
                    ]
                },
                "Teléfono": {
                    "phone_number": lead_data.get("phone", "")
                },
                "Email": {
                    "email": lead_data.get("email", "")
                },
                "Fecha de Registro": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }

            # Agregar presupuesto si existe
            if lead_data.get("budget"):
                properties["Presupuesto"] = {
                    "number": lead_data["budget"]
                }

            # Agregar propiedades interesadas si existen
            if lead_data.get("interested_properties"):
                properties["Propiedades Interesadas"] = {
                    "relation": [
                        {"id": prop_id} for prop_id in lead_data["interested_properties"]
                    ]
                }

            response = self.client.pages.create(
                parent={"database_id": self.db_leads},
                properties=properties
            )

            return response["id"]

        except Exception as e:
            logger.error(f"Error registering lead: {str(e)}")
            return None

    def schedule_visit(self, visit_data: Dict) -> Optional[str]:
        """
        Agenda una cita/visita en Notion.
        Espera: property_id, client_name, client_email, client_phone, preferred_date, preferred_time
        """
        try:
            # Combinar fecha y hora
            visit_datetime = f"{visit_data['preferred_date']}T{visit_data['preferred_time']}:00"

            properties = {
                "Propiedad": {
                    "relation": [{"id": visit_data["property_id"]}]
                },
                "Cliente": {
                    "title": [
                        {
                            "text": {
                                "content": visit_data["client_name"]
                            }
                        }
                    ]
                },
                "Email": {
                    "email": visit_data["client_email"]
                },
                "Teléfono": {
                    "phone_number": visit_data["client_phone"]
                },
                "Fecha y Hora": {
                    "date": {
                        "start": visit_datetime
                    }
                },
                "Estado": {
                    "select": {
                        "name": "Programada"
                    }
                }
            }

            response = self.client.pages.create(
                parent={"database_id": self.db_citas},
                properties=properties
            )

            return response["id"]

        except Exception as e:
            logger.error(f"Error scheduling visit: {str(e)}")
            return None

    def log_call(self, call_data: Dict) -> Optional[str]:
        """
        Registra una llamada en Notion.
        Espera: agent_id, phone_number, duration, transcript, lead_id (opcional)
        """
        try:
            properties = {
                "Agente": {
                    "select": {
                        "name": "Sofia"
                    }
                },
                "Teléfono": {
                    "phone_number": call_data.get("phone_number", "")
                },
                "Duración (segundos)": {
                    "number": call_data.get("duration", 0)
                },
                "Transcripción": {
                    "rich_text": [
                        {
                            "text": {
                                "content": call_data.get("transcript", "")[:1000]  # Limit to 1000 chars
                            }
                        }
                    ]
                },
                "Fecha": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }

            # Relacionar con lead si existe
            if call_data.get("lead_id"):
                properties["Lead"] = {
                    "relation": [{"id": call_data["lead_id"]}]
                }

            response = self.client.pages.create(
                parent={"database_id": self.db_llamadas},
                properties=properties
            )

            return response["id"]

        except Exception as e:
            logger.error(f"Error logging call: {str(e)}")
            return None

    @staticmethod
    def _extract_property_data(page) -> Optional[Dict]:
        """
        Extrae datos de una propiedad desde un page de Notion.
        """
        try:
            props = page["properties"]

            # Extraer datos según la estructura de la base de datos
            return {
                "id": page["id"],
                "name": props.get("Nombre", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                "price": props.get("Precio", {}).get("number"),
                "bedrooms": props.get("Recámaras", {}).get("number"),
                "bathrooms": props.get("Baños", {}).get("number"),
                "location": props.get("Ubicación", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "property_type": props.get("Tipo", {}).get("select", {}).get("name", ""),
                "description": props.get("Descripción", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "amenities": [
                    item.get("name", "")
                    for item in props.get("Amenidades", {}).get("multi_select", [])
                ]
            }
        except Exception as e:
            logger.error(f"Error extracting property data: {str(e)}")
            return None
