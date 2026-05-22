"""Geolocate an IP address (city, region, country, ISP) — no API key. Empty = your own IP."""

SCHEMA = {
    "name": "ip_geolocation",
    "description": "Look up location/ISP for an IP address (leave empty for your own).",
    "parameters": {"ip": {"type": "string"}},
    "required": [],
}


def handle(args: dict) -> dict:
    ip = (args.get("ip") or "").strip()
    try:
        import httpx
        with httpx.Client(timeout=15) as client:
            r = client.get(f"http://ip-api.com/json/{ip}")
            data = r.json()
        if data.get("status") == "fail":
            return {"error": data.get("message", "lookup_failed"), "ip": ip}
        return data
    except Exception as e:
        return {"error": str(e), "ip": ip}
