"""Install the platform-independent Russian catalog from a pinned official BN release."""
import argparse
import gettext
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

SOURCE = {
    "release": "2026-10-19",
    "url": "https://github.com/cataclysmbn/Cataclysm-BN/releases/download/2026-10-19/cbn-linux-curses-x64-2026-10-19.tar.gz",
    "archive_sha256": "1fbbc50783f4b9c6511d9fe67e2f7546c42e7e87e7edb5b48a36d724ae253fd0",
}
SUFFIX = "lang/mo/ru_RU/LC_MESSAGES/cataclysm-bn.mo"


def install(archive: Path, bn: Path) -> None:
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != SOURCE["archive_sha256"]:
        raise SystemExit("Official translation archive SHA256 mismatch")
    with tarfile.open(archive, "r:gz") as bundle:
        matches = [entry for entry in bundle if entry.isfile() and entry.name.endswith("/" + SUFFIX)]
        if len(matches) != 1:
            raise SystemExit("Expected exactly one official Russian catalog")
        data = bundle.extractfile(matches[0]).read()
    catalog = gettext.GNUTranslations(io.BytesIO(data))
    if len(catalog._catalog) < 1000 or catalog.gettext("Yes") == "Yes":
        raise SystemExit("Official Russian catalog is missing usable translations")
    target = bn / SUFFIX
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    source = {**SOURCE, "catalog_sha256": hashlib.sha256(data).hexdigest()}
    (bn / "lang/mo/ru_RU/SOURCE.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(f"Installed official Russian catalog: {len(catalog._catalog)} entries", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bn", type=Path)
    parser.add_argument("--archive", type=Path, help="Use an already downloaded official archive")
    args = parser.parse_args()
    if args.archive:
        install(args.archive, args.bn)
    else:
        with tempfile.TemporaryDirectory(prefix="trkv-bn-translation-") as scratch:
            archive = Path(scratch) / "official.tar.gz"
            with urllib.request.urlopen(SOURCE["url"], timeout=120) as response, archive.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            install(archive, args.bn)
