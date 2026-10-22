"""Model backends: Ollama on this machine, or (stand-in for now) the hosted Gemini API.

Contract the rest of the code relies on:
    generate(prompt: str) -> str
    embed(texts: list[str]) -> list[list[float]]
The Snapdragon NPU backends (Genie, onnxruntime-qnn) will be two more functions with these signatures.
"""
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODEL = os.environ.get("NYAYA_GEMINI_MODEL", "gemini-2.5-flash")


class BackendUnavailable(RuntimeError):
    """The local model server is not reachable; the message is shown to the advocate."""


def _post(host, path, body, timeout):
    # Case text must never leave the machine, so only loopback addresses are allowed
    if urlparse(host).hostname not in LOCAL_HOSTS:
        raise ValueError(f"model host must be local, got {host}")
    req = urllib.request.Request(host.rstrip("/") + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError) as e:
        raise BackendUnavailable(f"Ollama is not answering at {host} ({e}). Start it and pull the model.")


def ollama_generate(model="llama3.2:3b", host="http://127.0.0.1:11434", timeout=300):
    def generate(prompt):
        body = {"model": model, "prompt": prompt, "format": "json", "stream": False,
                "options": {"temperature": 0}}
        return _post(host, "/api/generate", body, timeout)["response"]
    return generate


def ollama_embed(model="all-minilm", host="http://127.0.0.1:11434", timeout=120):
    def embed(texts):
        return _post(host, "/api/embed", {"model": model, "input": texts}, timeout)["embeddings"]
    return embed


MAX_WAIT = 90  # seconds worth waiting on a rate limit before telling the advocate


def _retry_after(message):
    # Google's errors say "Please retry in 2m7.28s" or "retry in 35.1s"; returns whole seconds, 0 if absent
    m = re.search(r"retry in (?:(\d+)m)?([\d.]+)s", message or "")
    return int(int(m.group(1) or 0) * 60 + float(m.group(2))) + 1 if m else 0


def gemini_generate(model=GEMINI_MODEL, key=None, timeout=120, retries=5):
    # ponytail: sends paragraph text to Google, which breaks "case files never leave the laptop".
    # A stand-in until Ollama is set up: fictional cases only. Used only while GEMINI_API_KEY is set.
    key = key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise BackendUnavailable("GEMINI_API_KEY is not set.")
    url = GEMINI_URL + model + ":generateContent"

    config = {"temperature": 0, "responseMimeType": "application/json"}
    if "2.5" in model:
        config["thinkingConfig"] = {"thinkingBudget": 0}  # extraction needs no reasoning; thinking made each call ~10 s

    def generate(prompt):
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}).encode()
        for attempt in range(retries):
            req = urllib.request.Request(url, body, {"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.load(r)
                break
            except urllib.error.HTTPError as e:
                detail = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
                wait = _retry_after(detail)
                if e.code == 429 and wait > MAX_WAIT:  # the free daily quota, not a per-minute limit
                    raise BackendUnavailable(
                        f"Gemini free quota used up for {model}; Google says retry in {wait // 60} min. "
                        f"Wait, set NYAYA_GEMINI_MODEL to another model, or use Ollama.")
                if e.code in (429, 500, 503) and attempt < retries - 1:
                    time.sleep(wait or 10)
                    continue
                raise BackendUnavailable(f"Gemini refused the request ({e.code}): {detail[:300]}")
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as e:
                if attempt < retries - 1:  # a dropped connection is usually momentary
                    time.sleep(3)
                    continue
                raise BackendUnavailable(f"Cannot reach Gemini ({e}). Check the internet connection.")
        # A blocked or empty answer comes back as "", which the extractor reports for that paragraph
        parts = (out.get("candidates") or [{}])[0].get("content", {}).get("parts") or [{}]
        return parts[0].get("text", "")
    return generate


def using_gemini():
    return bool(os.environ.get("GEMINI_API_KEY"))
