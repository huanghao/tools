#!/usr/bin/env python3
"""Select specific pages from a PDF and write to a new PDF or stdout.

USAGE
-----
# Write to a file (auto-named if -o is omitted):
  python select_pages.py input.pdf PAGES [-o output.pdf]

# Write to stdout (pipe-friendly):
  python select_pages.py input.pdf PAGES -o -

# Only expand and print the page numbers, no PDF written:
  python select_pages.py input.pdf PAGES --print-only

PAGE EXPRESSION SYNTAX
----------------------
Tokens are separated by commas and/or whitespace.

  3,5,8          individual pages (1-based)
  5-9            inclusive range
  9-53:4         stepped range  — pages 9,13,17,…,53  (also: 9..53..4)
  53-9:-4        reverse stepped — pages 53,49,45,…,9
  range(9,53,4)  explicit range() syntax (same as 9-53:4)
"""

import argparse
import os
import re
import sys
from typing import List

from PyPDF2 import PdfReader, PdfWriter


def parse_pages(pages_expr: str, total_pages: int) -> List[int]:
    """Parse a pages expression into zero-based page indices.

    Input pages are 1-based. Validates all pages are within [1, total_pages].
    """
    if not pages_expr.strip():
        raise ValueError("pages expression cannot be empty")

    selected: List[int] = []
    # Split on whitespace/commas, but not inside parentheses (preserves range(a,b,c) as one token)
    parts = [p.strip() for p in re.split(r"[\s,]+(?![^(]*\))", pages_expr) if p.strip()]

    for part in parts:
        if part.lower().startswith('range(') and part.endswith(')'):
            inner = part[6:-1]
            nums = [n.strip() for n in inner.split(',') if n.strip()]
            if len(nums) != 3 or not all(s.lstrip('-').isdigit() for s in nums):
                raise ValueError(f"Invalid range(...) expression: {part}")
            start, end, step = int(nums[0]), int(nums[1]), int(nums[2])
            selected.extend(_stepped_range(start, end, step, total_pages))
            continue

        m = re.match(r"^(?P<start>-?\d+)[.]{2}(?P<end>-?\d+)[.]{2}(?P<step>-?\d+)$", part)
        if not m:
            m = re.match(r"^(?P<start>-?\d+)\s*-\s*(?P<end>-?\d+)\s*:\s*(?P<step>-?\d+)$", part)
        if m:
            start, end, step = int(m.group('start')), int(m.group('end')), int(m.group('step'))
            selected.extend(_stepped_range(start, end, step, total_pages))
            continue

        if '-' in part:
            start_str, end_str = part.split('-', 1)
            if not start_str.isdigit() or not end_str.isdigit():
                raise ValueError(f"Invalid range: {part}")
            start, end = int(start_str), int(end_str)
            if start > end:
                raise ValueError(f"Invalid range (start > end): {part}")
            selected.extend(_stepped_range(start, end, 1, total_pages))
            continue

        if not part.isdigit():
            raise ValueError(f"Invalid page number: {part}")
        p = int(part)
        if p == 0:
            raise ValueError("Page numbers must be positive (got 0)")
        if p > total_pages:
            raise ValueError(f"Page {p} out of bounds (total pages: {total_pages})")
        selected.append(p - 1)

    return selected


def _stepped_range(start: int, end: int, step: int, total_pages: int) -> List[int]:
    if step == 0:
        raise ValueError("range step cannot be 0")
    if (end - start) * step < 0:
        raise ValueError(f"range step does not progress from {start} to {end}")
    # Validate only the boundary values — every intermediate value is in-range by arithmetic
    _validate_page(start, total_pages)
    last = start if start == end else end if (end - start) % step == 0 else start + ((end - start) // step) * step
    _validate_page(last, total_pages)
    stop = end + (1 if step > 0 else -1)
    return [p - 1 for p in range(start, stop, step)]


def _validate_page(p: int, total_pages: int) -> None:
    if p <= 0:
        raise ValueError("Page numbers must be positive")
    if p > total_pages:
        raise ValueError(f"Page {p} out of bounds (total pages: {total_pages})")


def build_default_output_path(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    ext = ext or '.pdf'
    candidate = f"{base}.selected{ext}"
    if not os.path.exists(candidate):
        return candidate
    counter = 1
    while True:
        candidate = f"{base}.selected-{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _resolve_pages(input_pdf: str, pages_expr: str) -> List[int]:
    reader = PdfReader(input_pdf)
    return parse_pages(pages_expr, len(reader.pages))


def extract_pages(input_pdf: str, pages_expr: str, output_pdf: str | None) -> str | None:
    """Extract pages from input_pdf and write to output_pdf.

    Pass output_pdf='-' to write binary PDF to stdout.
    Returns the output path, or None when writing to stdout.
    """
    reader = PdfReader(input_pdf)
    page_indices = parse_pages(pages_expr, len(reader.pages))

    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])

    if output_pdf == '-':
        writer.write(sys.stdout.buffer)
        return None

    if output_pdf is None:
        output_pdf = build_default_output_path(input_pdf)

    with open(output_pdf, 'wb') as f:
        writer.write(f)

    return output_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input', help='Path to input PDF file')
    parser.add_argument('pages', help='Pages to include (see PAGE EXPRESSION SYNTAX above)')
    parser.add_argument(
        '-o', '--output',
        help='Output PDF path; use - to write to stdout (default: <input>.selected.pdf)',
        default=None,
    )
    parser.add_argument(
        '--print-only',
        action='store_true',
        help='Only print the expanded page numbers (1-based), then exit',
    )

    args = parser.parse_args()

    if args.print_only:
        page_indices = _resolve_pages(args.input, args.pages)
        print(','.join(str(i + 1) for i in page_indices))
        return

    output_path = extract_pages(args.input, args.pages, args.output)
    if output_path is not None:
        print(f"Wrote: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
