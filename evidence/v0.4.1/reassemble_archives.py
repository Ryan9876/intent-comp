#!/usr/bin/env python3
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parent
ARCHIVES = {
    "reviewed-evidence-archive.zip": [
        "reviewed-evidence-archive.zip.b64.part01",
        "reviewed-evidence-archive.zip.b64.part02",
        "reviewed-evidence-archive.zip.b64.part03",
    ],
    "private-audit-archive.zip": [
        "private-audit-archive.zip.b64.part01",
        "private-audit-archive.zip.b64.part02",
        "private-audit-archive.zip.b64.part03",
        "private-audit-archive.zip.b64.part04",
        "private-audit-archive.zip.b64.part05",
        "private-audit-archive.zip.b64.part06",
        "private-audit-archive.zip.b64.part07",
        "private-audit-archive.zip.b64.part08",
    ],
}

for output_name, part_names in ARCHIVES.items():
    encoded = "".join((ROOT / name).read_text(encoding="ascii").strip() for name in part_names)
    (ROOT / output_name).write_bytes(base64.b64decode(encoded))
    print(f"restored {output_name}")
