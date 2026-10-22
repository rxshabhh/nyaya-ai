"""Case archives (.nyaya): a zip of a vault folder. The vault is already ciphertext, so an archive
leaks nothing. Used by manual export/import and by cloud sync, which uploads exactly these bytes."""
import hashlib
import re
import zipfile
from pathlib import Path

MAX_ARCHIVE = 2 * 1024 ** 3  # unpacked size cap


class ArchiveError(Exception):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def write_archive(src, out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(Path(src).rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(src).as_posix())


def _allowed(name):
    return name in ("vault.json", "manifest.enc") or re.fullmatch(r"(files|state)/[\w.-]+\.enc", name)


def read_archive(fileobj, dest):
    """Unpack into dest after checking every entry name, which also rejects ../ and absolute paths."""
    dest = Path(dest)
    try:
        with zipfile.ZipFile(fileobj) as z:
            names = z.namelist()
            if "vault.json" not in names or not all(_allowed(n) for n in names):
                raise ArchiveError("this is not a Nyaya AI case archive")
            if sum(i.file_size for i in z.infolist()) > MAX_ARCHIVE:
                raise ArchiveError("archive is too large", 413)
            for n in names:
                (dest / n).parent.mkdir(parents=True, exist_ok=True)
                (dest / n).write_bytes(z.read(n))
    except zipfile.BadZipFile:
        raise ArchiveError("this is not a Nyaya AI case archive")


def digest(src):
    """Hash of a vault folder's contents (names and bytes, in order). Equal digests mean no local
    change since the last sync; zip timestamps would make hashing the archive itself unreliable."""
    h = hashlib.sha256()
    for f in sorted(Path(src).rglob("*")):
        if f.is_file():
            h.update(f.relative_to(src).as_posix().encode() + b"\0")
            h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()
