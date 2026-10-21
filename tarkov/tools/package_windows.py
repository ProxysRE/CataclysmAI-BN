"""Validate an installed Windows build, smoke-test it and create a portable ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def package(bn: Path, dist: Path, output: Path) -> None:
    if platform.system() != "Windows":
        raise SystemExit("The Windows smoke checks must run on Windows")
    baseline = json.loads((ROOT / "baseline.json").read_text(encoding="utf-8"))
    bn_sha = subprocess.check_output(["git", "-C", str(bn), "rev-parse", "HEAD"], text=True).strip()
    project_sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    if bn_sha != baseline["commit"] or not baseline["engine_changes"]:
        raise SystemExit("Unexpected BN baseline or missing engine-patch declaration")
    expected_line = "MAPBUFFER_REGISTRY.get( current_dimension_id_ ).set_pocket_info( pocket_info );"
    if expected_line not in (bn / "src/savegame.cpp").read_text(encoding="utf-8"):
        raise SystemExit("The mandatory bounds patch is missing from the built source")
    executable = dist / "cataclysm-bn-tiles.exe"
    with executable.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise SystemExit("The installed executable is not a Windows PE file")
    source_mod = ROOT / "mods/trkv_raid_core"
    for source in source_mod.rglob("*"):
        if source.is_file():
            installed = dist / "data/mods/trkv_raid_core" / source.relative_to(source_mod)
            if not installed.is_file() or digest(source) != digest(installed):
                raise SystemExit(f"Missing or stale installed mod file: {installed}")
    shader_names = [p.stem for p in (bn / "src/shaders").glob("*.hlsl")]
    if not shader_names:
        raise SystemExit("No shader sources found in pinned BN")
    for name in shader_names:
        for suffix in ("spv", "dxil"):
            shader = dist / "data/shaders" / f"{name}.{suffix}"
            if not shader.is_file() or shader.stat().st_size == 0:
                raise SystemExit(f"Missing installed shader: {shader}")
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    # Run against the INSTALLED data, not the source checkout.
    with tempfile.TemporaryDirectory(prefix="trkv-windows-smoke-") as scratch:
        try:
            for name, args, timeout in (("version", ["--version"], 60),
                                        ("check-mods", ["--check-mods", "trkv_raid_core"], 900)):
                log = output / f"windows-{name}.log"
                try:
                    with log.open("w", encoding="utf-8") as stream:
                        subprocess.run([str(executable), *args, "--userdir", scratch],
                                       cwd=dist, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, check=True, timeout=timeout)
                finally:
                    print(log.read_text(encoding="utf-8", errors="replace")[-12000:], flush=True)
        finally:
            debug = Path(scratch) / "config/debug.log"
            if debug.is_file():
                shutil.copyfile(debug, output / "windows-debug.log")
    shutil.copytree(ROOT, dist / "project-source/tarkov",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(ROOT / "README.md", dist / "TARKOV_README.md")
    shutil.copyfile(ROOT / "docs/WINDOWS_VALIDATION.md", dist / "WINDOWS_VALIDATION.md")
    metadata = {
        "schema": 1, "prototype": baseline["prototype"], "bn_sha": bn_sha,
        "project_sha": project_sha, "platform": platform.platform(),
        "executable_sha256": digest(executable),
        "patches": {p.name: digest(p) for p in sorted((ROOT / "patches").glob("*.patch"))},
        "automated_checks": ["installed --version", "installed --check-mods trkv_raid_core"],
        "windows_ui_verified": False,
    }
    (dist / "TARKOV_BUILD.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    archive_base = output / f"Tarkov_DEV01_Windows_x64_{project_sha[:8]}"
    if archive_base.with_suffix(".zip").exists():
        raise SystemExit("Refusing to replace an existing Windows archive")
    archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=dist.parent, base_dir=dist.name))
    archive.with_suffix(".zip.sha256").write_text(f"{digest(archive)}  {archive.name}\n", encoding="ascii")
    print(f"PASS installed Windows smoke checks; package: {archive.name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bn", type=Path)
    parser.add_argument("dist", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(args.bn.resolve(), args.dist.resolve(), args.output.resolve())
