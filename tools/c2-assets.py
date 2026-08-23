#!/usr/bin/env python3
"""Build and verify content-addressed Caesar II asset packs."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

SCHEMA = "second-impressions.caesar2.asset-pack.v1"
CORE_EXTENSIONS = {".PL8", ".WAV", ".DAT", ".256", ".XMI", ".GD8", ".OPL", ".AD"}
MEDIA_DIRS = ("PL8", "RAW", "XMI", "SMK")


def fold(path: str) -> str:
    value = path.replace("\\", "/").strip("/")
    parts = value.split("/")
    if not value or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"unsafe logical path: {path!r}")
    if any(any(ord(c) < 0x20 or ord(c) >= 0x7f for c in p) for p in parts):
        raise ValueError(f"non-ASCII logical path: {path!r}")
    return "/".join(p.upper() for p in parts)


def child_case(root: Path, name: str) -> Path | None:
    if not root.is_dir():
        return None
    exact = root / name
    if exact.exists():
        return exact
    found = sorted((p for p in root.iterdir() if p.name.casefold() == name.casefold()),
                   key=lambda p: (p.name.casefold(), p.name))
    return found[0] if len(found) == 1 else None


def source_layout(source: Path) -> tuple[list[Path], dict[str, list[Path]]]:
    source = source.resolve()
    win = child_case(source, "C2WIN95")
    win_hd = child_case(win, "HD") if win else None
    dos_hd = child_case(source, "HD")
    direct_text = child_case(source, "C2.ENG")
    bases: list[Path]
    media: dict[str, list[Path]] = {name: [] for name in MEDIA_DIRS}
    if win_hd and child_case(win_hd, "C2.ENG"):
        bases = [win_hd]
        if dos_hd:
            bases.append(dos_hd)
        for name in MEDIA_DIRS:
            parent = source if name == "XMI" else win
            directory = child_case(parent, name) if parent else None
            if directory:
                media[name].append(directory)
    elif dos_hd and child_case(dos_hd, "C2.ENG"):
        bases = [dos_hd]
        for name in MEDIA_DIRS:
            directory = child_case(source, name)
            if directory:
                media[name].append(directory)
    elif direct_text:
        bases = [source]
        for name in MEDIA_DIRS:
            directory = child_case(source, name)
            if directory:
                media[name].append(directory)
    else:
        # Component-only directories, notably extracted Mac SMK trees.
        bases = [source]
        if source.name.upper() in MEDIA_DIRS:
            media[source.name.upper()].append(source)
    return bases, media


def files_in(directory: Path):
    if not directory or not directory.is_dir():
        return
    for path in sorted(directory.rglob("*"), key=lambda p: str(p).casefold()):
        if path.is_file():
            yield path


def catalog_source(source: Path) -> dict[str, Path]:
    bases, media = source_layout(source)
    result: dict[str, Path] = {}
    for base in bases:
        for path in files_in(base):
            logical = fold(str(path.relative_to(base)))
            result.setdefault(logical, path)
    for name, directories in media.items():
        for directory in directories:
            for path in files_in(directory):
                logical = fold(f"{name}/{path.relative_to(directory)}")
                result.setdefault(logical, path)
    return result


def component(source: Path, kind: str) -> dict[str, Path]:
    catalog = catalog_source(source)
    selected: dict[str, Path] = {}
    for logical, path in catalog.items():
        ext = Path(logical).suffix.upper()
        if kind == "core" and ext in CORE_EXTENSIONS and logical not in ("C2.ENG", "HELP.ENG"):
            selected[logical] = path
        elif kind == "text" and logical in ("C2.ENG", "HELP.ENG"):
            selected[logical] = path
        elif kind == "speech" and logical.startswith("RAW/") and ext == ".RAW":
            selected[logical] = path
        elif kind == "video" and ext == ".SMK":
            target = "SMK/INTRO.SMK" if Path(logical).name.upper() == "INTRONEW.SMK" else logical
            selected[target] = path
    return selected


def parse_mapping(values: list[str], option: str) -> dict[str, Path]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{option} expects NAME=PATH: {value}")
        name, raw = value.split("=", 1)
        if not name or name in result:
            raise ValueError(f"invalid or duplicate {option} name: {name}")
        path = Path(raw)
        if not path.is_dir():
            raise ValueError(f"{option} path is not a directory: {path}")
        result[name] = path
    return result


def add_objects(components: dict[str, dict[str, Path]]):
    blobs: dict[str, dict] = {}
    refs: dict[str, dict[str, str]] = {}
    for component_name, entries in components.items():
        mapping = {}
        for logical, path in sorted(entries.items()):
            data_hash = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    data_hash.update(chunk)
                    size += len(chunk)
            digest = data_hash.hexdigest()
            previous = blobs.get(digest)
            if previous is not None and previous["size"] != size:
                raise ValueError("SHA-256 collision with different sizes")
            blobs.setdefault(digest, {"size": size, "source": path})
            mapping[logical] = digest
        refs[component_name] = mapping
    return blobs, refs


def build_manifest(core: Path, texts: dict[str, Path], speeches: dict[str, Path],
                   videos: dict[str, Path], default_language: str | None,
                   default_video: str | None):
    components = {"core/default": component(core, "core")}
    for name, path in texts.items():
        components[f"text/{name}"] = component(path, "text")
    for name, path in speeches.items():
        components[f"speech/{name}"] = component(path, "speech")
    for name, path in videos.items():
        components[f"video/{name}"] = component(path, "video")
    if len(components["core/default"]) < 100:
        raise ValueError("core source is incomplete (fewer than 100 runtime files)")
    for name in texts:
        if set(components[f"text/{name}"]) != {"C2.ENG", "HELP.ENG"}:
            raise ValueError(f"text profile {name} lacks C2.ENG or HELP.ENG")
    blobs, refs = add_objects(components)
    digest_ids = {digest: f"{i:08d}.BIN" for i, digest in enumerate(sorted(blobs), 1)}
    object_rows = {
        digest_ids[digest]: {"sha256": digest, "size": row["size"]}
        for digest, row in sorted(blobs.items())
    }
    component_rows = {
        name: {logical: digest_ids[digest] for logical, digest in mapping.items()}
        for name, mapping in refs.items()
    }
    languages = sorted(texts)
    video_names = sorted(videos)
    default_language = default_language or (languages[0] if languages else None)
    default_video = default_video or (video_names[0] if video_names else None)
    if default_language not in texts:
        raise ValueError("default language is not a text profile")
    if default_video is not None and default_video not in videos:
        raise ValueError("default video is not a video profile")
    profiles = {}
    for language in languages:
        selection = ["core/default", f"text/{language}"]
        if language in speeches:
            selection.append(f"speech/{language}")
        if default_video:
            selection.append(f"video/{default_video}")
        profiles[language] = selection
    manifest = {
        "schema": SCHEMA,
        "objects": object_rows,
        "components": component_rows,
        "profiles": profiles,
        "defaults": {"language": default_language, "video": default_video},
    }
    return manifest, blobs, digest_ids


def pack_index(manifest: dict) -> str:
    lines = ["C2PACK1"]
    defaults = manifest["defaults"]
    lines.append(f"DEFAULT_LANGUAGE\t{defaults.get('language') or ''}")
    lines.append(f"DEFAULT_VIDEO\t{defaults.get('video') or ''}")
    for object_name, row in sorted(manifest["objects"].items()):
        lines.append(f"OBJECT\t{object_name}\t{row['size']}\t{row['sha256']}")
    for component_name, entries in sorted(manifest["components"].items()):
        lines.append(f"COMPONENT\t{component_name}")
        for logical, object_name in sorted(entries.items()):
            lines.append(f"FILE\t{logical}\t{object_name}")
    for name, components in sorted(manifest["profiles"].items()):
        lines.append(f"PROFILE\t{name}\t{','.join(components)}")
    lines.append("END")
    return "\n".join(lines) + "\n"


def write_zip(output: Path, manifest: dict, blobs: dict, digest_ids: dict):
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        archive.writestr("C2PACK.JSN", json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                         compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("C2PACK.IDX", pack_index(manifest),
                         compress_type=zipfile.ZIP_DEFLATED)
        for digest in sorted(blobs):
            archive.write(blobs[digest]["source"], f"OBJECTS/{digest_ids[digest]}",
                          compress_type=zipfile.ZIP_DEFLATED)


def write_iso(output: Path, manifest: dict, blobs: dict, digest_ids: dict):
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1, vol_ident="CAESAR2_ASSETS")
    iso.add_directory(iso_path="/OBJECTS")
    with tempfile.TemporaryDirectory(prefix="c2-pack-") as temp:
        manifest_path = Path(temp) / "C2PACK.JSN"
        index_path = Path(temp) / "C2PACK.IDX"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        index_path.write_text(pack_index(manifest))
        iso.add_file(str(manifest_path), iso_path="/C2PACK.JSN;1")
        iso.add_file(str(index_path), iso_path="/C2PACK.IDX;1")
        for digest in sorted(blobs):
            iso.add_file(str(blobs[digest]["source"]),
                         iso_path=f"/OBJECTS/{digest_ids[digest]};1")
        iso.write(str(output))
    iso.close()


def read_pack(path: Path):
    if path.suffix.lower() in (".zip", ".c2assets"):
        archive = zipfile.ZipFile(path)
        raw = archive.read("C2PACK.JSN")
        return json.loads(raw), lambda name: archive.open(f"OBJECTS/{name}"), archive.close
    if path.suffix.lower() == ".iso":
        import pycdlib
        iso = pycdlib.PyCdlib()
        iso.open(str(path))
        manifest = io.BytesIO()
        iso.get_file_from_iso_fp(manifest, iso_path="/C2PACK.JSN;1")
        def opener(name):
            output = io.BytesIO()
            iso.get_file_from_iso_fp(output, iso_path=f"/OBJECTS/{name};1")
            output.seek(0)
            return output
        return json.loads(manifest.getvalue()), opener, iso.close
    raise ValueError("verify accepts .zip/.c2assets/.iso packs")


def verify(path: Path):
    manifest, opener, closer = read_pack(path)
    try:
        if manifest.get("schema") != SCHEMA:
            raise ValueError("unsupported asset-pack schema")
        for object_name, row in manifest["objects"].items():
            digest = hashlib.sha256()
            size = 0
            with opener(object_name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            if size != row["size"] or digest.hexdigest() != row["sha256"]:
                raise ValueError(f"object verification failed: {object_name}")
        for name, entries in manifest["components"].items():
            seen = set()
            for logical, object_name in entries.items():
                key = fold(logical)
                if key in seen or object_name not in manifest["objects"]:
                    raise ValueError(f"invalid component {name}: {logical}")
                seen.add(key)
        return manifest
    finally:
        closer()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("source", type=Path)
    build = sub.add_parser("build")
    build.add_argument("--core", required=True, type=Path)
    build.add_argument("--text", action="append", default=[], metavar="NAME=PATH")
    build.add_argument("--speech", action="append", default=[], metavar="NAME=PATH")
    build.add_argument("--video", action="append", default=[], metavar="NAME=PATH")
    build.add_argument("--default-language")
    build.add_argument("--default-video")
    build.add_argument("--format", choices=("zip", "iso"), default="zip")
    build.add_argument("--output", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("pack", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            catalog = catalog_source(args.source)
            counts = {}
            for name in catalog:
                ext = Path(name).suffix.upper() or "<none>"
                counts[ext] = counts.get(ext, 0) + 1
            print(json.dumps({"files": len(catalog), "extensions": counts}, indent=2, sort_keys=True))
        elif args.command == "build":
            texts = parse_mapping(args.text, "--text")
            speeches = parse_mapping(args.speech, "--speech")
            videos = parse_mapping(args.video, "--video")
            manifest, blobs, ids = build_manifest(args.core, texts, speeches, videos,
                                                   args.default_language, args.default_video)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.format == "zip":
                write_zip(args.output, manifest, blobs, ids)
            else:
                write_iso(args.output, manifest, blobs, ids)
            print(f"wrote {args.output}: {len(blobs)} objects, {args.output.stat().st_size} bytes")
        else:
            manifest = verify(args.pack)
            print(f"verified {args.pack}: {len(manifest['objects'])} objects, {len(manifest['profiles'])} profiles")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
