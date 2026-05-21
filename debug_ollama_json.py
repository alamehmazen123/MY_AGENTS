import asyncio
import httpx
from kernel.config import settings

async def test():
    payload = {
        "model": "deepseek-coder:1.3b",
        "prompt": "What is 2+2? Answer with one word.",
        "stream": False,
        "system": "You are a helpful assistant. Be concise.",
        "keep_alive": 0,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60)
        print(f"status={res.status_code}")
        print(f"headers={dict(res.headers)}")
        text = res.text
        print(f"text_len={len(text)}")
        print(f"text_first_500={text[:500]!r}")
        print(f"text_last_500={text[-500:]!r}")
        try:
            data = res.json()
            print(f"json_ok={data.get('response', '')[:100]!r}")
        except Exception as e:
            print(f"json_error={e}")

if __name__ == "__main__":
    asyncio.run(test())
