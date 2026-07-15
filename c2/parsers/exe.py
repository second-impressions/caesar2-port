"""DOS/4GW Professional executable structure parsing.

Parses the layered PS.EXE format:
  1. MZ DOS stub (real-mode bootstrap)
  2. BW #1: VMM.EXP (DOS/4GW Virtual Memory Manager)
  3. BW #2: 4GWPRO.EXP (DOS/4GW Professional extender kernel)
  4. LE: Caesar II game code (32-bit flat model)

Binary format references:
  - Open Watcom v2: bld/watcom/h/exe16m.h (dos16m_exe_header)
  - Open Watcom v2: bld/watcom/h/exeflat.h (LE header)
  - Open Watcom v2: bld/exedump/c/d16mexe.c (BW chain traversal)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO


# ── Constants ────────────────────────────────────────────────────────────────

MZ_SIGNATURE = 0x5A4D   # 'MZ'
BW_SIGNATURE = 0x5742   # 'BW'
LE_SIGNATURE = 0x454C   # 'LE'

DOS16M_HEADER_SIZE = 176  # sizeof(dos16m_exe_header) as laid out in file


# ── MZ Header ────────────────────────────────────────────────────────────────


@dataclass
class MZHeader:
    """Standard DOS MZ executable header (first 28 bytes)."""

    signature: int
    last_page_bytes: int
    pages_in_file: int
    num_relocs: int
    header_paragraphs: int
    min_alloc: int
    max_alloc: int
    init_ss: int
    init_sp: int
    checksum: int
    init_ip: int
    init_cs: int
    reloc_offset: int
    overlay_num: int

    @classmethod
    def read(cls, f: BinaryIO) -> MZHeader:
        data = f.read(28)
        if len(data) < 28:
            raise ValueError("File too small for MZ header")
        fields = struct.unpack("<14H", data)
        hdr = cls(*fields)
        if hdr.signature != MZ_SIGNATURE:
            raise ValueError(f"Not an MZ executable: signature 0x{hdr.signature:04X}")
        return hdr

    @property
    def load_module_size(self) -> int:
        """Total size of the MZ load module."""
        size = self.pages_in_file * 512
        if self.last_page_bytes:
            size = size - 512 + self.last_page_bytes
        return size


# ── BW (DOS/16M) Header ─────────────────────────────────────────────────────


@dataclass
class GDTEntry:
    """A single GDT selector entry."""

    selector: int
    file_size: int
    memory_size: int
    file_offset: int
    access: int
    is_code: bool
    is_present: bool
    is_zero_init: bool

    @property
    def access_str(self) -> str:
        if self.is_code:
            return "ER" if (self.access & 0x02) else "EO"
        else:
            return "RW" if (self.access & 0x02) else "RO"


@dataclass
class BWHeader:
    """DOS/16M (BW) executable header."""

    file_offset: int
    signature: int
    last_page_bytes: int
    pages_in_file: int
    min_alloc: int
    max_alloc: int
    stack_seg: int
    stack_ptr: int
    first_reloc_sel: int
    init_ip: int
    code_seg: int
    runtime_gdt_size: int
    makepm_version: int
    next_header_pos: int
    cv_info_offset: int
    last_sel_used: int
    gdtimage_size: int
    first_selector: int
    exp_flags: int
    exp_path: str
    gdt_entries: list[GDTEntry] = field(default_factory=list)

    @classmethod
    def read(cls, f: BinaryIO, file_offset: int) -> BWHeader:
        f.seek(file_offset)
        data = f.read(176)
        if len(data) < 128:
            raise ValueError(
                f"File too small for BW header at offset 0x{file_offset:X}"
            )

        sig = struct.unpack_from("<H", data, 0)[0]
        if sig != BW_SIGNATURE:
            raise ValueError(
                f"Not a BW header at 0x{file_offset:X}: signature 0x{sig:04X}"
            )

        last_page = struct.unpack_from("<H", data, 2)[0]
        pages = struct.unpack_from("<H", data, 4)[0]
        min_a, max_a = struct.unpack_from("<2H", data, 10)[0:2]
        stack_seg, stack_ptr = struct.unpack_from("<2H", data, 14)[0:2]
        first_reloc = struct.unpack_from("<H", data, 18)[0]
        init_ip = struct.unpack_from("<H", data, 20)[0]
        code_seg = struct.unpack_from("<H", data, 22)[0]
        gdt_size = struct.unpack_from("<H", data, 24)[0]
        makepm_ver = struct.unpack_from("<H", data, 26)[0]
        next_hdr = struct.unpack_from("<I", data, 28)[0]
        cv_off = struct.unpack_from("<I", data, 32)[0]
        last_sel = struct.unpack_from("<H", data, 36)[0]
        exp_flags = struct.unpack_from("<H", data, 52)[0]
        gdtimage_size = struct.unpack_from("<H", data, 56)[0]
        first_sel = struct.unpack_from("<H", data, 58)[0]
        if first_sel == 0:
            first_sel = 0x80

        if len(data) >= 176:
            exp_path_bytes = data[112:176]
            exp_path = exp_path_bytes.split(b"\x00")[0].decode(
                "ascii", errors="replace"
            )
        else:
            exp_path = ""

        hdr = cls(
            file_offset=file_offset,
            signature=sig,
            last_page_bytes=last_page,
            pages_in_file=pages,
            min_alloc=min_a,
            max_alloc=max_a,
            stack_seg=stack_seg,
            stack_ptr=stack_ptr,
            first_reloc_sel=first_reloc,
            init_ip=init_ip,
            code_seg=code_seg,
            runtime_gdt_size=gdt_size,
            makepm_version=makepm_ver,
            next_header_pos=next_hdr,
            cv_info_offset=cv_off,
            last_sel_used=last_sel,
            gdtimage_size=gdtimage_size,
            first_selector=first_sel,
            exp_flags=exp_flags,
            exp_path=exp_path,
        )

        # Calculate selector count
        if last_sel:
            sel_count = (last_sel - first_sel) // 8 + 1
        else:
            sel_count = (gdtimage_size + 1) // 8 - 17

        segdata_offset = (
            file_offset + DOS16M_HEADER_SIZE + 1 + gdtimage_size - 16 * 8
        )

        gdt_read_offset = file_offset + DOS16M_HEADER_SIZE
        f.seek(gdt_read_offset)

        current_file_offset = segdata_offset
        selector = first_sel

        for _ in range(sel_count):
            gdt_data = f.read(8)
            if len(gdt_data) < 8:
                break

            gdtlen, gdtaddr, gdtaddr_hi, gdtaccess, gdtreserved = struct.unpack(
                "<HHBBh", gdt_data
            )

            file_size = (gdtlen + 1) if gdtlen else 0
            mem_size = (gdtreserved & 0x1FFF) << 4
            if mem_size == 0:
                mem_size = file_size

            access_nibble = gdtaccess & 0x0F
            is_code = (access_nibble & 0x08) != 0
            is_present = (gdtaccess & 0x80) != 0
            is_zero_init = (gdtreserved & 0x2000) != 0

            entry = GDTEntry(
                selector=selector,
                file_size=file_size,
                memory_size=mem_size,
                file_offset=current_file_offset,
                access=access_nibble,
                is_code=is_code,
                is_present=is_present,
                is_zero_init=is_zero_init,
            )
            hdr.gdt_entries.append(entry)
            current_file_offset += file_size
            selector += 8

        return hdr

    @property
    def glu_version(self) -> str:
        major = self.makepm_version // 100 - 10
        minor = self.makepm_version % 100
        return f"{major}.{minor:02d}"


# ── LE (Linear Executable) Header ───────────────────────────────────────────


@dataclass
class LEObject:
    """An LE object table entry (24 bytes each)."""

    index: int
    virtual_size: int
    reloc_base_addr: int
    flags: int
    page_table_index: int
    num_pages: int

    @property
    def is_code(self) -> bool:
        return bool(self.flags & 0x0004)

    @property
    def is_readable(self) -> bool:
        return bool(self.flags & 0x0001)

    @property
    def is_writable(self) -> bool:
        return bool(self.flags & 0x0002)

    @property
    def is_executable(self) -> bool:
        return bool(self.flags & 0x0004)

    @property
    def is_32bit(self) -> bool:
        return bool(self.flags & 0x2000)

    @property
    def type_str(self) -> str:
        if self.is_executable:
            return "code"
        elif self.is_writable:
            return "data"
        else:
            return "rodata"

    @property
    def flags_str(self) -> str:
        r = "R" if self.is_readable else "-"
        w = "W" if self.is_writable else "-"
        x = "X" if self.is_executable else "-"
        bits = "32bit" if self.is_32bit else "16bit"
        return f"{r}{w}{x} {bits}"


@dataclass
class LEHeader:
    """LE (Linear Executable) header."""

    mz_offset: int
    le_offset: int
    cpu_type: int
    os_type: int
    module_flags: int
    num_pages: int
    eip_object: int
    eip: int
    esp_object: int
    esp: int
    page_size: int
    last_page_size: int
    num_objects: int
    object_table_offset: int
    data_pages_offset: int
    fixup_section_size: int
    objects: list[LEObject] = field(default_factory=list)

    @classmethod
    def read(cls, f: BinaryIO, mz_offset: int) -> LEHeader:
        """Read LE header from file. mz_offset is the MZ stub start."""
        f.seek(mz_offset)
        mz_sig = struct.unpack("<H", f.read(2))[0]
        if mz_sig != MZ_SIGNATURE:
            raise ValueError(
                f"Expected MZ at 0x{mz_offset:X}, got 0x{mz_sig:04X}"
            )

        f.seek(mz_offset + 0x3C)
        e_lfanew = struct.unpack("<I", f.read(4))[0]
        le_offset = mz_offset + e_lfanew

        f.seek(le_offset)
        le_sig = struct.unpack("<H", f.read(2))[0]
        if le_sig != LE_SIGNATURE:
            raise ValueError(
                f"Expected LE at 0x{le_offset:X}, got 0x{le_sig:04X}"
            )

        f.seek(le_offset)
        data = f.read(196)

        cpu_type = struct.unpack_from("<H", data, 8)[0]
        os_type = struct.unpack_from("<H", data, 10)[0]
        module_flags = struct.unpack_from("<I", data, 16)[0]
        num_pages = struct.unpack_from("<I", data, 20)[0]
        eip_object = struct.unpack_from("<I", data, 24)[0]
        eip = struct.unpack_from("<I", data, 28)[0]
        esp_object = struct.unpack_from("<I", data, 32)[0]
        esp = struct.unpack_from("<I", data, 36)[0]
        page_size = struct.unpack_from("<I", data, 40)[0]
        last_page_size = struct.unpack_from("<I", data, 44)[0]
        fixup_section_size = struct.unpack_from("<I", data, 48)[0]
        object_table_offset = struct.unpack_from("<I", data, 64)[0]
        num_objects = struct.unpack_from("<I", data, 68)[0]
        data_pages_offset = struct.unpack_from("<I", data, 128)[0]

        hdr = cls(
            mz_offset=mz_offset,
            le_offset=le_offset,
            cpu_type=cpu_type,
            os_type=os_type,
            module_flags=module_flags,
            num_pages=num_pages,
            eip_object=eip_object,
            eip=eip,
            esp_object=esp_object,
            esp=esp,
            page_size=page_size,
            last_page_size=last_page_size,
            num_objects=num_objects,
            object_table_offset=object_table_offset,
            data_pages_offset=data_pages_offset,
            fixup_section_size=fixup_section_size,
        )

        obj_table_abs = le_offset + object_table_offset
        f.seek(obj_table_abs)
        for i in range(num_objects):
            obj_data = f.read(24)
            if len(obj_data) < 24:
                break
            vsize = struct.unpack_from("<I", obj_data, 0)[0]
            reloc_base = struct.unpack_from("<I", obj_data, 4)[0]
            flags = struct.unpack_from("<I", obj_data, 8)[0]
            page_idx = struct.unpack_from("<I", obj_data, 12)[0]
            num_page_entries = struct.unpack_from("<I", obj_data, 16)[0]

            hdr.objects.append(
                LEObject(
                    index=i + 1,
                    virtual_size=vsize,
                    reloc_base_addr=reloc_base,
                    flags=flags,
                    page_table_index=page_idx,
                    num_pages=num_page_entries,
                )
            )

        return hdr

    @property
    def data_pages_abs(self) -> int:
        """Absolute file offset of the data pages."""
        return self.mz_offset + self.data_pages_offset

    def object_file_offset(self, obj: LEObject) -> int:
        """Get the absolute file offset of an object's data pages."""
        return self.data_pages_abs + (obj.page_table_index - 1) * self.page_size

    def object_file_size(self, obj: LEObject) -> int:
        """Get the actual file size of an object's data."""
        if obj.num_pages == 0:
            return 0
        full_pages = obj.num_pages - 1
        last_page = self.page_size
        last_page_idx = obj.page_table_index + obj.num_pages - 1
        if last_page_idx == self.num_pages:
            last_page = self.last_page_size
        return full_pages * self.page_size + last_page

    @property
    def entry_address(self) -> int | None:
        """Absolute entry point address (base + EIP offset)."""
        if self.eip_object <= len(self.objects):
            obj = self.objects[self.eip_object - 1]
            return obj.reloc_base_addr + self.eip
        return None

    @property
    def stack_address(self) -> int | None:
        """Absolute stack address (base + ESP offset)."""
        if self.esp_object <= len(self.objects):
            obj = self.objects[self.esp_object - 1]
            return obj.reloc_base_addr + self.esp
        return None


# ── DOS/4GW chain traversal ─────────────────────────────────────────────────


def find_bw_headers(f: BinaryIO, mz: MZHeader) -> list[BWHeader]:
    """Find all BW headers in the file by following the chain."""
    headers = []

    first_bw_offset = mz.load_module_size
    f.seek(first_bw_offset)
    sig = struct.unpack("<H", f.read(2))[0]
    if sig != BW_SIGNATURE:
        raise ValueError(
            f"Expected BW header at offset 0x{first_bw_offset:X}, "
            f"got 0x{sig:04X}"
        )

    bw = BWHeader.read(f, first_bw_offset)
    headers.append(bw)

    while bw.next_header_pos != 0:
        next_offset = bw.next_header_pos
        f.seek(next_offset)
        sig_data = f.read(2)
        if len(sig_data) < 2:
            break
        sig = struct.unpack("<H", sig_data)[0]
        if sig != BW_SIGNATURE:
            break
        bw = BWHeader.read(f, next_offset)
        headers.append(bw)

    return headers


def find_le_header(f: BinaryIO, bw_headers: list[BWHeader]) -> LEHeader | None:
    """Find the LE executable by following the last BW's next_header_pos."""
    if not bw_headers:
        return None

    last_bw = bw_headers[-1]
    if last_bw.next_header_pos == 0:
        return None

    le_mz_offset = last_bw.next_header_pos

    f.seek(le_mz_offset)
    sig_data = f.read(2)
    if len(sig_data) < 2:
        return None
    sig = struct.unpack("<H", sig_data)[0]
    if sig != MZ_SIGNATURE:
        return None

    return LEHeader.read(f, le_mz_offset)


def parse_exe(filepath: Path) -> tuple[MZHeader, list[BWHeader], LEHeader]:
    """Parse an executable with an LE payload.

    Handles two layouts:
      - DOS/4GW Professional: MZ → BW chain → MZ stub → LE  (original PS.EXE)
      - Watcom wlink output:  MZ stub → LE                   (recompiled)

    Returns (mz_header, bw_headers, le_header).
    Raises ValueError if no LE header is found.
    """
    with open(filepath, "rb") as f:
        mz = MZHeader.read(f)

        # Check if a BW chain follows the MZ load module
        first_bw_offset = mz.load_module_size
        f.seek(first_bw_offset)
        sig_data = f.read(2)
        has_bw = (
            len(sig_data) >= 2
            and struct.unpack("<H", sig_data)[0] == BW_SIGNATURE
        )

        if has_bw:
            bw_headers = find_bw_headers(f, mz)
            le = find_le_header(f, bw_headers)
        else:
            # No BW chain — MZ stub points directly at LE via e_lfanew
            bw_headers = []
            le = LEHeader.read(f, 0)

    if le is None:
        raise ValueError("No LE executable found")

    return mz, bw_headers, le


def extract_le_objects(filepath: Path, le: LEHeader, output_dir: Path) -> None:
    """Extract LE object data as flat binary files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(filepath, "rb") as f:
        for obj in le.objects:
            file_offset = le.object_file_offset(obj)
            file_size = le.object_file_size(obj)

            if obj.type_str == "code":
                bin_name = "le_code.bin"
            elif obj.index == 2:
                bin_name = "le_data.bin"
            else:
                bin_name = f"le_obj{obj.index}.bin"

            f.seek(file_offset)
            data = f.read(file_size)

            # Pad to virtual size if needed (BSS portion)
            if obj.virtual_size > file_size:
                data += b"\x00" * (obj.virtual_size - file_size)

            bin_path = output_dir / bin_name
            bin_path.write_bytes(data)
