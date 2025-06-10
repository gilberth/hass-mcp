#!/usr/bin/env python
"""Entry point for running Hass-MCP as a module"""

import uvicorn
import os

# Importamos la instancia mcp desde app.server
from app.server import mcp as mcp_app_instance

def main_stdio():
    """Run the MCP server with stdio communication (original behavior)"""
    print("Running Hass-MCP server with stdio communication.")
    mcp_app_instance.run() # Esto utiliza stdio_server internamente

def main_network():
    """Run the MCP server as a network service using Uvicorn"""
    host = os.environ.get("HASS_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("HASS_MCP_PORT", "8008"))
    reload_uvicorn = os.environ.get("HASS_MCP_RELOAD", "false").lower() == "true"

    print(f"Running Hass-MCP server as a network service on {host}:{port}")
    if reload_uvicorn:
        print("Uvicorn reload enabled.")

    # Aquí asumimos que 'mcp_app_instance' es directamente una aplicación ASGI
    # o que la librería 'mcp' registra sus rutas en una instancia de Starlette/FastAPI
    # que es accesible a través de mcp_app_instance o un atributo de ella.
    # Si mcp_app_instance.run() es lo que normalmente se usa para stdio,
    # y si FastMCP es una app Starlette/FastAPI-like, entonces 'mcp_app_instance'
    # debería ser la app ASGI.
    #
    # La clave está en si la instancia de FastMCP (mcp_app_instance) es en sí misma
    # una aplicación ASGI válida para Uvicorn.
    # Dado que pyproject.toml incluye 'mcp[cli]>=1.4.1', 'starlette', 'uvicorn',
    # es muy probable que sí.

    # Intentaremos pasar directamente la instancia mcp_app_instance a uvicorn.run
    # Si esto no funciona, necesitaríamos investigar la estructura de FastMCP
    # para encontrar el objeto de aplicación ASGI (ej. mcp_app_instance.app)
    uvicorn.run(mcp_app_instance, host=host, port=port, reload=reload_uvicorn)

if __name__ == "__main__":
    RUN_MODE = os.environ.get("HASS_MCP_RUN_MODE", "stdio").lower()
    if RUN_MODE == "network":
        main_network()
    elif RUN_MODE == "stdio":
        main_stdio()
    else:
        print(f"Unknown HASS_MCP_RUN_MODE: {RUN_MODE}. Defaulting to stdio.")
        main_stdio()
