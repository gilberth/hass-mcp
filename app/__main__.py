#!/usr/bin/env python
"""Entry point for running Hass-MCP as a module"""

import uvicorn
import os

# Importamos la instancia mcp desde app.server
from app.server import mcp as mcp_instance # Renombramos para claridad

def main_stdio():
    """Run the MCP server with stdio communication (original behavior)"""
    print("Running Hass-MCP server with stdio communication.")
    mcp_instance.run()

def main_network():
    """Run the MCP server as a network service using Uvicorn"""
    host = os.environ.get("HASS_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("HASS_MCP_PORT", "8008"))
    reload_uvicorn = os.environ.get("HASS_MCP_RELOAD", "false").lower() == "true"
    log_level_uvicorn = os.environ.get("HASS_MCP_LOG_LEVEL", "info").lower()


    print(f"Running Hass-MCP server as a network service on {host}:{port}")
    if reload_uvicorn:
        print("Uvicorn reload enabled.")

    # Dado que FastMCP es una subclase de starlette.applications.Starlette,
    # la instancia mcp_instance *ES* la aplicación ASGI.
    # El error anterior "TypeError: 'FastMCP' object is not callable" es peculiar.
    # Podría estar relacionado con cómo Uvicorn maneja las subclases directas
    # o si falta algún paso de inicialización que el método .run() de FastMCP haría.

    # Una posible razón para "ASGI 'lifespan' protocol appears unsupported."
    # es que los manejadores on_startup y on_shutdown no están siendo
    # registrados/ejecutados de la misma manera que lo haría FastMCP.run() a través de stdio_server.
    # La clase Starlette (y por ende FastMCP) soporta el protocolo lifespan.
    # El mensaje de Uvicorn podría ser una pista de que algo en la inicialización no está ocurriendo.

    # FastMCP tiene un método 'startup' y 'shutdown' que son llamados
    # por la lógica del ciclo de vida de Starlette si está configurado.

    # Vamos a pasar la ruta de importación de la instancia a Uvicorn,
    # lo cual a veces es más robusto para Uvicorn.
    # Uvicorn puede entonces importar y manejar la aplicación.
    uvicorn.run(
        "app.server:mcp",  # Ruta de importación a la instancia mcp
        host=host,
        port=port,
        reload=reload_uvicorn,
        log_level=log_level_uvicorn,
        factory=False # Indica que "app.server:mcp" es la app, no una factoría
    )

if __name__ == "__main__":
    RUN_MODE = os.environ.get("HASS_MCP_RUN_MODE", "stdio").lower()
    if RUN_MODE == "network":
        main_network()
    elif RUN_MODE == "stdio":
        main_stdio()
    else:
        print(f"Unknown HASS_MCP_RUN_MODE: {RUN_MODE}. Defaulting to stdio.")
        main_stdio()
