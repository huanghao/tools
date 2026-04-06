#!/usr/bin/env python3
"""
把多页PDF按网格拼接到一张纸上，便于缩印打印。

示例：
  python merge_multi_pages.py input.pdf -o output.pdf --rows 2 --cols 2
  python merge_multi_pages.py input.pdf --pages "1-8" --rows 3 --cols 2
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable, List, Tuple

import fitz  # PyMuPDF

try:
    # 复用 select_pages.py 里已经实现的复杂页码解析
    from select_pages import parse_pages as _parse_pages  # type: ignore
except Exception:  # pragma: no cover - 兜底处理导入失败
    _parse_pages = None


def parse_page_indices(pages_expr: str | None, total_pages: int) -> List[int]:
    """Parse a pages expression (1-based) into zero-based indices."""
    if not pages_expr:
        return list(range(total_pages))

    if _parse_pages is not None:
        return _parse_pages(pages_expr, total_pages)

    # 简单兜底：支持逗号分隔和区间 start-end
    indices: List[int] = []
    for part in pages_expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            if start <= 0 or end <= 0:
                raise ValueError("页码必须为正整数")
            if start > end:
                raise ValueError(f"区间起点必须小于等于终点: {part}")
            for page in range(start, end + 1):
                if page > total_pages:
                    raise ValueError(f"页码超出范围: {page}")
                indices.append(page - 1)
        else:
            page = int(part)
            if page <= 0:
                raise ValueError("页码必须为正整数")
            if page > total_pages:
                raise ValueError(f"页码超出范围: {page}")
            indices.append(page - 1)
    if not indices:
        raise ValueError("没有解析出任何有效的页码")
    return indices


def chunked(iterable: Iterable[int], size: int) -> Iterable[List[int]]:
    """Yield lists of length `size` from iterable."""
    chunk: List[int] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def build_default_output_path(input_path: Path) -> Path:
    base = input_path.with_suffix("")
    candidate = Path(f"{base}.multi.pdf")
    counter = 1
    while candidate.exists():
        candidate = Path(f"{base}.multi-{counter}.pdf")
        counter += 1
    return candidate


def merge_pages(
    input_pdf: Path,
    output_pdf: Path,
    page_indices: List[int],
    rows: int,
    cols: int,
    margin: float,
    spacing: float,
    order: str,
    keep_proportion: bool,
    page_size: Tuple[float, float] | None,
) -> None:
    """Create a new PDF with multiple source pages placed on one sheet."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows 和 cols 必须为正整数")
    cells_per_page = rows * cols
    if cells_per_page <= 0:
        raise ValueError("rows * cols 必须大于 0")
    if margin < 0 or spacing < 0:
        raise ValueError("margin 和 spacing 不能为负数")

    if not page_indices:
        raise ValueError("没有可处理的页面")

    with fitz.open(input_pdf) as src_doc, fitz.open() as out_doc:
        total_pages_src = src_doc.page_count
        if any(idx < 0 or idx >= total_pages_src for idx in page_indices):
            raise ValueError("页码超出范围")

        first_rect = src_doc[0].rect
        target_page_width, target_page_height = (
            page_size if page_size is not None else (first_rect.width, first_rect.height)
        )

        available_width = target_page_width - 2 * margin - (cols - 1) * spacing
        available_height = target_page_height - 2 * margin - (rows - 1) * spacing
        if available_width <= 0 or available_height <= 0:
            raise ValueError(
                "margin/spacing 设置过大，导致可用空间为负或零，请调整参数"
            )

        cell_width = available_width / cols
        cell_height = available_height / rows

        fill_order_row_major = order == "row-major"

        for group in chunked(page_indices, cells_per_page):
            out_page = out_doc.new_page(width=target_page_width, height=target_page_height)

            for pos, src_index in enumerate(group):
                if fill_order_row_major:
                    row = pos // cols
                    col = pos % cols
                else:
                    row = pos % rows
                    col = pos // rows

                x0 = margin + col * (cell_width + spacing)
                y0 = margin + row * (cell_height + spacing)
                slot = fitz.Rect(x0, y0, x0 + cell_width, y0 + cell_height)
                out_page.show_pdf_page(
                    slot,
                    src_doc,
                    src_index,
                    overlay=True,
                    keep_proportion=keep_proportion,
                )

        out_doc.save(output_pdf, deflate=True)
        print(
            f"生成完成：{output_pdf} "
            f"(共 {math.ceil(len(page_indices) / cells_per_page)} 页，每页 {rows}x{cols})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把多个PDF页面拼接成一页，实现缩印打印效果。",
    )
    parser.add_argument("input_pdf", help="输入PDF文件路径")
    parser.add_argument(
        "-o",
        "--output",
        help="输出PDF文件路径，默认在输入文件旁生成 *.multi.pdf",
    )
    parser.add_argument("--pages", help="要处理的页码，1-based。支持 1,3,5 或 1-8 之类的表达式。")
    parser.add_argument("--rows", type=int, default=2, help="拼接行数，默认 2")
    parser.add_argument("--cols", type=int, default=2, help="拼接列数，默认 2")
    parser.add_argument(
        "--margin",
        type=float,
        default=20.0,
        help="页面四周留白（单位：pt，1 pt ≈ 0.35mm），默认 20",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=10.0,
        help="单元格之间的间距（单位：pt），默认 10",
    )
    parser.add_argument(
        "--order",
        choices=("row-major", "column-major"),
        default="row-major",
        help="排版顺序：row-major 行优先（默认），column-major 列优先",
    )
    parser.add_argument(
        "--no-keep-proportion",
        action="store_true",
        help="默认按比例缩放以避免拉伸，指定后强制填满网格",
    )
    parser.add_argument(
        "--page-size",
        choices=("match", "A4", "Letter"),
        default="match",
        help="输出纸张大小：match 表示跟输入文件第一页一致（默认），也可选择 A4 或 Letter",
    )
    parser.add_argument(
        "--page-width",
        type=float,
        help="自定义输出页面宽度（单位：pt），与 --page-height 一起使用，优先级高于 --page-size",
    )
    parser.add_argument(
        "--page-height",
        type=float,
        help="自定义输出页面高度（单位：pt），与 --page-width 一起使用，优先级高于 --page-size",
    )
    return parser.parse_args()


def _resolve_page_size(args: argparse.Namespace) -> Tuple[float, float] | None:
    if args.page_width is not None or args.page_height is not None:
        if args.page_width is None or args.page_height is None:
            raise ValueError("自定义页面尺寸时必须同时提供 --page-width 和 --page-height")
        if args.page_width <= 0 or args.page_height <= 0:
            raise ValueError("自定义页面尺寸必须为正数")
        return float(args.page_width), float(args.page_height)

    preset_sizes = {
        "A4": (595.276, 841.89),  # 210mm x 297mm
        "Letter": (612.0, 792.0),  # 8.5in x 11in
    }
    if args.page_size == "match":
        return None
    return preset_sizes[args.page_size]


def main() -> int:
    args = parse_args()

    input_path = Path(args.input_pdf).expanduser().resolve()
    if not input_path.exists():
        print(f"文件不存在：{input_path}")
        return 1
    if input_path.suffix.lower() != ".pdf":
        print("输入文件必须是 PDF")
        return 1

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else build_default_output_path(input_path)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with fitz.open(input_path) as src_doc:
            page_indices = parse_page_indices(args.pages, src_doc.page_count)
    except Exception as exc:
        print(f"解析页码失败：{exc}")
        return 1

    try:
        merge_pages(
            input_path,
            output_path,
            page_indices,
            rows=args.rows,
            cols=args.cols,
            margin=args.margin,
            spacing=args.spacing,
            order=args.order,
            keep_proportion=not args.no_keep_proportion,
            page_size=_resolve_page_size(args),
        )
    except Exception as exc:
        print(f"拼接失败：{exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
