#!/usr/bin/env python3
"""
Script para crear automáticamente todas las propiedades necesarias en las bases de datos de Notion.
Ejecutar: python scripts/setup_notion_schema.py
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NOTION_API_KEY")
if not API_KEY:
    print("❌ NOTION_API_KEY no configurada")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# IDs de las bases de datos
databases = {
    "Llamadas": "572dadd3-cd50-48b6-bff7-c1d9ca104260",
    "Leads": "973c5050-b020-49c3-98c2-89e72496268c",
    "Propiedades": os.getenv("NOTION_DATABASE_ID_PROPIEDADES", ""),
    "Citas": os.getenv("NOTION_DATABASE_ID_CITAS", "")
}

# Propiedades a crear para cada base de datos
properties_config = {
    "Llamadas": {
        "Fecha": {"date": {}},
        "Contacto": {"rich_text": {}},
        "Teléfono": {"phone_number": {}},
        "Duración (min)": {"number": {}},
        "Tipo": {
            "select": {
                "options": [
                    {"name": "Entrante", "color": "blue"},
                    {"name": "Saliente", "color": "green"}
                ]
            }
        },
        "Transcript": {"rich_text": {}},
        "Resumen (Anthropic)": {"rich_text": {}},
        "Estatus": {
            "select": {
                "options": [
                    {"name": "Completada", "color": "green"},
                    {"name": "En Progreso", "color": "yellow"},
                    {"name": "Fallida", "color": "red"}
                ]
            }
        },
        "Call ID": {"rich_text": {}},
    },
    "Leads": {
        "Teléfono": {"phone_number": {}},
        "Temperatura": {
            "select": {
                "options": [
                    {"name": "cold", "color": "blue"},
                    {"name": "warm", "color": "yellow"},
                    {"name": "hot", "color": "red"}
                ]
            }
        },
        "Estatus": {
            "select": {
                "options": [
                    {"name": "Pendiente de llamar", "color": "gray"},
                    {"name": "En proceso", "color": "blue"},
                    {"name": "Cita agendada", "color": "green"},
                    {"name": "No contestado", "color": "red"},
                    {"name": "Sin interés", "color": "orange"},
                    {"name": "Cerrado", "color": "purple"}
                ]
            }
        },
        "Resumen Llamada": {"rich_text": {}},
        "Última Interacción": {"date": {}},
        "Fecha Primer Contacto": {"date": {}},
    },
    "Propiedades": {
        "Ubicación": {"rich_text": {}},
        "Precio Mensual": {"number": {}},
        "Recámaras": {"number": {}},
        "Baños": {"number": {}},
        "m²": {"number": {}},
        "Disponible": {
            "select": {
                "options": [
                    {"name": "Sí", "color": "green"},
                    {"name": "No", "color": "red"}
                ]
            }
        },
        "Descripción": {"rich_text": {}},
        "Fotos URL": {"rich_text": {}},
    },
    "Citas": {
        "Lead": {"rich_text": {}},
        "Propiedad": {"rich_text": {}},
        "Fecha": {"date": {}},
        "Hora": {"rich_text": {}},
        "Confirmada": {
            "select": {
                "options": [
                    {"name": "Sí", "color": "green"},
                    {"name": "No", "color": "red"},
                    {"name": "Pendiente", "color": "yellow"}
                ]
            }
        },
        "Notas": {"rich_text": {}},
    }
}

def create_properties(db_name, db_id):
    if not db_id:
        print(f"⏭️  {db_name}: ID no configurada, saltando")
        return

    print(f"\n{'='*80}")
    print(f"🔧 CONFIGURANDO {db_name} ({db_id})")
    print(f"{'='*80}")

    # Obtener propiedades actuales
    resp = requests.get(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=headers
    )

    if resp.status_code != 200:
        print(f"❌ Error obteniendo estructura: {resp.status_code}")
        print(resp.text)
        return

    current_props = set(resp.json().get("properties", {}).keys())
    print(f"✅ Propiedades actuales: {current_props}")

    # Determinar qué propiedades crear
    config = properties_config.get(db_name, {})
    props_to_create = {k: v for k, v in config.items() if k not in current_props}

    if not props_to_create:
        print(f"✅ {db_name} ya tiene todas las propiedades necesarias")
        return

    print(f"\n📝 Creando {len(props_to_create)} propiedades faltantes:")
    for prop_name in props_to_create.keys():
        print(f"   • {prop_name}")

    # Crear propiedades via PATCH
    payload = {
        "properties": props_to_create
    }

    resp = requests.patch(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=headers,
        json=payload
    )

    if resp.status_code == 200:
        print(f"\n✅ {db_name}: Propiedades creadas exitosamente")
    else:
        print(f"\n❌ Error creando propiedades: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    for db_name, db_id in databases.items():
        create_properties(db_name, db_id)

    print(f"\n{'='*80}")
    print("✅ Configuración completada")
    print(f"{'='*80}")
