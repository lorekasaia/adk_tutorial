# Agente Comercial Batia

Un sistema de IA multi-agente construido con el **Agent Development Kit (ADK) de Google**, diseñado para actuar como un asistente comercial avanzado para Grupo Batia.

## Características Principales

- 🏢 **Arquitectura Multi-Agente**: Un agente orquestador inteligente dirige las tareas a 4 agentes especializados (Datos, Analítica, CRM e IA Avanzada).
- 🔍 **Búsqueda y Consulta**: Acceso en tiempo real a la base de datos de clientes en Google Cloud SQL, con capacidad para ejecutar consultas SQL directas.
- 📈 **Análisis y Reportes**:
    - Generación de resúmenes financieros del pipeline.
    - Creación de gráficos visuales (Matplotlib) sobre métricas clave.
    - Exportación de datos a **Excel, PDF y Word**.
- ✍️ **Gestión de CRM**: Actualización de estados y registro de seguimientos de clientes en el pipeline.
- 🧠 **Capacidades de IA**:
    - Envío de correos electrónicos a clientes mediante SMTP (Office 365).
    - Análisis de documentos (**PDF, Word, Excel, Imágenes**) subidos por el usuario.
    - Cálculo de probabilidad de cierre (**Lead Scoring**).

## Requisitos Previos

- Python 3.8 o superior.
- Credenciales de Google Cloud y acceso a la base de datos Cloud SQL.

## Configuración Rápida

### What the Script Does

The setup script will:

1.  **Check for Python**: Ensures you have Python 3.8 or higher.
2.  **Create a Virtual Environment**: Sets up a dedicated `.adk_env` directory.
3.  **Install Dependencies**: Installs the required Python packages from `requirements.txt`.
4.  **Prompt for Project ID**: Asks for your Google Cloud Project ID.
5.  **Create `.env` File**: Generates a `.env` file in the root directory with the following configuration:

    ```env
    GOOGLE_GENAI_USE_VERTEXAI=TRUE
    GOOGLE_CLOUD_PROJECT=your_project_id
    GOOGLE_CLOUD_LOCATION=us-central1
    ```

## Running the Agent

After the setup is complete:

1.  **Activate the virtual environment**:

    **Mac/Linux:**
    ```bash
    source .adk_env/bin/activate
    ```

    **Windows:**
    ```cmd
    .adk_env\Scripts\activate
    ```

2.  **Run the FastAPI server**:

    ```bash
    python agent/main.py
    ```

3.  **Access the web interface**:

    Open your browser and go to `http://127.0.0.1:8000`.

## Deactivating the Environment

When you're done, you can deactivate the virtual environment:

```bash
deactivate
```