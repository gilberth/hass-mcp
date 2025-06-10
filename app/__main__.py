#!/usr/bin/env python
"""Entry point for running Hass-MCP as a module"""

import uvicorn
import os

# Importamos la instancia mcp desde app.server
from app.server import mcp as mcp_application # Nombre más explícito
from app.hass import cleanup_client as hass_cleanup_client

def main_stdio():
    """Run the MCP server with stdio communication (original behavior)"""
    print("Running Hass-MCP server with stdio communication.")
    mcp_application.run()

async def lifespan_handler(app_to_wrap):
    """Maneja el ciclo de vida de la aplicación."""
    # Aquí podríamos ejecutar código de startup si mcp_application lo necesitara explícitamente
    # y no lo hiciera a través de los eventos on_startup de Starlette.
    # Por ahora, nos enfocamos en el shutdown.
    yield
    # Shutdown
    print("Lifespan: Shutting down. Cleaning up Hass client.")
    await hass_cleanup_client()

def create_network_app():
    """Crea la aplicación ASGI para el modo de red."""
    # Dado que FastMCP hereda de Starlette, mcp_application *es* una app Starlette.
    # El error sugiere que no es 'callable' como Starlette espera para un app montada
    # o como Uvicorn espera para una app raíz.

    # Intentemos acceder directamente al router de Starlette de la instancia FastMCP
    # y construir una nueva Starlette con esas rutas.
    # Esto es más invasivo pero podría sortear el problema de "no callable".

    from starlette.applications import Starlette
    from starlette.routing import Route, Mount, WebSocketRoute

    # Extraer rutas y otros componentes de mcp_application si es posible.
    # Esto requiere introspección de la instancia Starlette (mcp_application).
    # mcp_application.routes es la lista de rutas.
    # mcp_application.user_middleware es la pila de middleware.
    # mcp_application.exception_handlers.
    # mcp_application.lifespan_context es el manejador de ciclo de vida.

    # Esta es la opción más directa y debería funcionar si mcp_application es una Starlette válida:
    # return mcp_application

    # Si lo anterior sigue fallando, necesitamos una forma de obtener el "corazón" de FastMCP.
    # Una opción drástica pero que podría funcionar es que FastMCP exponga su router.
    # Si FastMCP tiene un atributo como `mcp_application.router`, podríamos usarlo.
    # Por ahora, vamos a asumir que el problema es más sutil y que mcp_application
    # *debería* ser callable.

    # La librería anthropic-mcp en mcp/server/mcp.py (clase MCP) añade rutas así:
    # self.add_route("/mcp/prompts", self._list_prompts, methods=["GET"], name="list_prompts")
    # Estas rutas están en self.router.routes
    # Y FastMCP hereda de MCP.

    # El problema podría ser que al montar `Mount("/", app=mcp_application)`, Starlette
    # espera que `mcp_application` sea una función o un objeto con `__call__`.
    # Si `FastMCP.__call__` no está bien definido o está ausente, falla.

    # Vamos a probar sin montar, pasando mcp_application directamente a Uvicorn
    # PERO, asegurándonos de que el ciclo de vida de Uvicorn llama a los eventos
    # correctos en mcp_application.
    # Uvicorn puede tomar una función de ciclo de vida.

    # No, la forma más limpia es asegurar que la aplicación ASGI sea correcta.
    # Si mcp_application (FastMCP) hereda de Starlette, *es* una aplicación ASGI.
    # El error es muy confuso.

    # ¿Qué tal si envolvemos la llamada a mcp_application?
    async def asgi_callable_wrapper(scope, receive, send):
        # Aquí, mcp_application es la instancia de FastMCP
        # Debería ser directamente llamable como una app Starlette.
        return await mcp_application(scope, receive, send)

    # Creamos una app Starlette que usa nuestro wrapper de ciclo de vida explícito
    # y que tiene como única "ruta" el wrapper llamable.
    # Esto es un poco un hack.
    #
    # from starlette.applications import Starlette
    # from starlette.routing import Route
    #
    # network_app = Starlette(
    #     routes=[Route("/{path:path}", endpoint=asgi_callable_wrapper)],
    #     lifespan=lifespan_handler
    # )
    # return network_app

    # La forma más directa que *debería* funcionar si FastMCP está bien:
    # Simplemente devolver mcp_application y Uvicorn debería poder manejar su ciclo de vida.
    # El mensaje "ASGI 'lifespan' protocol appears unsupported" en logs anteriores
    # con "TypeError: 'FastMCP' object is not callable" es contradictorio.
    # Si no es llamable, no puede ni intentar el lifespan.
    # Pero si FastMCP es una Starlette app, SÍ soporta lifespan.

    # Vamos a simplificar y confiar en que Uvicorn maneje la instancia mcp_application.
    # La clave es que la instancia `mcp` en `app.server` DEBE ser la aplicación ASGI.
    return mcp_application


# Obtenemos la aplicación de red.
# Esto se hace a nivel de módulo para que Uvicorn con --reload pueda importarla.
# La cadena de importación para uvicorn sería "app.__main__:network_app_to_run"
network_app_to_run = create_network_app()

def main_network():
    """Run the MCP server as a network service using Uvicorn"""
    host = os.environ.get("HASS_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("HASS_MCP_PORT", "8008"))
    # DESACTIVAR RELOAD para esta prueba y simplificar
    reload_uvicorn = False # os.environ.get("HASS_MCP_RELOAD", "false").lower() == "true"
    log_level_uvicorn = os.environ.get("HASS_MCP_LOG_LEVEL", "info").lower()

    print(f"Running Hass-MCP server as a network service on {host}:{port}")
    if reload_uvicorn:
        print("Uvicorn reload enabled.")

    # Usamos la instancia network_app_to_run directamente
    uvicorn.run(
        network_app_to_run,
        host=host,
        port=port,
        reload=reload_uvicorn, # Estará a False para esta prueba
        log_level=log_level_uvicorn,
        lifespan="on" # Forzar a Uvicorn a usar el ciclo de vida, aunque debería ser auto.
                      # Si la app lo soporta (Starlette lo hace), se usará.
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
