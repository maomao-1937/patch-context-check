#!/usr/bin/env python3
"""Bounded, read-only checks for plain single-file unified diffs."""
import os
import json
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 20000
MAX_HUNKS = 1000
HEADER = re.compile(r"@@ -([0-9]+)(?:,([0-9]+))? \+([0-9]+)(?:,([0-9]+))? @@(?: .*)?\Z")
DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[1-9¹²³]|LPT[1-9¹²³])\Z", re.I)
HELP = "usage: python patch_context_check.py PATCH BASE\nRead-only plain unified diff check; exit 0 clean, 1 mismatch, 2 invalid.\n"


class Invalid(Exception):
    """Input cannot be checked within this tool's contract."""


def local_path(value):
    """Lexical checks precede all filesystem access."""
    if not value or "\x00" in value or value.startswith(("//", "\\\\")):
        raise Invalid
    if "/" in value and "\\" in value:
        raise Invalid
    tail = value
    if re.match(r"^[A-Za-z]:[/\\]", value):
        tail = value[2:]
    if ":" in tail:
        raise Invalid
    for component in re.split(r"[/\\]", tail):
        if component in ("", ".", ".."):
            continue
        if component.endswith((" ", ".")) or DEVICE.fullmatch(component.split(".", 1)[0]):
            raise Invalid
    return Path(value)


def read_lines(value):
    path = local_path(value)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise Invalid
    if getattr(info, "st_file_attributes", 0) & 0x400:
        raise Invalid
    if info.st_size > MAX_BYTES:
        raise Invalid
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise Invalid
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise Invalid
    text = data.decode("utf-8")
    if text.startswith("\ufeff") or "\x00" in text:
        raise Invalid
    text = text.replace("\r\n", "\n")
    if "\r" in text:
        raise Invalid
    lines = text.split("\n") if text else []
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) > MAX_LINES:
        raise Invalid
    return lines


def number(value, default=1):
    if value is None:
        return default
    if len(value) > 5:
        raise Invalid
    result = int(value)
    if result > 40000:
        raise Invalid
    return result


def parse(lines, base_length):
    if len(lines) < 3 or not lines[0].startswith("--- ") or not lines[1].startswith("+++ "):
        raise Invalid
    if not lines[0][4:] or not lines[1][4:]:
        raise Invalid
    hunks = []
    position = 2
    delta = 0
    previous_start = -1
    previous_end = 0
    while position < len(lines):
        match = HEADER.fullmatch(lines[position])
        if match is None or len(hunks) >= MAX_HUNKS:
            raise Invalid
        old_start, old_count, new_start, new_count = map(number, match.groups())
        if old_count > MAX_LINES or new_count > MAX_LINES or old_count + new_count == 0:
            raise Invalid
        if (old_count and old_start == 0) or (new_count and new_start == 0):
            raise Invalid
        old_index = old_start - 1 if old_count else old_start
        new_index = new_start - 1 if new_count else new_start
        if old_start <= previous_start or old_index < previous_end or new_index != old_index + delta:
            raise Invalid
        if old_index > base_length or old_index + old_count > base_length:
            raise Invalid
        position += 1
        old_seen = new_seen = 0
        old_lines = []
        while position < len(lines) and not lines[position].startswith("@@"):
            line = lines[position]
            if old_seen == old_count and new_seen == new_count:
                raise Invalid
            if not line or line[0] not in " +-":
                raise Invalid
            if line[0] in " -":
                old_lines.append((old_index + old_seen, position + 1, line[1:]))
                old_seen += 1
            if line[0] in " +":
                new_seen += 1
            if old_seen > old_count or new_seen > new_count:
                raise Invalid
            position += 1
        if (old_seen, new_seen) != (old_count, new_count):
            raise Invalid
        hunks.append(old_lines)
        previous_start = old_start
        previous_end = old_index + old_count
        delta += new_count - old_count
    return hunks


def check(patch, base):
    hunks = parse(patch, len(base))
    for ordinal, lines in enumerate(hunks, 1):
        for base_index, patch_line, expected in lines:
            if base[base_index] != expected:
                return 1, {"code": "MISMATCH", "file": 1, "hunk": ordinal,
                           "patch_line": patch_line, "base_line": base_index + 1}
    return 0, {"code": "CLEAN", "files": 1, "hunks": len(hunks)}


def emit(message):
    try:
        sys.stdout.write(message if isinstance(message, str) else json.dumps(message, sort_keys=True) + "\n")
        sys.stdout.flush()
    except (OSError, ValueError):
        # Disable interpreter shutdown flushing of a broken/closed pipe.
        sys.stdout = None


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if args in (["--help"], ["-h"]):
        emit(HELP)
        return 0
    if len(args) != 2:
        emit({"code": "INVALID"})
        return 2
    try:
        # Validate both names before opening either input.
        local_path(args[0])
        local_path(args[1])
        result, message = check(read_lines(args[0]), read_lines(args[1]))
    except (Invalid, OSError, UnicodeError, ValueError, OverflowError):
        result, message = 2, {"code": "INVALID"}
    emit(message)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
