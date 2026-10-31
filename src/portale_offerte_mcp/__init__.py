"""Open data del Portale Offerte (ARERA / Acquirente Unico) come server MCP."""

__version__ = "0.1.0"


def main() -> None:
    from .cli import main as _main

    _main()
