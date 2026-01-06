@echo off
REM Nova-16 MCP Server Startup Script
REM This script starts the Nova-16 MCP server for local development

cd /d "%~dp0"

echo ========================================
echo Nova-16 MCP Server Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo Checking dependencies...
py -3.13 -m pip list | find "mcp" >nul
if %errorlevel% neq 0 (
    echo.
    echo MCP package not found. Installing dependencies...
    echo.
    py -3.13 -m pip install -r requirements-mcp.txt
    if %errorlevel% neq 0 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Starting Nova-16 MCP Server...
echo ========================================
echo.
echo Server is running. It will wait for connections from Claude.
echo.
echo To use:
echo 1. Configure Claude with this path: %cd%\nova_mcp_server.py
echo 2. Restart Claude Desktop
echo 3. Nova-16 tools will appear in Claude
echo.
echo Press Ctrl+C to stop the server.
echo.

py -3.13 nova_mcp_server.py

if %errorlevel% neq 0 (
    echo.
    echo Error: Server failed to start
    pause
    exit /b 1
)
