"""
KynicOS — Registro de runtime compartido.

Un unico sitio donde vive el agent loop vivo y el session manager, para que los
canales (Telegram, WhatsApp) los consuman sin importarlos de `app.main`.

Por que existe: con `python -m app.main`, el arranque corre como `__main__`. Un
`from app.main import _agent_loop` dentro de un handler NO devuelve el de la
instancia viva: importa el archivo una segunda vez, creando un modulo nuevo en
el que `_agent_loop` es None. Eso producia "❌ Agent loop no iniciado" en cada
mensaje libre, mientras los logs decian "ConciergeAgentLoop (KYNIKOS) OK".
"""

from typing import Any, Optional

_agent_loop: Optional[Any] = None
_session_manager: Optional[Any] = None


def set_runtime(agent_loop: Any, session_manager: Any) -> None:
    """Lo llama el lifespan de app.main cuando las instancias ya existen."""
    global _agent_loop, _session_manager
    _agent_loop = agent_loop
    _session_manager = session_manager


def get_agent_loop() -> Optional[Any]:
    return _agent_loop


def get_session_manager() -> Optional[Any]:
    return _session_manager


def clear_runtime() -> None:
    """En el apagado, para no dejar referencias a objetos muertos."""
    global _agent_loop, _session_manager
    _agent_loop = None
    _session_manager = None
