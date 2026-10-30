from .client import (
    DEFAULT_BASE_URL,
    Client,
    NotFoundError,
    Proverb,
    ZubanDarazError,
)

__all__ = ["Client", "Proverb", "ZubanDarazError", "NotFoundError", "DEFAULT_BASE_URL"]
__version__ = "0.1.0"
