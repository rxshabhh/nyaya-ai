"""CPU model backends: Ollama on this machine.

Contract the rest of the code relies on:
    generate(prompt: str) -> str
    embed(texts: list[str]) -> list[list[float]]
The Snapdragon NPU backends (Genie, onnxruntime-qnn) will be two more functions with these signatures.
"""
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


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
