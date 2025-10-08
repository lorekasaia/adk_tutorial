@echo off
REM ADK Agent Virtual Environment Setup Script for Windows

setlocal enabledelayedexpansion

REM --- Function for error handling ---
:handle_error
echo Error: %~1
exit /b 1

REM --- Part 1: Set Google Cloud Project ID ---
set "PROJECT_FILE=%USERPROFILE%\project_id.txt"
echo --- Setting Google Cloud Project ID File ---

set /p user_project_id="Please enter your Google Cloud project ID: "

if not defined user_project_id (
    call :handle_error "No project ID was entered."
)

echo You entered: !user_project_id!
echo !user_project_id! > "%PROJECT_FILE%"

if !errorlevel! neq 0 (
    call :handle_error "Failed saving your project ID: !user_project_id!."
)
echo Successfully saved project ID.

echo 🚀 Setting up ADK Agent virtual environment...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is required but not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo ✅ Python %python_version% detected

REM Check which version of google-adk will be installed
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    echo 🎯 Python %python_version% >= 3.9 → Will install google-adk==1.5.0 (latest version)
) else (
    echo ⚠️  Python %python_version% < 3.9 → Will install google-adk==0.3.0 (compatible version)
    echo    For the latest features, consider upgrading to Python 3.9 or higher
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv .adk_env

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .adk_env\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
pip install --upgrade pip

REM Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

echo --- Setting Google Cloud Environment Variables ---

REM --- Authentication Check ---
echo Checking gcloud authentication status...

gcloud auth print-access-token >nul 2>&1
if !errorlevel! neq 0 (
    echo Error: gcloud is not authenticated.
    echo Please log in by running: gcloud auth login
    exit /b 1
)
echo gcloud is authenticated.

REM --- Get Project ID and Create .env file ---
if not exist "%PROJECT_FILE%" (
    echo Error: Project file not found at "%PROJECT_FILE%"
    echo Please run the script again and provide your Google Cloud project ID.
    exit /b 1
)

for /f "delims=" %%i in (%PROJECT_FILE%) do set PROJECT_ID_FROM_FILE=%%i
echo Setting gcloud config project to: !PROJECT_ID_FROM_FILE!
gcloud config set project "!PROJECT_ID_FROM_FILE!" --quiet

REM Re-confirm the project ID from the config
for /f "delims=" %%j in ('gcloud config get project') do set PROJECT_ID=%%j
set "REGION=us-central1"

echo 📝 Creating .env file...
(
    echo # Environment variables for ADK Agent, created by setup_venv.bat
    echo GOOGLE_GENAI_USE_VERTEXAI=TRUE
    echo GOOGLE_CLOUD_PROJECT=!PROJECT_ID!
    echo GOOGLE_CLOUD_LOCATION=!REGION!
) > .env

echo ✅ Setup complete! A '.env' file has been created with your configuration.
echo.
echo To activate the virtual environment, run:
echo    .adk_env\Scripts\activate
echo.
echo Your agent will automatically load the settings from the .env file.
echo To deactivate the virtual environment, run:
echo    deactivate
echo.
echo Press any key to continue...
pause >nul