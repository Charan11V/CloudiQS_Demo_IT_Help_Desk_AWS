#!/usr/bin/env python3
"""Build an ARM64 Python CodeZip for AgentCore Runtime (no Docker/QEMU)."""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

from common import RUNTIME_DIR, STATE_DIR, run

OUT_DIR = STATE_DIR / "build"
PKG_DIR = OUT_DIR / "deployment_package"
ZIP_PATH = OUT_DIR / "deployment_package.zip"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if PKG_DIR.exists():
        shutil.rmtree(PKG_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    PKG_DIR.mkdir(parents=True)

    req = RUNTIME_DIR / "requirements.txt"
    # Pre-download Linux arm64 wheels — AgentCore microVMs are Graviton.
    run(
        [
            "uv",
            "pip",
            "install",
            "--python-platform",
            "aarch64-manylinux2014",
            "--python-version",
            "3.13",
            "--target",
            str(PKG_DIR),
            "--only-binary",
            ":all:",
            "-r",
            str(req),
        ]
    )

    # Copy application sources to package root (AgentCore mounts at /var/task).
    for name in ("main.py", "VERSION", "requirements.txt", "pyproject.toml"):
        src = RUNTIME_DIR / name
        if src.exists():
            shutil.copy2(src, PKG_DIR / name)
    helio_src = RUNTIME_DIR / "helio_agent"
    helio_dst = PKG_DIR / "helio_agent"
    if helio_dst.exists():
        shutil.rmtree(helio_dst)
    shutil.copytree(
        helio_src,
        helio_dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )

    # Strip bytecode caches that may be host-arch incompatible.
    for p in PKG_DIR.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in PKG_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(PKG_DIR).as_posix())

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Created {ZIP_PATH} ({size_mb:.1f} MiB)")
    if size_mb > 240:
        print("WARNING: approaching AgentCore CodeZip 250 MiB limit", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
