#!/usr/bin/env python3
"""
add_one_liners.py

Reads a markdown file containing multiple prompt sections like:

## 1) Title
...prompt text...
---
## 2) Title
...prompt text...

For each section, inserts:
One-line version="...code-safe escaped string..."

The one-line string is the section content excluding the inserted line itself.
"""

import argparse
import json
import re
from pathlib import Path


HEADER_RE = re.compile(r"^##\s+\d+\)\s+.*$", re.M)
DIVIDER_RE = re.compile(r"^\s*---\s*$", re.M)
ONE_LINER_RE = re.compile(r'^\s*One-line version\s*=\s*".*"\s*$', re.M)


def escape_one_line(s: str) -> str:
    """
    Produce a code-safe one-line string:
    - Newlines become literal \n
    - Quotes/backslashes escaped
    Uses JSON escaping rules for correctness.
    Returns the content WITHOUT surrounding quotes.
    """
    s = s.rstrip("\n")
    return json.dumps(s, ensure_ascii=False)[1:-1]


def split_sections(md: str):
    """
    Split markdown into sections starting with '## N) ...'
    Returns list of (header_line, section_body_after_header).
    Keeps everything after the header until the next header or EOF.
    """
    matches = list(HEADER_RE.finditer(md))
    if not matches:
        return []

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        chunk = md[start:end]
        # Separate the first header line from the rest
        first_newline = chunk.find("\n")
        if first_newline == -1:
            header = chunk.strip("\n")
            body = ""
        else:
            header = chunk[:first_newline].rstrip("\n")
            body = chunk[first_newline + 1 :]
        sections.append((header, body))
    return sections


def remove_existing_one_liner(body: str) -> str:
    # Remove any previous One-line version="..."
    return ONE_LINER_RE.sub("", body).lstrip("\n")


def insert_one_liner(body: str, one_liner_value: str) -> str:
    """
    Insert One-line version="..." right before the first --- divider inside the section,
    otherwise append at end.
    """
    insertion = f'\nOne-line version="{one_liner_value}"\n'

    m = DIVIDER_RE.search(body)
    if m:
        # Insert before divider line
        return body[: m.start()] + insertion + "\n" + body[m.start():]
    else:
        # Append at end
        # Ensure trailing newline
        if not body.endswith("\n"):
            body += "\n"
        return body + insertion


def process(md: str) -> str:
    sections = split_sections(md)
    if not sections:
        raise ValueError("No sections found. Expected headers like: ## 1) Title")

    rebuilt = []
    for header, body in sections:
        body_clean = remove_existing_one_liner(body)

        # The prompt text to one-line: header + blank line + body (minus divider if present)
        # We want "above prompt" = everything in the section up to (but not including) the divider.
        divider_match = DIVIDER_RE.search(body_clean)
        prompt_part = body_clean[: divider_match.start()] if divider_match else body_clean
        prompt_text = header + "\n" + prompt_part

        one_liner = escape_one_line(prompt_text)

        new_body = insert_one_liner(body_clean, one_liner)
        rebuilt.append(header + "\n" + new_body)

    return "".join(rebuilt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_md", help="Input markdown file")
    ap.add_argument("-o", "--output", help="Output markdown file (default: overwrite input)")
    args = ap.parse_args()

    in_path = Path(args.input_md)
    md = in_path.read_text(encoding="utf-8")

    out_md = process(md)

    out_path = Path(args.output) if args.output else in_path
    out_path.write_text(out_md, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
