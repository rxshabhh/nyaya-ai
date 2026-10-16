"""Encrypted case vault.

Layout (nothing on disk is readable without the passphrase):
    vault.json      KDF settings and the data key, encrypted with a key derived from the passphrase
    manifest.enc    document names and metadata, encrypted with the data key
    files/<id>.enc  one encrypted document per random id
"""
import base64
import json
import os
import secrets
import unicodedata
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .parse import build_paras

DEFAULT_KDF = {"time": 3, "memory_kib": 65536, "parallelism": 4}  # Argon2id, 64 MiB
MIN_PASSPHRASE = 8
AAD_KEY, AAD_MANIFEST, AAD_FILE = b"nyaya-v1:key", b"nyaya-v1:manifest", b"nyaya-v1:file:"


class VaultError(Exception):
    pass


class WrongPassphrase(VaultError):
    pass


class CorruptVault(VaultError):
    pass


def _b64(b):
    return base64.b64encode(b).decode()


def _seal(key, data, aad):
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, data, aad)


def _unseal(key, blob, aad):  # raises InvalidTag on a wrong key, tampering, or a swapped file
    return AESGCM(key).decrypt(blob[:12], blob[12:], aad)


def _write(path, data):  # write then rename, so a crash never leaves a half-written file
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _derive(passphrase, kdf):
    # NFKC so the same passphrase typed on another keyboard or OS still matches
    secret = unicodedata.normalize("NFKC", passphrase).encode("utf-8")
    return hash_secret_raw(secret, base64.b64decode(kdf["salt"]), time_cost=kdf["time"],
                           memory_cost=kdf["memory_kib"], parallelism=kdf["parallelism"],
                           hash_len=32, type=Type.ID)


def _check(passphrase):
    if len(passphrase) < MIN_PASSPHRASE:
        raise VaultError(f"passphrase must be at least {MIN_PASSPHRASE} characters")


class Vault:
    def __init__(self, path, header, key, manifest):
        self.path, self.header, self.key, self.manifest = path, header, key, manifest

    @classmethod
    def create(cls, path, passphrase, kdf=None):
        path = Path(path)
        if path.exists() and any(path.iterdir()):
            raise VaultError("folder is not empty")
        _check(passphrase)
        (path / "files").mkdir(parents=True, exist_ok=True)
        header = {"version": 1, "kdf": {**DEFAULT_KDF, **(kdf or {}), "alg": "argon2id",
                                        "salt": _b64(os.urandom(16))}}
        vault = cls(path, header, os.urandom(32), {"documents": {}})
        vault._save_header(passphrase)
        vault._save_manifest()
        return vault

    @classmethod
    def open(cls, path, passphrase):
        path = Path(path)
        try:
            header = json.loads((path / "vault.json").read_text(encoding="utf-8"))
            wrapped = base64.b64decode(header["wrapped_key"])
        except (OSError, ValueError, KeyError):
            raise VaultError("not a Nyaya vault")
        try:
            key = _unseal(_derive(passphrase, header["kdf"]), wrapped, AAD_KEY)
        except InvalidTag:  # the only way to learn the passphrase is wrong: the GCM tag fails
            raise WrongPassphrase("wrong passphrase")
        try:
            manifest = json.loads(_unseal(key, (path / "manifest.enc").read_bytes(), AAD_MANIFEST))
        except (InvalidTag, OSError, ValueError):
            raise CorruptVault("the case index is damaged")
        return cls(path, header, key, manifest)

    def _save_header(self, passphrase):
        kek = _derive(passphrase, self.header["kdf"])
        self.header["wrapped_key"] = _b64(_seal(kek, self.key, AAD_KEY))
        _write(self.path / "vault.json", json.dumps(self.header, indent=2).encode())

    def _save_manifest(self):
        _write(self.path / "manifest.enc", _seal(self.key, json.dumps(self.manifest).encode(), AAD_MANIFEST))

    def documents(self):
        return {i: dict(m) for i, m in self.manifest["documents"].items()}

    def add_document(self, name, data, meta=None):
        if any(m["name"] == name for m in self.manifest["documents"].values()):
            raise VaultError(f"a document named {name} is already in this case")
        doc_id = secrets.token_hex(16)
        _write(self.path / "files" / f"{doc_id}.enc", _seal(self.key, data, AAD_FILE + doc_id.encode()))
        self.manifest["documents"][doc_id] = {"name": name, **(meta or {})}
        self._save_manifest()  # file first, index second: a crash leaves an unreferenced file, never a dangling entry
        return doc_id

    def read(self, doc_id):
        meta = self.manifest["documents"].get(doc_id)
        if meta is None:
            raise VaultError("no such document")
        try:
            blob = (self.path / "files" / f"{doc_id}.enc").read_bytes()
            return _unseal(self.key, blob, AAD_FILE + doc_id.encode())
        except (InvalidTag, OSError):
            raise CorruptVault(f"{meta['name']} is missing or failed its integrity check")

    def remove(self, doc_id):
        if self.manifest["documents"].pop(doc_id, None) is None:
            raise VaultError("no such document")
        self._save_manifest()
        (self.path / "files" / f"{doc_id}.enc").unlink(missing_ok=True)

    def change_passphrase(self, new):
        # Only the wrapped data key is rewritten; the documents stay as they are
        _check(new)
        self.header["kdf"]["salt"] = _b64(os.urandom(16))
        self._save_header(new)

    def paras(self):
        # Parse straight from decrypted bytes in memory; no plaintext touches disk
        return build_paras({m["name"]: self.read(i) for i, m in self.manifest["documents"].items()})
