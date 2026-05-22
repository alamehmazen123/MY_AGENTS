"""Current weather and forecast for a city (open-meteo, no API key)."""

SCHEMA = {
    "name": "weather",
    "description": "Current weather + daily forecast for a city (no API key).",
    "parameters": {"city": {"type": "string"}},
    "required": ["city"],
}


def handle(args: dict) -> dict:
    city = (args.get("city") or args.get("location") or "").strip()
    if not city:
        return {"error": "missing_city"}
    try:
        import httpx
        with httpx.Client(timeout=15) as client:
            g = client.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1})
            results = (g.json() or {}).get("results") if g.status_code == 200 else None
            if not results:
                return {"error": "city_not_found", "city": city}
            loc = results[0]
            w = client.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "current_weather": True,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            })
            wj = w.json()
        return {
            "location": f"{loc.get('name')}, {loc.get('country', '')}".strip(", "),
            "current_weather": wj.get("current_weather"),
            "daily": wj.get("daily"),
            "units": wj.get("current_weather_units") or wj.get("daily_units"),
        }
    except Exception as e:
        return {"error": str(e), "city": city}
