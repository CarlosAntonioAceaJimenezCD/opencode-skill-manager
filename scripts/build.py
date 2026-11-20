#!/usr/bin/env python3
"""Genera el paquete publicable de skill-manager.

Salida en dist/:
  index.json                          catálogo HTTP de OpenCode
  skill-manager/                      árbol que descarga OpenCode
  opencode-skill-manager-<ver>.zip    paquete para instalar a mano

Uso:
  python3 scripts/build.py            regenera dist/
  python3 scripts/build.py --check    falla si dist/ no coincide con la fuente
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ID = "skill-manager"
SOURCE = ROOT / "skills" / SKILL_ID
DIST = ROOT / "dist"
EXCLUDED_DIRS = {"__pycache__", ".git"}
EXCLUDED_FILES = {".DS_Store"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read_version() -> str:
    path = ROOT / "VERSION"
    if not path.exists():
        fail("falta VERSION")
    version = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"VERSION no es semver: {version!r}")
    return version


def yaml_field(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def validate() -> None:
    skill_md = SOURCE / "SKILL.md"
    if not skill_md.exists():
        fail(f"falta {skill_md.relative_to(ROOT)}")

    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        fail("SKILL.md no tiene frontmatter")

    frontmatter = match.group(1)
    name = yaml_field(frontmatter, "name")
    description = yaml_field(frontmatter, "description")

    if not name:
        fail("el frontmatter no tiene name")
    if name != SKILL_ID:
        fail(f"name={name!r} no coincide con la carpeta {SKILL_ID!r}")
    if not NAME_RE.fullmatch(name) or not 1 <= len(name) <= 64:
        fail(f"name no es un ID portable: {name!r}")
    if not description:
        fail("el frontmatter no tiene description")
    if len(description) > 1024:
        fail(f"description demasiado larga: {len(description)} caracteres")

    for path in SOURCE.rglob("*"):
        if path.is_symlink():
            fail(f"symlink no permitido: {path.relative_to(SOURCE)}")


def skill_files() -> list[Path]:
    files = []
    for path in SOURCE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SOURCE)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if rel.name in EXCLUDED_FILES or rel.suffix == ".pyc":
            continue
        files.append(rel)
    files.sort(key=lambda p: p.as_posix())
    if Path("SKILL.md") not in files:
        fail("la lista de archivos no incluye SKILL.md")
    return files


def write_index(dest: Path, version: str, files: list[Path]) -> None:
    index = {
        "skills": [
            {
                "name": SKILL_ID,
                "version": version,
                "files": [p.as_posix() for p in files],
            }
        ]
    }
    (dest / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def make_zip(path: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in files:
            info = zipfile.ZipInfo(f"{SKILL_ID}/{rel.as_posix()}", (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o755 << 16
            archive.writestr(info, (SOURCE / rel).read_bytes())


def build(dest: Path, version: str) -> None:
    files = skill_files()
    skill_dest = dest / SKILL_ID
    for rel in files:
        target = skill_dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / rel, target)
    write_index(dest, version, files)
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    make_zip(dest / f"opencode-skill-manager-{version}.zip", files)


def snapshot(root: Path) -> dict[str, bytes]:
    """Huella lógica: compara contenido, no la compresión del zip."""
    if not root.exists():
        fail(f"no existe {root.relative_to(ROOT)}")
    state: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                for member in sorted(archive.namelist()):
                    state[f"{rel}!{member}"] = archive.read(member)
        else:
            state[rel] = path.read_bytes()
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="verifica dist/ sin modificarlo"
    )
    args = parser.parse_args()

    validate()
    version = read_version()

    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        staging = Path(tmp) / "dist"
        staging.mkdir()
        build(staging, version)

        if args.check:
            current = snapshot(DIST)
            expected = snapshot(staging)
            if current != expected:
                only_disk = sorted(set(current) - set(expected))
                only_build = sorted(set(expected) - set(current))
                changed = sorted(
                    key for key in set(current) & set(expected)
                    if current[key] != expected[key]
                )
                for label, items in (
                    ("sobra en dist/", only_disk),
                    ("falta en dist/", only_build),
                    ("contenido distinto", changed),
                ):
                    if items:
                        print(f"{label}: {', '.join(items)}", file=sys.stderr)
                fail("dist/ está desactualizado; ejecutá python3 scripts/build.py")
            print(f"dist/ al día: {SKILL_ID} {version}")
            return

        if DIST.exists():
            shutil.rmtree(DIST)
        shutil.copytree(staging, DIST)

    files = skill_files()
    print(f"paquete: {SKILL_ID} {version}")
    print(f"  archivos: {len(files)}")
    for rel in files:
        print(f"    {rel.as_posix()}")
    print(f"  catálogo: {(DIST / 'index.json').relative_to(ROOT)}")
    print(f"  zip:      {(DIST / f'opencode-skill-manager-{version}.zip').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
