"""Tests for ``c2 fetch-original``'s extraction path and the
``c2.original`` integrity guard."""

from __future__ import annotations

import hashlib
import io

import pycdlib
import pytest
import typer

from c2.commands.fetch_original import (RAW_SECTOR, extract_ps_exe_from_iso,
                                        strip_raw_sectors)
from c2 import original as original_mod

PAYLOAD = b"MZ" + bytes(range(256)) * 20   # fake PS.EXE payload


@pytest.fixture()
def synthetic_iso(tmp_path):
    """A real ISO9660 image (built by pycdlib) containing HD/PS.EXE."""
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1)
    iso.add_directory("/HD")
    iso.add_fp(io.BytesIO(PAYLOAD), len(PAYLOAD), "/HD/PS.EXE;1")
    path = tmp_path / "cd.iso"
    iso.write(str(path))
    iso.close()
    return path


_SYNC = b"\x00" + b"\xff" * 10 + b"\x00"


def _to_raw_2352(iso_bytes: bytes, mode: int) -> bytes:
    out = bytearray()
    for off in range(0, len(iso_bytes), 2048):
        if mode == 1:      # 12 sync + 3 addr + mode + 2048 + 288 ecc
            out += _SYNC + b"\x00\x00\x00\x01" + iso_bytes[off:off + 2048] + b"\x00" * 288
        else:              # 12 sync + 3 addr + mode + 8 subheader + 2048 + 280
            out += (_SYNC + b"\x00\x00\x00\x02" + b"\x00" * 8
                    + iso_bytes[off:off + 2048] + b"\x00" * 280)
    return bytes(out)


def test_extract_from_iso(synthetic_iso):
    assert extract_ps_exe_from_iso(synthetic_iso) == PAYLOAD


@pytest.mark.parametrize("mode", [1, 2])
def test_strip_raw_sectors_roundtrip(synthetic_iso, tmp_path, mode):
    raw = _to_raw_2352(synthetic_iso.read_bytes(), mode)
    assert len(raw) % RAW_SECTOR == 0
    stripped = tmp_path / "stripped.iso"
    with stripped.open("wb") as dst:
        strip_raw_sectors(io.BytesIO(raw), dst, len(raw))
    assert stripped.read_bytes() == synthetic_iso.read_bytes()
    assert extract_ps_exe_from_iso(stripped) == PAYLOAD


def test_strip_raw_sectors_rejects_garbage():
    with pytest.raises(ValueError, match="sync"):
        strip_raw_sectors(io.BytesIO(b"\x00" * RAW_SECTOR), io.BytesIO(),
                          RAW_SECTOR)


def test_strip_raw_sectors_rejects_bad_size():
    with pytest.raises(ValueError, match="multiple"):
        strip_raw_sectors(io.BytesIO(b""), io.BytesIO(), RAW_SECTOR + 1)


def test_extract_missing_file(tmp_path):
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1)
    path = tmp_path / "empty.iso"
    iso.write(str(path))
    iso.close()
    with pytest.raises(Exception):
        extract_ps_exe_from_iso(path)


# ── the c2.original guard ────────────────────────────────────────────────────

def test_ensure_original_missing(tmp_path, capsys):
    with pytest.raises(typer.Exit):
        original_mod.ensure_original(tmp_path / "PS.EXE")
    err = capsys.readouterr().err
    assert "fetch-original" in err and "README" in err


def test_ensure_original_mismatch(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("C2_ALLOW_ORIGINAL_MISMATCH", raising=False)
    exe = tmp_path / "PS.EXE"
    exe.write_bytes(b"not the original")
    with pytest.raises(typer.Exit):
        original_mod.ensure_original(exe)
    err = capsys.readouterr().err
    assert "sha256" in err and "expected" in err


def test_ensure_original_mismatch_override(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("C2_ALLOW_ORIGINAL_MISMATCH", "1")
    exe = tmp_path / "PS.EXE"
    exe.write_bytes(b"not the original")
    assert original_mod.ensure_original(exe) == exe
    assert "warning" in capsys.readouterr().err


def test_ensure_original_accepts_pinned_hash(tmp_path, monkeypatch):
    exe = tmp_path / "PS.EXE"
    exe.write_bytes(PAYLOAD)
    pinned = hashlib.sha256(PAYLOAD).hexdigest()
    monkeypatch.setattr(original_mod, "expected_original_hash", lambda: pinned)
    assert original_mod.ensure_original(exe) == exe
