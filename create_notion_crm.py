"""
Script para crear el CRM de Sofia en Notion.
Crea 4 bases de datos: Propiedades, Leads, Llamadas, Citas
"""

import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
PARENT_PAGE_ID = "3d87e5f1daa280048a81e7f6c56dd376"

client = Client(auth=NOTION_API_KEY)

# Datos ficticios para CDMX
PROPIEDADES_CDMX = [
    {"titulo": "🏢 Penthouse Polanco - Vista Panorámica", "tipo": "Venta", "zona": "Polanco", "precio": 4500000, "metros": 250, "recamaras": 3, "banos": 3, "descripcion": "Penthouse de lujo con terraza privada y vistas a la ciudad"},
    {"titulo": "🏠 Casa Moderna Condesa - Ideal Familia", "tipo": "Venta", "zona": "Condesa", "precio": 2200000, "metros": 180, "recamaras": 3, "banos": 2, "descripcion": "Casa renovada en la mejor zona de Condesa"},
    {"titulo": "🌆 Departamento Roma Norte - Centro Cultural", "tipo": "Renta", "zona": "Roma", "precio": 18000, "metros": 120, "recamaras": 2, "banos": 1, "descripcion": "Departamento amueblado en la vibrante Roma Norte"},
    {"titulo": "💼 Oficina Reforma - Nuevo Negocio", "tipo": "Renta", "zona": "Reforma", "precio": 25000, "metros": 200, "recamaras": 0, "banos": 2, "descripcion": "Oficina ejecutiva en Torre de Reforma, piso 18"},
    {"titulo": "🏡 Casa Coyoacán - Estilo Colonial", "tipo": "Venta", "zona": "Coyoacán", "precio": 1800000, "metros": 200, "recamaras": 4, "banos": 2, "descripcion": "Casa colonial en el corazón histórico de Coyoacán"},
    {"titulo": "🏢 Loft Industrial San Ángel - Artistas", "tipo": "Renta", "zona": "San Ángel", "precio": 15000, "metros": 150, "recamaras": 2, "banos": 2, "descripcion": "Loft con acabados industriales para creativo"},
    {"titulo": "🌊 Departamento Juárez - Esquina Privada", "tipo": "Venta", "zona": "Juárez", "precio": 1600000, "metros": 110, "recamaras": 2, "banos": 1, "descripcion": "Departamento con terraza en Av. Paseo de la Reforma"},
    {"titulo": "🏰 Mansión Santa Fe - Máximo Lujo", "tipo": "Venta", "zona": "Santa Fe", "precio": 5800000, "metros": 450, "recamaras": 5, "banos": 4, "descripcion": "Mansión privada con piscina y jardín en Santa Fe"},
    {"titulo": "🎨 Estudio Coyoacán - Creativo Space", "tipo": "Renta", "zona": "Coyoacán", "precio": 8000, "metros": 80, "recamaras": 1, "banos": 1, "descripcion": "Estudio perfecto para freelancers en Coyoacán"},
    {"titulo": "🌳 Casa Pedregal - Seguridad y Naturales", "tipo": "Venta", "zona": "Pedregal", "precio": 3200000, "metros": 280, "recamaras": 4, "banos": 3, "descripcion": "Casa en privada segura del Pedregal con áreas verdes"},
    {"titulo": "🏢 Departamento Cuauhtémoc - Rentabilidad", "tipo": "Renta", "zona": "Cuauhtémoc", "precio": 12000, "metros": 95, "recamaras": 2, "banos": 1, "descripcion": "Departamento céntrico, perfecta inversión inmobiliaria"},
    {"titulo": "🌃 Loft Nápoles - Moderno y Minimalista", "tipo": "Venta", "zona": "Nápoles", "precio": 1400000, "metros": 130, "recamaras": 2, "banos": 2, "descripcion": "Loft minimalista en Nápoles con acabados premium"},
    {"titulo": "🏡 Casa Bosque de Chapultepec - Tranquilidad", "tipo": "Venta", "zona": "Bosque de Chapultepec", "precio": 2800000, "metros": 220, "recamaras": 3, "banos": 2, "descripcion": "Casa con vistas al Bosque, ideal para familias"},
    {"titulo": "💼 Oficina Shared Polanco - Flexible", "tipo": "Renta", "zona": "Polanco", "precio": 8000, "metros": 50, "recamaras": 0, "banos": 1, "descripcion": "Escritorio en espacio compartido, red profesional"},
    {"titulo": "🏢 Penthouse Reforma - Ejecutivos", "tipo": "Renta", "zona": "Reforma", "precio": 35000, "metros": 180, "recamaras": 2, "banos": 2, "descripcion": "Departamento amueblado en Torre financiera con 24/7"},
]

def create_database(parent_id, title, icon, properties):
    try:
        response = client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": title}}],
            icon={"type": "emoji", "emoji": icon},
            properties=properties
        )
        db_id = response["id"]
        print(f"✅ {title}: {db_id}")
        return db_id
    except Exception as e:
        print(f"❌ {title}: {str(e)}")
        return None

def add_row_to_database(db_id, properties_data):
    try:
        client.pages.create(parent={"type": "database_id", "database_id": db_id}, properties=properties_data)
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False

print("\n📊 Creando bases de datos...")

# PROPIEDADES
propiedades_db_id = create_database(PARENT_PAGE_ID, "🏢 Propiedades", "🏠", {
    "Título": {"title": {}},
    "Tipo": {"select": {"options": [{"name": "Venta", "color": "blue"}, {"name": "Renta", "color": "green"}]}},
    "Zona": {"select": {"options": [
        {"name": "Polanco", "color": "purple"}, {"name": "Condesa", "color": "pink"},
        {"name": "Roma", "color": "red"}, {"name": "Reforma", "color": "orange"},
        {"name": "Coyoacán", "color": "yellow"}, {"name": "San Ángel", "color": "green"},
        {"name": "Juárez", "color": "blue"}, {"name": "Santa Fe", "color": "brown"},
        {"name": "Pedregal", "color": "gray"}, {"name": "Cuauhtémoc", "color": "default"},
        {"name": "Nápoles", "color": "default"}, {"name": "Bosque de Chapultepec", "color": "default"},
    ]}},
    "Precio": {"number": {}},
    "M²": {"number": {}},
    "Recámaras": {"number": {}},
    "Baños": {"number": {}},
    "Descripción": {"rich_text": {}},
    "Disponible": {"checkbox": {}},
})

# LEADS
leads_db_id = create_database(PARENT_PAGE_ID, "👥 Leads", "👤", {
    "Nombre": {"title": {}},
    "Teléfono": {"phone_number": {}},
    "Email": {"email": {}},
    "Temperatura": {"select": {"options": [
        {"name": "🔥 Hot", "color": "red"}, {"name": "🟠 Warm", "color": "orange"},
        {"name": "❄️ Cold", "color": "blue"}
    ]}},
    "Estatus": {"select": {"options": [
        {"name": "Pendiente de llamar", "color": "gray"}, {"name": "En proceso", "color": "yellow"},
        {"name": "Cita agendada", "color": "green"}, {"name": "No contestado", "color": "red"},
        {"name": "Sin interés", "color": "purple"}, {"name": "Cerrado", "color": "brown"}
    ]}},
    "Resumen Llamada": {"rich_text": {}},
    "Propiedades Interesadas": {"multi_select": {"options": []}},
    "Fecha Primer Contacto": {"date": {}},
    "Última Interacción": {"date": {}},
    "Notas": {"rich_text": {}},
})

# LLAMADAS
llamadas_db_id = create_database(PARENT_PAGE_ID, "📞 Llamadas", "📱", {
    "Fecha": {"date": {}},
    "Contacto": {"rich_text": {}},
    "Teléfono": {"phone_number": {}},
    "Duración (min)": {"number": {}},
    "Tipo": {"select": {"options": [
        {"name": "Entrante", "color": "green"}, {"name": "Saliente", "color": "blue"}
    ]}},
    "Transcript": {"rich_text": {}},
    "Resumen (Anthropic)": {"rich_text": {}},
    "Estatus": {"select": {"options": [
        {"name": "Completada", "color": "green"}, {"name": "Fallida", "color": "red"},
        {"name": "Pendiente", "color": "yellow"}
    ]}},
    "Propiedad Mencionada": {"rich_text": {}},
    "Call ID": {"rich_text": {}},
})

# CITAS
citas_db_id = create_database(PARENT_PAGE_ID, "📅 Citas", "📆", {
    "Fecha/Hora": {"date": {}},
    "Contacto": {"rich_text": {}},
    "Propiedad": {"rich_text": {}},
    "Agente": {"rich_text": {}},
    "Estatus": {"select": {"options": [
        {"name": "Confirmada", "color": "green"}, {"name": "Pendiente", "color": "yellow"},
        {"name": "Cancelada", "color": "red"}, {"name": "Completada", "color": "blue"}
    ]}},
    "Notas": {"rich_text": {}},
})

# Llenar PROPIEDADES
print("\n🏠 Llenando Propiedades con 15 ficticias...")
if propiedades_db_id:
    for i, prop in enumerate(PROPIEDADES_CDMX, 1):
        props_data = {
            "Título": {"title": [{"text": {"content": prop["titulo"]}}]},
            "Tipo": {"select": {"name": prop["tipo"]}},
            "Zona": {"select": {"name": prop["zona"]}},
            "Precio": {"number": prop["precio"]},
            "M²": {"number": prop["metros"]},
            "Recámaras": {"number": prop["recamaras"]},
            "Baños": {"number": prop["banos"]},
            "Descripción": {"rich_text": [{"text": {"content": prop["descripcion"]}}]},
            "Disponible": {"checkbox": True},
        }
        if add_row_to_database(propiedades_db_id, props_data):
            print(f"  ✅ {i}/15")

# Guardar en .env
print("\n💾 Guardando IDs en .env...")
env_lines = f"""
# Notion CRM Databases (creadas {PARENT_PAGE_ID})
NOTION_DATABASE_ID_PROPIEDADES={propiedades_db_id}
NOTION_DATABASE_ID_LEADS={leads_db_id}
NOTION_DATABASE_ID_LLAMADAS={llamadas_db_id}
NOTION_DATABASE_ID_CITAS={citas_db_id}
"""

with open("/Users/davidfray/Documents/sofia test/.env", "a") as f:
    f.write(env_lines)

# Resumen
print("\n" + "="*60)
print("✅ CRM CREADO EXITOSAMENTE")
print("="*60)
print("\n📍 ACCESO DIRECTO:")
print(f"  🔗 Página CRM: https://app.notion.com/p/{PARENT_PAGE_ID}")
print("\n📊 BASES CREADAS:")
if propiedades_db_id:
    print(f"  🏢 Propiedades: {propiedades_db_id}")
if leads_db_id:
    print(f"  👥 Leads: {leads_db_id}")
if llamadas_db_id:
    print(f"  📞 Llamadas: {llamadas_db_id}")
if citas_db_id:
    print(f"  📅 Citas: {citas_db_id}")
print("\n" + "="*60)

