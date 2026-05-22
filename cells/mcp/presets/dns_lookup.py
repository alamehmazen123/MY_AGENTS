"""Resolve a hostname to IP addresses (and reverse lookup) using the standard library."""
import socket

SCHEMA = {
    "name": "dns_lookup",
    "description": "Resolve a hostname to its IP address(es); includes reverse DNS.",
    "parameters": {"host": {"type": "string"}},
    "required": ["host"],
}


def handle(args: dict) -> dict:
    host = (args.get("host") or args.get("hostname") or "").strip()
    if not host:
        return {"error": "missing_host"}
    # Accept a full URL too.
    host = host.split("//")[-1].split("/")[0]
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({i[4][0] for i in infos})
        result = {"host": host, "ips": ips}
        try:
            result["reverse"] = socket.gethostbyaddr(ips[0])[0]
        except Exception:
            result["reverse"] = None
        return result
    except Exception as e:
        return {"error": str(e), "host": host}
