r"""
::

                               ██████╗ ███████╗████████╗
                              ██╔════╝ ██╔════╝╚══██╔══╝
                              ██║  ███╗█████╗     ██║
                              ██║   ██║██╔══╝     ██║
                              ╚██████╔╝███████╗   ██║
                               ╚═════╝ ╚══════╝   ╚═╝

     ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗███████╗██████╗
    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗
    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   █████╗  ██║  ██║
    ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   ██╔══╝  ██║  ██║
    ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   ███████╗██████╔╝
     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═════╝

                     ██████╗██╗     ██╗███████╗███╗   ██╗████████╗
                    ██╔════╝██║     ██║██╔════╝████╗  ██║╚══██╔══╝
                    ██║     ██║     ██║█████╗  ██╔██╗ ██║   ██║
                    ██║     ██║     ██║██╔══╝  ██║╚██╗██║   ██║
                    ╚██████╗███████╗██║███████╗██║ ╚████║   ██║
                     ╚═════╝╚══════╝╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝

A typed Python client (and optional CLI) for Galaxy Digital's Get Connected API
"""

__title__ = "get-connected-client"
__version__ = "2026.8.17"
__author__ = "Brian Kohan"
__license__ = ""
__copyright__ = "Copyright 2026 Brian Kohan"

from .client import GalaxyClient
from .exceptions import (
    AuthError,
    GalaxyConnectionError,
    GalaxyError,
    GalaxyHTTPError,
    MissingAPIKeyError,
    NotFoundError,
    RateLimitError,
    ReadOnlyError,
    ValidationFailedError,
)

__all__ = [
    "AuthError",
    "GalaxyClient",
    "GalaxyConnectionError",
    "GalaxyError",
    "GalaxyHTTPError",
    "MissingAPIKeyError",
    "NotFoundError",
    "RateLimitError",
    "ReadOnlyError",
    "ValidationFailedError",
]
