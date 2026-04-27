import os
from dotenv import load_dotenv

# 1. Cargar configuración ANTES de importar las librerías de IA
# Busca el .env en el directorio actual o fuerza la búsqueda en el directorio padre
load_dotenv() 
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google import adk
from google.adk.runners import Runner
import matplotlib.pyplot as plt
import matplotlib
import uuid

from google.adk.sessions import DatabaseSessionService
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pg8000

from google.genai.types import Content, Part
import uvicorn
import asyncio

app = FastAPI(title="Batia Agent UI")

# Configuración para evitar errores de GUI con Matplotlib en servidores
matplotlib.use('Agg')

# Crear carpeta para guardar los gráficos generados y montarla en la web
os.makedirs("graficos", exist_ok=True)
app.mount("/graficos", StaticFiles(directory="graficos"), name="graficos")

# --- HERRAMIENTAS DE DATOS ---
# --- CONFIGURACIÓN DE BASE DE DATOS (Cloud SQL) ---

def consultar_cloud_sql(termino_busqueda: str = "") -> pd.DataFrame:
    """
    Se conecta a Google Cloud SQL (PostgreSQL) para consultar datos de clientes.
    Nota: Requerirá instalar dependencias como 'pg8000', 'sqlalchemy' y 'cloud-sql-python-connector'.
    """
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")

    if not all([db_user, db_pass, db_name, instance_connection_name]):
        raise ValueError("Faltan variables de entorno para Cloud SQL (DB_USER, DB_PASS, DB_NAME, INSTANCE_CONNECTION_NAME). Verifica tu archivo .env.")
    
    # Uso de Cloud SQL Python Connector
    connector = Connector()
    def getconn():
        return connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=IPTypes.PUBLIC
        )
    
    engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
    
    termino_limpio = termino_busqueda.strip().lower()
    if not termino_limpio or termino_limpio in ['todos', 'clientes', 'general', 'lista', 'información']:
        query = "SELECT * FROM clientes LIMIT 50"
    else:
        query = f"SELECT * FROM clientes WHERE nombre ILIKE '%{termino_busqueda}%' OR empresa ILIKE '%{termino_busqueda}%' OR notas ILIKE '%{termino_busqueda}%' LIMIT 50"
    
    with engine.connect() as conn:
        df = pd.read_sql(sqlalchemy.text(query), con=conn)
        
    connector.close()
        
    return df

def buscar_clientes_por_criterio(termino_busqueda: str = "") -> str:
    """
    Busca información sobre los clientes en la base de datos de producción (Cloud SQL).
    Busca coincidencias en las columnas 'nombre', 'empresa' o 'notas'.
    Si el usuario pide una lista general, usa un texto vacío ("").
    """
    try:
        df = consultar_cloud_sql(termino_busqueda)
        return df.to_string() if not df.empty else "No se encontraron resultados en la base de datos de producción."
    except Exception as e:
        # Es buena práctica registrar el error real para depuración
        print(f"Error al consultar Cloud SQL: {e}")
        return f"Hubo un error al conectar con la base de datos: {e}. Por favor, verifica la configuración."

def consultar_dashboard_bi(kpi: str, contexto: str = "general") -> str:
    """
    Consulta la API de Business Intelligence corporativa (ej. Power BI / Looker) para obtener métricas agregadas avanzadas y KPIs.
    Ejemplos de 'kpi': 'ventas_totales', 'tasa_conversion', 'rendimiento_vendedores'.
    """
    # NOTA: Esta es una plantilla lista para conectar con Power BI REST API o Looker API.
    # Usarías librerías como 'msal' o 'requests' para autenticarte y hacer la petición HTTP al dashboard real.
    print(f"[BI API Mock] Solicitando KPI: '{kpi}' con contexto '{contexto}'")
    
    if kpi == "ventas_totales":
        return f"El Dashboard de BI reporta que las ventas totales para '{contexto}' son de $1,450,000 MXN este trimestre."
    elif kpi == "tasa_conversion":
        return f"Según la plataforma de BI, la tasa de conversión de prospectos a clientes para '{contexto}' se sitúa en un 24.5%."
    elif kpi == "rendimiento_vendedores":
        return "El reporte de BI indica que Lore lidera las ventas con un 120% de alcance de cuota, seguida de cerca por el resto del equipo."
    else:
        return f"Datos del Dashboard para el KPI '{kpi}': Los indicadores están estables y dentro de los rangos esperados para el período actual."

def generar_grafico_analisis(metrica: str) -> str:
    """
    Genera un gráfico visual basado en los datos reales de los clientes en la base de datos.
    Métricas permitidas: 'prioridad' (gráfico de barras) o 'estado' (gráfico de pastel).
    """
    try:
        df = consultar_cloud_sql("") # Obtenemos todos los registros posibles
        if df.empty:
            return "No hay suficientes datos en la base para graficar."
        
        plt.figure(figsize=(8, 6))
        
        if metrica.lower() == "prioridad" and 'prioridad' in df.columns:
            conteo = df['prioridad'].value_counts()
            conteo.plot(kind='bar', color=['#4CAF50', '#FF9800', '#F44336'])
            plt.title("Distribución de Clientes por Prioridad")
            plt.xlabel("Nivel de Prioridad")
            plt.ylabel("Cantidad de Clientes")
            plt.xticks(rotation=0)
        elif metrica.lower() == "estado" and '_estado' in df.columns:
            conteo = df['_estado'].value_counts()
            conteo.plot(kind='pie', autopct='%1.1f%%', startangle=90)
            plt.title("Proporción de Clientes por Estado Interno")
            plt.ylabel("") # Ocultar label del eje Y
        else:
            return f"No se pudo generar el gráfico. Verifica que la métrica '{metrica}' sea 'prioridad' o 'estado'."
        
        filename = f"grafico_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join("graficos", filename)
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        # Le decimos al modelo de IA qué HTML devolver para que el frontend muestre la imagen
        return f"Gráfico generado con éxito. DEBES responder esto al usuario exactamente así para que vea la imagen: <br><img src='/graficos/{filename}' alt='Gráfico de {metrica}' style='max-width: 100%; border-radius: 8px; margin-top: 10px;'/>"
    except Exception as e:
        return f"Error al procesar y graficar los datos: {e}"

# --- CONFIGURACIÓN DEL AGENTE (ADK 1.15.1) ---
agente = adk.Agent(
    name="BatiaCommercialAgent",
    model="gemini-2.5-flash",
    instruction="Eres el asistente de Lore en Grupo Batia. Tu función es gestionar la información de los clientes para ventas. Puedes buscar clientes, consultar métricas en el Dashboard BI, y generar gráficos visuales reales usando los datos de la base de datos. Al buscar clientes, básate en 'nombre', 'empresa' o 'notas'. Siempre que generes un gráfico, debes mostrar la imagen en el chat usando etiquetas HTML (<img>).",
    tools=[buscar_clientes_por_criterio, consultar_dashboard_bi, generar_grafico_analisis]
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