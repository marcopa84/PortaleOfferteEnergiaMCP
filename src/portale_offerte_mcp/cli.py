from __future__ import annotations

import argparse

from mcp.server.transport_security import TransportSecuritySettings

from . import __version__


def security_settings(port: int, public_hosts: list[str], allow_any_host: bool) -> TransportSecuritySettings:
    if allow_any_host:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"]
    for h in public_hosts:
        hosts += [h, f"{h}:*"]
    origins = [f"http://{h}" for h in hosts[:3]] + [f"https://{h}" for h in public_hosts]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="portale-offerte-mcp",
        description="Server MCP sugli open data del Portale Offerte. Trasporto predefinito: stdio (Claude Desktop/Code).",
    )
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                    help="stdio per i client locali; http (Streamable HTTP) per client remoti come ChatGPT")
    ap.add_argument("--host", default="127.0.0.1", help="solo http; lasciare 127.0.0.1 e usare un tunnel")
    ap.add_argument("--port", type=int, default=8000, help="solo http")
    ap.add_argument("--public-host", action="append", default=[], metavar="HOSTNAME",
                    help="solo http: accetta questo header Host, es. l'hostname del tunnel (ripetibile)")
    ap.add_argument("--allow-any-host", action="store_true",
                    help="solo http: disattiva i controlli Host/Origin (comodo con tunnel a hostname casuale)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    from .server import mcp

    if args.transport == "stdio":
        mcp.run("stdio")
    else:
        mcp.run(
            "streamable-http",
            host=args.host,
            port=args.port,
            transport_security=security_settings(args.port, args.public_host, args.allow_any_host),
        )
