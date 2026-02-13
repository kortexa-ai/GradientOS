#!/usr/bin/env python3
"""
Extract A6-EC drive fault/alarm/bus-fault code tables from the vendor manual PDF.

Source PDF (in-repo):
  docs/resources/A6-EC_series_servo_drive_manual.pdf

This script extracts (Chapter 10 / Troubleshooting):
  - Table 10-1: List of factory fault codes (Er.. / ErC..)
  - Table 10-2: List of factory alarm codes (ALF.. / xxnr)
  - Table 10-3: List of bus fault codes (0x603F)

Outputs:
  - JSON: machine-readable mapping for tooling
  - Markdown: human-readable reference
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Optional


def _pdftotext_layout(pdf_path: str) -> list[str]:
    try:
        raw = subprocess.check_output(
            ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, "-"],
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        raise RuntimeError("pdftotext not found. Install poppler-utils.") from e
    return raw.decode("utf-8", errors="replace").splitlines()


def _find_range(lines: list[str], start_pat: str, end_pat: str) -> tuple[int, int]:
    start: Optional[int] = None
    for i, ln in enumerate(lines):
        if re.search(start_pat, ln):
            start = i
            break
    if start is None:
        raise RuntimeError(f"Start pattern not found: {start_pat!r}")

    end: Optional[int] = None
    for j in range(start + 1, len(lines)):
        if re.search(end_pat, lines[j]):
            end = j
            break
    if end is None:
        raise RuntimeError(f"End pattern not found: {end_pat!r}")
    return start, end


def _is_header_or_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.isdigit():
        return True
    noisy_substrings = (
        "Table 10-",
        "Troubleshooting",
        "Fault Code",
        "Fault Name",
        "Alarm Name",
        "Alarm Code",
        "Bus Fault",
        "(203F)",
        "(603F)",
        "Fault Group",
        "Alarm Group",
        "Bus Fault SN",
        "Bus Fault Code",
        "Bus Fault Name",
        "Contents",
    )
    return any(x in s for x in noisy_substrings)


def _collapse_ws(s: str) -> str:
    return " ".join(s.split())


def _parse_fault_table(lines: list[str]) -> list[dict[str, Any]]:
    # Example row:
    #   Er01.0  Mismatch of software versions  0x010  0x6100  Non-resettable
    # Some rows have '-' for bus fault code.
    row_re = re.compile(
        r"^\s*(?:(?P<class>Class\s+\d+)\s+)?"
        r"(?P<code>Er[A-Za-z0-9]{1,4}\.[0-9]{1,2})\s+"
        r"(?P<name>.*?)\s+"
        r"(?P<code_203f>0x[0-9A-Fa-f]+)\s+"
        r"(?P<bus_603f>0x[0-9A-Fa-f]+|-)\s+"
        r"(?P<reset>Resettable|Non-resettable)\s*$"
    )

    cur_class: Optional[str] = None
    pending: list[str] = []
    cur: Optional[dict[str, Any]] = None
    out: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal cur
        if cur is None:
            return
        cur["name"] = _collapse_ws(cur.get("name", ""))
        out.append(cur)
        cur = None

    for raw in lines:
        s = raw.strip()
        if not s:
            flush()
            pending = []
            continue

        # Class marker lines (sometimes inserted between rows without a blank line).
        # Some PDFs place the class label on its own line ("Class 1"), others may
        # prefix a wrapped description line ("Class 3 <text...>").
        m_class_prefix = re.match(r"^\s*(Class\s+\d+)\b(.*)$", raw)
        if m_class_prefix and not row_re.match(raw):
            flush()
            pending = []
            cur_class = m_class_prefix.group(1)
            rest = m_class_prefix.group(2).strip()
            if rest:
                pending.append(rest)
            continue

        if _is_header_or_noise(raw):
            flush()
            pending = []
            continue

        m = row_re.match(raw)
        if m:
            flush()
            code = m.group("code")
            name = (m.group("name") or "").strip()
            if pending:
                name = " ".join(pending + ([name] if name else []))
                pending = []

            row_class = m.group("class") or cur_class
            bus_603f = m.group("bus_603f")
            cur = {
                "code": code,
                "class": row_class,
                "name": name,
                "fault_code_203f": m.group("code_203f").upper(),
                "bus_fault_code_603f": None if bus_603f == "-" else bus_603f.upper(),
                "resettable": (m.group("reset") == "Resettable"),
            }
            if m.group("class"):
                cur_class = m.group("class")
            continue

        # Continuation line: attach to current entry if present, else treat as pending.
        if cur is not None:
            cur["name"] = (cur.get("name", "") + " " + s).strip()
        else:
            pending.append(s)

    flush()
    return out


def _parse_alarm_table(lines: list[str]) -> list[dict[str, Any]]:
    # Example row:
    #   ALF0.0  Emergency stop alarm  0x0F00  0x0F00  Resettable
    # Special row:
    #   xxnr   Servo not ready        0xFFFF      -   Resettable
    row_re = re.compile(
        r"^\s*(?:(?P<class>Class\s+\d+)\s+)?"
        r"(?P<code>ALF[A-Za-z0-9]{1,2}\.[0-9]{1,2}|xxnr)\s+"
        r"(?P<name>.*?)\s+"
        r"(?P<code_203f>0x[0-9A-Fa-f]+)\s+"
        r"(?P<bus_603f>0x[0-9A-Fa-f]+|-)\s+"
        r"(?P<reset>Resettable|Non-resettable)\s*$"
    )

    cur_class: Optional[str] = None
    pending: list[str] = []
    cur: Optional[dict[str, Any]] = None
    out: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal cur
        if cur is None:
            return
        cur["name"] = _collapse_ws(cur.get("name", ""))
        out.append(cur)
        cur = None

    for raw in lines:
        s = raw.strip()
        if not s:
            flush()
            pending = []
            continue

        m_class_prefix = re.match(r"^\s*(Class\s+\d+)\b(.*)$", raw)
        if m_class_prefix and not row_re.match(raw):
            flush()
            pending = []
            cur_class = m_class_prefix.group(1)
            rest = m_class_prefix.group(2).strip()
            if rest:
                pending.append(rest)
            continue

        if _is_header_or_noise(raw):
            flush()
            pending = []
            continue

        m = row_re.match(raw)
        if m:
            flush()
            code = m.group("code")
            name = (m.group("name") or "").strip()
            if pending:
                name = " ".join(pending + ([name] if name else []))
                pending = []

            row_class = m.group("class") or cur_class
            bus_603f = m.group("bus_603f")
            cur = {
                "code": code,
                "class": row_class,
                "name": name,
                "alarm_code_203f": m.group("code_203f").upper(),
                "bus_fault_code_603f": None if bus_603f == "-" else bus_603f.upper(),
                "resettable": (m.group("reset") == "Resettable"),
            }
            if m.group("class"):
                cur_class = m.group("class")
            continue

        if cur is not None:
            cur["name"] = (cur.get("name", "") + " " + s).strip()
        else:
            pending.append(s)

    flush()
    return out


def _parse_bus_fault_table(lines: list[str]) -> list[dict[str, Any]]:
    # Example row:
    #   21  0x8700  Synchronization controller
    row_re = re.compile(r"^\s*(?P<sn>\d+)\s+(?P<code>0x[0-9A-Fa-f]{4})\s+(?P<name>.+?)\s*$")
    out: list[dict[str, Any]] = []
    for raw in lines:
        if _is_header_or_noise(raw):
            continue
        m = row_re.match(raw)
        if not m:
            continue
        out.append(
            {
                "sn": int(m.group("sn")),
                "bus_fault_code_603f": m.group("code").upper(),
                "name": _collapse_ws(m.group("name")),
            }
        )
    return out


def _to_json_obj(pdf_path: str) -> dict[str, Any]:
    lines = _pdftotext_layout(pdf_path)

    t10_1_s, t10_1_e = _find_range(lines, r"Table\s+10-1", r"Table\s+10-2")
    t10_2_s, t10_2_e = _find_range(lines, r"Table\s+10-2", r"Table\s+10-3")
    t10_3_s, t10_3_e = _find_range(lines, r"Table\s+10-3", r"Table\s+10-4")

    faults = _parse_fault_table(lines[t10_1_s:t10_1_e])
    alarms = _parse_alarm_table(lines[t10_2_s:t10_2_e])
    bus = _parse_bus_fault_table(lines[t10_3_s:t10_3_e])

    fault_by_code = {e["code"]: e for e in faults}
    alarm_by_code = {e["code"]: e for e in alarms}
    bus_by_code = {e["bus_fault_code_603f"]: e for e in bus}

    return {
        "source_pdf": os.path.normpath(pdf_path),
        "tables": {
            "fault_codes": fault_by_code,
            "alarm_codes": alarm_by_code,
            "bus_fault_codes": bus_by_code,
        },
        "counts": {
            "fault_codes": len(fault_by_code),
            "alarm_codes": len(alarm_by_code),
            "bus_fault_codes": len(bus_by_code),
        },
        "notes": [
            "Extracted via pdftotext -layout; table formatting is best-effort.",
            "Bus fault codes correspond to the drive's CiA402 error code object 0x603F.",
            "For authoritative wording and context, refer to the PDF manual.",
        ],
    }


def _markdown_from_json(obj: dict[str, Any]) -> str:
    tables = obj.get("tables", {})
    faults: dict[str, Any] = tables.get("fault_codes", {})
    alarms: dict[str, Any] = tables.get("alarm_codes", {})
    bus: dict[str, Any] = tables.get("bus_fault_codes", {})

    out: list[str] = []
    out.append("## A6-EC fault/alarm/bus-fault code reference")
    out.append("")
    out.append(f"Source: `{obj.get('source_pdf','')}` (Chapter 10 tables 10-1, 10-2, 10-3).")
    out.append("")

    out.append("### Bus fault codes (`0x603F`)")
    out.append("")
    out.append("| 0x603F | Name |")
    out.append("|---:|---|")
    for code in sorted(bus.keys()):
        name = str(bus[code].get("name", "")).strip()
        out.append(f"| `{code}` | {name} |")
    out.append("")

    out.append("### Factory alarm codes (display code → meaning)")
    out.append("")
    out.append("| Code | Meaning | Bus fault (`0x603F`) | Resettable | Class |")
    out.append("|---|---|---|---:|---|")
    for code in sorted(alarms.keys()):
        e = alarms[code]
        meaning = str(e.get("name", "")).strip()
        bus_code = e.get("bus_fault_code_603f") or "-"
        reset = "yes" if e.get("resettable") else "no"
        cls = e.get("class") or "-"
        out.append(f"| `{code}` | {meaning} | `{bus_code}` | {reset} | {cls} |")
    out.append("")

    out.append("### Factory fault codes (display code → meaning)")
    out.append("")
    out.append("| Code | Meaning | Bus fault (`0x603F`) | Resettable | Class |")
    out.append("|---|---|---|---:|---|")
    for code in sorted(faults.keys()):
        e = faults[code]
        meaning = str(e.get("name", "")).strip()
        bus_code = e.get("bus_fault_code_603f") or "-"
        reset = "yes" if e.get("resettable") else "no"
        cls = e.get("class") or "-"
        out.append(f"| `{code}` | {meaning} | `{bus_code}` | {reset} | {cls} |")
    out.append("")

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract A6-EC manual code tables")
    ap.add_argument(
        "--pdf",
        default="docs/resources/A6-EC_series_servo_drive_manual.pdf",
        help="Path to A6-EC manual PDF",
    )
    ap.add_argument("--format", choices=("json", "md"), default="json", help="Output format")
    ap.add_argument("--out", default="-", help="Output path ('-' for stdout)")
    args = ap.parse_args()

    obj = _to_json_obj(args.pdf)
    if args.format == "md":
        output = _markdown_from_json(obj)
    else:
        output = json.dumps(obj, indent=2, sort_keys=True) + "\n"

    if args.out == "-":
        sys.stdout.write(output)
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

