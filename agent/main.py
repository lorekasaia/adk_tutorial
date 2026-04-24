import os
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from google import adk
from google.adk.runners import Runner

from google.adk.sessions import DatabaseSessionService

from google.genai.types import Content, Part
from dotenv import load_dotenv
import uvicorn
import asyncio

# 1. Cargar configuración
load_dotenv()

app = FastAPI(title="Batia Agent UI")

# --- HERRAMIENTAS DE DATOS ---
# --- CONFIGURACIÓN DE BASE DE DATOS (Preparación para Cloud SQL) ---
USE_CLOUD_SQL = os.getenv("USE_CLOUD_SQL", "False").lower() in ("true", "1")

# Cargar los datos en memoria una sola vez al arrancar la app para mejorar el rendimiento
try:
    df_clientes_local = pd.read_csv('datosdeprueba.csv')
except Exception:
    df_clientes_local = pd.DataFrame() # Si falla, creamos un DataFrame vacío para que no colapse

def consultar_cloud_sql(descripcion: str) -> pd.DataFrame:
    """
    Plantilla para la futura conexión a Google Cloud SQL (PostgreSQL).
    Nota: Requerirá instalar dependencias como 'pg8000', 'sqlalchemy' y 'cloud-sql-python-connector'.
    """
    # db_user = os.environ.get("DB_USER")
    # db_pass = os.environ.get("DB_PASS")
    # db_name = os.environ.get("DB_NAME")
    # instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    
    # Aquí iría la lógica para conectarse y ejecutar un query usando la descripción como filtro
    # engine = sqlalchemy.create_engine(...) 
    # query = f"SELECT * FROM clientes WHERE intereses LIKE '%{descripcion}%' LIMIT 50"
    # df = pd.read_sql(query, con=engine)
    
    print("Simulando consulta a Cloud SQL...")
    return pd.DataFrame() # Placeholder temporal

def buscar_clientes_por_criterio(descripcion: str) -> str:
    """
    Busca información sobre los clientes. 
    Usa datos locales por defecto, preparado para migrar a Cloud SQL.
    """
    if USE_CLOUD_SQL:
        df = consultar_cloud_sql(descripcion)
        return df.to_string() if not df.empty else "No se encontraron resultados en la base de datos de producción."
    else:
        if df_clientes_local.empty:
            return "Error: No se encontraron datos. Asegúrate de que datosdeprueba.csv exista."
        # Nota: Limitamos a los primeros 50 registros para evitar exceder el límite de contexto del LLM
        return df_clientes_local.head(50).to_string()

# --- CONFIGURACIÓN DEL AGENTE (ADK 1.15.1) ---
agente = adk.Agent(
    name="BatiaCommercialAgent",
    model="gemini-2.5-flash",
    instruction="Eres el asistente de Lorena Karen en Grupo Batia. Usa datosdeprueba.csv para gestionar ventas.",
    tools=[buscar_clientes_por_criterio]
)

# Creamos el servicio de sesión (guardará el historial en sessions.db)
session_service = DatabaseSessionService(db_url="sqlite:///sessions.db")

# Creamos el Runner pasándole el servicio de sesión
runner = Runner(agent=agente, app_name=agente.name, session_service=session_service)

# --- INTERFAZ WEB (HTML/CSS) ---
@app.get("/", response_class=HTMLResponse)
async def get_ui():
    # Servimos el archivo HTML estático.
    # Asegúrate de que la ruta es correcta desde donde ejecutas el script.
    # (Se asume que ejecutas `python agent/main.py` desde el directorio `ADK_Basic`)
    return FileResponse("agent/base.html")

# --- ENDPOINT DE COMUNICACIÓN ---
@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    if not prompt:
        return {"error": "No se recibió ningún prompt."}
    
    try:
        full_response = ""
        # 1. El input para run_async debe ser un objeto Content, no un string.
        #    Esto corrige el error "'str' object has no attribute 'model_copy'".
        message = Content(parts=[Part(text=prompt)], role="user")

        # 2. Aseguramos que la sesión exista en la base de datos antes de usarla
        try:
            session = await session_service.get_session(app_name=agente.name, user_id="web_user", session_id="web_session")
        except Exception:
            session = None
            
        if not session:
            await session_service.create_session(session_id="web_session", app_name=agente.name, user_id="web_user")

        # 3. Usamos runner.run_async() con un sistema de reintentos automático
        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_response = ""
                async for event in runner.run_async(
                    user_id="web_user",
                    session_id="web_session",
                    new_message=message
                ):
                    # El texto de respuesta está dentro de event.content.parts
                    if event.content:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                full_response += part.text
                break  # Si tiene éxito, salimos del bucle de reintentos
            except Exception as e:
                if "503" in str(e) and "UNAVAILABLE" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(4)  # Esperamos 4 segundos antes de volver a intentar
                    continue
                raise e  # Si no es un error 503 o se agotaron los intentos, lanzamos el error al bloque except principal
        
        if full_response:
            return {"respuesta": full_response}
        else:
            return {"respuesta": "El agente procesó la tarea, pero no devolvió texto."}
            
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg and "UNAVAILABLE" in error_msg:
            return {"respuesta": "El agente está experimentando una alta demanda en los servidores de Google en este momento. Por favor, espera un par de minutos y vuelve a intentarlo. ⏳"}
        elif "getaddrinfo failed" in error_msg:
            return {"respuesta": "Error de red: No se pudo conectar a los servidores de Google. Verifica tu conexión a internet, VPN o configuración de proxy corporativo. 🌐"}
        return {"error": f"Error en ejecución: {error_msg}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)