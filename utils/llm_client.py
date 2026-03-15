import os, json, http.client
from dotenv import load_dotenv
from config.constants import ANTHROPIC_MODEL
load_dotenv()

KEY = os.getenv("ANTHROPIC_API_KEY", "")

def call_llm(system_prompt, user_message, max_tokens=300):
    if not KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    payload = json.dumps({
        "model": ANTHROPIC_MODEL, "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    })
    headers = {
        "Content-Type": "application/json",
        "x-api-key": KEY,
        "anthropic-version": "2023-06-01",
        "Content-Length": str(len(payload.encode())),
    }
    conn = http.client.HTTPSConnection("api.anthropic.com", timeout=60)
    conn.request("POST", "/v1/messages", body=payload, headers=headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    conn.close()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    return "\n".join(b["text"] for b in data.get("content", []) if b.get("type") == "text").strip()
