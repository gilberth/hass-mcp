#!/usr/bin/env python
"""Entry point for running Hass-MCP as a module"""

import uvicorn
import os
from starlette.applications import Starlette # Importar Starlette
from starlette.routing import Mount # Importar Mount para montar aplicaciones

# Importamos la instancia mcp desde app.server
from app.server import mcp as mcp_sub_app # Renombramos para claridad, es nuestra sub-aplicación

# --- Lifespan event handlers (copiado de cómo FastMCP/Starlette podría hacerlo) ---
# Necesitamos asegurarnos de que los eventos de ciclo de vida de mcp_sub_app se llamen.
# FastMCP (como Starlette) tiene métodos on_event("startup") y on_event("shutdown")
# para registrar manejadores. Si tu app/server.py los usa, esto ayudará.

# Para asegurarnos de que los eventos de ciclo de vida de `mcp_sub_app` (que es una app Starlette)
# se ejecuten, podemos definir funciones de ciclo de vida para nuestra app principal
# que a su vez llamen a los manejadores de la sub-app si es necesario, o simplemente
# confiar en que Starlette maneje el ciclo de vida de las apps montadas.
# Starlette debería manejar esto automáticamente para apps montadas si estas
# definen sus propios manejadores de ciclo de vida.

# Si `mcp_sub_app` tiene manejadores de startup/shutdown definidos (lo cual es probable
# para inicializar el cliente HTTPX para app.hass, etc.), Starlette los llamará.
# El archivo app/hass.py tiene cleanup_client(), que debería ser llamado en shutdown.
# app/server.py no parece registrar explícitamente cleanup_client con on_event("shutdown")
# en la instancia 'mcp'. Esto podría ser un problema.

# Vamos a añadir explícitamente el cleanup_client al ciclo de vida de nuestra nueva app Starlette.
from app.hass import cleanup_client as hass_cleanup_client

async def run_hass_cleanup():
    await hass_cleanup_client()

# Creamos una nueva aplicación Starlette principal
# Los eventos de ciclo de vida de FastMCP (mcp_sub_app) deberían ser manejados
# si están registrados usando on_event.
# Si cleanup_client es el único importante, lo añadimos aquí.
app = Starlette(
    routes=[
        # Montamos nuestra aplicación Hass-MCP (FastMCP) en la raíz.
        # Cualquier petición (ej. /mcp/tool/get_version) será enviada a mcp_sub_app.
        Mount("/", app=mcp_sub_app)
    ],
    on_shutdown=[run_hass_cleanup] # Aseguramos la limpieza del cliente httpx
)

# --- Fin Lifespan ---

def main_stdio():
    """Run the MCP server with stdio communication (original behavior)"""
    print("Running Hass-MCP server with stdio communication.")
    # Para stdio, seguimos usando el método run() original de mcp_sub_app
    # que usa stdio_server(self)
    mcp_sub_app.run()

def main_network():
    """Run the MCP server as a network service using Uvicorn"""
    host = os.environ.get("HASS_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("HASS_MCP_PORT", "8008"))
    reload_uvicorn = os.environ.get("HASS_MCP_RELOAD", "false").lower() == "true"
    log_level_uvicorn = os.environ.get("HASS_MCP_LOG_LEVEL", "info").lower()

    print(f"Running Hass-MCP server as a network service on {host}:{port}")
    if reload_uvicorn:
        print("Uvicorn reload enabled.")

    # Ahora pasamos nuestra nueva app Starlette a Uvicorn
    uvicorn.run(
        app, # La instancia de Starlette que acabamos de crear
        host=host,
        port=port,
        reload=reload_uvicorn,
        log_level=log_level_uvicorn
        # factory=True ya no es necesario si pasamos la instancia directamente
    )

if __name__ == "__main__":
    RUN_MODE = os.environ.get("HASS_MCP_RUN_MODE", "stdio").lower()
    if RUN_MODE == "network":
        # Aquí es crucial que `app` (la instancia de Starlette) esté definida
        # a nivel de módulo para que Uvicorn pueda importarla si se usa una cadena,
        # o pasarla directamente si no se usa reload.
        # Si HASS_MCP_RELOAD es true, uvicorn.run necesita una cadena de importación.
        # Si es false, puede tomar la instancia directamente.
        # Para simplificar y consistencia con reload=True, es mejor referenciar por cadena.
        # Por lo tanto, el objeto 'app' debe ser importable.

        # Para que uvicorn --reload funcione bien, la app debe ser importable.
        # Así que en lugar de `uvicorn.run(app, ...)` cuando reload=True,
        # Uvicorn normalmente prefiere `uvicorn.run("tu_modulo:tu_app_instancia", reload=True)`

        # Vamos a reestructurar ligeramente para que 'app' sea accesible globalmente en este script
        # y Uvicorn pueda usarlo incluso con reload.
        # main_network() ahora usa la 'app' definida globalmente.
        main_network()

    elif RUN_MODE == "stdio":
        main_stdio()
    else:
        print(f"Unknown HASS_MCP_RUN_MODE: {RUN_MODE}. Defaulting to stdio.")
        main_stdio()
