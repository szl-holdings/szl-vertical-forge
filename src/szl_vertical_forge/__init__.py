"""Build and verify deterministic vertical artifacts from audited configs."""

from pathlib import Path
from typing import Any

VERTICALS_PATH = Path(__file__).with_name("verticals.json")
__version__ = "0.2.1"
__all__ = [
    "VERTICALS_PATH",
    "forge",
    "load_verticals",
    "validate_vertical",
    "verify_output",
    "verify_receipt",
    "write_output",
]


def forge(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .forge import forge as implementation

    return implementation(*args, **kwargs)


def load_verticals(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    from .forge import load_verticals as implementation

    return implementation(*args, **kwargs)


def validate_vertical(*args: Any, **kwargs: Any) -> list[str]:
    from .forge import validate_vertical as implementation

    return implementation(*args, **kwargs)


def verify_output(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .forge import verify_output as implementation

    return implementation(*args, **kwargs)


def verify_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .forge import verify_receipt as implementation

    return implementation(*args, **kwargs)


def write_output(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .forge import write_output as implementation

    return implementation(*args, **kwargs)
