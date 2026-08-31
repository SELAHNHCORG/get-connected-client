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

from importlib.metadata import version

__title__ = "get-connected-client"
__version__ = version("get-connected-client")
__author__ = "Brian Kohan"
__license__ = "MIT"
__copyright__ = "Copyright 2026 SELAH NHC"

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
