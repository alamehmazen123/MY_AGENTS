"""Convert units (length, mass, temperature) and currencies (no API key)."""

SCHEMA = {
    "name": "convert_units",
    "description": "Convert length/mass/temperature units and currencies. params: value, from, to.",
    "parameters": {"value": {"type": "number"}, "from": {"type": "string"}, "to": {"type": "string"}},
    "required": ["value", "from", "to"],
}

_LENGTH = {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144}
_MASS = {"kg": 1.0, "g": 0.001, "mg": 1e-6, "lb": 0.45359237, "oz": 0.028349523, "t": 1000.0}
_TEMP = {"c", "f", "k"}


def handle(args: dict) -> dict:
    if args.get("value") is None:
        return {"error": "missing_value"}
    frm = (args.get("from") or "").lower().strip()
    to = (args.get("to") or "").lower().strip()
    if not frm or not to:
        return {"error": "missing_from_or_to"}
    try:
        value = float(args["value"])
        if frm in _LENGTH and to in _LENGTH:
            return {"result": value * _LENGTH[frm] / _LENGTH[to], "from": frm, "to": to}
        if frm in _MASS and to in _MASS:
            return {"result": value * _MASS[frm] / _MASS[to], "from": frm, "to": to}
        if frm in _TEMP and to in _TEMP:
            c = value if frm == "c" else (value - 32) * 5 / 9 if frm == "f" else value - 273.15
            out = c if to == "c" else c * 9 / 5 + 32 if to == "f" else c + 273.15
            return {"result": round(out, 4), "from": frm, "to": to}
        # Currency fallback (keyless — Frankfurter / ECB data).
        import httpx
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            r = client.get("https://api.frankfurter.dev/v1/latest",
                           params={"base": frm.upper(), "symbols": to.upper()})
            rate = (r.json().get("rates") or {}).get(to.upper())
        if rate is not None:
            return {"result": round(value * rate, 4), "from": frm.upper(),
                    "to": to.upper(), "rate": rate}
        return {"error": "unsupported_units_or_currency", "from": frm, "to": to}
    except Exception as e:
        return {"error": str(e)}
