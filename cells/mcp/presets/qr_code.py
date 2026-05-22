"""Generate a QR code for text/URL — returns ASCII art (qrcode)."""
import io

SCHEMA = {
    "name": "qr_code",
    "description": "Generate a QR code (ASCII) for any text or URL.",
    "parameters": {"data": {"type": "string"}},
    "required": ["data"],
}


def handle(args: dict) -> dict:
    data = args.get("data") or args.get("text") or ""
    if not data:
        return {"error": "missing_data"}
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        buf = io.StringIO()
        qr.print_ascii(out=buf)
        return {"data": data, "ascii": buf.getvalue()}
    except Exception as e:
        return {"error": str(e)}
