#!/usr/bin/env python3
"""
1）把所有要打印的页面挑出来，按顺序排好
2）先打印单数，从前往后打印
3）再打印双数，从后往前打印（反着）
页数可以用9-53:4这样的表达式，也可以用53-9:-4反着写
"""

import argparse
import os
import re
from typing import List, Set

from PyPDF2 import PdfReader, PdfWriter


def parse_pages(pages_expr: str, total_pages: int) -> List[int]:
    """Parse a pages expression like "1,3,5-7" into zero-based page indices.

    - Input pages are 1-based for user friendliness.
    - Supports single numbers and inclusive ranges joined by commas.
    - Validates that all pages are within [1, total_pages].
    """
    if not pages_expr:
        raise ValueError("pages expression cannot be empty")

    selected: List[int] = []
    # Support tokens separated by commas and/or whitespace (spaces/newlines/tabs)
    parts = [p.strip() for p in re.split(r"[\s,]+", pages_expr) if p.strip()]
    if not parts:
        raise ValueError("pages expression did not contain any pages")

    for part in parts:
        # Support explicit range-like expression: range(start,end,step) inclusive
        if part.lower().startswith('range(') and part.endswith(')'):
            inner = part[6:-1]
            nums = [n.strip() for n in inner.split(',') if n.strip()]
            if len(nums) != 3 or not all(s.lstrip('-').isdigit() for s in nums):
                raise ValueError(f"Invalid range(...) expression: {part}")
            start = int(nums[0])
            end = int(nums[1])
            step = int(nums[2])
            if step == 0:
                raise ValueError("range step cannot be 0")
            if start == end:
                # Single value
                if start <= 0:
                    raise ValueError("Page numbers must be positive")
                if start > total_pages:
                    raise ValueError(
                        f"Page {start} out of bounds (total pages: {total_pages})"
                    )
                selected.append(start - 1)
                continue
            # Determine progression direction
            if (end - start) // step < 0:
                # Step sign does not move toward end
                raise ValueError(f"range step does not progress from {start} to {end}")
            current = start
            if step > 0:
                while current <= end:
                    if current <= 0:
                        raise ValueError("Page numbers must be positive")
                    if current > total_pages:
                        raise ValueError(
                            f"Page {current} out of bounds (total pages: {total_pages})"
                        )
                    selected.append(current - 1)
                    current += step
            else:
                while current >= end:
                    if current <= 0:
                        raise ValueError("Page numbers must be positive")
                    if current > total_pages:
                        raise ValueError(
                            f"Page {current} out of bounds (total pages: {total_pages})"
                        )
                    selected.append(current - 1)
                    current += step
            continue
        # Support stepped ranges like start-end:step or start..end..step (inclusive)
        m = re.match(r"^(?P<start>-?\d+)[.]{2}(?P<end>-?\d+)[.]{2}(?P<step>-?\d+)$", part)
        if not m:
            m = re.match(r"^(?P<start>-?\d+)\s*-\s*(?P<end>-?\d+)\s*:\s*(?P<step>-?\d+)$", part)
        if m:
            start = int(m.group('start'))
            end = int(m.group('end'))
            step_str = m.group('step')
            if step_str is None or step_str == '':
                raise ValueError(f"Stepped range requires step: {part}")
            step = int(step_str)
            if step == 0:
                raise ValueError("range step cannot be 0")
            if start == end:
                if start <= 0:
                    raise ValueError("Page numbers must be positive")
                if start > total_pages:
                    raise ValueError(
                        f"Page {start} out of bounds (total pages: {total_pages})"
                    )
                selected.append(start - 1)
                continue
            if (end - start) // step < 0:
                raise ValueError(f"range step does not progress from {start} to {end}")
            current = start
            if step > 0:
                while current <= end:
                    if current <= 0:
                        raise ValueError("Page numbers must be positive")
                    if current > total_pages:
                        raise ValueError(
                            f"Page {current} out of bounds (total pages: {total_pages})"
                        )
                    selected.append(current - 1)
                    current += step
            else:
                while current >= end:
                    if current <= 0:
                        raise ValueError("Page numbers must be positive")
                    if current > total_pages:
                        raise ValueError(
                            f"Page {current} out of bounds (total pages: {total_pages})"
                        )
                    selected.append(current - 1)
                    current += step
            continue
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            if not start_str.isdigit() or not end_str.isdigit():
                raise ValueError(f"Invalid range: {part}")
            start = int(start_str)
            end = int(end_str)
            if start <= 0 or end <= 0:
                raise ValueError("Page numbers must be positive")
            if start > end:
                raise ValueError(f"Invalid range (start > end): {part}")
            if end > total_pages:
                raise ValueError(
                    f"Page {end} out of bounds (total pages: {total_pages})"
                )
            for p in range(start, end + 1):
                selected.append(p - 1)
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid page number: {part}")
            p = int(part)
            if p <= 0:
                raise ValueError("Page numbers must be positive")
            if p > total_pages:
                raise ValueError(
                    f"Page {p} out of bounds (total pages: {total_pages})"
                )
            selected.append(p - 1)

    return selected


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


def extract_pages(input_pdf: str, pages_expr: str, output_pdf: str | None) -> str:
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)

    page_indices = parse_pages(pages_expr, total_pages)
    if not page_indices:
        raise ValueError("No valid pages selected")
    one_based = [str(i + 1) for i in page_indices]
    print(','.join(one_based))

    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])

    if output_pdf is None:
        output_pdf = build_default_output_path(input_pdf)

    with open(output_pdf, 'wb') as f:
        writer.write(f)

    return output_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select specific pages from a PDF and write to a new PDF",
    )
    parser.add_argument(
        'input',
        help='Path to input PDF file',
    )
    parser.add_argument(
        'pages',
        help=(
            'Pages to include. Tokens can be separated by space or comma. '\
            'Supported: single numbers (e.g. 3), ranges (e.g. 5-9), '\
            'stepped ranges (e.g. 9-53:4 or 9..53..4), and range(9,53,4).'
        ),
    )
    parser.add_argument(
        '-o', '--output',
        help='Output PDF path (default: <input>.selected.pdf)',
        default=None,
    )
    parser.add_argument(
        '--print-only',
        action='store_true',
        help='Only print the expanded page numbers (1-based), then exit',
    )

    args = parser.parse_args()

    if args.print_only:
        reader = PdfReader(args.input)
        total_pages = len(reader.pages)
        page_indices = parse_pages(args.pages, total_pages)
        one_based = [str(i + 1) for i in page_indices]
        print(','.join(one_based))
        return

    output_path = extract_pages(args.input, args.pages, args.output)
    print(f"Wrote: {output_path}")


if __name__ == '__main__':
    main()

